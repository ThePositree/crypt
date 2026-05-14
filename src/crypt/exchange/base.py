from __future__ import annotations

from typing import Protocol, runtime_checkable

from crypt.models import (
    Candle,
    FundingSnapshot,
    LongShortRatioSnapshot,
    OISnapshot,
    TakerVolumeSnapshot,
    Timeframe,
)


@runtime_checkable
class ExchangeClient(Protocol):
    """Minimal contract that any exchange adapter must satisfy."""

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 300,
    ) -> list[Candle]: ...

    async def fetch_funding_history(
        self,
        symbol: str,
        limit: int = 168,
    ) -> list[FundingSnapshot] | None: ...

    async def fetch_oi_history(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 168,
    ) -> list[OISnapshot] | None: ...

    async def fetch_ls_ratio(
        self,
        symbol: str,
        limit: int = 48,
    ) -> list[LongShortRatioSnapshot] | None: ...

    async def fetch_taker_volume(
        self,
        symbol: str,
        limit: int = 48,
    ) -> list[TakerVolumeSnapshot] | None: ...

    async def close(self) -> None: ...
