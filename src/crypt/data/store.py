from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

from crypt.models import (
    Candle,
    CandlePriceType,
    LongShortRatioSnapshot,
    OISnapshot,
    TakerVolumeSnapshot,
    Timeframe,
)

# Column schemas for each data type.
_OHLCV_COLS = ["open_time", "o", "h", "l", "c", "volume"]
_OHLC_PRICE_COLS = ("o", "h", "l", "c")
_OI_COLS = ["ts", "oi"]
_LS_RATIO_COLS = ["ts", "long_ratio", "short_ratio"]
_TAKER_VOL_COLS = ["ts", "buy_vol", "sell_vol"]
_PRICE_COMPARE_REL_TOL = 1e-10
_PRICE_COMPARE_ABS_TOL = 1e-10


def _symbol_dir(base: Path, symbol: str) -> Path:
    # e.g.  data/SOL-USDT-SWAP/
    return base / symbol


def _ohlcv_path(
    base: Path,
    symbol: str,
    timeframe: Timeframe,
    price_type: CandlePriceType = CandlePriceType.LAST,
) -> Path:
    prefix = "ohlcv" if price_type is CandlePriceType.LAST else "mark_ohlcv"
    suffix = timeframe.value if timeframe is not Timeframe.M1 else "1m"
    return _symbol_dir(base, symbol) / f"{prefix}_{suffix}.parquet"


def _minute_ohlcv_dir(
    base: Path,
    symbol: str,
    price_type: CandlePriceType,
) -> Path:
    prefix = "ohlcv" if price_type is CandlePriceType.LAST else "mark_ohlcv"
    return _symbol_dir(base, symbol) / f"{prefix}_1m"


def _oi_path(base: Path, symbol: str) -> Path:
    return _symbol_dir(base, symbol) / "oi_1h.parquet"


def _ls_ratio_path(base: Path, symbol: str) -> Path:
    return _symbol_dir(base, symbol) / "ls_ratio_1h.parquet"


def _taker_vol_path(base: Path, symbol: str) -> Path:
    return _symbol_dir(base, symbol) / "taker_vol_1h.parquet"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_parquet(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        logger.error("Failed to read {}: {}", path, exc)
        raise RuntimeError(f"refusing to overwrite unreadable parquet file: {path}") from exc


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        pq.write_table(table, tmp, compression="snappy")  # type: ignore[no-untyped-call]
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _upsert(existing: pd.DataFrame | None, new: pd.DataFrame, ts_col: str) -> pd.DataFrame:
    """Merge new rows into existing, dedup by ts_col, sort ascending."""
    if existing is None or existing.empty:
        return new.sort_values(ts_col).reset_index(drop=True)
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=[ts_col], keep="last")
    return combined.sort_values(ts_col).reset_index(drop=True)


def _assert_no_conflicting_ohlc_update(
    *,
    existing: pd.DataFrame | None,
    new: pd.DataFrame,
    path: Path,
) -> None:
    """Reject silent rewrites of closed candle OHLC values for the same open time."""
    if existing is None or existing.empty or new.empty:
        return
    existing_times = set(pd.to_datetime(existing["open_time"], utc=True))
    duplicates = new[pd.to_datetime(new["open_time"], utc=True).isin(existing_times)]
    if duplicates.empty:
        return

    existing_by_time = existing.copy()
    existing_by_time["open_time"] = pd.to_datetime(existing_by_time["open_time"], utc=True)
    existing_by_time = existing_by_time.set_index("open_time")
    for _, new_row in duplicates.iterrows():
        open_time = pd.Timestamp(new_row["open_time"])
        old_row = existing_by_time.loc[open_time]
        if isinstance(old_row, pd.DataFrame):
            old_row = old_row.iloc[-1]
        for column in _OHLC_PRICE_COLS:
            old_value = float(old_row[column])
            new_value = float(new_row[column])
            tolerance = abs(old_value) * _PRICE_COMPARE_REL_TOL + _PRICE_COMPARE_ABS_TOL
            if abs(old_value - new_value) > tolerance:
                raise ValueError(
                    "conflicting closed candle update refused: "
                    f"path={path} open_time={open_time.isoformat()} "
                    f"column={column} existing={old_value} new={new_value}"
                )


