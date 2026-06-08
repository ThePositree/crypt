import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict

import pandas as pd
from tqdm.auto import tqdm

from .exit_geometry import exit_geometry_config_from_args
from .fee_model import ExitContext, FeeModel, StaticPercentFeeModel
from .margin_policy import per_entry_margin_cap
from .risk_model import BasicRiskModel, EntryContext, RiskModel


class _NotEnoughBarsError(Exception):
    """Internal signal that input data is too short for simulation."""


class _EntryContextDict(TypedDict, total=True):
    """Per-bar context for potential position entry."""

    signal: int
    sl_price: float
    risk_percent: float
    rrr: float
    entry_price: float | None
    metadata: dict[str, Any]


_TRADE_METADATA_EXCLUDED_COLUMNS = frozenset(
    {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "signal",
        "sl_price",
        "risk_percent",
        "rrr",
        "trail_atr",
        "entry_price",
        "index",
        "open_time",
        "tick_time",
    }
)


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
    metadata: dict[str, Any]
    trail_activation_rrr: float = 0.0
    trail_distance_atr: float = 0.0
    trail_active: bool = False
    best_favorable_price: float | None = None
    trail_stop_price: float | None = None

    def __post_init__(self):
        """Validation of input data."""
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


class ExitReason(str, Enum):
    """Standardized reasons for closing a position."""

    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
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
            is_isolated_futures=True,  # Enable isolated futures mode with margin checking
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
        min_net_exposure: float = 0.01,
        max_allowed_leverage: float = 25.0,
        is_perpetual: bool = False,
        is_isolated_futures: bool = False,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        bar_exit_policy: str = "worst_case",
        max_daily_profit: float | None = None,
        max_daily_loss: float | None = None,
        trading_begin: int | None = None,
        trading_end: int | None = None,
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
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
            Maximum position duration in bars.
            If TP/SL not triggered, position closes at TTL expiration
            at next bar's open.
            Disabled if 0.
        min_net_exposure : float, default 0.01 (1%)
            Minimum capital percentage that must remain after commission
            when opening a position. If net_exposure < min_net_exposure * capital,
            position is not opened.
            Example: 0.01 → after fees, at least 1% of capital must be "net" position.
        max_allowed_leverage : float, default 25.0
            Maximum allowed leverage for the strategy.
            If leverage > max_allowed_leverage, position is not opened.
            Example: 25.0 → 25x leverage is not allowed.
        is_isolated_futures : bool, default False
            Enable isolated futures mode. In this mode:
            - All positions must have the same leverage
            - Each position is isolated from others
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
            Start of trading session in hours (0–23) based on the timestamp in
            the input DataFrame. New positions are opened only on bars where
            ``trading_begin <= hour < trading_end`` (if configured). Disabled
            if None.
        trading_end : int | None, optional
            End of trading session in hours (1–24). New positions are opened
            only on bars where ``trading_begin <= hour < trading_end``.
            Disabled if None.

        Notes:
        ----------
        - Position size = risk_value / (entry_price - sl_price) [long] or (sl_price - entry_price) [short]
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
        allowed_policies = {"best_case", "worst_case"}
        allowed_risk_base_periods = {"trade", "weekly", "monthly", "backtest"}

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
        self.min_net_exposure = min_net_exposure
        self.max_allowed_leverage = max_allowed_leverage
        self.is_isolated_futures = is_isolated_futures
        self.max_allowed_margin = max_allowed_margin
        self.risk_base_period = risk_base_period_normalized
        self.bar_exit_policy = bar_exit_policy_normalized
        self.max_daily_profit = max_daily_profit
        self.max_daily_loss = max_daily_loss
        self.trading_begin = trading_begin
        self.trading_end = trading_end
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
        # Check if we have existing positions
        if active_positions and self.is_isolated_futures:
            # Check leverage consistency
            common_leverage = active_positions[0].leverage
            if common_leverage > 0 and common_leverage != new_leverage:
                self._logger.debug(
                    "Isolated futures: leverage mismatch. Existing: %d, New: %d",
                    common_leverage,
                    new_leverage,
                )
                return False

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

        required_columns = ["open", "high", "low", "close", "signal", "sl_price"]
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
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
            current_high = row["high"]
            current_low = row["low"]

            trail_atr = row["trail_atr"] if "trail_atr" in row.dtype.names else None
            yield i, row, next_open, current_high, current_low, trail_atr, next_time

    def _update_active_positions(
        self,
        *,
        active_positions: list[Position],
        capital: float,
        i: int,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
        next_open: float,
        next_time: pd.Timestamp,
        trade_history: list[dict],
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

        for pos in active_positions:
            exit_reason, exit_price = self._resolve_bar_exit(
                pos=pos,
                current_high=current_high,
                current_low=current_low,
                trail_atr=trail_atr,
            )

            # TTL
            if not exit_reason and (
                self.position_ttl_bars > 0 and (i + 1) - pos.bar_opened >= self.position_ttl_bars
            ):
                exit_price = next_open
                exit_reason = ExitReason.TTL_EXPIRED

            # If exit required
            if exit_reason:
                exit_value = pos.size * exit_price
                entry_value = pos.size * pos.entry_price
                is_maker = exit_reason is ExitReason.TAKE_PROFIT
                exit_ctx = ExitContext(exit_reason=exit_reason.value)
                fee_exit = self._fee_model.calculate_exit_fee(
                    exit_value,
                    is_maker=is_maker,
                    ctx=exit_ctx,
                )

                fees = pos.fee_entry + fee_exit
                if pos.is_long:
                    pnl_abs = exit_value - entry_value - fees
                else:
                    pnl_abs = entry_value - exit_value - fees

                pnl_rel = pnl_abs / entry_value if entry_value != 0 else 0.0
                new_capital = capital + pnl_abs

                # Public API: expose string value of ExitReason in trade history.
                reason_value = (
                    exit_reason.value if isinstance(exit_reason, ExitReason) else exit_reason
                )

                trade_history.append(
                    {
                        "signal_time": pos.signal_time,
                        "entry_time": pos.entry_time,
                        "exit_time": next_time,
                        "entry_price": pos.entry_price,
                        "risk_base_capital": pos.risk_base_capital,
                        "exit_price": exit_price,
                        "size": pos.size,
                        "pnl_abs": pnl_abs,
                        "pnl_rel": pnl_rel,
                        "fee_entry": pos.fee_entry,
                        "fee_exit": fee_exit,
                        "tp_price": pos.tp_price,
                        "sl_price": pos.sl_price,
                        "trail_activation_rrr": pos.trail_activation_rrr,
                        "trail_distance_atr": pos.trail_distance_atr,
                        "trail_stop_price": pos.trail_stop_price,
                        "trail_active": pos.trail_active,
                        "exit_reason": reason_value,
                        "capital_before": pos.capital_before,
                        "capital_after": new_capital,
                        "holding_bars": (i + 1) - pos.bar_opened,
                        "leverage": pos.leverage,
                        "locked_margin": pos.locked_margin,
                        "available_balance_before": pos.available_balance_before,
                        "open_positions_before": pos.open_positions_before,
                        "total_locked_margin_before": pos.total_locked_margin_before,
                        "total_locked_margin_after_entry": pos.total_locked_margin_after_entry,
                        "is_long": pos.is_long,
                        "entry_bar_index": pos.bar_opened,
                        "exit_bar_index": i,
                        **pos.metadata,
                    }
                )

                capital = new_capital
            else:
                remaining_positions.append(pos)

        return capital, remaining_positions

    def _resolve_bar_exit(
        self,
        *,
        pos: Position,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
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
        if pos.trail_activation_rrr > 0:
            return self._resolve_trailing_bar_exit(
                pos=pos,
                current_high=current_high,
                current_low=current_low,
                trail_atr=trail_atr,
            )

        if pos.is_long:
            tp_hit = current_high >= pos.tp_price
            sl_hit = current_low <= pos.sl_price
        else:
            tp_hit = current_low <= pos.tp_price
            sl_hit = current_high >= pos.sl_price

        if not tp_hit and not sl_hit:
            return None, None

        if tp_hit and not sl_hit:
            return ExitReason.TAKE_PROFIT, pos.tp_price

        if sl_hit and not tp_hit:
            return ExitReason.STOP_LOSS, pos.sl_price

        # Both TP and SL are hit within the same bar:
        # resolve according to bar_exit_policy.
        if self.bar_exit_policy == "best_case":
            return ExitReason.TAKE_PROFIT, pos.tp_price

        if self.bar_exit_policy == "worst_case":
            return ExitReason.STOP_LOSS, pos.sl_price

        # This should be unreachable due to __init__ validation, but kept
        # defensively to avoid silent inconsistencies.
        raise RuntimeError(f"Unexpected bar_exit_policy {self.bar_exit_policy!r} at runtime.")

    def _resolve_trailing_bar_exit(
        self,
        *,
        pos: Position,
        current_high: float,
        current_low: float,
        trail_atr: float | None,
    ) -> tuple[ExitReason | None, float | None]:
        if trail_atr is None or pd.isna(trail_atr) or trail_atr <= 0:
            return self._resolve_fixed_exit_before_trailing_atr(pos, current_high, current_low)

        sl_dist = abs(pos.entry_price - pos.sl_price)
        if pos.is_long:
            original_sl_hit = current_low <= pos.sl_price
            activation_price = pos.entry_price + sl_dist * pos.trail_activation_rrr
            activation_hit = current_high >= activation_price
            if not pos.trail_active:
                if original_sl_hit and (not activation_hit or self.bar_exit_policy == "worst_case"):
                    return ExitReason.STOP_LOSS, pos.sl_price
                if not activation_hit:
                    tp_hit = current_high >= pos.tp_price
                    if tp_hit:
                        return ExitReason.TAKE_PROFIT, pos.tp_price
                    if original_sl_hit:
                        return ExitReason.STOP_LOSS, pos.sl_price
                    return None, None
                pos.trail_active = True
                pos.best_favorable_price = max(pos.entry_price, current_high)
            else:
                pos.best_favorable_price = max(
                    pos.best_favorable_price or pos.entry_price, current_high
                )

            proposed_stop = pos.best_favorable_price - trail_atr * pos.trail_distance_atr
            pos.trail_stop_price = max(pos.sl_price, proposed_stop)
            if current_low <= pos.trail_stop_price:
                return ExitReason.TRAILING_STOP, pos.trail_stop_price
            return None, None

        original_sl_hit = current_high >= pos.sl_price
        activation_price = pos.entry_price - sl_dist * pos.trail_activation_rrr
        activation_hit = current_low <= activation_price
        if not pos.trail_active:
            if original_sl_hit and (not activation_hit or self.bar_exit_policy == "worst_case"):
                return ExitReason.STOP_LOSS, pos.sl_price
            if not activation_hit:
                tp_hit = current_low <= pos.tp_price
                if tp_hit:
                    return ExitReason.TAKE_PROFIT, pos.tp_price
                if original_sl_hit:
                    return ExitReason.STOP_LOSS, pos.sl_price
                return None, None
            pos.trail_active = True
            pos.best_favorable_price = min(pos.entry_price, current_low)
        else:
            pos.best_favorable_price = min(pos.best_favorable_price or pos.entry_price, current_low)

        proposed_stop = pos.best_favorable_price + trail_atr * pos.trail_distance_atr
        pos.trail_stop_price = min(pos.sl_price, proposed_stop)
        if current_high >= pos.trail_stop_price:
            return ExitReason.TRAILING_STOP, pos.trail_stop_price
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
    ) -> _EntryContextDict:
        """
        Prepare and validate per-bar context required for potential entry.

        Returns
        -------
        dict
            Dictionary with keys: ``signal``, ``sl_price``, ``risk_percent``,
            ``rrr``, ``entry_price``.
        """
        signal = row["signal"]
        sl_price = row["sl_price"]

        risk_percent = self.risk_percent
        if columns_meta.has_risk_percent_col:
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
        if columns_meta.has_rrr_col:
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
        if columns_meta.has_entry_price_col:
            raw_entry_price = row["entry_price"]
            if not pd.isna(raw_entry_price):
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
            "signal": signal,
            "sl_price": sl_price,
            "risk_percent": risk_percent,
            "rrr": rrr,
            "entry_price": entry_price,
            "metadata": _trade_metadata_from_row(row),
        }

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
    ) -> list[Position]:
        """
        Try to open a new position based on signal and risk settings.

        Returns
        -------
        list[Position]
            Updated list of active positions (possibly unchanged).
        """
        signal = entry_ctx["signal"]
        sl_price = entry_ctx["sl_price"]
        risk_percent = entry_ctx["risk_percent"]
        rrr = entry_ctx["rrr"]
        ctx_entry_price = entry_ctx.get("entry_price")

        if (signal != 1 and signal != -1) or (
            len(active_positions) >= self.max_positions and self.max_positions > 0
        ):
            return active_positions

        if ctx_entry_price is not None:
            entry_price = ctx_entry_price
            entry_time = current_time
            bar_opened = i
        else:
            entry_price = next_open
            entry_time = next_time
            bar_opened = i + 1
        risk_base_capital = self._risk_base_capital_for_entry(entry_time, capital)

        if pd.isna(sl_price):
            self._logger.debug("Missing SL price, skipping signal")
            return active_positions

        # Calculate total margin already locked in active positions
        total_locked_margin = sum(pos.locked_margin for pos in active_positions)
        open_positions_before = len(active_positions)

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
        )

        risk_result = self._risk_model.calculate_position(entry_context)
        if risk_result is None:
            return active_positions

        position_value = risk_result.position_value
        risk_value = risk_result.risk_value
        available_balance = risk_result.available_balance
        total_locked_margin_after_entry = total_locked_margin + risk_result.locked_margin

        # Entry fee and exposure checks remain in the engine so that they can
        # combine risk and commission information.
        fee_entry = self._fee_model.calculate_entry_fee(position_value, entry_context)
        net_exposure = position_value - fee_entry

        # Protection: fee should not be larger than risk
        if fee_entry >= risk_value * 2:
            return active_positions

        if net_exposure < self.min_net_exposure * available_balance:
            return active_positions

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
            return active_positions

        new_position = Position(
            signal_time=current_time,
            entry_time=entry_time,
            entry_price=entry_price,
            risk_base_capital=risk_base_capital,
            size=risk_result.size,
            tp_price=risk_result.tp_price,
            sl_price=risk_result.sl_price,
            bar_opened=bar_opened,
            fee_entry=fee_entry,
            capital_before=capital,
            leverage=risk_result.required_leverage,
            is_long=risk_result.is_long,
            locked_margin=risk_result.locked_margin,
            available_balance_before=available_balance,
            open_positions_before=open_positions_before,
            total_locked_margin_before=total_locked_margin,
            total_locked_margin_after_entry=total_locked_margin_after_entry,
            metadata=entry_ctx["metadata"],
            trail_activation_rrr=self.trail_activation_rrr,
            trail_distance_atr=self.trail_distance_atr,
        )
        active_positions.append(new_position)

        return active_positions

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
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
        if self.trail_activation_rrr > 0 and "trail_atr" not in df.columns:
            df = _with_closed_atr14(df)

        try:
            columns_meta = self._validate_input_df(df)
        except _NotEnoughBarsError:
            return pd.DataFrame()

        capital = self.initial_capital
        active_positions: list[Position] = []
        trade_history: list[dict] = []

        # Daily RRR tracking state
        current_day = None
        profit_num = 0
        loss_num = 0
        daily_trading_blocked = False

        for i, row, next_open, current_high, current_low, trail_atr, next_time in self._iter_bars(
            df
        ):
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

            entry_ctx = self._prepare_entry_context(
                df=df,
                i=i,
                row=row,
                columns_meta=columns_meta,
            )

            # === 1. Check exit conditions (TP/SL/TTL) for all active positions ===
            prev_trades_len = len(trade_history)
            capital, active_positions = self._update_active_positions(
                active_positions=active_positions,
                capital=capital,
                i=i,
                current_high=current_high,
                current_low=current_low,
                trail_atr=trail_atr,
                next_open=next_open,
                next_time=next_time,
                trade_history=trade_history,
            )

            # === 1a. Update daily RRR counters based on newly closed trades ===
            if self.max_daily_profit or self.max_daily_loss:
                for trade in trade_history[prev_trades_len:]:
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
                current_time = df.index[i]
                active_positions = self._try_open_position(
                    i=i,
                    current_time=current_time,
                    next_time=next_time,
                    next_open=next_open,
                    capital=capital,
                    active_positions=active_positions,
                    entry_ctx=entry_ctx,
                )

        if active_positions:
            last_bar_index = len(df) - 1
            trade_history.extend(
                self._open_position_snapshot(pos=pos, last_bar_index=last_bar_index)
                for pos in active_positions
            )

        return pd.DataFrame(trade_history) if trade_history else pd.DataFrame()

    @staticmethod
    def _open_position_snapshot(*, pos: Position, last_bar_index: int) -> dict[str, Any]:
        """Represent an active entry without realizing PnL at end of data."""
        return {
            "signal_time": pos.signal_time,
            "entry_time": pos.entry_time,
            "exit_time": pd.NaT,
            "entry_price": pos.entry_price,
            "risk_base_capital": pos.risk_base_capital,
            "exit_price": pd.NA,
            "size": pos.size,
            "pnl_abs": pd.NA,
            "pnl_rel": pd.NA,
            "fee_entry": pos.fee_entry,
            "fee_exit": pd.NA,
            "tp_price": pos.tp_price,
            "sl_price": pos.sl_price,
            "trail_activation_rrr": pos.trail_activation_rrr,
            "trail_distance_atr": pos.trail_distance_atr,
            "trail_stop_price": pos.trail_stop_price,
            "trail_active": pos.trail_active,
            "exit_reason": ExitReason.OPEN.value,
            "capital_before": pos.capital_before,
            "capital_after": pd.NA,
            "holding_bars": max(last_bar_index - pos.bar_opened, 0),
            "leverage": pos.leverage,
            "locked_margin": pos.locked_margin,
            "available_balance_before": pos.available_balance_before,
            "open_positions_before": pos.open_positions_before,
            "total_locked_margin_before": pos.total_locked_margin_before,
            "total_locked_margin_after_entry": pos.total_locked_margin_after_entry,
            "is_long": pos.is_long,
            "entry_bar_index": pos.bar_opened,
            "exit_bar_index": pd.NA,
            **pos.metadata,
        }


def _with_closed_atr14(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    previous_close = enriched["close"].shift(1)
    true_range = pd.concat(
        [
            enriched["high"] - enriched["low"],
            (enriched["high"] - previous_close).abs(),
            (enriched["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    enriched["trail_atr"] = true_range.rolling(14).mean().shift(1)
    return enriched


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
