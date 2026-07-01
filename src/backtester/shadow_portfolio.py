"""Incremental shadow execution using the external simulator's execution rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backtester.execution_sim import ExecutionSim, Position


@dataclass(frozen=True, slots=True)
class PendingSignal:
    """Signal emitted on the previous closed bar for next-open execution."""

    bar_index: int
    timestamp: pd.Timestamp
    row: dict[str, Any]


@dataclass(slots=True)
class ShadowPortfolioState:
    """Mutable state for one counterfactual strategy portfolio."""

    capital: float
    active_positions: list[Position] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    pending_signal: PendingSignal | None = None
    previous_bar_index: int | None = None
    previous_timestamp: pd.Timestamp | None = None
    previous_open: float | None = None
    previous_high: float | None = None
    previous_low: float | None = None
    previous_trail_atr: float | None = None


class ShadowPortfolio:
    """Advance one strategy's hypothetical portfolio one closed bar at a time."""

    def __init__(self, execution: Any) -> None:
        self._execution = execution
        self._sim = ExecutionSim(
            initial_capital=execution.capital,
            taker_fee=execution.taker_fee,
            maker_fee=execution.maker_fee,
            risk_percent=execution.risk_percent,
            rrr=execution.rrr,
            trail_activation_rrr=execution.trail_activation_rrr,
            trail_distance_atr=execution.trail_distance_atr,
            max_positions=execution.max_positions,
            position_ttl_bars=execution.ttl,
            max_allowed_leverage=execution.max_allowed_leverage,
            max_allowed_margin=execution.max_allowed_margin,
            risk_base_period=execution.risk_base_period,
            max_daily_profit=execution.max_daily_profit,
            max_daily_loss=execution.max_daily_loss,
            trading_begin=execution.trading_begin,
            trading_end=execution.trading_end,
            exit_geometry=execution.exit_geometry,
            tp_move_pct=execution.tp_move_pct,
            structural_sl_mode=execution.structural_sl_mode,
            min_tp_move_pct=execution.min_tp_move_pct,
            instrument_precision_policy=getattr(execution, "instrument_precision_policy", None),
        )
        self.state = ShadowPortfolioState(capital=float(execution.capital))

    def on_closed_bar(
        self,
        *,
        bar_index: int,
        timestamp: pd.Timestamp,
        open_price: float,
        high: float,
        low: float,
        trail_atr: float | None,
        signal_row: pd.Series,
    ) -> None:
        """Advance exits/entries to ``timestamp`` and retain its next-open signal."""

        state = self.state
        if state.previous_timestamp is not None:
            if timestamp <= state.previous_timestamp:
                raise ValueError("Shadow bars must be strictly increasing")
            if state.previous_bar_index is None:
                raise RuntimeError("Shadow previous bar index is missing")
            if (
                state.previous_open is None
                or state.previous_high is None
                or state.previous_low is None
            ):
                raise RuntimeError("Shadow previous OHLC state is missing")
            state.capital, state.active_positions = self._sim._update_active_positions(
                active_positions=state.active_positions,
                capital=state.capital,
                i=state.previous_bar_index,
                current_open=float(state.previous_open),
                current_high=float(state.previous_high),
                current_low=float(state.previous_low),
                trail_atr=state.previous_trail_atr,
                next_open=float(open_price),
                next_time=timestamp,
                trade_history=state.trades,
            )
            pending = state.pending_signal
            if pending is not None:
                state.capital, state.active_positions = self._sim._try_open_position(
                    i=pending.bar_index,
                    current_time=pending.timestamp,
                    next_time=timestamp,
                    next_open=float(open_price),
                    capital=state.capital,
                    active_positions=state.active_positions,
                    entry_ctx=pending.row,  # type: ignore[arg-type]
                    entry_trail_atr=trail_atr,
                )

        state.pending_signal = PendingSignal(
            bar_index=bar_index,
            timestamp=timestamp,
            row=_entry_context(signal_row, self._execution),
        )
        state.previous_bar_index = bar_index
        state.previous_timestamp = timestamp
        state.previous_open = float(open_price)
        state.previous_high = float(high)
        state.previous_low = float(low)
        state.previous_trail_atr = trail_atr


def _entry_context(signal_row: pd.Series, execution: Any) -> dict[str, Any]:
    entry_raw = signal_row.get("entry_price")
    entry_price = float(entry_raw) if entry_raw is not None and not pd.isna(entry_raw) else None
    tp_raw = signal_row.get("tp_move_pct", execution.tp_move_pct)
    tp_move_pct = float(tp_raw) if tp_raw is not None and not pd.isna(tp_raw) else None
    metadata = {
        str(column): value
        for column, value in signal_row.items()
        if column
        not in {
            "open",
            "high",
            "low",
            "close",
            "volume",
            "signal",
            "sl_price",
            "risk_percent",
            "rrr",
            "position_ttl_bars",
            "trail_activation_rrr",
            "trail_distance_atr",
            "exit_geometry",
            "tp_move_pct",
            "structural_sl_mode",
            "min_tp_move_pct",
            "position_group",
            "drain_on_group_change",
            "entry_price",
        }
    }
    return {
        "signal": int(signal_row.get("signal", 0)),
        "sl_price": float(signal_row.get("sl_price", 0.0)),
        "risk_percent": float(signal_row.get("risk_percent", execution.risk_percent)),
        "rrr": float(signal_row.get("rrr", execution.rrr)),
        "entry_price": entry_price,
        "position_ttl_bars": int(signal_row.get("position_ttl_bars", execution.ttl)),
        "trail_activation_rrr": float(
            signal_row.get(
                "trail_activation_rrr",
                execution.trail_activation_rrr,
            )
        ),
        "trail_distance_atr": float(
            signal_row.get(
                "trail_distance_atr",
                execution.trail_distance_atr,
            )
        ),
        "exit_geometry": str(signal_row.get("exit_geometry", execution.exit_geometry)),
        "tp_move_pct": tp_move_pct,
        "structural_sl_mode": str(
            signal_row.get(
                "structural_sl_mode",
                execution.structural_sl_mode,
            )
        ),
        "min_tp_move_pct": float(
            signal_row.get(
                "min_tp_move_pct",
                execution.min_tp_move_pct,
            )
        ),
        "position_group": str(signal_row.get("position_group", "")),
        "drain_on_group_change": bool(signal_row.get("drain_on_group_change", False)),
        "metadata": metadata,
    }
