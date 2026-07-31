"""Parameterized filter factories for DSS.

Each factory takes ``FilterParams`` and returns a ``FilterFn``.
Every factory exposes a ``param_space()`` static function.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    FilterParams,
    FloatParam,
    IntParam,
    ParamDef,
)
from backtester.strategy_discovery.events import DiscoveryEvent, FilterResult
from backtester.strategy_discovery.features import DiscoveryDataset

FilterFn = Callable[[DiscoveryEvent, DiscoveryDataset], FilterResult]
FilterFactory = Callable[[FilterParams], FilterFn]


# ---------------------------------------------------------------------------
# Catalog registration
# ---------------------------------------------------------------------------


def parameterized_filter_catalog() -> dict[str, FilterFactory]:
    return cast(dict[str, FilterFactory], {
        "pf_atr_distance_band": pf_atr_distance_band_factory,
        "pf_body_to_range_min": pf_body_to_range_min_factory,
        "pf_trend_strength": pf_trend_strength_factory,
        "pf_rsi_zone": pf_rsi_zone_factory,
        "pf_volume_ratio": pf_volume_ratio_factory,
        "pf_bb_width": pf_bb_width_factory,
        "pf_vwap_proximity": pf_vwap_proximity_factory,
        "pf_context_aligned": pf_context_aligned_factory,
        "pf_session": pf_session_factory,
        "pf_anchor_age": pf_anchor_age_factory,
        "pf_avoid_large_move": pf_avoid_large_move_factory,
        "pf_trend_ema_stack": pf_trend_ema_stack_factory,
        "pf_bar_range_min": pf_bar_range_min_factory,
        "pf_no_liquidity_sweep": pf_no_liquidity_sweep_factory,
        "pf_side_long_only": pf_side_long_only_factory,
        "pf_side_short_only": pf_side_short_only_factory,
    })


def parameterized_filter_param_space() -> dict[str, dict[str, ParamDef]]:
    """Per-filter parameter spaces. Used to build DSSSearchSpace."""
    catalog: dict[str, dict[str, ParamDef]] = {}
    factories: dict[str, Any] = cast(dict[str, Any], parameterized_filter_catalog())
    for name, factory in factories.items():
        catalog[name] = factory.param_space()
    return catalog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(name: str, reason: str) -> FilterResult:
    return FilterResult(passed=True, filter_name=name, reason=reason, metadata={})


def _fail(name: str, reason: str) -> FilterResult:
    return FilterResult(passed=False, filter_name=name, reason=reason, metadata={})


def _safe_float(value: object) -> float | None:
    import pandas as pd

    if value is None:
        return None
    try:
        v = float(cast(Any, value))
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return None


def _clamp_float(value: object, low: float, high: float) -> float:
    coerced = float(cast(Any, value))
    return max(low, min(high, coerced))


def _clamp_int(value: object, low: int, high: int) -> int:
    coerced = int(cast(Any, value))
    return max(low, min(high, coerced))


# ---------------------------------------------------------------------------
# Factory implementations
# ---------------------------------------------------------------------------


class pf_atr_distance_band_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "low_mult": FloatParam(low=0.0, high=3.0),
            "high_mult": FloatParam(low=0.5, high=6.0),
        }

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        low_mult = _clamp_float(params.get("low_mult", 0.0), 0.0, 10.0)
        high_mult = _clamp_float(params.get("high_mult", 3.0), low_mult + 0.01, 20.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            atr = _safe_float(event.metadata.get("atr"))
            close = _safe_float(event.metadata.get("close"))
            anchor = _safe_float(event.metadata.get("anchor_price"))
            if atr is None or atr <= 0 or close is None:
                return _fail("pf_atr_distance_band", "missing_atr_or_price")
            dist = abs(close - anchor) / atr if anchor is not None else 0.0
            passed = low_mult <= dist <= high_mult
            reason = f"atr_dist={dist:.2f} in [{low_mult:.2f},{high_mult:.2f}]"
            return _ok("pf_atr_distance_band", reason) if passed else _fail("pf_atr_distance_band", reason)

        return _filter


class pf_body_to_range_min_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"ratio": FloatParam(low=0.05, high=0.7)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        ratio_min = _clamp_float(params.get("ratio", 0.3), 0.0, 1.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            btr = _safe_float(event.metadata.get("body_to_range"))
            if btr is None:
                return _fail("pf_body_to_range_min", "missing_body_to_range")
            passed = btr >= ratio_min
            reason = f"body_to_range={btr:.2f} >= {ratio_min:.2f}"
            return _ok("pf_body_to_range_min", reason) if passed else _fail("pf_body_to_range_min", reason)

        return _filter


class pf_trend_strength_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_atr": FloatParam(low=0.2, high=2.0)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_atr = _clamp_float(params.get("min_atr", 0.5), 0.0, 5.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            strength = _safe_float(event.metadata.get("trend_strength_atr"))
            if strength is None:
                return _fail("pf_trend_strength", "missing_trend_strength")
            passed = strength >= min_atr
            reason = f"trend_strength={strength:.2f} >= {min_atr:.2f}"
            return _ok("pf_trend_strength", reason) if passed else _fail("pf_trend_strength", reason)

        return _filter


class pf_rsi_zone_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "low": IntParam(low=20, high=60, step=5),
            "high": IntParam(low=40, high=80, step=5),
        }

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        low = _clamp_float(params.get("low", 30.0), 0.0, 100.0)
        high = _clamp_float(params.get("high", 70.0), low + 1.0, 100.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            rsi = _safe_float(event.metadata.get("rsi14"))
            if rsi is None:
                return _fail("pf_rsi_zone", "missing_rsi")
            passed = low <= rsi <= high
            reason = f"rsi={rsi:.1f} in [{low:.0f},{high:.0f}]"
            return _ok("pf_rsi_zone", reason) if passed else _fail("pf_rsi_zone", reason)

        return _filter


class pf_volume_ratio_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_ratio": FloatParam(low=0.5, high=3.0)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_ratio = _clamp_float(params.get("min_ratio", 1.0), 0.0, 10.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            volume = _safe_float(event.metadata.get("volume"))
            median = _safe_float(event.metadata.get("volume_median20"))
            if volume is None or median is None or median <= 0:
                return _fail("pf_volume_ratio", "missing_volume")
            ratio = volume / median
            passed = ratio >= min_ratio
            reason = f"vol_ratio={ratio:.2f} >= {min_ratio:.2f}"
            return _ok("pf_volume_ratio", reason) if passed else _fail("pf_volume_ratio", reason)

        return _filter


class pf_bb_width_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"max_width_pct": FloatParam(low=0.01, high=0.08)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        max_width = _clamp_float(params.get("max_width_pct", 0.04), 0.001, 0.5)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            width = _safe_float(event.metadata.get("bb_width_pct"))
            if width is None:
                return _fail("pf_bb_width", "missing_bb_width")
            passed = width <= max_width
            reason = f"bb_width={width:.4f} <= {max_width:.4f}"
            return _ok("pf_bb_width", reason) if passed else _fail("pf_bb_width", reason)

        return _filter


class pf_vwap_proximity_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"max_dist_pct": FloatParam(low=0.003, high=0.05)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        max_dist = _clamp_float(params.get("max_dist_pct", 0.01), 0.0, 0.5)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            dist = _safe_float(event.metadata.get("session_vwap_dist_pct"))
            if dist is None:
                return _fail("pf_vwap_proximity", "missing_vwap_dist")
            passed = abs(dist) <= max_dist
            reason = f"vwap_dist={abs(dist):.4f} <= {max_dist:.4f}"
            return _ok("pf_vwap_proximity", reason) if passed else _fail("pf_vwap_proximity", reason)

        return _filter


class pf_context_aligned_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"timeframe": CategoricalParam(choices=("h4", "d1"))}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        tf = str(params.get("timeframe", "h4"))

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            context_key = "d1_context" if tf == "d1" else "h4_context"
            ctx = str(event.metadata.get(context_key, "missing"))
            if ctx in {"missing", "neutral"}:
                return _ok("pf_context_aligned", "context_incomplete_skip")
            passed = ctx == event.side
            reason = f"{context_key}={ctx} vs side={event.side}"
            return _ok("pf_context_aligned", reason) if passed else _fail("pf_context_aligned", reason)

        return _filter


class pf_session_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"session": CategoricalParam(choices=("london", "ny", "asia"))}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        session = str(params.get("session", "london"))
        _SESSION_HOURS: dict[str, tuple[int, int]] = {
            "london": (7, 15),
            "ny": (13, 21),
            "asia": (0, 8),
        }
        start_h, end_h = _SESSION_HOURS.get(session, (7, 15))

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            hour = event.metadata.get("hour_utc")
            if hour is None:
                return _fail("pf_session", "missing_hour")
            passed = start_h <= int(hour) < end_h
            reason = f"hour={hour} in {session} [{start_h},{end_h})"
            return _ok("pf_session", reason) if passed else _fail("pf_session", reason)

        return _filter


class pf_anchor_age_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"max_hours": IntParam(low=4, high=120, step=4)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        max_hours = _clamp_float(params.get("max_hours", 48.0), 1.0, 10_000.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            anchor_age = _safe_float(event.metadata.get("anchor_age_hours"))
            if anchor_age is None:
                return _ok("pf_anchor_age", "no_anchor_age_skip")
            passed = anchor_age <= max_hours
            reason = f"anchor_age={anchor_age:.1f}h <= {max_hours:.0f}h"
            return _ok("pf_anchor_age", reason) if passed else _fail("pf_anchor_age", reason)

        return _filter


class pf_avoid_large_move_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"threshold_atr": FloatParam(low=1.5, high=5.0)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        threshold = _clamp_float(params.get("threshold_atr", 3.0), 0.1, 20.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            move = _safe_float(event.metadata.get("move_6_atr"))
            if move is None:
                return _fail("pf_avoid_large_move", "missing_move_6_atr")
            passed = move <= threshold
            reason = f"move_6_atr={move:.2f} <= {threshold:.2f}"
            return _ok("pf_avoid_large_move", reason) if passed else _fail("pf_avoid_large_move", reason)

        return _filter


class pf_trend_ema_stack_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "fast": IntParam(low=8, high=20, step=4),
            "mid": IntParam(low=20, high=50, step=5),
            "slow": IntParam(low=50, high=200, step=10),
        }

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            if event.side == "long":
                passed = bool(event.metadata.get("ema_stack_long", False))
            else:
                passed = bool(event.metadata.get("ema_stack_short", False))
            reason = "ema_stack_aligned" if passed else "ema_stack_misaligned"
            return _ok("pf_trend_ema_stack", reason) if passed else _fail("pf_trend_ema_stack", reason)

        return _filter


class pf_bar_range_min_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_atr_mult": FloatParam(low=0.2, high=1.5)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_mult = _clamp_float(params.get("min_atr_mult", 0.5), 0.0, 5.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            bar_range_atr = _safe_float(event.metadata.get("bar_range_atr"))
            if bar_range_atr is None:
                return _fail("pf_bar_range_min", "missing_bar_range_atr")
            passed = bar_range_atr >= min_mult
            reason = f"bar_range_atr={bar_range_atr:.2f} >= {min_mult:.2f}"
            return _ok("pf_bar_range_min", reason) if passed else _fail("pf_bar_range_min", reason)

        return _filter


class pf_no_liquidity_sweep_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            anchor_type = event.metadata.get("anchor_type")
            if anchor_type is None:
                return _ok("pf_no_liquidity_sweep", "no_anchor")
            passed = anchor_type != "liquidity_sweep"
            reason = "no_liquidity_sweep" if passed else "liquidity_sweep_blocked"
            return _ok("pf_no_liquidity_sweep", reason) if passed else _fail("pf_no_liquidity_sweep", reason)

        return _filter


class pf_side_long_only_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            passed = event.side == "long"
            return _ok("pf_side_long_only", "long") if passed else _fail("pf_side_long_only", "not_long")

        return _filter


class pf_side_short_only_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            passed = event.side == "short"
            return _ok("pf_side_short_only", "short") if passed else _fail("pf_side_short_only", "not_short")

        return _filter
