from __future__ import annotations

from typing import Any

import pytest

from crypt.execution.okx_order_client import OKXTradingClient, _okx_to_ccxt_symbol


class FakeOKXExchange:
    def __init__(self) -> None:
        self.leverage_calls: list[tuple[int, str, dict[str, Any]]] = []
        self.order_calls: list[tuple[str, str, str, float, Any, dict[str, Any]]] = []
        self.position_mode_response: dict[str, Any] = {"hedged": True}
        self.algo_pending_calls: list[dict[str, Any]] = []
        self.algo_pending_responses: dict[str, list[dict[str, Any]]] = {}

    def market(self, symbol: str) -> dict[str, Any]:
        assert symbol == "SOL/USDT:USDT"
        return {
            "contractSize": 1.0,
            "precision": {"amount": 0.01, "price": 0.01},
            "limits": {"amount": {"min": 0.01}},
            "info": {"lotSz": "0.01", "minSz": "0.01"},
        }

    def price_to_precision(self, symbol: str, price: float) -> str:
        assert symbol == "SOL/USDT:USDT"
        return f"{price:.2f}"

    async def set_leverage(
        self,
        leverage: int,
        symbol: str,
        params: dict[str, Any],
    ) -> None:
        self.leverage_calls.append((leverage, symbol, params))

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.order_calls.append((symbol, order_type, side, amount, price, params or {}))
        return {"id": "order-1"}

    async def fetch_position_mode(self) -> dict[str, Any]:
        return self.position_mode_response

    async def privateGetTradeOrdersAlgoPending(self, params: dict[str, Any]) -> dict[str, Any]:
        self.algo_pending_calls.append(dict(params))
        return {"data": self.algo_pending_responses.get(str(params["ordType"]), [])}


def make_client(exchange: FakeOKXExchange) -> OKXTradingClient:
    client = object.__new__(OKXTradingClient)
    client._dry_run = False
    client._max_retries = 1
    client._retry_base_delay = 0.0
    client._retry_max_delay = 0.0
    client._markets_loaded = True
    client._exchange = exchange
    return client


def test_okx_to_ccxt_symbol_maps_swap_inst_id() -> None:
    assert _okx_to_ccxt_symbol("SOL-USDT-SWAP") == "SOL/USDT:USDT"


@pytest.mark.asyncio
async def test_set_isolated_leverage_sets_both_hedge_sides() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.set_isolated_leverage("SOL-USDT-SWAP", 25)

    assert exchange.leverage_calls == [
        (25, "SOL/USDT:USDT", {"marginMode": "isolated", "posSide": "long"}),
        (25, "SOL/USDT:USDT", {"marginMode": "isolated", "posSide": "short"}),
    ]


@pytest.mark.asyncio
async def test_get_position_mode_hedged_reads_ccxt_response() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    assert await client.get_position_mode_hedged()
    exchange.position_mode_response = {"hedged": False}
    assert not await client.get_position_mode_hedged()


@pytest.mark.asyncio
async def test_get_pending_algo_orders_queries_required_okx_ord_types() -> None:
    exchange = FakeOKXExchange()
    exchange.algo_pending_responses = {
        "conditional": [{"algoId": "algo-1", "side": "sell", "sz": "2", "slTriggerPx": "90"}],
        "trigger": [{"algoId": "algo-2", "side": "buy", "sz": "3", "triggerPrice": "110"}],
    }
    client = make_client(exchange)

    orders = await client.get_pending_algo_orders("SOL-USDT-SWAP")

    assert exchange.algo_pending_calls == [
        {"instId": "SOL-USDT-SWAP", "ordType": "conditional"},
        {"instId": "SOL-USDT-SWAP", "ordType": "oco"},
        {"instId": "SOL-USDT-SWAP", "ordType": "trigger"},
        {"instId": "SOL-USDT-SWAP", "ordType": "move_order_stop"},
    ]
    assert [order.order_id for order in orders] == ["algo-1", "algo-2"]
    assert [order.kind for order in orders] == ["algo", "algo"]


@pytest.mark.asyncio
async def test_open_position_passes_okx_isolated_side_and_attached_sl_tp() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    order_id = await client.open_position(
        okx_symbol="SOL-USDT-SWAP",
        is_long=True,
        size_asset_units=12.4,
        sl_price=97.123,
        tp_price=108.456,
    )

    assert order_id == "order-1"
    assert exchange.order_calls == [
        (
            "SOL/USDT:USDT",
            "market",
            "buy",
            12.4,
            None,
            {
                "marginMode": "isolated",
                "positionSide": "long",
                "stopLoss": {
                    "triggerPrice": 97.12,
                    "type": "market",
                    "triggerPriceType": "last",
                },
                "takeProfit": {
                    "triggerPrice": 108.46,
                    "price": 108.46,
                    "type": "limit",
                    "triggerPriceType": "last",
                },
            },
        )
    ]


@pytest.mark.asyncio
async def test_open_position_uses_okx_lot_size_for_fractional_contracts() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.open_position(
        okx_symbol="SOL-USDT-SWAP",
        is_long=True,
        size_asset_units=0.4863,
        sl_price=70.0,
        tp_price=76.0,
    )

    assert exchange.order_calls[0][3] == pytest.approx(0.48)


@pytest.mark.asyncio
async def test_close_position_passes_reduce_only_isolated_position_side() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.close_position_at_market(
        okx_symbol="SOL-USDT-SWAP",
        is_long=False,
        contracts=7,
    )

    assert exchange.order_calls == [
        (
            "SOL/USDT:USDT",
            "market",
            "buy",
            7,
            None,
            {
                "reduceOnly": True,
                "marginMode": "isolated",
                "positionSide": "short",
            },
        )
    ]
