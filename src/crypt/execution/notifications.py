"""Telegram notifications for live execution state changes."""

from __future__ import annotations

import asyncio
import html
import random
from dataclasses import dataclass

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from crypt.config import Settings
from crypt.execution.exchange_sync import ExchangeSnapshot
from crypt.execution.position_state import ExecutionState, LivePosition

_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0


@dataclass(frozen=True)
class ExecutionTelegramNotifier:
    """Best-effort Telegram notifier for live execution events."""

    _bot: Bot
    _chat_id: str
    _dry_run: bool

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        dry_run: bool,
    ) -> ExecutionTelegramNotifier | None:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return None
        bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        return cls(_bot=bot, _chat_id=settings.telegram_chat_id, _dry_run=dry_run)

    async def send_daily_sync_report(
        self,
        *,
        snapshot: ExchangeSnapshot,
        state: ExecutionState,
    ) -> None:
        lines = [
            _title("FULL SYNC", ok=state.last_exchange_sync_ok, dry_run=self._dry_run),
            f"Time: {_esc(snapshot.fetched_at.isoformat())}",
            (
                "Balance: "
                f"total ${snapshot.balance.total:,.2f} | "
                f"free ${snapshot.balance.free:,.2f} | "
                f"used ${snapshot.balance.used:,.2f}"
            ),
            f"Position mode: {'long/short' if snapshot.position_mode_hedged else 'NOT long/short'}",
            f"Local open positions: {len(state.all_open_positions())}",
            f"Exchange positions: {len(snapshot.positions)}",
            f"Regular orders: {len(snapshot.open_orders)}",
            f"Algo orders: {len(snapshot.algo_orders)}",
            f"Sync: {'OK' if state.last_exchange_sync_ok else 'BLOCKED'}",
        ]
        if state.last_exchange_sync_errors:
            lines.append("Blocking reasons:")
            lines.extend(f"- {_esc(reason)}" for reason in state.last_exchange_sync_errors)
        open_positions = state.all_open_positions()
        if open_positions:
            lines.append("")
            lines.append("Local positions:")
            for pos in open_positions[:12]:
                lines.append(_position_line(pos))
            if len(open_positions) > 12:
                lines.append(f"... +{len(open_positions) - 12} more")
        await self._send("\n".join(lines))

    async def send_entry_opened(self, pos: LivePosition) -> None:
        side = "LONG" if pos.is_long else "SHORT"
        text = "\n".join(
            [
                _title("ENTRY", ok=True, dry_run=self._dry_run),
                f"{_esc(pos.symbol)} {side}",
                f"Contracts: {pos.contracts} | size: {pos.size:.4f}",
                f"Entry: ${pos.entry_price:,.4f}",
                f"SL: ${pos.sl_price:,.4f} | TP: ${pos.tp_price:,.4f}",
                f"Margin: ${pos.locked_margin:,.2f} | leverage: {pos.leverage:.0f}x",
                f"Risk base: ${pos.risk_base_capital:,.2f}",
                f"Order: {_esc(pos.entry_order_id or 'dry-run')}",
            ]
        )
        await self._send(text)

    async def send_position_closed(self, pos: LivePosition) -> None:
        side = "LONG" if pos.is_long else "SHORT"
        lines = [
            _title("EXIT", ok=True, dry_run=self._dry_run),
            f"{_esc(pos.symbol)} {side}",
            f"Reason: {_esc(pos.exit_reason or 'unknown')}",
            f"Entry: ${pos.entry_price:,.4f}",
        ]
        if pos.exit_price is not None:
            lines.append(f"Exit: ${pos.exit_price:,.4f}")
        if pos.realized_pnl is not None:
            lines.append(f"PnL: ${pos.realized_pnl:,.2f}")
        if pos.exit_fee is not None:
            lines.append(f"Exit fee: ${pos.exit_fee:,.2f}")
        lines.append(f"Position: {_esc(pos.position_id[:8])}")
        await self._send("\n".join(lines))

    async def _send(self, text: str) -> None:
        import logging

        logger = logging.getLogger(__name__)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._bot.send_message(self._chat_id, text)
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error("Execution Telegram send failed after %d retries: %s", _MAX_RETRIES, exc)
                    return
                wait = (_RETRY_BACKOFF**attempt) * random.uniform(0.5, 1.5)
                logger.warning(
                    "Execution Telegram send attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

    async def close(self) -> None:
        await self._bot.session.close()


def _title(kind: str, *, ok: bool, dry_run: bool) -> str:
    marker = "DRY RUN" if dry_run else "LIVE"
    status = "OK" if ok else "BLOCKED"
    return f"<b>{kind}</b> [{marker}] [{status}]"


def _position_line(pos: LivePosition) -> str:
    side = "LONG" if pos.is_long else "SHORT"
    return (
        f"- {_esc(pos.symbol)} {side} {pos.contracts} contracts | "
        f"entry ${pos.entry_price:,.4f} | SL ${pos.sl_price:,.4f} | TP ${pos.tp_price:,.4f}"
    )


def _esc(value: object) -> str:
    return html.escape(str(value), quote=False)
