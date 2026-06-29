"""OKXTradingClient — wraps ccxt OKX for live order placement.

All order placement paths accept a `dry_run` flag. When True, methods log
what they would do but make no API calls and return None for order IDs.

OKX symbol mapping:
  project format:  SOL-USDT-SWAP
  ccxt unified:    SOL/USDT:USDT
The client performs this conversion via `exchange.load_markets()`.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import ccxt.async_support as ccxt

from crypt.execution.exchange_sync import (
    ExchangeBalance,
    ExchangeOrder,
    ExchangePosition,
    ExchangeSnapshot,
)
from crypt.utils.retry import retry_with_backoff

_logger = logging.getLogger(__name__)
_OKX_PENDING_ALGO_ORD_TYPES = ("conditional", "oco", "trigger", "move_order_stop")


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
            _logger.warning("fetch_balance failed: %s", exc)
            return ExchangeBalance(total=0.0, free=0.0, used=0.0)

        usdt = balance.get("USDT", {})
        free = float(usdt.get("free", 0.0) or 0.0)
        total = float(usdt.get("total", 0.0) or 0.0)
        used = float(usdt.get("used", 0.0) or 0.0)
        return ExchangeBalance(total=total if total > 0 else free + used, free=free, used=used)

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
            _logger.warning("fetch_positions %s failed: %s", okx_symbol, exc)
            return []

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
            _logger.warning("fetch_position_mode failed: %s", exc)
            return False
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
            _logger.warning("fetch_open_orders %s failed: %s", okx_symbol, exc)
            return []
        return [_normalize_order(okx_symbol, order, kind="regular") for order in orders]

    async def get_pending_algo_orders(self, okx_symbol: str) -> list[ExchangeOrder]:
        """Return pending OKX algo orders when ccxt exposes the raw endpoint."""
        await self._ensure_markets()
        method = getattr(self._exchange, "privateGetTradeOrdersAlgoPending", None)
        if method is None:
            return []

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
                _logger.warning(
                    "orders-algo-pending %s ordType=%s failed: %s",
                    okx_symbol,
                    ord_type,
                    exc,
                )
                continue

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
            _logger.warning("fetch_my_trades %s failed: %s", okx_symbol, exc)
            return []
        return [dict(item) for item in fills]

    async def get_contract_size(self, okx_symbol: str) -> float:
        """Return the contract size for the symbol (e.g. 1.0 SOL per contract)."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        market = self._exchange.market(ccxt_sym)
        return float(market.get("contractSize", 1.0) or 1.0)

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

    async def set_isolated_leverage(self, okx_symbol: str, leverage: int) -> None:
        """Set isolated margin leverage for the symbol.

        Must be called before placing entry orders (OKX requirement).
        In OKX long/short position mode isolated leverage is side-specific, so
        live execution sets both sides before opening Core4 portfolio entries.
        """
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        if self._dry_run:
            _logger.info(
                "[DRY RUN] Would set isolated leverage %dx for %s", leverage, okx_symbol
            )
            return

        async def _call(pos_side: str) -> None:
            await self._exchange.set_leverage(
                leverage,
                ccxt_sym,
                {"marginMode": "isolated", "posSide": pos_side},
            )

        async def _call_long() -> None:
            await _call("long")

        async def _call_short() -> None:
            await _call("short")

        try:
            for pos_side, call in (("long", _call_long), ("short", _call_short)):
                await retry_with_backoff(
                    call,
                    max_attempts=self._max_retries,
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    label=f"set_leverage {okx_symbol} {pos_side}",
                )
            _logger.info("Leverage set to %dx (isolated) for %s", leverage, okx_symbol)
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
    ) -> str | None:
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

        order_params: dict[str, Any] = {
            "marginMode": "isolated",
            "positionSide": position_side,
            "stopLoss": {
                "triggerPrice": sl_precision,
                "type": "market",
                "triggerPriceType": "last",
            },
            "takeProfit": {
                "triggerPrice": tp_precision,
                "price": tp_precision,
                "type": "limit",
                "triggerPriceType": "last",
            },
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
            return order_id
        except Exception as exc:
            _logger.error("create_order entry %s failed: %s", okx_symbol, exc)
            raise

    async def close_position_at_market(
        self,
        *,
        okx_symbol: str,
        is_long: bool,
        contracts: float,
    ) -> None:
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
            return

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
                },
            )

        try:
            await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"close_position {okx_symbol}",
            )
            _logger.info(
                "Closed %s contracts of %s", _format_contracts(contracts), okx_symbol
            )
        except Exception as exc:
            _logger.error("close_position %s failed: %s", okx_symbol, exc)
            raise

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
    unrealized = raw.get("unrealizedPnl") or raw.get("unrealized_pnl")
    return ExchangePosition(
        symbol=symbol,
        contracts=contracts,
        side=str(side) if side is not None else None,
        entry_price=_float_or_none(entry_price),
        unrealized_pnl=_float_or_none(unrealized),
        raw=dict(raw),
    )


def _normalize_order(symbol: str, raw: dict[str, Any], *, kind: str) -> ExchangeOrder:
    order_id = raw.get("id") or raw.get("ordId") or raw.get("algoId") or ""
    amount = raw.get("amount") or raw.get("sz")
    price = raw.get("price") or raw.get("px") or raw.get("triggerPrice") or raw.get("slTriggerPx")
    side = raw.get("side")
    return ExchangeOrder(
        symbol=symbol,
        order_id=str(order_id),
        kind=kind,
        side=str(side) if side is not None else None,
        amount=_float_or_none(amount),
        price=_float_or_none(price),
        raw=dict(raw),
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


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
