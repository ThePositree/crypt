from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DISCOVERY_SCHEMA_VERSION = 1
TREND_STRENGTH_MIN_ATR = 0.5
AVOID_LOW_VOLUME_MEDIAN_RATIO = 0.5
BB_SQUEEZE_MAX_WIDTH_PCT = 0.04

_DISCOVERY_RAW_TRIGGERS = frozenset(
    {
        "h1_candle_confirm",
        "h1_momentum_burst",
        "h1_nr7_breakout",
        "h1_sweep_reversal",
        "h1_structure_break",
        "h1_order_block_retest",
    }
)

_UNSUPPORTED_TRIGGERS = frozenset(
    {
        "h1_pivot_reclaim",
        "h1_range_breakout",
        "h1_mean_revert_wick",
        "h1_ema_cross",
        "h1_rsi_reversal",
        "h1_bb_rejection",
        "h1_engulfing",
        "h1_inside_bar_breakout",
    }
)

_FILTER_PARAM_MAP: dict[str, dict[str, Any]] = {
    "side_short_only": {"allowed_sides": ["short"]},
    "side_long_only": {"allowed_sides": ["long"]},
    "block_context_reversal": {"block_d1_h4_context_reversal": True},
    "trend_strength_min": {"min_trend_strength_atr": TREND_STRENGTH_MIN_ATR},
    "avoid_low_volume": {"min_volume_median_ratio": AVOID_LOW_VOLUME_MEDIAN_RATIO},
    "h4_context_aligned": {"require_h4_context_aligned": True},
    "bb_squeeze": {"max_bb_width_pct": BB_SQUEEZE_MAX_WIDTH_PCT},
}

_UNSUPPORTED_FILTERS = frozenset(
    {
        "d1_context_aligned",
        "volatility_normal_only",
        "atr_distance_0_1",
        "atr_distance_1_2",
        "atr_distance_2_4",
        "atr_distance_4_plus",
        "anchor_pivot_only",
        "anchor_order_block_only",
        "anchor_no_liquidity_sweep",
        "anchor_age_max_24h",
        "anchor_age_max_72h",
        "avoid_after_large_move",
        "trend_ema_stack_aligned",
        "sma20_side_aligned",
        "rsi_side_aligned",
        "volatility_low_only",
        "volatility_high_only",
        "bb_wide",
        "body_to_range_min",
        "avoid_doji",
        "bar_range_min_atr",
        "session_london",
        "session_ny",
        "trend_strength_max",
        "volume_above_median",
        "roc_side_aligned",
    }
)

_DEFAULT_BACKTEST_ARGS: dict[str, Any] = {
    "ttl": 36,
    "rrr": 1.25,
    "risk_percent": 1.0,
    "risk_base_period": "monthly",
}


class DiscoveryConversionError(ValueError):
    """Raised when a discovery candidate cannot be converted safely."""


def convert_discovery_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a discovery-native strategy JSON into a donor crypt_ensemble config."""
    if payload.get("name") != "strategy_discovery_candidate":
        raise DiscoveryConversionError(
            "Expected discovery-native payload with name='strategy_discovery_candidate'"
        )
    params = payload.get("params")
    if not isinstance(params, dict):
        raise DiscoveryConversionError("Discovery payload missing params object")

    schema_version = params.get("discovery_schema_version")
    if schema_version != DISCOVERY_SCHEMA_VERSION:
        raise DiscoveryConversionError(f"Unsupported discovery_schema_version: {schema_version!r}")

    trigger = str(params.get("trigger", ""))
    if not trigger:
        raise DiscoveryConversionError("Discovery payload missing trigger")
    if trigger in _UNSUPPORTED_TRIGGERS:
        raise DiscoveryConversionError(
            f"Trigger {trigger!r} is not yet supported in donor crypt_ensemble conversion"
        )
    if trigger not in _DISCOVERY_RAW_TRIGGERS:
        raise DiscoveryConversionError(f"Unknown discovery trigger: {trigger!r}")

    raw_filters = params.get("filters", [])
    if not isinstance(raw_filters, list):
        raise DiscoveryConversionError("Discovery filters must be a list")
    filters = [str(item) for item in raw_filters]

    unsupported = sorted(set(filters).intersection(_UNSUPPORTED_FILTERS))
    if unsupported:
        joined = ", ".join(unsupported)
        raise DiscoveryConversionError(
            f"Discovery filters not yet supported in donor conversion: {joined}"
        )

    unknown = sorted(
        filter_name
        for filter_name in filters
        if filter_name not in _FILTER_PARAM_MAP and filter_name not in _UNSUPPORTED_FILTERS
    )
    if unknown:
        joined = ", ".join(unknown)
        raise DiscoveryConversionError(f"Unknown discovery filters: {joined}")

    donor_params: dict[str, Any] = {
        "setup_source": "h1_raw",
        "sl_atr_mult": 2.0,
        "sl_atr_buffer_mult": 0.1,
        "max_sl_distance_atr": 8.0,
        "allow_atr_sl_fallback": True,
        "optimized_windows": True,
        "progress": True,
        "timeframes": {
            "context": ["1d"],
            "setup": ["4h"],
            "trigger": "1h",
            "execution": "1h",
        },
        "trigger_rules": [trigger],
    }
    for filter_name in filters:
        donor_params.update(_FILTER_PARAM_MAP[filter_name])

    metrics = payload.get("metrics")
    candidate_id = _candidate_id(trigger, filters)
    version_suffix = candidate_id.replace("__", "-")

    converted: dict[str, Any] = {
        "name": "crypt_ensemble",
        "version": f"discovery-{version_suffix}",
        "params": donor_params,
        "backtest_args": dict(_DEFAULT_BACKTEST_ARGS),
        "discovery_source": {
            "candidate_id": candidate_id,
            "trigger": trigger,
            "filters": filters,
            "discovery_schema_version": DISCOVERY_SCHEMA_VERSION,
            "metrics": metrics if isinstance(metrics, dict) else None,
        },
    }
    return converted


def load_and_convert_discovery_strategy(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DiscoveryConversionError("Discovery strategy file must contain a JSON object")
    return convert_discovery_strategy(payload)


def _candidate_id(trigger: str, filters: list[str]) -> str:
    if not filters:
        return trigger
    return f"{trigger}__{'__'.join(filters)}"


def conversion_notes() -> str:
    return (
        "Discovery conversion uses setup_source=h1_raw so trigger events are evaluated on "
        "closed H1 candles without the H4 setup gate. block_context_reversal maps to "
        "block_d1_h4_context_reversal (D1/H4 SMA alignment), not the MTF "
        "block_context_reversal filter that blocks D1 SMC bias opposing the signal. "
        "Structural discovery triggers (sweep/structure/order-block) use simplified OHLCV "
        "rules in discovery but SMC-backed raw rules in donor execution; "
        "h1_candle_confirm, h1_momentum_burst, and h1_nr7_breakout are intended for "
        "faithful conversion when paired with mapped discovery filters."
    )
