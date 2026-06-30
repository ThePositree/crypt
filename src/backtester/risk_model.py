from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .exit_geometry import ExitGeometryConfig, resolve_exit_levels
from .margin_policy import (
    DEFAULT_LIQUIDATION_BUFFER_PCT,
    DEFAULT_LIQUIDATION_FEE_RATE,
    DEFAULT_MAINTENANCE_MARGIN_RATE,
    maintenance_margin_rate_for_size,
    per_entry_margin_cap,
    select_liquidation_safe_leverage_and_locked_margin,
)

logger = logging.getLogger(__name__)


@dataclass
class EntryContext:
    """
    Context required to calculate risk-based position sizing.

    Parameters
    ----------
    signal : int
        Trading signal direction. Expected values are ``1`` for long and
        ``-1`` for short. Any other value is treated as \"no trade\" at the
        risk-model level.
    sl_price : float
        Stop-loss price associated with the signal.
    entry_price : float
        Price at which the position would be opened (typically next bar open).
    capital : float
        Current total strategy capital before opening the position.
    risk_base_capital : float
        Capital base used for risk sizing. This can differ from current
        capital when sizing is anchored to a weekly/monthly/backtest window.
    total_locked_margin : float
        Total margin currently locked in open positions. Used to derive
        available balance.
    open_positions : int
        Number of positions already open before this entry attempt.
    risk_percent : float
        Fraction of available balance to risk on this trade, expressed in
        percent (e.g. ``1.0`` for 1%).
    rrr : float
        Reward-to-risk ratio. Defines how many times further TP is than SL.
    """

    signal: int
    sl_price: float
    entry_price: float
    capital: float
    risk_base_capital: float
    total_locked_margin: float
    open_positions: int
    risk_percent: float
    rrr: float
    existing_leverage: float | None = None
    existing_position_size: float = 0.0


@dataclass
class RiskResult:
    """
    Result of risk-based position sizing.

    Parameters
    ----------
    size : float
        Position size in asset units.
    position_value : float
        Notional value of the position (``size * entry_price``).
    required_leverage : float
        Leverage required to open the position under margin constraints.
    locked_margin : float
        Margin that must be locked for this position.
    risk_value : float
        Absolute risk in currency units put at risk in this trade.
    sl_dist : float
        Distance from entry to stop loss in price units.
    sl_price : float
        Resolved stop-loss price level.
    tp_price : float
        Take-profit price level.
    is_long : bool
        True if position is long, False if short.
    available_balance : float
        Available balance after subtracting ``total_locked_margin`` from
        ``capital``.
    """

    size: float
    position_value: float
    required_leverage: float
    locked_margin: float
    risk_value: float
    sl_dist: float
    sl_price: float
    tp_price: float
    is_long: bool
    available_balance: float
    liquidation_price: float
    maintenance_margin_rate: float
    liquidation_fee_rate: float
    liquidation_buffer_pct: float
    maintenance_margin_tier_schedule: str | None


class RiskModel:
    """
    Abstract interface for risk models.

    Implementations encapsulate risk calculation logic such as position sizing,
    leverage checks and TP/SL placement. They must be pure with respect to
    engine state: all required inputs are provided via :class:`EntryContext`
    and results are returned via :class:`RiskResult`.
    """

    def calculate_position(self, ctx: EntryContext) -> Optional[RiskResult]:
        """
        Calculate risk-based position parameters for a potential entry.

        Parameters
        ----------
        ctx : EntryContext
            Per-bar context describing the potential trade.

        Returns
        -------
        RiskResult or None
            RiskResult with fully specified position parameters if the trade
            is allowed under the current risk configuration, otherwise None.
        """

        raise NotImplementedError


