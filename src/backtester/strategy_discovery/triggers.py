from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import DiscoveryDataset

TriggerFn = Callable[[DiscoveryDataset], list[DiscoveryEvent]]


def trigger_catalog() -> dict[str, TriggerFn]:
    from backtester.strategy_discovery.catalog_expansion import expansion_trigger_catalog

    return {
        "h1_candle_confirm": _h1_candle_confirm,
        "h1_sweep_reversal": _h1_sweep_reversal,
        "h1_structure_break": _h1_structure_break,
        "h1_order_block_retest": _h1_order_block_retest,
        "h1_pivot_reclaim": _h1_pivot_reclaim,
        "h1_range_breakout": _h1_range_breakout,
        "h1_momentum_burst": _h1_momentum_burst,
        "h1_mean_revert_wick": _h1_mean_revert_wick,
        "h1_ema_cross": _h1_ema_cross,
        "h1_rsi_reversal": _h1_rsi_reversal,
        "h1_bb_rejection": _h1_bb_rejection,
        "h1_engulfing": _h1_engulfing,
        "h1_inside_bar_breakout": _h1_inside_bar_breakout,
        "h1_nr7_breakout": _h1_nr7_breakout,
        **expansion_trigger_catalog(),
    }


def _h1_candle_confirm(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    long_mask = df["close"] > df["open"]
    short_mask = df["close"] < df["open"]
    return _events_from_masks(dataset, "h1_candle_confirm", long_mask, short_mask)


def _h1_sweep_reversal(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    prior_low = df["low"].rolling(12, min_periods=6).min().shift(1)
    prior_high = df["high"].rolling(12, min_periods=6).max().shift(1)
    long_mask = (df["low"] < prior_low) & (df["close"] > df["open"])
    short_mask = (df["high"] > prior_high) & (df["close"] < df["open"])
    return _events_from_masks(
        dataset,
        "h1_sweep_reversal",
        long_mask,
        short_mask,
        anchor_type="liquidity_sweep",
    )


def _h1_structure_break(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    prior_high = df["high"].rolling(20, min_periods=10).max().shift(1)
    prior_low = df["low"].rolling(20, min_periods=10).min().shift(1)
    long_mask = df["close"] > prior_high
    short_mask = df["close"] < prior_low
    return _events_from_masks(
        dataset,
        "h1_structure_break",
        long_mask,
        short_mask,
        anchor_type="structure",
    )


def _h1_order_block_retest(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    previous_bearish = df["close"].shift(1) < df["open"].shift(1)
    previous_bullish = df["close"].shift(1) > df["open"].shift(1)
    previous_mid = (df["open"].shift(1) + df["close"].shift(1)) / 2
    retest = (df["low"] <= previous_mid) & (df["high"] >= previous_mid)
    long_mask = previous_bearish & retest & (df["close"] > previous_mid)
    short_mask = previous_bullish & retest & (df["close"] < previous_mid)
    return _events_from_masks(
        dataset,
        "h1_order_block_retest",
        long_mask,
        short_mask,
        anchor_type="order_block",
        anchor_age_bars=1,
        anchor_price=previous_mid,
    )


def _h1_pivot_reclaim(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    prior_low = df["low"].rolling(5, min_periods=5).min().shift(1)
    prior_high = df["high"].rolling(5, min_periods=5).max().shift(1)
    long_mask = (df["low"] <= prior_low) & (df["close"] > df["close"].shift(1))
    short_mask = (df["high"] >= prior_high) & (df["close"] < df["close"].shift(1))
    anchor_price = pd.Series(index=df.index, dtype="float64")
    anchor_price.loc[long_mask] = prior_low.loc[long_mask]
    anchor_price.loc[short_mask] = prior_high.loc[short_mask]
    return _events_from_masks(
        dataset,
        "h1_pivot_reclaim",
        long_mask,
        short_mask,
        anchor_type="pivot",
        anchor_age_bars=1,
        anchor_price=anchor_price,
    )


def _h1_range_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    range_high = df["high"].rolling(24, min_periods=12).max().shift(1)
    range_low = df["low"].rolling(24, min_periods=12).min().shift(1)
    long_mask = df["close"] > range_high
    short_mask = df["close"] < range_low
    anchor_price = pd.Series(index=df.index, dtype="float64")
    anchor_price.loc[long_mask] = range_high.loc[long_mask]
    anchor_price.loc[short_mask] = range_low.loc[short_mask]
    return _events_from_masks(
        dataset,
        "h1_range_breakout",
        long_mask,
        short_mask,
        anchor_type="range",
        anchor_age_bars=24,
        anchor_price=anchor_price,
    )


def _h1_momentum_burst(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    std = dataset.features["return_std20"]
    ret = dataset.features["return_1"]
    long_mask = (ret > std * 1.5) & (df["close"] > df["open"])
    short_mask = (ret < -std * 1.5) & (df["close"] < df["open"])
    return _events_from_masks(dataset, "h1_momentum_burst", long_mask, short_mask)


def _h1_ema_cross(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    features = dataset.features
    ema9 = features["ema9"]
    ema21 = features["ema21"]
    long_mask = (ema9 > ema21) & (ema9.shift(1) <= ema21.shift(1))
    short_mask = (ema9 < ema21) & (ema9.shift(1) >= ema21.shift(1))
    return _events_from_masks(
        dataset,
        "h1_ema_cross",
        long_mask,
        short_mask,
        anchor_type="structure",
    )


def _h1_rsi_reversal(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    rsi = dataset.features["rsi14"]
    prev_rsi = rsi.shift(1)
    long_mask = (rsi < 35) & (df["close"] > df["open"]) & (rsi > prev_rsi)
    short_mask = (rsi > 65) & (df["close"] < df["open"]) & (rsi < prev_rsi)
    return _events_from_masks(dataset, "h1_rsi_reversal", long_mask, short_mask)


def _h1_bb_rejection(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    bb_lower = dataset.features["bb_lower"]
    bb_upper = dataset.features["bb_upper"]
    long_mask = (df["low"] <= bb_lower) & (df["close"] > df["open"])
    short_mask = (df["high"] >= bb_upper) & (df["close"] < df["open"])
    return _events_from_masks(
        dataset,
        "h1_bb_rejection",
        long_mask,
        short_mask,
        anchor_type="range",
    )


def _h1_engulfing(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    prev_bear = prev_close < prev_open
    prev_bull = prev_close > prev_open
    long_mask = (
        prev_bear
        & (df["close"] > df["open"])
        & (df["open"] <= prev_close)
        & (df["close"] >= prev_open)
    )
    short_mask = (
        prev_bull
        & (df["close"] < df["open"])
        & (df["open"] >= prev_close)
        & (df["close"] <= prev_open)
    )
    return _events_from_masks(dataset, "h1_engulfing", long_mask, short_mask)


def _h1_inside_bar_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    mother_high = df["high"].shift(2)
    mother_low = df["low"].shift(2)
    inside = (df["high"].shift(1) < mother_high) & (df["low"].shift(1) > mother_low)
    long_mask = inside & (df["close"] > mother_high)
    short_mask = inside & (df["close"] < mother_low)
    anchor_price = pd.Series(index=df.index, dtype="float64")
    anchor_price.loc[long_mask] = mother_high.loc[long_mask]
    anchor_price.loc[short_mask] = mother_low.loc[short_mask]
    return _events_from_masks(
        dataset,
        "h1_inside_bar_breakout",
        long_mask,
        short_mask,
        anchor_type="range",
        anchor_age_bars=2,
        anchor_price=anchor_price,
    )


def _h1_nr7_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    bar_range = df["high"] - df["low"]
    is_nr7 = bar_range <= bar_range.rolling(7, min_periods=7).min()
    long_mask = is_nr7 & (df["close"] > df["open"])
    short_mask = is_nr7 & (df["close"] < df["open"])
    return _events_from_masks(
        dataset,
        "h1_nr7_breakout",
        long_mask,
        short_mask,
        anchor_type="range",
    )


def _h1_mean_revert_wick(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    body = (df["close"] - df["open"]).abs()
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    long_mask = (lower_wick > body * 2) & (df["close"] > df["open"])
    short_mask = (upper_wick > body * 2) & (df["close"] < df["open"])
    return _events_from_masks(
        dataset,
        "h1_mean_revert_wick",
        long_mask,
        short_mask,
        anchor_type="pivot",
    )


def _events_from_masks(
    dataset: DiscoveryDataset,
    trigger_name: str,
    long_mask: pd.Series,
    short_mask: pd.Series,
    *,
    anchor_type: str | None = None,
    anchor_age_bars: int | None = None,
    anchor_price: pd.Series | None = None,
) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    events: list[DiscoveryEvent] = []
    for side, mask in (("long", long_mask), ("short", short_mask)):
        selected = mask.fillna(False)
        for event_time in df.index[selected]:
            metadata = _base_metadata(dataset, event_time, side)
            if anchor_type is not None:
                metadata["anchor_type"] = anchor_type
            if anchor_age_bars is not None:
                metadata["anchor_age_hours"] = _bars_to_hours(df.index, anchor_age_bars)
            if anchor_price is not None:
                price = anchor_price.loc[event_time]
                if pd.notna(price):
                    metadata["anchor_price"] = float(price)
                    atr = dataset.features.loc[event_time, "atr"]
                    if pd.notna(atr) and float(atr) > 0:
                        metadata["atr_distance"] = abs(
                            float(df.loc[event_time, "close"]) - float(price)
                        ) / float(atr)
            events.append(
                DiscoveryEvent(
                    event_time=pd.Timestamp(event_time),
                    side=side,  # type: ignore[arg-type]
                    trigger_name=trigger_name,
                    entry_reference_price=float(df.loc[event_time, "close"]),
                    window_label=dataset.window_label,
                    symbol=dataset.symbol,
                    metadata=metadata,
                )
            )
    events.sort(key=lambda event: (event.event_time, event.side))
    return events


def _base_metadata(
    dataset: DiscoveryDataset, event_time: pd.Timestamp, side: str
) -> dict[str, object]:
    row = dataset.ohlcv.loc[event_time]
    features = dataset.features.loc[event_time]
    return {
        "rule_version": 1,
        "side": side,
        "close": float(row["close"]),
        "open": float(row["open"]),
        "atr": _float_or_none(features.get("atr")),
        "d1_context": str(features.get("d1_context", "missing")),
        "h4_context": str(features.get("h4_context", "missing")),
        "trend_strength_atr": _float_or_none(features.get("trend_strength_atr")),
        "volatility_rank": _float_or_none(features.get("volatility_rank")),
        "move_6_atr": _float_or_none(features.get("move_6_atr")),
        "volume": _float_or_none(row.get("volume")),
        "volume_median20": _float_or_none(features.get("volume_median20")),
        "rsi14": _float_or_none(features.get("rsi14")),
        "body_to_range": _float_or_none(features.get("body_to_range")),
        "bb_width_pct": _float_or_none(features.get("bb_width_pct")),
        "bar_range_atr": _float_or_none(features.get("bar_range_atr")),
        "hour_utc": _int_or_none(features.get("hour_utc")),
        "roc10": _float_or_none(features.get("roc10")),
        "ema_stack_long": bool(features.get("ema_stack_long", False)),
        "ema_stack_short": bool(features.get("ema_stack_short", False)),
        "sma20": _float_or_none(features.get("sma20")),
        "ema50": _float_or_none(features.get("ema50")),
        "session_vwap_dist_pct": _float_or_none(features.get("session_vwap_dist_pct")),
        "session_vwap": _float_or_none(features.get("session_vwap")),
        "session_open_hour": _int_or_none(features.get("session_open_hour")),
        "upper_wick_ratio": _float_or_none(features.get("upper_wick_ratio")),
        "lower_wick_ratio": _float_or_none(features.get("lower_wick_ratio")),
        "gap_pct": _float_or_none(features.get("gap_pct")),
        "consecutive_bull": _int_or_none(features.get("consecutive_bull")),
        "consecutive_bear": _int_or_none(features.get("consecutive_bear")),
        "prior_bar_same_color": _bool_or_none(features.get("prior_bar_same_color")),
        "atr_ratio_5_20": _float_or_none(features.get("atr_ratio_5_20")),
        "bb_width_rank_20": _float_or_none(features.get("bb_width_rank_20")),
        "bar_range_rank_20": _float_or_none(features.get("bar_range_rank_20")),
        "is_nr4": bool(features.get("is_nr4", False)),
        "is_nr14": bool(features.get("is_nr14", False)),
        "bb_at_20bar_low": bool(features.get("bb_at_20bar_low", False)),
        "bb_expanding": bool(features.get("bb_expanding", False)),
        "volume_ratio_20": _float_or_none(features.get("volume_ratio_20")),
        "close_location": _float_or_none(features.get("close_location")),
        "macd_proxy": _float_or_none(features.get("macd_proxy")),
        "macd_signal_proxy": _float_or_none(features.get("macd_signal_proxy")),
    }


def _bool_or_none(value: object) -> bool | None:
    if value is None or pd.isna(value):
        return None
    return bool(value)


def _int_or_none(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


def _float_or_none(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def _bars_to_hours(index: pd.DatetimeIndex, bars: int) -> float:
    if len(index) < 2:
        return float(bars)
    delta = index[1] - index[0]
    return float(delta.total_seconds() / 3600 * bars)
