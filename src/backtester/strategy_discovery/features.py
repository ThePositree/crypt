from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput

REQUIRED_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class DiscoveryDataset:
    window_label: str
    symbol: str
    primary: pd.DataFrame
    features: pd.DataFrame


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
    return features


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
