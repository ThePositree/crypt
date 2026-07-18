from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import ccxt.async_support as ccxt
from loguru import logger

from crypt.models import (
    Candle,
    CandlePriceType,
    FundingSnapshot,
    LongShortRatioSnapshot,
    OISnapshot,
    TakerVolumeSnapshot,
    Timeframe,
)
from crypt.utils.retry import retry_with_backoff

# Map our Timeframe enum values to ccxt / OKX timeframe strings.
_TF_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M15: "15m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
}

# Duration of each bar in seconds.
_TF_SECONDS: dict[Timeframe, int] = {
    Timeframe.M1: 60,
    Timeframe.M15: 15 * 60,
    Timeframe.H1: 60 * 60,
    Timeframe.H4: 4 * 60 * 60,
    Timeframe.D1: 24 * 60 * 60,
}

# A bar is only marked closed once its expected end time is this far in the past.
# Protects against OKX occasionally including the still-forming bar at the boundary.
_CLOSED_SAFETY_BUFFER: timedelta = timedelta(seconds=5)

# OKX rubik/stat period strings that match our timeframes.
_RUBIK_PERIOD_MAP: dict[str, str] = {
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
}


def _ts_ms_to_dt(ts_ms: int | float) -> datetime:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)


def _is_okx_history_limit(exc: Exception) -> bool:
    """Return True for OKX error 50030 'Illegal time range'.

    This error is permanent — the requested timestamp is older than OKX's
    history window for the endpoint. Retrying will never succeed, so callers
    should raise immediately instead of sleeping through backoff rounds.
    """
    return "50030" in str(exc)


