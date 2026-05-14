from __future__ import annotations

from loguru import logger

from crypt.models import Verdict
from crypt.sinks.base import BaseSink


class ExecutionStub(BaseSink):
    """
    Placeholder execution sink — logs the verdict but does not place any order.

    This stub will be replaced with a real OKX order router in M4.
    Only fires when should_alert=True (i.e. the verdict passed the decision layer).
    """

    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        if not should_alert or verdict.decision == "HOLD":
            return
        logger.info(
            "[EXECUTION STUB] Would execute {} {} conf={}% (no order placed)",
            verdict.decision,
            verdict.symbol,
            verdict.confidence,
        )
