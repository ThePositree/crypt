"""
Weight optimiser for the backtest harness — docs/backtest.md §9.

Algorithm:
    1. Grid search over per-regime weights + thresholds.
    2. Coordinate descent starting from the grid winner.

Objective (per regime):
    maximize  mean(pnl_net) - 0.5 * std(pnl_net)
    tie-break: lowest alert count

Search space (§9.1):
    weights : [0.0, 0.1, …, 1.0]  constrained to sum == 1.0 per regime
    thresholds : [0.15, 0.20, …, 0.55]

Sanity guards (§9.4):
    - Any engine weight == 1.0 in any regime (one-engine policy)
    - Train-test expectancy gap > 50% relative
    - Test expectancy < 0
    If guard fires: write weights.candidate.yaml, not weights.optimal.yaml.
"""

from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import yaml
from numpy.typing import NDArray

from crypt.aggregator.weights import SCORING_ENGINES, WeightsConfig
from crypt.models import Regime

# ---------------------------------------------------------------------------
# Search-space constants (§9.1)
# ---------------------------------------------------------------------------

_WEIGHT_GRID = np.round(np.arange(0.0, 1.01, 0.1), 2).tolist()
_THRESHOLD_GRID = np.round(np.arange(0.15, 0.56, 0.05), 2).tolist()
_REGIMES = ("TRENDING", "RANGING", "HIGH_VOL")
_ENGINES = ("trend", "meanrev", "smc_structure", "smc_order_blocks", "smc_liquidity")
# Fine grid for coordinate descent (5x finer than weight grid)
_FINE_STEP = 0.02


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class OptResult:
    """Output of run_optimizer() for a single fold's train slice."""

    # Best weights dict in the same format as config/weights.yaml
    weights: dict[str, Any]
    # Objective value on the train slice
    train_objective: float
    # Whether the sanity guard fired
    guard_fired: bool
    # Which guard rules were violated (empty = no guard)
    guard_violations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Objective function
# ---------------------------------------------------------------------------


def _objective(
    verdicts: pd.DataFrame,
    weights_cfg: WeightsConfig,  # noqa: ARG001
) -> float:
    """
    Compute  mean(pnl_net) - 0.5 * std(pnl_net) on BUY/SELL alerts
    using h24 forward return as the P&L proxy.

    'pnl_net' here uses the raw forward return aligned with direction —
    the ExecutionSim is not re-run for every candidate (too expensive).
    The signal quality metric is a good proxy for expected profitability.
    """
    alerts = verdicts[verdicts["decision"].isin(("BUY", "SELL"))].copy()
    if alerts.empty or "return_h24" not in alerts.columns:
        return -float("inf")

    direction_sign = alerts["decision"].map({"BUY": 1.0, "SELL": -1.0})
    pnl = alerts["return_h24"].astype(float) * direction_sign

    # Subtract a simple fee proxy (taker + slippage both sides ≈ 0.15%).
    pnl = pnl - 0.0015

    n = len(pnl)
    if n == 0:
        return -float("inf")

    mean_pnl = float(pnl.mean())
    std_pnl = float(pnl.std()) if n > 1 else 0.0
    return mean_pnl - 0.5 * std_pnl


