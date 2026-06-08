from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from backtester.strategy_discovery.events import DiscoveryEvent, FilterResult
from backtester.strategy_discovery.features import DiscoveryDataset

FilterFn = Callable[[DiscoveryEvent, DiscoveryDataset], FilterResult]


def filter_catalog() -> dict[str, FilterFn]:
    return {
        "side_long_only": _side_long_only,
        "side_short_only": _side_short_only,
        "d1_context_aligned": _d1_context_aligned,
        "h4_context_aligned": _h4_context_aligned,
        "block_context_reversal": _block_context_reversal,
        "volatility_normal_only": _volatility_normal_only,
        "trend_strength_min": _trend_strength_min,
        "atr_distance_0_1": _atr_distance_0_1,
        "atr_distance_1_2": _atr_distance_1_2,
        "atr_distance_2_4": _atr_distance_2_4,
        "atr_distance_4_plus": _atr_distance_4_plus,
        "anchor_pivot_only": _anchor_pivot_only,
        "anchor_order_block_only": _anchor_order_block_only,
        "anchor_no_liquidity_sweep": _anchor_no_liquidity_sweep,
        "anchor_age_max_24h": _anchor_age_max_24h,
        "anchor_age_max_72h": _anchor_age_max_72h,
        "avoid_after_large_move": _avoid_after_large_move,
        "avoid_low_volume": _avoid_low_volume,
        "trend_ema_stack_aligned": _trend_ema_stack_aligned,
        "sma20_side_aligned": _sma20_side_aligned,
        "rsi_side_aligned": _rsi_side_aligned,
        "volatility_low_only": _volatility_low_only,
        "volatility_high_only": _volatility_high_only,
        "bb_squeeze": _bb_squeeze,
        "bb_wide": _bb_wide,
        "body_to_range_min": _body_to_range_min,
        "avoid_doji": _avoid_doji,
        "bar_range_min_atr": _bar_range_min_atr,
        "session_london": _session_london,
        "session_ny": _session_ny,
        "trend_strength_max": _trend_strength_max,
        "volume_above_median": _volume_above_median,
        "roc_side_aligned": _roc_side_aligned,
    }


def _side_long_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _result(
        "side_long_only",
        event.side == "long",
        "side_long" if event.side == "long" else "side_not_long",
    )


def _side_short_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _result(
        "side_short_only",
        event.side == "short",
        "side_short" if event.side == "short" else "side_not_short",
    )


def _d1_context_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _context_result("d1_context_aligned", event, "d1_context")


def _h4_context_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _context_result("h4_context_aligned", event, "h4_context")


