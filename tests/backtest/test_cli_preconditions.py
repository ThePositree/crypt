from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd

from crypt.backtest.__main__ import _check_preconditions, _utc_timestamp
from crypt.data.store import ParquetStore
from crypt.models import Candle, Timeframe


def _save_ohlcv(
    store: ParquetStore,
    *,
    symbol: str,
    timeframe: Timeframe,
    start: datetime,
    n_bars: int,
) -> None:
    step = timedelta(hours=4) if timeframe == Timeframe.H4 else timedelta(days=1)
    candles = [
        Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=start + i * step,
            o=Decimal("100"),
            h=Decimal("101"),
            low=Decimal("99"),
            c=Decimal("100"),
            volume=Decimal("1000"),
            closed=True,
        )
        for i in range(n_bars)
    ]
    store.save_candles(candles)


def test_utc_timestamp_accepts_aware_and_naive_datetimes() -> None:
    aware = datetime(2024, 6, 1, tzinfo=UTC)
    naive = datetime(2024, 6, 1)

    assert _utc_timestamp(aware) == pd.Timestamp("2024-06-01T00:00:00Z")
    assert _utc_timestamp(naive) == pd.Timestamp("2024-06-01T00:00:00Z")


def test_check_preconditions_accepts_timezone_aware_bounds(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    symbol = "SOL-USDT-SWAP"
    from_dt = datetime(2024, 6, 1, tzinfo=UTC)
    to_dt = datetime(2024, 6, 5, tzinfo=UTC)

    _save_ohlcv(
        store,
        symbol=symbol,
        timeframe=Timeframe.H4,
        start=from_dt - timedelta(hours=4 * 260),
        n_bars=290,
    )
    _save_ohlcv(
        store,
        symbol=symbol,
        timeframe=Timeframe.D1,
        start=from_dt - timedelta(days=70),
        n_bars=75,
    )

    assert _check_preconditions(store, [symbol], from_dt, to_dt)
