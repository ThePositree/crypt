from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from backtester.execution_sim import ExecutionSim
from backtester.instrument_precision import InstrumentPrecision
from crypt.execution.exchange_sync import (
    ExchangeBalance,
    ExchangeOrder,
    ExchangePosition,
    ExchangeSnapshot,
)
from crypt.execution.executor import (
    LiveExecutionManager,
    _validate_execution_settings_match_strategy,
)
from crypt.execution.okx_order_client import CloseOrderResult, EntryOrderResult
from crypt.execution.position_state import ExecutionState, LivePosition
from crypt.execution.risk_calculator import LiveRiskCalculator
from crypt.execution.settings import ExecutionSettings
from crypt.execution.signal_runner import SignalBatch, SignalEvent


class _FakeAppSettings:
    okx_is_authenticated = False


class _FakeAuthenticatedAppSettings:
    okx_is_authenticated = True


class _FakeTradingClient:
    def __init__(self) -> None:
        self.opened: list[dict[str, object]] = []
        self.closed: list[dict[str, object]] = []

    async def set_isolated_leverage(
        self,
        symbol: str,
        leverage: int,
        *,
        is_long: bool,
    ) -> None:
        self.leverage = (symbol, leverage, is_long)

    async def get_contract_size(self, symbol: str) -> float:  # noqa: ARG002
        return 1.0

    async def get_instrument_precision(
        self, symbol: str  # noqa: ARG002
    ) -> InstrumentPrecision:
        return InstrumentPrecision(
            contract_size=1.0,
            amount_step=0.01,
            min_amount=0.01,
            price_tick=0.01,
        )

    async def get_last_price(self, symbol: str) -> float:  # noqa: ARG002
        return 100.0

    async def size_asset_units_to_contracts(
        self,
        symbol: str,  # noqa: ARG002
        size_asset_units: float,
    ) -> float:
        return int((size_asset_units / 1.0) / 0.01) * 0.01

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
    ) -> EntryOrderResult:
        self.opened.append(
            {
                "symbol": okx_symbol,
                "is_long": is_long,
                "size": size_asset_units,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "client_order_id": client_order_id,
                "algo_client_order_id": algo_client_order_id,
                "include_take_profit": include_take_profit,
            }
        )
        return EntryOrderResult(
            order_id=f"order-{len(self.opened)}",
            average_price=100.0,
            filled_contracts=float(int(size_asset_units / 0.01)) * 0.01,
            fee=0.0,
        )

    async def place_trailing_stop(self, **_kwargs: object) -> str:
        return "trailing-algo-1"

    async def close_position_at_market(
        self,
        *,
        okx_symbol: str,
        is_long: bool,
        contracts: float,
        client_order_id: str,
    ) -> CloseOrderResult:
        self.closed.append(
            {
                "symbol": okx_symbol,
                "is_long": is_long,
                "contracts": contracts,
                "client_order_id": client_order_id,
            }
        )
        return CloseOrderResult(
            order_id=f"close-{len(self.closed)}",
            average_price=100.0,
            filled_contracts=contracts,
            fee=0.0,
        )

    async def cancel_regular_order(self, **_kwargs: object) -> None:
        return None

    async def cancel_algo_order_for_position(self, **_kwargs: object) -> None:
        return None


class _SyncingTradingClient(_FakeTradingClient):
    async def get_exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:
        positions = []
        algo_orders = []
        open_orders = []
        if self.opened:
            positions = [
                ExchangePosition(
                    symbol=symbols[0],
                    contracts=sum(float(item["size"]) for item in self.opened),
                    side="long" if bool(self.opened[-1]["is_long"]) else "short",
                )
            ]
            algo_orders = [
                ExchangeOrder(
                    symbol=symbols[0],
                    order_id=f"algo-{index}",
                    kind="algo",
                    client_order_id=str(opened["algo_client_order_id"]),
                )
                for index, opened in enumerate(self.opened, start=1)
            ]
            open_orders = [
                ExchangeOrder(
                    symbol=symbols[0],
                    order_id=f"tp-{index}",
                    kind="regular",
                    side="sell" if bool(opened["is_long"]) else "buy",
                    amount=float(opened["size"]),
                    price=float(opened["tp_price"]),
                )
                for index, opened in enumerate(self.opened, start=1)
            ]
        return ExchangeSnapshot(
            fetched_at=datetime(2026, 6, 27, 11, tzinfo=UTC),
            balance=ExchangeBalance(total=10_000.0, free=9_000.0, used=1_000.0),
            positions=positions,
            open_orders=open_orders,
            algo_orders=algo_orders,
            recent_fills=[],
        )


class _DriftSyncingTradingClient(_SyncingTradingClient):
    async def get_last_price(self, symbol: str) -> float:  # noqa: ARG002
        return 101.0

    async def open_position(self, **kwargs: object) -> EntryOrderResult:
        result = await super().open_position(**kwargs)  # type: ignore[arg-type]
        return EntryOrderResult(
            order_id=result.order_id,
            average_price=101.0,
            filled_contracts=result.filled_contracts,
            fee=result.fee,
        )


