"""OHLCV catalog v3 expansion: candle patterns, session/VWAP, vol compression."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from backtester.strategy_discovery.events import DiscoveryEvent, FilterResult
from backtester.strategy_discovery.features import DiscoveryDataset

FilterFn = Callable[[DiscoveryEvent, DiscoveryDataset], FilterResult]


def expansion_trigger_catalog() -> dict[str, Callable[[DiscoveryDataset], list[DiscoveryEvent]]]:
    triggers: dict[str, Callable[[DiscoveryDataset], list[DiscoveryEvent]]] = {}
    triggers["h1_hammer"] = _h1_hammer
    triggers["h1_shooting_star"] = _h1_shooting_star
    triggers["h1_three_soldiers"] = _h1_three_soldiers
    triggers["h1_three_crows"] = _h1_three_crows
    triggers["h1_tweezer_bottom"] = _h1_tweezer_bottom
    triggers["h1_tweezer_top"] = _h1_tweezer_top
    triggers["h1_morning_star_proxy"] = _h1_morning_star_proxy
    triggers["h1_evening_star_proxy"] = _h1_evening_star_proxy
    triggers["h1_pin_bar_bull"] = _h1_pin_bar_bull
    triggers["h1_pin_bar_bear"] = _h1_pin_bar_bear
    triggers["h1_gap_up_continuation"] = _h1_gap_up_continuation
    triggers["h1_gap_down_continuation"] = _h1_gap_down_continuation
    triggers["h1_nr4_breakout"] = _h1_nr4_breakout
    triggers["h1_nr14_breakout"] = _h1_nr14_breakout
    triggers["h1_donchian_20_break"] = _h1_donchian_20_break
    triggers["h1_donchian_48_break"] = _h1_donchian_48_break
    triggers["h1_vwap_reclaim"] = _h1_vwap_reclaim
    triggers["h1_vwap_reject"] = _h1_vwap_reject
    triggers["h1_compression_breakout"] = _h1_compression_breakout
    triggers["h1_expansion_burst"] = _h1_expansion_burst
    triggers["h1_session_open_break"] = _h1_session_open_break
    triggers["h1_higher_high_higher_close"] = _h1_higher_high_higher_close
    triggers["h1_lower_low_lower_close"] = _h1_lower_low_lower_close
    triggers["h1_double_bottom_sweep"] = _h1_double_bottom_sweep
    triggers["h1_double_top_sweep"] = _h1_double_top_sweep
    triggers["h1_volume_spike_breakout"] = _h1_volume_spike_breakout
    triggers["h1_closing_range_high"] = _h1_closing_range_high
    triggers["h1_closing_range_low"] = _h1_closing_range_low
    triggers["h1_ema50_bounce"] = _h1_ema50_bounce
    triggers["h1_macd_proxy_cross"] = _h1_macd_proxy_cross
    return triggers


def expansion_filter_catalog() -> dict[str, FilterFn]:
    filters: dict[str, FilterFn] = {}

    def register(name: str, fn: FilterFn) -> None:
        filters[name] = fn

    register("session_asia", _session_hour_range(0, 7, "session_asia"))
    register("session_overlap", _session_hour_range(13, 15, "session_overlap"))
    register("session_off_hours", _session_off_hours)
    register("session_open_hour", _session_open_hour)

    register("vwap_side_aligned", _vwap_side_aligned)
    register("above_session_vwap", _above_session_vwap)
    register("below_session_vwap", _below_session_vwap)
    for threshold, label in ((0.002, "0_2pct"), (0.005, "0_5pct"), (0.01, "1pct")):
        register(
            f"vwap_dist_max_{label}",
            _metadata_max("session_vwap_dist_pct", threshold, f"vwap_dist_max_{label}"),
        )
        register(
            f"vwap_dist_min_{label}",
            _metadata_min("session_vwap_dist_pct", threshold, f"vwap_dist_min_{label}"),
        )

    register("vol_compression_active", _flag_true("bb_at_20bar_low", "vol_compression_active"))
    register("vol_expansion_active", _flag_true("bb_expanding", "vol_expansion_active"))
    register("compression_to_expansion", _compression_to_expansion)
    for threshold, label in ((0.7, "low"), (1.0, "mid"), (1.3, "high")):
        register(
            f"atr_ratio_5_20_{label}",
            _metadata_range("atr_ratio_5_20", _atr_ratio_bounds(threshold, label)),
        )
    for threshold, label in ((0.2, "low"), (0.5, "mid"), (0.8, "high")):
        register(
            f"bb_width_rank_max_{label}",
            _metadata_max("bb_width_rank_20", threshold, f"bb_width_rank_max_{label}"),
        )
        register(
            f"bb_width_rank_min_{label}",
            _metadata_min("bb_width_rank_20", threshold, f"bb_width_rank_min_{label}"),
        )

    register("consecutive_bull_2", _consecutive_min(2, "bull", "consecutive_bull_2"))
    register("consecutive_bull_3", _consecutive_min(3, "bull", "consecutive_bull_3"))
    register("consecutive_bear_2", _consecutive_min(2, "bear", "consecutive_bear_2"))
    register("consecutive_bear_3", _consecutive_min(3, "bear", "consecutive_bear_3"))
    register("prior_bar_same_color", _prior_bar_same_color)
    register("opposite_prior_bar", _opposite_prior_bar)

    for threshold, label in ((0.02, "2pct"), (0.03, "3pct"), (0.05, "5pct"), (0.06, "6pct")):
        register(
            f"bb_width_max_{label}",
            _metadata_max("bb_width_pct", threshold, f"bb_width_max_{label}"),
        )
    for threshold, label in ((0.08, "8pct"), (0.10, "10pct"), (0.12, "12pct")):
        register(
            f"bb_width_min_{label}",
            _metadata_min("bb_width_pct", threshold, f"bb_width_min_{label}"),
        )

    for low, high, label in ((0.0, 0.3, "0_3"), (0.3, 0.5, "3_5"), (0.5, 99.0, "5_plus")):
        register(
            f"trend_strength_band_{label}",
            _metadata_band("trend_strength_atr", low, high, f"trend_strength_band_{label}"),
        )

    for threshold, label in ((30.0, "30"), (35.0, "35"), (40.0, "40")):
        register(f"rsi_max_{label}", _metadata_max("rsi14", threshold, f"rsi_max_{label}"))
    for threshold, label in ((60.0, "60"), (65.0, "65"), (70.0, "70")):
        register(f"rsi_min_{label}", _metadata_min("rsi14", threshold, f"rsi_min_{label}"))

    register("lower_wick_dom", _wick_dom("lower", "lower_wick_dom"))
    register("upper_wick_dom", _wick_dom("upper", "upper_wick_dom"))
    register("wick_ratio_min_2", _wick_ratio_min(2.0, "wick_ratio_min_2"))

    register("no_gap", _gap_abs_max(0.001, "no_gap"))
    register("gap_up_min_0_3pct", _gap_min(0.003, "gap_up_min_0_3pct"))
    register("gap_down_min_0_3pct", _gap_max(-0.003, "gap_down_min_0_3pct"))

    register("volume_spike_1_5x", _volume_ratio_min(1.5, "volume_spike_1_5x"))
    register("volume_spike_2x", _volume_ratio_min(2.0, "volume_spike_2x"))
    register("volume_quiet_0_3x", _volume_ratio_max(0.3, "volume_quiet_0_3x"))
    register("volume_quiet_0_5x", _volume_ratio_max(0.5, "volume_quiet_0_5x"))

    register("roc_strong_pos", _metadata_min("roc10", 0.01, "roc_strong_pos"))
    register("roc_strong_neg", _metadata_max("roc10", -0.01, "roc_strong_neg"))

    register("nr4_active", _flag_true("is_nr4", "nr4_active"))
    register("nr14_active", _flag_true("is_nr14", "nr14_active"))
    register("bar_range_rank_low", _metadata_max("bar_range_rank_20", 0.2, "bar_range_rank_low"))
    register("bar_range_rank_high", _metadata_min("bar_range_rank_20", 0.8, "bar_range_rank_high"))

    register("close_near_high", _close_location_min(0.7, "close_near_high"))
    register("close_near_low", _close_location_max(0.3, "close_near_low"))
    register("ema50_side_aligned", _ema50_side_aligned)
    register("macd_proxy_aligned", _macd_proxy_aligned)

    return filters


def _atr_ratio_bounds(threshold: float, label: str) -> tuple[str, Callable[[float], bool]]:
    if label == "low":
        return (f"atr_ratio_5_20_{label}", lambda value: value <= threshold)
    if label == "mid":
        return (f"atr_ratio_5_20_{label}", lambda value: threshold < value <= 1.3)
    return (f"atr_ratio_5_20_{label}", lambda value: value > threshold)


def _masks(dataset: DiscoveryDataset) -> tuple[pd.DataFrame, pd.DataFrame]:
    return dataset.primary, dataset.features


def _emit(
    dataset: DiscoveryDataset,
    name: str,
    long_mask: pd.Series,
    short_mask: pd.Series,
    *,
    anchor_type: str | None = None,
    anchor_age_bars: int | None = None,
    anchor_price: pd.Series | None = None,
) -> list[DiscoveryEvent]:
    from backtester.strategy_discovery.triggers import _events_from_masks

    return _events_from_masks(
        dataset,
        name,
        long_mask,
        short_mask,
        anchor_type=anchor_type,
        anchor_age_bars=anchor_age_bars,
        anchor_price=anchor_price,
    )


def _h1_hammer(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _features = _masks(dataset)
    body = (df["close"] - df["open"]).abs()
    lower = df[["open", "close"]].min(axis=1) - df["low"]
    upper = df["high"] - df[["open", "close"]].max(axis=1)
    long_mask = (lower > body * 2) & (upper < body) & (df["close"] > df["open"])
    short_mask = (upper > body * 2) & (lower < body) & (df["close"] < df["open"])
    return _emit(dataset, "h1_hammer", long_mask, short_mask)


def _h1_shooting_star(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    body = (df["close"] - df["open"]).abs()
    upper = df["high"] - df[["open", "close"]].max(axis=1)
    lower = df[["open", "close"]].min(axis=1) - df["low"]
    short_mask = (upper > body * 2) & (lower < body * 0.5) & (df["close"] < df["open"])
    long_mask = (lower > body * 2) & (upper < body * 0.5) & (df["close"] > df["open"])
    return _emit(dataset, "h1_shooting_star", long_mask, short_mask)


def _h1_three_soldiers(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    bull = df["close"] > df["open"]
    long_mask = bull & bull.shift(1) & bull.shift(2) & (df["close"] > df["close"].shift(1))
    short_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_three_soldiers", long_mask, short_mask)


def _h1_three_crows(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    bear = df["close"] < df["open"]
    short_mask = bear & bear.shift(1) & bear.shift(2) & (df["close"] < df["close"].shift(1))
    long_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_three_crows", long_mask, short_mask)


def _h1_tweezer_bottom(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    tol = dataset.features["atr"] * 0.05
    long_mask = (df["low"] - df["low"].shift(1)).abs() <= tol
    short_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_tweezer_bottom", long_mask.fillna(False), short_mask)


def _h1_tweezer_top(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    tol = dataset.features["atr"] * 0.05
    short_mask = (df["high"] - df["high"].shift(1)).abs() <= tol
    long_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_tweezer_top", long_mask, short_mask.fillna(False))


def _h1_morning_star_proxy(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    bear1 = df["close"].shift(2) < df["open"].shift(2)
    small_body = features["body_to_range"].shift(1) <= 0.25
    bull3 = (df["close"] > df["open"]) & (df["close"] > df["close"].shift(1))
    long_mask = bear1 & small_body & bull3
    short_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_morning_star_proxy", long_mask.fillna(False), short_mask)


def _h1_evening_star_proxy(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    bull1 = df["close"].shift(2) > df["open"].shift(2)
    small_body = features["body_to_range"].shift(1) <= 0.25
    bear3 = (df["close"] < df["open"]) & (df["close"] < df["close"].shift(1))
    short_mask = bull1 & small_body & bear3
    long_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_evening_star_proxy", long_mask, short_mask.fillna(False))


def _h1_pin_bar_bull(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    long_mask = (features["lower_wick_ratio"] >= 2.0) & (df["close"] > df["open"])
    short_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_pin_bar_bull", long_mask.fillna(False), short_mask)


def _h1_pin_bar_bear(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    short_mask = (features["upper_wick_ratio"] >= 2.0) & (df["close"] < df["open"])
    long_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_pin_bar_bear", long_mask, short_mask.fillna(False))


def _h1_gap_up_continuation(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    long_mask = (features["gap_pct"] >= 0.003) & (df["close"] > df["open"])
    short_mask = (features["gap_pct"] <= -0.003) & (df["close"] < df["open"])
    return _emit(dataset, "h1_gap_up_continuation", long_mask.fillna(False), short_mask.fillna(False))


def _h1_gap_down_continuation(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    return _h1_gap_up_continuation(dataset)


def _h1_nr4_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    long_mask = features["is_nr4"].fillna(False) & (df["close"] > df["open"])
    short_mask = features["is_nr4"].fillna(False) & (df["close"] < df["open"])
    return _emit(dataset, "h1_nr4_breakout", long_mask, short_mask, anchor_type="range")


def _h1_nr14_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    long_mask = features["is_nr14"].fillna(False) & (df["close"] > df["open"])
    short_mask = features["is_nr14"].fillna(False) & (df["close"] < df["open"])
    return _emit(dataset, "h1_nr14_breakout", long_mask, short_mask, anchor_type="range")


def _h1_donchian_20_break(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    long_mask = df["close"] > features["donchian_high_20"]
    short_mask = df["close"] < features["donchian_low_20"]
    return _emit(dataset, "h1_donchian_20_break", long_mask.fillna(False), short_mask.fillna(False))


def _h1_donchian_48_break(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    high = df["high"].rolling(48, min_periods=24).max().shift(1)
    low = df["low"].rolling(48, min_periods=24).min().shift(1)
    long_mask = df["close"] > high
    short_mask = df["close"] < low
    return _emit(dataset, "h1_donchian_48_break", long_mask.fillna(False), short_mask.fillna(False))


def _h1_vwap_reclaim(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    dist = features["session_vwap_dist_pct"]
    long_mask = (dist.shift(1) < 0) & (dist >= 0) & (df["close"] > df["open"])
    short_mask = (dist.shift(1) > 0) & (dist <= 0) & (df["close"] < df["open"])
    return _emit(dataset, "h1_vwap_reclaim", long_mask.fillna(False), short_mask.fillna(False))


def _h1_vwap_reject(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    dist = features["session_vwap_dist_pct"]
    touched = (df["low"] <= features["session_vwap"]) & (df["high"] >= features["session_vwap"])
    long_mask = touched & (dist > 0) & (df["close"] < df["open"])
    short_mask = touched & (dist < 0) & (df["close"] > df["open"])
    return _emit(dataset, "h1_vwap_reject", long_mask.fillna(False), short_mask.fillna(False))


def _h1_compression_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    compressed = features["bb_at_20bar_low"].shift(1).astype("boolean").fillna(False)
    expanding = features["bb_expanding"].fillna(False)
    long_mask = compressed & expanding & (df["close"] > df["open"])
    short_mask = compressed & expanding & (df["close"] < df["open"])
    return _emit(dataset, "h1_compression_breakout", long_mask, short_mask)


def _h1_expansion_burst(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    burst = (features["atr_ratio_5_20"] >= 1.2) & features["bb_expanding"]
    long_mask = burst & (df["close"] > df["open"])
    short_mask = burst & (df["close"] < df["open"])
    return _emit(dataset, "h1_expansion_burst", long_mask.fillna(False), short_mask.fillna(False))


def _h1_session_open_break(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    session_open = features["hour_utc"] == features["session_open_hour"]
    day_high = df["high"].groupby(df.index.date).cummax().shift(1)
    day_low = df["low"].groupby(df.index.date).cummin().shift(1)
    long_mask = session_open & (df["close"] > day_high)
    short_mask = session_open & (df["close"] < day_low)
    return _emit(dataset, "h1_session_open_break", long_mask.fillna(False), short_mask.fillna(False))


def _h1_higher_high_higher_close(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    long_mask = (df["high"] > df["high"].shift(1)) & (df["close"] > df["close"].shift(1))
    short_mask = (df["low"] < df["low"].shift(1)) & (df["close"] < df["close"].shift(1))
    return _emit(dataset, "h1_higher_high_higher_close", long_mask.fillna(False), short_mask.fillna(False))


def _h1_lower_low_lower_close(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    return _h1_higher_high_higher_close(dataset)


def _h1_double_bottom_sweep(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    pivot = df["low"].rolling(10, min_periods=5).min().shift(1)
    swept = (df["low"] < pivot) & (df["close"] > pivot)
    long_mask = swept & (df["close"] > df["open"])
    short_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_double_bottom_sweep", long_mask.fillna(False), short_mask)


def _h1_double_top_sweep(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, _ = _masks(dataset)
    pivot = df["high"].rolling(10, min_periods=5).max().shift(1)
    swept = (df["high"] > pivot) & (df["close"] < pivot)
    short_mask = swept & (df["close"] < df["open"])
    long_mask = pd.Series(False, index=df.index)
    return _emit(dataset, "h1_double_top_sweep", long_mask, short_mask.fillna(False))


def _h1_volume_spike_breakout(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    spike = features["volume_ratio_20"] >= 1.5
    long_mask = spike & (df["close"] > df["high"].shift(1))
    short_mask = spike & (df["close"] < df["low"].shift(1))
    return _emit(dataset, "h1_volume_spike_breakout", long_mask.fillna(False), short_mask.fillna(False))


def _h1_closing_range_high(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    _df, features = _masks(dataset)
    long_mask = features["close_location"] >= 0.8
    short_mask = features["close_location"] <= 0.2
    return _emit(dataset, "h1_closing_range_high", long_mask.fillna(False), short_mask.fillna(False))


def _h1_closing_range_low(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    return _h1_closing_range_high(dataset)


def _h1_ema50_bounce(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    df, features = _masks(dataset)
    ema50 = features["ema50"]
    long_mask = (df["low"] <= ema50) & (df["close"] > ema50) & (df["close"] > df["open"])
    short_mask = (df["high"] >= ema50) & (df["close"] < ema50) & (df["close"] < df["open"])
    return _emit(dataset, "h1_ema50_bounce", long_mask.fillna(False), short_mask.fillna(False))


def _h1_macd_proxy_cross(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
    _df, features = _masks(dataset)
    macd = features["macd_proxy"]
    signal = features["macd_signal_proxy"]
    long_mask = (macd > signal) & (macd.shift(1) <= signal.shift(1))
    short_mask = (macd < signal) & (macd.shift(1) >= signal.shift(1))
    return _emit(dataset, "h1_macd_proxy_cross", long_mask.fillna(False), short_mask.fillna(False))


def _result(filter_name: str, passed: bool, reason: str) -> FilterResult:
    return FilterResult(passed=passed, filter_name=filter_name, reason=reason, metadata={})


def _float_metadata(event: DiscoveryEvent, key: str) -> float | None:
    value = event.metadata.get(key)
    if value is None or pd.isna(value):
        return None
    return float(value)


def _bool_metadata(event: DiscoveryEvent, key: str) -> bool | None:
    value = event.metadata.get(key)
    if value is None or pd.isna(value):
        return None
    return bool(value)


def _int_metadata(event: DiscoveryEvent, key: str) -> int | None:
    value = event.metadata.get(key)
    if value is None or pd.isna(value):
        return None
    return int(value)


def _session_hour_range(start: int, end: int, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        hour = _int_metadata(event, "hour_utc")
        if hour is None:
            return _result(name, False, "missing_hour_utc")
        passed = start <= hour < end
        return _result(name, passed, f"{name}_ok" if passed else f"outside_{name}")

    return _filter


def _session_off_hours(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    hour = _int_metadata(event, "hour_utc")
    if hour is None:
        return _result("session_off_hours", False, "missing_hour_utc")
    in_session = (7 <= hour < 15) or (13 <= hour < 21)
    return _result("session_off_hours", not in_session, "off_hours" if not in_session else "in_session")


def _session_open_hour(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    hour = _int_metadata(event, "hour_utc")
    open_hour = _int_metadata(event, "session_open_hour")
    if hour is None or open_hour is None:
        return _result("session_open_hour", False, "missing_session_hour")
    passed = hour == open_hour
    return _result("session_open_hour", passed, "session_open" if passed else "not_session_open")


def _vwap_side_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    dist = _float_metadata(event, "session_vwap_dist_pct")
    if dist is None:
        return _result("vwap_side_aligned", False, "missing_session_vwap_dist_pct")
    passed = dist >= 0 if event.side == "long" else dist <= 0
    return _result("vwap_side_aligned", passed, "vwap_aligned" if passed else "vwap_misaligned")


def _above_session_vwap(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    dist = _float_metadata(event, "session_vwap_dist_pct")
    if dist is None:
        return _result("above_session_vwap", False, "missing_session_vwap_dist_pct")
    passed = dist > 0
    return _result("above_session_vwap", passed, "above_vwap" if passed else "not_above_vwap")


def _below_session_vwap(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    dist = _float_metadata(event, "session_vwap_dist_pct")
    if dist is None:
        return _result("below_session_vwap", False, "missing_session_vwap_dist_pct")
    passed = dist < 0
    return _result("below_session_vwap", passed, "below_vwap" if passed else "not_below_vwap")


def _metadata_max(key: str, threshold: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _float_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        passed = value <= threshold
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _metadata_min(key: str, threshold: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _float_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        passed = value >= threshold
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _metadata_band(key: str, low: float, high: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _float_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        passed = low <= value < high
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _metadata_range(key: str, bounds: tuple[str, Callable[[float], bool]]) -> FilterFn:
    name, predicate = bounds

    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _float_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        passed = predicate(value)
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _flag_true(key: str, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _bool_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        return _result(name, value, f"{name}_ok" if value else f"{name}_inactive")

    return _filter


def _compression_to_expansion(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    compressed = _bool_metadata(event, "bb_at_20bar_low")
    expanding = _bool_metadata(event, "bb_expanding")
    if compressed is None or expanding is None:
        return _result("compression_to_expansion", False, "missing_compression_metadata")
    passed = compressed and expanding
    return _result(
        "compression_to_expansion",
        passed,
        "compression_to_expansion_ok" if passed else "compression_to_expansion_fail",
    )


def _consecutive_min(count: int, side: str, name: str) -> FilterFn:
    key = "consecutive_bull" if side == "bull" else "consecutive_bear"

    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        value = _int_metadata(event, key)
        if value is None:
            return _result(name, False, f"missing_{key}")
        passed = value >= count
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _prior_bar_same_color(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    same = _bool_metadata(event, "prior_bar_same_color")
    if same is None:
        return _result("prior_bar_same_color", False, "missing_prior_bar_same_color")
    return _result(
        "prior_bar_same_color",
        same,
        "same_color" if same else "different_color",
    )


def _opposite_prior_bar(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    same = _bool_metadata(event, "prior_bar_same_color")
    if same is None:
        return _result("opposite_prior_bar", False, "missing_prior_bar_same_color")
    passed = not same
    return _result("opposite_prior_bar", passed, "opposite_color" if passed else "same_color")


def _wick_dom(side: str, name: str) -> FilterFn:
    key = "lower_wick_ratio" if side == "lower" else "upper_wick_ratio"

    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        wick = _float_metadata(event, key)
        body = _float_metadata(event, "body_to_range")
        if wick is None or body is None:
            return _result(name, False, f"missing_{key}")
        passed = wick >= max(body, 0.15) * 2
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _wick_ratio_min(min_ratio: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        lower = _float_metadata(event, "lower_wick_ratio")
        upper = _float_metadata(event, "upper_wick_ratio")
        if lower is None or upper is None:
            return _result(name, False, "missing_wick_ratio")
        passed = max(lower, upper) >= min_ratio
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _gap_abs_max(max_abs: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        gap = _float_metadata(event, "gap_pct")
        if gap is None:
            return _result(name, False, "missing_gap_pct")
        passed = abs(gap) <= max_abs
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _gap_min(min_gap: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        gap = _float_metadata(event, "gap_pct")
        if gap is None:
            return _result(name, False, "missing_gap_pct")
        passed = gap >= min_gap
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _gap_max(max_gap: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        gap = _float_metadata(event, "gap_pct")
        if gap is None:
            return _result(name, False, "missing_gap_pct")
        passed = gap <= max_gap
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _volume_ratio_min(min_ratio: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        ratio = _float_metadata(event, "volume_ratio_20")
        if ratio is None:
            return _result(name, False, "missing_volume_ratio_20")
        passed = ratio >= min_ratio
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _volume_ratio_max(max_ratio: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        ratio = _float_metadata(event, "volume_ratio_20")
        if ratio is None:
            return _result(name, False, "missing_volume_ratio_20")
        passed = ratio <= max_ratio
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _close_location_min(threshold: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        loc = _float_metadata(event, "close_location")
        if loc is None:
            return _result(name, False, "missing_close_location")
        passed = loc >= threshold
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _close_location_max(threshold: float, name: str) -> FilterFn:
    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        del dataset
        loc = _float_metadata(event, "close_location")
        if loc is None:
            return _result(name, False, "missing_close_location")
        passed = loc <= threshold
        return _result(name, passed, f"{name}_ok" if passed else f"{name}_fail")

    return _filter


def _ema50_side_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    close = _float_metadata(event, "close")
    ema50 = _float_metadata(event, "ema50")
    if close is None or ema50 is None:
        return _result("ema50_side_aligned", False, "missing_ema50")
    passed = close > ema50 if event.side == "long" else close < ema50
    return _result("ema50_side_aligned", passed, "ema50_aligned" if passed else "ema50_misaligned")


def _macd_proxy_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    macd = _float_metadata(event, "macd_proxy")
    signal = _float_metadata(event, "macd_signal_proxy")
    if macd is None or signal is None:
        return _result("macd_proxy_aligned", False, "missing_macd_proxy")
    passed = macd > signal if event.side == "long" else macd < signal
    return _result("macd_proxy_aligned", passed, "macd_aligned" if passed else "macd_misaligned")
