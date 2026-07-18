from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crypt.execution.fill_classifier import (
    allocate_closed_position_fills,
    classify_closed_position_from_fills,
)
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


def test_realized_pnl_keeps_account_and_constituent_views() -> None:
    pos = _position(is_long=True)
    pos.aggregate_entry_price = 150.0
    result = classify_closed_position_from_fills(
        pos=pos,
        fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 150.0,
                "amount": 10.0,
                "fee": {"cost": 0.75},
            }
        ],
    )

    assert result.realized_pnl == pytest.approx(-0.75)
    assert result.constituent_realized_pnl == pytest.approx(499.25)


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


def test_position_with_client_ids_does_not_guess_unidentified_fill() -> None:
    pos = _position(is_long=True)
    pos.algo_client_order_id = "ca-this-position"
    pos.trailing_algo_client_order_id = "ct-this-position"
    pos.close_client_order_id = "cx-this-position"

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
                    "subType": "5",
                },
            }
        ],
    )

    assert result.exit_reason == "exchange_closed_unknown"
    assert result.exit_price is None


def test_position_with_client_ids_matches_close_client_order_id() -> None:
    pos = _position(is_long=True)
    pos.close_client_order_id = "cx-this-position"

    result = classify_closed_position_from_fills(
        pos=pos,
        fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 104.0,
                "amount": 10.0,
                "clientOrderId": "cx-this-position",
                "fee": {"cost": 0.52},
                "info": {
                    "instId": "SOL-USDT-SWAP",
                    "posSide": "long",
                },
            }
        ],
    )

    assert result.exit_reason == "take_profit"
    assert result.exit_price == pytest.approx(104.0)


def test_allocator_consumes_each_fill_for_only_its_exact_position() -> None:
    first = _position(is_long=True)
    first.close_client_order_id = "cx-first"
    second = _position(is_long=True)
    second.close_client_order_id = "cx-second"
    fills = [
        {
            "side": "sell",
            "timestamp": 1_782_561_600_000,
            "price": 104.0,
            "amount": 4.0,
            "clientOrderId": "cx-first",
        },
        {
            "side": "sell",
            "timestamp": 1_782_561_601_000,
            "price": 98.0,
            "amount": 10.0,
            "clientOrderId": "cx-second",
        },
    ]

    allocated = allocate_closed_position_fills(positions=[first, second], fills=fills)

    assert allocated[first.position_id].filled_contracts == pytest.approx(4.0)
    assert allocated[second.position_id].filled_contracts == pytest.approx(10.0)
    assert allocated[first.position_id].exit_price == pytest.approx(104.0)
    assert allocated[second.position_id].exit_price == pytest.approx(98.0)


def test_allocator_blocks_fill_that_matches_multiple_legacy_positions() -> None:
    first = _position(is_long=True)
    second = _position(is_long=True)
    ambiguous_fill = {
        "side": "sell",
        "timestamp": 1_782_561_600_000,
        "price": 104.0,
        "amount": 10.0,
        "info": {
            "instId": "SOL-USDT-SWAP",
            "posSide": "long",
            "subType": "5",
        },
    }

    allocated = allocate_closed_position_fills(
        positions=[first, second],
        fills=[ambiguous_fill],
    )

    assert allocated[first.position_id].filled_contracts == 0.0
    assert allocated[second.position_id].filled_contracts == 0.0


def test_fill_matches_stored_exchange_algo_order_id_without_client_id() -> None:
    pos = _position(is_long=True)
    pos.algo_client_order_id = "ca-missing-from-fill"
    pos.stop_algo_order_id = "algo-stop-1"

    result = classify_closed_position_from_fills(
        pos=pos,
        fills=[
            {
                "id": "trade-1",
                "order": "algo-stop-1",
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 98.0,
                "amount": 10.0,
                "info": {
                    "instId": "SOL-USDT-SWAP",
                    "posSide": "long",
                    "algoId": "algo-stop-1",
                },
            }
        ],
    )

    assert result.exit_price == pytest.approx(98.0)
    assert result.filled_contracts == pytest.approx(10.0)


def test_fill_matches_okx_triggered_algo_id_reported_as_client_order_id() -> None:
    pos = _position(is_long=False)
    pos.algo_client_order_id = "ca-local-stop-client-id"
    pos.stop_algo_order_id = "3739481296226607107"

    result = classify_closed_position_from_fills(
        pos=pos,
        fills=[
            {
                "id": "trade-1",
                "order": "3742361023178203137",
                "side": "buy",
                "timestamp": 1_782_561_600_000,
                "price": 102.0,
                "amount": 10.0,
                "clientOrderId": "3739481296226607107",
                "info": {
                    "instId": "SOL-USDT-SWAP",
                    "posSide": "short",
                    "clOrdId": "3739481296226607107",
                    "ordId": "3742361023178203137",
                },
            }
        ],
    )

    assert result.exit_reason == "stop_loss"
    assert result.exit_price == pytest.approx(102.0)
    assert result.filled_contracts == pytest.approx(10.0)


def test_duplicate_trade_id_is_counted_once() -> None:
    pos = _position(is_long=True)
    pos.close_client_order_id = "cx-1"
    fill = {
        "id": "trade-duplicate",
        "side": "sell",
        "timestamp": 1_782_561_600_000,
        "price": 104.0,
        "amount": 10.0,
        "clientOrderId": "cx-1",
    }

    result = classify_closed_position_from_fills(pos=pos, fills=[fill, dict(fill)])

    assert result.filled_contracts == pytest.approx(10.0)
