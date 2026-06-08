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


def _result(filter_name: str, passed: bool, reason: str) -> FilterResult:
    return FilterResult(
        passed=passed,
        filter_name=filter_name,
        reason=reason,
        metadata={},
    )
