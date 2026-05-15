from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from crypt.config import Settings
from crypt.runtime.health import run_health_check
from crypt.runtime.orchestrator import Orchestrator
from crypt.runtime.scheduler import H4Scheduler

_HEARTBEAT_INTERVAL_S = 30 * 60  # 30 minutes
_OKX_HEALTH_INTERVAL_S = 6 * 60 * 60  # 6 hours


def _configure_logging(level: str, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    tty = sys.stderr.isatty()
    # INFO and below → stdout so Railway tags them [inf] instead of [err].
    logger.add(
        sys.stdout,
        level=level,
        filter=lambda r: r["level"].no < 30,  # no=30 is WARNING
        colorize=tty,
        enqueue=tty,
    )
    # WARNING and above → stderr (Railway [err] is appropriate here).
    logger.add(sys.stderr, level="WARNING", colorize=tty, enqueue=tty)
    logger.add(
        log_dir / "crypt.log",
        level=level,
        # Rotate at midnight UTC so each day gets its own file.
        rotation="00:00",
        retention="30 days",
        compression="gz",
        serialize=True,
        enqueue=True,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="crypt",
        description="Ensemble decision system for OKX perpetual futures",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help=("Comma-separated OKX SWAP instrument IDs to monitor (overrides SYMBOLS env var)"),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one tick immediately then exit (useful for testing)",
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Skip the initial history bootstrap (assume data is already present)",
    )
    return parser.parse_args()


async def _heartbeat_loop(settings: Settings, stop_event: asyncio.Event) -> None:
    """
    Logs a liveness line every 30 minutes and re-runs the OKX health check
    every 6 hours so prolonged outages are surfaced between ticks.
    """
    last_okx_check = datetime.now(tz=UTC)
    while not stop_event.is_set():
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=_HEARTBEAT_INTERVAL_S)

        if stop_event.is_set():
            break

        now = datetime.now(tz=UTC)
        elapsed_since_okx = (now - last_okx_check).total_seconds()

        logger.info("Heartbeat: alive at {}", now.isoformat())

        if elapsed_since_okx >= _OKX_HEALTH_INTERVAL_S:
            logger.info("Periodic OKX health check…")
            await run_health_check(settings)
            last_okx_check = now


async def _main() -> None:
    args = _parse_args()
    settings = Settings()

    if args.symbols:
        # CLI override — reparse the comma-separated string.
        settings = settings.model_copy(
            update={"symbols": [s.strip() for s in args.symbols.split(",") if s.strip()]}
        )

    _configure_logging(settings.log_level, settings.log_dir)
    logger.info("Starting crypt — symbols: {}", settings.symbols)

    orchestrator = Orchestrator(settings)
    scheduler = H4Scheduler(orchestrator.tick)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    main_task = asyncio.current_task()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("Received {}, shutting down…", sig.name)
        stop_event.set()
        # Cancel the main task so that any in-progress await (health check,
        # bootstrap, tick) is interrupted immediately rather than running
        # to completion before the stop_event is checked.
        if main_task is not None and not main_task.done():
            main_task.cancel()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    heartbeat_task: asyncio.Task[None] | None = None

    try:
        await run_health_check(settings)

        if not args.no_bootstrap:
            await orchestrator.bootstrap()

        if args.once:
            await orchestrator.tick()
        else:
            scheduler.start()
            heartbeat_task = asyncio.create_task(
                _heartbeat_loop(settings, stop_event), name="heartbeat"
            )
            # Run one tick immediately so we don't wait up to 4h on startup.
            await orchestrator.tick()
            await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        scheduler.stop()
        await orchestrator.close()
        logger.info("Shutdown complete")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
