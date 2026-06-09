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

from crypt.utils.retry import retry_with_backoff

_logger = logging.getLogger(__name__)


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
            return 0.0

        usdt = balance.get("USDT", {})
        free = float(usdt.get("free", 0.0) or 0.0)
        total = float(usdt.get("total", 0.0) or 0.0)
        # Use total (equity) for risk sizing — mirrors how the backtester
        # uses unrealized PnL in capital tracking.
        return total if total > 0 else free

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

    async def get_contract_size(self, okx_symbol: str) -> float:
        """Return the contract size for the symbol (e.g. 1.0 SOL per contract)."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        market = self._exchange.market(ccxt_sym)
        return float(market.get("contractSize", 1.0) or 1.0)

    # ------------------------------------------------------------------
    # Write methods (no-ops in dry_run mode)
    # ------------------------------------------------------------------

    async def set_isolated_leverage(self, okx_symbol: str, leverage: int) -> None:
        """Set isolated margin leverage for the symbol.

        Must be called before placing entry orders (OKX requirement).
        """
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)

        if self._dry_run:
            _logger.info(
                "[DRY RUN] Would set isolated leverage %dx for %s", leverage, okx_symbol
            )
            return

        async def _call() -> None:
            await self._exchange.set_leverage(
                leverage, ccxt_sym, {"mgnMode": "isolated"}
            )

        try:
            await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"set_leverage {okx_symbol}",
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

        contracts = math.floor(size_asset_units / contract_size)
        if contracts < 1:
            _logger.warning(
                "Position size %.4f %s is less than 1 contract (contract_size=%.4f) — skipping",
                size_asset_units,
                okx_symbol,
                contract_size,
            )
            return None

        side = "buy" if is_long else "sell"

        sl_precision = float(self._exchange.price_to_precision(ccxt_sym, sl_price))
        tp_precision = float(self._exchange.price_to_precision(ccxt_sym, tp_price))

        order_params: dict[str, Any] = {
            "stopLoss": {"triggerPrice": sl_precision},
            "takeProfit": {"triggerPrice": tp_precision},
        }

        _logger.info(
            "%s Would open %s %d contracts of %s @ market | SL=%.4f TP=%.4f",
            "[DRY RUN]" if self._dry_run else "[LIVE]",
            "LONG" if is_long else "SHORT",
            contracts,
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
                "Entry order placed for %s: id=%s %d contracts %s SL=%.4f TP=%.4f",
                okx_symbol,
                order_id,
                contracts,
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
        contracts: int,
    ) -> None:
        """Close a position at market price (TTL exit or manual close)."""
        await self._ensure_markets()
        ccxt_sym = self._ccxt_symbol(okx_symbol)
        close_side = "sell" if is_long else "buy"

        _logger.info(
            "%s Would close %d contracts of %s at market (%s)",
            "[DRY RUN]" if self._dry_run else "[LIVE]",
            contracts,
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
                params={"reduceOnly": True},
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
                "Closed %d contracts of %s at market", contracts, okx_symbol
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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._exchange.close()
