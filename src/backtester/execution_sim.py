import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypedDict

import pandas as pd
from tqdm.auto import tqdm

from .data_contracts import IntrabarExecutionData
from .exit_geometry import exit_geometry_config_from_args
from .fee_model import ExitContext, FeeModel, StaticPercentFeeModel
from .instrument_precision import instrument_precision_from_name
from .margin_policy import (
    DEFAULT_LIQUIDATION_BUFFER_PCT,
    DEFAULT_LIQUIDATION_FEE_RATE,
    DEFAULT_MAINTENANCE_MARGIN_RATE,
    ISOLATED_FUTURES_ALWAYS,
    aggregate_linear_liquidation_price,
    aggregate_liquidation_is_beyond_stops,
    leverage_is_within_size_tier,
    maintenance_margin_rate_for_size,
    per_entry_margin_cap,
)
from .risk_model import BasicRiskModel, EntryContext, RiskModel
from .tp_policy import TpPolicyConfig, adjust_tp_rrr
from .trailing_policy import build_native_trailing_geometry, with_closed_atr14


class _NotEnoughBarsError(Exception):
    """Internal signal that input data is too short for simulation."""


class _EntryContextDict(TypedDict, total=True):
    """Per-bar context for potential position entry."""

    signal: int
    sl_price: float
    risk_percent: float
    rrr: float
    entry_price: float | None
    position_ttl_bars: int
    position_ttl_minutes: int
    trail_activation_rrr: float
    trail_distance_atr: float
    exit_geometry: str
    tp_move_pct: float | None
    structural_sl_mode: str
    min_tp_move_pct: float
    position_group: str
    drain_on_group_change: bool
    tp_policy_enabled: bool
    tp_policy_min_original_rrr: float
    tp_policy_min_distance_pct: float | None
    tp_policy_min_last_touch_bars: int | None
    tp_policy_adjusted_rrr: float
    tp_last_touch_bars: int | None
    metadata: dict[str, Any]


_TRADE_METADATA_EXCLUDED_COLUMNS = frozenset(
    {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "signal",
        "signal_events",
        "sl_price",
        "risk_percent",
        "rrr",
        "position_ttl_bars",
        "position_ttl_minutes",
        "trail_activation_rrr",
        "trail_distance_atr",
        "exit_geometry",
        "tp_move_pct",
        "structural_sl_mode",
        "min_tp_move_pct",
        "position_group",
        "drain_on_group_change",
        "tp_policy_enabled",
        "tp_policy_min_original_rrr",
        "tp_policy_min_distance_pct",
        "tp_policy_min_last_touch_bars",
        "tp_policy_adjusted_rrr",
        "tp_last_touch_bars",
        "original_rrr",
        "effective_rrr",
        "tp_adjusted",
        "tp_adjustment_reason",
        "tp_distance_pct",
        "trail_atr",
        "entry_price",
        "index",
        "open_time",
        "tick_time",
    }
)


def _signal_events_request_trailing(df: pd.DataFrame) -> bool:
    if "signal_events" not in df.columns:
        return False
    for raw_events in df["signal_events"]:
        if raw_events is None:
            continue
        if not isinstance(raw_events, list):
            continue
        for event in raw_events:
            if not isinstance(event, dict):
                continue
            try:
                if float(event.get("trail_activation_rrr", 0.0)) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


@dataclass
class _InputColumnsMeta:
    """Metadata about optional per-bar input columns and their NaN counts."""

    has_risk_percent_col: bool
    has_rrr_col: bool
    has_entry_price_col: bool
    nan_count_risk_percent: int
    nan_count_rrr: int


@dataclass
class Position:
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry_price: float
    risk_base_capital: float
    size: float
    tp_price: float
    sl_price: float
    bar_opened: int
    fee_entry: float
    capital_before: float
    leverage: float
    locked_margin: float
    available_balance_before: float
    open_positions_before: int
    total_locked_margin_before: float
    total_locked_margin_after_entry: float
    is_long: bool
    liquidation_price: float
    maintenance_margin_rate: float
    liquidation_fee_rate: float
    liquidation_buffer_pct: float
    maintenance_margin_tier_schedule: str | None
    metadata: dict[str, Any]
    aggregate_entry_price: float | None = None
    position_ttl_bars: int = 0
    position_ttl_minutes: int = 0
    position_group: str = ""
    trail_activation_rrr: float = 0.0
    trail_distance_atr: float = 0.0
    trail_activation_price: float | None = None
    trail_callback_spread: float | None = None
    trail_active: bool = False
    best_favorable_price: float | None = None
    trail_stop_price: float | None = None

    def __post_init__(self):
        """Validation of input data."""
        if self.aggregate_entry_price is None:
            self.aggregate_entry_price = self.entry_price
        if self.size <= 0:
            raise ValueError("Position size must be positive")
        if self.is_long:
            if self.tp_price <= self.entry_price:
                raise ValueError("Take Profit price must be higher than entry price for long")
            if self.sl_price >= self.entry_price:
                raise ValueError("Stop Loss price must be lower than entry price for long")
        else:
            if self.tp_price >= self.entry_price:
                raise ValueError("Take Profit price must be lower than entry price for short")
            if self.sl_price <= self.entry_price:
                raise ValueError("Stop Loss price must be higher than entry price for short")
        if self.leverage < 1:
            raise ValueError("Leverage must be at least 1.0")


class ExitReason(StrEnum):
    """Standardized reasons for closing a position."""

    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    LIQUIDATION = "liquidation"
    UNSAFE_LIQUIDATION_BUFFER = "unsafe_liquidation_buffer"
    TTL_EXPIRED = "ttl_expired"
    OPEN = "open"


