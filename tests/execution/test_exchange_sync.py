from __future__ import annotations

from datetime import UTC, datetime

from crypt.execution.exchange_sync import (
    ExchangeBalance,
    ExchangeOrder,
    ExchangePosition,
    ExchangeSnapshot,
    reconcile_exchange_snapshot,
)
from crypt.execution.position_state import ExecutionState, LivePosition


def _snapshot(
    *,
    positions: list[ExchangePosition] | None = None,
    orders: list[ExchangeOrder] | None = None,
) -> ExchangeSnapshot:
    return ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_000.0, used=1_000.0),
        positions=positions or [],
        open_orders=orders or [],
        algo_orders=[],
        recent_fills=[],
    )


def _state_with_position(symbol: str = "SOL-USDT-SWAP") -> ExecutionState:
    pos = LivePosition.create(
        symbol=symbol,
        signal_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=24,
        entry_order_id="entry-1",
        selected_strategy="donor_a",
    )
    return ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )


def test_reconcile_clean_snapshot() -> None:
    state = _state_with_position()
    report = reconcile_exchange_snapshot(
        state=state,
        snapshot=_snapshot(
            positions=[ExchangePosition(symbol="SOL-USDT-SWAP", contracts=10.0)]
        ),
        symbols=["SOL-USDT-SWAP"],
    )
    assert report.synced
    assert report.blocking_reasons == []


def test_reconcile_blocks_orphan_exchange_position() -> None:
    state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    report = reconcile_exchange_snapshot(
        state=state,
        snapshot=_snapshot(
            positions=[ExchangePosition(symbol="SOL-USDT-SWAP", contracts=10.0)]
        ),
        symbols=["SOL-USDT-SWAP"],
    )
    assert not report.synced
    assert report.blocking_reasons == ["orphan_exchange_position:SOL-USDT-SWAP:1"]


def test_reconcile_blocks_missing_exchange_position() -> None:
    report = reconcile_exchange_snapshot(
        state=_state_with_position(),
        snapshot=_snapshot(),
        symbols=["SOL-USDT-SWAP"],
    )
    assert not report.synced
    assert report.blocking_reasons == ["missing_exchange_position:SOL-USDT-SWAP:1"]


def test_reconcile_blocks_orphan_order() -> None:
    state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    report = reconcile_exchange_snapshot(
        state=state,
        snapshot=_snapshot(
            orders=[
                ExchangeOrder(
                    symbol="SOL-USDT-SWAP",
                    order_id="algo-1",
                    kind="algo",
                )
            ]
        ),
        symbols=["SOL-USDT-SWAP"],
    )
    assert not report.synced
    assert report.blocking_reasons == ["orphan_order:SOL-USDT-SWAP:algo-1:algo"]


def test_reconcile_blocks_non_hedged_position_mode() -> None:
    report = reconcile_exchange_snapshot(
        state=ExecutionState(
            schema_version=2,
            risk_window_month=None,
            monthly_risk_base=10_000.0,
            positions=[],
        ),
        snapshot=ExchangeSnapshot(
            fetched_at=datetime(2026, 6, 27, tzinfo=UTC),
            balance=ExchangeBalance(total=10_000.0, free=10_000.0, used=0.0),
            positions=[],
            open_orders=[],
            algo_orders=[],
            recent_fills=[],
            position_mode_hedged=False,
        ),
        symbols=["SOL-USDT-SWAP"],
    )

    assert not report.synced
    assert report.blocking_reasons == ["position_mode_not_long_short"]
