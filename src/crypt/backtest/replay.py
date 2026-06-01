"""
ReplayParquetStore — a read-only wrapper around ParquetStore that enforces
the no-look-ahead contract during backtesting.

Hard contract (from docs/backtest.md §5.1):

    At tick_time = T, no engine may access any datum with
    open_time >= T (candles) or ts >= T (OI/LS-ratio/taker-vol).

The live ParquetStore is safe by construction (future data has not arrived
yet). During replay we have the full dataset, so we must slice explicitly.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from crypt.data.store import ParquetStore
from crypt.models import (
    EvaluationContext,
    Timeframe,
)

# How many rows to load per data type before slicing.  Keep identical to the
# live context builder so the replay uses the same warm-up window.
_CANDLE_LIMIT = 250
_OI_LIMIT = 200
_LS_LIMIT = 100
_TAKER_LIMIT = 100


def _filter_ts(df: pd.DataFrame, col: str, cutoff: datetime) -> pd.DataFrame:
    """Return rows where col < cutoff (strict)."""
    ts = pd.Timestamp(cutoff)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return df[df[col] < ts].copy()


class ReplayParquetStore:
    """
    Wraps ParquetStore and adds a time-fence at `tick_time`.

    All data reads are sliced to `[..., tick_time)` so engines cannot
    accidentally see future information.  The wrapped store's write methods
    are NOT exposed — replay is read-only.
    """

    def __init__(self, store: ParquetStore) -> None:
        self._store = store
        self._candles_cache: dict[tuple[str, Timeframe], pd.DataFrame] = {}
        self._oi_cache: dict[str, pd.DataFrame] = {}
        self._ls_ratio_cache: dict[str, pd.DataFrame] = {}
        self._taker_volume_cache: dict[str, pd.DataFrame] = {}

    def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        tick_time: datetime,
        limit: int | None = _CANDLE_LIMIT,
    ) -> pd.DataFrame:
        """Load closed candles strictly before tick_time."""
        cache_key = (symbol, timeframe)
        if cache_key not in self._candles_cache:
            self._candles_cache[cache_key] = self._store.load_candles(
                symbol, timeframe, limit=None
            )
        df = self._candles_cache[cache_key]
        if df.empty:
            return df
        df = _filter_ts(df, "open_time", tick_time)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    def load_oi(
        self,
        symbol: str,
        tick_time: datetime,
        limit: int | None = _OI_LIMIT,
    ) -> pd.DataFrame:
        """Load open-interest snapshots strictly before tick_time."""
        if symbol not in self._oi_cache:
            self._oi_cache[symbol] = self._store.load_oi(symbol, limit=None)
        df = self._oi_cache[symbol]
        if df.empty:
            return df
        df = _filter_ts(df, "ts", tick_time)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    def load_ls_ratio(
        self,
        symbol: str,
        tick_time: datetime,
        limit: int | None = _LS_LIMIT,
    ) -> pd.DataFrame:
        """Load long/short ratio snapshots strictly before tick_time."""
        if symbol not in self._ls_ratio_cache:
            self._ls_ratio_cache[symbol] = self._store.load_ls_ratio(symbol, limit=None)
        df = self._ls_ratio_cache[symbol]
        if df.empty:
            return df
        df = _filter_ts(df, "ts", tick_time)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df

    def load_taker_volume(
        self,
        symbol: str,
        tick_time: datetime,
        limit: int | None = _TAKER_LIMIT,
    ) -> pd.DataFrame:
        """Load taker-volume snapshots strictly before tick_time."""
        if symbol not in self._taker_volume_cache:
            self._taker_volume_cache[symbol] = self._store.load_taker_volume(symbol, limit=None)
        df = self._taker_volume_cache[symbol]
        if df.empty:
            return df
        df = _filter_ts(df, "ts", tick_time)
        if limit is not None:
            df = df.tail(limit).reset_index(drop=True)
        return df


class ReplayContextBuilder:
    """
    Drop-in replacement for ContextBuilder during backtesting.

    Uses ReplayParquetStore to build an EvaluationContext that contains no
    data from tick_time onwards, matching the live invariant.
    """

    def __init__(self, replay_store: ReplayParquetStore) -> None:
        self._rs = replay_store

    def build(self, symbol: str, tick_time: datetime) -> EvaluationContext:
        candles: dict[Timeframe, pd.DataFrame] = {}
        for tf in (Timeframe.H4, Timeframe.H1, Timeframe.D1):
            df = self._rs.load_candles(symbol, tf, tick_time)
            if not df.empty:
                candles[tf] = df

        oi_df = self._rs.load_oi(symbol, tick_time)
        ls_df = self._rs.load_ls_ratio(symbol, tick_time)
        taker_df = self._rs.load_taker_volume(symbol, tick_time)

        from crypt.data.context import (
            _df_to_ls_ratio,
            _df_to_oi,
            _df_to_taker_volume,
        )

        return EvaluationContext(
            symbol=symbol,
            tick_time=tick_time,
            candles=candles,
            oi=_df_to_oi(oi_df, symbol),
            ls_ratio=_df_to_ls_ratio(ls_df, symbol),
            taker_volume=_df_to_taker_volume(taker_df, symbol),
        )
