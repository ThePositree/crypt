"""Incremental adapter for discovery-native crypt_ensemble configurations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.incremental_strategy import (
    IncrementalStrategyConfig,
    register_incremental_adapter,
)
from backtester.strategies.crypt_ensemble import CryptEnsembleStrategy
from backtester.strategy_discovery.features import DiscoveryDataset


class CryptEnsembleIncrementalAdapter:
    """Evaluate supported raw-H1 crypt configs from shared causal features."""

    def prepare_replay(
        self,
        *,
        data: StrategyInput,
        dataset: DiscoveryDataset,  # noqa: ARG002
        config: IncrementalStrategyConfig,
    ) -> pd.DataFrame:
        primary = data.require_timeframe("H1") if isinstance(data, StrategyData) else data
        frame = CryptEnsembleStrategy(config.params).generate(data)
        if len(frame) != len(primary):
            raise ValueError("canonical crypt_ensemble output length changed during replay")
        output = frame.copy()
        output.index = primary.index
        return output


def _signal_frame(
    *,
    primary: pd.DataFrame,
    dataset: DiscoveryDataset,
    params: dict[str, Any],
) -> pd.DataFrame:
    rules = tuple(str(rule) for rule in params.get("trigger_rules", ()))
    if len(rules) != 1:
        raise ValueError("Incremental crypt_ensemble adapter requires one raw-H1 trigger")
    trigger = _TRIGGERS.get(rules[0])
    if trigger is None:
        raise ValueError(f"Unsupported incremental crypt_ensemble trigger: {rules[0]!r}")
    signal = trigger(primary, dataset.features)
    signal = _apply_filters(
        signal=signal,
        primary=primary,
        features=dataset.features,
        params=params,
    )
    atr = _closed_atr14(primary)
    close = primary["close"].astype(float)
    stop = pd.Series(0.0, index=primary.index)
    stop.loc[signal == 1] = close.loc[signal == 1] - atr.loc[signal == 1]
    stop.loc[signal == -1] = close.loc[signal == -1] + atr.loc[signal == -1]
    invalid_atr = ~np.isfinite(atr) | atr.le(0)
    stop.loc[(signal == 1) & invalid_atr] = close.loc[(signal == 1) & invalid_atr] * 0.999
    stop.loc[(signal == -1) & invalid_atr] = close.loc[(signal == -1) & invalid_atr] * 1.001

    output = primary.copy()
    output["signal"] = signal.astype(int)
    output["sl_price"] = stop.astype(float)
    output["entry_price"] = float("nan")
    return output


def _direction(primary: pd.DataFrame) -> pd.Series:
    direction = pd.Series(0, index=primary.index, dtype="int64")
    direction.loc[primary["close"] > primary["open"]] = 1
    direction.loc[primary["close"] < primary["open"]] = -1
    return direction


def _nr4(primary: pd.DataFrame, features: pd.DataFrame) -> pd.Series:
    return _direction(primary).where(features["is_nr4"].fillna(False), 0)


def _nr7(primary: pd.DataFrame, features: pd.DataFrame) -> pd.Series:  # noqa: ARG001
    bar_range = primary["high"] - primary["low"]
    is_nr7 = bar_range <= bar_range.rolling(7, min_periods=7).min()
    return _direction(primary).where(is_nr7.fillna(False), 0)


def _vwap_reclaim(
    primary: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.Series:
    direction = _direction(primary)
    current = pd.to_numeric(
        features["session_vwap_dist_pct"],
        errors="coerce",
    )
    previous = current.shift(1)
    output = pd.Series(0, index=primary.index, dtype="int64")
    output.loc[(direction == 1) & previous.lt(0) & current.ge(0)] = 1
    output.loc[(direction == -1) & previous.gt(0) & current.le(0)] = -1
    return output


_TRIGGERS = {
    "h1_nr4_breakout": _nr4,
    "h1_nr7_breakout": _nr7,
    "h1_vwap_reclaim": _vwap_reclaim,
}


def _apply_filters(
    *,
    signal: pd.Series,
    primary: pd.DataFrame,
    features: pd.DataFrame,
    params: dict[str, Any],
) -> pd.Series:
    keep = signal.ne(0)
    side = signal.map({1: "long", -1: "short"})
    if params.get("require_h4_context_aligned", False):
        keep &= features["h4_context"].astype(str).eq(side)
    if "max_bb_width_pct" in params:
        keep &= pd.to_numeric(
            features["bb_width_pct"],
            errors="coerce",
        ).le(float(params["max_bb_width_pct"]))
    if "min_body_to_range" in params:
        keep &= pd.to_numeric(
            features["body_to_range"],
            errors="coerce",
        ).ge(float(params["min_body_to_range"]))
    if "min_volume_median_ratio" in params:
        median = pd.to_numeric(
            features["volume_median20"],
            errors="coerce",
        )
        keep &= primary["volume"].ge(median * float(params["min_volume_median_ratio"]))
    if "min_bb_width_rank_20" in params:
        keep &= pd.to_numeric(
            features["bb_width_rank_20"],
            errors="coerce",
        ).ge(float(params["min_bb_width_rank_20"]))
    if params.get("require_session_off_hours", False):
        hour = pd.Series(primary.index.hour, index=primary.index)
        keep &= ~(((hour >= 7) & (hour < 15)) | ((hour >= 13) & (hour < 21)))
    if "max_session_vwap_dist_pct" in params:
        keep &= pd.to_numeric(
            features["session_vwap_dist_pct"],
            errors="coerce",
        ).le(float(params["max_session_vwap_dist_pct"]))
    if "min_session_vwap_dist_pct" in params:
        keep &= pd.to_numeric(
            features["session_vwap_dist_pct"],
            errors="coerce",
        ).ge(float(params["min_session_vwap_dist_pct"]))
    return signal.where(keep, 0).astype("int64")


def _closed_atr14(primary: pd.DataFrame) -> pd.Series:
    high = primary["high"].astype(float)
    low = primary["low"].astype(float)
    close = primary["close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(14, min_periods=1).mean()


register_incremental_adapter(
    "crypt_ensemble",
    CryptEnsembleIncrementalAdapter,
)
