"""DSSStrategy — registered backtester strategy that replays a DSS TrialConfig.

Used by ``compare-fixed``, ``walk-forward``, and ``optimize`` when the candidate
JSON references ``"name": "dss_strategy"``.

Params dict (from candidate JSON ``params`` key) must contain all fields of
TrialConfig: trigger_name, trigger_params, filter_names, filter_params,
rrr, risk_percent, position_ttl_bars, atr_sl_mult.
"""

from __future__ import annotations

import logging
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyInput
from backtester.strategy import BaseStrategy
from backtester.strategy_discovery.dss_config import TrialConfig
from backtester.strategy_discovery.signal_composer import (
    SignalComposer,
    signal_df_to_ohlcv_aligned,
)

logger = logging.getLogger(__name__)

_ENTRY_SKIP_FEATURES = {"entry_dayofweek", "stop_distance_pct"}
_ENTRY_SKIP_OPS = {"<", "<=", ">", ">=", "==", "!="}


class DSSStrategy(BaseStrategy):
    """Replay a DSS trial config as a donor-compatible strategy.

    The strategy generates signals using the parameterized trigger + filter
    stack from ``TrialConfig`` and converts them to the OHLCV-aligned format
    expected by ``ExecutionSim``.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self._config = TrialConfig.from_dict(params)
        self._composer = SignalComposer()
        self._generate_fn = self._composer.build(self._config)
        raw_allowed_signal = params.get("allowed_signal")
        self._allowed_signal = int(raw_allowed_signal) if raw_allowed_signal is not None else None
        if self._allowed_signal not in (None, -1, 1):
            raise ValueError("allowed_signal must be -1, 1, or omitted")
        self._entry_skip_rules = list(params.get("entry_skip_rules") or [])
        self._validate_entry_skip_rules()

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        from backtester.data_contracts import StrategyData

        primary = data.primary if isinstance(data, StrategyData) else data

        try:
            signal_df = self._generate_fn(data)
        except Exception:
            logger.warning("DSSStrategy.generate() failed; returning zero signals", exc_info=True)
            return pd.DataFrame(
                {"signal": 0, "sl_price": 0.0},
                index=primary.index,
            )

        aligned = signal_df_to_ohlcv_aligned(signal_df, primary)
        if self._allowed_signal is not None:
            rejected = aligned["signal"] != self._allowed_signal
            aligned.loc[rejected, "signal"] = 0
            aligned.loc[rejected, "sl_price"] = 0.0
        self._apply_entry_skip_rules(aligned, primary)
        return aligned

    def _validate_entry_skip_rules(self) -> None:
        for rule in self._entry_skip_rules:
            conditions = rule.get("conditions")
            if not isinstance(conditions, list) or not conditions:
                raise ValueError("entry_skip_rules items must contain a non-empty conditions list")
            for condition in conditions:
                feature = condition.get("feature")
                op = condition.get("op")
                if feature not in _ENTRY_SKIP_FEATURES:
                    raise ValueError(f"unsupported entry skip feature: {feature}")
                if op not in _ENTRY_SKIP_OPS:
                    raise ValueError(f"unsupported entry skip op: {op}")
                if "value" not in condition:
                    raise ValueError("entry skip condition must contain value")

    def _apply_entry_skip_rules(self, aligned: pd.DataFrame, primary: pd.DataFrame) -> None:
        if not self._entry_skip_rules:
            return

        entry_open = primary["open"].shift(-1)
        entry_times = pd.Series(primary.index, index=primary.index).shift(-1)
        feature_values = {
            "entry_dayofweek": entry_times.dt.dayofweek.astype("float64"),
            "stop_distance_pct": (entry_open - aligned["sl_price"]).abs() / entry_open,
        }

        skip_mask = pd.Series(False, index=aligned.index)
        for rule in self._entry_skip_rules:
            rule_mask = aligned["signal"] != 0
            for condition in rule["conditions"]:
                values = feature_values[condition["feature"]]
                rule_mask &= self._compare_entry_feature(values, condition["op"], float(condition["value"]))
            skip_mask |= rule_mask.fillna(False)

        aligned.loc[skip_mask, "signal"] = 0
        aligned.loc[skip_mask, "sl_price"] = 0.0

    @staticmethod
    def _compare_entry_feature(values: pd.Series, op: str, threshold: float) -> pd.Series:
        if op == "<":
            return values < threshold
        if op == "<=":
            return values <= threshold
        if op == ">":
            return values > threshold
        if op == ">=":
            return values >= threshold
        if op == "==":
            return values == threshold
        if op == "!=":
            return values != threshold
        raise ValueError(f"unsupported entry skip op: {op}")

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:  # noqa: ARG002
        """DSS strategy parameters are fixed; no Optuna suggestions."""
        return {}
