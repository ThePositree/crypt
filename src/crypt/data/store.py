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
    LongShortRatioSnapshot,
    OISnapshot,
    TakerVolumeSnapshot,
    Timeframe,
)

# Column schemas for each data type.
_OHLCV_COLS = ["open_time", "o", "h", "l", "c", "volume"]
_OI_COLS = ["ts", "oi"]
_LS_RATIO_COLS = ["ts", "long_ratio", "short_ratio"]
_TAKER_VOL_COLS = ["ts", "buy_vol", "sell_vol"]


def _symbol_dir(base: Path, symbol: str) -> Path:
    # e.g.  data/SOL-USDT-SWAP/
    return base / symbol


def _ohlcv_path(base: Path, symbol: str, timeframe: Timeframe) -> Path:
    return _symbol_dir(base, symbol) / f"ohlcv_{timeframe.value}.parquet"


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
        path = _ohlcv_path(self._base, symbol, tf)
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
        existing = _read_parquet(path)
        merged = _upsert(existing, new_df, "open_time")
        _write_parquet(merged, path)
        logger.debug("Saved {} {} candles for {}", len(candles), tf.value, symbol)

    def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame of closed candles: columns open_time, o, h, l, c, volume.
        Sorted ascending by open_time. Returns empty DataFrame if nothing stored.
        """
        path = _ohlcv_path(self._base, symbol, timeframe)
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