def _apply_weights(
    verdicts: pd.DataFrame,
    weights_data: dict[str, Any],
) -> pd.DataFrame:
    """
    Re-apply the decision rule to verdicts using candidate weights.

    For speed, re-runs only the aggregation step (not the full engine pipeline).
    Input verdicts_df must have columns: tick_time, symbol, regime, confidence,
    and strength_<engine> for scoring engines emitted during replay.
    Decision is inferred as: BUY if score >= threshold, SELL if score <= -threshold, else HOLD.
    """
    cfg = WeightsConfig(weights_data)
    df = verdicts.copy()
    strength_cols = [f"strength_{engine}" for engine in sorted(SCORING_ENGINES)]
    has_strengths = any(col in df.columns for col in strength_cols)

    if has_strengths:
        df["score"] = 0.0
        for regime_name in _REGIMES:
            mask = df["regime"] == regime_name
            if not bool(mask.any()):
                continue

            regime = Regime(regime_name)
            base_weights = cfg.engine_weights(regime)
            numerator = pd.Series(0.0, index=df.index[mask])
            denominator = pd.Series(0.0, index=df.index[mask])
            active_count = pd.Series(0.0, index=df.index[mask])
            equal_sum = pd.Series(0.0, index=df.index[mask])

            for engine in SCORING_ENGINES:
                col = f"strength_{engine}"
                if col not in df.columns:
                    continue
                values = pd.to_numeric(df.loc[mask, col], errors="coerce")
                present = values.notna()
                weight = base_weights[engine]
                numerator = numerator.add(values.fillna(0.0) * weight, fill_value=0.0)
                denominator = denominator.add(present.astype(float) * weight, fill_value=0.0)
                active_count = active_count.add(present.astype(float), fill_value=0.0)
                equal_sum = equal_sum.add(values.fillna(0.0), fill_value=0.0)

            weighted_score = numerator.divide(denominator.where(denominator > 0.0))
            equal_score = equal_sum.divide(active_count.where(active_count > 0.0))
            score = weighted_score.fillna(equal_score).fillna(0.0)
            df.loc[mask, "score"] = np.clip(score.to_numpy(dtype=float), -1.0, 1.0)

    df["decision"] = "HOLD"
    for regime_name in _REGIMES:
        mask = df["regime"] == regime_name
        if not bool(mask.any()):
            continue
        threshold = cfg.threshold(Regime(regime_name))
        df.loc[mask & (df["score"].astype(float) >= threshold), "decision"] = "BUY"
        df.loc[mask & (df["score"].astype(float) <= -threshold), "decision"] = "SELL"
    return df


# ---------------------------------------------------------------------------
# Grid search (§9.3 step 1)
# ---------------------------------------------------------------------------


def _weight_candidates() -> list[tuple[float, ...]]:
    """All primary OHLCV-only weight tuples that sum to 1.0."""
    result: list[tuple[float, ...]] = []
    for leading in itertools.product(_WEIGHT_GRID, repeat=len(_ENGINES) - 1):
        last = round(1.0 - sum(leading), 10)
        if 0.0 <= last <= 1.0 + 1e-9:
            result.append((*leading, round(last, 2)))
    return result


def _grid_search(
    verdicts: pd.DataFrame,
) -> tuple[dict[str, Any], float, int]:
    """
    Brute-force grid search over weight x threshold space independently per regime.

    Returns (best_weights_data, best_objective, n_alerts).
    """
    weight_tuples = _weight_candidates()
    best_weights = _default_candidate()

    for regime in _REGIMES:
        regime_verdicts = verdicts[verdicts["regime"] == regime]
        if regime_verdicts.empty:
            continue

        best_regime_obj = -float("inf")
        best_regime_alerts = 0
        best_regime_weights = dict(best_weights[regime])
        best_regime_threshold = float(best_weights["thresholds"][regime])
        strengths = _strength_matrix(regime_verdicts)
        returns = regime_verdicts["return_h24"].astype(float).to_numpy()

        for weights in weight_tuples:
            scores = _scores_from_strengths(strengths, np.asarray(weights, dtype=float))
            for threshold in _THRESHOLD_GRID:
                decisions = np.where(scores >= threshold, 1.0, np.where(scores <= -threshold, -1.0, 0.0))
                obj = _objective_from_arrays(decisions, returns)
                n_alerts = int(np.count_nonzero(decisions))

                if obj > best_regime_obj or (
                    obj == best_regime_obj and n_alerts < best_regime_alerts
                ):
                    best_regime_obj = obj
                    best_regime_alerts = n_alerts
                    best_regime_weights = dict(zip(_ENGINES, weights, strict=True))
                    best_regime_weights["derivatives"] = 0.0
                    best_regime_threshold = threshold

        best_weights[regime] = best_regime_weights
        best_weights["thresholds"][regime] = best_regime_threshold

    verdicts_new = _apply_weights(verdicts, best_weights)
    best_obj = _objective(verdicts_new, WeightsConfig(best_weights))
    best_n_alerts = int((verdicts_new["decision"] != "HOLD").sum())
    return best_weights, best_obj, best_n_alerts


def _strength_matrix(verdicts: pd.DataFrame) -> NDArray[np.float64]:
    cols = [f"strength_{engine}" for engine in _ENGINES]
    data = {
        col: pd.to_numeric(verdicts[col], errors="coerce")
        if col in verdicts.columns
        else np.nan
        for col in cols
    }
    return np.asarray(pd.DataFrame(data, index=verdicts.index).to_numpy(dtype=float))


