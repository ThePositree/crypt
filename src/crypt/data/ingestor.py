from __future__ import annotations

import asyncio
from typing import ClassVar

from loguru import logger

from crypt.data.store import ParquetStore
from crypt.exchange.base import ExchangeClient
from crypt.models import Timeframe


class Ingestor:
    """
    Pulls all required data types for a set of symbols from the exchange
    and persists them to the ParquetStore.

    Called once on bootstrap and then on every 4h tick.
    """

    # Candle limits per timeframe — enough warm-up for the slowest indicator
    # (EMA200 on H4 needs 200 bars; D1 needs 60).
    _OHLCV_LIMITS: ClassVar[dict[Timeframe, int]] = {
        Timeframe.H4: 250,
        Timeframe.H1: 250,
        Timeframe.D1: 100,
    }

    def __init__(
        self,
        exchange: ExchangeClient,
        store: ParquetStore,
        symbols: list[str],
    ) -> None:
        self._exchange = exchange
        self._store = store
        self._symbols = symbols

    async def ingest_all(self) -> None:
        """Pull and persist all data types for every symbol concurrently."""
        tasks = [self._ingest_symbol(sym) for sym in self._symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(self._symbols, results, strict=True):
            if isinstance(res, BaseException):
                logger.error("ingest_all: symbol {} raised: {}", sym, res)

    async def _ingest_symbol(self, symbol: str) -> None:
        logger.info("Ingesting {}", symbol)
        labels = ["ohlcv", "funding", "oi", "ls_ratio", "taker_volume"]
        results = await asyncio.gather(
            self._ingest_ohlcv(symbol),
            self._ingest_funding(symbol),
            self._ingest_oi(symbol),
            self._ingest_ls_ratio(symbol),
            self._ingest_taker_volume(symbol),
            return_exceptions=True,
        )
        for label, res in zip(labels, results, strict=True):
            if isinstance(res, BaseException):
                logger.error("_ingest_symbol {}/{}: {}", symbol, label, res)

    async def _ingest_ohlcv(self, symbol: str) -> None:
        for tf, limit in self._OHLCV_LIMITS.items():
            try:
                candles = await self._exchange.fetch_ohlcv(symbol, tf, limit=limit)
                closed = [c for c in candles if c.closed]
                if closed:
                    self._store.save_candles(closed)
            except Exception as exc:
                logger.error("OHLCV {}/{} error: {}", symbol, tf.value, exc)

    async def _ingest_funding(self, symbol: str) -> None:
        try:
            snapshots = await self._exchange.fetch_funding_history(symbol, limit=200)
            if snapshots:
                self._store.save_funding(snapshots)
        except Exception as exc:
            logger.error("Funding {} error: {}", symbol, exc)

    async def _ingest_oi(self, symbol: str) -> None:
        try:
            snapshots = await self._exchange.fetch_oi_history(symbol, timeframe="1h", limit=200)
            if snapshots:
                self._store.save_oi(snapshots)
        except Exception as exc:
            logger.error("OI {} error: {}", symbol, exc)

    async def _ingest_ls_ratio(self, symbol: str) -> None:
        try:
            snapshots = await self._exchange.fetch_ls_ratio(symbol, limit=100)
            if snapshots:
                self._store.save_ls_ratio(snapshots)
        except Exception as exc:
            logger.error("LS ratio {} error: {}", symbol, exc)

    async def _ingest_taker_volume(self, symbol: str) -> None:
        try:
            snapshots = await self._exchange.fetch_taker_volume(symbol, limit=100)
            if snapshots:
                self._store.save_taker_volume(snapshots)
        except Exception as exc:
            logger.error("Taker volume {} error: {}", symbol, exc)
