from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crypt.execution.fill_classifier import classify_closed_position_from_fills
from crypt.execution.position_state import LivePosition


def _position(*, is_long: bool = True) -> LivePosition:
    return LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0 if is_long else 102.0,
        tp_price=104.0 if is_long else 96.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=is_long,
        ttl_bars=24,
        entry_order_id="entry-1",
    )


def test_classifies_long_take_profit_fill() -> None:
    result = classify_closed_position_from_fills(
        pos=_position(is_long=True),
        fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 104.0,
                "amount": 10.0,
                "fee": {"cost": 0.52},
            }
        ],
    )

    assert result.exit_reason == "take_profit"
    assert result.exit_price == pytest.approx(104.0)
    assert result.realized_pnl == pytest.approx(39.48)
    assert result.exit_fee == pytest.approx(0.52)


def test_classifies_short_stop_loss_fill() -> None:
    result = classify_closed_position_from_fills(
        pos=_position(is_long=False),
        fills=[
            {
                "side": "buy",
                "datetime": "2026-06-27T12:00:00Z",
                "price": 102.0,
                "amount": 10.0,
                "fee": {"cost": 0.51},
            }
        ],
    )

    assert result.exit_reason == "stop_loss"
    assert result.exit_price == pytest.approx(102.0)
    assert result.realized_pnl == pytest.approx(-20.51)


def test_no_matching_fill_is_unknown() -> None:
    result = classify_closed_position_from_fills(
        pos=_position(is_long=True),
        fills=[{"side": "buy", "timestamp": 1_782_561_600_000, "price": 104.0}],
    )

    assert result.exit_reason == "exchange_closed_unknown"
    assert result.exit_price is None
    assert result.realized_pnl is None


def test_ignores_other_position_algo_fill() -> None:
    pos = _position(is_long=True)
    pos.algo_client_order_id = "algo-this-position"

    result = classify_closed_position_from_fills(
        pos=pos,
        fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 104.0,
                "amount": 10.0,
                "info": {
                    "instId": "SOL-USDT-SWAP",
                    "posSide": "long",
                    "algoClOrdId": "algo-other-position",
                    "subType": "5",
                },
            }
        ],
    )

    assert result.exit_reason == "exchange_closed_unknown"
    assert result.exit_price is None