class BasicRiskModel(RiskModel):
    """
    Default risk model mirroring the original ExecutionSim implementation.

    The model performs:

    - validation of stop-loss distance relative to entry;
    - computation of available balance and risk value;
    - position size and notional calculation;
    - leverage and margin-based checks using configuration limits;
    - take-profit price placement based on reward/risk ratio.
    """

    def __init__(
        self,
        *,
        max_allowed_margin: float,
        max_positions: int,
        max_allowed_leverage: float,
        exit_geometry_config: ExitGeometryConfig | None = None,
        maintenance_margin_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
        liquidation_fee_rate: float = DEFAULT_LIQUIDATION_FEE_RATE,
        liquidation_buffer_pct: float = DEFAULT_LIQUIDATION_BUFFER_PCT,
        maintenance_margin_tier_schedule: str | None = None,
    ) -> None:
        """
        Create a basic risk model.

        Parameters
        ----------
        max_allowed_margin : float
            Maximum allowed margin fraction used for leverage calculations.
            Mirrors ``ExecutionSim.max_allowed_margin`` semantics.
        max_positions : int
            Maximum number of simultaneous positions. Used to derive margin
            share when ``max_allowed_margin`` is zero.
        max_allowed_leverage : float
            Maximum allowed leverage. If required leverage exceeds this value,
            the trade is rejected.
        exit_geometry_config : ExitGeometryConfig | None
            TP/SL placement mode. Defaults to legacy SL-first ``sl_rrr``.
        """

        self._max_allowed_margin = max_allowed_margin
        self._max_positions = max_positions
        self._max_allowed_leverage = max_allowed_leverage
        self._exit_geometry_config = exit_geometry_config or ExitGeometryConfig()
        self._maintenance_margin_rate = maintenance_margin_rate
        self._liquidation_fee_rate = liquidation_fee_rate
        self._liquidation_buffer_pct = liquidation_buffer_pct
        self._maintenance_margin_tier_schedule = maintenance_margin_tier_schedule

    def calculate_position(self, ctx: EntryContext) -> Optional[RiskResult]:
        """
        Calculate risk-based position parameters for a potential entry.

        This method reproduces the sizing and leverage logic previously
        embedded in :meth:`ExecutionSim._try_open_position` while remaining
        independent of the simulation engine.
        """

        signal = ctx.signal
        if signal not in (1, -1):
            return None

        is_long = signal == 1
        entry_price = ctx.entry_price
        structural_sl_price = ctx.sl_price

        resolved = resolve_exit_levels(
            signal=signal,
            entry_price=entry_price,
            structural_sl_price=structural_sl_price,
            rrr=ctx.rrr,
            config=self._exit_geometry_config,
        )
        if resolved is None:
            logger.debug(
                "Exit geometry rejected trade at entry %r (structural sl %r)",
                entry_price,
                structural_sl_price,
            )
            return None

        sl_price = resolved.sl_price
        sl_dist = resolved.sl_dist
        tp_price = resolved.tp_price

        # Available balance and risk
        total_locked_margin = ctx.total_locked_margin
        available_balance = ctx.capital - total_locked_margin
        risk_available_balance = max(ctx.risk_base_capital - total_locked_margin, 0.0)
        risk_value = risk_available_balance * (ctx.risk_percent / 100)
        if risk_value <= 0:
            logger.debug("Risk value is non-positive, skipping signal")
            return None

        # Position size and value
        size = risk_value / sl_dist
        position_value = size * entry_price

        per_entry_cap = per_entry_margin_cap(
            available_balance=available_balance,
            max_allowed_margin=self._max_allowed_margin,
            max_positions=self._max_positions,
            open_positions=ctx.open_positions,
        )
        leverage_result = select_liquidation_safe_leverage_and_locked_margin(
            position_value=position_value,
            position_size=size + ctx.existing_position_size,
            per_entry_cap=per_entry_cap,
            max_allowed_leverage=self._max_allowed_leverage,
            entry_price=entry_price,
            stop_price=sl_price,
            is_long=is_long,
            maintenance_margin_rate=self._maintenance_margin_rate,
            liquidation_fee_rate=self._liquidation_fee_rate,
            liquidation_buffer_pct=self._liquidation_buffer_pct,
            maintenance_margin_tier_schedule=self._maintenance_margin_tier_schedule,
            existing_leverage=ctx.existing_leverage,
        )
        if leverage_result is None:
            logger.debug(
                "Position value %.2f does not fit per-entry margin cap %.2f",
                position_value,
                per_entry_cap,
            )
            return None

        required_leverage, locked_margin, liquidation_price = leverage_result
        resolved_maintenance_margin_rate = maintenance_margin_rate_for_size(
            position_size=size + ctx.existing_position_size,
            default_rate=self._maintenance_margin_rate,
            tier_schedule=self._maintenance_margin_tier_schedule,
        )

        return RiskResult(
            size=size,
            position_value=position_value,
            required_leverage=required_leverage,
            locked_margin=locked_margin,
            risk_value=risk_value,
            sl_dist=sl_dist,
            sl_price=sl_price,
            tp_price=tp_price,
            is_long=is_long,
            available_balance=available_balance,
            liquidation_price=liquidation_price,
            maintenance_margin_rate=resolved_maintenance_margin_rate,
            liquidation_fee_rate=self._liquidation_fee_rate,
            liquidation_buffer_pct=self._liquidation_buffer_pct,
            maintenance_margin_tier_schedule=self._maintenance_margin_tier_schedule,
        )