class _LeverageFailingTradingClient(_FakeTradingClient):
    async def set_isolated_leverage(
        self,
        symbol: str,
        leverage: int,
        *,
        is_long: bool,  # noqa: ARG002
    ) -> None:
        raise RuntimeError(f"leverage rejected for {symbol} at {leverage}x")


class _EntryFailingTradingClient(_FakeTradingClient):
    async def open_position(self, **_kwargs: object) -> EntryOrderResult:
        raise RuntimeError("entry transport failed after submit boundary")


class _FeeChargingTradingClient(_FakeTradingClient):
    async def open_position(self, **kwargs: object) -> EntryOrderResult:
        result = await super().open_position(**kwargs)  # type: ignore[arg-type]
        return EntryOrderResult(
            order_id=result.order_id,
            average_price=result.average_price,
            filled_contracts=result.filled_contracts,
            fee=result.average_price * result.filled_contracts * 0.0005,
        )


class _TrailingFailingTradingClient(_FakeTradingClient):
    async def place_trailing_stop(self, **_kwargs: object) -> str:
        raise RuntimeError("trailing rejected")


class _TtlCloseFailingTradingClient(_FakeTradingClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    async def close_position_at_market(self, **_kwargs: object) -> CloseOrderResult:
        self.calls.append("close")
        raise RuntimeError("close rejected")

    async def cancel_regular_order(self, **_kwargs: object) -> None:
        self.calls.append("cancel_regular")

    async def cancel_algo_order_for_position(self, **_kwargs: object) -> None:
        self.calls.append("cancel_algo")


class _RestartRecoveryTradingClient(_FakeTradingClient):
    def __init__(
        self,
        snapshot: ExchangeSnapshot,
        *,
        entry_fill: EntryOrderResult | None = None,
        close_fill: CloseOrderResult | None = None,
    ) -> None:
        super().__init__()
        self.snapshot = snapshot
        self.entry_fill = entry_fill
        self.close_fill = close_fill

    async def get_exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:  # noqa: ARG002
        return self.snapshot

    async def recover_entry_fill(self, **_kwargs: object) -> EntryOrderResult | None:
        return self.entry_fill

    async def recover_close_fill(self, **_kwargs: object) -> CloseOrderResult | None:
        return self.close_fill

    async def get_order_by_client_id(self, **_kwargs: object) -> dict[str, object] | None:
        return {"state": "filled"} if self.entry_fill is not None else None


class _BatchSignalRunner:
    def __init__(self, batch: SignalBatch) -> None:
        self.batch = batch
        self.refreshed: list[str] = []
        self.latest_calls: list[str] = []

    async def refresh_candles(self, symbol: str) -> None:
        self.refreshed.append(symbol)

    def get_latest_signal_batch(self, symbol: str) -> SignalBatch:
        self.latest_calls.append(symbol)
        return self.batch


class _RejectingRiskCalculator:
    def calculate(self, **kwargs: object) -> None:  # noqa: ARG002
        return None


class _FakeNotifier:
    def __init__(self) -> None:
        self.daily: list[tuple[ExchangeSnapshot, ExecutionState]] = []
        self.attempts: list[dict[str, object]] = []
        self.rejections: list[dict[str, object]] = []
        self.errors: list[tuple[str, str]] = []
        self.drift_alerts: list[dict[str, object]] = []
        self.entries: list[LivePosition] = []
        self.exits: list[LivePosition] = []

    async def send_daily_sync_report(
        self,
        *,
        snapshot: ExchangeSnapshot,
        state: ExecutionState,
    ) -> None:
        self.daily.append((snapshot, state))

    async def send_entry_opened(self, pos: LivePosition) -> None:
        self.entries.append(pos)

    async def send_entry_attempt(self, **kwargs: object) -> None:
        self.attempts.append(kwargs)

    async def send_entry_rejected(self, **kwargs: object) -> None:
        self.rejections.append(kwargs)

    async def send_entry_drift_alert(self, **kwargs: object) -> None:
        self.drift_alerts.append(kwargs)

    async def send_execution_error(self, *, context: str, detail: str) -> None:
        self.errors.append((context, detail))

    async def send_position_closed(self, pos: LivePosition) -> None:
        self.exits.append(pos)

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_entry_attempt_and_rejection_are_written_to_normal_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    event = SignalEvent(
        bar_time=datetime(2026, 6, 30, 13, tzinfo=UTC),
        signal=1,
        sl_price=72.1907,
        next_open=72.84,
        rrr=1.5,
        risk_percent=0.75,
        position_ttl_bars=116,
        trail_activation_rrr=1.5,
        trail_distance_atr=0.25,
        exit_geometry="sl_rrr",
        tp_move_pct=None,
        structural_sl_mode="cap",
        min_tp_move_pct=0.004,
        selected_strategy="smac_donor",
        position_group="smac_donor",
        raw_event={"signal": 1},
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._notifier = None
    with caplog.at_level(logging.INFO, logger="crypt.execution.executor"):
        await manager._notify_entry_attempt("SOL-USDT-SWAP", event, 72.84)
        await manager._notify_entry_rejected(
            "SOL-USDT-SWAP",
            event,
            "entry drift 0.934% exceeds 0.100%",
        )

    combined = caplog.text
    assert "ENTRY ATTEMPT" in combined
    assert "entry=72.8400" in combined
    assert "ENTRY REJECTED" in combined
    assert "entry drift 0.934% exceeds 0.100%" in combined


def _settings(tmp_path: Path) -> ExecutionSettings:
    return ExecutionSettings.model_validate(
        {
            "enabled": True,
            "dry_run": True,
            "strategy_config": "strategies/archive/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85.json",
            "data_dir": "data",
            "state_path": str(tmp_path / "state.json"),
            "exit_geometry": "sl_rrr",
            "risk_percent": 1.0,
            "rrr": 2.0,
            "ttl_bars": 0,
            "max_positions": 0,
            "max_leverage": 25.0,
            "risk_base_period": "monthly",
            "require_exchange_sync": True,
        }
    )


def _long_event(
    *,
    bar_time: datetime = datetime(2026, 6, 29, 10, tzinfo=UTC),
    strategy: str = "donor_long",
    trailing: bool = False,
) -> SignalEvent:
    return SignalEvent(
        bar_time=bar_time,
        signal=1,
        sl_price=98.0,
        next_open=100.0,
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=24,
        trail_activation_rrr=1.0 if trailing else 0.0,
        trail_distance_atr=0.25 if trailing else 0.0,
        trail_entry_atr=4.0 if trailing else None,
        exit_geometry="sl_rrr",
        tp_move_pct=None,
        structural_sl_mode="cap",
        min_tp_move_pct=0.004,
        selected_strategy=strategy,
        position_group=strategy,
        raw_event={"selected_strategy": strategy, "signal": 1},
    )


@pytest.mark.asyncio
async def test_try_open_signal_batch_processes_all_events_in_order(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )

    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="donor_long",
                position_group="donor_long",
                raw_event={"selected_strategy": "donor_long", "signal": 1},
            ),
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=-1,
                sl_price=102.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=32,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="donor_short",
                position_group="donor_short",
                raw_event={"selected_strategy": "donor_short", "signal": -1},
            ),
        ],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    assert [pos.selected_strategy for pos in manager._state.positions] == [
        "donor_long",
        "donor_short",
    ]
    assert [pos.entry_price for pos in manager._state.positions] == [100.0, 100.0]
    assert [pos.ttl_bars for pos in manager._state.positions] == [24, 32]
    assert len(manager._trading_client.opened) == 2


