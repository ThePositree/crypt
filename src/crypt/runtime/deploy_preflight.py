from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pandas as pd
from loguru import logger

from crypt.backfill.__main__ import _parse_date, _run_backfill
from crypt.config import Settings
from crypt.data.store import ParquetStore
from crypt.execution.settings import ExecutionSettings
from crypt.models import Timeframe
from crypt.runtime.logging import configure_runtime_logging

_VALID_BOOTSTRAP_DATA_TYPES = {
    "ohlcv",
    "execution_1m",
    "last_1m",
    "mark_1m",
    "oi",
    "ls_ratio",
    "taker_vol",
}
_LIVE_OHLCV_TIMEFRAMES = (Timeframe.H1, Timeframe.H4, Timeframe.D1)
_TIMEFRAME_STEPS = {
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}
_MAX_LIVE_STALENESS = {
    Timeframe.H1: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=12),
    Timeframe.D1: timedelta(days=3),
}
_DEFAULT_BOOTSTRAP_FROM = "2021-12-18"
_DEFAULT_BOOTSTRAP_DATA_TYPES = "ohlcv"


@dataclass(frozen=True)
class CoverageIssue:
    symbol: str
    timeframe: Timeframe
    reason: str


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _parse_data_types(raw: str | None) -> list[str]:
    value = raw if raw is not None and raw.strip() else _DEFAULT_BOOTSTRAP_DATA_TYPES
    data_types = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(data_types) - _VALID_BOOTSTRAP_DATA_TYPES)
    if unknown:
        valid = ", ".join(sorted(_VALID_BOOTSTRAP_DATA_TYPES))
        raise ValueError(
            f"unknown EXECUTION_BOOTSTRAP_DATA_TYPES values: {unknown}; valid: {valid}"
        )
    return data_types


def _default_to_dt(now: datetime) -> datetime:
    next_midnight = datetime(now.year, now.month, now.day, tzinfo=UTC) + timedelta(days=1)
    return next_midnight + timedelta(days=_env_int("EXECUTION_BOOTSTRAP_TO_BUFFER_DAYS", 1))


def _parse_from_dt() -> datetime:
    return _parse_date(os.getenv("EXECUTION_BOOTSTRAP_FROM", _DEFAULT_BOOTSTRAP_FROM))


def _parse_to_dt(now: datetime) -> datetime:
    raw = os.getenv("EXECUTION_BOOTSTRAP_TO")
    if raw is not None and raw.strip():
        return _parse_date(raw.strip())
    return _default_to_dt(now)


def _zero_byte_parquet_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted(path for path in data_dir.rglob("*.parquet") if path.stat().st_size == 0)


def _remove_zero_byte_parquet_files(data_dir: Path) -> int:
    removed = 0
    for path in _zero_byte_parquet_files(data_dir):
        logger.warning("Removing zero-byte parquet before backfill: {}", path)
        path.unlink()
        removed += 1
    return removed


def _has_gap(frame: pd.DataFrame, timeframe: Timeframe) -> bool:
    if len(frame) < 2:
        return False
    timestamps = pd.Series(pd.to_datetime(frame["open_time"], utc=True)).sort_values()
    return bool((timestamps.diff().dropna() > _TIMEFRAME_STEPS[timeframe]).any())


def _latest_timestamp(frame: pd.DataFrame) -> datetime:
    latest = pd.to_datetime(frame["open_time"], utc=True).max()
    return cast(datetime, latest.to_pydatetime())


def _earliest_timestamp(frame: pd.DataFrame) -> datetime:
    earliest = pd.to_datetime(frame["open_time"], utc=True).min()
    return cast(datetime, earliest.to_pydatetime())


