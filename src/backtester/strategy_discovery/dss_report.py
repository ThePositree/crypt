"""DSSReport — Pareto front extraction and candidate JSON export.

After n_trials, writes:
  study.journal        (already exists; this module reads it)
  pareto_front.json    (all non-dominated complete trials)
  summary.md           (top-N candidates table)
  candidates/          (one JSON per top-N candidate)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import optuna
import pandas as pd

from backtester.strategy_discovery.dss_config import DSSConfig, TrialConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pareto front helpers
# ---------------------------------------------------------------------------


def _is_dominated(scores_a: list[float], scores_b: list[float]) -> bool:
    """Return True if ``scores_a`` is dominated by ``scores_b`` (all ≥, at least one >)."""
    if len(scores_a) != len(scores_b):
        return False
    at_least_one_better = False
    for a, b in zip(scores_a, scores_b, strict=True):
        if b < a:
            return False
        if b > a:
            at_least_one_better = True
    return at_least_one_better


def _extract_pareto_front(
    trials: list[optuna.trial.FrozenTrial],
    n_objectives: int,
) -> list[optuna.trial.FrozenTrial]:
    """Filter to non-dominated complete trials (Pareto front)."""
    complete = [
        t for t in trials
        if t.state == optuna.trial.TrialState.COMPLETE
        and t.values is not None
        and len(t.values) == n_objectives
    ]
    pareto: list[optuna.trial.FrozenTrial] = []
    for candidate in complete:
        scores_c = list(candidate.values)  # type: ignore[arg-type]
        dominated = False
        for other in complete:
            if other.number == candidate.number:
                continue
            if _is_dominated(scores_c, list(other.values)):  # type: ignore[arg-type]
                dominated = True
                break
        if not dominated:
            pareto.append(candidate)
    return sorted(pareto, key=lambda t: sum(t.values or []), reverse=True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Candidate JSON helpers
# ---------------------------------------------------------------------------


def _trial_to_trial_config(trial: optuna.trial.FrozenTrial) -> TrialConfig | None:
    """Reconstruct a TrialConfig from an Optuna trial's params."""
    params = trial.params
    trigger_name = params.get("trigger_name")
    if trigger_name is None:
        return None

    trigger_params: dict[str, float | int] = {}
    filter_params: dict[str, dict[str, float | int]] = {}

    trigger_prefix = f"tp_{trigger_name}_"
    for k, v in params.items():
        if k.startswith(trigger_prefix):
            pname = k[len(trigger_prefix):]
            if isinstance(v, (int, float)):
                trigger_params[pname] = v
            else:
                trigger_params[pname] = v

    n_filters = int(params.get("n_filters", 0))
    filter_names_raw: list[str] = []
    for i in range(n_filters):
        fn = params.get(f"filter_{i}")
        if fn is not None:
            filter_names_raw.append(str(fn))
    filter_names = tuple(sorted(set(filter_names_raw)))

    for fn in filter_names:
        fp: dict[str, float | int] = {}
        prefix = f"fp_{fn}_"
        for k, v in params.items():
            if k.startswith(prefix):
                pname = k[len(prefix):]
                fp[pname] = v
        filter_params[fn] = fp

    try:
        return TrialConfig(
            trigger_name=str(trigger_name),
            trigger_params=trigger_params,
            filter_names=filter_names,
            filter_params=filter_params,
            rrr=float(params.get("rrr", 2.0)),
            risk_percent=float(params.get("risk_percent", 1.0)),
            position_ttl_bars=int(params.get("position_ttl_bars", 36)),
            atr_sl_mult=float(params.get("atr_sl_mult", 1.0)),
        )
    except (TypeError, ValueError, KeyError):
        return None


