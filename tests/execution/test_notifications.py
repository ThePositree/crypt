# ruff: noqa: RUF001

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crypt.execution.exchange_sync import ExchangeBalance, ExchangeSnapshot
from crypt.execution.notifications import ExecutionTelegramNotifier
from crypt.execution.position_state import ExecutionState, LivePosition


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.session = _FakeSession()

    async def send_message(self, chat_id: str, text: str) -> None:
        self.messages.append((chat_id, text))


@pytest.mark.asyncio
async def test_daily_sync_report_includes_blocking_reasons() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=True,
    )
    state = ExecutionState(
        schema_version=2,
        risk_window_month=None,
        monthly_risk_base=10_000.0,
        positions=[],
        last_exchange_sync_ok=False,
        last_exchange_sync_errors=["position_mode_not_long_short"],
    )
    snapshot = ExchangeSnapshot(
        fetched_at=datetime(2026, 6, 28, 12, tzinfo=UTC),
        balance=ExchangeBalance(total=10_000.0, free=9_500.0, used=500.0),
        positions=[],
        open_orders=[],
        algo_orders=[],
        recent_fills=[],
        position_mode_hedged=False,
    )

    await notifier.send_daily_sync_report(snapshot=snapshot, state=state)

    assert bot.messages
    text = bot.messages[0][1]
    assert "Проверка бота" in text
    assert "входы остановлены" in text
    assert "position_mode_not_long_short" in text
    assert "Баланс: всего $10,000.00" in text


@pytest.mark.asyncio
async def test_entry_and_exit_messages_are_sent() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=False,
    )
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 28, 10, tzinfo=UTC),
        entry_time=datetime(2026, 6, 28, 11, tzinfo=UTC),
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
    )
    await notifier.send_entry_opened(pos)
    pos.status = "closed"
    pos.exit_reason = "take_profit"
    pos.exit_price = 104.0
    pos.realized_pnl = 39.48
    await notifier.send_position_closed(pos)

    assert len(bot.messages) == 2
    assert "Сделка открыта" in bot.messages[0][1]
    assert "Сделка закрыта" in bot.messages[1][1]
    assert "PnL: $39.48" in bot.messages[1][1]


@pytest.mark.asyncio
async def test_entry_attempt_rejection_and_execution_error_are_sent() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=True,
    )

    await notifier.send_entry_attempt(
        symbol="SOL-USDT-SWAP",
        is_long=False,
        strategy="dss_donor",
        signal_time=datetime(2026, 6, 29, 10, tzinfo=UTC),
        entry_price=145.25,
        sl_price=147.10,
    )
    await notifier.send_entry_rejected(
        symbol="SOL-USDT-SWAP",
        is_long=False,
        strategy="dss_donor",
        reason="insufficient margin",
    )
    await notifier.send_execution_error(
        context="place entry for SOL-USDT-SWAP",
        detail="ExchangeError: order rejected",
    )

    assert len(bot.messages) == 3
    assert "Найден сигнал" in bot.messages[0][1]
    assert "Сигнал передан на проверку" in bot.messages[0][1]
    assert "dss_donor" in bot.messages[0][1]
    assert "Вход пропущен" in bot.messages[1][1]
    assert "insufficient margin" in bot.messages[1][1]
    assert "Нужна проверка" in bot.messages[2][1]
    assert "order rejected" in bot.messages[2][1]


@pytest.mark.asyncio
async def test_entry_drift_message_states_that_entry_was_executed() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=False,
    )

    await notifier.send_entry_drift_alert(
        symbol="SOL-USDT-SWAP",
        strategy="smac_donor",
        h1_open=100.0,
        quote=100.8,
        fill=101.0,
        h1_fill_drift_pct=0.01,
        quote_fill_drift_pct=0.001984,
    )

    text = bot.messages[0][1]
    assert "Цена входа отличается от плана" in text
    assert "Сделка уже открыта" in text
    assert "Отклонение от плана: 1.000%" in text


@pytest.mark.asyncio
async def test_missed_signal_and_risk_base_blocker_are_plain_russian_alerts() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=False,
    )

    await notifier.send_missed_signal(
        symbol="SOL-USDT-SWAP",
        is_long=False,
        strategy="donor_short",
        signal_time=datetime(2026, 7, 23, 12, tzinfo=UTC),
        entry_price=76.90,
        sl_price=77.71,
        blocking_reasons=["position_size_mismatch:SOL-USDT-SWAP"],
        cumulative_count=1,
    )
    await notifier.send_risk_base_continuity_blocked(
        reason="state and checkpoint disagree",
        checkpoint_dir="/app/data/risk_base_checkpoints",
        state_path="/app/data/live_positions.json",
    )

    assert "Сигнал пропущен из-за защиты" in bot.messages[0][1]
    assert "Ордер не отправлен" in bot.messages[0][1]
    assert "Всего пропущено из-за защиты: 1" in bot.messages[0][1]
    assert "Проверка риск-базы не пройдена" in bot.messages[1][1]
    assert "Новые входы остановлены" in bot.messages[1][1]


@pytest.mark.asyncio
async def test_dynamic_execution_error_is_escaped_and_kept_within_telegram_limit() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=False,
    )

    await notifier.send_execution_error(
        context="place entry for <untrusted>",
        detail="&<>" * 2_000,
    )

    text = bot.messages[0][1]
    assert len(text) <= 4_000
    assert "&lt;untrusted&gt;" in text
    assert "&amp;&lt;&gt;" in text


@pytest.mark.asyncio
async def test_opened_trade_uses_the_asset_from_its_symbol() -> None:
    bot = _FakeBot()
    notifier = ExecutionTelegramNotifier(
        _bot=bot,  # type: ignore[arg-type]
        _chat_id="chat-1",
        _dry_run=False,
    )
    pos = LivePosition.create(
        symbol="TON-USDT-SWAP",
        signal_time=datetime(2026, 7, 28, 10, tzinfo=UTC),
        entry_time=datetime(2026, 7, 28, 11, tzinfo=UTC),
        entry_price=3.0,
        sl_price=2.8,
        tp_price=3.4,
        size=10.0,
        contracts=10.0,
        leverage=25.0,
        locked_margin=1.2,
        risk_base_capital=100.0,
        is_long=True,
        ttl_bars=0,
        entry_order_id="entry-1",
    )

    await notifier.send_entry_opened(pos)

    assert "10.0000 TON" in bot.messages[0][1]
