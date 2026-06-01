# Adapted from backtester/src/backtester/execution_sim.py
# Original: https://github.com/AuriumX/backtester
#
# Changes vs. the original (see docs/backtest.md §18.4):
#
#   🔴 FundingRateModel interface added; funding charges deducted per bar.
#   🔴 Multi-symbol: input df may have a `symbol` column; capital is shared.
#   🟡 SL gap-adjusted fill: exit_price = min/max(sl_price, bar_open) for gaps.
#   🟡 exit_time off-by-one fixed: TP/SL use df.index[i], TTL uses next_time.
#   🟡 Equity-curve duplicate exit_time fix is in metrics.py (ResultsAnalyzer).
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypedDict

import pandas as pd
from loguru import logger

from crypt.backtest.fee_model import ExitContext, FeeModel, StaticPercentFeeModel
from crypt.backtest.risk_model import BasicRiskModel, EntryContext, RiskModel

# ---------------------------------------------------------------------------
# Funding rate model (🔴 new — funding was dead code in original)
# ---------------------------------------------------------------------------


class FundingRateModel(Protocol):
    """
    Charge funding on an open position.

    Called once per H4 bar for each open position.  Returns the absolute
    funding cost in the same currency as position_value.  A negative return
    means the position *receives* funding (longs pay shorts when rate > 0).
    """

    def charge(self, position_value: float, symbol: str, bar_ts: pd.Timestamp) -> float: ...


class ZeroFundingModel:
    """Default no-op funding model (use with --no-funding flag)."""

    def charge(self, position_value: float, symbol: str, bar_ts: pd.Timestamp) -> float:  # noqa: ARG002
        return 0.0


class ParquetFundingModel:
    """
    Looks up funding rate from a pre-loaded DataFrame.

    The DataFrame must have columns: `ts` (DatetimeIndex or column, UTC) and
    `rate` (float).  Missing rates default to 0 with a WARNING.

    OKX perpetual funding is every 8h; we charge once per H4 bar (= every 4h)
    as half the 8h rate to approximate the correct exposure.
    """

    def __init__(self, funding_df: pd.DataFrame) -> None:
        df = funding_df.set_index("ts") if "ts" in funding_df.columns else funding_df.copy()
        df.index = pd.to_datetime(df.index, utc=True)
        self._df = df.sort_index()

    def charge(self, position_value: float, symbol: str, bar_ts: pd.Timestamp) -> float:  # noqa: ARG002
        if self._df.empty:
            return 0.0
        # Find the most recent funding rate at or before bar_ts.
        idx = self._df.index.searchsorted(bar_ts, side="right") - 1
        if idx < 0:
            return 0.0
        rate = float(self._df.iloc[idx]["rate"])
        # Charge half the 8h rate per H4 bar (2 H4 bars per 8h window).
        return position_value * rate * 0.5


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------


class _NotEnoughBarsError(Exception):
    pass


class _EntryCtxDict(TypedDict, total=True):
    signal: int
    sl_price: float
    risk_percent: float
    rrr: float
    entry_price: float | None
    symbol: str


@dataclass
class Position:
    entry_time: pd.Timestamp
    entry_price: float
    size: float
    tp_price: float
    sl_price: float
    bar_opened: int
    fee_entry: float
    capital_before: float
    leverage: float
    locked_margin: float
    is_long: bool
    symbol: str = ""
    accumulated_funding: float = 0.0

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("Position size must be positive")
        if self.is_long:
            if self.tp_price <= self.entry_price:
                raise ValueError("TP must be above entry for long")
            if self.sl_price >= self.entry_price:
                raise ValueError("SL must be below entry for long")
        else:
            if self.tp_price >= self.entry_price:
                raise ValueError("TP must be below entry for short")
            if self.sl_price <= self.entry_price:
                raise ValueError("SL must be above entry for short")
        if self.leverage < 1:
            raise ValueError("Leverage must be >= 1")