@pytest.mark.asyncio
async def test_entry_drift_warns_but_does_not_reject_trade(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _DriftSyncingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        next_open=100.0,
        events=[_long_event()],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 11, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=10_000.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )

    with caplog.at_level(logging.WARNING, logger="crypt.execution.executor"):
        await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot)

    assert len(manager._trading_client.opened) == 1
    assert len(manager._state.all_open_positions()) == 1
    opened = manager._trading_client.opened[0]
    assert opened["size"] == pytest.approx(50.0)
    assert opened["sl_price"] == pytest.approx(98.0)
    assert opened["tp_price"] == pytest.approx(104.0)
    pos = manager._state.all_open_positions()[0]
    assert pos.entry_price == pytest.approx(101.0)
    assert pos.size == pytest.approx(50.0)
    assert pos.trail_activation_price is None
    assert notifier.rejections == []
    assert "proceeding with entry" in caplog.text
    assert len(notifier.errors) == 1
    assert "actual fill risk" in notifier.errors[0][0]
    assert notifier.drift_alerts == [
        {
            "symbol": "SOL-USDT-SWAP",
            "strategy": "donor_long",
            "h1_open": 100.0,
            "quote": 101.0,
            "fill": 101.0,
            "h1_fill_drift_pct": 0.01,
            "quote_fill_drift_pct": 0.0,
        }
    ]


@pytest.mark.asyncio
async def test_live_same_bar_entries_use_capital_after_previous_entry_fee(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={"risk_base_period": "trade"})
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FeeChargingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            _long_event(strategy="first"),
            _long_event(strategy="second"),
        ],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    first, second = manager._state.positions
    assert first.entry_fee > 0
    assert second.risk_base_capital == pytest.approx(10_000.0 - first.entry_fee)
    assert second.size < first.size


@pytest.mark.asyncio
async def test_try_open_signal_batch_reuses_same_side_leverage_without_setting_it(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    existing = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 8, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 9, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-0",
        selected_strategy="existing",
        position_group="existing",
    )
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[existing],
    )

    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="new_same_side",
                position_group="new_same_side",
                raw_event={"selected_strategy": "new_same_side", "signal": 1},
            )
        ],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    assert len(manager._state.positions) == 2
    assert manager._trading_client.opened
    assert not hasattr(manager._trading_client, "leverage")


@pytest.mark.asyncio
async def test_try_open_signal_batch_notifies_each_entry(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="donor_long",
                position_group="donor_long",
                raw_event={"selected_strategy": "donor_long", "signal": 1},
            )
        ],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    assert [attempt["strategy"] for attempt in notifier.attempts] == ["donor_long"]
    assert [pos.symbol for pos in notifier.entries] == ["SOL-USDT-SWAP"]
    assert notifier.rejections == []
    assert notifier.errors == []


