from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from backtester.execution_sim import ExecutionSim
from crypt.execution.exchange_sync import ExchangeBalance, ExchangePosition, ExchangeSnapshot
from crypt.execution.executor import (
    LiveExecutionManager,
    _validate_execution_settings_match_strategy,
)
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

    async def set_isolated_leverage(self, symbol: str, leverage: int) -> None:
        self.leverage = (symbol, leverage)

    async def get_contract_size(self, symbol: str) -> float:  # noqa: ARG002
        return 1.0

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
    ) -> str:
        self.opened.append(
            {
                "symbol": okx_symbol,
                "is_long": is_long,
                "size": size_asset_units,
                "sl_price": sl_price,
                "tp_price": tp_price,
            }
        )
        return f"order-{len(self.opened)}"


class _SyncingTradingClient(_FakeTradingClient):
    async def get_exchange_snapshot(self, symbols: list[str]) -> ExchangeSnapshot:
        positions = []
        if self.opened:
            positions = [
                ExchangePosition(
                    symbol=symbols[0],
                    contracts=float(len(self.opened)),
                    side="long" if bool(self.opened[-1]["is_long"]) else "short",
                )
            ]
        return ExchangeSnapshot(
            fetched_at=datetime(2026, 6, 27, 11, tzinfo=UTC),
            balance=ExchangeBalance(total=10_000.0, free=9_000.0, used=1_000.0),
            positions=positions,
            open_orders=[],
            algo_orders=[],
            recent_fills=[],
        )


class _BatchSignalRunner:
    def __init__(self, batch: SignalBatch) -> None:
        self.batch = batch
        self.refreshed: list[str] = []

    async def refresh_candles(self, symbol: str) -> None:
        self.refreshed.append(symbol)

    def get_latest_signal_batch(self, symbol: str) -> SignalBatch:  # noqa: ARG002
        return self.batch


class _FakeNotifier:
    def __init__(self) -> None:
        self.daily: list[tuple[ExchangeSnapshot, ExecutionState]] = []
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

    async def send_position_closed(self, pos: LivePosition) -> None:
        self.exits.append(pos)

    async def close(self) -> None:
        return None


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

    assert [pos.symbol for pos in notifier.entries] == ["SOL-USDT-SWAP"]


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
    assert [pos.selected_strategy for pos in manager._state.all_open_positions()] == [
        "new_donor"
    ]
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
        positions=[ExchangePosition(symbol="SOL-USDT-SWAP", contracts=10.0)],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
    )

    await manager._manage_open_positions("SOL-USDT-SWAP", snapshot)

    assert pos.status == "open"


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
    assert pos.exit_fee == pytest.approx(0.52)


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
