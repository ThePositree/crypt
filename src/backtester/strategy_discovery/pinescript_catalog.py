"""PineScript-derived DSS trigger and filter catalog.

The module implements repo-native OHLCV primitives inspired by the PineScript
files under ``pinescript/``. It is intentionally separate from the legacy
parameterized catalog so DSS runs can search only this new space.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    FilterParams,
    FloatParam,
    IntParam,
    ParamDef,
    TriggerParams,
)
from backtester.strategy_discovery.events import DiscoveryEvent, FilterResult
from backtester.strategy_discovery.features import DiscoveryDataset
from backtester.strategy_discovery.parameterized_filters import (
    FilterFactory,
    FilterFn,
)
from backtester.strategy_discovery.parameterized_triggers import (
    TriggerFactory,
    TriggerFn,
)


def pinescript_trigger_catalog() -> dict[str, TriggerFactory]:
    return cast(dict[str, TriggerFactory], {
        "pt_ps_supertrend_flip": pt_ps_supertrend_flip_factory,
        "pt_ps_ut_trail_cross": pt_ps_ut_trail_cross_factory,
        "pt_ps_squeeze_release": pt_ps_squeeze_release_factory,
        "pt_ps_wavetrend_cross": pt_ps_wavetrend_cross_factory,
        "pt_ps_macd_signal_cross": pt_ps_macd_signal_cross_factory,
        "pt_ps_vixfix_reversal": pt_ps_vixfix_reversal_factory,
        "pt_ps_pivot_volume_break": pt_ps_pivot_volume_break_factory,
        "pt_ps_trendline_break": pt_ps_trendline_break_factory,
        "pt_ps_smc_structure_break": pt_ps_smc_structure_break_factory,
        "pt_ps_smc_fvg": pt_ps_smc_fvg_factory,
        "pt_ps_smc_equal_sweep": pt_ps_smc_equal_sweep_factory,
        "pt_ps_smc_premium_discount_reversal": pt_ps_smc_premium_discount_reversal_factory,
        "pt_ps_smc_order_block_retest": pt_ps_smc_order_block_retest_factory,
    })


def pinescript_filter_catalog() -> dict[str, FilterFactory]:
    return cast(dict[str, FilterFactory], {
        "pf_ps_supertrend_state": pf_ps_supertrend_state_factory,
        "pf_ps_adx_di_aligned": pf_ps_adx_di_aligned_factory,
        "pf_ps_macd_hist_state": pf_ps_macd_hist_state_factory,
        "pf_ps_squeeze_recent": pf_ps_squeeze_recent_factory,
        "pf_ps_wavetrend_zone": pf_ps_wavetrend_zone_factory,
        "pf_ps_vixfix_spike": pf_ps_vixfix_spike_factory,
        "pf_ps_killzone_session": pf_ps_killzone_session_factory,
        "pf_ps_pivot_volume": pf_ps_pivot_volume_factory,
        "pf_ps_trendline_slope": pf_ps_trendline_slope_factory,
        "pf_ps_smc_bias": pf_ps_smc_bias_factory,
        "pf_ps_smc_fvg_recent": pf_ps_smc_fvg_recent_factory,
        "pf_ps_smc_premium_discount": pf_ps_smc_premium_discount_factory,
        "pf_ps_smc_equal_level_recent": pf_ps_smc_equal_level_recent_factory,
        "pf_ps_smc_order_block_active": pf_ps_smc_order_block_active_factory,
    })


def pinescript_trigger_param_space() -> dict[str, dict[str, ParamDef]]:
    return {
        name: factory.param_space()  # type: ignore[attr-defined]
        for name, factory in pinescript_trigger_catalog().items()
    }


def pinescript_filter_param_space() -> dict[str, dict[str, ParamDef]]:
    return {
        name: factory.param_space()  # type: ignore[attr-defined]
        for name, factory in pinescript_filter_catalog().items()
    }


def _events_from_masks(
    dataset: DiscoveryDataset,
    trigger_name: str,
    long_mask: pd.Series,
    short_mask: pd.Series,
) -> list[DiscoveryEvent]:
    df = dataset.ohlcv
    events: list[DiscoveryEvent] = []
    for side, mask in (("long", long_mask), ("short", short_mask)):
        selected = mask.fillna(False)
        for event_time in df.index[selected]:
            metadata = {
                "atr": _safe_float(dataset.features.loc[event_time, "atr"]),
                "close": float(df.loc[event_time, "close"]),
                "hour_utc": int(event_time.hour),
                "volume": float(df.loc[event_time, "volume"]),
            }
            metadata.update(_feature_metadata(dataset, event_time))
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


def _feature_metadata(dataset: DiscoveryDataset, event_time: pd.Timestamp) -> dict[str, Any]:
    keys = (
        "ps_supertrend_dir",
        "ps_ut_trail",
        "ps_squeeze_on",
        "ps_squeeze_release",
        "ps_squeeze_momentum",
        "ps_squeeze_momentum_slope",
        "ps_wt1",
        "ps_wt2",
        "ps_macd",
        "ps_macd_signal",
        "ps_macd_hist",
        "ps_macd_hist_slope",
        "ps_adx",
        "ps_di_plus",
        "ps_di_minus",
        "ps_vixfix",
        "ps_vixfix_spike",
        "ps_pivot_high",
        "ps_pivot_low",
        "ps_volume_osc",
        "ps_trendline_upper",
        "ps_trendline_lower",
        "ps_trendline_upper_slope",
        "ps_trendline_lower_slope",
        "ps_killzone",
        "ps_smc_internal_bias",
        "ps_smc_swing_bias",
        "ps_smc_internal_bullish_bos",
        "ps_smc_internal_bearish_bos",
        "ps_smc_internal_bullish_choch",
        "ps_smc_internal_bearish_choch",
        "ps_smc_swing_bullish_bos",
        "ps_smc_swing_bearish_bos",
        "ps_smc_swing_bullish_choch",
        "ps_smc_swing_bearish_choch",
        "ps_smc_bullish_fvg",
        "ps_smc_bearish_fvg",
        "ps_smc_bullish_fvg_top",
        "ps_smc_bullish_fvg_bottom",
        "ps_smc_bearish_fvg_top",
        "ps_smc_bearish_fvg_bottom",
        "ps_smc_equal_high",
        "ps_smc_equal_low",
        "ps_smc_range_position",
        "ps_smc_zone",
        "ps_smc_bullish_ob_active",
        "ps_smc_bearish_ob_active",
        "ps_smc_bullish_ob_high",
        "ps_smc_bullish_ob_low",
        "ps_smc_bearish_ob_high",
        "ps_smc_bearish_ob_low",
        "ps_smc_bullish_ob_retest",
        "ps_smc_bearish_ob_retest",
    )
    row = dataset.features.loc[event_time]
    return {key: row.get(key, None) for key in keys}


def _ok(name: str, reason: str) -> FilterResult:
    return FilterResult(passed=True, filter_name=name, reason=reason, metadata={})


def _fail(name: str, reason: str) -> FilterResult:
    return FilterResult(passed=False, filter_name=name, reason=reason, metadata={})


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if pd.isna(result) else result


def _safe_bool(value: object) -> bool:
    return bool(value) if value is not None and not pd.isna(value) else False


def _clamp_float(value: object, low: float, high: float) -> float:
    return max(low, min(high, float(value)))  # type: ignore[arg-type]


def _clamp_int(value: object, low: int, high: int) -> int:
    try:
        parsed = int(cast(Any, value))
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def _crosses_above(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left > right) & (left.shift(1) <= right.shift(1))


def _crosses_below(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left < right) & (left.shift(1) >= right.shift(1))


class pt_ps_supertrend_flip_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            direction = dataset.features["ps_supertrend_dir"]
            long_mask = (direction == 1) & (direction.shift(1) == -1)
            short_mask = (direction == -1) & (direction.shift(1) == 1)
            return _events_from_masks(dataset, "pt_ps_supertrend_flip", long_mask, short_mask)

        return _trigger


class pt_ps_ut_trail_cross_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            close = dataset.ohlcv["close"]
            trail = dataset.features["ps_ut_trail"]
            long_mask = _crosses_above(close, trail)
            short_mask = _crosses_below(close, trail)
            return _events_from_masks(dataset, "pt_ps_ut_trail_cross", long_mask, short_mask)

        return _trigger


class pt_ps_squeeze_release_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_slope": FloatParam(low=0.0, high=1.5)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        min_slope = _clamp_float(params.get("min_slope", 0.0), 0.0, 10.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            release = dataset.features["ps_squeeze_release"].fillna(False)
            momentum = dataset.features["ps_squeeze_momentum"]
            slope = dataset.features["ps_squeeze_momentum_slope"]
            long_mask = release & (momentum > 0) & (slope >= min_slope)
            short_mask = release & (momentum < 0) & (slope <= -min_slope)
            return _events_from_masks(
                dataset,
                f"pt_ps_squeeze_release_s{min_slope:.2f}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_wavetrend_cross_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "oversold": IntParam(low=-80, high=-40, step=5),
            "overbought": IntParam(low=40, high=80, step=5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        oversold = _clamp_float(params.get("oversold", -60), -100.0, 0.0)
        overbought = _clamp_float(params.get("overbought", 60), 0.0, 100.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            wt1 = dataset.features["ps_wt1"]
            wt2 = dataset.features["ps_wt2"]
            long_mask = _crosses_above(wt1, wt2) & (wt1.shift(1) <= oversold)
            short_mask = _crosses_below(wt1, wt2) & (wt1.shift(1) >= overbought)
            return _events_from_masks(
                dataset,
                f"pt_ps_wavetrend_cross_os{oversold:.0f}_ob{overbought:.0f}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_macd_signal_cross_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"zero_filter": CategoricalParam(choices=("off", "with_zero", "against_zero"))}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        zero_filter = str(params.get("zero_filter", "off"))

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            macd = dataset.features["ps_macd"]
            signal = dataset.features["ps_macd_signal"]
            long_mask = _crosses_above(macd, signal)
            short_mask = _crosses_below(macd, signal)
            if zero_filter == "with_zero":
                long_mask &= macd > 0
                short_mask &= macd < 0
            elif zero_filter == "against_zero":
                long_mask &= macd < 0
                short_mask &= macd > 0
            return _events_from_masks(
                dataset,
                f"pt_ps_macd_signal_cross_{zero_filter}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_vixfix_reversal_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"confirm_bull": CategoricalParam(choices=("off", "on"))}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        confirm_bull = str(params.get("confirm_bull", "on")) == "on"

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            spike = dataset.features["ps_vixfix_spike"].fillna(False)
            long_mask = spike
            if confirm_bull:
                long_mask &= dataset.ohlcv["close"] > dataset.ohlcv["open"]
            short_mask = pd.Series(False, index=dataset.ohlcv.index)
            return _events_from_masks(dataset, "pt_ps_vixfix_reversal", long_mask, short_mask)

        return _trigger


class pt_ps_pivot_volume_break_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_volume_osc": FloatParam(low=0.0, high=40.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        min_volume_osc = _clamp_float(params.get("min_volume_osc", 10.0), -100.0, 200.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            close = dataset.ohlcv["close"]
            volume_ok = dataset.features["ps_volume_osc"] >= min_volume_osc
            long_mask = _crosses_above(close, dataset.features["ps_pivot_high"]) & volume_ok
            short_mask = _crosses_below(close, dataset.features["ps_pivot_low"]) & volume_ok
            return _events_from_masks(
                dataset,
                f"pt_ps_pivot_volume_break_v{min_volume_osc:.1f}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_trendline_break_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            close = dataset.ohlcv["close"]
            long_mask = _crosses_above(close, dataset.features["ps_trendline_upper"])
            short_mask = _crosses_below(close, dataset.features["ps_trendline_lower"])
            return _events_from_masks(dataset, "pt_ps_trendline_break", long_mask, short_mask)

        return _trigger


class pt_ps_smc_structure_break_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "structure": CategoricalParam(choices=("internal", "swing")),
            "event": CategoricalParam(choices=("all", "bos", "choch")),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        structure = str(params.get("structure", "internal"))
        if structure not in {"internal", "swing"}:
            structure = "internal"
        event = str(params.get("event", "all"))
        if event not in {"all", "bos", "choch"}:
            event = "all"

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            prefix = f"ps_smc_{structure}"
            long_mask = pd.Series(False, index=dataset.ohlcv.index)
            short_mask = pd.Series(False, index=dataset.ohlcv.index)
            if event in {"all", "bos"}:
                long_mask |= dataset.features[f"{prefix}_bullish_bos"].fillna(False)
                short_mask |= dataset.features[f"{prefix}_bearish_bos"].fillna(False)
            if event in {"all", "choch"}:
                long_mask |= dataset.features[f"{prefix}_bullish_choch"].fillna(False)
                short_mask |= dataset.features[f"{prefix}_bearish_choch"].fillna(False)
            return _events_from_masks(
                dataset,
                f"pt_ps_smc_structure_break_{structure}_{event}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_smc_fvg_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_gap_atr": FloatParam(low=0.0, high=1.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        min_gap_atr = _clamp_float(params.get("min_gap_atr", 0.0), 0.0, 10.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            atr = dataset.features["atr"].replace(0, pd.NA)
            bull_gap = (
                dataset.features["ps_smc_bullish_fvg_top"]
                - dataset.features["ps_smc_bullish_fvg_bottom"]
            ) / atr
            bear_gap = (
                dataset.features["ps_smc_bearish_fvg_top"]
                - dataset.features["ps_smc_bearish_fvg_bottom"]
            ) / atr
            long_mask = dataset.features["ps_smc_bullish_fvg"].fillna(False) & (
                bull_gap >= min_gap_atr
            )
            short_mask = dataset.features["ps_smc_bearish_fvg"].fillna(False) & (
                bear_gap >= min_gap_atr
            )
            return _events_from_masks(
                dataset,
                f"pt_ps_smc_fvg_gap{min_gap_atr:.2f}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_smc_equal_sweep_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"confirm_candle": CategoricalParam(choices=("off", "on"))}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        confirm_candle = str(params.get("confirm_candle", "on")) == "on"

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            long_mask = dataset.features["ps_smc_equal_low"].fillna(False)
            short_mask = dataset.features["ps_smc_equal_high"].fillna(False)
            if confirm_candle:
                long_mask &= dataset.ohlcv["close"] > dataset.ohlcv["open"]
                short_mask &= dataset.ohlcv["close"] < dataset.ohlcv["open"]
            return _events_from_masks(
                dataset,
                "pt_ps_smc_equal_sweep",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_smc_premium_discount_reversal_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"zone": CategoricalParam(choices=("strict", "include_equilibrium"))}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        include_equilibrium = str(params.get("zone", "strict")) == "include_equilibrium"

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            zone = dataset.features["ps_smc_zone"].astype("string")
            long_zone = zone == "discount"
            short_zone = zone == "premium"
            if include_equilibrium:
                long_zone |= zone == "equilibrium"
                short_zone |= zone == "equilibrium"
            long_mask = long_zone & (dataset.ohlcv["close"] > dataset.ohlcv["open"])
            short_mask = short_zone & (dataset.ohlcv["close"] < dataset.ohlcv["open"])
            return _events_from_masks(
                dataset,
                "pt_ps_smc_premium_discount_reversal",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_ps_smc_order_block_retest_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"require_bias": CategoricalParam(choices=("off", "internal", "swing"))}

    def __new__(cls, params: TriggerParams) -> TriggerFn:  # type: ignore[misc]
        require_bias = str(params.get("require_bias", "off"))
        if require_bias not in {"off", "internal", "swing"}:
            require_bias = "off"

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            long_mask = dataset.features["ps_smc_bullish_ob_retest"].fillna(False)
            short_mask = dataset.features["ps_smc_bearish_ob_retest"].fillna(False)
            if require_bias != "off":
                bias = dataset.features[f"ps_smc_{require_bias}_bias"]
                long_mask &= bias > 0
                short_mask &= bias < 0
            return _events_from_masks(
                dataset,
                f"pt_ps_smc_order_block_retest_{require_bias}",
                long_mask,
                short_mask,
            )

        return _trigger


class pf_ps_supertrend_state_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            direction = _safe_float(event.metadata.get("ps_supertrend_dir"))
            if direction is None:
                return _fail("pf_ps_supertrend_state", "missing_supertrend")
            passed = (event.side == "long" and direction > 0) or (
                event.side == "short" and direction < 0
            )
            reason = f"supertrend_dir={direction:.0f}"
            return _ok("pf_ps_supertrend_state", reason) if passed else _fail("pf_ps_supertrend_state", reason)

        return _filter


class pf_ps_adx_di_aligned_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_adx": FloatParam(low=10.0, high=40.0)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_adx = _clamp_float(params.get("min_adx", 20.0), 0.0, 100.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            adx = _safe_float(event.metadata.get("ps_adx"))
            di_plus = _safe_float(event.metadata.get("ps_di_plus"))
            di_minus = _safe_float(event.metadata.get("ps_di_minus"))
            if adx is None or di_plus is None or di_minus is None:
                return _fail("pf_ps_adx_di_aligned", "missing_adx_di")
            side_ok = di_plus > di_minus if event.side == "long" else di_minus > di_plus
            passed = adx >= min_adx and side_ok
            reason = f"adx={adx:.1f} di+={di_plus:.1f} di-={di_minus:.1f}"
            return _ok("pf_ps_adx_di_aligned", reason) if passed else _fail("pf_ps_adx_di_aligned", reason)

        return _filter


class pf_ps_macd_hist_state_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"require_slope": CategoricalParam(choices=("off", "on"))}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        require_slope = str(params.get("require_slope", "on")) == "on"

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            hist = _safe_float(event.metadata.get("ps_macd_hist"))
            slope = _safe_float(event.metadata.get("ps_macd_hist_slope"))
            if hist is None or slope is None:
                return _fail("pf_ps_macd_hist_state", "missing_macd_hist")
            if event.side == "long":
                passed = hist > 0 and (slope > 0 or not require_slope)
            else:
                passed = hist < 0 and (slope < 0 or not require_slope)
            reason = f"hist={hist:.4f} slope={slope:.4f}"
            return _ok("pf_ps_macd_hist_state", reason) if passed else _fail("pf_ps_macd_hist_state", reason)

        return _filter


class pf_ps_squeeze_recent_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"lookback": IntParam(low=3, high=24, step=3)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        lookback = _clamp_int(params.get("lookback", 12), 1, 72)

        def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
            if event.event_time not in dataset.features.index:
                return _fail("pf_ps_squeeze_recent", "event_missing")
            idx = dataset.features.index.get_loc(event.event_time)
            start = max(0, idx - lookback)
            recent = dataset.features["ps_squeeze_on"].iloc[start : idx + 1].fillna(False).any()
            return _ok("pf_ps_squeeze_recent", "recent_squeeze") if recent else _fail("pf_ps_squeeze_recent", "no_recent_squeeze")

        return _filter


class pf_ps_wavetrend_zone_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "oversold": IntParam(low=-80, high=-40, step=5),
            "overbought": IntParam(low=40, high=80, step=5),
        }

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        oversold = _clamp_float(params.get("oversold", -53), -100.0, 0.0)
        overbought = _clamp_float(params.get("overbought", 53), 0.0, 100.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            wt1 = _safe_float(event.metadata.get("ps_wt1"))
            if wt1 is None:
                return _fail("pf_ps_wavetrend_zone", "missing_wavetrend")
            passed = wt1 <= oversold if event.side == "long" else wt1 >= overbought
            reason = f"wt1={wt1:.1f}"
            return _ok("pf_ps_wavetrend_zone", reason) if passed else _fail("pf_ps_wavetrend_zone", reason)

        return _filter


class pf_ps_vixfix_spike_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            passed = _safe_bool(event.metadata.get("ps_vixfix_spike"))
            return _ok("pf_ps_vixfix_spike", "vixfix_spike") if passed else _fail("pf_ps_vixfix_spike", "no_vixfix_spike")

        return _filter


class pf_ps_killzone_session_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"session": CategoricalParam(choices=("asia", "london", "nyam", "nypm"))}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        session = str(params.get("session", "nyam"))

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            actual = str(event.metadata.get("ps_killzone", "other"))
            passed = actual == session
            reason = f"killzone={actual}"
            return _ok("pf_ps_killzone_session", reason) if passed else _fail("pf_ps_killzone_session", reason)

        return _filter


class pf_ps_pivot_volume_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_volume_osc": FloatParam(low=0.0, high=40.0)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_volume_osc = _clamp_float(params.get("min_volume_osc", 10.0), -100.0, 200.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            volume_osc = _safe_float(event.metadata.get("ps_volume_osc"))
            if volume_osc is None:
                return _fail("pf_ps_pivot_volume", "missing_volume_osc")
            passed = volume_osc >= min_volume_osc
            reason = f"volume_osc={volume_osc:.1f}"
            return _ok("pf_ps_pivot_volume", reason) if passed else _fail("pf_ps_pivot_volume", reason)

        return _filter


class pf_ps_trendline_slope_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"min_abs_slope": FloatParam(low=0.0, high=0.5)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        min_abs_slope = _clamp_float(params.get("min_abs_slope", 0.0), 0.0, 10.0)

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            key = "ps_trendline_upper_slope" if event.side == "long" else "ps_trendline_lower_slope"
            slope = _safe_float(event.metadata.get(key))
            if slope is None:
                return _fail("pf_ps_trendline_slope", "missing_trendline_slope")
            passed = abs(slope) >= min_abs_slope
            reason = f"slope={slope:.4f}"
            return _ok("pf_ps_trendline_slope", reason) if passed else _fail("pf_ps_trendline_slope", reason)

        return _filter


class pf_ps_smc_bias_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"structure": CategoricalParam(choices=("internal", "swing"))}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        structure = str(params.get("structure", "internal"))
        if structure not in {"internal", "swing"}:
            structure = "internal"

        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            bias = _safe_float(event.metadata.get(f"ps_smc_{structure}_bias"))
            if bias is None:
                return _fail("pf_ps_smc_bias", "missing_smc_bias")
            passed = (event.side == "long" and bias > 0) or (event.side == "short" and bias < 0)
            reason = f"{structure}_bias={bias:.0f}"
            return _ok("pf_ps_smc_bias", reason) if passed else _fail("pf_ps_smc_bias", reason)

        return _filter


class pf_ps_smc_fvg_recent_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"lookback": IntParam(low=3, high=24, step=3)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        lookback = _clamp_int(params.get("lookback", 12), 1, 72)

        def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
            if event.event_time not in dataset.features.index:
                return _fail("pf_ps_smc_fvg_recent", "event_missing")
            idx = dataset.features.index.get_loc(event.event_time)
            start = max(0, idx - lookback)
            key = "ps_smc_bullish_fvg" if event.side == "long" else "ps_smc_bearish_fvg"
            recent = dataset.features[key].iloc[start : idx + 1].fillna(False).any()
            reason = f"lookback={lookback}"
            return _ok("pf_ps_smc_fvg_recent", reason) if recent else _fail("pf_ps_smc_fvg_recent", "no_recent_fvg")

        return _filter


class pf_ps_smc_premium_discount_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            zone = str(event.metadata.get("ps_smc_zone", "unknown"))
            passed = zone == "discount" if event.side == "long" else zone == "premium"
            reason = f"zone={zone}"
            return _ok("pf_ps_smc_premium_discount", reason) if passed else _fail("pf_ps_smc_premium_discount", reason)

        return _filter


class pf_ps_smc_equal_level_recent_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"lookback": IntParam(low=3, high=24, step=3)}

    def __new__(cls, params: FilterParams) -> FilterFn:  # type: ignore[misc]
        lookback = _clamp_int(params.get("lookback", 12), 1, 72)

        def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
            if event.event_time not in dataset.features.index:
                return _fail("pf_ps_smc_equal_level_recent", "event_missing")
            idx = dataset.features.index.get_loc(event.event_time)
            start = max(0, idx - lookback)
            key = "ps_smc_equal_low" if event.side == "long" else "ps_smc_equal_high"
            recent = dataset.features[key].iloc[start : idx + 1].fillna(False).any()
            reason = f"lookback={lookback}"
            return _ok("pf_ps_smc_equal_level_recent", reason) if recent else _fail("pf_ps_smc_equal_level_recent", "no_recent_equal_level")

        return _filter


class pf_ps_smc_order_block_active_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {}

    def __new__(cls, _params: FilterParams) -> FilterFn:  # type: ignore[misc]
        def _filter(event: DiscoveryEvent, _dataset: DiscoveryDataset) -> FilterResult:
            key = "ps_smc_bullish_ob_active" if event.side == "long" else "ps_smc_bearish_ob_active"
            passed = _safe_bool(event.metadata.get(key))
            reason = "active_order_block" if passed else "no_active_order_block"
            return _ok("pf_ps_smc_order_block_active", reason) if passed else _fail("pf_ps_smc_order_block_active", reason)

        return _filter
