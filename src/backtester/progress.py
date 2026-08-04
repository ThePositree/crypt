"""Small progress logging helpers for long CLI workflows."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass


def format_duration(seconds: float | None) -> str:
    """Format a duration for operator-facing progress logs."""
    if seconds is None:
        return "n/a"
    if seconds < 0 or seconds == float("inf"):
        return "n/a"
    rounded = int(seconds)
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


@dataclass
class ProgressLogger:
    """Rate-limited elapsed/rate/ETA logger."""

    logger: logging.Logger
    label: str
    total: int
    unit: str
    interval_s: float = 10.0

    def __post_init__(self) -> None:
        self.total = max(int(self.total), 0)
        self._started_at = time.monotonic()
        self._last_log_at = self._started_at
        self._last_done = 0
        self._finished = False
        self.logger.info("%s: started total=%d %s", self.label, self.total, self.unit)

    def update(self, done: int, *, force: bool = False) -> None:
        if self._finished:
            return
        done = max(0, min(int(done), self.total)) if self.total else max(0, int(done))
        now = time.monotonic()
        if not force and done < self.total and now - self._last_log_at < self.interval_s:
            return
        elapsed = now - self._started_at
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = max(self.total - done, 0)
        eta = remaining / rate if rate > 0 else None
        self.logger.info(
            "%s: %d/%d %s elapsed=%s rate=%.2f %s/s eta=%s",
            self.label,
            done,
            self.total,
            self.unit,
            format_duration(elapsed),
            rate,
            self.unit,
            format_duration(eta),
        )
        self._last_log_at = now
        self._last_done = done

    def finish(self, done: int | None = None) -> None:
        if self._finished:
            return
        done = self.total if done is None else done
        if done != self._last_done:
            self.update(done, force=True)
        elapsed = time.monotonic() - self._started_at
        self.logger.info("%s: finished elapsed=%s", self.label, format_duration(elapsed))
        self._finished = True


class HeartbeatLogger:
    """Periodic elapsed-time logger for phases without measurable progress."""

    def __init__(
        self,
        logger: logging.Logger,
        label: str,
        *,
        interval_s: float = 10.0,
    ) -> None:
        self.logger = logger
        self.label = label
        self.interval_s = interval_s
        self._started_at = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> HeartbeatLogger:
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, name=f"{self.label}-heartbeat", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            elapsed = time.monotonic() - self._started_at
            self.logger.info("%s: still running elapsed=%s eta=n/a", self.label, format_duration(elapsed))