@pytest.mark.asyncio
async def test_risk_rejection_notifies_attempt_and_terminal_result(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = _RejectingRiskCalculator()
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    event = SignalEvent(
        bar_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        signal=-1,
        sl_price=102.0,
        next_open=100.0,
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=24,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        exit_geometry="sl_rrr",
        tp_move_pct=None,
        structural_sl_mode="cap",
        min_tp_move_pct=0.004,
        selected_strategy="donor_short",
        position_group="donor_short",
        raw_event={"selected_strategy": "donor_short", "signal": -1},
    )

    await manager._try_open_event(
        symbol="SOL-USDT-SWAP",
        event=event,
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        capital=10_000.0,
        risk_base=10_000.0,
    )

    assert len(notifier.attempts) == 1
    assert len(notifier.rejections) == 1
    assert notifier.rejections[0]["strategy"] == "donor_short"
    assert manager._state.positions == []


@pytest.mark.asyncio
async def test_leverage_failure_notifies_execution_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._trading_client = _LeverageFailingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    event = SignalEvent(
        bar_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        signal=1,
        sl_price=98.0,
        next_open=100.0,
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=24,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        exit_geometry="sl_rrr",
        tp_move_pct=None,
        structural_sl_mode="cap",
        min_tp_move_pct=0.004,
        selected_strategy="donor_long",
        position_group="donor_long",
        raw_event={"selected_strategy": "donor_long", "signal": 1},
    )

    await manager._try_open_event(
        symbol="SOL-USDT-SWAP",
        event=event,
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        capital=10_000.0,
        risk_base=10_000.0,
    )

    assert len(notifier.attempts) == 1
    assert notifier.rejections == []
    assert len(notifier.errors) == 1
    assert "set leverage" in notifier.errors[0][0]
    assert "leverage rejected" in notifier.errors[0][1]
    assert manager._state.positions == []


@pytest.mark.asyncio
async def test_entry_intent_is_persisted_before_submit_failure(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _EntryFailingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )

    await manager._try_open_event(
        symbol="SOL-USDT-SWAP",
        event=_long_event(strategy="persisted_before_submit"),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        capital=10_000.0,
        risk_base=10_000.0,
    )

    assert len(manager._state.positions) == 1
    pos = manager._state.positions[0]
    assert pos.status == "open"
    assert pos.entry_state == "entry_submitted"
    assert pos.entry_order_id is None
    assert pos.client_order_id.startswith("ce")
    assert pos.algo_client_order_id.startswith("ca")
    assert settings.state_path.exists()
    assert "persisted_before_submit" in settings.state_path.read_text(encoding="utf-8")
    assert len(notifier.errors) == 1


@pytest.mark.asyncio
async def test_trailing_failure_after_entry_triggers_fail_safe_close(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    trading_client = _TrailingFailingTradingClient()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = trading_client
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )

    await manager._try_open_event(
        symbol="SOL-USDT-SWAP",
        event=_long_event(strategy="trailing_required", trailing=True),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        capital=10_000.0,
        risk_base=10_000.0,
    )

    assert len(manager._state.positions) == 1
    pos = manager._state.positions[0]
    assert pos.status == "closed"
    assert pos.exit_reason == "native trailing placement failed after entry fill"
    assert trading_client.closed == [
        {
            "symbol": "SOL-USDT-SWAP",
            "is_long": True,
            "contracts": pos.contracts,
            "client_order_id": f"cx{pos.event_id}",
        }
    ]
    assert notifier.entries == []
    assert notifier.exits == [pos]
    assert len(notifier.errors) == 1
    assert "place native trailing" in notifier.errors[0][0]


@pytest.mark.asyncio
async def test_ttl_close_failure_keeps_protection_orders_until_close_confirms(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    trading_client = _TtlCloseFailingTradingClient()
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 8, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 9, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=1,
        entry_order_id="entry-1",
        selected_strategy="ttl",
    )
    pos.take_profit_order_id = "tp-1"
    pos.algo_client_order_id = "ca1"
    pos.stop_algo_order_id = "sl-1"
    pos.trailing_algo_client_order_id = "ct1"
    pos.trailing_algo_order_id = "trail-1"
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = trading_client
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )

    await manager._close_ttl(pos)

    assert trading_client.calls == ["close"]
    assert pos.status == "closing"
    assert pos.close_client_order_id == f"cx{pos.event_id}"
    assert len(notifier.errors) == 1
    assert "TTL close" in notifier.errors[0][0]


