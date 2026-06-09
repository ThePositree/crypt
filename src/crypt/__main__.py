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
from crypt.execution.executor import LiveExecutionManager
from crypt.execution.settings import ExecutionSettings
from crypt.runtime.health import run_health_check
from crypt.runtime.orchestrator import Orchestrator
from crypt.runtime.scheduler import H1Scheduler, H4Scheduler

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


def _maybe_build_execution_manager(
    app_settings: Settings,
) -> tuple[LiveExecutionManager, ExecutionSettings] | None:
    """
    Build LiveExecutionManager if execution is enabled.

    Returns None when EXECUTION_ENABLED is false or live trading is requested
    but OKX credentials are absent.
    """
    exec_settings = ExecutionSettings()
    if not exec_settings.enabled:
        return None

    if not exec_settings.dry_run and not app_settings.okx_is_authenticated:
        logger.error(
            "EXECUTION_DRY_RUN=false but OKX credentials are not configured — "
            "refusing to start live executor. Set EXECUTION_DRY_RUN=true or "
            "provide OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE."
        )
        return None

    mode = "DRY RUN" if exec_settings.dry_run else "LIVE"
    logger.info(
        "LiveExecutionManager enabled [{mode}] for symbols: {symbols}",
        mode=mode,
        symbols=exec_settings.symbols,
    )
    return LiveExecutionManager(exec_settings, app_settings), exec_settings


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
    h4_scheduler = H4Scheduler(orchestrator.tick)

    exec_bundle = _maybe_build_execution_manager(settings)
    h1_scheduler: H1Scheduler | None = None

    if exec_bundle is not None:
        exec_manager, exec_settings = exec_bundle

        async def _execution_tick() -> None:
            for sym in exec_settings.symbols:
                try:
                    await exec_manager.on_h1_close(sym)
                except Exception as exc:
                    logger.error("Execution tick failed for {}: {}", sym, exc)

        h1_scheduler = H1Scheduler(_execution_tick)

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

        # Reconcile live positions against OKX state on startup.
        if exec_bundle is not None:
            await exec_bundle[0].reconcile()

        if not args.no_bootstrap:
            await orchestrator.bootstrap()

        if args.once:
            await orchestrator.tick()
            if h1_scheduler is not None:
                await h1_scheduler.run_now()
        else:
            h4_scheduler.start()
            if h1_scheduler is not None:
                h1_scheduler.start()

            heartbeat_task = asyncio.create_task(
                _heartbeat_loop(settings, stop_event), name="heartbeat"
            )
            # Run one tick immediately so we don't wait up to 4h / 1h on startup.
            await orchestrator.tick()
            if h1_scheduler is not None:
                await h1_scheduler.run_now()

            await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        h4_scheduler.stop()
        if h1_scheduler is not None:
            h1_scheduler.stop()
        if exec_bundle is not None:
            await exec_bundle[0].close()
        await orchestrator.close()
        logger.info("Shutdown complete")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