def _trial_to_candidate_json(
    trial: optuna.trial.FrozenTrial,
    window_labels: list[str],
    candidate_id: str,
) -> dict[str, Any]:
    """Build a strategies/backtester/*.json-compatible candidate dict."""
    config = _trial_to_trial_config(trial)
    if config is None:
        return {}

    scores: dict[str, float] = {}
    for label in window_labels:
        v = trial.user_attrs.get(f"score_{label}")
        if v is not None:
            scores[label] = float(v)

    return {
        "name": "dss_strategy",
        "version": "1.0",
        "candidate_id": candidate_id,
        "trial_number": trial.number,
        "scores": scores,
        "min_score": min(scores.values()) if scores else float("-inf"),
        "params": config.to_dict(),
        "backtest_args": {
            "rrr": config.rrr,
            "risk_percent": config.risk_percent,
            "position_ttl_bars": config.position_ttl_bars,
            "risk_base_period": "monthly",
            "exit_geometry": "sl_rrr",
        },
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_dss_report(
    *,
    study: optuna.Study,
    dss_config: DSSConfig,
    output: Path,
) -> None:
    """Write all DSS artifacts after a study completes (or is interrupted).

    Writes:
      pareto_front.json  — all non-dominated solutions
      summary.md         — human-readable top-N table
      candidates/        — one JSON per top-N candidate
    """
    output.mkdir(parents=True, exist_ok=True)
    windows = dss_config.windows
    window_labels = [w.label for w in windows]
    n_objectives = len(windows)

    all_trials = study.trials
    logger.info(
        "DSS report: %d total trials, extracting Pareto front…", len(all_trials)
    )

    pareto = _extract_pareto_front(all_trials, n_objectives)
    logger.info("Pareto front size: %d non-dominated solutions", len(pareto))

    # Filter by accept_min_score_per_window
    threshold = dss_config.accept_min_score_per_window
    accepted = [
        t for t in pareto
        if t.values and all(v >= threshold for v in t.values)  # type: ignore[misc]
    ]
    logger.info(
        "%d solutions pass accept_min_score_per_window=%.0f", len(accepted), threshold
    )

    # Write pareto_front.json
    pareto_payload = {
        "study_name": study.study_name,
        "n_trials": len(all_trials),
        "n_complete": sum(
            1 for t in all_trials if t.state == optuna.trial.TrialState.COMPLETE
        ),
        "n_pareto": len(pareto),
        "n_accepted": len(accepted),
        "windows": window_labels,
        "solutions": [
            {
                "trial_number": t.number,
                "params": dict(t.params.items()),
                "scores": {
                    label: float(v)
                    for label, v in zip(window_labels, t.values or [], strict=False)
                },
                "min_score": min(t.values) if t.values else float("-inf"),
            }
            for t in pareto
        ],
    }
    pareto_json = output / "pareto_front.json"
    pareto_json.write_text(
        json.dumps(pareto_payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    logger.info("Pareto front JSON → %s", pareto_json)

    # Select top-N candidates
    top_n = min(dss_config.top_n_candidates, len(accepted))
    top_trials = accepted[:top_n]

    # Write candidates/
    candidates_dir = output / "candidates"
    candidates_dir.mkdir(exist_ok=True)
    candidate_paths: list[Path] = []

    for rank, trial in enumerate(top_trials, 1):
        trigger_name = trial.params.get("trigger_name", "unknown")
        rrr = trial.params.get("rrr", 0.0)
        candidate_id = f"dss_{rank:03d}_{trigger_name}_rrr{rrr:.1f}"
        payload = _trial_to_candidate_json(trial, window_labels, candidate_id)
        if not payload:
            continue
        fname = candidates_dir / f"{candidate_id}.json"
        fname.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        candidate_paths.append(fname)

    logger.info("Exported %d candidate JSON files → %s", len(candidate_paths), candidates_dir)

    # Write summary.md
    md = _build_summary_md(
        top_trials=top_trials,
        window_labels=window_labels,
        study_name=study.study_name,
        n_trials=len(all_trials),
        n_pareto=len(pareto),
        n_accepted=len(accepted),
    )
    summary_md = output / "summary.md"
    summary_md.write_text(md, encoding="utf-8")
    logger.info("Summary MD → %s", summary_md)

    # Write trials.csv for all complete trials
    complete_trials = [
        t for t in all_trials if t.state == optuna.trial.TrialState.COMPLETE
    ]
    if complete_trials:
        rows = []
        for t in complete_trials:
            row: dict[str, Any] = {
                "trial": t.number,
                "state": "complete",
                **{f"score_{label}": float(v) for label, v in zip(window_labels, t.values or [], strict=False)},
                "min_score": min(t.values) if t.values else float("-inf"),
                **{f"p_{k}": v for k, v in t.params.items()},
                **{f"ua_{k}": v for k, v in t.user_attrs.items()},
            }
            rows.append(row)
        trials_df = pd.DataFrame(rows)
        trials_csv = output / "trials.csv"
        trials_df.to_csv(trials_csv, index=False)
        logger.info("Trials CSV → %s", trials_csv)


def _build_summary_md(
    *,
    top_trials: list[optuna.trial.FrozenTrial],
    window_labels: list[str],
    study_name: str,
    n_trials: int,
    n_pareto: int,
    n_accepted: int,
) -> str:
    lines = [
        f"# DSS run summary — {study_name}",
        "",
        f"- Total trials: **{n_trials}**",
        f"- Pareto front: **{n_pareto}** non-dominated solutions",
        f"- Accepted (above threshold): **{n_accepted}**",
        f"- Top candidates shown: **{len(top_trials)}**",
        "",
    ]
    if not top_trials:
        lines.append("_No candidates passed the acceptance threshold._")
        return "\n".join(lines)

    header_cols = ["#", "Trial", "Trigger", "Filters", "RRR", "TTL", "Risk%"]
    for label in window_labels:
        header_cols.append(label)
    header_cols.append("min_score")

    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join("---" for _ in header_cols) + " |")

    for rank, trial in enumerate(top_trials, 1):
        trigger = trial.params.get("trigger_name", "?")
        n_filters = trial.params.get("n_filters", 0)
        rrr = trial.params.get("rrr", 0.0)
        ttl = trial.params.get("position_ttl_bars", 0)
        risk = trial.params.get("risk_percent", 0.0)
        scores = [
            f"{float(v):.1f}" if trial.values and i < len(trial.values) else "—"
            for i, v in enumerate(trial.values or [])
        ]
        min_score = f"{min(trial.values):.1f}" if trial.values else "—"

        row = [
            str(rank),
            str(trial.number),
            trigger,
            str(n_filters),
            f"{rrr:.2f}",
            str(ttl),
            f"{risk:.2f}%",
            *scores,
            min_score,
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append(
        "> Candidates exported to `candidates/` directory. "
        "Use `backtester compare-fixed` to validate top picks."
    )
    lines.append("")
    return "\n".join(lines)