def _block_context_reversal(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    d1 = event.metadata.get("d1_context")
    h4 = event.metadata.get("h4_context")
    if d1 in {"missing", "neutral", None} or h4 in {"missing", "neutral", None}:
        return _result("block_context_reversal", True, "context_incomplete")
    passed = d1 == h4
    return _result(
        "block_context_reversal",
        passed,
        "context_not_reversed" if passed else "context_reversal",
    )


def _volatility_normal_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    rank = _float_metadata(event, "volatility_rank")
    if rank is None:
        return _result("volatility_normal_only", False, "missing_volatility_rank")
    passed = 0.2 <= rank <= 0.8
    return _result(
        "volatility_normal_only", passed, "normal_volatility" if passed else "abnormal_volatility"
    )


def _trend_strength_min(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    strength = _float_metadata(event, "trend_strength_atr")
    if strength is None:
        return _result("trend_strength_min", False, "missing_trend_strength")
    passed = strength >= 0.5
    return _result(
        "trend_strength_min", passed, "trend_strength_ok" if passed else "trend_strength_low"
    )


def _atr_distance_0_1(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    return _atr_distance_bucket(event, dataset, "atr_distance_0_1", lower=0.0, upper=1.0)


def _atr_distance_1_2(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    return _atr_distance_bucket(event, dataset, "atr_distance_1_2", lower=1.0, upper=2.0)


def _atr_distance_2_4(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    return _atr_distance_bucket(event, dataset, "atr_distance_2_4", lower=2.0, upper=4.0)


def _atr_distance_4_plus(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    distance = _float_metadata(event, "atr_distance")
    if distance is None:
        return _result("atr_distance_4_plus", False, "missing_anchor_metadata")
    passed = distance >= 4.0
    return _result(
        "atr_distance_4_plus",
        passed,
        "atr_distance_in_bucket" if passed else "atr_distance_out_of_bucket",
    )


def _anchor_pivot_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _anchor_type(event, "anchor_pivot_only", {"pivot"})


def _anchor_order_block_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    return _anchor_type(event, "anchor_order_block_only", {"order_block"})


def _anchor_no_liquidity_sweep(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    anchor_type = event.metadata.get("anchor_type")
    if anchor_type is None:
        return _result("anchor_no_liquidity_sweep", False, "missing_anchor_metadata")
    passed = anchor_type != "liquidity_sweep"
    return _result(
        "anchor_no_liquidity_sweep",
        passed,
        "anchor_allowed" if passed else "liquidity_sweep_anchor",
    )


def _anchor_age_max_24h(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    return _anchor_age_max(event, dataset, "anchor_age_max_24h", 24.0)


def _anchor_age_max_72h(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    return _anchor_age_max(event, dataset, "anchor_age_max_72h", 72.0)


def _avoid_after_large_move(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    move = _float_metadata(event, "move_6_atr")
    if move is None:
        return _result("avoid_after_large_move", False, "missing_move_6_atr")
    passed = move <= 2.0
    return _result("avoid_after_large_move", passed, "move_ok" if passed else "large_recent_move")


def _avoid_low_volume(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    volume = _float_metadata(event, "volume")
    median = _float_metadata(event, "volume_median20")
    if volume is None or median is None:
        return _result("avoid_low_volume", False, "missing_volume")
    passed = volume >= median * 0.5
    return _result("avoid_low_volume", passed, "volume_ok" if passed else "low_volume")


def _trend_ema_stack_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    if event.side == "long":
        passed = bool(event.metadata.get("ema_stack_long"))
        return _result(
            "trend_ema_stack_aligned",
            passed,
            "ema_stack_aligned" if passed else "ema_stack_misaligned",
        )
    passed = bool(event.metadata.get("ema_stack_short"))
    return _result(
        "trend_ema_stack_aligned",
        passed,
        "ema_stack_aligned" if passed else "ema_stack_misaligned",
    )


def _sma20_side_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    close = _float_metadata(event, "close")
    sma20 = _float_metadata(event, "sma20")
    if close is None or sma20 is None:
        return _result("sma20_side_aligned", False, "missing_sma20")
    passed = close > sma20 if event.side == "long" else close < sma20
    return _result(
        "sma20_side_aligned",
        passed,
        "sma20_aligned" if passed else "sma20_misaligned",
    )


def _rsi_side_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    rsi = _float_metadata(event, "rsi14")
    if rsi is None:
        return _result("rsi_side_aligned", False, "missing_rsi14")
    passed = 25.0 <= rsi <= 55.0 if event.side == "long" else 45.0 <= rsi <= 75.0
    return _result(
        "rsi_side_aligned",
        passed,
        "rsi_aligned" if passed else "rsi_misaligned",
    )


def _volatility_low_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    rank = _float_metadata(event, "volatility_rank")
    if rank is None:
        return _result("volatility_low_only", False, "missing_volatility_rank")
    passed = rank <= 0.2
    return _result(
        "volatility_low_only",
        passed,
        "low_volatility" if passed else "volatility_not_low",
    )


def _volatility_high_only(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    rank = _float_metadata(event, "volatility_rank")
    if rank is None:
        return _result("volatility_high_only", False, "missing_volatility_rank")
    passed = rank >= 0.8
    return _result(
        "volatility_high_only",
        passed,
        "high_volatility" if passed else "volatility_not_high",
    )


def _bb_squeeze(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    width = _float_metadata(event, "bb_width_pct")
    if width is None:
        return _result("bb_squeeze", False, "missing_bb_width_pct")
    passed = width <= 0.04
    return _result("bb_squeeze", passed, "bb_squeeze_ok" if passed else "bb_not_squeezed")


def _bb_wide(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    width = _float_metadata(event, "bb_width_pct")
    if width is None:
        return _result("bb_wide", False, "missing_bb_width_pct")
    passed = width >= 0.08
    return _result("bb_wide", passed, "bb_wide_ok" if passed else "bb_not_wide")


def _body_to_range_min(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    ratio = _float_metadata(event, "body_to_range")
    if ratio is None:
        return _result("body_to_range_min", False, "missing_body_to_range")
    passed = ratio >= 0.55
    return _result(
        "body_to_range_min",
        passed,
        "body_to_range_ok" if passed else "body_to_range_low",
    )


def _avoid_doji(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    ratio = _float_metadata(event, "body_to_range")
    if ratio is None:
        return _result("avoid_doji", False, "missing_body_to_range")
    passed = ratio >= 0.15
    return _result("avoid_doji", passed, "not_doji" if passed else "doji_like")


def _bar_range_min_atr(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    bar_range = _float_metadata(event, "bar_range_atr")
    if bar_range is None:
        return _result("bar_range_min_atr", False, "missing_bar_range_atr")
    passed = bar_range >= 0.35
    return _result(
        "bar_range_min_atr",
        passed,
        "bar_range_ok" if passed else "bar_range_too_small",
    )


def _session_london(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    hour = _int_metadata(event, "hour_utc")
    if hour is None:
        return _result("session_london", False, "missing_hour_utc")
    passed = 7 <= hour < 15
    return _result("session_london", passed, "london_session" if passed else "outside_london")


def _session_ny(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    hour = _int_metadata(event, "hour_utc")
    if hour is None:
        return _result("session_ny", False, "missing_hour_utc")
    passed = 13 <= hour < 21
    return _result("session_ny", passed, "ny_session" if passed else "outside_ny")


def _trend_strength_max(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    strength = _float_metadata(event, "trend_strength_atr")
    if strength is None:
        return _result("trend_strength_max", False, "missing_trend_strength")
    passed = strength <= 1.5
    return _result(
        "trend_strength_max",
        passed,
        "trend_strength_ok" if passed else "trend_strength_high",
    )


def _volume_above_median(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    volume = _float_metadata(event, "volume")
    median = _float_metadata(event, "volume_median20")
    if volume is None or median is None:
        return _result("volume_above_median", False, "missing_volume")
    passed = volume >= median
    return _result(
        "volume_above_median",
        passed,
        "volume_above_median" if passed else "volume_below_median",
    )


def _roc_side_aligned(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
    del dataset
    roc = _float_metadata(event, "roc10")
    if roc is None:
        return _result("roc_side_aligned", False, "missing_roc10")
    passed = roc > 0.0 if event.side == "long" else roc < 0.0
    return _result(
        "roc_side_aligned",
        passed,
        "roc_aligned" if passed else "roc_misaligned",
    )


def _context_result(filter_name: str, event: DiscoveryEvent, key: str) -> FilterResult:
    context = event.metadata.get(key)
    if context in {None, "missing", "neutral"}:
        return _result(filter_name, False, f"missing_{key}")
    passed = context == event.side
    return _result(filter_name, passed, "context_aligned" if passed else "context_misaligned")


def _atr_distance_bucket(
    event: DiscoveryEvent,
    dataset: DiscoveryDataset,
    filter_name: str,
    *,
    lower: float,
    upper: float,
) -> FilterResult:
    del dataset
    distance = _float_metadata(event, "atr_distance")
    if distance is None:
        return _result(filter_name, False, "missing_anchor_metadata")
    passed = lower <= distance < upper
    return _result(
        filter_name, passed, "atr_distance_in_bucket" if passed else "atr_distance_out_of_bucket"
    )


def _anchor_type(event: DiscoveryEvent, filter_name: str, allowed: set[str]) -> FilterResult:
    anchor_type = event.metadata.get("anchor_type")
    if anchor_type is None:
        return _result(filter_name, False, "missing_anchor_metadata")
    passed = str(anchor_type) in allowed
    return _result(filter_name, passed, "anchor_type_allowed" if passed else "anchor_type_blocked")


def _anchor_age_max(
    event: DiscoveryEvent,
    dataset: DiscoveryDataset,
    filter_name: str,
    max_hours: float,
) -> FilterResult:
    del dataset
    age = _float_metadata(event, "anchor_age_hours")
    if age is None:
        return _result(filter_name, False, "missing_anchor_metadata")
    passed = age <= max_hours
    return _result(filter_name, passed, "anchor_age_ok" if passed else "anchor_too_old")


def _float_metadata(event: DiscoveryEvent, key: str) -> float | None:
    value = event.metadata.get(key)
    if value is None or pd.isna(value):
        return None
    return float(value)


def _int_metadata(event: DiscoveryEvent, key: str) -> int | None:
    value = event.metadata.get(key)
    if value is None or pd.isna(value):
        return None
    return int(value)


def _result(filter_name: str, passed: bool, reason: str) -> FilterResult:
    return FilterResult(
        passed=passed,
        filter_name=filter_name,
        reason=reason,
        metadata={},
    )
