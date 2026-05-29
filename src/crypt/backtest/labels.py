"""
Forward-label loader for the backtest harness.

Spec: docs/backtest.md §6.

For each verdict at tick_time T compute:
    return_h4  = (close[T + 4h]  - close[T]) / close[T]
    return_h24 = (close[T + 24h] - close[T]) / close[T]
    return_h96 = (close[T + 96h] - close[T]) / close[T]
    mae = (min_low  over [T, T+96h] - close[T]) / close[T]   # <= 0 for a long
    mfe = (max_high over [T, T+96h] - close[T]) / close[T]   # >= 0 for a long

The "hit" convention (direction-aware):
    hit_h4  = 1 if BUY and return_h4  > 0, or SELL and return_h4  < 0; else 0
    hit_h24 / hit_h96 — same for the longer horizons
    Neutral (HOLD) verdicts receive NaN for hit_*.

Drop the last 24 ticks from the labelled output — their 96h forward
windows are not fully observed in the historical dataset.

Convention for close[T]:
    tick_time T is the H4 bar boundary at which the tick fires.
    The H4 OHLCV dataframe uses open_time as row index; the bar that
    *closes* at T has open_time = T - 4h.  We therefore index the close
    series by bar close time: close_series[open_time + 4h] = close_price.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

_H4 = timedelta(hours=4)
_H24 = timedelta(hours=24)
_H96 = timedelta(hours=96)
# Drop the last N ticks whose 96h forward window is not fully observed.
DROP_TAIL_TICKS = 24


def compute_labels(
    verdicts_df: pd.DataFrame,
    h4_ohlcv: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join verdicts with forward OHLCV labels.

    Parameters
    ----------
    verdicts_df:
        Must have column ``tick_time`` (UTC timezone-aware).
        Should also have ``decision`` (BUY/SELL/HOLD) for hit-rate columns.
    h4_ohlcv:
        Full H4 OHLCV for the **same symbol**.  Columns:
        ``open_time`` (UTC datetime), ``o``, ``h``, ``l``, ``c``, ``volume``.
        Must span ``[min(tick_time), max(tick_time) + 96h]``.

    Returns
    -------
    pd.DataFrame
        verdicts_df with appended columns:
        ``entry_price``, ``return_h4``, ``return_h24``, ``return_h96``,
        ``mae``, ``mfe``, ``hit_h4``, ``hit_h24``, ``hit_h96``.
        Rows with incomplete forward windows are dropped.
        The last DROP_TAIL_TICKS rows are also dropped.
    """
    if verdicts_df.empty or h4_ohlcv.empty:
        return verdicts_df.copy()

    # Build close/high/low series indexed by bar close time.
    ohlcv = h4_ohlcv.copy()
    ohlcv["close_time"] = pd.to_datetime(ohlcv["open_time"], utc=True) + _H4
    ohlcv = ohlcv.set_index("close_time").sort_index()
    close_s = ohlcv["c"].astype(float)
    high_s = ohlcv["h"].astype(float)
    low_s = ohlcv["l"].astype(float)

    df = verdicts_df.copy()
    df["tick_time"] = pd.to_datetime(df["tick_time"], utc=True)
    df = df.sort_values("tick_time").reset_index(drop=True)

    # Drop the last DROP_TAIL_TICKS rows whose 96h forward window may not be fully observed.
    # Skip when the dataset is smaller than the drop window (unit tests / tiny slices).
    if len(df) > DROP_TAIL_TICKS:
        df = df.iloc[:-DROP_TAIL_TICKS].reset_index(drop=True)

    # Vectorised forward close prices.
    # Pass the pandas Series (not .values) to reindex so that timezone info is preserved;
    # datetime64[ns] from .values would drop the UTC marker and miss all index lookups.
    tick_times = df["tick_time"]
    t_h4 = tick_times + _H4
    t_h24 = tick_times + _H24
    t_h96 = tick_times + _H96

    c0 = close_s.reindex(tick_times).values.astype(float)
    c_h4 = close_s.reindex(t_h4).values.astype(float)
    c_h24 = close_s.reindex(t_h24).values.astype(float)
    c_h96 = close_s.reindex(t_h96).values.astype(float)

    # Rows where all four close prices are present and entry is non-zero.
    valid = ~np.isnan(c0) & ~np.isnan(c_h4) & ~np.isnan(c_h24) & ~np.isnan(c_h96) & (c0 != 0)

    df["entry_price"] = np.where(valid, c0, np.nan)
    df["return_h4"] = np.where(valid, (c_h4 - c0) / c0, np.nan)
    df["return_h24"] = np.where(valid, (c_h24 - c0) / c0, np.nan)
    df["return_h96"] = np.where(valid, (c_h96 - c0) / c0, np.nan)

    # MAE / MFE require scanning the forward bars — unavoidably per-row.
    mae_vals: list[float] = []
    mfe_vals: list[float] = []
    for idx, (t0, is_valid, entry) in enumerate(zip(tick_times, valid, c0, strict=False)):
        if not is_valid:
            mae_vals.append(float("nan"))
            mfe_vals.append(float("nan"))
            continue
        t0_ts = pd.Timestamp(t0)
        mask = (ohlcv.index > t0_ts) & (ohlcv.index <= t0_ts + _H96)
        window = ohlcv.loc[mask]
        if window.empty:
            mae_vals.append(float("nan"))
            mfe_vals.append(float("nan"))
            valid[idx] = False
            continue
        max_high = float(high_s.loc[mask].max())
        min_low = float(low_s.loc[mask].min())
        mae_vals.append((min_low - entry) / entry)
        mfe_vals.append((max_high - entry) / entry)

    df["mae"] = mae_vals
    df["mfe"] = mfe_vals

    # Recompute valid mask (may have been updated for empty window rows).
    valid = (
        ~df["return_h4"].isna()
        & ~df["return_h24"].isna()
        & ~df["return_h96"].isna()
        & ~df["mae"].isna()
        & ~df["mfe"].isna()
    )
    df = df[valid].reset_index(drop=True)

    # Hit-rate columns (direction-aware).
    if "decision" in df.columns:
        direction_sign = df["decision"].map({"BUY": 1, "SELL": -1, "HOLD": 0})
        for col, ret_col in [
            ("hit_h4", "return_h4"),
            ("hit_h24", "return_h24"),
            ("hit_h96", "return_h96"),
        ]:
            ret = df[ret_col]
            hit = pd.array(
                [
                    float("nan") if d == 0 else float(int(np.sign(r) == d))
                    for d, r in zip(direction_sign, ret, strict=False)
                ],
                dtype="object",
            )
            df[col] = hit

    return df
