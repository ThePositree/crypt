from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class NativeTrailingGeometry:
    activation_price: float
    callback_spread: float
    fixed_take_profit_enabled: bool


def build_native_trailing_geometry(
    *,
    entry_price: float,
    stop_price: float,
    take_profit_price: float,
    is_long: bool,
    activation_rrr: float,
    distance_atr: float,
    entry_atr: float,
) -> NativeTrailingGeometry:
    if activation_rrr <= 0 or distance_atr <= 0 or entry_atr <= 0:
        raise ValueError("native trailing requires positive activation, distance, and entry ATR")
    stop_distance = abs(entry_price - stop_price)
    activation_price = (
        entry_price + stop_distance * activation_rrr
        if is_long
        else entry_price - stop_distance * activation_rrr
    )
    callback_spread = entry_atr * distance_atr
    fixed_take_profit_enabled = (
        take_profit_price < activation_price if is_long else take_profit_price > activation_price
    )
    return NativeTrailingGeometry(
        activation_price=activation_price,
        callback_spread=callback_spread,
        fixed_take_profit_enabled=fixed_take_profit_enabled,
    )


def with_closed_atr14(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["trail_atr"] = _true_range(df).rolling(14).mean().shift(1)
    return enriched


def latest_entry_atr14(df: pd.DataFrame) -> float | None:
    values = _true_range(df).rolling(14).mean()
    if values.empty or pd.isna(values.iloc[-1]):
        return None
    value = float(values.iloc[-1])
    return value if value > 0 else None


def _true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