class ExitReason(StrEnum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TTL_EXPIRED = "ttl_expired"


# ---------------------------------------------------------------------------
# ExecutionSim
# ---------------------------------------------------------------------------


class ExecutionSim:
    """
    Multi-symbol trading execution simulator.

    Accepts a time-ordered DataFrame where each row is one (symbol, bar) pair.
    Capital is shared across all symbols.  Use ``is_isolated_futures=True``
    so that locked margin per open position reduces available balance for
    subsequent entries (preventing virtual capital tripling).

    Input df required columns:
        open, high, low, close, signal, sl_price

    Optional columns:
        symbol      — string identifying the trading pair
        risk_percent — per-bar risk override
        rrr          — per-bar reward/risk override
        entry_price  — intra-bar entry (must lie within [low, high])

    Exit-time rule (🟡 fix §18.4):
        TP/SL exits:    exit_time = df.index[i]  (bar where price was hit)
        TTL exits:      exit_time = next_time     (actually executes at next open)
    """

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        taker_fee: float = 0.0005,
        maker_fee: float = 0.0002,
        risk_percent: float = 1.0,
        rrr: float = 2.0,
        max_positions: int = 3,
        position_ttl_bars: int = 6,
        min_net_exposure: float = 0.01,
        max_allowed_leverage: float = 20.0,
        is_isolated_futures: bool = True,
        max_allowed_margin: float = 1.0,
        bar_exit_policy: str = "worst_case",
        sl_pessimism_pct: float = 0.0,
        max_daily_profit: float | None = None,
        max_daily_loss: float | None = None,
        risk_model: RiskModel | None = None,
        fee_model: FeeModel | None = None,
        funding_model: FundingRateModel | None = None,
    ) -> None:
        allowed = {"best_case", "worst_case"}
        policy = bar_exit_policy.strip().lower()
        if policy not in allowed:
            raise ValueError(f"bar_exit_policy must be one of {sorted(allowed)!r}")

        self.initial_capital = initial_capital
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.risk_percent = risk_percent
        self.rrr = rrr
        self.max_positions = max_positions
        self.position_ttl_bars = position_ttl_bars
        self.min_net_exposure = min_net_exposure
        self.max_allowed_leverage = max_allowed_leverage
        self.is_isolated_futures = is_isolated_futures
        self.max_allowed_margin = max_allowed_margin
        self.bar_exit_policy = policy
        self.sl_pessimism_pct = sl_pessimism_pct
        self.max_daily_profit = max_daily_profit
        self.max_daily_loss = max_daily_loss

        self._risk_model: RiskModel = risk_model or BasicRiskModel(
            max_allowed_margin=max_allowed_margin,
            max_positions=max_positions,
            max_allowed_leverage=max_allowed_leverage,
        )
        self._fee_model: FeeModel = fee_model or StaticPercentFeeModel(
            taker_fee=taker_fee,
            maker_fee=maker_fee,
        )
        self._funding_model: FundingRateModel = funding_model or ZeroFundingModel()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_df(self, df: pd.DataFrame) -> bool:
        if len(df) < 2:
            logger.warning("Not enough bars to run simulation")
            raise _NotEnoughBarsError
        required = ["open", "high", "low", "close", "signal", "sl_price"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return "symbol" in df.columns

    # ------------------------------------------------------------------
    # Intra-bar exit resolution
    # ------------------------------------------------------------------

    def _resolve_bar_exit(
        self,
        pos: Position,
        current_high: float,
        current_low: float,
        current_bar_open: float,
    ) -> tuple[ExitReason | None, float | None]:
        """
        Resolve TP/SL within the current bar.

        🟡 Fix §18.4 (SL gap): when bar opens beyond SL, fill at open price.
        Policy `worst_case` (default): SL wins when both TP and SL are hit.
        """
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
            return ExitReason.STOP_LOSS, self._gap_adjusted_sl(pos, current_bar_open)

        # Both hit — resolve by policy.
        if self.bar_exit_policy == "best_case":
            return ExitReason.TAKE_PROFIT, pos.tp_price
        return ExitReason.STOP_LOSS, self._gap_adjusted_sl(pos, current_bar_open)

    def _gap_adjusted_sl(self, pos: Position, bar_open: float) -> float:
        """
        Return the actual SL fill price accounting for gap risk.

        For longs: if the bar opened below SL, the true fill was the open.
        For shorts: if the bar opened above SL, the true fill was the open.
        Optional `sl_pessimism_pct` adds additional slippage beyond the gap.
        """
        base = min(pos.sl_price, bar_open) if pos.is_long else max(pos.sl_price, bar_open)

        if self.sl_pessimism_pct > 0:
            # Apply additional pessimism on top of gap-adjusted price.
            if pos.is_long:
                base = base * (1 - self.sl_pessimism_pct / 100)
            else:
                base = base * (1 + self.sl_pessimism_pct / 100)

        return base

    # ------------------------------------------------------------------
    # Position lifecycle
    # ------------------------------------------------------------------

    def _can_open(
        self,
        position_value: float,
        new_leverage: float,
        active_positions: list[Position],
        available_balance: float,
    ) -> bool:
        if active_positions and self.is_isolated_futures:
            common_lev = active_positions[0].leverage
            if common_lev > 0 and common_lev != new_leverage:
                return False

        required_margin = position_value / new_leverage
        max_margin = self.max_allowed_margin * available_balance or available_balance
        return required_margin <= max_margin

    def _update_active_positions(
        self,
        *,
        active_positions: list[Position],
        capital: float,
        i: int,
        bar_time: pd.Timestamp,
        current_high: float,
        current_low: float,
        current_open: float,
        next_open: float,
        next_time: pd.Timestamp,
        current_symbol: str,
        trade_history: list[dict[str, Any]],
    ) -> tuple[float, list[Position]]:
        remaining: list[Position] = []

        for pos in active_positions:
            # In multi-symbol mode only check positions for the current symbol.
            if current_symbol and pos.symbol and pos.symbol != current_symbol:
                remaining.append(pos)
                continue

            # 🔴 Charge funding for this bar.
            funding_charge = self._funding_model.charge(
                pos.size * pos.entry_price, pos.symbol, bar_time
            )
            pos.accumulated_funding += funding_charge

            exit_reason, exit_price = self._resolve_bar_exit(
                pos, current_high, current_low, current_open
            )

            # TTL check.
            if exit_reason is None and (
                self.position_ttl_bars > 0 and (i + 1) - pos.bar_opened >= self.position_ttl_bars
            ):
                exit_price = next_open
                exit_reason = ExitReason.TTL_EXPIRED

            if exit_reason is not None and exit_price is not None:
                exit_value = pos.size * exit_price
                entry_value = pos.size * pos.entry_price
                is_maker = exit_reason is ExitReason.TAKE_PROFIT
                fee_exit = self._fee_model.calculate_exit_fee(
                    exit_value,
                    is_maker=is_maker,
                    ctx=ExitContext(exit_reason=exit_reason.value),
                )

                fees = pos.fee_entry + fee_exit + pos.accumulated_funding
                pnl_abs = (
                    (exit_value - entry_value - fees)
                    if pos.is_long
                    else (entry_value - exit_value - fees)
                )
                pnl_rel = pnl_abs / entry_value if entry_value != 0 else 0.0
                new_capital = capital + pnl_abs

                # 🟡 Fix §18.4 (exit_time off-by-one):
                # TP/SL fires within bar i → exit_time = bar i's timestamp.
                # TTL fires at next bar's open → exit_time = next_time.
                actual_exit_time = next_time if exit_reason is ExitReason.TTL_EXPIRED else bar_time

                trade_history.append(
                    {
                        "symbol": pos.symbol,
                        "entry_time": pos.entry_time,
                        "exit_time": actual_exit_time,
                        "entry_price": pos.entry_price,
                        "exit_price": exit_price,
                        "size": pos.size,
                        "pnl_abs": pnl_abs,
                        "pnl_rel": pnl_rel,
                        "fee_entry": pos.fee_entry,
                        "fee_exit": fee_exit,
                        "funding": pos.accumulated_funding,
                        "tp_price": pos.tp_price,
                        "sl_price": pos.sl_price,
                        "exit_reason": exit_reason.value,
                        "capital_before": pos.capital_before,
                        "capital_after": new_capital,
                        "holding_bars": (i + 1) - pos.bar_opened,
                        "leverage": pos.leverage,
                        "is_long": pos.is_long,
                        "entry_bar_index": pos.bar_opened,
                        "exit_bar_index": i,
                    }
                )
                capital = new_capital
            else:
                remaining.append(pos)

        return capital, remaining

    def _try_open_position(
        self,
        *,
        i: int,
        bar_time: pd.Timestamp,
        next_time: pd.Timestamp,
        next_open: float,
        capital: float,
        active_positions: list[Position],
        entry_ctx: _EntryCtxDict,
    ) -> list[Position]:
        signal = entry_ctx["signal"]
        if signal not in (1, -1):
            return active_positions
        if self.max_positions > 0 and len(active_positions) >= self.max_positions:
            return active_positions

        sl_price = entry_ctx["sl_price"]
        if pd.isna(sl_price):
            return active_positions

        ctx_entry_price = entry_ctx.get("entry_price")
        if ctx_entry_price is not None:
            entry_price = ctx_entry_price
            entry_time = bar_time
            bar_opened = i
        else:
            entry_price = next_open
            entry_time = next_time
            bar_opened = i + 1

        total_locked_margin = sum(p.locked_margin for p in active_positions)
        risk_ctx = EntryContext(
            signal=signal,
            sl_price=float(sl_price),
            entry_price=entry_price,
            capital=capital,
            total_locked_margin=total_locked_margin,
            risk_percent=entry_ctx["risk_percent"],
            rrr=entry_ctx["rrr"],
        )
        rr = self._risk_model.calculate_position(risk_ctx)
        if rr is None:
            return active_positions

        fee_entry = self._fee_model.calculate_entry_fee(rr.position_value, risk_ctx)
        net_exposure = rr.position_value - fee_entry

        # Protection: fee must not exceed 2x the risk value.
        if fee_entry >= rr.risk_value * 2:
            return active_positions

        if net_exposure < self.min_net_exposure * rr.available_balance:
            return active_positions

        if not self._can_open(
            rr.position_value, rr.required_leverage, active_positions, rr.available_balance
        ):
            return active_positions

        pos = Position(
            entry_time=entry_time,
            entry_price=entry_price,
            size=rr.size,
            tp_price=rr.tp_price,
            sl_price=float(sl_price),
            bar_opened=bar_opened,
            fee_entry=fee_entry,
            capital_before=capital,
            leverage=rr.required_leverage,
            is_long=rr.is_long,
            locked_margin=rr.locked_margin,
            symbol=entry_ctx.get("symbol", ""),
        )
        active_positions.append(pos)
        return active_positions

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulate trading on df; return trade history DataFrame.

        See class docstring for required/optional columns.
        """
        try:
            has_symbol = self._validate_df(df)
        except _NotEnoughBarsError:
            return pd.DataFrame()

        has_risk_pct = "risk_percent" in df.columns
        has_rrr = "rrr" in df.columns
        has_entry_px = "entry_price" in df.columns

        capital = self.initial_capital
        active_positions: list[Position] = []
        trade_history: list[dict[str, Any]] = []

        current_day: pd.Timestamp | None = None
        profit_num = 0
        loss_num = 0
        daily_blocked = False

        work_df = df.copy()
        work_df["__bar_time"] = pd.to_datetime(work_df.index, utc=True)
        if has_symbol:
            symbol_key = work_df["symbol"].astype(str)
            grouped = work_df.groupby(symbol_key, sort=False)
            work_df["__bar_number"] = grouped.cumcount()
            work_df["__next_open"] = grouped["open"].shift(-1)
            work_df["__next_time"] = grouped["__bar_time"].shift(-1)
        else:
            work_df["__bar_number"] = range(len(work_df))
            work_df["__next_open"] = work_df["open"].shift(-1)
            work_df["__next_time"] = work_df["__bar_time"].shift(-1)

        # The final row per symbol has no next open for next-bar entries/TTL exits.
        # TP/SL resolution on those rows is intentionally skipped; the backtest
        # drops tail labels, so forced terminal liquidation would add noise.
        work_df = work_df[work_df["__next_open"].notna()].copy()
        if work_df.empty:
            return pd.DataFrame()

        records = work_df.to_records()

        for i in range(len(records)):
            if capital <= 1:
                logger.warning("Capital below 1, stopping simulation")
                break

            row = records[i]
            bar_time = pd.Timestamp(row["__bar_time"])
            next_time = pd.Timestamp(row["__next_time"])
            next_open: float = float(row["__next_open"])
            bar_number = int(row["__bar_number"])
            current_high: float = float(row["high"])
            current_low: float = float(row["low"])
            current_open: float = float(row["open"])
            current_symbol: str = str(row["symbol"]) if has_symbol else ""

            bar_day = next_time.normalize()
            if current_day is None or bar_day != current_day:
                current_day = bar_day
                profit_num = 0
                loss_num = 0
                daily_blocked = False

            # Prepare entry context.
            signal = int(row["signal"])
            sl_price: float = float(row["sl_price"])
            risk_pct = float(row["risk_percent"]) if has_risk_pct else self.risk_percent
            rrr = float(row["rrr"]) if has_rrr else self.rrr
            entry_px: float | None = None
            if has_entry_px:
                raw_ep = row["entry_price"]
                if not pd.isna(raw_ep):
                    entry_px = float(raw_ep)

            entry_ctx: _EntryCtxDict = {
                "signal": signal,
                "sl_price": sl_price,
                "risk_percent": risk_pct,
                "rrr": rrr,
                "entry_price": entry_px,
                "symbol": current_symbol,
            }

            # Step 1: update existing positions (TP/SL/TTL/funding).
            prev_len = len(trade_history)
            capital, active_positions = self._update_active_positions(
                active_positions=active_positions,
                capital=capital,
                i=bar_number,
                bar_time=bar_time,
                current_high=current_high,
                current_low=current_low,
                current_open=current_open,
                next_open=next_open,
                next_time=next_time,
                current_symbol=current_symbol,
                trade_history=trade_history,
            )

            # Step 1a: daily RRR tracking.
            if self.max_daily_profit or self.max_daily_loss:
                for trade in trade_history[prev_len:]:
                    if pd.Timestamp(trade["exit_time"]).normalize() == current_day:
                        if trade["pnl_abs"] > 0:
                            profit_num += 1
                        elif trade["pnl_abs"] < 0:
                            loss_num += 1

                daily_rrr = profit_num * self.rrr - loss_num
                hit_profit = (
                    self.max_daily_profit is not None
                    and self.max_daily_profit > 0
                    and daily_rrr >= self.max_daily_profit
                )
                hit_loss = (
                    self.max_daily_loss is not None
                    and self.max_daily_loss > 0
                    and daily_rrr <= -self.max_daily_loss
                )
                if hit_profit or hit_loss:
                    daily_blocked = True

            # Step 2: try to open new position.
            if not daily_blocked:
                active_positions = self._try_open_position(
                    i=bar_number,
                    bar_time=bar_time,
                    next_time=next_time,
                    next_open=next_open,
                    capital=capital,
                    active_positions=active_positions,
                    entry_ctx=entry_ctx,
                )

        return pd.DataFrame(trade_history) if trade_history else pd.DataFrame()
