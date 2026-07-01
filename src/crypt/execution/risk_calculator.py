"""LiveRiskCalculator — mirrors ExecutionSim risk/sizing logic exactly.

All sizing decisions come from the same backtester classes:
  - backtester.risk_model.BasicRiskModel
  - backtester.exit_geometry.resolve_exit_levels / ExitGeometryConfig
  - backtester.margin_policy.per_entry_margin_cap / select_leverage_and_locked_margin
  - backtester.fee_model.StaticPercentFeeModel

If the backtester logic changes, this module must change in the same commit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from backtester.exit_geometry import ExitGeometryConfig, exit_geometry_config_from_args
from backtester.fee_model import StaticPercentFeeModel
from backtester.margin_policy import per_entry_margin_cap
from backtester.risk_model import BasicRiskModel, EntryContext, RiskResult
from crypt.execution.position_state import ExecutionState, LivePosition
from crypt.execution.settings import ExecutionSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveEntryDecision:
    """Computed entry parameters — all values are ready to pass to OKXTradingClient."""

    risk_result: RiskResult
    risk_base_capital: float
    fee_entry: float
    available_balance: float
    total_locked_margin: float


class LiveRiskCalculator:
    """
    Computes position size, SL, TP, leverage, and margin for a live entry.

    Mirrors `ExecutionSim._try_open_position()` and
    `ExecutionSim._risk_base_capital_for_entry()` exactly.
    """

    def __init__(self, settings: ExecutionSettings) -> None:
        self._settings = settings
        self._exit_geometry_config: ExitGeometryConfig = exit_geometry_config_from_args(
            exit_geometry=settings.exit_geometry,
            tp_move_pct=settings.tp_move_pct if settings.exit_geometry == "tp_pct" else None,
            structural_sl_mode=settings.structural_sl_mode,
            min_tp_move_pct=settings.min_tp_move_pct,
        )
        self._risk_model = BasicRiskModel(
            max_allowed_margin=settings.max_allowed_margin,
            max_positions=settings.max_positions,
            max_allowed_leverage=settings.max_leverage,
            exit_geometry_config=self._exit_geometry_config,
            maintenance_margin_rate=settings.maintenance_margin_rate,
            liquidation_fee_rate=settings.liquidation_fee_rate,
            liquidation_buffer_pct=settings.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=settings.maintenance_margin_tier_schedule,
        )
        self._fee_model = StaticPercentFeeModel(
            taker_fee=settings.taker_fee,
            maker_fee=settings.maker_fee,
        )

    # ------------------------------------------------------------------
    # Monthly risk base (mirrors ExecutionSim._risk_base_capital_for_entry)
    # ------------------------------------------------------------------

    def update_monthly_risk_base(
        self,
        state: ExecutionState,
        entry_time: datetime,
        current_capital: float,
    ) -> float:
        """
        Return the risk-base capital for this entry and update state if needed.

        Mirrors `ExecutionSim._risk_base_capital_for_entry()` for
        `risk_base_period = "monthly"`.
        """
        period = self._settings.risk_base_period

        if period == "trade":
            return current_capital
        if period == "backtest":
            if state.monthly_risk_base <= 0:
                state.monthly_risk_base = current_capital
            return state.monthly_risk_base

        entry_time_utc = entry_time.astimezone(UTC)
        if period == "weekly":
            iso = entry_time_utc.isocalendar()
            window_key: tuple[int, int] = (int(iso.year), int(iso.week))
        else:
            window_key = (int(entry_time_utc.year), int(entry_time_utc.month))

        if state.risk_window_month != window_key:
            state.risk_window_month = window_key
            state.monthly_risk_base = current_capital
            logger.info(
                "New risk window %s — monthly_risk_base set to %.2f",
                window_key,
                current_capital,
            )

        return state.monthly_risk_base

    # ------------------------------------------------------------------
    # Main sizing method
    # ------------------------------------------------------------------

    def calculate(
        self,
        *,
        signal: int,
        sl_price: float,
        entry_price: float,
        capital: float,
        risk_base_capital: float,
        open_positions: list[LivePosition],
        risk_percent: float | None = None,
        rrr: float | None = None,
        exit_geometry: str | None = None,
        tp_move_pct: float | None = None,
        structural_sl_mode: str | None = None,
        min_tp_move_pct: float | None = None,
    ) -> LiveEntryDecision | None:
        """
        Compute entry parameters for a new position.

        Parameters
        ----------
        signal : int
            1 for long, -1 for short.
        sl_price : float
            Structural SL price from `crypt_ensemble`.
        entry_price : float
            Expected fill price (current H1 open, which is "next bar open"
            relative to the signal bar — same semantics as the backtester).
        capital : float
            Current realized equity (OKX USDT balance).
        risk_base_capital : float
            Capital base for this period (from `update_monthly_risk_base()`).
        open_positions : list[LivePosition]
            Currently open positions (all symbols or just this symbol).

        Returns
        -------
        LiveEntryDecision or None
            None if any guard rejects the trade.
        """
        if signal not in (1, -1):
            return None

        # max_positions guard
        n_open = len([p for p in open_positions if p.status == "open"])
        if self._settings.max_positions > 0 and n_open >= self._settings.max_positions:
            logger.debug("max_positions=%d reached, skipping entry", self._settings.max_positions)
            return None

        total_locked_margin = sum(p.locked_margin for p in open_positions if p.status == "open")

        effective_risk_percent = (
            self._settings.risk_percent if risk_percent is None else float(risk_percent)
        )
        effective_rrr = self._settings.rrr if rrr is None else float(rrr)
        is_long_signal = signal == 1
        same_side_positions = [
            position
            for position in open_positions
            if position.status == "open" and position.is_long is is_long_signal
        ]
        same_side_leverage = same_side_positions[0].leverage if same_side_positions else None
        same_side_size = sum(position.size for position in same_side_positions)
        risk_model = self._risk_model
        if (
            exit_geometry is not None
            or tp_move_pct is not None
            or structural_sl_mode is not None
            or min_tp_move_pct is not None
        ):
            risk_model = BasicRiskModel(
                max_allowed_margin=self._settings.max_allowed_margin,
                max_positions=self._settings.max_positions,
                max_allowed_leverage=self._settings.max_leverage,
                exit_geometry_config=exit_geometry_config_from_args(
                    exit_geometry=exit_geometry or self._exit_geometry_config.mode,
                    tp_move_pct=tp_move_pct
                    if tp_move_pct is not None
                    else self._exit_geometry_config.tp_move_pct,
                    structural_sl_mode=structural_sl_mode
                    or self._exit_geometry_config.structural_sl_mode,
                    min_tp_move_pct=min_tp_move_pct
                    if min_tp_move_pct is not None
                    else self._exit_geometry_config.min_tp_move_pct,
                ),
                maintenance_margin_rate=self._settings.maintenance_margin_rate,
                liquidation_fee_rate=self._settings.liquidation_fee_rate,
                liquidation_buffer_pct=self._settings.liquidation_buffer_pct,
                maintenance_margin_tier_schedule=self._settings.maintenance_margin_tier_schedule,
            )

        entry_ctx = EntryContext(
            signal=signal,
            sl_price=sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=risk_base_capital,
            total_locked_margin=total_locked_margin,
            open_positions=n_open,
            risk_percent=effective_risk_percent,
            rrr=effective_rrr,
            existing_leverage=same_side_leverage,
            existing_position_size=same_side_size,
        )

        risk_result = risk_model.calculate_position(entry_ctx)
        if risk_result is None:
            logger.debug("BasicRiskModel rejected entry at price %s", entry_price)
            return None

        # Available balance check (mirrors ExecutionSim._can_open_position)
        available_balance = capital - total_locked_margin
        per_entry_cap = per_entry_margin_cap(
            available_balance=available_balance,
            max_allowed_margin=self._settings.max_allowed_margin,
            max_positions=self._settings.max_positions,
            open_positions=n_open,
        )
        required_margin = risk_result.position_value / risk_result.required_leverage
        if required_margin > per_entry_cap + 1e-9:
            logger.debug(
                "Insufficient margin: required=%.2f, cap=%.2f",
                required_margin,
                per_entry_cap,
            )
            return None

        # Fee + exposure guards
        fee_ctx = EntryContext(
            signal=signal,
            sl_price=sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=risk_base_capital,
            total_locked_margin=total_locked_margin,
            open_positions=n_open,
            risk_percent=effective_risk_percent,
            rrr=effective_rrr,
            existing_leverage=same_side_leverage,
            existing_position_size=same_side_size,
        )
        fee_entry = self._fee_model.calculate_entry_fee(risk_result.position_value, fee_ctx)
        net_exposure = risk_result.position_value - fee_entry

        if fee_entry >= risk_result.risk_value * 2:
            logger.debug(
                "Fee %.4f >= 2x risk_value %.4f — skipping", fee_entry, risk_result.risk_value
            )
            return None

        if net_exposure < self._settings.min_net_exposure * available_balance:
            logger.debug(
                "Net exposure %.2f < min_net_exposure * balance %.2f — skipping",
                net_exposure,
                self._settings.min_net_exposure * available_balance,
            )
            return None

        return LiveEntryDecision(
            risk_result=risk_result,
            risk_base_capital=risk_base_capital,
            fee_entry=fee_entry,
            available_balance=available_balance,
            total_locked_margin=total_locked_margin,
        )
