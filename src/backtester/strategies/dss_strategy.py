"""DSSStrategy — registered backtester strategy that replays a DSS TrialConfig.

Used by ``compare-fixed``, ``walk-forward``, and ``optimize`` when the candidate
JSON references ``"name": "dss_strategy"``.

Params dict (from candidate JSON ``params`` key) must contain all fields of
TrialConfig: trigger_name, trigger_params, filter_names, filter_params,
plus downstream execution defaults such as rrr, risk_percent, and
position_ttl_minutes when present.
"""

from __future__ import annotations

import logging
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyInput
from backtester.strategy import BaseStrategy
from backtester.strategy_discovery.dss_config import (
    DSS_DEFAULT_DIRECTIONAL_SL_MOVE_PCT,
    TrialConfig,
)
from backtester.strategy_discovery.signal_composer import (
    ProgressCallback,
    SignalComposer,
    signal_df_to_ohlcv_aligned,
)

logger = logging.getLogger(__name__)

_ENTRY_SKIP_FEATURES = {"entry_dayofweek", "stop_distance_pct"}
_ENTRY_SKIP_OPS = {"<", "<=", ">", ">=", "==", "!="}


def apply_default_dss_execution_stops(
    aligned: pd.DataFrame,
    primary: pd.DataFrame,
    fallback_stop_pct: float,
    atr_sl_mult: float | None = None,
) -> None:
    """Make directional-only DSS signals executable by adding a default SL."""

    if aligned.empty:
        return

    signals = pd.to_numeric(aligned["signal"], errors="coerce").fillna(0).astype(int)
    stops = pd.to_numeric(aligned["sl_price"], errors="coerce")
    entry_basis = pd.to_numeric(primary["open"].shift(-1), errors="coerce")
    close_fallback = pd.to_numeric(primary["close"], errors="coerce")
    entry_basis = entry_basis.where(entry_basis > 0, close_fallback)

    actionable = signals != 0
    valid_entry = entry_basis.notna() & (entry_basis > 0)
    atr_entry_basis = close_fallback.where(close_fallback > 0, entry_basis)
    invalid_stop = stops.isna() | (stops <= 0)
    invalid_stop |= ((signals == 1) & (stops >= entry_basis)).fillna(False)
    invalid_stop |= ((signals == -1) & (stops <= entry_basis)).fillna(False)
    fallback_mask = actionable & valid_entry & invalid_stop
    if not bool(fallback_mask.any()):
        return

    long_mask = fallback_mask & (signals == 1)
    short_mask = fallback_mask & (signals == -1)
    if atr_sl_mult is not None and atr_sl_mult > 0:
        atr_distance = _closed_atr14(primary) * atr_sl_mult
        valid_atr = atr_distance.notna() & (atr_distance > 0)
        atr_long_mask = long_mask & valid_atr
        atr_short_mask = short_mask & valid_atr
        aligned.loc[atr_long_mask, "sl_price"] = (
            atr_entry_basis.loc[atr_long_mask] - atr_distance.loc[atr_long_mask]
        )
        aligned.loc[atr_short_mask, "sl_price"] = (
            atr_entry_basis.loc[atr_short_mask] + atr_distance.loc[atr_short_mask]
        )
        long_mask &= ~valid_atr
        short_mask &= ~valid_atr
    aligned.loc[long_mask, "sl_price"] = entry_basis.loc[long_mask] * (1.0 - fallback_stop_pct)
    aligned.loc[short_mask, "sl_price"] = entry_basis.loc[short_mask] * (1.0 + fallback_stop_pct)


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
    return true_range.shift(1).rolling(14, min_periods=1).mean()


class DSSStrategy(BaseStrategy):
    """Replay a DSS trial config as a donor-compatible strategy.

    The strategy generates signals using the parameterized trigger + filter
    stack from ``TrialConfig`` and converts them to the OHLCV-aligned format
    expected by ``ExecutionSim``.
    """

    signals_depend_on_execution_context = False

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
        self._fallback_stop_pct = float(
            params.get(
                "directional_sl_move_pct",
                params.get("sl_pct", DSS_DEFAULT_DIRECTIONAL_SL_MOVE_PCT),
            )
        )
        raw_atr_sl_mult = params.get("atr_sl_mult")
        self._atr_sl_mult = float(raw_atr_sl_mult) if raw_atr_sl_mult is not None else None
        if self._fallback_stop_pct <= 0:
            raise ValueError("directional_sl_move_pct/sl_pct must be positive")
        self._validate_entry_skip_rules()

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Attach owner-facing progress logging for long DSS signal generation."""

        self._composer.set_progress_callback(callback)

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        from backtester.data_contracts import StrategyData

        primary = (
            data.require_timeframe(self._config.trigger_instance.timeframe)
            if isinstance(data, StrategyData)
            else data
        )

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
        self._apply_default_execution_stops(aligned, primary)
        self._apply_entry_skip_rules(aligned, primary)
        return aligned

    def _apply_default_execution_stops(
        self, aligned: pd.DataFrame, primary: pd.DataFrame
    ) -> None:
        apply_default_dss_execution_stops(
            aligned,
            primary,
            self._fallback_stop_pct,
            atr_sl_mult=self._atr_sl_mult,
        )

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