def _ohlcv_coverage_issues(
    *,
    data_dir: Path,
    symbols: list[str],
    now: datetime,
    from_dt: datetime | None = None,
) -> list[CoverageIssue]:
    store = ParquetStore(data_dir)
    issues: list[CoverageIssue] = []
    for symbol in symbols:
        for timeframe in _LIVE_OHLCV_TIMEFRAMES:
            try:
                candles = store.load_candles(symbol, timeframe)
            except RuntimeError as exc:
                issues.append(CoverageIssue(symbol, timeframe, f"unreadable parquet: {exc}"))
                continue

            if candles.empty:
                issues.append(CoverageIssue(symbol, timeframe, "missing or empty parquet"))
                continue

            if from_dt is not None:
                earliest = _earliest_timestamp(candles)
                if earliest > from_dt + _TIMEFRAME_STEPS[timeframe]:
                    issues.append(
                        CoverageIssue(
                            symbol,
                            timeframe,
                            f"history starts too late: {earliest.isoformat()}",
                        )
                    )
                    continue

            if _has_gap(candles, timeframe):
                issues.append(CoverageIssue(symbol, timeframe, "historical candle gap"))
                continue

            latest = _latest_timestamp(candles)
            if latest < now - _MAX_LIVE_STALENESS[timeframe]:
                issues.append(
                    CoverageIssue(
                        symbol,
                        timeframe,
                        f"latest candle is stale: {latest.isoformat()}",
                    )
                )
    return issues


async def run_preflight(now: datetime | None = None) -> None:
    if not _env_bool("EXECUTION_BOOTSTRAP_ENABLED", True):
        logger.info("Execution bootstrap preflight disabled")
        return

    now = now or datetime.now(UTC)
    settings = Settings()
    execution_settings = ExecutionSettings()
    data_dir = execution_settings.data_dir
    symbols = execution_settings.symbols if execution_settings.symbols else settings.symbols
    data_types = _parse_data_types(os.getenv("EXECUTION_BOOTSTRAP_DATA_TYPES"))
    from_dt = _parse_from_dt()
    to_dt = _parse_to_dt(now)
    if to_dt <= from_dt:
        raise ValueError("EXECUTION_BOOTSTRAP_TO must be after EXECUTION_BOOTSTRAP_FROM")

    data_dir.mkdir(parents=True, exist_ok=True)
    removed = _remove_zero_byte_parquet_files(data_dir)
    issues = (
        _ohlcv_coverage_issues(data_dir=data_dir, symbols=symbols, now=now, from_dt=from_dt)
        if "ohlcv" in data_types
        else []
    )
    force = _env_bool("EXECUTION_BOOTSTRAP_FORCE", False)
    non_ohlcv_requested = any(item != "ohlcv" for item in data_types)
    needs_backfill = force or bool(issues) or non_ohlcv_requested or removed > 0

    if not needs_backfill:
        logger.info(
            "Railway live preflight OK: data_dir={} symbols={} data_types={} no backfill needed",
            data_dir,
            symbols,
            data_types,
        )
        return

    for issue in issues:
        logger.warning(
            "Railway live preflight requires backfill: {} {} {}",
            issue.symbol,
            issue.timeframe.value,
            issue.reason,
        )

    page_size = min(_env_int("EXECUTION_BOOTSTRAP_PAGE_SIZE", 100), 100)
    max_rps = _env_float("EXECUTION_BOOTSTRAP_MAX_RPS", 5.0)
    logger.info(
        "Railway live preflight backfill starting: data_dir={} symbols={} from={} to={} "
        "types={} page_size={} max_rps={}",
        data_dir,
        symbols,
        from_dt.date(),
        to_dt.date(),
        data_types,
        page_size,
        max_rps,
    )
    for symbol in symbols:
        await _run_backfill(
            symbol=symbol,
            from_dt=from_dt,
            to_dt=to_dt,
            data_types=data_types,
            page_size=page_size,
            max_rps=max_rps,
            data_dir=data_dir,
        )
    logger.info("Railway live preflight backfill complete")


def main() -> None:
    settings = Settings()
    configure_runtime_logging(settings.log_level, settings.log_dir)
    asyncio.run(run_preflight())


if __name__ == "__main__":
    main()
