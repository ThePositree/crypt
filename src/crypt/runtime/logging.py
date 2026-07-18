from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger


class InterceptStdlibLogging(logging.Handler):
    """Forward standard-library logging records into loguru sinks."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def _stdlib_level(level: str) -> int:
    value = logging.getLevelNamesMapping().get(level.upper())
    if isinstance(value, int):
        return value
    return logging.INFO


def configure_runtime_logging(level: str, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    normalized_level = level.upper()
    configured_no = _stdlib_level(normalized_level)
    stderr_level = "WARNING" if configured_no < logging.WARNING else normalized_level
    tty = sys.stderr.isatty()

    logger.remove()
    logger.add(
        sys.stdout,
        level=normalized_level,
        filter=lambda record: record["level"].no < logging.WARNING,
        colorize=tty,
        enqueue=tty,
    )
    logger.add(sys.stderr, level=stderr_level, colorize=tty, enqueue=tty)
    logger.add(
        log_dir / "crypt.log",
        level=normalized_level,
        rotation="00:00",
        retention="30 days",
        compression="gz",
        serialize=True,
        enqueue=True,
    )
    logging.basicConfig(
        handlers=[InterceptStdlibLogging()],
        level=configured_no,
        force=True,
    )
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
