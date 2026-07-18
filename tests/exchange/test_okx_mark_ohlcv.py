from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from crypt.exchange.okx import OKXClient
from crypt.models import CandlePriceType, Timeframe


@pytest.mark.asyncio
async def test_fetch_mark_ohlcv_uses_mark_endpoint() -> None:
    client = OKXClient(max_retries=1)
    client._exchange.fetch_mark_ohlcv = AsyncMock(  # type: ignore[method-assign]
        return_value=[[1_767_225_600_000, 100, 101, 99, 100]]
    )

    candles = await client.fetch_mark_ohlcv(
        "SOL-USDT-SWAP",
        Timeframe.M1,
        since_ms=1_767_225_600_000,
        limit=100,
    )

    assert len(candles) == 1
    assert candles[0].price_type is CandlePriceType.MARK
    assert candles[0].volume == 0
    client._exchange.fetch_mark_ohlcv.assert_awaited_once_with(
        "SOL-USDT-SWAP",
        "1m",
        since=1_767_225_600_000,
        limit=100,
    )
    await client.close()