def _assert_h1_matches_complete_minutes(
    *,
    base: Path,
    symbol: str,
    price_type: CandlePriceType,
    new: pd.DataFrame,
) -> None:
    """When complete 1m data exists, require stored H1 OHLC to aggregate from it."""
    for _, row in new.iterrows():
        open_time = pd.Timestamp(row["open_time"]).tz_convert(UTC)
        end = open_time + pd.Timedelta(hours=1)
        minute_frame = _load_minute_window(
            base=base,
            symbol=symbol,
            price_type=price_type,
            start=open_time,
            end=end,
        )
        if minute_frame is None:
            continue
        aggregated = {
            "o": float(minute_frame.iloc[0]["o"]),
            "h": float(minute_frame["h"].max()),
            "l": float(minute_frame["l"].min()),
            "c": float(minute_frame.iloc[-1]["c"]),
        }
        for column, expected in aggregated.items():
            actual = float(row[column])
            tolerance = abs(expected) * _PRICE_COMPARE_REL_TOL + _PRICE_COMPARE_ABS_TOL
            if abs(actual - expected) > tolerance:
                raise ValueError(
                    "H1 candle does not aggregate from complete 1m data: "
                    f"symbol={symbol} price_type={price_type.value} "
                    f"open_time={open_time.isoformat()} column={column} "
                    f"h1={actual} m1={expected}"
                )


