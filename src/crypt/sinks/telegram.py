from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger

from crypt.models import Verdict
from crypt.sinks.base import BaseSink

_DECISION_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0  # seconds


def _format_message(verdict: Verdict) -> str:
    emoji = _DECISION_EMOJI.get(verdict.decision, "⚪")
    lines = [
        f"{emoji} <b>{verdict.symbol}</b> — <b>{verdict.decision}</b>",
        f"Confidence: {verdict.confidence}%   Score: {verdict.score:+.3f}",
        f"Regime: {verdict.regime.value}",
        "",
        f"<pre>{verdict.rationale}</pre>",
    ]
    return "\n".join(lines)


class TelegramSink(BaseSink):
    """
    Sends BUY/SELL alerts to a Telegram chat via aiogram.

    Retries up to _MAX_RETRIES times with exponential backoff on network errors.
    Failures are logged but never raised — the verdict is always persisted by
    other sinks regardless.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
        self._chat_id = chat_id

    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        if not should_alert:
            return
        if verdict.decision == "HOLD":
            return

        text = _format_message(verdict)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._bot.send_message(self._chat_id, text)
                logger.info("Telegram alert sent: {} {}", verdict.symbol, verdict.decision)
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "Telegram send failed after {} retries: {}", _MAX_RETRIES, exc
                    )
                else:
                    wait = _RETRY_BACKOFF ** attempt
                    logger.warning(
                        "Telegram send attempt {}/{} failed ({}), retrying in {:.0f}s",
                        attempt,
                        _MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)

    async def close(self) -> None:
        await self._bot.session.close()
