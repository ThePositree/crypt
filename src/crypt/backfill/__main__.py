"""
Backfill CLI — fetches historical OKX data into the Parquet store.

Usage:
    uv run python -m crypt.backfill \\
        --symbol SOL-USDT-SWAP \\
        --from 2024-02-01 \\
        --to   2026-06-01 \\
        [--data-types ohlcv,oi,ls_ratio] \\
        [--page-size 100] \\
        [--max-rps 5]

Resume safety: re-running is idempotent; ParquetStore._upsert deduplicates.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from crypt.config import Settings
from crypt.data.store import ParquetStore
from crypt.exchange.okx import OKXClient
from crypt.models import Candle, CandlePriceType, Timeframe
from crypt.runtime.logging import configure_runtime_logging

# Milliseconds per bar for each timeframe.
_MS_PER_BAR: dict[Timeframe, int] = {
    Timeframe.M1: 60 * 1000,
    Timeframe.M15: 15 * 60 * 1000,
    Timeframe.H1: 60 * 60 * 1000,
    Timeframe.H4: 4 * 60 * 60 * 1000,
    Timeframe.D1: 24 * 60 * 60 * 1000,
}

# Milliseconds per hour (used for LS ratio / taker volume window sizing).
_MS_PER_HOUR = 60 * 60 * 1000

# Warm-up extra bars to prepend before `from_dt` so indicators (EMA200)
# have enough history.  250 H4 bars = 1000 hours ≈ 41 days.
_OHLCV_WARMUP_H4_BARS = 250

# After this many consecutive windows return no data we assume we have hit
# OKX's history wall (error 50030) and skip ahead by _HISTORY_SKIP_MS.
_MAX_CONSECUTIVE_EMPTY = 3

# How far to jump forward when a history wall is detected.  90 days is
# generous enough to land past any known OKX Rubik / OI lookback limit.
_HISTORY_SKIP_MS = 90 * 24 * 60 * 60 * 1000


def _dt_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


async def _backfill_ohlcv(
    client: OKXClient,
    store: ParquetStore,
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    page_size: int,
    delay_s: float,
) -> None:
    """Paginate forward through OHLCV for all required timeframes."""
    timeframes = [Timeframe.H4, Timeframe.H1, Timeframe.D1]

    for tf in timeframes:
        ms_per_bar = _MS_PER_BAR[tf]

        # H4 needs warm-up bars; others get 14-day warm-up.
        if tf == Timeframe.H4:
            warmup_ms = _OHLCV_WARMUP_H4_BARS * ms_per_bar
        else:
            warmup_ms = 14 * 24 * _MS_PER_HOUR

        start_ms = _dt_to_ms(from_dt) - warmup_ms
        end_ms = _dt_to_ms(to_dt)
        total_bars = max(1, (end_ms - start_ms) // ms_per_bar)
        desc = f"{symbol} OHLCV/{tf.value}"

        with tqdm(total=total_bars, desc=desc, unit="bar", leave=False, file=sys.stdout) as pbar:
            cursor = start_ms
            while cursor < end_ms:
                candles = await client.fetch_ohlcv_page(symbol, tf, cursor, limit=page_size)
                if not candles:
                    logger.debug("{} {}: no data at since={}", symbol, tf.value, cursor)
                    break

                closed = [c for c in candles if c.closed]
                if closed:
                    store.save_candles_with_policy(closed, allow_ohlc_rewrite=True)

                last_ts_ms = _dt_to_ms(candles[-1].open_time)
                logger.debug(
                    "{} {}: fetched {} bars, last={}", symbol, tf.value, len(candles), last_ts_ms
                )

                # Advance cursor past the last returned bar.
                new_cursor = last_ts_ms + ms_per_bar
                pbar.update(max(0, (new_cursor - cursor) // ms_per_bar))

                if last_ts_ms >= end_ms or new_cursor <= cursor:
                    break
                cursor = new_cursor

                if delay_s > 0:
                    await asyncio.sleep(delay_s)


async def _backfill_execution_1m_series(
    client: OKXClient,
    store: ParquetStore,
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    page_size: int,
    delay_s: float,
    *,
    mark_price: bool,
) -> None:
    """Backfill one complete minute execution series with monthly checkpoints."""
    timeframe = Timeframe.M1
    ms_per_bar = _MS_PER_BAR[timeframe]
    start_ms = _dt_to_ms(from_dt)
    end_ms = _dt_to_ms(to_dt)
    total_bars = max(1, (end_ms - start_ms) // ms_per_bar)
    price_name = "mark" if mark_price else "last"
    desc = f"{symbol} execution/{price_name}/1m"
    price_type = CandlePriceType.MARK if mark_price else CandlePriceType.LAST

    with tqdm(total=total_bars, desc=desc, unit="bar", leave=False, file=sys.stdout) as pbar:
        cursor = start_ms
        while cursor < end_ms:
            cursor_dt = datetime.fromtimestamp(cursor / 1000, tz=UTC)
            if cursor_dt.month == 12:
                next_month = cursor_dt.replace(
                    year=cursor_dt.year + 1,
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            else:
                next_month = cursor_dt.replace(
                    month=cursor_dt.month + 1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            segment_end_ms = min(_dt_to_ms(next_month), end_ms)
            segment_end = datetime.fromtimestamp(segment_end_ms / 1000, tz=UTC)
            if store.has_complete_minute_range(
                symbol,
                price_type=price_type,
                start=cursor_dt,
                end=segment_end,
            ):
                pbar.update((segment_end_ms - cursor) // ms_per_bar)
                cursor = segment_end_ms
                continue

            buffered: list[Candle] = []
            while cursor < segment_end_ms:
                if mark_price:
                    candles = await client.fetch_mark_ohlcv_page(
                        symbol,
                        timeframe,
                        cursor,
                        limit=page_size,
                    )
                else:
                    candles = await client.fetch_ohlcv_page(
                        symbol,
                        timeframe,
                        cursor,
                        limit=page_size,
                    )
                if not candles:
                    raise RuntimeError(
                        f"OKX returned no {price_name} 1m data before requested end: "
                        f"symbol={symbol} "
                        f"cursor={datetime.fromtimestamp(cursor / 1000, tz=UTC)} "
                        f"end={to_dt}"
                    )

                buffered.extend(
                    candle
                    for candle in candles
                    if candle.closed and start_ms <= _dt_to_ms(candle.open_time) < segment_end_ms
                )
                last_ts_ms = _dt_to_ms(candles[-1].open_time)
                new_cursor = last_ts_ms + ms_per_bar
                pbar.update(max(0, min(new_cursor, segment_end_ms) - cursor) // ms_per_bar)
                if new_cursor <= cursor:
                    raise RuntimeError(
                        f"OKX {price_name} 1m pagination did not advance for {symbol}: "
                        f"cursor={cursor} last={last_ts_ms}"
                    )
                cursor = min(new_cursor, segment_end_ms)
                if delay_s > 0:
                    await asyncio.sleep(delay_s)
            store.save_candles_with_policy(buffered, allow_ohlc_rewrite=True)


async def _backfill_execution_1m(
    client: OKXClient,
    store: ParquetStore,
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    page_size: int,
    delay_s: float,
) -> None:
    """Backfill last-trade and mark-price minute series used by execution replay."""
    await _backfill_execution_1m_series(
        client,
        store,
        symbol,
        from_dt,
        to_dt,
        page_size,
        delay_s,
        mark_price=False,
    )
    await _backfill_execution_1m_series(
        client,
        store,
        symbol,
        from_dt,
        to_dt,
        page_size,
        delay_s,
        mark_price=True,
    )


async def _backfill_oi(
    client: OKXClient,
    store: ParquetStore,
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    page_size: int,
    delay_s: float,
) -> None:
    """Paginate forward through open interest history (1h bars)."""
    warmup_ms = 7 * 24 * _MS_PER_HOUR
    start_ms = _dt_to_ms(from_dt) - warmup_ms
    end_ms = _dt_to_ms(to_dt)
    total_est = max(1, (end_ms - start_ms) // _MS_PER_HOUR)

    with tqdm(
        total=total_est, desc=f"{symbol} OI", unit="bar", leave=False, file=sys.stdout
    ) as pbar:
        cursor = start_ms
        consecutive_empty = 0
        while cursor < end_ms:
            snaps = await client.fetch_oi_history_page(symbol, cursor, limit=page_size)
            if not snaps:
                consecutive_empty += 1
                if consecutive_empty >= _MAX_CONSECUTIVE_EMPTY:
                    skip_to = min(cursor + _HISTORY_SKIP_MS, end_ms)
                    logger.warning(
                        "{} OI: {} consecutive empty pages — OKX history wall detected,"
                        " skipping {} ms ahead",
                        symbol,
                        consecutive_empty,
                        skip_to - cursor,
                    )
                    pbar.update(max(0, (skip_to - cursor) // _MS_PER_HOUR))
                    cursor = skip_to
                    consecutive_empty = 0
                else:
                    logger.debug("{} OI: no data at since={}", symbol, cursor)
                    # Advance by one page-worth of hours so we don't spin in place.
                    new_cursor = cursor + page_size * _MS_PER_HOUR
                    pbar.update(max(0, (new_cursor - cursor) // _MS_PER_HOUR))
                    cursor = new_cursor
                continue

            consecutive_empty = 0
            store.save_oi(snaps)
            last_ts_ms = _dt_to_ms(snaps[-1].ts)
            logger.debug("{} OI: fetched {}, last={}", symbol, len(snaps), last_ts_ms)

            new_cursor = last_ts_ms + _MS_PER_HOUR
            pbar.update(max(0, (new_cursor - cursor) // _MS_PER_HOUR))

            if last_ts_ms >= end_ms or new_cursor <= cursor:
                break
            cursor = new_cursor

            if delay_s > 0:
                await asyncio.sleep(delay_s)


async def _backfill_rubik(
    client: OKXClient,
    store: ParquetStore,
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    page_size: int,
    delay_s: float,
    data_type: str,
) -> None:
    """Paginate through LS ratio or taker volume using begin/end windows."""
    warmup_ms = 7 * 24 * _MS_PER_HOUR
    start_ms = _dt_to_ms(from_dt) - warmup_ms
    end_ms = _dt_to_ms(to_dt)
    window_ms = page_size * _MS_PER_HOUR
    total_est = max(1, (end_ms - start_ms) // _MS_PER_HOUR)

    with tqdm(
        total=total_est,
        desc=f"{symbol} {data_type}",
        unit="bar",
        leave=False,
        file=sys.stdout,
    ) as pbar:
        cursor = start_ms
        consecutive_empty = 0
        while cursor < end_ms:
            window_end = min(cursor + window_ms, end_ms)

            fetched = 0
            if data_type == "ls_ratio":
                ls_result = await client.fetch_ls_ratio_range(
                    symbol, cursor, window_end, limit=page_size
                )
                if ls_result:
                    store.save_ls_ratio(ls_result)
                    fetched = len(ls_result)
            else:
                tv_result = await client.fetch_taker_volume_range(
                    symbol, cursor, window_end, limit=page_size
                )
                if tv_result:
                    store.save_taker_volume(tv_result)
                    fetched = len(tv_result)
            logger.debug(
                "{} {}: fetched {} records [{}, {}]", symbol, data_type, fetched, cursor, window_end
            )

            if fetched == 0:
                consecutive_empty += 1
                if consecutive_empty >= _MAX_CONSECUTIVE_EMPTY:
                    skip_to = min(cursor + _HISTORY_SKIP_MS, end_ms)
                    logger.warning(
                        "{} {}: {} consecutive empty windows — OKX history wall detected,"
                        " skipping {} ms ahead",
                        symbol,
                        data_type,
                        consecutive_empty,
                        skip_to - cursor,
                    )
                    pbar.update(max(0, (skip_to - cursor) // _MS_PER_HOUR))
                    cursor = skip_to
                    consecutive_empty = 0
                    continue
            else:
                consecutive_empty = 0

            advance = window_end - cursor
            pbar.update(max(0, advance // _MS_PER_HOUR))
            cursor = window_end

            if delay_s > 0:
                await asyncio.sleep(delay_s)


async def _run_backfill(
    symbol: str,
    from_dt: datetime,
    to_dt: datetime,
    data_types: list[str],
    page_size: int,
    max_rps: float,
    data_dir: Path,
) -> None:
    delay_s = 1.0 / max_rps if max_rps > 0 else 0.0
    client = OKXClient()
    store = ParquetStore(data_dir)

    logger.info(
        "Backfill {} | {} → {} | types={}", symbol, from_dt.date(), to_dt.date(), data_types
    )

    try:
        if "ohlcv" in data_types:
            await _backfill_ohlcv(client, store, symbol, from_dt, to_dt, page_size, delay_s)

        if "execution_1m" in data_types:
            await _backfill_execution_1m(
                client,
                store,
                symbol,
                from_dt,
                to_dt,
                page_size,
                delay_s,
            )
        else:
            if "last_1m" in data_types:
                await _backfill_execution_1m_series(
                    client,
                    store,
                    symbol,
                    from_dt,
                    to_dt,
                    page_size,
                    delay_s,
                    mark_price=False,
                )
            if "mark_1m" in data_types:
                await _backfill_execution_1m_series(
                    client,
                    store,
                    symbol,
                    from_dt,
                    to_dt,
                    page_size,
                    delay_s,
                    mark_price=True,
                )

        if "oi" in data_types:
            await _backfill_oi(client, store, symbol, from_dt, to_dt, page_size, delay_s)

        if "ls_ratio" in data_types:
            await _backfill_rubik(
                client, store, symbol, from_dt, to_dt, page_size, delay_s, "ls_ratio"
            )

        if "taker_vol" in data_types:
            await _backfill_rubik(
                client, store, symbol, from_dt, to_dt, page_size, delay_s, "taker_vol"
            )

        logger.info("Backfill complete: {}", symbol)
    finally:
        await client.close()


def main() -> None:
    settings = Settings()
    configure_runtime_logging(settings.log_level, settings.log_dir)

    parser = argparse.ArgumentParser(
        prog="python -m crypt.backfill",
        description="Backfill historical OKX data into the Parquet store.",
    )
    parser.add_argument("--symbol", required=True, help="OKX instId, e.g. SOL-USDT-SWAP")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument(
        "--to", dest="to_date", required=True, help="End date YYYY-MM-DD (exclusive)"
    )
    parser.add_argument(
        "--data-types",
        default="ohlcv,oi,ls_ratio",
        help=("Comma-separated list: ohlcv,execution_1m,last_1m,mark_1m,oi,ls_ratio,taker_vol"),
    )
    parser.add_argument("--page-size", type=int, default=100, help="Records per API call (max 100)")
    parser.add_argument("--max-rps", type=float, default=5.0, help="Max API requests per second")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Override DATA_DIR (default: read from .env / env var)",
    )

    args = parser.parse_args()

    from_dt = _parse_date(args.from_date)
    to_dt = _parse_date(args.to_date)
    if to_dt <= from_dt:
        logger.error("--to must be after --from")
        sys.exit(1)

    data_types = [t.strip() for t in args.data_types.split(",") if t.strip()]
    valid_types = {
        "ohlcv",
        "execution_1m",
        "last_1m",
        "mark_1m",
        "oi",
        "ls_ratio",
        "taker_vol",
    }
    unknown = set(data_types) - valid_types
    if unknown:
        logger.error("Unknown data types: {}. Valid: {}", unknown, valid_types)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else settings.data_dir

    asyncio.run(
        _run_backfill(
            symbol=args.symbol,
            from_dt=from_dt,
            to_dt=to_dt,
            data_types=data_types,
            page_size=min(args.page_size, 100),
            max_rps=args.max_rps,
            data_dir=data_dir,
        )
    )


if __name__ == "__main__":
    main()
