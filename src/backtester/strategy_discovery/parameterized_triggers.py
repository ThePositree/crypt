"""Parameterized trigger factories for DSS.

Each factory takes a ``TriggerParams`` dict and returns a ``TriggerFn``.
Every factory exposes a ``param_space()`` static function returning the
declared search bounds.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from backtester.strategy_discovery.dss_config import (
    FloatParam,
    IntParam,
    ParamDef,
    TriggerParams,
)
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import DiscoveryDataset

TriggerFn = Callable[[DiscoveryDataset], list[DiscoveryEvent]]
TriggerFactory = Callable[[TriggerParams], TriggerFn]


# ---------------------------------------------------------------------------
# Catalog registration
# ---------------------------------------------------------------------------


def parameterized_trigger_catalog() -> dict[str, TriggerFactory]:
    return {
        "pt_sweep_reversal": pt_sweep_reversal_factory,
        "pt_structure_break": pt_structure_break_factory,
        "pt_range_breakout": pt_range_breakout_factory,
        "pt_momentum_burst": pt_momentum_burst_factory,
        "pt_mean_revert_wick": pt_mean_revert_wick_factory,
        "pt_ema_cross": pt_ema_cross_factory,
        "pt_rsi_reversal": pt_rsi_reversal_factory,
        "pt_bb_rejection": pt_bb_rejection_factory,
        "pt_engulfing": pt_engulfing_factory,
        "pt_nr4_breakout": pt_nr4_breakout_factory,
        "pt_nr14_breakout": pt_nr14_breakout_factory,
        "pt_vwap_reclaim": pt_vwap_reclaim_factory,
        "pt_compression_breakout": pt_compression_breakout_factory,
        "pt_pivot_reclaim": pt_pivot_reclaim_factory,
        "pt_volume_spike": pt_volume_spike_factory,
        "pt_hammer": pt_hammer_factory,
        "pt_pin_bar": pt_pin_bar_factory,
        "pt_candle_confirm": pt_candle_confirm_factory,
        "pt_order_block_retest": pt_order_block_retest_factory,
        "pt_double_bottom_sweep": pt_double_bottom_sweep_factory,
    }


def parameterized_trigger_param_space() -> dict[str, dict[str, ParamDef]]:
    """Per-trigger parameter spaces. Used to build DSSSearchSpace."""
    catalog: dict[str, dict[str, ParamDef]] = {}
    factories: dict[str, Any] = {
        "pt_sweep_reversal": pt_sweep_reversal_factory,
        "pt_structure_break": pt_structure_break_factory,
        "pt_range_breakout": pt_range_breakout_factory,
        "pt_momentum_burst": pt_momentum_burst_factory,
        "pt_mean_revert_wick": pt_mean_revert_wick_factory,
        "pt_ema_cross": pt_ema_cross_factory,
        "pt_rsi_reversal": pt_rsi_reversal_factory,
        "pt_bb_rejection": pt_bb_rejection_factory,
        "pt_engulfing": pt_engulfing_factory,
        "pt_nr4_breakout": pt_nr4_breakout_factory,
        "pt_nr14_breakout": pt_nr14_breakout_factory,
        "pt_vwap_reclaim": pt_vwap_reclaim_factory,
        "pt_compression_breakout": pt_compression_breakout_factory,
        "pt_pivot_reclaim": pt_pivot_reclaim_factory,
        "pt_volume_spike": pt_volume_spike_factory,
        "pt_hammer": pt_hammer_factory,
        "pt_pin_bar": pt_pin_bar_factory,
        "pt_candle_confirm": pt_candle_confirm_factory,
        "pt_order_block_retest": pt_order_block_retest_factory,
        "pt_double_bottom_sweep": pt_double_bottom_sweep_factory,
    }
    for name, factory in factories.items():
        catalog[name] = factory.param_space()  # type: ignore[attr-defined]
    return catalog


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _events_from_masks(
    dataset: DiscoveryDataset,
    trigger_name: str,
    long_mask: pd.Series,
    short_mask: pd.Series,
) -> list[DiscoveryEvent]:
    df = dataset.primary
    events: list[DiscoveryEvent] = []
    for side, mask in (("long", long_mask), ("short", short_mask)):
        selected = mask.fillna(False)
        for event_time in df.index[selected]:
            atr_val = dataset.features.loc[event_time, "atr"]
            events.append(
                DiscoveryEvent(
                    event_time=pd.Timestamp(event_time),
                    side=side,  # type: ignore[arg-type]
                    trigger_name=trigger_name,
                    entry_reference_price=float(df.loc[event_time, "close"]),
                    window_label=dataset.window_label,
                    symbol=dataset.symbol,
                    metadata={
                        "atr": float(atr_val) if pd.notna(atr_val) else None,
                        "close": float(df.loc[event_time, "close"]),
                        "hour_utc": int(event_time.hour),
                        "session_vwap_dist_pct": _safe_float(
                            dataset.features.loc[event_time, "session_vwap_dist_pct"]
                        ),
                        "body_to_range": _safe_float(
                            dataset.features.loc[event_time, "body_to_range"]
                        ),
                        "rsi14": _safe_float(dataset.features.loc[event_time, "rsi14"]),
                        "volume": float(df.loc[event_time, "volume"]),
                        "volume_median20": _safe_float(
                            dataset.features.loc[event_time, "volume_median20"]
                        ),
                        "trend_strength_atr": _safe_float(
                            dataset.features.loc[event_time, "trend_strength_atr"]
                        ),
                        "bb_width_pct": _safe_float(
                            dataset.features.loc[event_time, "bb_width_pct"]
                        ),
                        "bb_width_rank_20": _safe_float(
                            dataset.features.loc[event_time, "bb_width_rank_20"]
                        ),
                        "volatility_rank": _safe_float(
                            dataset.features.loc[event_time, "volatility_rank"]
                        ),
                        "ema_stack_long": bool(dataset.features.loc[event_time, "ema_stack_long"]),
                        "ema_stack_short": bool(
                            dataset.features.loc[event_time, "ema_stack_short"]
                        ),
                        "d1_context": str(dataset.features.loc[event_time, "d1_context"]),
                        "h4_context": str(dataset.features.loc[event_time, "h4_context"]),
                        "move_6_atr": _safe_float(
                            dataset.features.loc[event_time, "move_6_atr"]
                        ),
                        "bar_range_atr": _safe_float(
                            dataset.features.loc[event_time, "bar_range_atr"]
                        ),
                    },
                )
            )
    events.sort(key=lambda e: (e.event_time, e.side))
    return events


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)  # type: ignore[arg-type]
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return None


def _clamp_int(value: object, low: int, high: int) -> int:
    return max(low, min(high, int(value)))  # type: ignore[arg-type]


def _clamp_float(value: object, low: float, high: float) -> float:
    return max(low, min(high, float(value)))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Factory implementations
# ---------------------------------------------------------------------------


class pt_sweep_reversal_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"window": IntParam(low=6, high=24, step=2)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 12), 4, 48)
        min_p = max(3, window // 2)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            prior_low = df["low"].rolling(window, min_periods=min_p).min().shift(1)
            prior_high = df["high"].rolling(window, min_periods=min_p).max().shift(1)
            long_mask = (df["low"] < prior_low) & (df["close"] > df["open"])
            short_mask = (df["high"] > prior_high) & (df["close"] < df["open"])
            return _events_from_masks(dataset, f"pt_sweep_reversal_w{window}", long_mask, short_mask)

        return _trigger


class pt_structure_break_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"window": IntParam(low=8, high=40, step=4)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 20), 4, 80)
        min_p = max(4, window // 2)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            prior_high = df["high"].rolling(window, min_periods=min_p).max().shift(1)
            prior_low = df["low"].rolling(window, min_periods=min_p).min().shift(1)
            long_mask = df["close"] > prior_high
            short_mask = df["close"] < prior_low
            return _events_from_masks(dataset, f"pt_structure_break_w{window}", long_mask, short_mask)

        return _trigger


class pt_range_breakout_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"window": IntParam(low=8, high=48, step=4)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 24), 4, 96)
        min_p = max(4, window // 2)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            range_high = df["high"].rolling(window, min_periods=min_p).max().shift(1)
            range_low = df["low"].rolling(window, min_periods=min_p).min().shift(1)
            long_mask = df["close"] > range_high
            short_mask = df["close"] < range_low
            return _events_from_masks(dataset, f"pt_range_breakout_w{window}", long_mask, short_mask)

        return _trigger


class pt_momentum_burst_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"threshold": FloatParam(low=1.0, high=4.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        threshold = _clamp_float(params.get("threshold", 1.5), 0.3, 8.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            std = dataset.features["return_std20"]
            ret = dataset.features["return_1"]
            long_mask = (ret > std * threshold) & (df["close"] > df["open"])
            short_mask = (ret < -std * threshold) & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_momentum_burst_t{threshold:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_mean_revert_wick_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "window": IntParam(low=4, high=24, step=2),
            "threshold": FloatParam(low=0.3, high=2.0),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        threshold = _clamp_float(params.get("threshold", 2.0), 0.1, 5.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            body = (df["close"] - df["open"]).abs()
            lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
            upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
            long_mask = (lower_wick > body * threshold) & (df["close"] > df["open"])
            short_mask = (upper_wick > body * threshold) & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_mean_revert_wick_t{threshold:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_ema_cross_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "fast": IntParam(low=4, high=20, step=2),
            "slow": IntParam(low=20, high=100, step=5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        fast = _clamp_int(params.get("fast", 9), 2, 50)
        slow = _clamp_int(params.get("slow", 21), fast + 2, 200)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            ema_fast = df["close"].ewm(span=fast, adjust=False).mean().shift(1)
            ema_slow = df["close"].ewm(span=slow, adjust=False).mean().shift(1)
            long_mask = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
            short_mask = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))
            return _events_from_masks(
                dataset, f"pt_ema_cross_{fast}_{slow}", long_mask, short_mask
            )

        return _trigger


class pt_rsi_reversal_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "period": IntParam(low=7, high=21, step=2),
            "oversold": IntParam(low=20, high=40, step=5),
            "overbought": IntParam(low=60, high=80, step=5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        period = _clamp_int(params.get("period", 14), 4, 50)
        oversold = _clamp_int(params.get("oversold", 35), 10, 45)
        overbought = _clamp_int(params.get("overbought", 65), 55, 90)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
            loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
            rs = gain / loss.replace(0, pd.NA)
            rsi_raw = 100 - 100 / (1 + rs)
            rsi_raw = rsi_raw.where(loss > 0, 100.0)
            rsi_raw = rsi_raw.where((gain > 0) | (loss > 0), 50.0)
            rsi = rsi_raw.shift(1)
            prev_rsi = rsi.shift(1)
            long_mask = (rsi < oversold) & (df["close"] > df["open"]) & (rsi > prev_rsi)
            short_mask = (rsi > overbought) & (df["close"] < df["open"]) & (rsi < prev_rsi)
            return _events_from_masks(
                dataset,
                f"pt_rsi_reversal_p{period}_os{oversold}_ob{overbought}",
                long_mask,
                short_mask,
            )

        return _trigger


class pt_bb_rejection_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "period": IntParam(low=14, high=28, step=2),
            "std": FloatParam(low=1.5, high=2.5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        period = _clamp_int(params.get("period", 20), 5, 60)
        std_mult = _clamp_float(params.get("std", 2.0), 0.5, 4.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            mid = df["close"].rolling(period, min_periods=period).mean().shift(1)
            bb_std = df["close"].rolling(period, min_periods=period).std().shift(1)
            bb_lower = mid - std_mult * bb_std
            bb_upper = mid + std_mult * bb_std
            long_mask = (df["low"] <= bb_lower) & (df["close"] > df["open"])
            short_mask = (df["high"] >= bb_upper) & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_bb_rejection_p{period}_s{std_mult:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_engulfing_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"body_ratio": FloatParam(low=0.6, high=1.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        body_ratio = _clamp_float(params.get("body_ratio", 0.8), 0.0, 2.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            prev_open = df["open"].shift(1)
            prev_close = df["close"].shift(1)
            prev_body = (prev_close - prev_open).abs()
            curr_body = (df["close"] - df["open"]).abs()
            prev_bear = prev_close < prev_open
            prev_bull = prev_close > prev_open
            long_mask = (
                prev_bear
                & (df["close"] > df["open"])
                & (df["open"] <= prev_close)
                & (df["close"] >= prev_open)
                & (curr_body >= prev_body * body_ratio)
            )
            short_mask = (
                prev_bull
                & (df["close"] < df["open"])
                & (df["open"] >= prev_close)
                & (df["close"] <= prev_open)
                & (curr_body >= prev_body * body_ratio)
            )
            return _events_from_masks(
                dataset, f"pt_engulfing_br{body_ratio:.2f}", long_mask, short_mask
            )

        return _trigger


class pt_nr4_breakout_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"lookback": IntParam(low=3, high=8, step=1)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        lookback = _clamp_int(params.get("lookback", 4), 2, 20)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            bar_range = df["high"] - df["low"]
            is_nr = bar_range <= bar_range.rolling(lookback, min_periods=lookback).min().shift(1)
            long_mask = is_nr & (df["close"] > df["open"])
            short_mask = is_nr & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_nr{lookback}_breakout", long_mask, short_mask
            )

        return _trigger


class pt_nr14_breakout_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"lookback": IntParam(low=8, high=20, step=2)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        lookback = _clamp_int(params.get("lookback", 14), 4, 40)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            bar_range = df["high"] - df["low"]
            is_nr = bar_range <= bar_range.rolling(lookback, min_periods=lookback).min().shift(1)
            long_mask = is_nr & (df["close"] > df["open"])
            short_mask = is_nr & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_nr{lookback}_breakout", long_mask, short_mask
            )

        return _trigger


class pt_vwap_reclaim_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"tolerance": FloatParam(low=0.001, high=0.02)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        tolerance = _clamp_float(params.get("tolerance", 0.005), 0.0, 0.1)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            vwap = dataset.features["session_vwap"]
            dist_pct = (df["close"] - vwap).abs() / df["close"].replace(0, pd.NA)
            near_vwap = dist_pct <= tolerance
            long_mask = near_vwap & (df["close"] > df["open"]) & (df["close"] > vwap)
            short_mask = near_vwap & (df["close"] < df["open"]) & (df["close"] < vwap)
            return _events_from_masks(
                dataset, f"pt_vwap_reclaim_t{tolerance:.4f}", long_mask, short_mask
            )

        return _trigger


class pt_compression_breakout_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "window": IntParam(low=8, high=24, step=2),
            "threshold": FloatParam(low=0.3, high=1.5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 12), 4, 48)
        threshold = _clamp_float(params.get("threshold", 0.6), 0.1, 3.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            bar_range = df["high"] - df["low"]
            atr = dataset.features["atr"]
            atr_ratio = bar_range / atr.replace(0, pd.NA)
            compressed = atr_ratio.rolling(window, min_periods=window // 2).mean().shift(1) <= threshold
            long_mask = compressed & (df["close"] > df["open"])
            short_mask = compressed & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_compression_breakout_w{window}_t{threshold:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_pivot_reclaim_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"window": IntParam(low=12, high=48, step=4)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 20), 4, 100)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            prior_low = df["low"].rolling(window, min_periods=window // 2).min().shift(1)
            prior_high = df["high"].rolling(window, min_periods=window // 2).max().shift(1)
            long_mask = (df["low"] <= prior_low) & (df["close"] > df["close"].shift(1))
            short_mask = (df["high"] >= prior_high) & (df["close"] < df["close"].shift(1))
            return _events_from_masks(
                dataset, f"pt_pivot_reclaim_w{window}", long_mask, short_mask
            )

        return _trigger


class pt_volume_spike_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"mult": FloatParam(low=1.5, high=5.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        mult = _clamp_float(params.get("mult", 2.0), 0.5, 10.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            vol_median = dataset.features["volume_median20"]
            vol_spike = df["volume"] >= vol_median * mult
            long_mask = vol_spike & (df["close"] > df["open"])
            short_mask = vol_spike & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_volume_spike_m{mult:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_hammer_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "shadow_ratio": FloatParam(low=1.5, high=4.0),
            "body_ratio": FloatParam(low=0.05, high=0.3),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        shadow_ratio = _clamp_float(params.get("shadow_ratio", 2.0), 0.5, 8.0)
        body_ratio_max = _clamp_float(params.get("body_ratio", 0.3), 0.01, 0.8)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            body = (df["close"] - df["open"]).abs()
            bar_range = df["high"] - df["low"]
            lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
            body_pct = body / bar_range.replace(0, pd.NA)
            hammer_mask = (
                (lower_wick >= body * shadow_ratio)
                & (body_pct <= body_ratio_max)
            )
            long_mask = hammer_mask
            short_mask = pd.Series(False, index=df.index)
            return _events_from_masks(
                dataset, f"pt_hammer_sr{shadow_ratio:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_pin_bar_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"shadow_ratio": FloatParam(low=2.0, high=5.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        shadow_ratio = _clamp_float(params.get("shadow_ratio", 3.0), 0.5, 10.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            body = (df["close"] - df["open"]).abs()
            lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
            upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
            long_mask = lower_wick >= body * shadow_ratio
            short_mask = upper_wick >= body * shadow_ratio
            return _events_from_masks(
                dataset, f"pt_pin_bar_sr{shadow_ratio:.1f}", long_mask, short_mask
            )

        return _trigger


class pt_candle_confirm_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"body_ratio": FloatParam(low=0.1, high=0.8)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        body_ratio_min = _clamp_float(params.get("body_ratio", 0.3), 0.0, 1.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            body = (df["close"] - df["open"]).abs()
            bar_range = df["high"] - df["low"]
            body_pct = body / bar_range.replace(0, pd.NA)
            strong_body = body_pct >= body_ratio_min
            long_mask = strong_body & (df["close"] > df["open"])
            short_mask = strong_body & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_candle_confirm_br{body_ratio_min:.2f}", long_mask, short_mask
            )

        return _trigger


class pt_order_block_retest_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {"tolerance": FloatParam(low=0.3, high=1.0)}

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        tolerance_atr = _clamp_float(params.get("tolerance", 0.5), 0.0, 3.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            atr = dataset.features["atr"]
            previous_bearish = df["close"].shift(1) < df["open"].shift(1)
            previous_bullish = df["close"].shift(1) > df["open"].shift(1)
            previous_mid = (df["open"].shift(1) + df["close"].shift(1)) / 2
            dist_to_mid = (df["close"] - previous_mid).abs()
            within_tol = dist_to_mid <= atr * tolerance_atr
            long_mask = previous_bearish & within_tol & (df["close"] > previous_mid)
            short_mask = previous_bullish & within_tol & (df["close"] < previous_mid)
            return _events_from_masks(
                dataset, f"pt_ob_retest_t{tolerance_atr:.2f}", long_mask, short_mask
            )

        return _trigger


class pt_double_bottom_sweep_factory:
    @staticmethod
    def param_space() -> dict[str, ParamDef]:
        return {
            "window": IntParam(low=4, high=16, step=2),
            "tolerance": FloatParam(low=0.1, high=0.5),
        }

    def __new__(cls, params: TriggerParams) -> TriggerFn:
        window = _clamp_int(params.get("window", 8), 2, 40)
        tolerance_atr = _clamp_float(params.get("tolerance", 0.2), 0.0, 2.0)

        def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
            df = dataset.primary
            atr = dataset.features["atr"]
            prior_low = df["low"].rolling(window, min_periods=window // 2).min().shift(1)
            prior_high = df["high"].rolling(window, min_periods=window // 2).max().shift(1)
            near_prior_low = (df["low"] - prior_low).abs() <= atr * tolerance_atr
            near_prior_high = (df["high"] - prior_high).abs() <= atr * tolerance_atr
            long_mask = near_prior_low & (df["close"] > df["open"])
            short_mask = near_prior_high & (df["close"] < df["open"])
            return _events_from_masks(
                dataset, f"pt_double_bottom_sweep_w{window}_t{tolerance_atr:.2f}", long_mask, short_mask
            )

        return _trigger