def _load_minute_window(
    *,
    base: Path,
    symbol: str,
    price_type: CandlePriceType,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame | None:
    expected = pd.date_range(start=start, end=end, freq="1min", inclusive="left")
    if expected.empty:
        return pd.DataFrame(columns=_OHLCV_COLS)
    partition_dir = _minute_ohlcv_dir(base, symbol, price_type)
    frames: list[pd.DataFrame] = []
    for month in expected.strftime("%Y-%m").unique():
        frame = _read_parquet(partition_dir / f"{month}.parquet")
        if frame is None:
            return None
        frames.append(frame)
    actual = pd.concat(frames, ignore_index=True)
    actual["open_time"] = pd.to_datetime(actual["open_time"], utc=True)
    actual = actual[(actual["open_time"] >= start) & (actual["open_time"] < end)].copy()
    if actual.empty:
        return None
    actual = actual.drop_duplicates(subset=["open_time"], keep="last").sort_values("open_time")
    if not pd.DatetimeIndex(actual["open_time"]).equals(expected):
        return None
    return actual.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ParquetStore:
    """
    Thin Parquet-backed store for each symbol's time-series data.

    All timestamps are stored as UTC datetime64[us, UTC].
    Prices/volumes are stored as float64 for space efficiency (Decimal → float
    at write time; engines only need float arithmetic).
    """

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir

    # --- OHLCV ---

    def save_candles(self, candles: list[Candle]) -> None:
        if not candles:
            return
        open_candles = [c for c in candles if not c.closed]
        if open_candles:
            raise ValueError(
                f"save_candles received {len(open_candles)} non-closed candle(s); "
                "only closed bars may be persisted to prevent look-ahead bias. "
                f"First offender: {open_candles[0].symbol} {open_candles[0].timeframe} "
                f"{open_candles[0].open_time.isoformat()}"
            )
        symbol = candles[0].symbol
        tf = candles[0].timeframe
        price_type = candles[0].price_type
        if any(c.symbol != symbol for c in candles):
            raise ValueError("save_candles requires one symbol per batch")
        if any(c.timeframe is not tf for c in candles):
            raise ValueError("save_candles requires one timeframe per batch")
        if any(c.price_type is not price_type for c in candles):
            raise ValueError("save_candles requires one price type per batch")
        new_df = pd.DataFrame(
            [
                {
                    "open_time": c.open_time,
                    "o": float(c.o),
                    "h": float(c.h),
                    "l": float(c.low),
                    "c": float(c.c),
                    "volume": float(c.volume),
                    "closed": c.closed,
                }
                for c in candles
            ]
        )
        new_df["open_time"] = pd.to_datetime(new_df["open_time"], utc=True)
        if tf is Timeframe.M1:
            partition_dir = _minute_ohlcv_dir(self._base, symbol, price_type)
            month_keys = new_df["open_time"].dt.strftime("%Y-%m")
            for month, month_df in new_df.groupby(month_keys, sort=True):
                path = partition_dir / f"{month}.parquet"
                existing = _read_parquet(path)
                _assert_no_conflicting_ohlc_update(
                    existing=existing,
                    new=month_df,
                    path=path,
                )
                merged = _upsert(existing, month_df, "open_time")
                _write_parquet(merged, path)
        else:
            path = _ohlcv_path(self._base, symbol, tf, price_type)
            existing = _read_parquet(path)
            _assert_no_conflicting_ohlc_update(
                existing=existing,
                new=new_df,
                path=path,
            )
            if tf is Timeframe.H1:
                _assert_h1_matches_complete_minutes(
                    base=self._base,
                    symbol=symbol,
                    price_type=price_type,
                    new=new_df,
                )
            merged = _upsert(existing, new_df, "open_time")
            _write_parquet(merged, path)
        logger.debug(
            "Saved {} {} {} candles for {}",
            len(candles),
            price_type.value,
            tf.value,
            symbol,
        )

    def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int | None = None,
        price_type: CandlePriceType = CandlePriceType.LAST,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame of closed candles: columns open_time, o, h, l, c, volume.
        Sorted ascending by open_time. Returns empty DataFrame if nothing stored.
        """
        if timeframe is Timeframe.M1:
            partition_dir = _minute_ohlcv_dir(self._base, symbol, price_type)
            frames = [
                frame
                for path in sorted(partition_dir.glob("*.parquet"))
                if (frame := _read_parquet(path)) is not None
            ]
            df = pd.concat(frames, ignore_index=True) if frames else None
        else:
            path = _ohlcv_path(self._base, symbol, timeframe, price_type)
            df = _read_parquet(path)
        if df is None or df.empty:
            return pd.DataFrame(columns=_OHLCV_COLS)
        # Keep only closed candles.
        if "closed" in df.columns:
            df = df[df["closed"]].copy()
        df = df[_OHLCV_COLS].sort_values("open_time").reset_index(drop=True)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    def has_complete_minute_range(
        self,
        symbol: str,
        *,
        price_type: CandlePriceType,
        start: datetime,
        end: datetime,
    ) -> bool:
        """Return whether every UTC minute in ``[start, end)`` is persisted."""
        if end <= start:
            return True
        partition_dir = _minute_ohlcv_dir(self._base, symbol, price_type)
        expected = pd.date_range(start=start, end=end, freq="1min", inclusive="left")
        frames: list[pd.DataFrame] = []
        for month in expected.strftime("%Y-%m").unique():
            frame = _read_parquet(partition_dir / f"{month}.parquet")
            if frame is None:
                return False
            frames.append(frame)
        actual = pd.concat(frames, ignore_index=True)
        timestamps = pd.DatetimeIndex(pd.to_datetime(actual["open_time"], utc=True))
        timestamps = timestamps[(timestamps >= expected[0]) & (timestamps <= expected[-1])]
        return not timestamps.has_duplicates and timestamps.sort_values().equals(expected)

    # --- Open Interest ---

    def save_oi(self, snapshots: list[OISnapshot]) -> None:
        if not snapshots:
            return
        symbol = snapshots[0].symbol
        path = _oi_path(self._base, symbol)
        new_df = pd.DataFrame([{"ts": s.ts, "oi": float(s.oi)} for s in snapshots])
        new_df["ts"] = pd.to_datetime(new_df["ts"], utc=True)
        existing = _read_parquet(path)
        merged = _upsert(existing, new_df, "ts")
        _write_parquet(merged, path)

    def load_oi(self, symbol: str, limit: int | None = None) -> pd.DataFrame:
        path = _oi_path(self._base, symbol)
        df = _read_parquet(path)
        if df is None or df.empty:
            return pd.DataFrame(columns=_OI_COLS)
        df = df[_OI_COLS].sort_values("ts").reset_index(drop=True)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    # --- Long/Short ratio ---

    def save_ls_ratio(self, snapshots: list[LongShortRatioSnapshot]) -> None:
        if not snapshots:
            return
        symbol = snapshots[0].symbol
        path = _ls_ratio_path(self._base, symbol)
        new_df = pd.DataFrame(
            [
                {
                    "ts": s.ts,
                    "long_ratio": s.long_ratio,
                    "short_ratio": s.short_ratio,
                }
                for s in snapshots
            ]
        )
        new_df["ts"] = pd.to_datetime(new_df["ts"], utc=True)
        existing = _read_parquet(path)
        merged = _upsert(existing, new_df, "ts")
        _write_parquet(merged, path)

    def load_ls_ratio(self, symbol: str, limit: int | None = None) -> pd.DataFrame:
        path = _ls_ratio_path(self._base, symbol)
        df = _read_parquet(path)
        if df is None or df.empty:
            return pd.DataFrame(columns=_LS_RATIO_COLS)
        df = df[_LS_RATIO_COLS].sort_values("ts").reset_index(drop=True)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    # --- Taker volume ---

    def save_taker_volume(self, snapshots: list[TakerVolumeSnapshot]) -> None:
        if not snapshots:
            return
        symbol = snapshots[0].symbol
        path = _taker_vol_path(self._base, symbol)
        new_df = pd.DataFrame(
            [
                {
                    "ts": s.ts,
                    "buy_vol": float(s.buy_vol),
                    "sell_vol": float(s.sell_vol),
                }
                for s in snapshots
            ]
        )
        new_df["ts"] = pd.to_datetime(new_df["ts"], utc=True)
        existing = _read_parquet(path)
        merged = _upsert(existing, new_df, "ts")
        _write_parquet(merged, path)

    def load_taker_volume(self, symbol: str, limit: int | None = None) -> pd.DataFrame:
        path = _taker_vol_path(self._base, symbol)
        df = _read_parquet(path)
        if df is None or df.empty:
            return pd.DataFrame(columns=_TAKER_VOL_COLS)
        df = df[_TAKER_VOL_COLS].sort_values("ts").reset_index(drop=True)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    # --- Cleanup helpers ---

    def trim(
        self,
        symbol: str,
        before: datetime,
    ) -> None:
        """Remove all rows older than `before` across all data types."""
        path_fns: list[Callable[[], Path]] = [
            lambda: _ohlcv_path(self._base, symbol, Timeframe.H4),
            lambda: _ohlcv_path(self._base, symbol, Timeframe.H1),
            lambda: _ohlcv_path(self._base, symbol, Timeframe.D1),
            lambda: _oi_path(self._base, symbol),
            lambda: _ls_ratio_path(self._base, symbol),
            lambda: _taker_vol_path(self._base, symbol),
        ]
        for path_fn in path_fns:
            path = path_fn()
            df = _read_parquet(path)
            if df is None or df.empty:
                continue
            ts_col = "open_time" if "open_time" in df.columns else "ts"
            df = df[df[ts_col] >= pd.Timestamp(before, tz=UTC)]
            if not df.empty:
                _write_parquet(df.reset_index(drop=True), path)
