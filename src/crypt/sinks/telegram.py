from __future__ import annotations

import asyncio
import html
import random

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from crypt.models import Verdict
from crypt.sinks.base import BaseSink

_DECISION_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
_DECISION_LABEL = {
    "BUY": "рост (покупка)",
    "SELL": "снижение (продажа)",
    "HOLD": "без сделки",
}
_REGIME_LABEL = {
    "TRENDING": "выраженное движение",
    "RANGING": "боковой рынок",
    "VOLATILE": "повышенная волатильность",
    "UNKNOWN": "не определён",
}
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0  # seconds
_MAX_TELEGRAM_MESSAGE = 4_000
_MAX_ESCAPED_RATIONALE = 2_800
_MAX_ESCAPED_SYMBOL = 240


def _format_message(verdict: Verdict, *, uncalibrated: bool = True) -> str:
    emoji = _DECISION_EMOJI.get(verdict.decision, "⚪")
    decision_label = _DECISION_LABEL.get(verdict.decision, verdict.decision)
    title = (
        f"{emoji} <b>{_escape_bounded(verdict.symbol, _MAX_ESCAPED_SYMBOL)}</b> "
        f"— <b>{_escape_bounded(decision_label, _MAX_ESCAPED_SYMBOL)}</b>"
    )
    if uncalibrated:
        title += " ⚠️ <b>[UNCALIBRATED] модель ещё не откалибрована</b>"
    lines = [
        title,
        f"Уверенность модели: {verdict.confidence}% · оценка: {verdict.score:+.3f}",
        f"Состояние рынка: {_REGIME_LABEL.get(verdict.regime.value, verdict.regime.value)}",
        "",
        "Техническое объяснение:",
        f"<pre>{_escape_bounded(verdict.rationale, _MAX_ESCAPED_RATIONALE)}</pre>",
    ]
    return _limit_telegram_message(lines)


def _escape_bounded(value: object, limit: int) -> str:
    """Escape an operator field while preserving complete HTML entities."""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ↩ ")
    output: list[str] = []
    used = 0
    for char in text:
        encoded = html.escape(char, quote=False)
        if used + len(encoded) > limit - 1:
            output.append("…")
            break
        output.append(encoded)
        used += len(encoded)
    return "".join(output)


def _limit_telegram_message(lines: list[str]) -> str:
    """Return complete HTML lines only, under Telegram's 4096-character cap."""
    kept: list[str] = []
    for line in lines:
        candidate = "\n".join([*kept, line])
        if len(candidate) > _MAX_TELEGRAM_MESSAGE:
            break
        kept.append(line)
    return "\n".join(kept)


class TelegramSink(BaseSink):
    """
    Sends BUY/SELL alerts to a Telegram chat via aiogram.

    Retries up to _MAX_RETRIES times with exponential backoff on network errors.
    Failures are logged but never raised — the verdict is always persisted by
    other sinks regardless.

    When ``uncalibrated=True`` (default), every alert includes the canonical
    ``[UNCALIBRATED]`` marker plus a Russian explanation per ADR-0011. Flip
    to ``False`` only after M2 produces calibrated weights and ADR-0013
    ratifies them.
    """

    def __init__(self, bot_token: str, chat_id: str, *, uncalibrated: bool = True) -> None:
        self._bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._chat_id = chat_id
        self._uncalibrated = uncalibrated

    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        if not should_alert:
            return
        if verdict.decision == "HOLD":
            return

        text = _format_message(verdict, uncalibrated=self._uncalibrated)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._bot.send_message(self._chat_id, text)
                logger.info("Telegram alert sent: {} {}", verdict.symbol, verdict.decision)
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error("Telegram send failed after {} retries: {}", _MAX_RETRIES, exc)
                else:
                    # Full-jitter: uniform(0.5, 1.5) multiplier avoids
                    # thundering-herd when multiple symbols retry at once.
                    wait = (_RETRY_BACKOFF**attempt) * random.uniform(0.5, 1.5)
                    logger.warning(
                        "Telegram send attempt {}/{} failed ({}), retrying in {:.1f}s",
                        attempt,
                        _MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)

    async def close(self) -> None:
        await self._bot.session.close()
