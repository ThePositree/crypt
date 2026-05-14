from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from crypt.models import Verdict
from crypt.sinks.base import BaseSink


class JsonLogSink(BaseSink):
    """
    Appends every verdict to a JSONL file (one JSON object per line).

    Runs synchronously inside the async emit — file I/O is fast enough
    for a 4h-tick system.
    """

    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def emit(self, verdict: Verdict, should_alert: bool) -> None:
        record = {
            **verdict.model_dump(mode="json"),
            "alerted": should_alert,
        }
        try:
            with self._path.open("a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as exc:
            logger.error("JsonLogSink write failed: {}", exc)
