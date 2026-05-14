from __future__ import annotations

from loguru import logger

from crypt.models import Verdict
from crypt.sinks.base import BaseSink

_DECISION_ICON = {"BUY": "▲", "SELL": "▼", "HOLD": "—"}


class ConsoleSink(BaseSink):
    """Logs every verdict to stdout/loguru at INFO level."""

    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        icon = _DECISION_ICON.get(verdict.decision, "?")
        alert_tag = " [ALERT]" if should_alert else ""
        logger.info(
            "{}{} {} {} | conf={}% score={:+.3f} regime={}",
            icon,
            alert_tag,
            verdict.symbol,
            verdict.decision,
            verdict.confidence,
            verdict.score,
            verdict.regime.value,
        )
        for line in verdict.rationale.split("\n"):
            logger.debug("  {}", line)
