from __future__ import annotations

from typing import Any

import ccxt
import pytest

from crypt.execution.okx_order_client import OKXTradingClient, _okx_to_ccxt_symbol


class FakeOKXExchange:
    def __init__(self) -> None:
        self.leverage_calls: list[tuple[int, str, dict[str, Any]]] = []
        self.order_calls: list[tuple[str, str, str, float, Any, dict[str, Any]]] = []
        self.position_mode_response: dict[str, Any] = {"hedged": True}
        self.algo_pending_calls: list[dict[str, Any]] = []
        self.algo_pending_responses: dict[str, list[dict[str, Any]]] = {}
        self.cancel_algo_calls: list[list[dict[str, Any]]] = []
        self.cancel_order_calls: list[tuple[str, str]] = []
        self.place_algo_calls: list[dict[str, Any]] = []
        self.cancel_as_missing = False

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

    async def privateGetTradeOrder(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "data": [
                {
                    "ordId": "order-1",
                    "clOrdId": params["clOrdId"],
                    "state": "filled",
                    "avgPx": "100.25",
                    "accFillSz": "12.4",
                }
            ]
        }

    async def privatePostTradeCancelAlgos(self, params: list[dict[str, Any]]) -> dict[str, Any]:
        if self.cancel_as_missing:
            raise ccxt.OrderNotFound("already terminal")
        self.cancel_algo_calls.append(params)
        return {"data": [{"sCode": "0"}]}

    async def privatePostTradeOrderAlgo(self, params: dict[str, Any]) -> dict[str, Any]:
        self.place_algo_calls.append(params)
        return {"data": [{"algoId": "trailing-1", "sCode": "0", "sMsg": ""}]}

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        if self.cancel_as_missing:
            raise ccxt.OrderNotFound("already terminal")
        self.cancel_order_calls.append((order_id, symbol))


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
async def test_get_instrument_precision_uses_live_market_metadata() -> None:
    client = make_client(FakeOKXExchange())

    precision = await client.get_instrument_precision("SOL-USDT-SWAP")

    assert precision.contract_size == 1.0
    assert precision.amount_step == 0.01
    assert precision.min_amount == 0.01
    assert precision.price_tick == 0.01


@pytest.mark.asyncio
async def test_set_isolated_leverage_sets_only_requested_hedge_side() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.set_isolated_leverage("SOL-USDT-SWAP", 25, is_long=True)

    assert exchange.leverage_calls == [
        (25, "SOL/USDT:USDT", {"marginMode": "isolated", "posSide": "long"}),
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

    result = await client.open_position(
        okx_symbol="SOL-USDT-SWAP",
        is_long=True,
        size_asset_units=12.4,
        sl_price=97.123,
        tp_price=108.456,
        client_order_id="entry-1",
        algo_client_order_id="algo-1",
    )

    assert result is not None
    assert result.order_id == "order-1"
    assert result.average_price == pytest.approx(100.25)
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
                "clientOrderId": "entry-1",
                "attachAlgoOrds": [
                    {
                        "attachAlgoClOrdId": "algo-1",
                        "slTriggerPx": "97.12",
                        "slOrdPx": "-1",
                        "slTriggerPxType": "last",
                        "tpTriggerPx": "108.46",
                        "tpOrdPx": "108.46",
                        "tpOrdKind": "limit",
                        "tpTriggerPxType": "last",
                    }
                ],
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
        client_order_id="entry-2",
        algo_client_order_id="algo-2",
    )

    assert exchange.order_calls[0][3] == pytest.approx(0.48)


@pytest.mark.asyncio
async def test_open_position_can_keep_stop_without_racing_fixed_take_profit() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.open_position(
        okx_symbol="SOL-USDT-SWAP",
        is_long=True,
        size_asset_units=0.41,
        sl_price=70.95,
        tp_price=75.99,
        client_order_id="entry-trailing",
        algo_client_order_id="stop-trailing",
        include_take_profit=False,
    )

    attached = exchange.order_calls[0][5]["attachAlgoOrds"][0]
    assert attached["slTriggerPx"] == "70.95"
    assert "tpTriggerPx" not in attached


@pytest.mark.asyncio
async def test_close_position_passes_reduce_only_isolated_position_side() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.close_position_at_market(
        okx_symbol="SOL-USDT-SWAP",
        is_long=False,
        contracts=7,
        client_order_id="close-1",
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
                "clientOrderId": "close-1",
            },
        )
    ]


@pytest.mark.asyncio
async def test_cancel_protection_accepts_exchange_generated_ids() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    await client.cancel_algo_order_for_position(
        okx_symbol="SOL-USDT-SWAP",
        algo_client_order_id="",
        algo_order_id="algo-123",
    )
    await client.cancel_regular_order(
        okx_symbol="SOL-USDT-SWAP",
        order_id="tp-456",
    )

    assert exchange.cancel_algo_calls == [[{"instId": "SOL-USDT-SWAP", "algoId": "algo-123"}]]
    assert exchange.cancel_order_calls == [("tp-456", "SOL/USDT:USDT")]


@pytest.mark.asyncio
async def test_cancel_protection_is_idempotent_when_oco_sibling_already_terminal() -> None:
    exchange = FakeOKXExchange()
    exchange.cancel_as_missing = True
    client = make_client(exchange)

    await client.cancel_regular_order(
        okx_symbol="SOL-USDT-SWAP",
        order_id="tp-terminal",
    )
    await client.cancel_algo_order_for_position(
        okx_symbol="SOL-USDT-SWAP",
        algo_client_order_id="",
        algo_order_id="sl-terminal",
    )


@pytest.mark.asyncio
async def test_place_native_trailing_stop_uses_fixed_spread_and_activation() -> None:
    exchange = FakeOKXExchange()
    client = make_client(exchange)

    algo_id = await client.place_trailing_stop(
        okx_symbol="SOL-USDT-SWAP",
        is_long=True,
        contracts=0.41,
        activation_price=75.9916,
        callback_spread=0.3123,
        algo_client_order_id="trail-1",
    )

    assert algo_id == "trailing-1"
    assert exchange.place_algo_calls == [
        {
            "instId": "SOL-USDT-SWAP",
            "tdMode": "isolated",
            "side": "sell",
            "posSide": "long",
            "ordType": "move_order_stop",
            "sz": "0.41",
            "callbackSpread": "0.31",
            "activePx": "75.99",
            "algoClOrdId": "trail-1",
            "reduceOnly": True,
        }
    ]
