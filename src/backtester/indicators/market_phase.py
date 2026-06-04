"""Market regime phase from Supertrend and optional ADX filtering."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's smoothed moving average (RMA), as used for ATR on TradingView.

    Parameters
    ----------
    series:
        Input values (e.g. true range).
    length:
        Smoothing length.

    Returns
    -------
    pd.Series
        RMA aligned to ``series.index``; leading values until ``length`` are NaN
        except the first seeded value at position ``length - 1``.
    """
    result = pd.Series(np.nan, index=series.index)
    if len(series) < length:
        return result
    result.iloc[length - 1] = series.iloc[:length].mean()
    for i in range(length, len(series)):
        result.iloc[i] = (result.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    return result


def compute_supertrend_adx_phase(
    df: pd.DataFrame,
    *,
    atr_period: int = 10,
    multiplier: float = 3.0,
    adx_period: int = 14,
    adx_thresh: float = 20.0,
    use_adx_filter: bool = True,
    warmup_bars: int | None = None,
) -> pd.Series:
    """Classify each bar into bull / bear / sideways using Supertrend and ADX.

    Supertrend bands follow the usual iterative Pine Script v4-style update.
    When ``use_adx_filter`` is True, bars with ADX below ``adx_thresh`` are
    labelled sideways (``0``) regardless of Supertrend direction; otherwise the
    raw Supertrend direction is used (``1`` up, ``-1`` down).

    The first ``warmup_bars`` rows (default ``max(atr_period, adx_period) * 2 + 5``)
    are set to NaN so downstream logic can treat them as "no regime".

    Parameters
    ----------
    df:
        OHLCV data; must contain columns ``open``, ``high``, ``low``, ``close``.
        The frame is sorted by index internally; the returned series is
        reindexed to match ``df.index`` row-for-row.
    atr_period:
        Length for ATR (RMA of true range).
    multiplier:
        Band distance from mid-price in ATR units.
    adx_period:
        Length for ADX components when the ADX filter is enabled.
    adx_thresh:
        ADX threshold; below this value phase is ``0`` when filtering is on.
    use_adx_filter:
        If False, phase is only Supertrend direction (no sideways bucket).
    warmup_bars:
        Explicit warm-up bar count. If None, uses
        ``max(atr_period, adx_period) * 2 + 5``.

    Returns
    -------
    pd.Series
        Phase per bar: ``1`` bullish, ``-1`` bearish, ``0`` sideways,
        ``NaN`` during warm-up or when ATR cannot be seeded.

    Notes
    -----
    Index should be unique so reindexing after ``sort_index`` preserves rows.
    """
    sorted_df = df.sort_index().copy()
    idx = sorted_df.index

    prev_close = sorted_df["close"].shift(1)
    tr = pd.concat(
        [
            sorted_df["high"] - sorted_df["low"],
            (sorted_df["high"] - prev_close).abs(),
            (sorted_df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = _rma(tr, atr_period)

    src = (sorted_df["high"] + sorted_df["low"]) / 2.0
    up_basic = src - multiplier * atr
    dn_basic = src + multiplier * atr

    up = pd.Series(np.nan, index=idx)
    dn = pd.Series(np.nan, index=idx)
    trend = pd.Series(np.nan, index=idx)

    start_idx = atr.first_valid_index()
    if start_idx is None:
        out = pd.Series(np.nan, index=idx)
        return out.reindex(df.index)

    idx_list = idx.tolist()
    start_pos = idx_list.index(start_idx)

    up.iloc[start_pos] = up_basic.iloc[start_pos]
    dn.iloc[start_pos] = dn_basic.iloc[start_pos]
    trend.iloc[start_pos] = 1

    for i in range(start_pos + 1, len(sorted_df)):
        up1 = up.iloc[i - 1] if not pd.isna(up.iloc[i - 1]) else up_basic.iloc[i]
        dn1 = dn.iloc[i - 1] if not pd.isna(dn.iloc[i - 1]) else dn_basic.iloc[i]

        curr_up_basic = up_basic.iloc[i]
        curr_dn_basic = dn_basic.iloc[i]

        prev_close_val = sorted_df["close"].iloc[i - 1]

        if prev_close_val > up1:
            up_val = max(curr_up_basic, up1)
        else:
            up_val = curr_up_basic

        if prev_close_val < dn1:
            dn_val = min(curr_dn_basic, dn1)
        else:
            dn_val = curr_dn_basic

        up.iloc[i] = up_val
        dn.iloc[i] = dn_val

        curr_close = sorted_df["close"].iloc[i]
        prev_trend = trend.iloc[i - 1]

        if prev_trend == -1 and curr_close > dn1:
            trend.iloc[i] = 1
        elif prev_trend == 1 and curr_close < up1:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = prev_trend

    if use_adx_filter:
        dm_pos = (sorted_df["high"] - sorted_df["high"].shift(1)).clip(lower=0)
        dm_neg = (sorted_df["low"].shift(1) - sorted_df["low"]).clip(lower=0)

        tr_rma = _rma(tr, adx_period)
        di_p = (_rma(dm_pos, adx_period) / tr_rma) * 100
        di_n = (_rma(dm_neg, adx_period) / tr_rma) * 100

        dx = 100 * (di_p - di_n).abs() / (di_p + di_n + 1e-10)
        adx = _rma(dx, adx_period)

        phase = np.where(adx < adx_thresh, 0, trend)
        phase = pd.Series(phase, index=idx, dtype=float)
    else:
        phase = trend.astype(float)

    if warmup_bars is None:
        warmup = max(atr_period, adx_period) * 2 + 5
    else:
        warmup = warmup_bars
    if warmup > 0:
        phase.iloc[:warmup] = np.nan

    return phase.reindex(df.index)
