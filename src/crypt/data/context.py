from __future__ import annotations

from datetime import datetime

import pandas as pd

from crypt.data.store import ParquetStore
from crypt.models import (
    EvaluationContext,
    FundingSnapshot,
    LongShortRatioSnapshot,
    OISnapshot,
    TakerVolumeSnapshot,
    Timeframe,
)

# How many rows to load for each data type when building a context.
_CANDLE_LIMIT = 250
_FUNDING_LIMIT = 200  # ~7-8 days of 8h funding snapshots
_OI_LIMIT = 200  # ~8 days of hourly
_LS_LIMIT = 100  # ~4 days of hourly
_TAKER_LIMIT = 100


def _df_to_funding(df: pd.DataFrame, symbol: str) -> list[FundingSnapshot] | None:
    if df.empty:
        return None
    result = []
    for _, row in df.iterrows():
        from decimal import Decimal

        result.append(
            FundingSnapshot(
                symbol=symbol,
                ts=row["ts"].to_pydatetime() if hasattr(row["ts"], "to_pydatetime") else row["ts"],
                rate=Decimal(str(row["rate"])),
            )
        )
    return result or None


def _df_to_oi(df: pd.DataFrame, symbol: str) -> list[OISnapshot] | None:
    if df.empty:
        return None
    from decimal import Decimal

    result = []
    for _, row in df.iterrows():
        result.append(
            OISnapshot(
                symbol=symbol,
                ts=row["ts"].to_pydatetime() if hasattr(row["ts"], "to_pydatetime") else row["ts"],
                oi=Decimal(str(row["oi"])),
            )
        )
    return result or None


def _df_to_ls_ratio(df: pd.DataFrame, symbol: str) -> list[LongShortRatioSnapshot] | None:
    if df.empty:
        return None
    result = []
    for _, row in df.iterrows():
        result.append(
            LongShortRatioSnapshot(
                symbol=symbol,
                ts=row["ts"].to_pydatetime() if hasattr(row["ts"], "to_pydatetime") else row["ts"],
                long_ratio=float(row["long_ratio"]),
                short_ratio=float(row["short_ratio"]),
            )
        )
    return result or None


def _df_to_taker_volume(df: pd.DataFrame, symbol: str) -> list[TakerVolumeSnapshot] | None:
    if df.empty:
        return None
    from decimal import Decimal

    result = []
    for _, row in df.iterrows():
        result.append(
            TakerVolumeSnapshot(
                symbol=symbol,
                ts=row["ts"].to_pydatetime() if hasattr(row["ts"], "to_pydatetime") else row["ts"],
                buy_vol=Decimal(str(row["buy_vol"])),
                sell_vol=Decimal(str(row["sell_vol"])),
            )
        )
    return result or None


class ContextBuilder:
    """
    Assembles an EvaluationContext for one symbol from the ParquetStore.

    Candles are returned as DataFrames (float64 columns) because engines
    operate on vectorised pandas/numpy arrays via pandas-ta.
    """

    def __init__(self, store: ParquetStore) -> None:
        self._store = store

    def build(self, symbol: str, tick_time: datetime) -> EvaluationContext:
        candles: dict[Timeframe, pd.DataFrame] = {}
        for tf in (Timeframe.H4, Timeframe.H1, Timeframe.D1):
            df = self._store.load_candles(symbol, tf, limit=_CANDLE_LIMIT)
            if not df.empty:
                candles[tf] = df

        funding_df = self._store.load_funding(symbol, limit=_FUNDING_LIMIT)
        oi_df = self._store.load_oi(symbol, limit=_OI_LIMIT)
        ls_df = self._store.load_ls_ratio(symbol, limit=_LS_LIMIT)
        taker_df = self._store.load_taker_volume(symbol, limit=_TAKER_LIMIT)

        return EvaluationContext(
            symbol=symbol,
            tick_time=tick_time,
            candles=candles,
            funding=_df_to_funding(funding_df, symbol),
            oi=_df_to_oi(oi_df, symbol),
            ls_ratio=_df_to_ls_ratio(ls_df, symbol),
            taker_volume=_df_to_taker_volume(taker_df, symbol),
        )