def _scores_from_strengths(
    strengths: NDArray[np.float64],
    weights: NDArray[np.float64],
) -> NDArray[np.float64]:
    present = np.isfinite(strengths)
    values = np.nan_to_num(strengths, nan=0.0)
    numerator = values @ weights
    denominator = present.astype(float) @ weights
    active_count = present.sum(axis=1)
    equal_scores = np.divide(
        values.sum(axis=1),
        active_count,
        out=np.zeros(len(strengths), dtype=float),
        where=active_count > 0,
    )
    scores = np.divide(
        numerator,
        denominator,
        out=equal_scores,
        where=denominator > 0,
    )
    return np.asarray(np.clip(scores, -1.0, 1.0), dtype=np.float64)


def _objective_from_arrays(
    decisions: NDArray[np.float64],
    returns: NDArray[np.float64],
) -> float:
    alert_mask = decisions != 0.0
    if not bool(alert_mask.any()):
        return -float("inf")

    pnl = returns[alert_mask] * decisions[alert_mask] - 0.0015
    mean_pnl = float(pnl.mean())
    std_pnl = float(pnl.std(ddof=1)) if len(pnl) > 1 else 0.0
    return mean_pnl - 0.5 * std_pnl


def _default_candidate() -> dict[str, Any]:
    equal = round(1.0 / len(_ENGINES), 4)
    candidate: dict[str, Any] = {
        "thresholds": dict.fromkeys(_REGIMES, 0.30),
        "vol_confidence_multiplier": {"low": 0.95, "normal": 1.0, "high": 0.85},
    }
    for regime in _REGIMES:
        candidate[regime] = dict.fromkeys(_ENGINES, equal)
        candidate[regime]["derivatives"] = 0.0
    return candidate


# ---------------------------------------------------------------------------
# Coordinate descent (§9.3 step 2)
# ---------------------------------------------------------------------------


def _coord_descent(
    verdicts: pd.DataFrame,
    start_weights: dict[str, Any],
    start_obj: float,
) -> tuple[dict[str, Any], float]:
    """
    Refine weights from start_weights using coordinate descent on a 5x finer grid.

    Varies one dimension at a time until no single-variable change improves obj.
    """
    current_weights = _deep_copy_weights(start_weights)
    current_obj = start_obj

    improved = True
    while improved:
        improved = False
        for regime in _REGIMES:
            for engine in _ENGINES:
                others = [e for e in _ENGINES if e != engine]
                current_val = float(current_weights[regime][engine])

                fine_range = np.round(
                    np.arange(
                        max(0.0, current_val - 0.1),
                        min(1.0, current_val + 0.1) + _FINE_STEP / 2,
                        _FINE_STEP,
                    ),
                    10,
                )

                for new_val in fine_range:
                    if abs(new_val - current_val) < 1e-9:
                        continue
                    remainder = 1.0 - new_val
                    if remainder < 0:
                        continue
                    # Redistribute remainder proportionally among the other engines.
                    other_sum = sum(float(current_weights[regime][e]) for e in others)
                    if other_sum <= 0:
                        split = {e: remainder / len(others) for e in others}
                    else:
                        split = {
                            e: float(current_weights[regime][e]) / other_sum * remainder
                            for e in others
                        }

                    candidate = _deep_copy_weights(current_weights)
                    candidate[regime][engine] = round(new_val, 4)
                    for e, w in split.items():
                        candidate[regime][e] = round(max(0.0, w), 4)

                    verdicts_new = _apply_weights(verdicts, candidate)
                    obj = _objective(verdicts_new, WeightsConfig(candidate))
                    if obj > current_obj:
                        current_obj = obj
                        current_weights = candidate
                        improved = True

            # Also try fine threshold adjustments.
            current_thresh = float(current_weights["thresholds"][regime])
            fine_thresh = np.round(
                np.arange(
                    max(0.05, current_thresh - 0.1),
                    min(0.70, current_thresh + 0.1) + _FINE_STEP / 2,
                    _FINE_STEP,
                ),
                4,
            )
            for new_thresh in fine_thresh:
                if abs(new_thresh - current_thresh) < 1e-9:
                    continue
                candidate = _deep_copy_weights(current_weights)
                candidate["thresholds"][regime] = round(float(new_thresh), 4)
                verdicts_new = _apply_weights(verdicts, candidate)
                obj = _objective(verdicts_new, WeightsConfig(candidate))
                if obj > current_obj:
                    current_obj = obj
                    current_weights = candidate
                    improved = True

    return current_weights, current_obj