class OKXClient:
    """
    Wraps ccxt's async OKX exchange to produce typed model objects.

    Public (unauthenticated) endpoints only for MVP market-data fetching.
    Authenticated endpoints become available when api_key/secret/passphrase
    are provided (required for M4 execution).
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        api_passphrase: str = "",
        max_retries: int = 5,
        retry_base_delay: float = 2.0,
        retry_max_delay: float = 60.0,
    ) -> None:
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay

        config: dict[str, Any] = {
            "enableRateLimit": True,
            # 30 s hard cap per request — prevents hung connections from
            # blocking the tick indefinitely (with max_instances=1 a hung
            # request would also skip the following tick).
            "timeout": 30_000,
            "options": {"defaultType": "swap"},
        }
        if api_key and api_secret and api_passphrase:
            config["apiKey"] = api_key
            config["secret"] = api_secret
            config["password"] = api_passphrase

        self._exchange: ccxt.okx = ccxt.okx(config)

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 300,
        since_ms: int | None = None,
    ) -> list[Candle]:
        return await self._fetch_price_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            since_ms=since_ms,
            price_type=CandlePriceType.LAST,
        )

    async def fetch_mark_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 100,
        since_ms: int | None = None,
    ) -> list[Candle]:
        return await self._fetch_price_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            since_ms=since_ms,
            price_type=CandlePriceType.MARK,
        )

    async def _fetch_price_candles(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        limit: int,
        since_ms: int | None,
        price_type: CandlePriceType,
    ) -> list[Candle]:
        tf_str = _TF_MAP[timeframe]

        async def _call() -> list[list[Any]]:
            if price_type is CandlePriceType.MARK:
                return await self._exchange.fetch_mark_ohlcv(  # type: ignore[no-any-return]
                    symbol, tf_str, since=since_ms, limit=limit
                )
            return await self._exchange.fetch_ohlcv(  # type: ignore[no-any-return]
                symbol, tf_str, since=since_ms, limit=limit
            )

        try:
            raw: list[list[Any]] = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_{price_type.value}_ohlcv {symbol}/{tf_str}",
            )
        except Exception as exc:
            logger.warning(
                "fetch_{}_ohlcv {}/{} failed: {}",
                price_type.value,
                symbol,
                tf_str,
                exc,
            )
            return []

        now = datetime.now(tz=UTC)
        tf_seconds = _TF_SECONDS[timeframe]
        candles: list[Candle] = []
        for row in raw:
            ts_ms, o, h, lo, c = row[:5]
            vol = row[5] if price_type is CandlePriceType.LAST and len(row) > 5 else 0
            open_time = _ts_ms_to_dt(ts_ms)
            bar_close = open_time + timedelta(seconds=tf_seconds)
            # A bar is closed only when its expected end is safely in the past.
            is_closed = bar_close + _CLOSED_SAFETY_BUFFER <= now
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    o=Decimal(str(o)),
                    h=Decimal(str(h)),
                    low=Decimal(str(lo)),
                    c=Decimal(str(c)),
                    volume=Decimal(str(vol)),
                    closed=is_closed,
                    price_type=price_type,
                )
            )
        return candles

    async def fetch_ohlcv_page(
        self,
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int = 100,
    ) -> list[Candle]:
        """Fetch one page of OHLCV starting from since_ms (inclusive). Used by backfill."""
        return await self.fetch_ohlcv(symbol, timeframe, limit=limit, since_ms=since_ms)

    async def fetch_mark_ohlcv_page(
        self,
        symbol: str,
        timeframe: Timeframe,
        since_ms: int,
        limit: int = 100,
    ) -> list[Candle]:
        """Fetch one historical mark-price OHLCV page for backfill."""
        return await self.fetch_mark_ohlcv(
            symbol,
            timeframe,
            limit=limit,
            since_ms=since_ms,
        )

    # ------------------------------------------------------------------
    # Funding rate history
    # ------------------------------------------------------------------

    async def fetch_funding_history(
        self,
        symbol: str,
        limit: int = 168,
    ) -> list[FundingSnapshot] | None:
        async def _call() -> list[Any]:
            return await self._exchange.fetch_funding_rate_history(symbol, limit=limit)  # type: ignore[no-any-return]

        try:
            raw = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_funding_history {symbol}",
            )
        except Exception as exc:
            logger.warning("fetch_funding_history {} failed: {}", symbol, exc)
            return None

        result: list[FundingSnapshot] = []
        for item in raw:
            ts = item.get("timestamp") or item.get("fundingDatetime")
            rate = item.get("fundingRate")
            if ts is None or rate is None:
                continue
            ts_dt = _ts_ms_to_dt(ts) if isinstance(ts, (int, float)) else datetime.fromisoformat(ts)
            result.append(
                FundingSnapshot(
                    symbol=symbol,
                    ts=ts_dt,
                    rate=Decimal(str(rate)),
                    next_fund_time=None,
                )
            )
        return sorted(result, key=lambda s: s.ts)

    async def fetch_funding_history_page(
        self,
        symbol: str,
        since_ms: int,
        limit: int = 100,
    ) -> list[FundingSnapshot] | None:
        """Fetch one page of funding rate history starting from since_ms. Used by backfill."""

        async def _call() -> list[Any]:
            return await self._exchange.fetch_funding_rate_history(  # type: ignore[no-any-return]
                symbol, since=since_ms, limit=limit
            )

        try:
            raw = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_funding_history_page {symbol}",
            )
        except Exception as exc:
            logger.warning("fetch_funding_history_page {} failed: {}", symbol, exc)
            return None

        result: list[FundingSnapshot] = []
        for item in raw:
            ts = item.get("timestamp") or item.get("fundingDatetime")
            rate = item.get("fundingRate")
            if ts is None or rate is None:
                continue
            ts_dt = _ts_ms_to_dt(ts) if isinstance(ts, (int, float)) else datetime.fromisoformat(ts)
            result.append(
                FundingSnapshot(
                    symbol=symbol,
                    ts=ts_dt,
                    rate=Decimal(str(rate)),
                    next_fund_time=None,
                )
            )
        return sorted(result, key=lambda s: s.ts) if result else None

    # ------------------------------------------------------------------
    # Open Interest history
    # ------------------------------------------------------------------

    async def fetch_oi_history(
        self,
        symbol: str,
        timeframe: str = "1h",  # noqa: ARG002 — interface compat, deep endpoint ignores it
        limit: int = 168,
    ) -> list[OISnapshot] | None:
        # OKX deep-history endpoint — goes back to Feb 2024; ccxt's high-level
        # fetch_open_interest_history only covers ~9 days (ADR-0016).
        # Endpoint: GET /api/v5/rubik/stat/contracts/open-interest-history
        # Requires instId (full swap id), not ccy.
        # Response row: [ts_ms, oi_contracts, oiCcy, oiUsd] — we store oiUsd (row[3]).
        now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
        since_ms = now_ms - limit * 3_600_000

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatContractsOpenInterestHistory(  # type: ignore[no-any-return]
                {
                    "instId": symbol,
                    "period": "1H",
                    "begin": str(since_ms),
                    "end": str(now_ms),
                    "limit": str(min(limit, 100)),
                }
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_oi_history {symbol}",
            )
        except Exception as exc:
            logger.warning("fetch_oi_history {} failed: {}", symbol, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[OISnapshot] = []
        for row in data:
            result.append(
                OISnapshot(
                    symbol=symbol,
                    ts=_ts_ms_to_dt(int(row[0])),
                    oi=Decimal(str(row[3])),  # oiUsd — USD-denominated OI
                )
            )
        return sorted(result, key=lambda s: s.ts)

    async def fetch_oi_history_page(
        self,
        symbol: str,
        since_ms: int,
        limit: int = 100,
        timeframe: str = "1h",  # noqa: ARG002 — interface compat, deep endpoint ignores it
    ) -> list[OISnapshot] | None:
        """Fetch one page of OI history starting from since_ms. Used by backfill."""
        # OKX deep-history endpoint — goes back to Feb 2024; ccxt's high-level
        # fetch_open_interest_history only covers ~9 days (ADR-0016).
        # Requires instId (full swap id). Response: [ts, oi_contracts, oiCcy, oiUsd].

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatContractsOpenInterestHistory(  # type: ignore[no-any-return]
                {
                    "instId": symbol,
                    "period": "1H",
                    "begin": str(since_ms),
                    "end": str(since_ms + limit * 3_600_000),
                    "limit": str(min(limit, 100)),
                }
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_oi_history_page {symbol}",
                no_retry_on=_is_okx_history_limit,
            )
        except Exception as exc:
            logger.warning("fetch_oi_history_page {} failed: {}", symbol, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[OISnapshot] = []
        for row in data:
            result.append(
                OISnapshot(symbol=symbol, ts=_ts_ms_to_dt(int(row[0])), oi=Decimal(str(row[3])))
            )
        return sorted(result, key=lambda s: s.ts) if result else None

    # ------------------------------------------------------------------
    # Long/Short ratio (OKX-specific rubik/stat endpoint)
    # ------------------------------------------------------------------

    async def fetch_ls_ratio(
        self,
        symbol: str,
        limit: int = 48,
    ) -> list[LongShortRatioSnapshot] | None:
        # /rubik/stat/contracts/long-short-account-ratio requires `ccy` (base
        # currency, e.g. "SOL"), not the full instId.
        ccy = symbol.split("-")[0]

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatContractsLongShortAccountRatio(  # type: ignore[no-any-return]
                {"ccy": ccy, "period": "1H", "limit": str(limit)}
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_ls_ratio {symbol}",
            )
        except Exception as exc:
            logger.warning("fetch_ls_ratio {} failed: {}", symbol, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[LongShortRatioSnapshot] = []
        for row in data:
            # OKX returns [ts_ms, long_short_ratio, long_ratio, short_ratio]
            # or {"ts": ..., "longShortRatio": ..., ...}
            if isinstance(row, list):
                ts_ms, ls_ratio_val = int(row[0]), float(row[1])
                long_ratio = float(row[2]) if len(row) > 2 else ls_ratio_val / (1 + ls_ratio_val)
                short_ratio = 1.0 - long_ratio
            else:
                ts_ms = int(row.get("ts", 0))
                long_ratio = float(row.get("longRatio", 0.5))
                short_ratio = float(row.get("shortRatio", 0.5))

            result.append(
                LongShortRatioSnapshot(
                    symbol=symbol,
                    ts=_ts_ms_to_dt(ts_ms),
                    long_ratio=long_ratio,
                    short_ratio=short_ratio,
                )
            )

        return sorted(result, key=lambda s: s.ts)

    async def fetch_ls_ratio_range(
        self,
        symbol: str,
        begin_ms: int,
        end_ms: int,
        limit: int = 100,
    ) -> list[LongShortRatioSnapshot] | None:
        """Fetch LS ratio for [begin_ms, end_ms] window. Used by backfill."""
        ccy = symbol.split("-")[0]

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatContractsLongShortAccountRatio(  # type: ignore[no-any-return]
                {
                    "ccy": ccy,
                    "period": "1H",
                    "limit": str(limit),
                    "begin": str(begin_ms),
                    "end": str(end_ms),
                }
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_ls_ratio_range {symbol}",
                no_retry_on=_is_okx_history_limit,
            )
        except Exception as exc:
            logger.warning("fetch_ls_ratio_range {} failed: {}", symbol, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[LongShortRatioSnapshot] = []
        for row in data:
            if isinstance(row, list):
                ts_ms, ls_ratio_val = int(row[0]), float(row[1])
                long_ratio = float(row[2]) if len(row) > 2 else ls_ratio_val / (1 + ls_ratio_val)
                short_ratio = 1.0 - long_ratio
            else:
                ts_ms = int(row.get("ts", 0))
                long_ratio = float(row.get("longRatio", 0.5))
                short_ratio = float(row.get("shortRatio", 0.5))
            result.append(
                LongShortRatioSnapshot(
                    symbol=symbol,
                    ts=_ts_ms_to_dt(ts_ms),
                    long_ratio=long_ratio,
                    short_ratio=short_ratio,
                )
            )
        return sorted(result, key=lambda s: s.ts) if result else None

    # ------------------------------------------------------------------
    # Taker buy/sell volume (OKX-specific rubik/stat endpoint)
    # ------------------------------------------------------------------

    async def fetch_taker_volume(
        self,
        symbol: str,
        limit: int = 48,
    ) -> list[TakerVolumeSnapshot] | None:
        # /rubik/stat/taker-volume requires `ccy` (base currency, e.g. "SOL"),
        # not the full instId.
        ccy = symbol.split("-")[0]

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatTakerVolume(  # type: ignore[no-any-return]
                {"ccy": ccy, "instType": "CONTRACTS", "period": "1H", "limit": str(limit)}
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_taker_volume {symbol}",
            )
        except Exception as exc:
            logger.warning("fetch_taker_volume {} ({}) failed: {}", symbol, ccy, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[TakerVolumeSnapshot] = []
        for row in data:
            if isinstance(row, list):
                ts_ms = int(row[0])
                buy_vol = Decimal(str(row[1]))
                sell_vol = Decimal(str(row[2]))
            else:
                ts_ms = int(row.get("ts", 0))
                buy_vol = Decimal(str(row.get("buyVol", "0")))
                sell_vol = Decimal(str(row.get("sellVol", "0")))

            result.append(
                TakerVolumeSnapshot(
                    symbol=symbol,
                    ts=_ts_ms_to_dt(ts_ms),
                    buy_vol=buy_vol,
                    sell_vol=sell_vol,
                )
            )

        return sorted(result, key=lambda s: s.ts)

    async def fetch_taker_volume_range(
        self,
        symbol: str,
        begin_ms: int,
        end_ms: int,
        limit: int = 100,
    ) -> list[TakerVolumeSnapshot] | None:
        """Fetch taker buy/sell volume for [begin_ms, end_ms] window. Used by backfill."""
        ccy = symbol.split("-")[0]

        async def _call() -> dict[str, Any]:
            return await self._exchange.publicGetRubikStatTakerVolume(  # type: ignore[no-any-return]
                {
                    "ccy": ccy,
                    "instType": "CONTRACTS",
                    "period": "1H",
                    "limit": str(limit),
                    "begin": str(begin_ms),
                    "end": str(end_ms),
                }
            )

        try:
            response = await retry_with_backoff(
                _call,
                max_attempts=self._max_retries,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                label=f"fetch_taker_volume_range {symbol}",
                no_retry_on=_is_okx_history_limit,
            )
        except Exception as exc:
            logger.warning("fetch_taker_volume_range {} ({}) failed: {}", symbol, ccy, exc)
            return None

        data = response.get("data", [])
        if not data:
            return None

        result: list[TakerVolumeSnapshot] = []
        for row in data:
            if isinstance(row, list):
                ts_ms = int(row[0])
                buy_vol = Decimal(str(row[1]))
                sell_vol = Decimal(str(row[2]))
            else:
                ts_ms = int(row.get("ts", 0))
                buy_vol = Decimal(str(row.get("buyVol", "0")))
                sell_vol = Decimal(str(row.get("sellVol", "0")))
            result.append(
                TakerVolumeSnapshot(
                    symbol=symbol,
                    ts=_ts_ms_to_dt(ts_ms),
                    buy_vol=buy_vol,
                    sell_vol=sell_vol,
                )
            )
        return sorted(result, key=lambda s: s.ts) if result else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._exchange.close()
