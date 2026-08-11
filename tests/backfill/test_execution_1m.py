from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from crypt.backfill.__main__ import _backfill_execution_1m, _backfill_ohlcv
from crypt.models import Candle, CandlePriceType, Timeframe


class _Store:
    def __init__(self) -> None:
        self.saved: list[Candle] = []
        self.complete_checks: list[tuple[str, CandlePriceType, datetime, datetime]] = []
        self.policy_calls: list[tuple[Timeframe, bool, bool]] = []

    def has_complete_minute_range(
        self,
        symbol: str,
        *,
        price_type: CandlePriceType,
        start: datetime,
        end: datetime,
    ) -> bool:
        self.complete_checks.append((symbol, price_type, start, end))
        return False

    def save_candles(self, candles: list[Candle]) -> None:
        self.saved.extend(candles)

    def save_candles_with_policy(
        self,
        candles: list[Candle],
        *,
        allow_ohlc_rewrite: bool,
        validate_h1_from_1m: bool = True,
    ) -> None:
        assert allow_ohlc_rewrite is True
        assert validate_h1_from_1m in {False, True}
        if candles:
            self.policy_calls.append(
                (candles[0].timeframe, allow_ohlc_rewrite, validate_h1_from_1m)
            )
        self.save_candles(candles)


class _Client:
    async def fetch_ohlcv_page(
        self,
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int,
    ) -> list[Candle]:
        return self._page(symbol, timeframe, since_ms, limit, CandlePriceType.LAST)

    async def fetch_mark_ohlcv_page(
        self,
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int,
    ) -> list[Candle]:
        return self._page(symbol, timeframe, since_ms, limit, CandlePriceType.MARK)

    @staticmethod
    def _page(
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int,
        price_type: CandlePriceType,
    ) -> list[Candle]:
        start = datetime.fromtimestamp(since_ms / 1000, tz=UTC)
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=start + timedelta(minutes=offset),
                o=Decimal("100"),
                h=Decimal("101"),
                low=Decimal("99"),
                c=Decimal("100"),
                volume=Decimal("1") if price_type is CandlePriceType.LAST else Decimal("0"),
                price_type=price_type,
            )
            for offset in range(limit)
        ]


class _OnePageOhlcvClient:
    def __init__(self) -> None:
        self.seen: set[Timeframe] = set()

    async def fetch_ohlcv_page(
        self,
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int,
    ) -> list[Candle]:
        _ = limit
        if timeframe in self.seen:
            return []
        self.seen.add(timeframe)
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=datetime.fromtimestamp(since_ms / 1000, tz=UTC),
                o=Decimal("100"),
                h=Decimal("101"),
                low=Decimal("99"),
                c=Decimal("100"),
                volume=Decimal("1"),
            )
        ]


@pytest.mark.asyncio
async def test_execution_minute_backfill_writes_last_and_mark_series() -> None:
    store = _Store()

    await _backfill_execution_1m(
        _Client(),  # type: ignore[arg-type]
        store,  # type: ignore[arg-type]
        "SOL-USDT-SWAP",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 1, 0, 3, tzinfo=UTC),
        page_size=2,
        delay_s=0,
    )

    assert len(store.saved) == 6
    assert [c.price_type for c in store.saved].count(CandlePriceType.LAST) == 3
    assert [c.price_type for c in store.saved].count(CandlePriceType.MARK) == 3


@pytest.mark.asyncio
async def test_ohlcv_backfill_includes_dss_m15_timeframe() -> None:
    store = _Store()

    await _backfill_ohlcv(
        _OnePageOhlcvClient(),  # type: ignore[arg-type]
        store,  # type: ignore[arg-type]
        "SOL-USDT-SWAP",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
        page_size=100,
        delay_s=0,
    )

    assert {c.timeframe for c in store.saved} == {
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.H4,
        Timeframe.D1,
    }
    assert all(validate is False for _tf, _rewrite, validate in store.policy_calls)