@pytest.mark.asyncio
async def test_restart_adopts_filled_entry_and_actual_protection(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10.0,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=24,
        entry_order_id=None,
        selected_strategy="restart",
        client_order_id="ce-restart",
        algo_client_order_id="ca-restart",
    )
    pos.entry_state = "entry_submitted"
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 11, 0, 5, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_950.0, used=50.0),
        positions=[
            ExchangePosition(
                symbol=pos.symbol,
                contracts=9.5,
                side="long",
                leverage=25.0,
                margin_mode="isolated",
            )
        ],
        open_orders=[
            ExchangeOrder(
                symbol=pos.symbol,
                order_id="tp-restart",
                kind="regular",
                side="sell",
                amount=9.5,
                price=104.0,
            )
        ],
        algo_orders=[
            ExchangeOrder(
                symbol=pos.symbol,
                order_id="sl-restart",
                kind="algo",
                client_order_id="ca-restart",
                side="sell",
                amount=9.5,
                price=98.0,
            )
        ],
        recent_fills=[],
    )
    client = _RestartRecoveryTradingClient(
        snapshot,
        entry_fill=EntryOrderResult(
            order_id="entry-restart",
            average_price=101.0,
            filled_contracts=9.5,
            fee=0.48,
        ),
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = client
    manager._notifier = _FakeNotifier()
    manager._state = ExecutionState(
        schema_version=7,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )

    recovered = await manager._recover_transitional_positions(snapshot)

    assert recovered is snapshot
    assert pos.status == "open"
    assert pos.entry_state == "protected"
    assert pos.entry_order_id == "entry-restart"
    assert pos.entry_price == pytest.approx(101.0)
    assert pos.contracts == pytest.approx(9.5)
    assert pos.entry_fee == pytest.approx(0.48)
    assert pos.stop_algo_order_id == "sl-restart"
    assert pos.take_profit_order_id == "tp-restart"


@pytest.mark.asyncio
async def test_restart_adopts_entry_without_repricing_trailing_geometry(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10.0,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=24,
        entry_order_id=None,
        selected_strategy="restart-trailing",
        client_order_id="ce-restart-trailing",
        algo_client_order_id="ca-restart-trailing",
        trailing_algo_client_order_id="ct-restart-trailing",
        trail_activation_rrr=1.0,
        trail_distance_atr=0.25,
        trail_activation_price=102.0,
        trail_callback_spread=1.0,
        fixed_take_profit_enabled=False,
    )
    pos.entry_state = "entry_submitted"
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 11, 0, 5, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_950.0, used=50.0),
        positions=[
            ExchangePosition(
                symbol=pos.symbol,
                contracts=9.5,
                side="long",
                leverage=25.0,
                margin_mode="isolated",
            )
        ],
        open_orders=[],
        algo_orders=[
            ExchangeOrder(
                symbol=pos.symbol,
                order_id="sl-restart-trailing",
                kind="algo",
                client_order_id="ca-restart-trailing",
                side="sell",
                amount=9.5,
                price=98.0,
            ),
            ExchangeOrder(
                symbol=pos.symbol,
                order_id="trail-restart-trailing",
                kind="algo",
                client_order_id="ct-restart-trailing",
                side="sell",
                amount=9.5,
                raw={"ordType": "move_order_stop"},
            ),
        ],
        recent_fills=[],
    )
    client = _RestartRecoveryTradingClient(
        snapshot,
        entry_fill=EntryOrderResult(
            order_id="entry-restart-trailing",
            average_price=101.0,
            filled_contracts=9.5,
            fee=0.48,
        ),
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = client
    manager._notifier = _FakeNotifier()
    manager._state = ExecutionState(
        schema_version=7,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )

    await manager._recover_transitional_positions(snapshot)

    assert pos.status == "open"
    assert pos.entry_state == "protected"
    assert pos.entry_price == pytest.approx(101.0)
    assert pos.trail_activation_price == pytest.approx(102.0)
    assert pos.trail_callback_spread == pytest.approx(1.0)
    assert pos.trailing_algo_order_id == "trail-restart-trailing"


@pytest.mark.asyncio
async def test_restart_adopts_close_fill_from_closing_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10.0,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=24,
        entry_order_id="entry-1",
        selected_strategy="restart-close",
    )
    pos.status = "closing"
    pos.close_client_order_id = "cx-restart"
    pos.exit_reason = "ttl_expired"
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_010.0, free=10_010.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )
    client = _RestartRecoveryTradingClient(
        snapshot,
        close_fill=CloseOrderResult(
            order_id="close-restart",
            average_price=102.0,
            filled_contracts=10.0,
            fee=0.51,
        ),
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = client
    manager._notifier = _FakeNotifier()
    manager._state = ExecutionState(
        schema_version=7,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )

    await manager._recover_transitional_positions(snapshot)

    assert pos.status == "closed"
    assert pos.exit_reason == "ttl_expired"
    assert pos.exit_price == pytest.approx(102.0)
    assert pos.realized_pnl == pytest.approx(19.49)


@pytest.mark.asyncio
async def test_live_fail_safe_closes_position_after_liquidation_buffer_is_lost(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10.0,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=24,
        entry_order_id="entry-unsafe",
        selected_strategy="unsafe-buffer",
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_960.0, used=40.0),
        positions=[
            ExchangePosition(
                symbol=pos.symbol,
                contracts=10.0,
                side="long",
                liquidation_price=97.8,
            )
        ],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )
    client = _RestartRecoveryTradingClient(snapshot)
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = client
    manager._notifier = _FakeNotifier()
    manager._state = ExecutionState(
        schema_version=7,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )

    await manager._close_unsafe_exchange_positions(snapshot)

    assert pos.status == "closed"
    assert pos.exit_reason == "unsafe_liquidation_buffer"
    assert len(client.closed) == 1


