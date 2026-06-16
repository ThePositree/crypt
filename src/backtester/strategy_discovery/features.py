from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput

REQUIRED_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class DiscoveryDataset:
    window_label: str
    symbol: str
    primary: pd.DataFrame
    features: pd.DataFrame


def build_donor_discovery_features(
    *,
    primary: pd.DataFrame,
    h4: pd.DataFrame | None,
    d1: pd.DataFrame | None,
) -> pd.DataFrame:
    """Discovery-aligned per-bar features for donor crypt_ensemble filter parity."""
    validated = _validate_primary(primary)
    features = _build_primary_features(validated)
    features["h4_context"] = _aligned_context_direction(h4, validated.index)
    features["d1_context"] = _aligned_context_direction(d1, validated.index)
    return features


def build_discovery_dataset(
    *,
    data: StrategyInput,
    window_label: str,
    symbol: str,
) -> DiscoveryDataset:
    primary = data.primary if isinstance(data, StrategyData) else data
    primary = _validate_primary(primary).copy()
    candles = data.candles if isinstance(data, StrategyData) else {}
    features = _build_primary_features(primary)
    features["h4_context"] = _aligned_context_direction(
        candles.get("H4"),
        primary.index,
    )
    features["d1_context"] = _aligned_context_direction(
        candles.get("D1"),
        primary.index,
    )
    return DiscoveryDataset(
        window_label=window_label,
        symbol=symbol,
        primary=primary,
        features=features,
    )