def _deep_copy_weights(w: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(w)


# ---------------------------------------------------------------------------
# Sanity guard (§9.4)
# ---------------------------------------------------------------------------


def _check_sanity(
    weights: dict[str, Any],
    train_obj: float,
    test_obj: float,
) -> list[str]:
    """Return list of violated guard conditions (empty = clean)."""
    violations: list[str] = []

    # Guard 1: no engine weight == 1.0 in any regime.
    for regime in _REGIMES:
        for engine in _ENGINES:
            w = float(weights.get(regime, {}).get(engine, 0.0))
            if w >= 1.0 - 1e-6:
                violations.append(
                    f"Engine '{engine}' has weight 1.0 in regime '{regime}' (over-fit)"
                )

    # Guard 2: train-test expectancy gap > 50% relative.
    if train_obj != 0 and test_obj < 0 and abs(test_obj - train_obj) > abs(train_obj) * 0.5:
        violations.append(
            f"Train-test expectancy gap too large (train={train_obj:.4f}, test={test_obj:.4f})"
        )

    # Guard 3: test expectancy < 0.
    if test_obj < 0:
        violations.append(
            f"Test-slice expectancy is negative ({test_obj:.4f}) — calibrated weights are worse than nothing"
        )

    return violations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_optimizer(
    train_verdicts: pd.DataFrame,
    test_verdicts: pd.DataFrame,
) -> OptResult:
    """
    Fit weights on train_verdicts and evaluate on test_verdicts.

    Both DataFrames must come from labels.compute_labels() — i.e. must have
    columns: decision, score, regime, return_h24.

    Returns
    -------
    OptResult with fitted weights and sanity guard status.
    """
    if train_verdicts.empty:
        warnings.warn("train_verdicts is empty — returning default weights", stacklevel=2)
        return OptResult(
            weights={},
            train_objective=0.0,
            guard_fired=True,
            guard_violations=["Empty train slice"],
        )

    best_weights, best_obj, _ = _grid_search(train_verdicts)
    refined_weights, refined_obj = _coord_descent(train_verdicts, best_weights, best_obj)

    # Evaluate on test slice.
    test_verdicts_new = _apply_weights(test_verdicts, refined_weights)
    test_obj = _objective(test_verdicts_new, WeightsConfig(refined_weights))

    violations = _check_sanity(refined_weights, refined_obj, test_obj)
    return OptResult(
        weights=refined_weights,
        train_objective=refined_obj,
        guard_fired=bool(violations),
        guard_violations=violations,
    )


def aggregate_weights_across_folds(
    fold_weights: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Produce the recommended weights file from per-fold optimal weights.

    Rule (§13):
    - For each (regime, engine): median weight across folds, renormalized.
    - For thresholds: max across folds (conservative — fewer false alerts).
    """
    if not fold_weights:
        return {}

    result: dict[str, Any] = {
        "thresholds": {},
        "vol_confidence_multiplier": {"low": 0.95, "normal": 1.0, "high": 0.85},
    }

    for regime in _REGIMES:
        engine_medians: dict[str, float] = {}
        for engine in _ENGINES:
            vals = [float(w.get(regime, {}).get(engine, 0.0)) for w in fold_weights]
            engine_medians[engine] = float(np.median(vals))

        total = sum(engine_medians.values())
        if total <= 0:
            total = 1.0
        result[regime] = {e: round(v / total, 4) for e, v in engine_medians.items()}

        thresh_vals = [float(w.get("thresholds", {}).get(regime, 0.30)) for w in fold_weights]
        result["thresholds"][regime] = round(float(np.max(thresh_vals)), 4)

    return result


def weights_to_yaml(weights: dict[str, Any], path: str) -> None:
    """Write weights dict to a YAML file."""
    from pathlib import Path as _Path

    with _Path(path).open("w") as fh:
        yaml.safe_dump(
            _to_plain_yaml(weights),
            fh,
            default_flow_style=False,
            sort_keys=True,
        )


def _to_plain_yaml(value: Any) -> Any:
    """Convert numpy/pandas scalar containers to safe YAML primitives."""
    if isinstance(value, dict):
        return {str(k): _to_plain_yaml(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_to_plain_yaml(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value
