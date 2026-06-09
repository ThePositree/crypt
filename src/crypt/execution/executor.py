"""LiveExecutionManager — H1-tick orchestrator for M4 auto-execution.

Called once per H1 close for each configured symbol. The manager:
  1. Refreshes Parquet candles from OKX.
  2. Checks for TTL-expired open positions and closes them.
  3. Reconciles OKX positions against the state file (detects SL/TP fills).
  4. If no position is open for this symbol, checks for a new signal.
  5. If signal found: sizes position, sets leverage, places entry order.
  6. Persists updated state.

All state mutations go through `position_state.save_state()` at the end
of each tick. Startup reconciliation is in `reconcile()`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from crypt.config import Settings
from crypt.exchange.okx import OKXClient
from crypt.execution.okx_order_client import OKXTradingClient
from crypt.execution.position_state import (
    LivePosition,
    load_state,
    save_state,
)
from crypt.execution.risk_calculator import LiveRiskCalculator
from crypt.execution.settings import ExecutionSettings
from crypt.execution.signal_runner import LiveSignalRunner, SignalRow

logger = logging.getLogger(__name__)


class LiveExecutionManager:
    """
    Orchestrates signal generation, risk sizing, and order placement.

    Parameters
    ----------
    exec_settings : ExecutionSettings
        Execution-specific configuration.
    app_settings : Settings
        Main application settings (OKX credentials, data_dir, etc.).
    """

    def __init__(
        self,
        exec_settings: ExecutionSettings,
        app_settings: Settings,
    ) -> None:
        self._settings = exec_settings
        self._app_settings = app_settings

        # Build the shared OKXClient (public data)
        self._okx_data_client = OKXClient(
            api_key=app_settings.okx_api_key,
            api_secret=app_settings.okx_api_secret,
            api_passphrase=app_settings.okx_api_passphrase,
        )

        # Build the trading client
        self._trading_client = OKXTradingClient(
            api_key=app_settings.okx_api_key,
            api_secret=app_settings.okx_api_secret,
            api_passphrase=app_settings.okx_api_passphrase,
            dry_run=exec_settings.dry_run,
        )

        self._signal_runner = LiveSignalRunner(
            strategy_config_path=exec_settings.strategy_config,
            data_dir=exec_settings.data_dir,
            okx_client=self._okx_data_client,
        )

        self._risk_calc = LiveRiskCalculator(exec_settings)
        self._state = load_state(exec_settings.state_path)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def reconcile(self) -> None:
        """
        On startup: sync local state with OKX positions.

        Positions that are in the state file but absent on OKX are treated
        as externally closed (SL/TP filled or manually closed).
        """
        if not self._app_settings.okx_is_authenticated:
            logger.warning(
                "OKX credentials not set — reconcile skipped (dry_run or misconfigured)"
            )
            return

        remaining: list[LivePosition] = []
        for pos in self._state.positions:
            if pos.status != "open":
                remaining.append(pos)
                continue

            okx_positions = await self._trading_client.get_open_positions(pos.symbol)
            has_okx = any(
                abs(float(p.get("contracts", 0) or 0)) > 0 for p in okx_positions
            )
            if has_okx:
                remaining.append(pos)
                logger.info("Reconcile: position %s for %s is still open on OKX", pos.position_id[:8], pos.symbol)
            else:
                logger.info(
                    "Reconcile: position %s for %s not found on OKX — marking closed",
                    pos.position_id[:8],
                    pos.symbol,
                )

        self._state.positions = remaining
        save_state(self._state, self._settings.state_path)

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    async def on_h1_close(self, symbol: str) -> None:
        """
        Called on each H1 bar close for the given symbol.

        Entry point for the H1 scheduler job.
        """
        if not self._settings.enabled:
            return

        logger.debug("H1 tick for %s at %s", symbol, datetime.now(UTC).isoformat())

        # 1. Refresh candle data
        await self._signal_runner.refresh_candles(symbol)

        # 2. Manage open positions (TTL + fill detection)
        await self._manage_open_positions(symbol)

        # 3. Check for new signal if no open position for this symbol
        open_for_symbol = self._state.open_positions_for(symbol)
        if len(open_for_symbol) >= self._settings.max_positions:
            logger.debug(
                "Max positions (%d) reached for %s — skipping signal check",
                self._settings.max_positions,
                symbol,
            )
            save_state(self._state, self._settings.state_path)
            return

        # `get_latest_signal` runs crypt_ensemble.generate() which is CPU-bound
        # and may take several minutes for a full year of H1 data.
        # Run in a thread pool to avoid blocking the asyncio event loop.
        loop = asyncio.get_event_loop()
        signal_row = await loop.run_in_executor(
            None, self._signal_runner.get_latest_signal, symbol
        )
        if signal_row is not None:
            await self._try_open_position(symbol, signal_row)

        save_state(self._state, self._settings.state_path)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    async def _manage_open_positions(self, symbol: str) -> None:
        """Check TTL and OKX fill status for all open positions of this symbol."""
        now = datetime.now(UTC)

        for pos in list(self._state.positions):
            if pos.symbol != symbol or pos.status != "open":
                continue

            # TTL check (wall-clock based, mirrors bar-count TTL in simulator)
            ttl_expiry = pos.entry_dt + timedelta(hours=pos.ttl_bars)
            if now >= ttl_expiry:
                logger.info(
                    "TTL expired for position %s (%s) — closing at market",
                    pos.position_id[:8],
                    symbol,
                )
                await self._close_ttl(pos)
                continue

            # SL/TP fill detection: check OKX position
            if self._app_settings.okx_is_authenticated:
                okx_positions = await self._trading_client.get_open_positions(symbol)
                has_okx = any(
                    abs(float(p.get("contracts", 0) or 0)) > 0 for p in okx_positions
                )
                if not has_okx:
                    logger.info(
                        "Position %s for %s was closed by SL/TP on OKX",
                        pos.position_id[:8],
                        symbol,
                    )
                    pos.status = "closed"

    async def _close_ttl(self, pos: LivePosition) -> None:
        """Cancel algo orders and close the position at market (TTL exit)."""
        try:
            await self._trading_client.cancel_algo_orders(pos.symbol)
            await self._trading_client.close_position_at_market(
                okx_symbol=pos.symbol,
                is_long=pos.is_long,
                contracts=pos.contracts,
            )
            pos.status = "closed"
            logger.info(
                "TTL close executed for position %s (%s)",
                pos.position_id[:8],
                pos.symbol,
            )
        except Exception:
            logger.exception(
                "Failed to close TTL position %s (%s) — will retry next tick",
                pos.position_id[:8],
                pos.symbol,
            )
            pos.status = "closing"

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------

    async def _try_open_position(self, symbol: str, signal_row: SignalRow) -> None:
        """Size the position and place the entry order."""

        # Capital and balance
        if self._app_settings.okx_is_authenticated:
            capital = await self._trading_client.get_usdt_balance()
        else:
            capital = self._state.monthly_risk_base or 10_000.0

        if capital <= 0:
            logger.warning("Zero capital reported for %s — skipping entry", symbol)
            return

        # Circuit breaker: skip if too much capital is already locked
        all_open = self._state.all_open_positions()
        total_locked = sum(p.locked_margin for p in all_open)
        if capital > 0 and (total_locked / capital) * 100 >= self._settings.max_capital_risk_pct:
            logger.warning(
                "Circuit breaker: %.1f%% capital locked (limit %.1f%%) — skipping entry",
                (total_locked / capital) * 100,
                self._settings.max_capital_risk_pct,
            )
            return

        # Monthly risk base
        entry_time = datetime.now(UTC)
        risk_base = self._risk_calc.update_monthly_risk_base(
            self._state, entry_time, capital
        )

        # Risk calculation — use signal bar's close as the entry price proxy
        # (the backtester uses next bar's open; close is the closest approximation
        # available before the fill)
        entry_price_estimate = signal_row.bar_close if signal_row.bar_close > 0 else _fallback_entry_price(signal_row)
        open_for_symbol = self._state.open_positions_for(symbol)
        decision = self._risk_calc.calculate(
            signal=signal_row.signal,
            sl_price=signal_row.sl_price,
            entry_price=entry_price_estimate,
            capital=capital,
            risk_base_capital=risk_base,
            open_positions=open_for_symbol,
        )
        if decision is None:
            logger.debug("Risk calculator rejected entry for %s", symbol)
            return

        rr = decision.risk_result

        # Set leverage and place order
        leverage = int(self._settings.max_leverage)
        try:
            await self._trading_client.set_isolated_leverage(symbol, leverage)
        except Exception:
            logger.exception("Failed to set leverage for %s — aborting entry", symbol)
            return

        contract_size = await self._trading_client.get_contract_size(symbol)
        contracts = int(rr.size // contract_size)
        if contracts < 1:
            logger.info(
                "Position size %.4f < 1 contract for %s (contract_size=%.4f) — skipping",
                rr.size,
                symbol,
                contract_size,
            )
            return

        try:
            order_id = await self._trading_client.open_position(
                okx_symbol=symbol,
                is_long=rr.is_long,
                size_asset_units=rr.size,
                sl_price=rr.sl_price,
                tp_price=rr.tp_price,
            )
        except Exception:
            logger.exception("open_position failed for %s — entry aborted", symbol)
            return

        # Record position in state
        new_pos = LivePosition.create(
            symbol=symbol,
            signal_time=signal_row.bar_time,
            entry_time=entry_time,
            entry_price=entry_price_estimate,
            sl_price=rr.sl_price,
            tp_price=rr.tp_price,
            size=rr.size,
            contracts=contracts,
            leverage=float(leverage),
            locked_margin=rr.locked_margin,
            risk_base_capital=risk_base,
            is_long=rr.is_long,
            ttl_bars=self._settings.ttl_bars,
            entry_order_id=order_id,
        )
        self._state.positions.append(new_pos)

        logger.info(
            "Position opened: %s %s %d contracts SL=%.4f TP=%.4f margin=%.2f%s",
            "LONG" if rr.is_long else "SHORT",
            symbol,
            contracts,
            rr.sl_price,
            rr.tp_price,
            rr.locked_margin,
            " [DRY RUN]" if self._settings.dry_run else "",
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Persist state and close exchange connections."""
        save_state(self._state, self._settings.state_path)
        await self._okx_data_client.close()
        await self._trading_client.close()


def _fallback_entry_price(signal_row: SignalRow) -> float:
    """
    Last-resort entry price estimate when bar_close is not available.
    Uses sl_price plus a 2% buffer, which gives a conservative (slightly
    oversized) position — safer than undersizing the risk guard.
    """
    return signal_row.sl_price * 1.02 if signal_row.signal == 1 else signal_row.sl_price * 0.98
