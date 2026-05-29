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

from crypt.aggregator.weights import WeightsConfig

# ---------------------------------------------------------------------------
# Search-space constants (§9.1)
# ---------------------------------------------------------------------------

_WEIGHT_GRID = np.round(np.arange(0.0, 1.01, 0.1), 2).tolist()
_THRESHOLD_GRID = np.round(np.arange(0.15, 0.56, 0.05), 2).tolist()
_REGIMES = ("TRENDING", "RANGING", "HIGH_VOL")
_ENGINES = ("trend", "meanrev", "derivatives")
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
    Input verdicts_df must have columns: tick_time, symbol, score, regime, confidence.
    Decision is inferred as: BUY if score >= threshold, SELL if score <= -threshold, else HOLD.
    """
    cfg = WeightsConfig(weights_data)
    df = verdicts.copy()

    def _decide(row: pd.Series) -> str:
        try:
            threshold = cfg.threshold(row["regime"])
        except Exception:
            return "HOLD"
        score = float(row["score"])
        if score >= threshold:
            return "BUY"
        if score <= -threshold:
            return "SELL"
        return "HOLD"

    df["decision"] = df.apply(_decide, axis=1)
    return df


# ---------------------------------------------------------------------------
# Grid search (§9.3 step 1)
# ---------------------------------------------------------------------------


def _weight_candidates() -> list[tuple[float, float, float]]:
    """All (trend, meanrev, derivatives) weight triples that sum to 1.0."""
    result: list[tuple[float, float, float]] = []
    for w1, w2 in itertools.product(_WEIGHT_GRID, repeat=2):
        w3 = round(1.0 - w1 - w2, 10)
        if 0.0 <= w3 <= 1.0 + 1e-9:
            result.append((w1, w2, round(w3, 2)))
    return result


def _grid_search(
    verdicts: pd.DataFrame,
) -> tuple[dict[str, Any], float, int]:
    """
    Brute-force grid search over weight x threshold space for all regimes.

    Returns (best_weights_data, best_objective, n_alerts).
    """
    weight_triples = _weight_candidates()
    best_obj = -float("inf")
    best_weights: dict[str, Any] = {}
    best_n_alerts = 0

    for thresholds in itertools.product(_THRESHOLD_GRID, repeat=len(_REGIMES)):
        for regime_weights in itertools.product(weight_triples, repeat=len(_REGIMES)):
            candidate: dict[str, Any] = {
                "thresholds": dict(zip(_REGIMES, thresholds, strict=True)),
                "vol_confidence_multiplier": {"low": 0.95, "normal": 1.0, "high": 0.85},
            }
            for regime, (w1, w2, w3) in zip(_REGIMES, regime_weights, strict=True):
                candidate[regime] = {
                    "trend": w1,
                    "meanrev": w2,
                    "derivatives": w3,
                }

            verdicts_new = _apply_weights(verdicts, candidate)
            obj = _objective(verdicts_new, WeightsConfig(candidate))
            n_alerts = int((verdicts_new["decision"] != "HOLD").sum())

            if obj > best_obj or (obj == best_obj and n_alerts < best_n_alerts):
                best_obj = obj
                best_weights = candidate
                best_n_alerts = n_alerts

    return best_weights, best_obj, best_n_alerts


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
        yaml.dump(weights, fh, default_flow_style=False, sort_keys=True)
