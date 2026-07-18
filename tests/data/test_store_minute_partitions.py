from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from crypt.data.store import ParquetStore
from crypt.models import Candle, CandlePriceType, Timeframe


def _candle(ts: datetime, price_type: CandlePriceType) -> Candle:
    return Candle(
        symbol="SOL-USDT-SWAP",
        timeframe=Timeframe.M1,
        open_time=ts,
        o=Decimal("100"),
        h=Decimal("101"),
        low=Decimal("99"),
        c=Decimal("100"),
        volume=Decimal("1") if price_type is CandlePriceType.LAST else Decimal("0"),
        price_type=price_type,
    )


def _h1_candle(
    ts: datetime,
    *,
    o: str = "100",
    h: str = "101",
    low: str = "99",
    c: str = "100",
) -> Candle:
    return Candle(
        symbol="SOL-USDT-SWAP",
        timeframe=Timeframe.H1,
        open_time=ts,
        o=Decimal(o),
        h=Decimal(h),
        low=Decimal(low),
        c=Decimal(c),
        volume=Decimal("60"),
    )


def test_minute_candles_are_partitioned_by_month_and_price_type(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    last = [
        _candle(datetime(2026, 1, 31, 23, 59, tzinfo=UTC), CandlePriceType.LAST),
        _candle(datetime(2026, 2, 1, 0, 0, tzinfo=UTC), CandlePriceType.LAST),
    ]
    mark = [
        _candle(datetime(2026, 1, 31, 23, 59, tzinfo=UTC), CandlePriceType.MARK),
        _candle(datetime(2026, 2, 1, 0, 0, tzinfo=UTC), CandlePriceType.MARK),
    ]

    store.save_candles(last)
    store.save_candles(mark)

    assert (tmp_path / "SOL-USDT-SWAP/ohlcv_1m/2026-01.parquet").exists()
    assert (tmp_path / "SOL-USDT-SWAP/ohlcv_1m/2026-02.parquet").exists()
    assert (tmp_path / "SOL-USDT-SWAP/mark_ohlcv_1m/2026-01.parquet").exists()
    assert len(store.load_candles("SOL-USDT-SWAP", Timeframe.M1)) == 2
    assert (
        len(
            store.load_candles(
                "SOL-USDT-SWAP",
                Timeframe.M1,
                price_type=CandlePriceType.MARK,
            )
        )
        == 2
    )
    assert store.has_complete_minute_range(
        "SOL-USDT-SWAP",
        price_type=CandlePriceType.LAST,
        start=datetime(2026, 1, 31, 23, 59, tzinfo=UTC),
        end=datetime(2026, 2, 1, 0, 1, tzinfo=UTC),
    )


def test_h1_save_rejects_mismatch_when_complete_last_minutes_exist(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    minutes = [
        _candle(start + timedelta(minutes=offset), CandlePriceType.LAST) for offset in range(60)
    ]
    store.save_candles(minutes)

    with pytest.raises(ValueError, match="H1 candle does not aggregate"):
        store.save_candles([_h1_candle(start, low="98")])


def test_h1_save_accepts_match_when_complete_last_minutes_exist(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    minutes = [
        _candle(start + timedelta(minutes=offset), CandlePriceType.LAST) for offset in range(60)
    ]
    store.save_candles(minutes)
    store.save_candles([_h1_candle(start)])

    frame = store.load_candles("SOL-USDT-SWAP", Timeframe.H1)
    assert len(frame) == 1
    assert not store.has_complete_minute_range(
        "SOL-USDT-SWAP",
        price_type=CandlePriceType.MARK,
        start=datetime(2026, 1, 31, 23, 58, tzinfo=UTC),
        end=datetime(2026, 2, 1, 0, 1, tzinfo=UTC),
    )
