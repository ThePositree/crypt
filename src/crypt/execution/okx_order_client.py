"""OKXTradingClient — wraps ccxt OKX for live order placement.

All order placement paths accept a `dry_run` flag. When True, methods log
what they would do but make no API calls and return None for order IDs.

OKX symbol mapping:
  project format:  SOL-USDT-SWAP
  ccxt unified:    SOL/USDT:USDT
The client performs this conversion via `exchange.load_markets()`.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Any

import ccxt.async_support as ccxt

from backtester.instrument_precision import InstrumentPrecision
from crypt.execution.exchange_sync import (
    ExchangeBalance,
    ExchangeOrder,
    ExchangePosition,
    ExchangeSnapshot,
)
from crypt.utils.retry import retry_with_backoff

_logger = logging.getLogger(__name__)
_OKX_PENDING_ALGO_ORD_TYPES = ("conditional", "oco", "trigger", "move_order_stop")
_FILL_CONFIRM_TIMEOUT_S = 10.0
_FILL_CONFIRM_POLL_S = 0.25


@dataclass(frozen=True)
class EntryOrderResult:
    order_id: str
    average_price: float
    filled_contracts: float
    fee: float


@dataclass(frozen=True)
class CloseOrderResult:
    order_id: str
    average_price: float
    filled_contracts: float
    fee: float


def _okx_to_ccxt_symbol(okx_symbol: str) -> str:
    """Convert OKX instId to ccxt unified symbol.

    SOL-USDT-SWAP → SOL/USDT:USDT
    TON-USDT-SWAP → TON/USDT:USDT
    """
    parts = okx_symbol.split("-")
    if len(parts) >= 3 and parts[-1] == "SWAP":
        base = parts[0]
        quote = parts[1]
        return f"{base}/{quote}:{quote}"
    return okx_symbol


class OKXTradingClient:
    """
    Async OKX trading client for the live execution module.

    Provides:
    - leverage management (isolated margin)
    - balance and position queries
    - market entry orders with embedded SL and TP
    - market close orders
    - OKX algo order cancellation

    All write methods are no-ops when ``dry_run=True``.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        *,
        dry_run: bool = True,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 15.0,
    ) -> None:
        self._dry_run = dry_run
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._markets_loaded = False

        config: dict[str, Any] = {
            "enableRateLimit": True,
            "timeout": 30_000,
            "options": {"defaultType": "swap"},
        }
        if api_key and api_secret and api_passphrase:
            config["apiKey"] = api_key
            config["secret"] = api_secret
            config["password"] = api_passphrase

        self._exchange: ccxt.okx = ccxt.okx(config)

    async def _ensure_markets(self) -> None:
        if not self._markets_loaded:
            await self._exchange.load_markets()
            self._markets_loaded = True

    def _ccxt_symbol(self, okx_symbol: str) -> str:
        return _okx_to_ccxt_symbol(okx_symbol)

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    async def get_usdt_balance(self) -> float:
        """Return available USDT balance (equity minus locked margin)."""
        balance = await self.get_usdt_balance_snapshot()
        return balance.total if balance.total > 0 else balance.free

    async def get_usdt_balance_snapshot(self) -> ExchangeBalance:
        """Return normalized USDT balance components."""
        await self._ensure_markets()

        async def _call() -> dict[str, Any]:
            return await self._exchange.fetch_balance()  # type: ignore[no-any-return]

        try:
            balance = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label="fetch_balance",
            )
        except Exception as exc:
            raise RuntimeError("failed to fetch OKX balance") from exc

        usdt = balance.get("USDT", {})
        free = float(usdt.get("free", 0.0) or 0.0)
        equity = float(usdt.get("total", 0.0) or 0.0)
        cash_balance = _okx_cash_balance(balance)
        total = cash_balance if cash_balance is not None else equity
        used = max(total - free, 0.0)
        return ExchangeBalance(
            total=total if total > 0 else free + used,
            free=free,
            used=used,
            equity=equity if equity > 0 else None,
        )

    async def get_open_positions(self, okx_symbol: str) -> list[dict[str, Any]]:
        """Return all open positions for the given symbol."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        async def _call() -> list[Any]:
            return await self._exchange.fetch_positions([ccxt_sym])  # type: ignore[no-any-return]

        try:
            positions = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_positions {okx_symbol}",
            )
        except Exception as exc:
            raise RuntimeError(f"failed to fetch OKX positions for {okx_symbol}") from exc

        return [p for p in positions if float(p.get("contracts", 0) or 0) != 0]

    async def get_exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:
        """Fetch balance, positions, open orders, algo orders, and recent fills."""
        from datetime import UTC, datetime

        await self._ensure_markets()
        balance = await self.get_usdt_balance_snapshot()
        position_mode_hedged = await self.get_position_mode_hedged()
        positions: list[ExchangePosition] = []
        open_orders: list[ExchangeOrder] = []
        algo_orders: list[ExchangeOrder] = []
        recent_fills: list[dict[str, Any]] = []

        for symbol in symbols:
            raw_positions = await self.get_open_positions(symbol)
            positions.extend(_normalize_position(symbol, item) for item in raw_positions)
            open_orders.extend(await self.get_open_orders(symbol))
            algo_orders.extend(await self.get_pending_algo_orders(symbol))
            recent_fills.extend(await self.get_recent_fills(symbol))

        return ExchangeSnapshot(
            fetched_at=datetime.now(UTC),
            balance=balance,
            positions=positions,
            open_orders=open_orders,
            algo_orders=algo_orders,
            recent_fills=recent_fills,
            position_mode_hedged=position_mode_hedged,
        )

    async def get_position_mode_hedged(self) -> bool:
        """Return True when OKX account is in long/short position mode."""
        await self._ensure_markets()

        async def _call() -> dict[str, Any]:
            return await self._exchange.fetch_position_mode()  # type: ignore[no-any-return]

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label="fetch_position_mode",
            )
        except Exception as exc:
            raise RuntimeError("failed to fetch OKX position mode") from exc
        return bool(response.get("hedged", False))

    async def get_open_orders(self, okx_symbol: str) -> list[ExchangeOrder]:
        """Return normalized regular open orders for a symbol."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        async def _call() -> list[Any]:
            return await self._exchange.fetch_open_orders(ccxt_sym)  # type: ignore[no-any-return]

        try:
            orders = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_open_orders {okx_symbol}",
            )
        except Exception as exc:
            raise RuntimeError(f"failed to fetch OKX open orders for {okx_symbol}") from exc
        return [_normalize_order(okx_symbol, order, kind="regular") for order in orders]

    async def get_pending_algo_orders(self, okx_symbol: str) -> list[ExchangeOrder]:
        """Return pending OKX algo orders when ccxt exposes the raw endpoint."""
        await self._ensure_markets()
        method = getattr(self._exchange, "privateGetTradeOrdersAlgoPending", None)
        if method is None:
            raise RuntimeError("ccxt does not expose OKX pending algo orders")

        orders: list[ExchangeOrder] = []
        seen_order_ids: set[str] = set()
        for ord_type in _OKX_PENDING_ALGO_ORD_TYPES:

            async def _call(ord_type: str = ord_type) -> dict[str, Any]:
                return await method(  # type: ignore[no-any-return]
                    {"instId": okx_symbol, "ordType": ord_type}
                )

            try:
                response = await retry_with_backoff(
                    _call,
                    max_attempts=self._max_retries,
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    label=f"orders-algo-pending {okx_symbol} {ord_type}",
                )
            except Exception as exc:
                raise RuntimeError(
                    f"failed to fetch OKX {ord_type} algo orders for {okx_symbol}"
                ) from exc

            data = response.get("data", []) if isinstance(response, dict) else []
            for raw_order in data:
                order = _normalize_order(okx_symbol, raw_order, kind="algo")
                dedupe_key = order.order_id or repr(raw_order)
                if dedupe_key in seen_order_ids:
                    continue
                seen_order_ids.add(dedupe_key)
                orders.append(order)
        return orders

    async def get_recent_fills(self, okx_symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent fills for reconciliation and operator diagnostics."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        async def _call() -> list[Any]:
            return await self._exchange.fetch_my_trades(ccxt_sym, limit=limit)  # type: ignore[no-any-return]

        try:
            fills = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_my_trades {okx_symbol}",
            )
        except Exception as exc:
            raise RuntimeError(f"failed to fetch OKX fills for {okx_symbol}") from exc
        deduplicated: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in fills:
            fill = dict(item)
            identity = _fill_identity(fill)
            if identity in seen:
                continue
            seen.add(identity)
            deduplicated.append(fill)
        return deduplicated

    async def get_contract_size(self, okx_symbol: str) -> float:
        """Return the contract size for the symbol (e.g. 1.0 SOL per contract)."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        market = self._exchange.market(ccxt_sym)
        return float(market.get("contractSize", 1.0) or 1.0)

    async def get_instrument_precision(self, okx_symbol: str) -> InstrumentPrecision:
        """Return the live exchange precision contract for one instrument."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        market = self._exchange.market(ccxt_sym)
        step = _market_amount_step(market)
        price_precision = (market.get("precision") or {}).get("price")
        if not price_precision:
            raise RuntimeError(f"OKX returned no price precision for {okx_symbol}")
        return InstrumentPrecision(
            contract_size=float(market.get("contractSize", 1.0) or 1.0),
            amount_step=step,
            min_amount=_market_min_amount(market, step),
            price_tick=float(price_precision),
        )

    async def get_last_price(self, okx_symbol: str) -> float:
        """Return the latest tradable last price for sizing and drift measurement."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        async def _call() -> dict[str, Any]:
            return await self._exchange.fetch_ticker(ccxt_sym)  # type: ignore[no-any-return]

        ticker = await retry_with_backoff(
            _call,
            max_attempts=self._max_retries,
            base_delay=self._retry_base_delay,
            max_delay=self._retry_max_delay,
            label=f"fetch_ticker {okx_symbol}",
        )
        last = _float_or_none(ticker.get("last"))
        if last is None or last <= 0:
            raise RuntimeError(f"OKX returned no valid last price for {okx_symbol}")
        return last

    async def size_asset_units_to_contracts(
        self,
        okx_symbol: str,
        size_asset_units: float,
    ) -> float:
        """Convert base-asset position size to OKX contracts rounded down to lot size."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        market = self._exchange.market(ccxt_sym)
        contract_size = float(market.get("contractSize", 1.0) or 1.0)
        if contract_size <= 0:
            return 0.0

        raw_contracts = size_asset_units / contract_size
        step = _market_amount_step(market)
        contracts = math.floor((raw_contracts / step) + 1e-12) * step
        min_amount = _market_min_amount(market, step)
        if contracts + 1e-12 < min_amount:
            return 0.0
        return _trim_float(contracts)

    # ------------------------------------------------------------------
    # Write methods (no-ops in dry_run mode)
    # ------------------------------------------------------------------

    async def set_isolated_leverage(
        self,
        okx_symbol: str,
        leverage: int,
        *,
        is_long: bool,
    ) -> None:
        """Set isolated margin leverage for the symbol.

        Must be called before placing entry orders (OKX requirement).
        In OKX long/short position mode isolated leverage is side-specific.
        Never rewrite the opposite side because it may have a position/order.
        """
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        if self._dry_run:
            _logger.info("[DRY RUN] Would set isolated leverage %dx for %s", leverage, okx_symbol)
            return

        pos_side = "long" if is_long else "short"

        async def _call() -> None:
            await self._exchange.set_leverage(
                leverage,
                ccxt_sym,
                {"marginMode": "isolated", "posSide": pos_side},
            )

        try:
            await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"set_leverage {okx_symbol} {pos_side}",
            )
            _logger.info(
                "Leverage set to %dx (isolated) for %s %s",
                leverage,
                okx_symbol,
                pos_side,
            )
        except Exception as exc:
            _logger.error("set_leverage %s failed: %s", okx_symbol, exc)
            raise

    async def open_position(
        self,
        *,
        okx_symbol: str,
        is_long: bool,
        size_asset_units: float,
        sl_price: float,
        tp_price: float,
        client_order_id: str,
        algo_client_order_id: str,
        include_take_profit: bool = True,
    ) -> EntryOrderResult | None:
        """
        Place a market entry order with embedded stop-loss and take-profit.

        Parameters
        ----------
        okx_symbol : str
            OKX instId (e.g. SOL-USDT-SWAP).
        is_long : bool
            True for long (buy), False for short (sell).
        size_asset_units : float
            Position size in base asset units (e.g. SOL).
            Converted to OKX contracts internally.
        sl_price : float
            Stop-loss trigger price. Filled as a market order by OKX algo.
        tp_price : float
            Take-profit trigger price. Filled as a limit order by OKX algo.

        Returns
        -------
        str or None
            OKX entry order ID, or None in dry_run mode.
        """
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        contract_size = await self.get_contract_size(okx_symbol)

        contracts = await self.size_asset_units_to_contracts(okx_symbol, size_asset_units)
        if contracts <= 0:
            _logger.warning(
                "Position size %.4f %s is below exchange min amount (contract_size=%.4f) — skipping",
                size_asset_units,
                okx_symbol,
                contract_size,
            )
            return None

        side = "buy" if is_long else "sell"
        position_side = "long" if is_long else "short"

        sl_precision = float(self._exchange.price_to_precision(ccxt_sym, sl_price))
        tp_precision = float(self._exchange.price_to_precision(ccxt_sym, tp_price))

        attached_protection: dict[str, str] = {
            "attachAlgoClOrdId": algo_client_order_id,
            "slTriggerPx": str(sl_precision),
            "slOrdPx": "-1",
            "slTriggerPxType": "last",
        }
        if include_take_profit:
            attached_protection.update(
                {
                    "tpTriggerPx": str(tp_precision),
                    "tpOrdPx": str(tp_precision),
                    "tpOrdKind": "limit",
                    "tpTriggerPxType": "last",
                }
            )
        order_params: dict[str, Any] = {
            "marginMode": "isolated",
            "positionSide": position_side,
            "clientOrderId": client_order_id,
            "attachAlgoOrds": [attached_protection],
        }

        _logger.info(
            "%s Would open %s %s contracts of %s @ market | SL=%.4f TP=%.4f",
            "[DRY RUN]" if self._dry_run else "[LIVE]",
            "LONG" if is_long else "SHORT",
            _format_contracts(contracts),
            okx_symbol,
            sl_precision,
            tp_precision,
        )

        if self._dry_run:
            return None

        async def _call() -> dict[str, Any]:
            return await self._exchange.create_order(  # type: ignore[no-any-return]
                ccxt_sym, "market", side, contracts, params=order_params
            )

        try:
            order = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"create_order entry {okx_symbol}",
            )
            order_id = str(order.get("id", ""))
            _logger.info(
                "Entry order placed for %s: id=%s %s contracts %s SL=%.4f TP=%.4f",
                okx_symbol,
                order_id,
                _format_contracts(contracts),
                "LONG" if is_long else "SHORT",
                sl_precision,
                tp_precision,
            )
            return await self._confirm_entry_fill(
                okx_symbol=okx_symbol,
                order_id=order_id,
                client_order_id=client_order_id,
            )
        except Exception as exc:
            recovered = await self._fetch_order_by_client_id(
                okx_symbol=okx_symbol,
                client_order_id=client_order_id,
            )
            if recovered is not None:
                order_id = str(recovered.get("ordId") or recovered.get("id") or "")
                if order_id:
                    _logger.warning(
                        "Recovered entry %s after create_order error via clientOrderId=%s",
                        order_id,
                        client_order_id,
                    )
                    return await self._confirm_entry_fill(
                        okx_symbol=okx_symbol,
                        order_id=order_id,
                        client_order_id=client_order_id,
                    )
            _logger.error("create_order entry %s failed: %s", okx_symbol, exc)
            raise

    async def place_trailing_stop(
        self,
        *,
        okx_symbol: str,
        is_long: bool,
        contracts: float,
        activation_price: float,
        callback_spread: float,
        algo_client_order_id: str,
    ) -> str | None:
        """Place one reduce-only native OKX price-spread trailing stop."""
        await self._ensure_markets()
        if self._dry_run:
            return None
        method = getattr(self._exchange, "privatePostTradeOrderAlgo", None)
        if method is None:
            raise RuntimeError("ccxt does not expose OKX place algo endpoint")
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        active_px = self._exchange.price_to_precision(ccxt_sym, activation_price)
        spread = self._exchange.price_to_precision(ccxt_sym, callback_spread)
        params = {
            "instId": okx_symbol,
            "tdMode": "isolated",
            "side": "sell" if is_long else "buy",
            "posSide": "long" if is_long else "short",
            "ordType": "move_order_stop",
            "sz": str(contracts),
            "callbackSpread": str(spread),
            "activePx": str(active_px),
            "algoClOrdId": algo_client_order_id,
            "reduceOnly": True,
        }

        async def _call() -> Any:
            return await method(params)

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"place_trailing_stop {okx_symbol}",
            )
        except Exception:
            pending = await self.get_pending_algo_orders(okx_symbol)
            recovered = next(
                (order for order in pending if order.client_order_id == algo_client_order_id),
                None,
            )
            if recovered is not None:
                return recovered.order_id
            raise
        data = response.get("data", []) if isinstance(response, dict) else []
        if not data or not isinstance(data[0], dict):
            raise RuntimeError("OKX returned no trailing algo result")
        if str(data[0].get("sCode", "0")) != "0":
            raise RuntimeError(f"OKX rejected trailing algo: {data[0].get('sMsg', '')}")
        algo_id = str(data[0].get("algoId") or "")
        if not algo_id:
            raise RuntimeError("OKX trailing algo response has no algoId")
        return algo_id

    async def _fetch_order_by_client_id(
        self,
        *,
        okx_symbol: str,
        client_order_id: str,
        strict: bool = False,
    ) -> dict[str, Any] | None:
        method = getattr(self._exchange, "privateGetTradeOrder", None)
        if method is None:
            return None
        try:
            response = await method({"instId": okx_symbol, "clOrdId": client_order_id})
        except Exception as exc:
            if strict:
                raise RuntimeError(
                    f"failed to query OKX order by client ID {client_order_id}"
                ) from exc
            return None
        data = response.get("data", []) if isinstance(response, dict) else []
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return None
        return dict(data[0])

    async def get_order_by_client_id(
        self,
        *,
        okx_symbol: str,
        client_order_id: str,
    ) -> dict[str, Any] | None:
        """Fetch one regular order for deterministic restart recovery."""
        await self._ensure_markets()
        return await self._fetch_order_by_client_id(
            okx_symbol=okx_symbol,
            client_order_id=client_order_id,
            strict=True,
        )

    async def recover_entry_fill(
        self,
        *,
        okx_symbol: str,
        client_order_id: str,
    ) -> EntryOrderResult | None:
        """Return an already-filled entry by client ID without submitting."""
        details = await self.get_order_by_client_id(
            okx_symbol=okx_symbol,
            client_order_id=client_order_id,
        )
        if details is None or details.get("state") not in {
            "filled",
            "canceled",
            "mmp_canceled",
        }:
            return None
        if (_float_or_none(details.get("accFillSz")) or 0.0) <= 0:
            return None
        return _entry_result_from_details(details, fallback_order_id=client_order_id)

    async def recover_close_fill(
        self,
        *,
        okx_symbol: str,
        client_order_id: str,
    ) -> CloseOrderResult | None:
        """Return an already-filled close by client ID without submitting."""
        details = await self.get_order_by_client_id(
            okx_symbol=okx_symbol,
            client_order_id=client_order_id,
        )
        if details is None or details.get("state") not in {
            "filled",
            "canceled",
            "mmp_canceled",
        }:
            return None
        if (_float_or_none(details.get("accFillSz")) or 0.0) <= 0:
            return None
        return _close_result_from_details(details, fallback_order_id=client_order_id)

    async def _confirm_entry_fill(
        self,
        *,
        okx_symbol: str,
        order_id: str,
        client_order_id: str,
    ) -> EntryOrderResult:
        details: dict[str, Any] | None = None
        deadline = asyncio.get_running_loop().time() + _FILL_CONFIRM_TIMEOUT_S
        while asyncio.get_running_loop().time() < deadline:
            details = await self._fetch_order_by_client_id(
                okx_symbol=okx_symbol,
                client_order_id=client_order_id,
            )
            if details is not None and details.get("state") == "filled":
                break
            await asyncio.sleep(_FILL_CONFIRM_POLL_S)
        if details is None or details.get("state") != "filled":
            raise RuntimeError(f"entry order {order_id} was not confirmed filled by OKX")
        return _entry_result_from_details(details, fallback_order_id=order_id)

    async def close_position_at_market(
        self,
        *,
        okx_symbol: str,
        is_long: bool,
        contracts: float,
        client_order_id: str,
    ) -> CloseOrderResult | None:
        """Close a position at market price (TTL exit or manual close)."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        close_side = "sell" if is_long else "buy"
        position_side = "long" if is_long else "short"

        _logger.info(
            "%s Would close %s contracts of %s at market (%s)",
            "[DRY RUN]" if self._dry_run else "[LIVE]",
            _format_contracts(contracts),
            okx_symbol,
            "sell" if is_long else "buy",
        )

        if self._dry_run:
            return None

        async def _call() -> dict[str, Any]:
            return await self._exchange.create_order(  # type: ignore[no-any-return]
                ccxt_sym,
                "market",
                close_side,
                contracts,
                params={
                    "reduceOnly": True,
                    "marginMode": "isolated",
                    "positionSide": position_side,
                    "clientOrderId": client_order_id,
                },
            )

        try:
            order = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"close_position {okx_symbol}",
            )
            order_id = str(order.get("id", ""))
            result = await self._confirm_close_fill(
                okx_symbol=okx_symbol,
                order_id=order_id,
                client_order_id=client_order_id,
            )
            _logger.info("Closed %s contracts of %s", _format_contracts(contracts), okx_symbol)
            return result
        except Exception as exc:
            recovered = await self._fetch_order_by_client_id(
                okx_symbol=okx_symbol,
                client_order_id=client_order_id,
            )
            if recovered is not None:
                order_id = str(recovered.get("ordId") or recovered.get("id") or "")
                if order_id:
                    return await self._confirm_close_fill(
                        okx_symbol=okx_symbol,
                        order_id=order_id,
                        client_order_id=client_order_id,
                    )
            _logger.error("close_position %s failed: %s", okx_symbol, exc)
            raise

    async def _confirm_close_fill(
        self,
        *,
        okx_symbol: str,
        order_id: str,
        client_order_id: str,
    ) -> CloseOrderResult:
        details: dict[str, Any] | None = None
        deadline = asyncio.get_running_loop().time() + _FILL_CONFIRM_TIMEOUT_S
        while asyncio.get_running_loop().time() < deadline:
            details = await self._fetch_order_by_client_id(
                okx_symbol=okx_symbol,
                client_order_id=client_order_id,
            )
            if details is not None and details.get("state") == "filled":
                break
            await asyncio.sleep(_FILL_CONFIRM_POLL_S)
        if details is None or details.get("state") != "filled":
            raise RuntimeError(f"close order {order_id} was not confirmed filled by OKX")
        return _close_result_from_details(details, fallback_order_id=order_id)

    async def cancel_algo_orders(self, okx_symbol: str) -> None:
        """Cancel all open algo (conditional/SL/TP) orders for the symbol.

        Called before TTL exits to prevent OKX from re-opening the position
        after the market close order.
        """
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        _logger.info(
            "%s Would cancel all algo orders for %s",
            "[DRY RUN]" if self._dry_run else "[LIVE]",
            okx_symbol,
        )

        if self._dry_run:
            return

        await self._cancel_pending_algo_orders(okx_symbol)

        async def _fetch() -> list[Any]:
            return await self._exchange.fetch_open_orders(ccxt_sym)  # type: ignore[no-any-return]

        try:
            orders = await retry_with_backoff(
                _fetch,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_open_orders {okx_symbol}",
            )
        except Exception as exc:
            _logger.warning("fetch_open_orders %s failed: %s", okx_symbol, exc)
            return

        algo_orders = [o for o in orders if o.get("type") in ("stop", "stop_market", "conditional")]
        for order in algo_orders:
            oid = order.get("id")
            if not oid:
                continue

            async def _cancel(order_id: str = oid) -> None:
                await self._exchange.cancel_order(order_id, ccxt_sym)

            try:
                await retry_with_backoff(
                    _cancel,
                    max_attempts=self._max_retries,
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    label=f"cancel_order {oid}",
                )
                _logger.debug("Cancelled algo order %s for %s", oid, okx_symbol)
            except Exception as exc:
                _logger.warning("cancel_order %s failed: %s", oid, exc)

    async def cancel_algo_order_for_position(
        self,
        *,
        okx_symbol: str,
        algo_client_order_id: str,
        algo_order_id: str = "",
    ) -> None:
        """Cancel only the attached protection order belonging to one entry."""
        if not algo_client_order_id and not algo_order_id:
            raise RuntimeError(f"position for {okx_symbol} has no attached algo identity")
        if self._dry_run:
            _logger.info(
                "[DRY RUN] Would cancel algo %s for %s",
                algo_client_order_id,
                okx_symbol,
            )
            return
        method = getattr(self._exchange, "privatePostTradeCancelAlgos", None)
        if method is None:
            raise RuntimeError("ccxt does not expose OKX cancel algos endpoint")

        async def _cancel() -> Any:
            try:
                return await method(
                    [
                        {
                            "instId": okx_symbol,
                            **(
                                {"algoClOrdId": algo_client_order_id}
                                if algo_client_order_id
                                else {"algoId": algo_order_id}
                            ),
                        }
                    ]
                )
            except ccxt.OrderNotFound:
                _logger.info(
                    "Algo protection %s for %s is already terminal",
                    algo_client_order_id or algo_order_id,
                    okx_symbol,
                )
                return None

        await retry_with_backoff(
            _cancel,
            max_attempts=self._max_retries,
            base_delay=self._retry_base_delay,
            max_delay=self._retry_max_delay,
            label=f"cancel_algo_order {algo_client_order_id or algo_order_id}",
        )

    async def cancel_regular_order(
        self,
        *,
        okx_symbol: str,
        order_id: str,
    ) -> None:
        """Cancel one regular reduce-only protection order by exchange ID."""
        if not order_id:
            return
        if self._dry_run:
            _logger.info("[DRY RUN] Would cancel order %s for %s", order_id, okx_symbol)
            return
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        async def _cancel() -> Any:
            try:
                return await self._exchange.cancel_order(order_id, ccxt_sym)
            except ccxt.OrderNotFound:
                _logger.info(
                    "Regular protection %s for %s is already terminal",
                    order_id,
                    okx_symbol,
                )
                return None

        await retry_with_backoff(
            _cancel,
            max_attempts=self._max_retries,
            base_delay=self._retry_base_delay,
            max_delay=self._retry_max_delay,
            label=f"cancel_order {order_id}",
        )

    async def _cancel_pending_algo_orders(self, okx_symbol: str) -> None:
        """Best-effort cancellation for OKX pending algo orders."""
        method = getattr(self._exchange, "privatePostTradeCancelAlgos", None)
        if method is None:
            return

        orders = await self.get_pending_algo_orders(okx_symbol)
        for order in orders:
            if not order.order_id:
                continue

            async def _cancel(algo_id: str = order.order_id) -> Any:
                return await method([{"instId": okx_symbol, "algoId": algo_id}])

            try:
                await retry_with_backoff(
                    _cancel,
                    max_attempts=self._max_retries,
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    label=f"cancel_algo_order {order.order_id}",
                )
                _logger.debug("Cancelled pending algo order %s for %s", order.order_id, okx_symbol)
            except Exception as exc:
                _logger.warning("cancel_algo_order %s failed: %s", order.order_id, exc)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._exchange.close()


def _normalize_position(symbol: str, raw: dict[str, Any]) -> ExchangePosition:
    side = raw.get("side")
    contracts = float(raw.get("contracts", 0.0) or raw.get("contractSize", 0.0) or 0.0)
    entry_price = raw.get("entryPrice") or raw.get("entry_price")
    liquidation_price = raw.get("liquidationPrice") or raw.get("liquidation_price")
    unrealized = raw.get("unrealizedPnl") or raw.get("unrealized_pnl")
    leverage = raw.get("leverage")
    margin_mode = raw.get("marginMode") or raw.get("margin_mode")
    return ExchangePosition(
        symbol=symbol,
        contracts=contracts,
        side=str(side) if side is not None else None,
        entry_price=_float_or_none(entry_price),
        liquidation_price=_float_or_none(liquidation_price),
        unrealized_pnl=_float_or_none(unrealized),
        leverage=_float_or_none(leverage),
        margin_mode=str(margin_mode) if margin_mode is not None else None,
        raw=dict(raw),
    )


def _normalize_order(symbol: str, raw: dict[str, Any], *, kind: str) -> ExchangeOrder:
    order_id = raw.get("id") or raw.get("ordId") or raw.get("algoId") or ""
    amount = raw.get("amount") or raw.get("sz")
    price = (
        raw.get("price")
        or raw.get("px")
        or raw.get("triggerPrice")
        or raw.get("slTriggerPx")
        or raw.get("activePx")
    )
    side = raw.get("side")
    client_order_id = raw.get("clientOrderId") or raw.get("clOrdId") or raw.get("algoClOrdId") or ""
    return ExchangeOrder(
        symbol=symbol,
        order_id=str(order_id),
        kind=kind,
        client_order_id=str(client_order_id),
        side=str(side) if side is not None else None,
        amount=_float_or_none(amount),
        price=_float_or_none(price),
        raw=dict(raw),
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _entry_result_from_details(
    details: dict[str, Any],
    *,
    fallback_order_id: str,
) -> EntryOrderResult:
    order_id = str(details.get("ordId") or details.get("id") or fallback_order_id)
    average_price = _float_or_none(details.get("avgPx"))
    filled_contracts = _float_or_none(details.get("accFillSz"))
    if average_price is None or average_price <= 0:
        raise RuntimeError(f"entry order {order_id} has no average fill price")
    if filled_contracts is None or filled_contracts <= 0:
        raise RuntimeError(f"entry order {order_id} has no filled size")
    return EntryOrderResult(
        order_id=order_id,
        average_price=average_price,
        filled_contracts=filled_contracts,
        fee=abs(_float_or_none(details.get("fee")) or 0.0),
    )


def _close_result_from_details(
    details: dict[str, Any],
    *,
    fallback_order_id: str,
) -> CloseOrderResult:
    entry = _entry_result_from_details(details, fallback_order_id=fallback_order_id)
    return CloseOrderResult(
        order_id=entry.order_id,
        average_price=entry.average_price,
        filled_contracts=entry.filled_contracts,
        fee=entry.fee,
    )


def _fill_identity(fill: dict[str, Any]) -> str:
    info = fill.get("info")
    raw = info if isinstance(info, dict) else {}
    for value in (
        fill.get("id"),
        raw.get("tradeId"),
        raw.get("fillId"),
    ):
        if value not in (None, ""):
            return f"trade:{value}"
    return "|".join(
        str(value)
        for value in (
            raw.get("ordId") or fill.get("order"),
            fill.get("timestamp"),
            fill.get("side"),
            fill.get("price"),
            fill.get("amount"),
            raw.get("fillIdxPx"),
        )
    )


def _okx_cash_balance(balance: dict[str, Any]) -> float | None:
    info = balance.get("info")
    if not isinstance(info, dict):
        return None
    data = info.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return None
    details = data[0].get("details")
    if not isinstance(details, list):
        return None
    for detail in details:
        if isinstance(detail, dict) and detail.get("ccy") == "USDT":
            return _float_or_none(detail.get("cashBal"))
    return None


def _market_amount_step(market: dict[str, Any]) -> float:
    precision = market.get("precision") or {}
    amount_precision = precision.get("amount")
    if amount_precision:
        return float(amount_precision)
    info = market.get("info") or {}
    lot_size = info.get("lotSz")
    if lot_size:
        return float(lot_size)
    return 1.0


def _market_min_amount(market: dict[str, Any], default: float) -> float:
    limits = market.get("limits") or {}
    amount_limits = limits.get("amount") or {}
    min_amount = amount_limits.get("min")
    if min_amount:
        return float(min_amount)
    info = market.get("info") or {}
    min_size = info.get("minSz")
    if min_size:
        return float(min_size)
    return default


def _trim_float(value: float) -> float:
    return float(f"{value:.12g}")


def _format_contracts(value: float) -> str:
    return f"{value:.12g}"
