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
from crypt.execution.exchange_sync import (
    ExchangeSnapshot,
    reconcile_exchange_snapshot,
)
from crypt.execution.fill_classifier import (
    apply_closed_position_fill,
    classify_closed_position_from_fills,
)
from crypt.execution.notifications import ExecutionTelegramNotifier
from crypt.execution.okx_order_client import OKXTradingClient
from crypt.execution.position_state import (
    LivePosition,
    load_state,
    save_state,
)
from crypt.execution.risk_calculator import LiveRiskCalculator
from crypt.execution.settings import ExecutionSettings
from crypt.execution.signal_runner import LiveSignalRunner, SignalBatch, SignalEvent

logger = logging.getLogger(__name__)

_BACKTEST_ARG_TO_SETTING = {
    "exit_geometry": "exit_geometry",
    "tp_move_pct": "tp_move_pct",
    "structural_sl_mode": "structural_sl_mode",
    "min_tp_move_pct": "min_tp_move_pct",
    "risk_base_period": "risk_base_period",
    "ttl": "ttl_bars",
    "rrr": "rrr",
    "risk_percent": "risk_percent",
    "trail_activation_rrr": "trail_activation_rrr",
    "trail_distance_atr": "trail_distance_atr",
    "max_positions": "max_positions",
    "max_allowed_margin": "max_allowed_margin",
    "max_allowed_leverage": "max_leverage",
}


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
        _validate_execution_settings_match_strategy(exec_settings)
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
        self._notifier = ExecutionTelegramNotifier.from_settings(
            app_settings,
            dry_run=exec_settings.dry_run,
        )

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

        snapshot = await self._exchange_snapshot(self._settings.symbols)
        self._apply_exchange_sync(snapshot=snapshot, log_summary=False)
        remaining: list[LivePosition] = []
        for pos in self._state.positions:
            if pos.status != "open":
                remaining.append(pos)
                continue

            exchange_count = len([p for p in snapshot.positions if p.symbol == pos.symbol])
            if exchange_count:
                remaining.append(pos)
                logger.info("Reconcile: position %s for %s is still open on OKX", pos.position_id[:8], pos.symbol)
            else:
                logger.info(
                    "Reconcile: position %s for %s not found on OKX — marking closed",
                    pos.position_id[:8],
                    pos.symbol,
                )
                close_fill = classify_closed_position_from_fills(
                    pos=pos,
                    fills=snapshot.recent_fills,
                )
                apply_closed_position_fill(pos, close_fill)
                remaining.append(pos)
                await self._notify_position_closed(pos)

        self._state.positions = remaining
        self._apply_exchange_sync(snapshot=snapshot, log_summary=True)
        await self._notify_daily_sync_if_due(snapshot)
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

        tick_started_at = datetime.now(UTC)
        logger.info("Execution H1 tick started for %s at %s", symbol, tick_started_at.isoformat())

        # 1. Refresh candle data
        await self._signal_runner.refresh_candles(symbol)

        # 2. Full exchange sync before trusting local state.
        snapshot = await self._exchange_snapshot(self._settings.symbols)
        sync_ok = self._apply_exchange_sync(snapshot=snapshot, log_summary=False)

        # 3. Manage open positions (TTL + fill detection)
        await self._manage_open_positions(symbol, snapshot=snapshot)
        sync_ok = self._apply_exchange_sync(snapshot=snapshot, log_summary=True)
        await self._notify_daily_sync_if_due(snapshot)

        if self._settings.require_exchange_sync and not sync_ok:
            logger.error(
                "Exchange sync is not clean — skipping new entries for %s: %s",
                symbol,
                self._state.last_exchange_sync_errors,
            )
            save_state(self._state, self._settings.state_path)
            return

        # 4. Check for new signal if the backtester-compatible cap allows it.
        open_for_symbol = self._state.open_positions_for(symbol)
        if self._settings.max_positions > 0 and len(open_for_symbol) >= self._settings.max_positions:
            logger.info(
                "Max positions (%d) reached for %s — skipping signal check",
                self._settings.max_positions,
                symbol,
            )
            save_state(self._state, self._settings.state_path)
            return

        # `get_latest_signal_batch` runs strategy.generate() which is CPU-bound
        # and may take several minutes for a full year of H1 data.
        # Run in a thread pool to avoid blocking the asyncio event loop.
        loop = asyncio.get_event_loop()
        signal_batch = await loop.run_in_executor(
            None, self._signal_runner.get_latest_signal_batch, symbol
        )
        if signal_batch is not None:
            await self._try_open_signal_batch(symbol, signal_batch, snapshot)
        else:
            logger.info("No Core4 entry events for %s on the latest closed H1 bar", symbol)

        save_state(self._state, self._settings.state_path)
        elapsed = (datetime.now(UTC) - tick_started_at).total_seconds()
        logger.info(
            "Execution H1 tick complete for %s in %.1fs | open_positions=%d sync_ok=%s",
            symbol,
            elapsed,
            len(self._state.all_open_positions()),
            self._state.last_exchange_sync_ok,
        )

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    async def _manage_open_positions(self, symbol: str, snapshot: ExchangeSnapshot) -> None:
        """Check TTL and OKX fill status for all open positions of this symbol."""
        now = datetime.now(UTC)
        exchange_symbols = {pos.symbol for pos in snapshot.positions}

        for pos in list(self._state.positions):
            if pos.symbol != symbol or pos.status != "open":
                continue

            # TTL check (wall-clock based, mirrors bar-count TTL in simulator)
            ttl_expiry = pos.entry_dt + timedelta(hours=pos.ttl_bars)
            if pos.ttl_bars > 0 and now >= ttl_expiry:
                logger.info(
                    "TTL expired for position %s (%s) — closing at market",
                    pos.position_id[:8],
                    symbol,
                )
                await self._close_ttl(pos)
                continue

            # SL/TP fill detection: check OKX position
            if self._app_settings.okx_is_authenticated and symbol not in exchange_symbols:
                close_fill = classify_closed_position_from_fills(
                    pos=pos,
                    fills=snapshot.recent_fills,
                )
                logger.info(
                    "Position %s for %s was closed on OKX: reason=%s exit_price=%s pnl=%s",
                    pos.position_id[:8],
                    symbol,
                    close_fill.exit_reason,
                    close_fill.exit_price,
                    close_fill.realized_pnl,
                )
                apply_closed_position_fill(pos, close_fill)
                await self._notify_position_closed(pos)

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
            pos.exit_time = datetime.now(UTC).isoformat()
            pos.exit_reason = "ttl_expired"
            logger.info(
                "TTL close executed for position %s (%s)",
                pos.position_id[:8],
                pos.symbol,
            )
            await self._notify_position_closed(pos)
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

    async def _try_open_signal_batch(
        self,
        symbol: str,
        signal_batch: SignalBatch,
        snapshot: ExchangeSnapshot,
    ) -> None:
        """Process same-bar events in backtester order."""
        # Capital and balance
        if self._settings.dry_run and self._settings.dry_run_capital > 0:
            capital = self._settings.dry_run_capital
            logger.info(
                "Dry-run sizing uses override capital %.2f; real OKX balance_total=%.2f free=%.2f",
                capital,
                snapshot.balance.total,
                snapshot.balance.free,
            )
        elif self._app_settings.okx_is_authenticated:
            capital = snapshot.balance.total if snapshot.balance.total > 0 else snapshot.balance.free
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
        entry_time = signal_batch.next_time
        risk_base = self._risk_calc.update_monthly_risk_base(
            self._state, entry_time, capital
        )

        for event in signal_batch.events:
            await self._try_open_event(
                symbol=symbol,
                event=event,
                entry_time=entry_time,
                entry_price=signal_batch.next_open,
                capital=capital,
                risk_base=risk_base,
            )
        if self._app_settings.okx_is_authenticated:
            post_entry_snapshot = await self._exchange_snapshot(self._settings.symbols)
            self._apply_exchange_sync(snapshot=post_entry_snapshot, log_summary=True)

    async def _try_open_event(
        self,
        *,
        symbol: str,
        event: SignalEvent,
        entry_time: datetime,
        entry_price: float,
        capital: float,
        risk_base: float,
    ) -> None:
        """Size one Core v4 signal event and place the entry order."""
        open_positions = self._state.all_open_positions()
        decision = self._risk_calc.calculate(
            signal=event.signal,
            sl_price=event.sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=risk_base,
            open_positions=open_positions,
            risk_percent=event.risk_percent,
            rrr=event.rrr,
            exit_geometry=event.exit_geometry,
            tp_move_pct=event.tp_move_pct,
            structural_sl_mode=event.structural_sl_mode,
            min_tp_move_pct=event.min_tp_move_pct,
        )
        if decision is None:
            logger.debug("Risk calculator rejected entry for %s", symbol)
            return

        rr = decision.risk_result
        if event.drain_on_group_change and open_positions:
            active_groups = {position.position_group for position in open_positions}
            if event.position_group not in active_groups:
                logger.debug(
                    "Drain-on-group-change rejected %s event for group %s; active groups=%s",
                    symbol,
                    event.position_group,
                    sorted(active_groups),
                )
                return

        contracts = await self._trading_client.size_asset_units_to_contracts(symbol, rr.size)
        if contracts <= 0:
            contract_size = await self._trading_client.get_contract_size(symbol)
            logger.info(
                "Position size %.4f is below exchange min amount for %s (contract_size=%.4f) — skipping",
                rr.size,
                symbol,
                contract_size,
            )
            return

        # Set leverage and place order
        leverage = int(rr.required_leverage)
        try:
            await self._trading_client.set_isolated_leverage(symbol, leverage)
        except Exception:
            logger.exception("Failed to set leverage for %s — aborting entry", symbol)
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
            signal_time=event.bar_time,
            entry_time=entry_time,
            entry_price=entry_price,
            sl_price=rr.sl_price,
            tp_price=rr.tp_price,
            size=rr.size,
            contracts=contracts,
            leverage=float(leverage),
            locked_margin=rr.locked_margin,
            risk_base_capital=risk_base,
            is_long=rr.is_long,
            ttl_bars=event.position_ttl_bars
            if event.position_ttl_bars is not None
            else self._settings.ttl_bars,
            entry_order_id=order_id,
            selected_strategy=event.selected_strategy,
            position_group=event.position_group,
            signal_event=_jsonable_event(event.raw_event),
            trail_activation_rrr=event.trail_activation_rrr or 0.0,
            trail_distance_atr=event.trail_distance_atr or 0.0,
        )
        self._state.positions.append(new_pos)
        await self._notify_entry_opened(new_pos)

        logger.info(
            "Position opened: %s %s %d contracts SL=%.4f TP=%.4f margin=%.2f strategy=%s%s",
            "LONG" if rr.is_long else "SHORT",
            symbol,
            contracts,
            rr.sl_price,
            rr.tp_price,
            rr.locked_margin,
            event.selected_strategy,
            " [DRY RUN]" if self._settings.dry_run else "",
        )

    async def _exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:
        if not self._app_settings.okx_is_authenticated:
            return ExchangeSnapshot.empty_dry_run(
                balance=self._state.monthly_risk_base or 10_000.0
            )
        return await self._trading_client.get_exchange_snapshot(symbols)

    def _apply_exchange_sync(self, *, snapshot: ExchangeSnapshot, log_summary: bool = True) -> bool:
        report = reconcile_exchange_snapshot(
            state=self._state,
            snapshot=snapshot,
            symbols=self._settings.symbols,
        )
        self._state.last_exchange_sync_at = report.fetched_at.isoformat()
        self._state.last_exchange_sync_ok = report.synced
        self._state.last_exchange_sync_errors = report.blocking_reasons
        for pos in self._state.all_open_positions():
            pos.last_sync_at = report.fetched_at.isoformat()
            pos.last_sync_status = "ok" if report.synced else "blocked"
        if not log_summary:
            return report.synced
        if report.synced:
            logger.info(
                "Exchange sync OK: balance_total=%.2f free=%.2f positions=%d orders=%d algo_orders=%d hedged=%s",
                snapshot.balance.total,
                snapshot.balance.free,
                len(snapshot.positions),
                len(snapshot.open_orders),
                len(snapshot.algo_orders),
                snapshot.position_mode_hedged,
            )
        else:
            logger.error(
                "Exchange sync blocked: reasons=%s balance_total=%.2f free=%.2f positions=%d orders=%d algo_orders=%d hedged=%s",
                report.blocking_reasons,
                snapshot.balance.total,
                snapshot.balance.free,
                len(snapshot.positions),
                len(snapshot.open_orders),
                len(snapshot.algo_orders),
                snapshot.position_mode_hedged,
            )
        return report.synced

    async def _notify_daily_sync_if_due(self, snapshot: ExchangeSnapshot) -> None:
        notifier = getattr(self, "_notifier", None)
        if notifier is None:
            return
        report_date = snapshot.fetched_at.date().isoformat()
        if self._state.last_daily_sync_report_date == report_date:
            return
        await notifier.send_daily_sync_report(snapshot=snapshot, state=self._state)
        self._state.last_daily_sync_report_date = report_date

    async def _notify_entry_opened(self, pos: LivePosition) -> None:
        notifier = getattr(self, "_notifier", None)
        if notifier is not None:
            await notifier.send_entry_opened(pos)

    async def _notify_position_closed(self, pos: LivePosition) -> None:
        notifier = getattr(self, "_notifier", None)
        if notifier is not None:
            await notifier.send_position_closed(pos)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Persist state and close exchange connections."""
        save_state(self._state, self._settings.state_path)
        await self._okx_data_client.close()
        await self._trading_client.close()
        notifier = getattr(self, "_notifier", None)
        if notifier is not None:
            await notifier.close()


def _jsonable_event(raw: dict[str, object]) -> dict[str, object]:
    """Convert numpy/pandas scalars in event metadata to JSON-safe values."""
    output: dict[str, object] = {}
    for key, value in raw.items():
        if hasattr(value, "item"):
            output[str(key)] = value.item()
        elif isinstance(value, (str, int, float, bool)) or value is None:
            output[str(key)] = value
        else:
            output[str(key)] = str(value)
    return output


def _validate_execution_settings_match_strategy(settings: ExecutionSettings) -> None:
    """Fail fast if live execution settings diverge from strategy backtest args."""
    from backtester.cli_runner import load_strategy_config

    cfg = load_strategy_config(str(settings.strategy_config), logger)
    if cfg is None:
        raise ValueError(f"Invalid strategy config: {settings.strategy_config}")
    backtest_args = cfg.backtest_args or {}
    mismatches: list[str] = []
    for backtest_key, setting_name in _BACKTEST_ARG_TO_SETTING.items():
        if backtest_key not in backtest_args:
            continue
        expected = backtest_args[backtest_key]
        actual = getattr(settings, setting_name)
        if expected is None and actual is None:
            continue
        if isinstance(expected, (int, float)) or isinstance(actual, (int, float)):
            if expected is None or actual is None or abs(float(expected) - float(actual)) > 1e-12:
                mismatches.append(f"{setting_name}: strategy={expected!r} live={actual!r}")
        elif str(expected) != str(actual):
            mismatches.append(f"{setting_name}: strategy={expected!r} live={actual!r}")
    if mismatches:
        details = "; ".join(mismatches)
        raise ValueError(
            "Live execution settings must match strategy backtest_args for parity: "
            f"{details}"
        )