@pytest.mark.asyncio
async def test_sync_blocker_alert_is_sent_on_every_failed_sync() -> None:
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
        last_exchange_sync_ok=False,
        last_exchange_sync_errors=["position_mode_not_long_short"],
    )

    await manager._notify_sync_blocker(False)
    await manager._notify_sync_blocker(False)
    manager._state.last_exchange_sync_errors = ["orphan_exchange_position:SOL-USDT-SWAP"]
    await manager._notify_sync_blocker(False)

    assert len(notifier.errors) == 3
    assert "position_mode_not_long_short" in notifier.errors[0][1]
    assert "position_mode_not_long_short" in notifier.errors[1][1]
    assert "orphan_exchange_position" in notifier.errors[2][1]


@pytest.mark.asyncio
async def test_dry_run_capital_override_sizes_against_test_capital(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={"dry_run_capital": 10_000.0})
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _SyncingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = None
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=0.0,
        positions=[],
    )
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="donor_long",
                position_group="donor_long",
                raw_event={"selected_strategy": "donor_long", "signal": 1},
            )
        ],
    )
    low_balance_snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 11, tzinfo=UTC),
        balance=ExchangeBalance(total=105.0, free=105.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=low_balance_snapshot)

    assert len(manager._state.positions) == 1
    assert manager._state.positions[0].risk_base_capital == pytest.approx(10_000.0)
    assert manager._trading_client.opened


@pytest.mark.asyncio
async def test_try_open_signal_batch_respects_drain_on_group_change(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._notifier = None
    existing = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 8, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 9, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-0",
        selected_strategy="old",
        position_group="old_group",
    )
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[existing],
    )
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="new",
                position_group="new_group",
                raw_event={"selected_strategy": "new", "signal": 1},
                drain_on_group_change=True,
            )
        ],
    )

    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    assert manager._state.positions == [existing]
    assert manager._trading_client.opened == []


@pytest.mark.asyncio
async def test_on_h1_close_rechecks_sync_after_marking_missing_position_closed(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    stale_pos = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    stale_pos_position = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 26, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 26, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=10_000,
        entry_order_id="old-entry",
        selected_strategy="old_donor",
    )
    stale_pos.positions.append(stale_pos_position)
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="new_donor",
                position_group="new_donor",
                raw_event={"selected_strategy": "new_donor", "signal": 1},
            )
        ],
    )

    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _SyncingTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._state = stale_pos
    manager._signal_runner = _BatchSignalRunner(batch)

    await manager.on_h1_close("SOL-USDT-SWAP")

    assert stale_pos_position.status == "closed"
    assert [pos.selected_strategy for pos in manager._state.all_open_positions()] == ["new_donor"]
    assert manager._state.last_exchange_sync_ok


@pytest.mark.asyncio
async def test_startup_tick_syncs_but_does_not_open_past_signal(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    batch = SignalBatch(
        bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        next_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
                signal=1,
                sl_price=98.0,
                next_open=100.0,
                rrr=2.0,
                risk_percent=1.0,
                position_ttl_bars=24,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
                selected_strategy="startup_donor",
                position_group="startup_donor",
                raw_event={"selected_strategy": "startup_donor", "signal": 1},
            )
        ],
    )
    signal_runner = _BatchSignalRunner(batch)
    trading_client = _SyncingTradingClient()

    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = trading_client
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )
    manager._signal_runner = signal_runner

    await manager.on_h1_close("SOL-USDT-SWAP", trigger_source="startup")

    assert signal_runner.refreshed == ["SOL-USDT-SWAP"]
    assert signal_runner.latest_calls == []
    assert trading_client.opened == []
    assert manager._state.all_open_positions() == []
    assert manager._state.last_exchange_sync_ok


@pytest.mark.asyncio
async def test_manage_open_positions_ttl_zero_does_not_expire(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 26, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 26, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-1",
        selected_strategy="ttl_disabled",
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 11, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_000.0, used=1_000.0),
        positions=[
            ExchangePosition(
                symbol="SOL-USDT-SWAP",
                contracts=10.0,
                side="long",
            )
        ],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert pos.status == "open"


def test_exchange_sync_binds_legacy_stop_and_take_profit_ids(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 12, tzinfo=UTC),
        entry_price=73.47,
        sl_price=70.9484,
        tp_price=75.9916,
        size=0.4164,
        contracts=0.41,
        leverage=25.0,
        locked_margin=1.22,
        risk_base_capital=105.0,
        is_long=True,
        ttl_bars=16,
        entry_order_id="3698898461833158656",
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=105.0,
        positions=[pos],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 29, 13, tzinfo=UTC),
        balance=ExchangeBalance(total=105.0, free=103.78, used=1.22),
        positions=[
            ExchangePosition(
                symbol="SOL-USDT-SWAP",
                contracts=0.41,
                side="long",
            )
        ],
        open_orders=[
            ExchangeOrder(
                symbol="SOL-USDT-SWAP",
                order_id="tp-order",
                kind="regular",
                side="sell",
                amount=0.41,
                price=75.99,
            )
        ],
        algo_orders=[
            ExchangeOrder(
                symbol="SOL-USDT-SWAP",
                order_id="sl-algo",
                kind="algo",
                side="sell",
                amount=0.41,
                price=70.95,
            )
        ],
        recent_fills=[],
    )

    assert manager._apply_exchange_sync(snapshot=snapshot)
    assert pos.stop_algo_order_id == "sl-algo"
    assert pos.take_profit_order_id == "tp-order"


