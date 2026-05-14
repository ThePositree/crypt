from __future__ import annotations

from abc import ABC, abstractmethod

from crypt.models import Verdict


class BaseSink(ABC):
    """All sinks must implement this interface."""

    @abstractmethod
    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        """
        Receive a verdict.

        ``should_alert`` indicates whether the decision layer approved an alert
        for real-time notification channels (e.g. Telegram).
        Non-alert sinks (JsonLogSink, ConsoleSink) should ignore this flag.
        """
        ...

    async def close(self) -> None:  # noqa: B027
        """Optional teardown — called once on shutdown."""
