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
    assert "FULL SYNC" in text
    assert "BLOCKED" in text
    assert "position_mode_not_long_short" in text
    assert "Balance: total $10,000.00" in text


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
    assert "ENTRY" in bot.messages[0][1]
    assert "EXIT" in bot.messages[1][1]
    assert "PnL: $39.48" in bot.messages[1][1]