class ExecutionSim:
    """
    Trading execution simulator with support for multiple positions,
    risk management (TP/SL), simultaneous position limits,
    position time-to-live (TTL) and protection against economically unfavorable entries.

    Features:
    - Entry at open of next bar after signal
    - Exit via Take Profit, Stop Loss or TTL expiration (in bars)
    - Position size calculated based on risk_percent and SL distance
    - TP level calculated as: entry_price ± (entry_price - sl_price) * rrr
    - Entry/exit commissions (taker fee for entry and SL/exit, maker fee for TP)
    - Support for long (signal=1) and short (signal=-1) positions
    - Protection against opening positions with too small capital or high commission ratio
    - Support for multiple simultaneous positions with strict limit
    - Open positions at end of data remain ``exit_reason=open`` with unrealized
      PnL (no forced close at the last bar)
    - Isolated futures mode with leverage consistency and total position value limits
    - Configurable intra-bar TP/SL policy controlling how ambiguous bars are
      resolved using :class:`ExitReason` values.

    Notes on intra-bar TP/SL policy
    --------------------------------
    For a given bar, only its high/low are known, so when both TP and SL lie
    inside the bar range their true order is ambiguous. This simulator uses
    a configurable policy to resolve such bars:

    - ``bar_exit_policy="best_case"``:
        - If both TP and SL are touched within the same bar, prefer the more
          favorable outcome for the trader (``"take_profit"`` over
          ``"stop_loss"``).
    - ``bar_exit_policy="worst_case"``:
        - If both TP and SL are touched within the same bar, prefer the less
          favorable outcome (``"stop_loss"`` over ``"take_profit"``).

    In both modes:
    - If only one of TP/SL is hit within a bar, that exit is used.
    - TTL is evaluated after TP/SL; if neither TP nor SL is hit and TTL
      expires, the position is closed at next bar's open with
      ``exit_reason="ttl_expired"`` (see :class:`ExitReason`).

    Usage example:
    ```
        sim = ExecutionSim(
            initial_capital=1000,
            taker_fee=0.001,
            maker_fee=0.0002,
            risk_percent=1.0,   # 1% of capital at risk
            rrr=2.0,            # 2:1 reward/risk
            max_positions=3,
            position_ttl_bars=15,
            max_allowed_leverage=25.0,
            bar_exit_policy="worst_case",
        )
        trades = sim.run(df)
    ```
    """

    def __init__(
        self,
        initial_capital: float = 1000.0,
        taker_fee: float = 0.001,
        maker_fee: float = 0.0002,
        risk_percent: float = 1.0,
        rrr: float = 2.0,
        trail_activation_rrr: float = 0.0,
        trail_distance_atr: float = 0.0,
        max_positions: int = 0,
        position_ttl_bars: int = 0,
        position_ttl_minutes: int = 0,
        min_net_exposure: float = 0.01,
        max_allowed_leverage: float = 25.0,
        is_perpetual: bool = False,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        bar_exit_policy: str = "worst_case",
        max_daily_profit: float | None = None,
        max_daily_loss: float | None = None,
        trading_begin: int | None = None,
        trading_end: int | None = None,
        capital_sweep: str = "none",
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
        maintenance_margin_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
        liquidation_fee_rate: float = DEFAULT_LIQUIDATION_FEE_RATE,
        liquidation_buffer_pct: float = DEFAULT_LIQUIDATION_BUFFER_PCT,
        maintenance_margin_tier_schedule: str | None = None,
        instrument_precision_policy: str | None = None,
        intrabar_execution_timeframe: str | None = None,
        risk_model: RiskModel | None = None,
        fee_model: FeeModel | None = None,
    ):
        """
        Trading simulator initialization with risk-based position sizing.

        Parameters:
        ----------
        initial_capital : float, default 1000.0
            Starting capital in dollars (or other currency).
        taker_fee : float, default 0.001 (0.1%)
            Market order commission (entry and exit via SL/TTL). Applied to position volume.
        maker_fee : float, default 0.0002 (0.02%)
            Commission for a limit order (maker). Used when exiting via Take Profit (TP).
        risk_percent : float, default 1.0 (1%)
            Percentage of current capital you are willing to lose on a single trade.
            Example: 1.0 → 1% of current capital is at risk.
        rrr : float, default 2.0
            Reward to Risk ratio. Defines how many times further TP is than SL.
            Example: 2.0 → TP is 2x the distance from entry as SL.
        trail_activation_rrr : float, default 0.0
            Profit threshold, in structural stop-distance multiples, at which
            trailing stop mode starts. ``0`` disables trailing and preserves
            fixed-TP behaviour.
        trail_distance_atr : float, default 0.0
            Trailing stop distance in ATR units after activation. Required to
            be positive when ``trail_activation_rrr`` is positive.
        max_positions : int, default 0
            Maximum number of simultaneous open positions.
            If reached, new signals are ignored.
            Disabled if 0.
        position_ttl_bars : int, default 0
            Legacy maximum position duration in execution bars.
            If TP/SL not triggered, position closes at TTL expiration
            at next bar's open.
            Disabled if 0.
        position_ttl_minutes : int, default 0
            Maximum position duration in clock minutes. When set, this takes
            precedence over ``position_ttl_bars`` and is safe across mixed
            execution timeframes.
        min_net_exposure : float, default 0.01 (1%)
            Minimum capital percentage that must remain after commission
            when opening a position. If net_exposure < min_net_exposure * capital,
            position is not opened.
            Example: 0.01 → after fees, at least 1% of capital must be "net" position.
        max_allowed_leverage : float, default 25.0
            Maximum allowed leverage for the strategy.
            If leverage > max_allowed_leverage, position is not opened.
            Example: 25.0 → 25x leverage is not allowed.
        max_allowed_margin : float, default 1.0
            Maximum allowed margin for the strategy.
            If margin > max_allowed_margin, position is not opened.
        bar_exit_policy : {"best_case", "worst_case"}, default "worst_case"
            Policy for resolving ambiguous intra-bar exits when both TP and SL
            lie within a single bar's range.
            - "best_case": prefer take_profit over stop_loss when both are hit.
            - "worst_case": prefer stop_loss over take_profit when both are hit.
            If an unsupported value is provided, a ValueError is raised.
        risk_model : RiskModel | None, optional
            Custom risk model implementation. If None, a default
            :class:`BasicRiskModel` is used that mirrors the built-in sizing
            behaviour.
        fee_model : FeeModel | None, optional
            Custom fee model implementation. If None, a default
            :class:`StaticPercentFeeModel` is used that mirrors the original
            taker/maker commission logic.
        max_daily_profit : float | None, optional
            Maximum allowed daily profit in RRR units. Daily RRR is computed as
            ``profit_num * rrr - loss_num`` over all closed trades for a given
            day, where ``profit_num`` is the number of profitable trades and
            ``loss_num`` is the number of losing trades, and ``rrr`` is the
            simulator-level reward-to-risk ratio. If ``daily_rrr >= max_daily_profit``,
            new positions will not be opened until the next trading day. Disabled
            if None or 0.
        max_daily_loss : float | None, optional
            Maximum allowed daily loss in RRR units (absolute value). When
            ``daily_rrr <= -max_daily_loss``, new positions will not be opened
            until the next trading day. Disabled if None or 0.
        trading_begin : int | None, optional
            Start of trading session in hours (0-23) based on the timestamp in
            the input DataFrame. New positions are opened only on bars where
            ``trading_begin <= hour < trading_end`` (if configured). Disabled
            if None.
        trading_end : int | None, optional
            End of trading session in hours (1-24). New positions are opened
            only on bars where ``trading_begin <= hour < trading_end``.
            Disabled if None.

        Notes:
        ----------
        - Position size = risk_value / (entry_price - sl_price) [long] or
          (sl_price - entry_price) [short]
        - TP price = entry_price ± (entry_price - sl_price) * rrr
        - All exit prices (TP, SL, TTL) are checked on next bar after signal.
        - Entry happens at next bar's open.
        - TP/SL exit uses current bar's high/low for accurate modeling.
        - Positions are opened only if:
            a) signal exists (signal == 1 or -1)
            b) active positions count < max_positions
            c) capital >= min_capital_to_trade (implicit via min_net_exposure)
            d) net_exposure >= min_net_exposure * capital
            e) isolated futures constraints are satisfied (if enabled):
               - leverage matches existing positions
               - available balance covers required margin
        """
        del is_perpetual  # Retained for backward-compatible public construction.
        allowed_policies = {"best_case", "worst_case"}
        allowed_risk_base_periods = {"trade", "weekly", "monthly", "backtest"}
        allowed_capital_sweeps = {"none", "monthly_profit", "trade_profit"}

        bar_exit_policy_normalized = bar_exit_policy.strip().lower()
        if bar_exit_policy_normalized not in allowed_policies:
            msg = (
                "Unsupported bar_exit_policy "
                f"{bar_exit_policy!r}. Expected one of "
                f"{sorted(allowed_policies)!r}."
            )
            raise ValueError(msg)
        risk_base_period_normalized = risk_base_period.strip().lower()
        if risk_base_period_normalized not in allowed_risk_base_periods:
            msg = (
                "Unsupported risk_base_period "
                f"{risk_base_period!r}. Expected one of "
                f"{sorted(allowed_risk_base_periods)!r}."
            )
            raise ValueError(msg)
        capital_sweep_normalized = capital_sweep.strip().lower()
        if capital_sweep_normalized not in allowed_capital_sweeps:
            msg = (
                "Unsupported capital_sweep "
                f"{capital_sweep!r}. Expected one of "
                f"{sorted(allowed_capital_sweeps)!r}."
            )
            raise ValueError(msg)
        if trail_activation_rrr < 0:
            raise ValueError("trail_activation_rrr must be >= 0")
        if trail_distance_atr < 0:
            raise ValueError("trail_distance_atr must be >= 0")
        if trail_activation_rrr > 0 and trail_distance_atr <= 0:
            raise ValueError("trail_distance_atr must be > 0 when trailing is enabled")

        self.initial_capital = initial_capital
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.risk_percent = risk_percent
        self.rrr = rrr
        self.trail_activation_rrr = trail_activation_rrr
        self.trail_distance_atr = trail_distance_atr
        self.max_positions = max_positions
        self.position_ttl_bars = position_ttl_bars
        self.position_ttl_minutes = position_ttl_minutes
        self.min_net_exposure = min_net_exposure
        self.max_allowed_leverage = max_allowed_leverage
        self.is_isolated_futures = ISOLATED_FUTURES_ALWAYS
        self.max_allowed_margin = max_allowed_margin
        self.risk_base_period = risk_base_period_normalized
        self.bar_exit_policy = bar_exit_policy_normalized
        self.max_daily_profit = max_daily_profit
        self.max_daily_loss = max_daily_loss
        self.trading_begin = trading_begin
        self.trading_end = trading_end
        self.capital_sweep = capital_sweep_normalized
        self.maintenance_margin_rate = maintenance_margin_rate
        self.liquidation_fee_rate = liquidation_fee_rate
        self.liquidation_buffer_pct = liquidation_buffer_pct
        self.maintenance_margin_tier_schedule = maintenance_margin_tier_schedule
        self.instrument_precision_policy = instrument_precision_policy
        if intrabar_execution_timeframe not in {None, "1m"}:
            raise ValueError(
                "intrabar_execution_timeframe must be None or '1m', "
                f"got {intrabar_execution_timeframe!r}"
            )
        self.intrabar_execution_timeframe = intrabar_execution_timeframe
        self._instrument_precision = instrument_precision_from_name(instrument_precision_policy)
        self._exit_geometry_config = exit_geometry_config_from_args(
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
        )
        self._logger = logging.getLogger(__name__)

        # Risk/fee models
        self._risk_model: RiskModel = risk_model or BasicRiskModel(
            max_allowed_margin=self.max_allowed_margin,
            max_positions=self.max_positions,
            max_allowed_leverage=self.max_allowed_leverage,
            exit_geometry_config=self._exit_geometry_config,
            maintenance_margin_rate=self.maintenance_margin_rate,
            liquidation_fee_rate=self.liquidation_fee_rate,
            liquidation_buffer_pct=self.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=self.maintenance_margin_tier_schedule,
        )
        self._fee_model: FeeModel = fee_model or StaticPercentFeeModel(
            taker_fee=self.taker_fee,
            maker_fee=self.maker_fee,
        )
        self._risk_window_key: tuple[int, int] | None = None
        self._risk_window_capital = initial_capital

    def _risk_base_capital_for_entry(
        self, entry_time: pd.Timestamp, current_capital: float
    ) -> float:
        """Return capital used for risk sizing at this entry timestamp."""
        if self.risk_base_period == "trade":
            return current_capital

        if self.risk_base_period == "backtest":
            return self.initial_capital

        if self.risk_base_period == "weekly":
            iso = entry_time.isocalendar()
            window_key = (int(iso.year), int(iso.week))
        else:
            window_key = (int(entry_time.year), int(entry_time.month))

        if self._risk_window_key != window_key:
            self._risk_window_key = window_key
            self._risk_window_capital = current_capital
        return self._risk_window_capital

    def _can_open_position(
        self,
        new_position_value: float,
        new_leverage: float,
        active_positions: list[Position],
        available_balance: float,
    ) -> bool:
        """
        Check if new position can be opened.

        Parameters:
        -----------
        new_position_value : float
            Value of the new position
        new_leverage : float
            Leverage of the new position
        active_positions : list
            List of active Position objects
        available_balance : float
            Available balance (capital minus locked margin)

        Returns:
        -----------
        bool
            True if position can be opened, False otherwise
        """
        required_margin = new_position_value / new_leverage
        max_allowed_margin = per_entry_margin_cap(
            available_balance=available_balance,
            max_allowed_margin=self.max_allowed_margin,
            max_positions=self.max_positions,
            open_positions=len(active_positions),
        )

        if required_margin > max_allowed_margin:
            self._logger.debug(
                "Isolated futures: insufficient balance for margin. "
                "Required margin: %.2f, Max allowed margin: %.2f",
                required_margin,
                max_allowed_margin,
            )
            return False

        return True

    def _validate_input_df(self, df: pd.DataFrame) -> _InputColumnsMeta:
        """
        Validate input DataFrame and precompute optional column metadata.

        Returns
        -------
        _InputColumnsMeta
            Container with flags for optional columns and their NaN counts.
        """
        min_bar_to_run = 2
        if len(df) < min_bar_to_run:
            self._logger.warning("Not enough bars to run simulation")
            raise _NotEnoughBarsError

        required_columns = ["open", "high", "low", "close"]
        missing = [col for col in required_columns if col not in df.columns]
        has_signal_events = "signal_events" in df.columns
        if not has_signal_events:
            for col in ("signal", "sl_price"):
                if col not in df.columns:
                    missing.append(col)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        has_risk_percent_col = "risk_percent" in df.columns
        has_rrr_col = "rrr" in df.columns
        has_entry_price_col = "entry_price" in df.columns

        nan_count_risk_percent = int(df["risk_percent"].isna().sum()) if has_risk_percent_col else 0
        nan_count_rrr = int(df["rrr"].isna().sum()) if has_rrr_col else 0

        return _InputColumnsMeta(
            has_risk_percent_col=has_risk_percent_col,
            has_rrr_col=has_rrr_col,
            has_entry_price_col=has_entry_price_col,
            nan_count_risk_percent=nan_count_risk_percent,
            nan_count_rrr=nan_count_rrr,
        )

    def _iter_bars(self, df: pd.DataFrame):
        """
        Iterate over bars, yielding context needed for simulation loop.

        Yields
        ------
        tuple
            (i, row, next_open, current_high, current_low, next_time)
        """
        timestamps = df.index.to_list()
        records = df.to_records()
        i_range = records
        if self._logger.isEnabledFor(logging.DEBUG):
            i_range = tqdm(
                records,
                total=len(df) - 1,
                desc="Running simulation",
                unit="bar",
                ascii=True,
            )

        for i, row in enumerate(i_range):
            if i == len(records) - 1:
                break

            next_record = records[i + 1]
            next_time = timestamps[i + 1]
            next_open = next_record["open"]
            current_open = row["open"]
            current_high = row["high"]
            current_low = row["low"]

            trail_atr = row["trail_atr"] if "trail_atr" in row.dtype.names else None
            yield (
                i,
                row,
                next_open,
                current_open,
                current_high,
                current_low,
                trail_atr,
                next_time,
            )

    def _update_active_positions(
        self,
        *,
        active_positions: list[Position],
        capital: float,
        i: int,
        current_open: float,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
        next_open: float,
        next_time: pd.Timestamp,
        trade_history: list[dict],
        mark_open: float | None = None,
        mark_high: float | None = None,
        mark_low: float | None = None,
        evaluate_ttl: bool = True,
        evaluate_unsafe: bool = True,
    ) -> tuple[float, list[Position]]:
        """
        Update active positions for current bar, applying TP/SL/TTL logic.

        Returns
        -------
        capital : float
            Updated capital after closing positions, if any.
        remaining_positions : list[Position]
            Positions that remain open after this bar.
        """
        remaining_positions: list[Position] = []
        positions_to_process = sorted(
            active_positions,
            key=_adverse_exit_priority,
        )

        for position_index, pos in enumerate(positions_to_process):
            exit_reason, exit_price = self._resolve_bar_exit(
                pos=pos,
                current_open=current_open,
                current_high=current_high,
                current_low=current_low,
                trail_atr=trail_atr,
                mark_open=mark_open,
                mark_high=mark_high,
                mark_low=mark_low,
            )

            # TTL
            if evaluate_ttl and not exit_reason and self._position_ttl_expired(
                pos=pos,
                i=i,
                next_time=next_time,
            ):
                exit_price = next_open
                exit_reason = ExitReason.TTL_EXPIRED

            # If exit required
            if exit_reason:
                if exit_price is None:
                    raise RuntimeError("exit reason resolved without an exit price")
                capital = self._record_position_exit(
                    pos=pos,
                    exit_reason=exit_reason,
                    exit_price=exit_price,
                    capital=capital,
                    i=i,
                    next_time=next_time,
                    trade_history=trade_history,
                )
                self._refresh_aggregate_liquidation(
                    [
                        *remaining_positions,
                        *positions_to_process[position_index + 1 :],
                    ]
                )
            else:
                remaining_positions.append(pos)

        self._refresh_aggregate_liquidation(remaining_positions)
        while evaluate_unsafe:
            unsafe = next(
                (
                    position
                    for position in sorted(
                        remaining_positions,
                        key=_adverse_exit_priority,
                    )
                    if not _liquidation_buffer_is_safe(position)
                ),
                None,
            )
            if unsafe is None:
                break
            remaining_positions.remove(unsafe)
            capital = self._record_position_exit(
                pos=unsafe,
                exit_reason=ExitReason.UNSAFE_LIQUIDATION_BUFFER,
                exit_price=next_open,
                capital=capital,
                i=i,
                next_time=next_time,
                trade_history=trade_history,
            )
            self._refresh_aggregate_liquidation(remaining_positions)

        return capital, remaining_positions

    def _apply_h1_boundary_exits(
        self,
        *,
        active_positions: list[Position],
        capital: float,
        i: int,
        next_open: float,
        next_time: pd.Timestamp,
        trade_history: list[dict[str, Any]],
    ) -> tuple[float, list[Position]]:
        """Apply TTL and aggregate-buffer fail-safe only at an H1 boundary."""
        remaining: list[Position] = []
        for pos in sorted(active_positions, key=_adverse_exit_priority):
            if self._position_ttl_expired(pos=pos, i=i, next_time=next_time):
                capital = self._record_position_exit(
                    pos=pos,
                    exit_reason=ExitReason.TTL_EXPIRED,
                    exit_price=next_open,
                    capital=capital,
                    i=i,
                    next_time=next_time,
                    trade_history=trade_history,
                )
            else:
                remaining.append(pos)

        self._refresh_aggregate_liquidation(remaining)
        while True:
            unsafe = next(
                (
                    pos
                    for pos in sorted(remaining, key=_adverse_exit_priority)
                    if not _liquidation_buffer_is_safe(pos)
                ),
                None,
            )
            if unsafe is None:
                break
            remaining.remove(unsafe)
            capital = self._record_position_exit(
                pos=unsafe,
                exit_reason=ExitReason.UNSAFE_LIQUIDATION_BUFFER,
                exit_price=next_open,
                capital=capital,
                i=i,
                next_time=next_time,
                trade_history=trade_history,
            )
            self._refresh_aggregate_liquidation(remaining)
        return capital, remaining

    @staticmethod
    def _position_ttl_expired(*, pos: Position, i: int, next_time: pd.Timestamp) -> bool:
        if pos.position_ttl_minutes > 0:
            expires_at = pos.entry_time + pd.Timedelta(minutes=pos.position_ttl_minutes)
            return next_time >= expires_at
        return pos.position_ttl_bars > 0 and (i + 1) - pos.bar_opened >= pos.position_ttl_bars

    def _record_position_exit(
        self,
        *,
        pos: Position,
        exit_reason: ExitReason,
        exit_price: float,
        capital: float,
        i: int,
        next_time: pd.Timestamp,
        trade_history: list[dict[str, Any]],
    ) -> float:
        """Apply one exit cash flow and append its deterministic audit row."""
        exit_value = pos.size * exit_price
        aggregate_entry_price = pos.aggregate_entry_price or pos.entry_price
        entry_value = pos.size * aggregate_entry_price
        constituent_entry_value = pos.size * pos.entry_price
        exit_ctx = ExitContext(exit_reason=exit_reason.value)
        fee_exit = self._fee_model.calculate_exit_fee(
            exit_value,
            is_maker=False,
            ctx=exit_ctx,
        )
        fees = pos.fee_entry + fee_exit
        if pos.is_long:
            pnl_abs = exit_value - entry_value - fees
            constituent_pnl_abs = exit_value - constituent_entry_value - fees
            capital_delta = exit_value - entry_value - fee_exit
        else:
            pnl_abs = entry_value - exit_value - fees
            constituent_pnl_abs = constituent_entry_value - exit_value - fees
            capital_delta = entry_value - exit_value - fee_exit
        pnl_rel = pnl_abs / entry_value if entry_value != 0 else 0.0
        constituent_pnl_rel = (
            constituent_pnl_abs / constituent_entry_value if constituent_entry_value != 0 else 0.0
        )
        new_capital = capital + capital_delta
        trade_history.append(
            {
                "execution_sequence": len(trade_history),
                "signal_time": pos.signal_time,
                "entry_time": pos.entry_time,
                "exit_time": next_time,
                "entry_price": pos.entry_price,
                "aggregate_entry_price": aggregate_entry_price,
                "risk_base_capital": pos.risk_base_capital,
                "exit_price": exit_price,
                "size": pos.size,
                "pnl_abs": pnl_abs,
                "pnl_rel": pnl_rel,
                "constituent_pnl_abs": constituent_pnl_abs,
                "constituent_pnl_rel": constituent_pnl_rel,
                "fee_entry": pos.fee_entry,
                "fee_exit": fee_exit,
                "tp_price": pos.tp_price,
                "sl_price": pos.sl_price,
                "trail_activation_rrr": pos.trail_activation_rrr,
                "trail_distance_atr": pos.trail_distance_atr,
                "trail_activation_price": pos.trail_activation_price,
                "trail_callback_spread": pos.trail_callback_spread,
                "trail_stop_price": pos.trail_stop_price,
                "trail_active": pos.trail_active,
                "exit_reason": exit_reason.value,
                "capital_before": pos.capital_before,
                "capital_after": new_capital,
                "holding_bars": (i + 1) - pos.bar_opened,
                "position_ttl_bars": pos.position_ttl_bars,
                "position_ttl_minutes": pos.position_ttl_minutes,
                "position_group": pos.position_group,
                "leverage": pos.leverage,
                "locked_margin": pos.locked_margin,
                "available_balance_before": pos.available_balance_before,
                "open_positions_before": pos.open_positions_before,
                "total_locked_margin_before": pos.total_locked_margin_before,
                "total_locked_margin_after_entry": pos.total_locked_margin_after_entry,
                "is_long": pos.is_long,
                "liquidation_price": pos.liquidation_price,
                "maintenance_margin_rate": pos.maintenance_margin_rate,
                "liquidation_fee_rate": pos.liquidation_fee_rate,
                "liquidation_buffer_pct": pos.liquidation_buffer_pct,
                "maintenance_margin_tier_schedule": pos.maintenance_margin_tier_schedule,
                "entry_bar_index": pos.bar_opened,
                "exit_bar_index": i,
                **pos.metadata,
            }
        )
        return new_capital

    def _apply_trade_profit_capital_sweep(
        self,
        *,
        closed_trades: list[dict[str, Any]],
        capital_before_exits: float,
        banked_profit: float,
    ) -> tuple[float, float]:
        capital_without_sweeps = capital_before_exits
        trading_capital = capital_before_exits

        for trade in closed_trades:
            capital_after_exit_without_sweeps = float(trade["capital_after"])
            capital_delta = capital_after_exit_without_sweeps - capital_without_sweeps
            capital_without_sweeps = capital_after_exit_without_sweeps
            trading_capital += capital_delta
            trade["capital_after"] = trading_capital

            sweep_amount = 0.0
            sweep_month: str | object = pd.NA
            if float(trade["pnl_abs"]) > 0 and trading_capital > self.initial_capital:
                sweep_amount = trading_capital - self.initial_capital
                banked_profit += sweep_amount
                trading_capital = self.initial_capital
                sweep_month = pd.Timestamp(trade["exit_time"]).strftime("%Y-%m")

            trade["capital_sweep_amount"] = sweep_amount
            trade["capital_sweep_month"] = sweep_month
            trade["banked_profit_after"] = banked_profit
            trade["trading_capital_after_sweep"] = trading_capital

        return trading_capital, banked_profit

    @staticmethod
    def _refresh_aggregate_liquidation(positions: list[Position]) -> None:
        """Refresh exchange-side margin and liquidation without changing its average entry."""
        for is_long in (True, False):
            side_positions = [position for position in positions if position.is_long is is_long]
            if not side_positions:
                continue
            aggregate_entry_price = (
                side_positions[0].aggregate_entry_price or side_positions[0].entry_price
            )
            if any(
                abs(
                    (position.aggregate_entry_price or position.entry_price) - aggregate_entry_price
                )
                > 1e-9
                for position in side_positions
            ):
                raise RuntimeError("same-side positions disagree on OKX aggregate entry price")
            aggregate_size = sum(position.size for position in side_positions)
            maintenance_margin_rate = maintenance_margin_rate_for_size(
                position_size=aggregate_size,
                default_rate=side_positions[0].maintenance_margin_rate,
                tier_schedule=side_positions[0].maintenance_margin_tier_schedule,
            )
            liquidation = aggregate_linear_liquidation_price(
                entries=[(aggregate_entry_price, aggregate_size)],
                is_long=is_long,
                leverage=side_positions[0].leverage,
                maintenance_margin_rate=maintenance_margin_rate,
                liquidation_fee_rate=side_positions[0].liquidation_fee_rate,
                maintenance_margin_tier_schedule=side_positions[0].maintenance_margin_tier_schedule,
            )
            if liquidation is not None:
                for position in side_positions:
                    position.aggregate_entry_price = aggregate_entry_price
                    position.maintenance_margin_rate = maintenance_margin_rate
                    position.locked_margin = (
                        position.size * aggregate_entry_price / side_positions[0].leverage
                    )
                    position.liquidation_price = liquidation

    def _resolve_bar_exit(
        self,
        *,
        pos: Position,
        current_open: float | None = None,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
        mark_open: float | None = None,
        mark_high: float | None = None,
        mark_low: float | None = None,
    ) -> tuple[ExitReason | None, float | None]:
        """
        Resolve TP/SL exit for a single position within the current bar.

        The method inspects the current bar's high/low and determines whether
        TP and/or SL have been touched. If both are touched within the same
        bar, the outcome is resolved according to the configured
        ``bar_exit_policy``.

        Parameters
        ----------
        pos : Position
            Open position to evaluate.
        current_high : float
            Current bar high.
        current_low : float
            Current bar low.

        Returns
        -------
        exit_reason : ExitReason | None
            Exit reason if position should be closed (take profit or
            stop loss), otherwise None. The corresponding string value
            (``\"take_profit\"`` or ``\"stop_loss\"``) is exposed in
            the public trade history.
        exit_price : float | None
            Price at which the position is considered closed, or None if
            no TP/SL exit occurs in this bar.
        """
        separate_mark_price = (
            mark_high is not None and mark_low is not None and mark_open is not None
        )
        liquidation_high = current_high if mark_high is None else mark_high
        liquidation_low = current_low if mark_low is None else mark_low
        liquidation_open = current_open if mark_open is None else mark_open
        liquidation_hit = (
            liquidation_low <= pos.liquidation_price
            if pos.is_long
            else liquidation_high >= pos.liquidation_price
        )
        if separate_mark_price and liquidation_hit and self.bar_exit_policy == "worst_case":
            return (
                ExitReason.LIQUIDATION,
                _adverse_trigger_fill(
                    trigger=pos.liquidation_price,
                    bar_open=liquidation_open,
                    is_long=pos.is_long,
                ),
            )

        if pos.trail_activation_rrr > 0:
            trailing_reason, trailing_price = self._resolve_trailing_bar_exit(
                pos=pos,
                current_open=current_open,
                current_high=current_high,
                current_low=current_low,
                trail_atr=trail_atr,
            )
            if trailing_reason is not None:
                return trailing_reason, trailing_price
            if liquidation_hit:
                return (
                    ExitReason.LIQUIDATION,
                    _adverse_trigger_fill(
                        trigger=pos.liquidation_price,
                        bar_open=liquidation_open,
                        is_long=pos.is_long,
                    ),
                )
            return None, None

        if pos.is_long:
            tp_hit = current_high >= pos.tp_price
            sl_hit = current_low <= pos.sl_price
        else:
            tp_hit = current_low <= pos.tp_price
            sl_hit = current_high >= pos.sl_price

        if liquidation_hit and not sl_hit:
            return (
                ExitReason.LIQUIDATION,
                _adverse_trigger_fill(
                    trigger=pos.liquidation_price,
                    bar_open=liquidation_open,
                    is_long=pos.is_long,
                ),
            )

        if not tp_hit and not sl_hit:
            return None, None

        if tp_hit and not sl_hit:
            return ExitReason.TAKE_PROFIT, pos.tp_price

        if sl_hit and not tp_hit:
            return (
                ExitReason.STOP_LOSS,
                _adverse_trigger_fill(
                    trigger=pos.sl_price,
                    bar_open=current_open,
                    is_long=pos.is_long,
                ),
            )

        # Both TP and SL are hit within the same bar:
        # resolve according to bar_exit_policy.
        if self.bar_exit_policy == "best_case":
            return ExitReason.TAKE_PROFIT, pos.tp_price

        if self.bar_exit_policy == "worst_case":
            return (
                ExitReason.STOP_LOSS,
                _adverse_trigger_fill(
                    trigger=pos.sl_price,
                    bar_open=current_open,
                    is_long=pos.is_long,
                ),
            )

        # This should be unreachable due to __init__ validation, but kept
        # defensively to avoid silent inconsistencies.
        raise RuntimeError(f"Unexpected bar_exit_policy {self.bar_exit_policy!r} at runtime.")

    def _resolve_trailing_bar_exit(
        self,
        *,
        pos: Position,
        current_open: float | None,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
    ) -> tuple[ExitReason | None, float | None]:
        del trail_atr  # Native OKX callback spread is fixed at entry.
        activation_price = pos.trail_activation_price
        callback_spread = pos.trail_callback_spread
        if activation_price is None or callback_spread is None or callback_spread <= 0:
            raise RuntimeError("trailing position has no fixed OKX activation/callback geometry")
        if pos.is_long:
            original_sl_hit = current_low <= pos.sl_price
            activation_hit = current_high >= activation_price
            if not pos.trail_active:
                if original_sl_hit and (not activation_hit or self.bar_exit_policy == "worst_case"):
                    return (
                        ExitReason.STOP_LOSS,
                        _adverse_trigger_fill(
                            trigger=pos.sl_price,
                            bar_open=current_open,
                            is_long=True,
                        ),
                    )
                if not activation_hit:
                    tp_hit = pos.tp_price < activation_price and current_high >= pos.tp_price
                    if tp_hit:
                        return ExitReason.TAKE_PROFIT, pos.tp_price
                    if original_sl_hit:
                        return (
                            ExitReason.STOP_LOSS,
                            _adverse_trigger_fill(
                                trigger=pos.sl_price,
                                bar_open=current_open,
                                is_long=True,
                            ),
                        )
                    return None, None
                pos.trail_active = True
                pos.best_favorable_price = max(pos.entry_price, current_high)
                proposed_stop = pos.best_favorable_price - callback_spread
                pos.trail_stop_price = max(pos.sl_price, proposed_stop)
                if self.bar_exit_policy == "worst_case":
                    return None, None
            else:
                previous_stop = pos.trail_stop_price or max(
                    pos.sl_price,
                    (pos.best_favorable_price or pos.entry_price) - callback_spread,
                )
                if self.bar_exit_policy == "worst_case" and current_low <= previous_stop:
                    return (
                        ExitReason.TRAILING_STOP,
                        _adverse_trigger_fill(
                            trigger=previous_stop,
                            bar_open=current_open,
                            is_long=True,
                        ),
                    )
                pos.best_favorable_price = max(
                    pos.best_favorable_price or pos.entry_price, current_high
                )

            proposed_stop = pos.best_favorable_price - callback_spread
            pos.trail_stop_price = max(pos.sl_price, proposed_stop)
            if current_low <= pos.trail_stop_price:
                return (
                    ExitReason.TRAILING_STOP,
                    _adverse_trigger_fill(
                        trigger=pos.trail_stop_price,
                        bar_open=current_open,
                        is_long=True,
                    ),
                )
            return None, None

        original_sl_hit = current_high >= pos.sl_price
        activation_hit = current_low <= activation_price
        if not pos.trail_active:
            if original_sl_hit and (not activation_hit or self.bar_exit_policy == "worst_case"):
                return (
                    ExitReason.STOP_LOSS,
                    _adverse_trigger_fill(
                        trigger=pos.sl_price,
                        bar_open=current_open,
                        is_long=False,
                    ),
                )
            if not activation_hit:
                tp_hit = pos.tp_price > activation_price and current_low <= pos.tp_price
                if tp_hit:
                    return ExitReason.TAKE_PROFIT, pos.tp_price
                if original_sl_hit:
                    return (
                        ExitReason.STOP_LOSS,
                        _adverse_trigger_fill(
                            trigger=pos.sl_price,
                            bar_open=current_open,
                            is_long=False,
                        ),
                    )
                return None, None
            pos.trail_active = True
            pos.best_favorable_price = min(pos.entry_price, current_low)
            proposed_stop = pos.best_favorable_price + callback_spread
            pos.trail_stop_price = min(pos.sl_price, proposed_stop)
            if self.bar_exit_policy == "worst_case":
                return None, None
        else:
            previous_stop = pos.trail_stop_price or min(
                pos.sl_price,
                (pos.best_favorable_price or pos.entry_price) + callback_spread,
            )
            if self.bar_exit_policy == "worst_case" and current_high >= previous_stop:
                return (
                    ExitReason.TRAILING_STOP,
                    _adverse_trigger_fill(
                        trigger=previous_stop,
                        bar_open=current_open,
                        is_long=False,
                    ),
                )
            pos.best_favorable_price = min(pos.best_favorable_price or pos.entry_price, current_low)

        proposed_stop = pos.best_favorable_price + callback_spread
        pos.trail_stop_price = min(pos.sl_price, proposed_stop)
        if current_high >= pos.trail_stop_price:
            return (
                ExitReason.TRAILING_STOP,
                _adverse_trigger_fill(
                    trigger=pos.trail_stop_price,
                    bar_open=current_open,
                    is_long=False,
                ),
            )
        return None, None

    def _resolve_fixed_exit_before_trailing_atr(
        self,
        pos: Position,
        current_high: float,
        current_low: float,
    ) -> tuple[ExitReason | None, float | None]:
        if pos.is_long:
            tp_hit = current_high >= pos.tp_price
            sl_hit = current_low <= pos.sl_price
            if tp_hit and sl_hit:
                if self.bar_exit_policy == "best_case":
                    return ExitReason.TAKE_PROFIT, pos.tp_price
                return ExitReason.STOP_LOSS, pos.sl_price
            if tp_hit:
                return ExitReason.TAKE_PROFIT, pos.tp_price
            if sl_hit:
                return ExitReason.STOP_LOSS, pos.sl_price
        else:
            tp_hit = current_low <= pos.tp_price
            sl_hit = current_high >= pos.sl_price
            if tp_hit and sl_hit:
                if self.bar_exit_policy == "best_case":
                    return ExitReason.TAKE_PROFIT, pos.tp_price
                return ExitReason.STOP_LOSS, pos.sl_price
            if tp_hit:
                return ExitReason.TAKE_PROFIT, pos.tp_price
            if sl_hit:
                return ExitReason.STOP_LOSS, pos.sl_price
        return None, None

    def _prepare_entry_context(
        self,
        *,
        df: pd.DataFrame,
        i: int,
        row,
        columns_meta: _InputColumnsMeta,
        event: dict[str, Any] | None = None,
    ) -> _EntryContextDict:
        """
        Prepare and validate per-bar context required for potential entry.

        Returns
        -------
        dict
            Dictionary with keys: ``signal``, ``sl_price``, ``risk_percent``,
            ``rrr``, ``entry_price``.
        """
        signal = self._event_or_row_value(row, event, "signal", default=0)
        sl_price = self._event_or_row_value(row, event, "sl_price", default=float("nan"))

        risk_percent = self.risk_percent
        if event is not None and "risk_percent" in event:
            risk_percent = event["risk_percent"]
        elif columns_meta.has_risk_percent_col:
            risk_percent = row["risk_percent"]
            if columns_meta.nan_count_risk_percent > 0 and pd.isna(risk_percent):
                index_value = df.index[i]
                msg = (
                    f"NaN in column 'risk_percent' at index "
                    f"{index_value!r} (total NaN count: {columns_meta.nan_count_risk_percent})"
                )
                self._logger.error(msg)
                raise ValueError(msg)

        rrr = self.rrr
        if event is not None and "rrr" in event:
            rrr = event["rrr"]
        elif columns_meta.has_rrr_col:
            rrr = row["rrr"]
            if columns_meta.nan_count_rrr > 0 and pd.isna(rrr):
                index_value = df.index[i]
                msg = (
                    f"NaN in column 'rrr' at index "
                    f"{index_value!r} (total NaN count: {columns_meta.nan_count_rrr})"
                )
                self._logger.error(msg)
                raise ValueError(msg)

        entry_price: float | None = None
        if event is not None and "entry_price" in event:
            raw_entry_price = event["entry_price"]
        elif columns_meta.has_entry_price_col:
            raw_entry_price = row["entry_price"]
        else:
            raw_entry_price = None
        if raw_entry_price is not None and not pd.isna(raw_entry_price):
            current_low = row["low"]
            current_high = row["high"]
            if signal in (1, -1) and not (current_low <= raw_entry_price <= current_high):
                index_value = df.index[i]
                msg = (
                    "Invalid entry_price: value must lie within current bar "
                    f"range [low, high]. Got entry_price={raw_entry_price!r}, "
                    f"low={current_low!r}, high={current_high!r} at index "
                    f"{index_value!r}."
                )
                self._logger.error(msg)
                raise ValueError(msg)
            entry_price = float(raw_entry_price)

        return {
            "signal": int(signal),
            "sl_price": float(sl_price),
            "risk_percent": risk_percent,
            "rrr": rrr,
            "entry_price": entry_price,
            "position_ttl_bars": int(
                self._event_or_row_value(
                    row,
                    event,
                    "position_ttl_bars",
                    default=self.position_ttl_bars,
                )
            ),
            "position_ttl_minutes": int(
                self._event_or_row_value(
                    row,
                    event,
                    "position_ttl_minutes",
                    default=self.position_ttl_minutes,
                )
            ),
            "trail_activation_rrr": float(
                self._event_or_row_value(
                    row,
                    event,
                    "trail_activation_rrr",
                    default=self.trail_activation_rrr,
                )
            ),
            "trail_distance_atr": float(
                self._event_or_row_value(
                    row,
                    event,
                    "trail_distance_atr",
                    default=self.trail_distance_atr,
                )
            ),
            "exit_geometry": str(
                self._event_or_row_value(
                    row,
                    event,
                    "exit_geometry",
                    default=self._exit_geometry_config.mode,
                )
            ),
            "tp_move_pct": (
                None
                if pd.isna(
                    self._event_or_row_value(
                        row,
                        event,
                        "tp_move_pct",
                        default=self._exit_geometry_config.tp_move_pct,
                    )
                )
                else float(
                    self._event_or_row_value(
                        row,
                        event,
                        "tp_move_pct",
                        default=self._exit_geometry_config.tp_move_pct,
                    )
                )
            ),
            "structural_sl_mode": str(
                self._event_or_row_value(
                    row,
                    event,
                    "structural_sl_mode",
                    default=self._exit_geometry_config.structural_sl_mode,
                )
            ),
            "min_tp_move_pct": float(
                self._event_or_row_value(
                    row,
                    event,
                    "min_tp_move_pct",
                    default=self._exit_geometry_config.min_tp_move_pct,
                )
            ),
            "position_group": str(
                self._event_or_row_value(row, event, "position_group", default="")
            ),
            "drain_on_group_change": bool(
                self._event_or_row_value(
                    row,
                    event,
                    "drain_on_group_change",
                    default=False,
                )
            ),
            "tp_policy_enabled": bool(
                self._event_or_row_value(row, event, "tp_policy_enabled", default=False)
            ),
            "tp_policy_min_original_rrr": float(
                self._event_or_row_value(row, event, "tp_policy_min_original_rrr", default=4.0)
            ),
            "tp_policy_min_distance_pct": _optional_float_value(
                self._event_or_row_value(row, event, "tp_policy_min_distance_pct", default=0.07)
            ),
            "tp_policy_min_last_touch_bars": _optional_int_value(
                self._event_or_row_value(row, event, "tp_policy_min_last_touch_bars", default=720)
            ),
            "tp_policy_adjusted_rrr": float(
                self._event_or_row_value(row, event, "tp_policy_adjusted_rrr", default=3.0)
            ),
            "tp_last_touch_bars": _optional_int_value(
                self._event_or_row_value(row, event, "tp_last_touch_bars", default=None)
            ),
            "metadata": _trade_metadata_from_row(row) | _trade_metadata_from_event(event),
        }

    def _entry_contexts_for_bar(
        self,
        *,
        df: pd.DataFrame,
        i: int,
        row,
        columns_meta: _InputColumnsMeta,
    ) -> list[_EntryContextDict]:
        if "signal_events" not in row.dtype.names:
            has_signal_events = False
        else:
            raw_events = row["signal_events"]
            has_signal_events = raw_events is not None and not (
                isinstance(raw_events, float) and pd.isna(raw_events)
            )
        if not has_signal_events:
            return [
                self._prepare_entry_context(
                    df=df,
                    i=i,
                    row=row,
                    columns_meta=columns_meta,
                )
            ]

        if not isinstance(raw_events, (list, tuple)):
            raise ValueError("signal_events must be a list/tuple of event dictionaries")

        contexts: list[_EntryContextDict] = []
        for event in raw_events:
            if not isinstance(event, dict):
                raise ValueError("signal_events entries must be dictionaries")
            contexts.append(
                self._prepare_entry_context(
                    df=df,
                    i=i,
                    row=row,
                    columns_meta=columns_meta,
                    event=event,
                )
            )
        return contexts

    @staticmethod
    def _event_or_row_value(row, event: dict[str, Any] | None, key: str, *, default: Any) -> Any:
        if event is not None and key in event:
            return event[key]
        if key in row.dtype.names:
            return row[key]
        return default

    def _try_open_position(
        self,
        *,
        i: int,
        current_time: pd.Timestamp,
        next_time: pd.Timestamp,
        next_open: float,
        capital: float,
        active_positions: list[Position],
        entry_ctx: _EntryContextDict,
        entry_trail_atr: float | None,
    ) -> tuple[float, list[Position]]:
        """
        Try to open a new position based on signal and risk settings.

        Returns
        -------
        tuple[float, list[Position]]
            Capital after any immediate entry fee and updated active positions.
        """
        signal = entry_ctx["signal"]
        sl_price = entry_ctx["sl_price"]
        risk_percent = entry_ctx["risk_percent"]
        original_rrr = float(entry_ctx["rrr"])
        ctx_entry_price = entry_ctx.get("entry_price")
        position_group = entry_ctx["position_group"]

        if (signal != 1 and signal != -1) or (
            len(active_positions) >= self.max_positions and self.max_positions > 0
        ):
            return capital, active_positions
        if entry_ctx["drain_on_group_change"] and active_positions:
            active_groups = {position.position_group for position in active_positions}
            if position_group not in active_groups:
                return capital, active_positions

        if ctx_entry_price is not None:
            entry_price = ctx_entry_price
            entry_time = current_time
            bar_opened = i
        else:
            entry_price = next_open
            entry_time = next_time
            bar_opened = i + 1
        if pd.isna(sl_price):
            self._logger.debug("Missing SL price, skipping signal")
            return capital, active_positions

        tp_decision = adjust_tp_rrr(
            signal=signal,
            entry_price=entry_price,
            sl_price=float(sl_price),
            original_rrr=original_rrr,
            last_touch_bars=entry_ctx["tp_last_touch_bars"],
            policy=TpPolicyConfig(
                enabled=entry_ctx["tp_policy_enabled"],
                min_original_rrr=entry_ctx["tp_policy_min_original_rrr"],
                min_tp_distance_pct=entry_ctx["tp_policy_min_distance_pct"],
                min_last_touch_bars=entry_ctx["tp_policy_min_last_touch_bars"],
                adjusted_rrr=entry_ctx["tp_policy_adjusted_rrr"],
            ),
        )
        rrr = tp_decision.effective_rrr
        metadata = dict(entry_ctx["metadata"])
        metadata.update(
            {
                "original_rrr": tp_decision.original_rrr,
                "effective_rrr": tp_decision.effective_rrr,
                "tp_adjusted": tp_decision.adjusted,
                "tp_adjustment_reason": tp_decision.reason,
                "tp_distance_pct": tp_decision.tp_distance_pct,
                "tp_last_touch_bars": tp_decision.last_touch_bars,
            }
        )
        risk_base_capital = self._risk_base_capital_for_entry(entry_time, capital)

        # Calculate total margin already locked in active positions
        total_locked_margin = sum(pos.locked_margin for pos in active_positions)
        open_positions_before = len(active_positions)

        is_long_signal = signal == 1
        same_side_positions_before = [
            pos for pos in active_positions if pos.is_long is is_long_signal
        ]
        entry_context = EntryContext(
            signal=signal,
            sl_price=sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=risk_base_capital,
            total_locked_margin=total_locked_margin,
            open_positions=open_positions_before,
            risk_percent=risk_percent,
            rrr=rrr,
            existing_leverage=(
                same_side_positions_before[0].leverage if same_side_positions_before else None
            ),
            existing_position_size=sum(pos.size for pos in same_side_positions_before),
        )

        risk_model = self._risk_model
        if (
            entry_ctx["exit_geometry"] != self._exit_geometry_config.mode
            or entry_ctx["tp_move_pct"] != self._exit_geometry_config.tp_move_pct
            or entry_ctx["structural_sl_mode"] != self._exit_geometry_config.structural_sl_mode
            or entry_ctx["min_tp_move_pct"] != self._exit_geometry_config.min_tp_move_pct
        ):
            risk_model = BasicRiskModel(
                max_allowed_margin=self.max_allowed_margin,
                max_positions=self.max_positions,
                max_allowed_leverage=self.max_allowed_leverage,
                exit_geometry_config=exit_geometry_config_from_args(
                    exit_geometry=entry_ctx["exit_geometry"],
                    tp_move_pct=entry_ctx["tp_move_pct"],
                    structural_sl_mode=entry_ctx["structural_sl_mode"],
                    min_tp_move_pct=entry_ctx["min_tp_move_pct"],
                ),
                maintenance_margin_rate=self.maintenance_margin_rate,
                liquidation_fee_rate=self.liquidation_fee_rate,
                liquidation_buffer_pct=self.liquidation_buffer_pct,
                maintenance_margin_tier_schedule=self.maintenance_margin_tier_schedule,
            )
        risk_result = risk_model.calculate_position(entry_context)
        if risk_result is None:
            return capital, active_positions
        precision = self._instrument_precision
        position_size = risk_result.size
        sl_price_rounded = risk_result.sl_price
        tp_price_rounded = risk_result.tp_price
        if precision is not None:
            contracts = precision.asset_size_to_contracts(position_size)
            if contracts <= 0:
                return capital, active_positions
            position_size = precision.contracts_to_asset_size(contracts)
            sl_price_rounded = precision.round_price(sl_price_rounded)
            tp_price_rounded = precision.round_price(tp_price_rounded)
            if risk_result.is_long:
                valid_geometry = sl_price_rounded < entry_price < tp_price_rounded
            else:
                valid_geometry = tp_price_rounded < entry_price < sl_price_rounded
            if not valid_geometry:
                return capital, active_positions
        same_side_positions = same_side_positions_before
        aggregate_size = sum(pos.size for pos in same_side_positions) + position_size
        if not leverage_is_within_size_tier(
            position_size=aggregate_size,
            leverage=risk_result.required_leverage,
            configured_max_leverage=self.max_allowed_leverage,
            tier_schedule=risk_result.maintenance_margin_tier_schedule,
        ):
            return capital, active_positions
        aggregate_safe, aggregate_liquidation = aggregate_liquidation_is_beyond_stops(
            entries_and_stops=[
                (
                    pos.aggregate_entry_price or pos.entry_price,
                    pos.size,
                    pos.sl_price,
                )
                for pos in same_side_positions
            ]
            + [(entry_price, position_size, sl_price_rounded)],
            is_long=risk_result.is_long,
            leverage=risk_result.required_leverage,
            maintenance_margin_rate=risk_result.maintenance_margin_rate,
            liquidation_fee_rate=risk_result.liquidation_fee_rate,
            buffer_pct=risk_result.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=risk_result.maintenance_margin_tier_schedule,
        )
        if not aggregate_safe or aggregate_liquidation is None:
            return capital, active_positions
        trail_activation_rrr = entry_ctx["trail_activation_rrr"]
        trail_distance_atr = entry_ctx["trail_distance_atr"]
        trail_activation_price: float | None = None
        trail_callback_spread: float | None = None
        if trail_activation_rrr > 0:
            if entry_trail_atr is None or pd.isna(entry_trail_atr) or entry_trail_atr <= 0:
                return capital, active_positions
            geometry = build_native_trailing_geometry(
                entry_price=entry_price,
                stop_price=sl_price_rounded,
                take_profit_price=tp_price_rounded,
                is_long=risk_result.is_long,
                activation_rrr=trail_activation_rrr,
                distance_atr=trail_distance_atr,
                entry_atr=float(entry_trail_atr),
            )
            trail_activation_price = geometry.activation_price
            trail_callback_spread = geometry.callback_spread
            if precision is not None:
                trail_activation_price = precision.round_price(trail_activation_price)
                trail_callback_spread = precision.round_price(trail_callback_spread)
                if trail_callback_spread <= 0:
                    return capital, active_positions

        position_value = position_size * entry_price
        risk_value = position_size * abs(entry_price - sl_price_rounded)
        available_balance = risk_result.available_balance
        locked_margin = position_value / risk_result.required_leverage
        total_locked_margin_after_entry = total_locked_margin + locked_margin

        # Entry fee and exposure checks remain in the engine so that they can
        # combine risk and commission information.
        fee_entry = self._fee_model.calculate_entry_fee(position_value, entry_context)
        net_exposure = position_value - fee_entry

        # Protection: fee should not be larger than risk
        if fee_entry >= risk_value * 2:
            return capital, active_positions

        if net_exposure < self.min_net_exposure * available_balance:
            return capital, active_positions

        if not self._can_open_position(
            position_value,
            risk_result.required_leverage,
            active_positions,
            available_balance,
        ):
            self._logger.debug(
                "Position value: %.2f, Risk value: %.2f, SL distance: %.2f",
                position_value,
                risk_value,
                risk_result.sl_dist,
            )
            return capital, active_positions

        new_position = Position(
            signal_time=current_time,
            entry_time=entry_time,
            entry_price=entry_price,
            risk_base_capital=risk_base_capital,
            size=position_size,
            tp_price=tp_price_rounded,
            sl_price=sl_price_rounded,
            bar_opened=bar_opened,
            fee_entry=fee_entry,
            capital_before=capital,
            leverage=risk_result.required_leverage,
            is_long=risk_result.is_long,
            locked_margin=locked_margin,
            available_balance_before=available_balance,
            open_positions_before=open_positions_before,
            total_locked_margin_before=total_locked_margin,
            total_locked_margin_after_entry=total_locked_margin_after_entry,
            liquidation_price=risk_result.liquidation_price,
            maintenance_margin_rate=risk_result.maintenance_margin_rate,
            liquidation_fee_rate=risk_result.liquidation_fee_rate,
            liquidation_buffer_pct=risk_result.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=risk_result.maintenance_margin_tier_schedule,
            metadata=metadata,
            aggregate_entry_price=entry_price,
            position_ttl_bars=entry_ctx["position_ttl_bars"],
            position_ttl_minutes=entry_ctx["position_ttl_minutes"],
            position_group=position_group,
            trail_activation_rrr=trail_activation_rrr,
            trail_distance_atr=trail_distance_atr,
            trail_activation_price=trail_activation_price,
            trail_callback_spread=trail_callback_spread,
        )
        existing_size = sum(position.size for position in same_side_positions)
        existing_notional = (
            existing_size
            * (same_side_positions[0].aggregate_entry_price or same_side_positions[0].entry_price)
            if same_side_positions
            else 0.0
        )
        aggregate_entry_price = (existing_notional + position_size * entry_price) / (
            existing_size + position_size
        )
        for position in [*same_side_positions, new_position]:
            position.aggregate_entry_price = aggregate_entry_price
        active_positions.append(new_position)
        self._refresh_aggregate_liquidation(active_positions)
        new_position.total_locked_margin_after_entry = sum(
            position.locked_margin for position in active_positions
        )

        return capital - fee_entry, active_positions

    def run(
        self,
        df: pd.DataFrame,
        *,
        intrabar_data: IntrabarExecutionData | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> pd.DataFrame:
        """
        Run trading simulation based on signal data.

        Parameters:
        ----------
        df : pd.DataFrame
            DataFrame with OHLCV and 'signal' column.
            Required columns:
                - 'open', 'high', 'low', 'close', 'signal', 'sl_price'
            Optional per-bar columns:
                - 'risk_percent': fraction of current capital put at risk
                  for this bar (overrides self.risk_percent).
                - 'rrr': reward/risk ratio for this bar (overrides self.rrr).
                - 'entry_price': optional custom entry price for the bar with
                  a non-zero signal. When provided and non-NaN, it must lie
                  within the current bar's range ``[low, high]`` and is used
                  as the execution price with ``entry_time`` equal to the
                  current bar timestamp. If absent or NaN, the simulator
                  falls back to entering at the next bar's open price with
                  ``entry_time`` equal to the next bar timestamp.

            If optional columns are provided and used, their values must be
            numeric and must not contain NaN. NaN in these columns will lead
            to an explicit error during simulation.

            Index must be DatetimeIndex (sorted in ascending time order).
            Index name is ignored; times are taken from positional index
            values, so ``df.index.name`` may be None.
            signal: 1 = long entry, -1 = short entry, 0 = no signal.
            sl_price: stop loss price for the signal.
            Intra-bar TP/SL resolution is controlled by ``bar_exit_policy``:
            if both TP and SL are within the same bar range, the simulator
            either prefers the more favorable or less favorable outcome for
            the trader depending on the configured policy.

        Returns:
        -----------
        pd.DataFrame
            Trades table with following columns:
            - entry_time: entry time (at next bar's open)
            - signal_time: timestamp of the bar that emitted the entry signal
            - exit_time: exit time
            - entry_price: entry price
            - exit_price: exit price
            - size: position size in asset units
            - pnl_abs: profit/loss in dollars
            - pnl_rel: relative profit (pnl_abs / invested)
            - fee_entry: entry commission
            - fee_exit: exit commission
            - tp_price: Take Profit price
            - sl_price: Stop Loss price
            - exit_reason: exit reason string; currently one of
              ``"take_profit"``, ``"stop_loss"`` or ``"ttl_expired"`` as
              defined by :class:`ExitReason`.
            - capital_before: capital before entry
            - capital_after: capital after exit
            - holding_bars: how many bars position was held
            - leverage: leverage used
            - locked_margin: margin locked by this isolated-futures-style
              position sizing decision
            - available_balance_before: realized capital minus already locked
              margin immediately before opening this position
            - open_positions_before: active position count immediately before
              opening this position
            - total_locked_margin_before: total margin locked by previously
              active positions immediately before opening this position
            - total_locked_margin_after_entry: total locked margin after this
              position is added
            - is_long: True for long, False for short
            - entry_bar_index: index of the bar where position was opened
            - exit_bar_index: index of the bar where position was closed
            - any strategy metadata columns from the signal row, for example
              confidence, score, regime, rationale, and per-engine strengths
        """
        trailing_requested = (
            self.trail_activation_rrr > 0
            or (
                "trail_activation_rrr" in df.columns
                and pd.to_numeric(df["trail_activation_rrr"], errors="coerce").fillna(0).gt(0).any()
            )
            or (_signal_events_request_trailing(df))
        )
        if trailing_requested and "trail_atr" not in df.columns:
            df = with_closed_atr14(df)

        try:
            columns_meta = self._validate_input_df(df)
        except _NotEnoughBarsError:
            return pd.DataFrame()

        last_1m: pd.DataFrame | None = None
        mark_1m: pd.DataFrame | None = None
        if self.intrabar_execution_timeframe == "1m":
            if intrabar_data is None:
                raise ValueError(
                    "intrabar_execution_timeframe='1m' requires last and mark minute data"
                )
            last_1m, mark_1m = _validate_minute_execution_data(df, intrabar_data)

        capital = self.initial_capital
        active_positions: list[Position] = []
        trade_history: list[dict] = []

        # Daily RRR tracking state
        current_day = None
        profit_num = 0
        loss_num = 0
        daily_trading_blocked = False
        current_sweep_month: tuple[int, int] | None = None
        banked_profit = 0.0
        pending_capital_sweep_amount = 0.0
        pending_capital_sweep_month: str | None = None

        for (
            i,
            row,
            next_open,
            current_open,
            current_high,
            current_low,
            trail_atr,
            next_time,
        ) in self._iter_bars(df):
            if progress_callback is not None:
                progress_callback(i + 1)
            if capital <= 1:
                self._logger.warning("Capital below 1, exiting")
                break

            # Detect new trading day by next bar's timestamp (used for entries/exits)
            bar_day = next_time.normalize()
            if current_day is None or bar_day != current_day:
                current_day = bar_day
                profit_num = 0
                loss_num = 0
                daily_trading_blocked = False

            current_time = pd.Timestamp(df.index[i])

            # === 1. Check exit conditions (TP/SL/TTL) for all active positions ===
            prev_trades_len = len(trade_history)
            if last_1m is not None and mark_1m is not None:
                if active_positions:
                    interval_last = last_1m.loc[
                        (last_1m.index >= current_time) & (last_1m.index < next_time)
                    ]
                    interval_mark = mark_1m.loc[
                        (mark_1m.index >= current_time) & (mark_1m.index < next_time)
                    ]
                    for minute_offset in range(len(interval_last)):
                        if not active_positions:
                            break
                        capital_before_exits = capital
                        minute_prev_trades_len = len(trade_history)
                        last_row = interval_last.iloc[minute_offset]
                        mark_row = interval_mark.iloc[minute_offset]
                        minute_time = pd.Timestamp(interval_last.index[minute_offset])
                        minute_next_open = (
                            float(interval_last.iloc[minute_offset + 1]["open"])
                            if minute_offset < len(interval_last) - 1
                            else float(next_open)
                        )
                        capital, active_positions = self._update_active_positions(
                            active_positions=active_positions,
                            capital=capital,
                            i=i,
                            current_open=float(last_row["open"]),
                            current_high=float(last_row["high"]),
                            current_low=float(last_row["low"]),
                            trail_atr=trail_atr,
                            next_open=minute_next_open,
                            next_time=minute_time,
                            trade_history=trade_history,
                            mark_open=float(mark_row["open"]),
                            mark_high=float(mark_row["high"]),
                            mark_low=float(mark_row["low"]),
                            evaluate_ttl=False,
                            evaluate_unsafe=False,
                        )
                        if self.capital_sweep == "trade_profit":
                            capital, banked_profit = self._apply_trade_profit_capital_sweep(
                                closed_trades=trade_history[minute_prev_trades_len:],
                                capital_before_exits=capital_before_exits,
                                banked_profit=banked_profit,
                            )
                    capital_before_exits = capital
                    boundary_prev_trades_len = len(trade_history)
                    capital, active_positions = self._apply_h1_boundary_exits(
                        active_positions=active_positions,
                        capital=capital,
                        i=i,
                        next_open=float(next_open),
                        next_time=pd.Timestamp(next_time),
                        trade_history=trade_history,
                    )
                    if self.capital_sweep == "trade_profit":
                        capital, banked_profit = self._apply_trade_profit_capital_sweep(
                            closed_trades=trade_history[boundary_prev_trades_len:],
                            capital_before_exits=capital_before_exits,
                            banked_profit=banked_profit,
                        )
            else:
                capital_before_exits = capital
                capital, active_positions = self._update_active_positions(
                    active_positions=active_positions,
                    capital=capital,
                    i=i,
                    current_open=current_open,
                    current_high=current_high,
                    current_low=current_low,
                    trail_atr=trail_atr,
                    next_open=next_open,
                    next_time=next_time,
                    trade_history=trade_history,
                )
                if self.capital_sweep == "trade_profit":
                    capital, banked_profit = self._apply_trade_profit_capital_sweep(
                        closed_trades=trade_history[prev_trades_len:],
                        capital_before_exits=capital_before_exits,
                        banked_profit=banked_profit,
                    )
            newly_closed_trades = trade_history[prev_trades_len:]

            bar_month = (next_time.year, next_time.month)
            capital_sweep_amount = 0.0
            capital_sweep_month: str | None = None
            if current_sweep_month is None:
                current_sweep_month = bar_month
            elif bar_month != current_sweep_month:
                capital_sweep_month = f"{current_sweep_month[0]:04d}-{current_sweep_month[1]:02d}"
                current_sweep_month = bar_month
                if self.capital_sweep == "monthly_profit" and capital > self.initial_capital:
                    capital_sweep_amount = capital - self.initial_capital
                    banked_profit += capital_sweep_amount
                    capital = self.initial_capital
                    pending_capital_sweep_amount += capital_sweep_amount
                    pending_capital_sweep_month = capital_sweep_month

            for trade in newly_closed_trades:
                trade.setdefault("capital_sweep_amount", 0.0)
                trade.setdefault("capital_sweep_month", pd.NA)
                trade.setdefault("banked_profit_after", banked_profit)
                trade.setdefault("trading_capital_after_sweep", capital)
            if (
                self.capital_sweep != "trade_profit"
                and newly_closed_trades
                and pending_capital_sweep_amount
            ):
                newly_closed_trades[-1]["capital_sweep_amount"] = pending_capital_sweep_amount
                newly_closed_trades[-1]["capital_sweep_month"] = pending_capital_sweep_month
                pending_capital_sweep_amount = 0.0
                pending_capital_sweep_month = None

            # === 1a. Update daily RRR counters based on newly closed trades ===
            if self.max_daily_profit or self.max_daily_loss:
                for trade in newly_closed_trades:
                    exit_time = trade["exit_time"]
                    trade_day = exit_time.normalize()
                    # If a trade closed for a different day (shouldn't normally happen),
                    # update counters against that trade's day semantics.
                    is_profitable = trade["pnl_abs"] > 0
                    is_losing = trade["pnl_abs"] < 0
                    if trade_day == current_day:
                        if is_profitable:
                            profit_num += 1
                        elif is_losing:
                            loss_num += 1

                if self.max_daily_profit or self.max_daily_loss:
                    daily_rrr = profit_num * self.rrr - loss_num

                    hit_profit_limit = (
                        self.max_daily_profit is not None
                        and self.max_daily_profit > 0
                        and daily_rrr >= self.max_daily_profit
                    )
                    hit_loss_limit = (
                        self.max_daily_loss is not None
                        and self.max_daily_loss > 0
                        and daily_rrr <= -self.max_daily_loss
                    )

                    if hit_profit_limit or hit_loss_limit:
                        daily_trading_blocked = True

            # === 2. Enter new position based on signal ===
            can_open_in_session = True
            if self.trading_begin is not None or self.trading_end is not None:
                hour = next_time.hour
                if self.trading_begin is not None and hour < self.trading_begin:
                    can_open_in_session = False
                if self.trading_end is not None and hour >= self.trading_end:
                    can_open_in_session = False

            if not daily_trading_blocked and can_open_in_session:
                entry_contexts = self._entry_contexts_for_bar(
                    df=df,
                    i=i,
                    row=row,
                    columns_meta=columns_meta,
                )
                for entry_ctx in entry_contexts:
                    entry_trail_atr = (
                        float(df.iloc[i + 1]["trail_atr"])
                        if "trail_atr" in df.columns and not pd.isna(df.iloc[i + 1]["trail_atr"])
                        else None
                    )
                    capital, active_positions = self._try_open_position(
                        i=i,
                        current_time=current_time,
                        next_time=next_time,
                        next_open=next_open,
                        capital=capital,
                        active_positions=active_positions,
                        entry_ctx=entry_ctx,
                        entry_trail_atr=entry_trail_atr,
                    )

        if active_positions:
            last_bar_index = len(df) - 1
            for pos in active_positions:
                snapshot = self._open_position_snapshot(pos=pos, last_bar_index=last_bar_index)
                snapshot["execution_sequence"] = len(trade_history)
                snapshot["capital_sweep_amount"] = pending_capital_sweep_amount
                snapshot["capital_sweep_month"] = pending_capital_sweep_month
                snapshot["banked_profit_after"] = banked_profit
                snapshot["trading_capital_after_sweep"] = capital
                trade_history.append(snapshot)
                pending_capital_sweep_amount = 0.0
                pending_capital_sweep_month = None

        if trade_history and pending_capital_sweep_amount:
            last_trade = trade_history[-1]
            last_trade["capital_sweep_amount"] = (
                float(last_trade.get("capital_sweep_amount", 0.0)) + pending_capital_sweep_amount
            )
            last_trade["capital_sweep_month"] = pending_capital_sweep_month
            last_trade["banked_profit_after"] = banked_profit
            last_trade["trading_capital_after_sweep"] = capital
            pending_capital_sweep_amount = 0.0
            pending_capital_sweep_month = None

        for trade in trade_history:
            trade.setdefault("capital_sweep_amount", 0.0)
            trade.setdefault("capital_sweep_month", pd.NA)
            trade.setdefault("banked_profit_after", banked_profit)
            trade.setdefault("trading_capital_after_sweep", capital)
            trade["account_capital_at_end"] = capital
            trade["account_capital_at_end_time"] = df.index[-1]
            trade["account_initial_capital"] = self.initial_capital

        return pd.DataFrame(trade_history) if trade_history else pd.DataFrame()

    @staticmethod
    def _open_position_snapshot(*, pos: Position, last_bar_index: int) -> dict[str, Any]:
        """Represent an active entry without realizing PnL at end of data."""
        return {
            "signal_time": pos.signal_time,
            "entry_time": pos.entry_time,
            "exit_time": pd.NaT,
            "entry_price": pos.entry_price,
            "aggregate_entry_price": pos.aggregate_entry_price or pos.entry_price,
            "risk_base_capital": pos.risk_base_capital,
            "exit_price": pd.NA,
            "size": pos.size,
            "pnl_abs": pd.NA,
            "pnl_rel": pd.NA,
            "constituent_pnl_abs": pd.NA,
            "constituent_pnl_rel": pd.NA,
            "fee_entry": pos.fee_entry,
            "fee_exit": pd.NA,
            "tp_price": pos.tp_price,
            "sl_price": pos.sl_price,
            "trail_activation_rrr": pos.trail_activation_rrr,
            "trail_distance_atr": pos.trail_distance_atr,
            "trail_activation_price": pos.trail_activation_price,
            "trail_callback_spread": pos.trail_callback_spread,
            "trail_stop_price": pos.trail_stop_price,
            "trail_active": pos.trail_active,
            "exit_reason": ExitReason.OPEN.value,
            "capital_before": pos.capital_before,
            "capital_after": pd.NA,
            "holding_bars": max(last_bar_index - pos.bar_opened, 0),
            "position_ttl_bars": pos.position_ttl_bars,
            "position_ttl_minutes": pos.position_ttl_minutes,
            "leverage": pos.leverage,
            "locked_margin": pos.locked_margin,
            "available_balance_before": pos.available_balance_before,
            "open_positions_before": pos.open_positions_before,
            "total_locked_margin_before": pos.total_locked_margin_before,
            "total_locked_margin_after_entry": pos.total_locked_margin_after_entry,
            "is_long": pos.is_long,
            "liquidation_price": pos.liquidation_price,
            "maintenance_margin_rate": pos.maintenance_margin_rate,
            "liquidation_fee_rate": pos.liquidation_fee_rate,
            "liquidation_buffer_pct": pos.liquidation_buffer_pct,
            "maintenance_margin_tier_schedule": pos.maintenance_margin_tier_schedule,
            "entry_bar_index": pos.bar_opened,
            "exit_bar_index": pd.NA,
            **pos.metadata,
        }


def _trade_metadata_from_row(row) -> dict[str, Any]:
    """Copy non-execution strategy columns from a signal row into trade output."""
    metadata: dict[str, Any] = {}
    names = getattr(row, "dtype", None)
    if names is None or names.names is None:
        return metadata

    for column in names.names:
        if column in _TRADE_METADATA_EXCLUDED_COLUMNS:
            continue
        value = row[column]
        if pd.isna(value):
            continue
        metadata[column] = value.item() if hasattr(value, "item") else value
    return metadata


def _optional_float_value(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _optional_int_value(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _adverse_trigger_fill(
    *,
    trigger: float,
    bar_open: float | None,
    is_long: bool,
) -> float:
    """Apply adverse gap-through slippage to a market-triggered exit."""
    if bar_open is None:
        return trigger
    return min(trigger, bar_open) if is_long else max(trigger, bar_open)


def _adverse_exit_priority(pos: Position) -> tuple[int, float]:
    """Process nearer same-side protective exits before deeper liquidation."""
    protective = (
        pos.trail_stop_price
        if pos.trail_active and pos.trail_stop_price is not None
        else pos.sl_price
    )
    return (0, -protective) if pos.is_long else (1, protective)


def _liquidation_buffer_is_safe(pos: Position) -> bool:
    buffer_distance = pos.entry_price * pos.liquidation_buffer_pct
    if pos.is_long:
        return pos.liquidation_price <= pos.sl_price - buffer_distance + 1e-12
    return pos.liquidation_price >= pos.sl_price + buffer_distance - 1e-12


def _validate_minute_execution_data(
    primary: pd.DataFrame,
    data: IntrabarExecutionData,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return complete aligned minute frames for every simulated execution interval."""
    primary_index = primary.index
    if not isinstance(primary_index, pd.DatetimeIndex):
        raise TypeError("minute execution requires a DatetimeIndex OHLCV frame")
    if len(primary_index) < 2:
        raise ValueError("minute execution requires at least two execution bars")
    deltas = primary_index[1:] - primary_index[:-1]
    unique_deltas = deltas.unique()
    if len(unique_deltas) != 1:
        raise ValueError("minute execution requires a continuous OHLCV frame")
    execution_delta = pd.Timedelta(unique_deltas[0])
    if execution_delta < pd.Timedelta(minutes=1):
        raise ValueError("minute execution requires execution bars of at least one minute")
    if execution_delta % pd.Timedelta(minutes=1) != pd.Timedelta(0):
        raise ValueError("minute execution requires minute-aligned execution bars")

    expected = pd.date_range(
        start=primary_index[0],
        end=primary_index[-1],
        freq="1min",
        inclusive="left",
    )
    required_columns = {"open", "high", "low", "close"}
    validated: list[pd.DataFrame] = []
    for name, source in (("last", data.last_1m), ("mark", data.mark_1m)):
        if not isinstance(source.index, pd.DatetimeIndex):
            raise TypeError(f"{name} 1m execution frame must use DatetimeIndex")
        missing_columns = sorted(required_columns - set(source.columns))
        if missing_columns:
            raise ValueError(
                f"{name} 1m execution frame is missing columns: {', '.join(missing_columns)}"
            )
        if source.index.has_duplicates:
            duplicate = source.index[source.index.duplicated()][0]
            raise ValueError(f"{name} 1m execution frame has duplicate timestamp {duplicate}")
        if not source.index.is_monotonic_increasing:
            raise ValueError(f"{name} 1m execution frame must be sorted ascending")
        frame = source.loc[(source.index >= expected[0]) & (source.index <= expected[-1])]
        if not frame.index.equals(expected):
            missing = expected.difference(frame.index)
            extra = frame.index.difference(expected)
            detail = f"first missing={missing[0]}" if len(missing) else f"first extra={extra[0]}"
            raise ValueError(
                f"{name} 1m execution coverage is incomplete: "
                f"expected={len(expected)} actual={len(frame)} {detail}"
            )
        if name == "last":
            aggregated = frame.resample(execution_delta).agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                }
            )
            expected_h1 = primary.loc[
                primary_index[:-1],
                ["open", "high", "low", "close"],
            ]
            comparable_columns = ["high", "low", "close"]
            delta = (aggregated[comparable_columns] - expected_h1[comparable_columns]).abs()
            # OKX native higher-timeframe OHLC and its historical 1m candles can differ by
            # a few ticks. Minute coverage remains strict; this tolerance only prevents
            # harmless aggregation drift from blocking 1m execution.
            tolerance = expected_h1[comparable_columns].abs() * 1e-3 + 0.1
            if "close" in tolerance.columns:
                tolerance.loc[:, "close"] = expected_h1["close"].abs() * 1e-8 + 1e-3
            mismatch = delta > tolerance
            if mismatch.any().any():
                mismatch_time, mismatch_column = mismatch.stack().loc[lambda s: s].index[0]
                raise ValueError(
                    "last 1m candles do not aggregate to execution OHLCV: "
                    f"timestamp={mismatch_time} column={mismatch_column} "
                    f"execution={expected_h1.at[mismatch_time, mismatch_column]} "
                    f"m1={aggregated.at[mismatch_time, mismatch_column]}"
                )
            open_tolerance = expected_h1["open"].abs() * 1e-3 + 0.1
            minute_open_outside_h1 = (
                aggregated["open"] < expected_h1["low"] - open_tolerance
            ) | (aggregated["open"] > expected_h1["high"] + open_tolerance)
            if minute_open_outside_h1.any():
                mismatch_time = minute_open_outside_h1.loc[minute_open_outside_h1].index[0]
                raise ValueError(
                    "first last-price 1m open is outside execution OHLCV range: "
                    f"timestamp={mismatch_time} open={aggregated.at[mismatch_time, 'open']} "
                    f"low={expected_h1.at[mismatch_time, 'low']} "
                    f"high={expected_h1.at[mismatch_time, 'high']}"
                )
        validated.append(frame)
    return validated[0], validated[1]


def _trade_metadata_from_event(event: dict[str, Any] | None) -> dict[str, Any]:
    """Copy non-execution event fields into trade output."""
    if event is None:
        return {}
    metadata: dict[str, Any] = {}
    for column, value in event.items():
        if column in _TRADE_METADATA_EXCLUDED_COLUMNS:
            continue
        if pd.isna(value):
            continue
        metadata[column] = value.item() if hasattr(value, "item") else value
    return metadata