@pytest.mark.asyncio
async def test_manage_open_positions_records_exchange_close_fill(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-1",
        selected_strategy="donor",
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_040.0, free=10_040.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 104.0,
                "amount": 10.0,
                "fee": {"cost": 0.52},
            }
        ],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert pos.status == "closed"
    assert pos.exit_reason == "take_profit"
    assert pos.exit_price == pytest.approx(104.0)
    assert pos.realized_pnl == pytest.approx(39.48)
    assert pos.constituent_realized_pnl == pytest.approx(39.48)
    assert pos.exit_fee == pytest.approx(0.52)


@pytest.mark.asyncio
async def test_manage_open_positions_records_constituent_pnl_when_aggregate_differs(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=150.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=60.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-1",
        selected_strategy="donor",
    )
    pos.aggregate_entry_price = 150.0
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=10_000.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 150.0,
                "amount": 10.0,
                "fee": {"cost": 0.75},
            }
        ],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert pos.status == "closed"
    assert pos.realized_pnl == pytest.approx(-0.75)
    assert pos.constituent_realized_pnl == pytest.approx(499.25)


@pytest.mark.asyncio
async def test_manage_open_positions_notifies_exchange_close_fill(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 27, 11, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=104.0,
        size=10.0,
        contracts=10,
        leverage=25.0,
        locked_margin=40.0,
        risk_base_capital=10_000.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-1",
        selected_strategy="donor",
    )
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[pos],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_040.0, free=10_040.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[
            {
                "side": "sell",
                "timestamp": 1_782_561_600_000,
                "price": 104.0,
                "amount": 10.0,
                "fee": {"cost": 0.52},
            }
        ],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert notifier.exits == [pos]


@pytest.mark.asyncio
async def test_manage_open_positions_closes_reduced_same_side_constituent_with_missing_protection(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    first = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 7, 13, 12, tzinfo=UTC),
        entry_time=datetime(2026, 7, 13, 13, tzinfo=UTC),
        entry_price=75.84,
        sl_price=76.62,
        tp_price=73.46,
        size=0.66,
        contracts=0.66,
        leverage=25.0,
        locked_margin=2.0,
        risk_base_capital=104.77,
        is_long=False,
        ttl_bars=10000,
        entry_order_id="entry-first",
        selected_strategy="freq_4pw_r02_hyperband_004678",
    )
    first.stop_algo_order_id = "stop-first"
    first.take_profit_order_id = "tp-first"
    second = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 7, 13, 17, tzinfo=UTC),
        entry_time=datetime(2026, 7, 13, 18, tzinfo=UTC),
        entry_price=74.60,
        sl_price=75.34,
        tp_price=72.13,
        size=0.63,
        contracts=0.63,
        leverage=25.0,
        locked_margin=1.88,
        risk_base_capital=104.77,
        is_long=False,
        ttl_bars=10000,
        entry_order_id="entry-second",
        selected_strategy="freq_4pw_r02_hyperband_004678",
    )
    second.stop_algo_order_id = "stop-second"
    second.take_profit_order_id = "tp-second"
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAuthenticatedAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=8,
        risk_window_month=(2026, 7),
        monthly_risk_base=104.77,
        positions=[first, second],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 7, 14, 1, 32, tzinfo=UTC),
        balance=ExchangeBalance(total=102.64, free=102.64, used=0.0),
        positions=[
            ExchangePosition(
                symbol="SOL-USDT-SWAP",
                contracts=0.66,
                side="short",
                entry_price=75.84,
                leverage=25.0,
                margin_mode="isolated",
                liquidation_price=78.5,
            )
        ],
        open_orders=[
            ExchangeOrder(
                symbol="SOL-USDT-SWAP",
                order_id="tp-first",
                kind="regular",
                side="buy",
                amount=0.66,
                price=73.46,
            )
        ],
        algo_orders=[
            ExchangeOrder(
                symbol="SOL-USDT-SWAP",
                order_id="stop-first",
                kind="algo",
                side="buy",
                amount=0.66,
                price=76.62,
            )
        ],
        recent_fills=[],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert first.status == "open"
    assert second.status == "closed"
    assert second.exit_reason == "exchange_reduced_unknown"
    assert second.exit_time == snapshot.fetched_at.isoformat()
    assert notifier.exits == [second]