def _validate_primary(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Discovery data must use a DatetimeIndex")
    missing = [col for col in REQUIRED_OHLCV_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Discovery data missing columns: {missing}")
    if df.empty:
        raise ValueError("Discovery data is empty")
    frame = df.loc[:, REQUIRED_OHLCV_COLUMNS].copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame.sort_index(inplace=True)
    return frame


def _build_primary_features(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(14, min_periods=14).mean().shift(1)
    features["atr"] = atr
    features["atr_pct"] = atr / df["close"].replace(0, pd.NA)
    features["sma20"] = df["close"].rolling(20, min_periods=20).mean().shift(1)
    features["volume_median20"] = df["volume"].rolling(20, min_periods=20).median().shift(1)
    features["return_1"] = df["close"].pct_change()
    features["return_std20"] = features["return_1"].rolling(20, min_periods=20).std().shift(1)
    features["move_6_atr"] = (df["close"] - df["close"].shift(6)).abs() / features["atr"].replace(
        0, pd.NA
    )
    features["trend_strength_atr"] = (df["close"] - features["sma20"]).abs() / features[
        "atr"
    ].replace(0, pd.NA)
    features["volatility_rank"] = (
        features["atr_pct"].rolling(100, min_periods=20).rank(pct=True).shift(1)
    )
    ema9 = df["close"].ewm(span=9, adjust=False).mean().shift(1)
    ema21 = df["close"].ewm(span=21, adjust=False).mean().shift(1)
    ema50 = df["close"].ewm(span=50, adjust=False).mean().shift(1)
    features["ema9"] = ema9
    features["ema21"] = ema21
    features["ema50"] = ema50
    features["ema_stack_long"] = (ema9 > ema21) & (ema21 > ema50)
    features["ema_stack_short"] = (ema9 < ema21) & (ema21 < ema50)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(loss > 0, 100.0)
    rsi = rsi.where((gain > 0) | (loss > 0), 50.0)
    features["rsi14"] = rsi.shift(1)
    bb_std = df["close"].rolling(20, min_periods=20).std().shift(1)
    bb_mid = features["sma20"]
    features["bb_upper"] = bb_mid + 2 * bb_std
    features["bb_lower"] = bb_mid - 2 * bb_std
    features["bb_width_pct"] = (features["bb_upper"] - features["bb_lower"]) / bb_mid.replace(
        0, pd.NA
    )
    bar_range = df["high"] - df["low"]
    body = (df["close"] - df["open"]).abs()
    features["body_to_range"] = body / bar_range.replace(0, pd.NA)
    features["bar_range_atr"] = bar_range / atr.replace(0, pd.NA)
    features["roc10"] = df["close"].pct_change(10).shift(1)
    features["hour_utc"] = df.index.hour.astype("int64")
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    session_day = pd.Series(df.index.date, index=df.index)
    cumulative_tpv = (typical_price * df["volume"]).groupby(session_day).cumsum()
    cumulative_volume = df["volume"].groupby(session_day).cumsum()
    session_vwap = (cumulative_tpv / cumulative_volume.replace(0, pd.NA)).shift(1)
    features["session_vwap"] = session_vwap
    features["session_vwap_dist_pct"] = (
        (df["close"] - session_vwap) / df["close"].replace(0, pd.NA)
    ).shift(1)
    features["session_open_hour"] = (
        pd.Series(df.index.hour, index=df.index).groupby(session_day).transform("min")
    )
    bar_range = df["high"] - df["low"]
    body = (df["close"] - df["open"]).abs()
    features["upper_wick_ratio"] = (
        (df["high"] - df[["open", "close"]].max(axis=1)) / body.replace(0, pd.NA)
    ).shift(1)
    features["lower_wick_ratio"] = (
        (df[["open", "close"]].min(axis=1) - df["low"]) / body.replace(0, pd.NA)
    ).shift(1)
    features["gap_pct"] = (
        (df["open"] - df["close"].shift(1)) / df["close"].shift(1).replace(0, pd.NA)
    ).shift(1)
    bull_bar = df["close"] > df["open"]
    bear_bar = df["close"] < df["open"]
    features["consecutive_bull"] = _consecutive_true_count(bull_bar).shift(1)
    features["consecutive_bear"] = _consecutive_true_count(bear_bar).shift(1)
    features["prior_bar_same_color"] = (
        bull_bar.astype("boolean") == bull_bar.shift(1).astype("boolean")
    ).shift(1)
    atr5 = true_range.rolling(5, min_periods=5).mean().shift(1)
    features["atr_ratio_5_20"] = (atr5 / atr.replace(0, pd.NA)).shift(1)
    features["bb_width_rank_20"] = (
        features["bb_width_pct"].rolling(20, min_periods=10).rank(pct=True).shift(1)
    )
    features["bar_range_rank_20"] = (
        (bar_range / atr.replace(0, np.nan)).rolling(20, min_periods=10).rank(pct=True).shift(1)
    )
    rolling_bb_min = features["bb_width_pct"].rolling(20, min_periods=10).min().shift(1)
    features["bb_at_20bar_low"] = features["bb_width_pct"] <= rolling_bb_min
    features["bb_expanding"] = features["bb_width_pct"] > features["bb_width_pct"].shift(1) * 1.1
    features["is_nr4"] = bar_range <= bar_range.rolling(4, min_periods=4).min()
    features["is_nr14"] = bar_range <= bar_range.rolling(14, min_periods=14).min()
    features["donchian_high_20"] = df["high"].rolling(20, min_periods=10).max().shift(1)
    features["donchian_low_20"] = df["low"].rolling(20, min_periods=10).min().shift(1)
    features["volume_ratio_20"] = (
        df["volume"] / features["volume_median20"].replace(0, pd.NA)
    ).shift(1)
    features["close_location"] = (
        (df["close"] - df["low"]) / bar_range.replace(0, pd.NA)
    ).shift(1)
    ema12 = df["close"].ewm(span=12, adjust=False).mean().shift(1)
    ema26 = df["close"].ewm(span=26, adjust=False).mean().shift(1)
    features["macd_proxy"] = ema12 - ema26
    features["macd_signal_proxy"] = features["macd_proxy"].ewm(span=9, adjust=False).mean()
    _add_pinescript_features(df, features, true_range)
    return features


def _add_pinescript_features(
    df: pd.DataFrame, features: pd.DataFrame, true_range: pd.Series
) -> None:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    atr10 = true_range.rolling(10, min_periods=10).mean()
    hl2 = (high + low) / 2
    upper_basic = hl2 - 3.0 * atr10
    lower_basic = hl2 + 3.0 * atr10
    upper_band = _supertrend_upper_band(upper_basic, close)
    lower_band = _supertrend_lower_band(lower_basic, close)
    supertrend_dir = _supertrend_direction(close, upper_band, lower_band)
    features["ps_supertrend_upper"] = upper_band
    features["ps_supertrend_lower"] = lower_band
    features["ps_supertrend_dir"] = supertrend_dir

    ut_trail = _atr_trailing_stop(close, atr10)
    features["ps_ut_trail"] = ut_trail

    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std()
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    kc_mid = close.rolling(20, min_periods=20).mean()
    range_ma = true_range.rolling(20, min_periods=20).mean()
    kc_upper = kc_mid + 1.5 * range_ma
    kc_lower = kc_mid - 1.5 * range_ma
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    squeeze_off = (bb_lower < kc_lower) & (bb_upper > kc_upper)
    squeeze_basis = (high.rolling(20, min_periods=20).max() + low.rolling(20, min_periods=20).min()) / 2
    squeeze_source = close - ((squeeze_basis + bb_mid) / 2)
    squeeze_momentum = _rolling_linreg_last(squeeze_source, 20)
    features["ps_squeeze_on"] = squeeze_on
    features["ps_squeeze_off"] = squeeze_off
    features["ps_squeeze_release"] = squeeze_off & squeeze_on.shift(1).fillna(False)
    features["ps_squeeze_momentum"] = squeeze_momentum
    features["ps_squeeze_momentum_slope"] = squeeze_momentum - squeeze_momentum.shift(1)

    ap = (high + low + close) / 3
    esa = ap.ewm(span=10, adjust=False).mean()
    dev = (ap - esa).abs().ewm(span=10, adjust=False).mean()
    ci = (ap - esa) / (0.015 * dev.replace(0, np.nan))
    wt1 = ci.ewm(span=21, adjust=False).mean()
    wt2 = wt1.rolling(4, min_periods=4).mean()
    features["ps_wt1"] = wt1
    features["ps_wt2"] = wt2

    ema12_now = close.ewm(span=12, adjust=False).mean()
    ema26_now = close.ewm(span=26, adjust=False).mean()
    macd = ema12_now - ema26_now
    macd_signal = macd.rolling(9, min_periods=9).mean()
    macd_hist = macd - macd_signal
    features["ps_macd"] = macd
    features["ps_macd_signal"] = macd_signal
    features["ps_macd_hist"] = macd_hist
    features["ps_macd_hist_slope"] = macd_hist - macd_hist.shift(1)

    up_move = high.diff()
    down_move = -low.diff()
    dm_plus = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    dm_minus = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    smoothed_tr = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(alpha=1 / 14, adjust=False).mean() / smoothed_tr.replace(0, np.nan)
    di_minus = 100 * dm_minus.ewm(alpha=1 / 14, adjust=False).mean() / smoothed_tr.replace(0, np.nan)
    dx = ((di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)) * 100
    features["ps_di_plus"] = di_plus
    features["ps_di_minus"] = di_minus
    features["ps_adx"] = dx.rolling(14, min_periods=14).mean()

    vixfix = ((close.rolling(22, min_periods=22).max() - low) / close.rolling(22, min_periods=22).max()) * 100
    vix_mid = vixfix.rolling(20, min_periods=20).mean()
    vix_upper = vix_mid + 2.0 * vixfix.rolling(20, min_periods=20).std()
    vix_range_high = vixfix.rolling(50, min_periods=20).max() * 0.85
    features["ps_vixfix"] = vixfix
    features["ps_vixfix_spike"] = (vixfix >= vix_upper) | (vixfix >= vix_range_high)

    features["ps_pivot_high"] = high.rolling(31, center=True, min_periods=31).max().shift(15)
    features["ps_pivot_low"] = low.rolling(31, center=True, min_periods=31).min().shift(15)
    vol_ema5 = df["volume"].ewm(span=5, adjust=False).mean()
    vol_ema10 = df["volume"].ewm(span=10, adjust=False).mean()
    features["ps_volume_osc"] = 100 * (vol_ema5 - vol_ema10) / vol_ema10.replace(0, np.nan)

    pivot_high_fast = high.rolling(15, min_periods=15).max().shift(1)
    pivot_low_fast = low.rolling(15, min_periods=15).min().shift(1)
    features["ps_trendline_upper"] = pivot_high_fast - (features["atr"] / 14.0)
    features["ps_trendline_lower"] = pivot_low_fast + (features["atr"] / 14.0)
    features["ps_trendline_upper_slope"] = features["ps_trendline_upper"].diff()
    features["ps_trendline_lower_slope"] = features["ps_trendline_lower"].diff()
    features["ps_killzone"] = pd.Series(df.index.hour, index=df.index).map(_killzone_label)


def _supertrend_upper_band(basic: pd.Series, close: pd.Series) -> pd.Series:
    values = basic.copy()
    for idx in range(1, len(values)):
        prev = values.iat[idx - 1]
        if pd.notna(prev) and close.iat[idx - 1] > prev:
            values.iat[idx] = max(values.iat[idx], prev)
    return values


def _supertrend_lower_band(basic: pd.Series, close: pd.Series) -> pd.Series:
    values = basic.copy()
    for idx in range(1, len(values)):
        prev = values.iat[idx - 1]
        if pd.notna(prev) and close.iat[idx - 1] < prev:
            values.iat[idx] = min(values.iat[idx], prev)
    return values


def _supertrend_direction(close: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
    direction = pd.Series(1, index=close.index, dtype="int64")
    for idx in range(1, len(close)):
        prev_dir = direction.iat[idx - 1]
        if prev_dir == -1 and pd.notna(lower.iat[idx - 1]) and close.iat[idx] > lower.iat[idx - 1]:
            direction.iat[idx] = 1
        elif prev_dir == 1 and pd.notna(upper.iat[idx - 1]) and close.iat[idx] < upper.iat[idx - 1]:
            direction.iat[idx] = -1
        else:
            direction.iat[idx] = prev_dir
    return direction


def _atr_trailing_stop(close: pd.Series, atr: pd.Series, multiplier: float = 1.0) -> pd.Series:
    trail = pd.Series(index=close.index, dtype="float64")
    for idx in range(len(close)):
        loss = multiplier * atr.iat[idx]
        if idx == 0 or pd.isna(loss):
            trail.iat[idx] = close.iat[idx]
            continue
        prev = trail.iat[idx - 1]
        if close.iat[idx] > prev and close.iat[idx - 1] > prev:
            trail.iat[idx] = max(prev, close.iat[idx] - loss)
        elif close.iat[idx] < prev and close.iat[idx - 1] < prev:
            trail.iat[idx] = min(prev, close.iat[idx] + loss)
        elif close.iat[idx] > prev:
            trail.iat[idx] = close.iat[idx] - loss
        else:
            trail.iat[idx] = close.iat[idx] + loss
    return trail


def _rolling_linreg_last(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype="float64")

    def _fit(values: Any) -> float:
        if np.isnan(values).any():
            return np.nan
        slope, intercept = np.polyfit(x, values, 1)
        return float(intercept + slope * (window - 1))

    return series.rolling(window, min_periods=window).apply(_fit, raw=True)


def _killzone_label(hour: int) -> str:
    if 0 <= hour < 4:
        return "asia"
    if 7 <= hour < 10:
        return "london"
    if 13 <= hour < 16:
        return "nyam"
    if 17 <= hour < 20:
        return "nypm"
    return "other"


def _consecutive_true_count(mask: pd.Series) -> pd.Series:
    groups = (mask != mask.shift(fill_value=False)).cumsum()
    return mask.groupby(groups).cumsum().astype("int64")


def _aligned_context_direction(
    frame: pd.DataFrame | None,
    target_index: pd.DatetimeIndex,
) -> pd.Series:
    if frame is None or frame.empty:
        return pd.Series("missing", index=target_index)
    context = _validate_primary(frame)
    sma = context["close"].rolling(20, min_periods=20).mean().shift(1)
    direction = pd.Series("neutral", index=context.index)
    direction.loc[context["close"] > sma] = "long"
    direction.loc[context["close"] < sma] = "short"
    direction.index = _available_after_close_index(context.index)
    return direction.reindex(target_index, method="ffill").fillna("missing")


def _available_after_close_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if len(index) < 2:
        return index
    deltas = index.to_series().diff().dropna()
    if deltas.empty:
        return index
    return index + deltas.median()
