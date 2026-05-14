from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


class H4Scheduler:
    """
    Fires a coroutine callback on every 4h boundary (00:00, 04:00, 08:00,
    12:00, 16:00, 20:00 UTC), allowing a small offset so candles are
    confirmed closed on the exchange before we pull them.

    offset_minutes: how many minutes after the boundary to wait before
    triggering (default 2 — gives the exchange time to close the candle).
    """

    def __init__(
        self,
        callback: Callable[[], Coroutine[Any, Any, None]],
        offset_minutes: int = 2,
    ) -> None:
        self._callback = callback
        self._offset = offset_minutes
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        trigger = CronTrigger(
            hour="0,4,8,12,16,20",
            minute=str(self._offset),
            second=0,
            timezone="UTC",
        )
        self._scheduler.add_job(
            self._run,
            trigger=trigger,
            id="h4_tick",
            max_instances=1,
            misfire_grace_time=300,
        )
        self._scheduler.start()
        logger.info(
            "H4Scheduler started — fires at *:00+{}m UTC on 4h boundaries",
            self._offset,
        )

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("H4Scheduler stopped")

    async def _run(self) -> None:
        now = datetime.now(tz=UTC)
        logger.info("H4 tick at {}", now.isoformat())
        try:
            await self._callback()
        except Exception as exc:
            logger.error("H4 tick callback error: {}", exc)

    async def run_now(self) -> None:
        """Trigger one immediate tick (used for bootstrap / manual testing)."""
        await self._run()
