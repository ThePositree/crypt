from __future__ import annotations

import argparse
import asyncio
import signal
import sys

from loguru import logger

from crypt.config import Settings
from crypt.runtime.orchestrator import Orchestrator
from crypt.runtime.scheduler import H4Scheduler


def _configure_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, colorize=True, enqueue=True)
    logger.add(
        "logs/crypt.log",
        level=level,
        rotation="100 MB",
        retention="30 days",
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
        help=(
            "Comma-separated OKX SWAP instrument IDs to monitor "
            "(overrides SYMBOLS env var)"
        ),
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


async def _main() -> None:
    args = _parse_args()
    settings = Settings()

    if args.symbols:
        # CLI override — reparse the comma-separated string.
        settings = settings.model_copy(
            update={"symbols": [s.strip() for s in args.symbols.split(",") if s.strip()]}
        )

    _configure_logging(settings.log_level)
    logger.info("Starting crypt — symbols: {}", settings.symbols)

    orchestrator = Orchestrator(settings)
    scheduler = H4Scheduler(orchestrator.tick)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("Received {}, shutting down…", sig.name)
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    try:
        if not args.no_bootstrap:
            await orchestrator.bootstrap()

        if args.once:
            await orchestrator.tick()
        else:
            scheduler.start()
            # Run one tick immediately so we don't wait up to 4h on startup.
            await orchestrator.tick()
            await stop_event.wait()
    finally:
        scheduler.stop()
        await orchestrator.close()
        logger.info("Shutdown complete")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
