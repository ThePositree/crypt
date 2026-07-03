from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from backtester.execution_sim import ExecutionSim, Position
from crypt.execution.position_state import LivePosition


@dataclass(frozen=True)
class ReplayReport:
    position_id: str
    expected_exit_reason: str | None
    actual_exit_reason: str | None
    expected_trigger_price: float | None
    actual_fill_price: float | None
    fill_minus_trigger: float | None
    actual_realized_pnl: float | None
    reconstructed_actual_pnl: float | None
    matched: bool


def replay_position(
    *,
    pos: LivePosition,
    candles: pd.DataFrame,
    bar_exit_policy: str = "worst_case",
) -> ReplayReport:
    if pos.status != "closed":
        raise ValueError(f"position {pos.position_id} is not closed")
    entry_time = pos.entry_dt.astimezone(UTC)
    exit_time = (
        datetime.fromisoformat(pos.exit_time).astimezone(UTC)
        if pos.exit_time
        else candles["open_time"].max().to_pydatetime()
    )
    window = candles[
        (pd.to_datetime(candles["open_time"], utc=True) >= pd.Timestamp(entry_time))
        & (pd.to_datetime(candles["open_time"], utc=True) <= pd.Timestamp(exit_time))
    ]
    native_trailing_placed = (
        pos.trail_activation_price is not None
        and pos.trail_callback_spread is not None
        and bool(pos.trailing_algo_client_order_id or pos.trailing_algo_order_id)
    )
    simulated = Position(
        signal_time=pd.Timestamp(pos.signal_dt),
        entry_time=pd.Timestamp(entry_time),
        entry_price=pos.entry_price,
        aggregate_entry_price=pos.aggregate_entry_price or pos.entry_price,
        risk_base_capital=pos.risk_base_capital,
        size=pos.size,
        tp_price=pos.tp_price,
        sl_price=pos.sl_price,
        bar_opened=0,
        fee_entry=pos.entry_fee,
        capital_before=pos.risk_base_capital,
        leverage=pos.leverage,
        locked_margin=pos.locked_margin,
        available_balance_before=pos.risk_base_capital,
        open_positions_before=0,
        total_locked_margin_before=0.0,
        total_locked_margin_after_entry=pos.locked_margin,
        is_long=pos.is_long,
        liquidation_price=(
            pos.liquidation_price
            if pos.liquidation_price is not None
            else (-float("inf") if pos.is_long else float("inf"))
        ),
        maintenance_margin_rate=pos.maintenance_margin_rate,
        liquidation_fee_rate=pos.liquidation_fee_rate,
        liquidation_buffer_pct=pos.liquidation_buffer_pct,
        maintenance_margin_tier_schedule=pos.maintenance_margin_tier_schedule,
        metadata={},
        position_ttl_bars=pos.ttl_bars,
        trail_activation_rrr=pos.trail_activation_rrr if native_trailing_placed else 0.0,
        trail_distance_atr=pos.trail_distance_atr if native_trailing_placed else 0.0,
        trail_activation_price=pos.trail_activation_price if native_trailing_placed else None,
        trail_callback_spread=pos.trail_callback_spread if native_trailing_placed else None,
    )
    sim = ExecutionSim(
        initial_capital=max(pos.risk_base_capital, 1.0),
        bar_exit_policy=bar_exit_policy,
    )
    expected_reason: str | None = None
    expected_price: float | None = None
    bars = list(window.itertuples(index=False))
    for bar_index, row in enumerate(bars):
        bar_number = bar_index + 1
        reason, price = sim._resolve_bar_exit(
            pos=simulated,
            current_open=float(row.o),
            current_high=float(row.h),
            current_low=float(row.l),
            trail_atr=None,
        )
        if reason is not None:
            expected_reason = reason.value
            expected_price = price
            break
        if pos.ttl_bars > 0 and bar_number >= pos.ttl_bars:
            expected_reason = "ttl_expired"
            expected_price = (
                float(bars[bar_index + 1].o) if bar_index + 1 < len(bars) else pos.exit_price
            )
            break

    reconstructed = None
    if pos.exit_price is not None:
        aggregate_entry_price = pos.aggregate_entry_price or pos.entry_price
        gross = (
            (pos.exit_price - aggregate_entry_price) * pos.size
            if pos.is_long
            else (aggregate_entry_price - pos.exit_price) * pos.size
        )
        reconstructed = gross - pos.entry_fee - (pos.exit_fee or 0.0)
    price_difference = (
        pos.exit_price - expected_price
        if pos.exit_price is not None and expected_price is not None
        else None
    )
    return ReplayReport(
        position_id=pos.position_id,
        expected_exit_reason=expected_reason,
        actual_exit_reason=pos.exit_reason,
        expected_trigger_price=expected_price,
        actual_fill_price=pos.exit_price,
        fill_minus_trigger=price_difference,
        actual_realized_pnl=pos.realized_pnl,
        reconstructed_actual_pnl=reconstructed,
        matched=expected_reason == pos.exit_reason,
    )
