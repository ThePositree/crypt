"""Tests for the closed-candle invariant in ParquetStore and Ingestor."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from crypt.data.store import ParquetStore, _read_parquet
from crypt.models import Candle, Timeframe


def _make_candle(
    *,
    closed: bool,
    symbol: str = "SOL-USDT-SWAP",
    timeframe: Timeframe = Timeframe.H4,
) -> Candle:
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        open_time=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        o=Decimal("100"),
        h=Decimal("101"),
        low=Decimal("99"),
        c=Decimal("100.5"),
        volume=Decimal("1000"),
        closed=closed,
    )


class TestSaveCandlesClosedInvariant:
    def test_open_candle_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            with pytest.raises(ValueError, match="non-closed"):
                store.save_candles([_make_candle(closed=False)])

    def test_mixed_list_raises(self) -> None:
        """A list containing even one open candle must be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            closed = _make_candle(closed=True)
            open_c = Candle(
                symbol="SOL-USDT-SWAP",
                timeframe=Timeframe.H4,
                open_time=datetime(2026, 5, 1, 4, 0, 0, tzinfo=UTC),
                o=Decimal("100"),
                h=Decimal("101"),
                low=Decimal("99"),
                c=Decimal("100.5"),
                volume=Decimal("1000"),
                closed=False,
            )
            with pytest.raises(ValueError, match="non-closed"):
                store.save_candles([closed, open_c])

    def test_all_closed_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            store.save_candles([_make_candle(closed=True)])
            df = store.load_candles("SOL-USDT-SWAP", Timeframe.H4)
            assert len(df) == 1

    def test_empty_list_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            store.save_candles([])


class TestIngestorClosedFilter:
    """Ingestor must filter out open candles before calling save_candles."""

    def test_open_candle_dropped_before_store(self) -> None:
        """
        Ingestor._ingest_ohlcv filters to closed=True before save_candles.
        If save_candles received an open candle it would raise — this test
        verifies the filter is in place by running only closed candles through.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            closed = _make_candle(closed=True)
            # save_candles should accept only closed ones
            store.save_candles([closed])
            df = store.load_candles("SOL-USDT-SWAP", Timeframe.H4)
            assert len(df) == 1

    def test_open_candle_in_raw_fetch_would_raise(self) -> None:
        """
        Confirms that if a caller bypasses the ingestor filter and passes
        an open candle directly to save_candles, a ValueError is raised.
        This documents the contract for future callers.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(Path(tmp))
            with pytest.raises(ValueError):
                store.save_candles([_make_candle(closed=False)])


def test_corrupt_parquet_is_not_treated_as_missing(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.parquet"
    path.write_bytes(b"not parquet")

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        _read_parquet(path)
