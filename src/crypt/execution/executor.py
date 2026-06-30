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

from backtester.margin_policy import (
    aggregate_liquidation_is_beyond_stops,
    estimate_linear_liquidation_price,
    leverage_is_within_size_tier,
)
from backtester.trailing_policy import build_native_trailing_geometry
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
    build_event_id,
    load_state,
    save_state,
)
from crypt.execution.risk_calculator import LiveRiskCalculator
from crypt.execution.settings import ExecutionSettings
from crypt.execution.signal_runner import LiveSignalRunner, SignalBatch, SignalEvent
from crypt.runtime.h1_websocket import H1Boundary

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
    "maintenance_margin_rate": "maintenance_margin_rate",
    "liquidation_fee_rate": "liquidation_fee_rate",
    "liquidation_buffer_pct": "liquidation_buffer_pct",
    "maintenance_margin_tier_schedule": "maintenance_margin_tier_schedule",
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
            logger.warning("OKX credentials not set — reconcile skipped (dry_run or misconfigured)")
            await self.notify_execution_error(
                context="startup reconciliation",
                error="OKX credentials are not configured; real account sync was skipped",
            )
            return

        snapshot = await self._exchange_snapshot(self._settings.symbols)
        self._apply_exchange_sync(snapshot=snapshot, log_summary=False)
        remaining: list[LivePosition] = []
        for pos in self._state.positions:
            if pos.status != "open":
                remaining.append(pos)
                continue

            close_fill = classify_closed_position_from_fills(
                pos=pos,
                fills=snapshot.recent_fills,
            )
            exact_close_detected = bool(
                (pos.algo_client_order_id or pos.close_client_order_id)
                and close_fill.exit_price is not None
                and close_fill.filled_contracts + 1e-8 >= pos.contracts
            )
            exchange_side_open = any(
                exchange_pos.symbol == pos.symbol
                and exchange_pos.side == ("long" if pos.is_long else "short")
                for exchange_pos in snapshot.positions
            )
            if exchange_side_open and not exact_close_detected:
                remaining.append(pos)
                logger.info(
                    "Reconcile: position %s for %s is still open on OKX",
                    pos.position_id[:8],
                    pos.symbol,
                )
            else:
                logger.info(
                    "Reconcile: position %s for %s not found on OKX — marking closed",
                    pos.position_id[:8],
                    pos.symbol,
                )
                apply_closed_position_fill(pos, close_fill)
                await self._cancel_remaining_protection(pos, snapshot)
                remaining.append(pos)
                await self._notify_position_closed(pos)

        self._state.positions = remaining
        sync_ok = self._apply_exchange_sync(snapshot=snapshot, log_summary=True)
        await self._notify_sync_blocker(sync_ok)
        await self._notify_daily_sync_if_due(snapshot)
        save_state(self._state, self._settings.state_path)

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    async def on_h1_close(
        self,
        symbol: str,
        websocket_boundary: H1Boundary | None = None,
        trigger_source: str = "manual",
    ) -> None:
        """
        Called on each H1 bar close for the given symbol.

        Entry point for the H1 scheduler job.
        """
        if not self._settings.enabled:
            return

        tick_started_at = datetime.now(UTC)
        logger.info(
            "Execution H1 tick started for %s at %s source=%s",
            symbol,
            tick_started_at.isoformat(),
            trigger_source,
        )

        # 1. Refresh candle data
        if websocket_boundary is None:
            await self._signal_runner.refresh_candles(symbol)
        else:
            await self._signal_runner.refresh_candles(
                symbol,
                websocket_boundary=websocket_boundary,
            )

        # 2. Full exchange sync before trusting local state.
        snapshot = await self._exchange_snapshot(self._settings.symbols)
        sync_ok = self._apply_exchange_sync(snapshot=snapshot, log_summary=False)

        # 3. Manage open positions (TTL + fill detection)
        await self._manage_open_positions(symbol, snapshot=snapshot)
        if self._app_settings.okx_is_authenticated:
            snapshot = await self._exchange_snapshot(self._settings.symbols)
        sync_ok = self._apply_exchange_sync(snapshot=snapshot, log_summary=True)
        await self._notify_sync_blocker(sync_ok)
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
        if (
            self._settings.max_positions > 0
            and len(open_for_symbol) >= self._settings.max_positions
        ):
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

        for pos in list(self._state.positions):
            if pos.symbol != symbol or pos.status != "open":
                continue

            close_fill = classify_closed_position_from_fills(
                pos=pos,
                fills=snapshot.recent_fills,
            )
            exact_close_detected = bool(
                (pos.algo_client_order_id or pos.close_client_order_id)
                and close_fill.exit_price is not None
                and close_fill.filled_contracts + 1e-8 >= pos.contracts
            )
            exchange_side_open = any(
                exchange_pos.symbol == symbol
                and exchange_pos.side == ("long" if pos.is_long else "short")
                for exchange_pos in snapshot.positions
            )
            if self._app_settings.okx_is_authenticated and (
                exact_close_detected or not exchange_side_open
            ):
                logger.info(
                    "Position %s for %s was closed on OKX: reason=%s exit_price=%s pnl=%s",
                    pos.position_id[:8],
                    symbol,
                    close_fill.exit_reason,
                    close_fill.exit_price,
                    close_fill.realized_pnl,
                )
                apply_closed_position_fill(pos, close_fill)
                await self._cancel_remaining_protection(pos, snapshot)
                await self._notify_position_closed(pos)
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

    async def _close_ttl(self, pos: LivePosition) -> None:
        """Cancel algo orders and close the position at market (TTL exit)."""
        try:
            await self._trading_client.cancel_regular_order(
                okx_symbol=pos.symbol,
                order_id=pos.take_profit_order_id,
            )
            if pos.trailing_algo_client_order_id or pos.trailing_algo_order_id:
                await self._trading_client.cancel_algo_order_for_position(
                    okx_symbol=pos.symbol,
                    algo_client_order_id=pos.trailing_algo_client_order_id,
                    algo_order_id=pos.trailing_algo_order_id,
                )
            await self._trading_client.cancel_algo_order_for_position(
                okx_symbol=pos.symbol,
                algo_client_order_id=pos.algo_client_order_id,
                algo_order_id=pos.stop_algo_order_id,
            )
            close_client_order_id = pos.close_client_order_id or f"cx{pos.event_id}"
            pos.close_client_order_id = close_client_order_id
            save_state(self._state, self._settings.state_path)
            close_result = await self._trading_client.close_position_at_market(
                okx_symbol=pos.symbol,
                is_long=pos.is_long,
                contracts=pos.contracts,
                client_order_id=close_client_order_id,
            )
            pos.status = "closed"
            pos.exit_time = datetime.now(UTC).isoformat()
            pos.exit_reason = "ttl_expired"
            if close_result is not None:
                pos.exit_price = close_result.average_price
                pos.exit_fee = close_result.fee
                gross = (
                    (pos.exit_price - pos.entry_price) * pos.size
                    if pos.is_long
                    else (pos.entry_price - pos.exit_price) * pos.size
                )
                pos.realized_pnl = gross - pos.entry_fee - close_result.fee
            logger.info(
                "TTL close executed for position %s (%s)",
                pos.position_id[:8],
                pos.symbol,
            )
            await self._notify_position_closed(pos)
        except Exception as exc:
            logger.exception(
                "Failed to close TTL position %s (%s) — will retry next tick",
                pos.position_id[:8],
                pos.symbol,
            )
            pos.status = "open"
            await self.notify_execution_error(
                context=f"TTL close for {pos.symbol} position={pos.position_id[:8]}",
                error=exc,
            )

    async def _cancel_remaining_protection(
        self,
        pos: LivePosition,
        snapshot: ExchangeSnapshot,
    ) -> None:
        """Cancel still-live sibling protection after any exchange-side exit."""
        regular_ids = {order.order_id for order in snapshot.open_orders}
        algo_ids = {order.order_id for order in snapshot.algo_orders}
        try:
            if pos.take_profit_order_id in regular_ids:
                await self._trading_client.cancel_regular_order(
                    okx_symbol=pos.symbol,
                    order_id=pos.take_profit_order_id,
                )
            for client_id, order_id in (
                (pos.algo_client_order_id, pos.stop_algo_order_id),
                (pos.trailing_algo_client_order_id, pos.trailing_algo_order_id),
            ):
                if order_id and order_id in algo_ids:
                    await self._trading_client.cancel_algo_order_for_position(
                        okx_symbol=pos.symbol,
                        algo_client_order_id=client_id,
                        algo_order_id=order_id,
                    )
        except Exception as exc:
            await self.notify_execution_error(
                context=f"cleanup protection for {pos.symbol} position={pos.position_id[:8]}",
                error=exc,
            )

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
            capital = (
                snapshot.balance.total if snapshot.balance.total > 0 else snapshot.balance.free
            )
        else:
            capital = self._state.monthly_risk_base or 10_000.0

        if capital <= 0:
            logger.warning("Zero capital reported for %s — skipping entry", symbol)
            await self._reject_signal_batch(
                symbol,
                signal_batch,
                reason="OKX reported zero available capital",
            )
            return

        # Circuit breaker: skip if too much capital is already locked
        all_open = self._state.all_open_positions()
        total_locked = sum(p.locked_margin for p in all_open)
        if capital > 0 and (total_locked / capital) * 100 >= self._settings.max_capital_risk_pct:
            locked_pct = (total_locked / capital) * 100
            logger.warning(
                "Circuit breaker: %.1f%% capital locked (limit %.1f%%) — skipping entry",
                locked_pct,
                self._settings.max_capital_risk_pct,
            )
            await self._reject_signal_batch(
                symbol,
                signal_batch,
                reason=(
                    f"capital circuit breaker: {locked_pct:.1f}% locked, "
                    f"limit {self._settings.max_capital_risk_pct:.1f}%"
                ),
            )
            return

        # Monthly risk base
        entry_time = signal_batch.next_time
        risk_base = self._risk_calc.update_monthly_risk_base(self._state, entry_time, capital)
        entry_price = signal_batch.next_open
        if self._app_settings.okx_is_authenticated:
            entry_price = await self._trading_client.get_last_price(symbol)
            drift_pct = abs(entry_price - signal_batch.next_open) / signal_batch.next_open
            if drift_pct > self._settings.max_entry_drift_pct:
                await self._reject_signal_batch(
                    symbol,
                    signal_batch,
                    reason=(
                        f"entry drift {drift_pct:.3%} exceeds "
                        f"{self._settings.max_entry_drift_pct:.3%}; "
                        f"H1 open={signal_batch.next_open:.4f}, live={entry_price:.4f}"
                    ),
                )
                return

        for event in signal_batch.events:
            await self._try_open_event(
                symbol=symbol,
                event=event,
                entry_time=entry_time,
                entry_price=entry_price,
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
        event_id = build_event_id(
            symbol=symbol,
            signal_time=event.bar_time,
            selected_strategy=event.selected_strategy,
            is_long=event.signal == 1,
        )
        if any(position.event_id == event_id for position in self._state.positions):
            await self._notify_entry_rejected(
                symbol,
                event,
                f"event {event_id} was already processed",
            )
            return
        await self._notify_entry_attempt(symbol, event, entry_price)
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
            await self._notify_entry_rejected(
                symbol,
                event,
                "risk, margin, leverage, fee, or exposure guard rejected the entry",
            )
            return

        rr = decision.risk_result
        same_side_positions = [
            position for position in open_positions if position.is_long is rr.is_long
        ]
        aggregate_size = sum(position.size for position in same_side_positions) + rr.size
        if not leverage_is_within_size_tier(
            position_size=aggregate_size,
            leverage=rr.required_leverage,
            configured_max_leverage=self._settings.max_leverage,
            tier_schedule=rr.maintenance_margin_tier_schedule,
        ):
            await self._notify_entry_rejected(
                symbol,
                event,
                (
                    "OKX side-aggregated size exceeds the tier max leverage: "
                    f"size={aggregate_size:.8g}, leverage={rr.required_leverage:.0f}x"
                ),
            )
            return
        aggregate_safe, aggregate_liquidation = aggregate_liquidation_is_beyond_stops(
            entries_and_stops=[
                (position.entry_price, position.size, position.sl_price)
                for position in same_side_positions
            ]
            + [(entry_price, rr.size, rr.sl_price)],
            is_long=rr.is_long,
            leverage=rr.required_leverage,
            maintenance_margin_rate=rr.maintenance_margin_rate,
            liquidation_fee_rate=rr.liquidation_fee_rate,
            buffer_pct=rr.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=rr.maintenance_margin_tier_schedule,
        )
        if not aggregate_safe:
            await self._notify_entry_rejected(
                symbol,
                event,
                (
                    "OKX side-aggregated liquidation would be unsafe: "
                    f"liq={aggregate_liquidation}, new_sl={rr.sl_price:.4f}"
                ),
            )
            return
        if event.drain_on_group_change and open_positions:
            active_groups = {position.position_group for position in open_positions}
            if event.position_group not in active_groups:
                logger.debug(
                    "Drain-on-group-change rejected %s event for group %s; active groups=%s",
                    symbol,
                    event.position_group,
                    sorted(active_groups),
                )
                await self._notify_entry_rejected(
                    symbol,
                    event,
                    (
                        f"position group {event.position_group or 'unknown'} cannot replace "
                        f"active groups {sorted(active_groups)}"
                    ),
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
            await self._notify_entry_rejected(
                symbol,
                event,
                (
                    f"calculated size {rr.size:.4f} is below the OKX minimum "
                    f"(contract size {contract_size:.4f})"
                ),
            )
            return

        # Set leverage only before opening a fresh side. OKX may reject leverage
        # changes while that side already has open positions/orders; in that
        # case the risk model has already reused the existing same-side leverage.
        leverage = int(rr.required_leverage)
        if not same_side_positions:
            try:
                await self._trading_client.set_isolated_leverage(symbol, leverage)
            except Exception as exc:
                logger.exception("Failed to set leverage for %s — aborting entry", symbol)
                await self.notify_execution_error(
                    context=f"set leverage for {symbol} strategy={event.selected_strategy}",
                    error=exc,
                )
                return

        client_order_id = f"ce{event_id}"
        algo_client_order_id = f"ca{event_id}"
        trailing_algo_client_order_id = f"ct{event_id}"
        trailing_geometry = None
        if (event.trail_activation_rrr or 0.0) > 0:
            if event.trail_entry_atr is None or event.trail_entry_atr <= 0:
                await self._notify_entry_rejected(
                    symbol,
                    event,
                    "native OKX trailing requires a valid entry-known closed ATR14",
                )
                return
            trailing_geometry = build_native_trailing_geometry(
                entry_price=entry_price,
                stop_price=rr.sl_price,
                take_profit_price=rr.tp_price,
                is_long=rr.is_long,
                activation_rrr=event.trail_activation_rrr or 0.0,
                distance_atr=event.trail_distance_atr or 0.0,
                entry_atr=event.trail_entry_atr,
            )
        try:
            order_result = await self._trading_client.open_position(
                okx_symbol=symbol,
                is_long=rr.is_long,
                size_asset_units=rr.size,
                sl_price=rr.sl_price,
                tp_price=rr.tp_price,
                client_order_id=client_order_id,
                algo_client_order_id=algo_client_order_id,
                include_take_profit=(
                    trailing_geometry is None or trailing_geometry.fixed_take_profit_enabled
                ),
            )
        except Exception as exc:
            logger.exception("open_position failed for %s — entry aborted", symbol)
            await self.notify_execution_error(
                context=f"place entry for {symbol} strategy={event.selected_strategy}",
                error=exc,
            )
            return

        order_id = order_result.order_id if order_result is not None else None
        actual_entry_price = order_result.average_price if order_result is not None else entry_price
        fill_drift_pct = abs(actual_entry_price - entry_price) / entry_price
        actual_contracts = order_result.filled_contracts if order_result is not None else contracts
        contract_size = await self._trading_client.get_contract_size(symbol)
        actual_size = actual_contracts * contract_size
        actual_position_value = actual_size * actual_entry_price
        actual_locked_margin = actual_position_value / rr.required_leverage
        actual_liquidation = estimate_linear_liquidation_price(
            entry_price=actual_entry_price,
            is_long=rr.is_long,
            leverage=rr.required_leverage,
            maintenance_margin_rate=rr.maintenance_margin_rate,
            liquidation_fee_rate=rr.liquidation_fee_rate,
        )
        if actual_liquidation is None:
            raise RuntimeError("failed to estimate liquidation after entry fill")
        actual_aggregate_safe, actual_aggregate_liquidation = aggregate_liquidation_is_beyond_stops(
            entries_and_stops=[
                (position.entry_price, position.size, position.sl_price)
                for position in same_side_positions
            ]
            + [(actual_entry_price, actual_size, rr.sl_price)],
            is_long=rr.is_long,
            leverage=rr.required_leverage,
            maintenance_margin_rate=rr.maintenance_margin_rate,
            liquidation_fee_rate=rr.liquidation_fee_rate,
            buffer_pct=rr.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=rr.maintenance_margin_tier_schedule,
        )
        if actual_aggregate_liquidation is not None:
            actual_liquidation = actual_aggregate_liquidation
        actual_aggregate_size = sum(position.size for position in same_side_positions) + actual_size
        actual_aggregate_leverage_allowed = leverage_is_within_size_tier(
            position_size=actual_aggregate_size,
            leverage=rr.required_leverage,
            configured_max_leverage=self._settings.max_leverage,
            tier_schedule=rr.maintenance_margin_tier_schedule,
        )
        if trailing_geometry is not None:
            trailing_geometry = build_native_trailing_geometry(
                entry_price=actual_entry_price,
                stop_price=rr.sl_price,
                take_profit_price=rr.tp_price,
                is_long=rr.is_long,
                activation_rrr=event.trail_activation_rrr or 0.0,
                distance_atr=event.trail_distance_atr or 0.0,
                entry_atr=event.trail_entry_atr or 0.0,
            )

        # Record position in state
        new_pos = LivePosition.create(
            symbol=symbol,
            signal_time=event.bar_time,
            entry_time=entry_time,
            entry_price=actual_entry_price,
            sl_price=rr.sl_price,
            tp_price=rr.tp_price,
            size=actual_size,
            contracts=actual_contracts,
            leverage=float(leverage),
            locked_margin=actual_locked_margin,
            risk_base_capital=risk_base,
            is_long=rr.is_long,
            ttl_bars=event.position_ttl_bars
            if event.position_ttl_bars is not None
            else self._settings.ttl_bars,
            entry_order_id=order_id,
            event_id=event_id,
            client_order_id=client_order_id,
            algo_client_order_id=algo_client_order_id,
            entry_fee=order_result.fee if order_result is not None else 0.0,
            trailing_algo_client_order_id=(
                trailing_algo_client_order_id if trailing_geometry is not None else ""
            ),
            trail_activation_price=(
                trailing_geometry.activation_price if trailing_geometry is not None else None
            ),
            trail_callback_spread=(
                trailing_geometry.callback_spread if trailing_geometry is not None else None
            ),
            fixed_take_profit_enabled=(
                trailing_geometry is None or trailing_geometry.fixed_take_profit_enabled
            ),
            selected_strategy=event.selected_strategy,
            position_group=event.position_group,
            signal_event=_jsonable_event(event.raw_event),
            liquidation_price=actual_liquidation,
            maintenance_margin_rate=rr.maintenance_margin_rate,
            liquidation_fee_rate=rr.liquidation_fee_rate,
            liquidation_buffer_pct=rr.liquidation_buffer_pct,
            maintenance_margin_tier_schedule=rr.maintenance_margin_tier_schedule,
            trail_activation_rrr=event.trail_activation_rrr or 0.0,
            trail_distance_atr=event.trail_distance_atr or 0.0,
        )
        self._state.positions.append(new_pos)
        for position in [*same_side_positions, new_pos]:
            position.liquidation_price = actual_liquidation
        save_state(self._state, self._settings.state_path)
        if trailing_geometry is not None:
            try:
                new_pos.trailing_algo_order_id = (
                    await self._trading_client.place_trailing_stop(
                        okx_symbol=symbol,
                        is_long=rr.is_long,
                        contracts=actual_contracts,
                        activation_price=trailing_geometry.activation_price,
                        callback_spread=trailing_geometry.callback_spread,
                        algo_client_order_id=trailing_algo_client_order_id,
                    )
                    or ""
                )
                save_state(self._state, self._settings.state_path)
            except Exception as exc:
                await self.notify_execution_error(
                    context=f"place native trailing for {symbol} position={new_pos.position_id[:8]}",
                    error=exc,
                )
        await self._notify_entry_opened(new_pos)
        if fill_drift_pct > self._settings.max_entry_drift_pct:
            await self.notify_execution_error(
                context=f"entry fill drift for {symbol}",
                error=(
                    f"quote={entry_price:.4f}, fill={actual_entry_price:.4f}, "
                    f"drift={fill_drift_pct:.3%}"
                ),
            )
        if not actual_aggregate_safe:
            await self.notify_execution_error(
                context=f"unsafe post-fill liquidation for {symbol}",
                error=(
                    f"actual entry={actual_entry_price:.4f}, "
                    f"liq={actual_liquidation:.4f}, sl={rr.sl_price:.4f}"
                ),
            )
        if not actual_aggregate_leverage_allowed:
            await self.notify_execution_error(
                context=f"unsafe post-fill leverage tier for {symbol}",
                error=(
                    f"aggregate_size={actual_aggregate_size:.8g}, "
                    f"leverage={rr.required_leverage:.0f}x"
                ),
            )

        logger.info(
            "Position opened: %s %s %.8g contracts SL=%.4f TP=%.4f liq=%.4f "
            "margin=%.2f leverage=%.0fx strategy=%s%s",
            "LONG" if rr.is_long else "SHORT",
            symbol,
            contracts,
            rr.sl_price,
            rr.tp_price,
            rr.liquidation_price,
            rr.locked_margin,
            rr.required_leverage,
            event.selected_strategy,
            " [DRY RUN]" if self._settings.dry_run else "",
        )

    async def _exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:
        if not self._app_settings.okx_is_authenticated:
            return ExchangeSnapshot.empty_dry_run(balance=self._state.monthly_risk_base or 10_000.0)
        return await self._trading_client.get_exchange_snapshot(symbols)

    def _apply_exchange_sync(self, *, snapshot: ExchangeSnapshot, log_summary: bool = True) -> bool:
        self._bind_protection_order_ids(snapshot)
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

    def _bind_protection_order_ids(self, snapshot: ExchangeSnapshot) -> None:
        """Bind exchange-generated protection IDs to local positions."""
        for pos in self._state.all_open_positions():
            close_side = "sell" if pos.is_long else "buy"
            if not pos.stop_algo_order_id:
                stop_candidates = [
                    order
                    for order in snapshot.algo_orders
                    if order.symbol == pos.symbol
                    and order.side == close_side
                    and _amount_matches(order.amount, pos.contracts)
                    and _price_matches(order.price, pos.sl_price)
                    and order.raw.get("ordType") != "move_order_stop"
                    and (
                        not pos.algo_client_order_id
                        or not order.client_order_id
                        or order.client_order_id == pos.algo_client_order_id
                    )
                ]
                if len(stop_candidates) == 1:
                    pos.stop_algo_order_id = stop_candidates[0].order_id
            if pos.trail_activation_rrr > 0 and not pos.trailing_algo_order_id:
                trailing_candidates = [
                    order
                    for order in snapshot.algo_orders
                    if order.symbol == pos.symbol
                    and order.raw.get("ordType") == "move_order_stop"
                    and (
                        order.client_order_id == pos.trailing_algo_client_order_id
                        if pos.trailing_algo_client_order_id
                        else _amount_matches(order.amount, pos.contracts)
                    )
                ]
                if len(trailing_candidates) == 1:
                    pos.trailing_algo_order_id = trailing_candidates[0].order_id
            if pos.fixed_take_profit_enabled and not pos.take_profit_order_id:
                tp_candidates = [
                    order
                    for order in snapshot.open_orders
                    if order.symbol == pos.symbol
                    and order.side == close_side
                    and _amount_matches(order.amount, pos.contracts)
                    and _price_matches(order.price, pos.tp_price)
                ]
                if len(tp_candidates) == 1:
                    pos.take_profit_order_id = tp_candidates[0].order_id

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

    async def _notify_entry_attempt(
        self,
        symbol: str,
        event: SignalEvent,
        entry_price: float,
    ) -> None:
        logger.info(
            "ENTRY ATTEMPT: symbol=%s side=%s strategy=%s signal_time=%s "
            "entry=%.4f sl=%.4f",
            symbol,
            "LONG" if event.signal == 1 else "SHORT",
            event.selected_strategy,
            event.bar_time.isoformat(),
            entry_price,
            event.sl_price,
        )
        notifier = getattr(self, "_notifier", None)
        if notifier is not None:
            await notifier.send_entry_attempt(
                symbol=symbol,
                is_long=event.signal == 1,
                strategy=event.selected_strategy,
                signal_time=event.bar_time,
                entry_price=entry_price,
                sl_price=event.sl_price,
            )

    async def _notify_entry_rejected(
        self,
        symbol: str,
        event: SignalEvent,
        reason: str,
    ) -> None:
        logger.warning(
            "ENTRY REJECTED: symbol=%s side=%s strategy=%s reason=%s",
            symbol,
            "LONG" if event.signal == 1 else "SHORT",
            event.selected_strategy,
            reason,
        )
        notifier = getattr(self, "_notifier", None)
        if notifier is not None:
            await notifier.send_entry_rejected(
                symbol=symbol,
                is_long=event.signal == 1,
                strategy=event.selected_strategy,
                reason=reason,
            )

    async def _reject_signal_batch(
        self,
        symbol: str,
        signal_batch: SignalBatch,
        *,
        reason: str,
    ) -> None:
        for event in signal_batch.events:
            await self._notify_entry_attempt(symbol, event, signal_batch.next_open)
            await self._notify_entry_rejected(symbol, event, reason)

    async def notify_execution_error(
        self,
        *,
        context: str,
        error: BaseException | str,
    ) -> None:
        """Send a best-effort operator alert for an execution failure."""
        notifier = getattr(self, "_notifier", None)
        if notifier is None:
            return
        detail = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else error
        await notifier.send_execution_error(context=context, detail=detail)

    async def _notify_sync_blocker(self, sync_ok: bool) -> None:
        if sync_ok:
            return
        signature = tuple(sorted(self._state.last_exchange_sync_errors))
        await self.notify_execution_error(
            context="exchange synchronization blocked",
            error="; ".join(signature) or "unknown synchronization blocker",
        )

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


def _amount_matches(actual: float | None, expected: float) -> bool:
    return actual is not None and abs(actual - expected) <= 1e-8


def _price_matches(actual: float | None, expected: float) -> bool:
    if actual is None:
        return False
    return abs(actual - expected) <= max(abs(expected) * 0.001, 1e-8)


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
            f"Live execution settings must match strategy backtest_args for parity: {details}"
        )