@pytest.mark.asyncio
async def test_daily_sync_notification_is_sent_once_per_utc_day(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    notifier = _FakeNotifier()
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._notifier = notifier
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
        last_exchange_sync_ok=True,
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 27, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=10_000.0, used=0.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )

    await manager._notify_daily_sync_if_due(snapshot)
    await manager._notify_daily_sync_if_due(snapshot)

    assert len(notifier.daily) == 1
    assert manager._state.last_daily_sync_report_date == "2026-06-27"


@pytest.mark.asyncio
async def test_live_entry_decisions_match_execution_sim_for_same_signal_events(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    manager = LiveExecutionManager.__new__(LiveExecutionManager)
    manager._settings = settings
    manager._app_settings = _FakeAppSettings()
    manager._trading_client = _FakeTradingClient()
    manager._risk_calc = LiveRiskCalculator(settings)
    manager._state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
    )

    index = pd.to_datetime(
        [
            "2026-06-27 10:00:00+00:00",
            "2026-06-27 11:00:00+00:00",
            "2026-06-27 12:00:00+00:00",
        ]
    )
    events = [
        {
            "signal": 1,
            "sl_price": 98.0,
            "selected_strategy": "donor_long",
            "position_group": "donor_long",
            "risk_percent": 1.0,
            "rrr": 2.0,
            "position_ttl_bars": 24,
            "exit_geometry": "sl_rrr",
            "structural_sl_mode": "cap",
            "min_tp_move_pct": 0.004,
        },
        {
            "signal": -1,
            "sl_price": 102.0,
            "selected_strategy": "donor_short",
            "position_group": "donor_short",
            "risk_percent": 1.0,
            "rrr": 2.0,
            "position_ttl_bars": 32,
            "exit_geometry": "sl_rrr",
            "structural_sl_mode": "cap",
            "min_tp_move_pct": 0.004,
        },
    ]
    signal_df = pd.DataFrame(
        {
            "open": [99.0, 100.0, 100.0],
            "high": [99.5, 100.5, 100.5],
            "low": [98.5, 99.5, 99.5],
            "close": [99.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
            "signal_events": [events, [], []],
        },
        index=index,
    )
    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=settings.taker_fee,
        maker_fee=settings.maker_fee,
        risk_percent=settings.risk_percent,
        rrr=settings.rrr,
        max_positions=settings.max_positions,
        position_ttl_bars=settings.ttl_bars,
        max_allowed_leverage=settings.max_leverage,
        max_allowed_margin=settings.max_allowed_margin,
        risk_base_period=settings.risk_base_period,
        exit_geometry=settings.exit_geometry,
        structural_sl_mode="cap",
        min_tp_move_pct=0.004,
        instrument_precision_policy="okx_sol_usdt_swap_2026_07_01",
    )
    trades = sim.run(signal_df)

    batch = SignalBatch(
        bar_time=index[0].to_pydatetime(),
        next_time=index[1].to_pydatetime(),
        next_open=100.0,
        events=[
            SignalEvent(
                bar_time=index[0].to_pydatetime(),
                signal=int(event["signal"]),
                sl_price=float(event["sl_price"]),
                next_open=100.0,
                rrr=float(event["rrr"]),
                risk_percent=float(event["risk_percent"]),
                position_ttl_bars=int(event["position_ttl_bars"]),
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry=str(event["exit_geometry"]),
                tp_move_pct=None,
                structural_sl_mode=str(event["structural_sl_mode"]),
                min_tp_move_pct=float(event["min_tp_move_pct"]),
                selected_strategy=str(event["selected_strategy"]),
                position_group=str(event["position_group"]),
                raw_event=event,
            )
            for event in events
        ],
    )
    await manager._try_open_signal_batch("SOL-USDT-SWAP", batch, snapshot=None)  # type: ignore[arg-type]

    assert len(trades) == len(manager._state.positions) == 2
    for trade, live_pos in zip(trades.to_dict("records"), manager._state.positions, strict=True):
        assert live_pos.signal_dt == trade["signal_time"].to_pydatetime()
        assert live_pos.entry_dt == trade["entry_time"].to_pydatetime()
        assert live_pos.entry_price == pytest.approx(trade["entry_price"])
        assert live_pos.sl_price == pytest.approx(trade["sl_price"])
        assert live_pos.tp_price == pytest.approx(trade["tp_price"])
        assert live_pos.size == pytest.approx(trade["size"])
        assert live_pos.risk_base_capital == pytest.approx(trade["risk_base_capital"])
        assert live_pos.is_long == bool(trade["is_long"])
        assert live_pos.selected_strategy == trade["selected_strategy"]
        assert live_pos.ttl_bars == int(trade["position_ttl_bars"])
        assert live_pos.leverage == pytest.approx(trade["leverage"])
        assert live_pos.locked_margin == pytest.approx(trade["locked_margin"])
        assert live_pos.position_group == live_pos.selected_strategy


def test_execution_settings_must_match_strategy_backtest_args(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _validate_execution_settings_match_strategy(settings)

    mismatched = settings.model_copy(update={"rrr": 3.0})
    with pytest.raises(ValueError, match="strategy backtest_args"):
        _validate_execution_settings_match_strategy(mismatched)
