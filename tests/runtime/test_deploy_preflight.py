from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from crypt.data.store import ParquetStore
from crypt.models import Candle, Timeframe
from crypt.runtime import deploy_preflight


def _candles(
    symbol: str,
    timeframe: Timeframe,
    start: datetime,
    count: int,
    step: timedelta,
) -> list[Candle]:
    return [
        Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=start + step * idx,
            o=Decimal("70"),
            h=Decimal("71"),
            low=Decimal("69"),
            c=Decimal("70.5"),
            volume=Decimal("1000"),
            closed=True,
        )
        for idx in range(count)
    ]


def _save_live_ohlcv(data_dir: Path, symbol: str, now: datetime) -> None:
    store = ParquetStore(data_dir)
    store.save_candles(
        _candles(symbol, Timeframe.H1, now - timedelta(hours=36), 35, timedelta(hours=1))
    )
    store.save_candles(
        _candles(symbol, Timeframe.H4, now - timedelta(hours=36), 9, timedelta(hours=4))
    )
    store.save_candles(
        _candles(symbol, Timeframe.D1, now - timedelta(days=3), 3, timedelta(days=1))
    )


def test_parse_data_types_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="unknown EXECUTION_BOOTSTRAP_DATA_TYPES"):
        deploy_preflight._parse_data_types("ohlcv,bad_type")


def test_zero_byte_parquet_files_are_removed(tmp_path: Path) -> None:
    broken = tmp_path / "SOL-USDT-SWAP" / "ohlcv_1h.parquet"
    broken.parent.mkdir(parents=True)
    broken.touch()

    removed = deploy_preflight._remove_zero_byte_parquet_files(tmp_path)

    assert removed == 1
    assert not broken.exists()


def test_ohlcv_coverage_accepts_recent_continuous_live_frames(tmp_path: Path) -> None:
    now = datetime(2026, 7, 19, 12, tzinfo=UTC)
    _save_live_ohlcv(tmp_path, "SOL-USDT-SWAP", now)

    issues = deploy_preflight._ohlcv_coverage_issues(
        data_dir=tmp_path,
        symbols=["SOL-USDT-SWAP"],
        now=now,
    )

    assert issues == []


def test_ohlcv_coverage_flags_empty_frames(tmp_path: Path) -> None:
    issues = deploy_preflight._ohlcv_coverage_issues(
        data_dir=tmp_path,
        symbols=["SOL-USDT-SWAP"],
        now=datetime(2026, 7, 19, 12, tzinfo=UTC),
    )

    assert {(issue.symbol, issue.timeframe) for issue in issues} == {
        ("SOL-USDT-SWAP", Timeframe.H1),
        ("SOL-USDT-SWAP", Timeframe.H4),
        ("SOL-USDT-SWAP", Timeframe.D1),
    }


@pytest.mark.asyncio
async def test_run_preflight_backfills_missing_live_ohlcv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    async def fake_run_backfill(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(deploy_preflight, "_run_backfill", fake_run_backfill)
    monkeypatch.setenv("EXECUTION_SYMBOLS", "SOL-USDT-SWAP")
    monkeypatch.setenv("EXECUTION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EXECUTION_BOOTSTRAP_FROM", "2026-07-01")
    monkeypatch.setenv("EXECUTION_BOOTSTRAP_TO", "2026-07-20")
    monkeypatch.setenv("EXECUTION_BOOTSTRAP_DATA_TYPES", "ohlcv")

    await deploy_preflight.run_preflight(now=datetime(2026, 7, 19, 12, tzinfo=UTC))

    assert calls == [
        {
            "symbol": "SOL-USDT-SWAP",
            "from_dt": datetime(2026, 7, 1, tzinfo=UTC),
            "to_dt": datetime(2026, 7, 20, tzinfo=UTC),
            "data_types": ["ohlcv"],
            "page_size": 100,
            "max_rps": 5.0,
            "data_dir": tmp_path,
        }
    ]


@pytest.mark.asyncio
async def test_run_preflight_skips_backfill_when_live_ohlcv_is_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 19, 12, tzinfo=UTC)
    _save_live_ohlcv(tmp_path, "SOL-USDT-SWAP", now)

    async def fail_run_backfill(**_kwargs: object) -> None:
        raise AssertionError("backfill should not run")

    monkeypatch.setattr(deploy_preflight, "_run_backfill", fail_run_backfill)
    monkeypatch.setenv("EXECUTION_SYMBOLS", "SOL-USDT-SWAP")
    monkeypatch.setenv("EXECUTION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EXECUTION_BOOTSTRAP_FROM", "2026-07-18")
    monkeypatch.setenv("EXECUTION_BOOTSTRAP_DATA_TYPES", "ohlcv")

    await deploy_preflight.run_preflight(now=now)
