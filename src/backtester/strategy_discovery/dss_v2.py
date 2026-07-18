"""DSS v2 staged quality-diversity search runner."""

from __future__ import annotations

import csv
import json
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.dss_archive import DSSArchive, DSSArchiveElite, DSSScore
from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    DSSBehavior,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    FloatParam,
    IntParam,
    ParamDef,
)
from backtester.strategy_discovery.dss_objective import (
    _BACKTEST_ERROR_PENALTY,
    _EMPTY_SIGNAL_PENALTY,
    compute_mandate_score,
    run_dss_backtest,
)
from backtester.strategy_discovery.dss_stage1 import (
    BarrierMetrics,
    Stage1Result,
    evaluate_stage1,
    stage1_rank_score,
)
from backtester.strategy_discovery.dss_stage1 import (
    ComposerProtocol as _Composer,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

logger = logging.getLogger(__name__)

_STATE_VERSION = 2

__all__ = [
    "BarrierMetrics",
    "DSSV2Result",
    "Stage1Result",
    "StageScoreResult",
    "evaluate_stage1",
    "evaluate_stage_scores",
    "export_stage1_candidates",
    "export_stage4_candidates",
    "run_dss_v2_search",
    "write_stage1_ranked",
]


@dataclass(frozen=True, slots=True)
class StageScoreResult:
    candidate: DSSCandidate
    behavior: DSSBehavior
    score: DSSScore


@dataclass(frozen=True, slots=True)
class DSSV2Result:
    output: Path
    generated: int
    stage1_survivors: int
    stage2_survivors: int
    stage3_evaluations: int
    exported_candidates: list[Path]
    archive: DSSArchive


def run_dss_v2_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSV2Result:
    """Run DSS v2 and write resumable staged artifacts under config.output."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_stage3 = _read_completed_ids(output / "stage3_full_scores.csv")
    completed_stage0 = _read_stage0_candidates(output / "stage0_candidates.jsonl")
    stage0_by_id = {candidate.candidate_id: candidate for candidate in completed_stage0}

    candidates = list(completed_stage0)
    if len(candidates) < config.n_trials:
        candidates.extend(
            _generate_stage0_candidates(
                search_space=search_space,
                start=len(candidates),
                limit=config.n_trials,
                max_filters=config.max_filters,
            )
        )

    composer = SignalComposer()
    archive = DSSArchive()
    stage1_survivors = 0
    stage2_survivors = 0
    stage3_evaluations = 0

    for candidate in candidates:
        try:
            if candidate.candidate_id not in stage0_by_id:
                _append_jsonl(output / "stage0_candidates.jsonl", candidate.to_dict())
                stage0_by_id[candidate.candidate_id] = candidate

            if candidate.candidate_id in completed_stage3:
                continue

            stage1 = evaluate_stage1(candidate, window_data, config, composer)
            _append_stage1(output, candidate, stage1, config.windows)
            if not stage1.should_promote:
                continue
            behavior = stage1.behavior
            assert behavior is not None
            stage1_survivors += 1
            if config.stage_mode == "stage1":
                continue

            stage2 = evaluate_stage_scores(
                candidate=candidate,
                behavior=behavior,
                windows=_proxy_windows(config.windows),
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=10.0 if archive.occupied_cells == 0 else 0.0,
            )
            _append_stage_score(output / "stage2_proxy.csv", stage2, config.windows)
            archive.consider(stage2.candidate, stage2.behavior, stage2.score)

            if not _should_promote_to_stage3(stage2, archive, config):
                continue
            stage2_survivors += 1

            stage3 = evaluate_stage_scores(
                candidate=candidate,
                behavior=behavior,
                windows=config.windows,
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=0.0,
            )
            _append_stage_score(output / "stage3_full_scores.csv", stage3, config.windows)
            _append_score_history(output / "score_history.csv", stage3)
            archive.consider(stage3.candidate, stage3.behavior, stage3.score)
            completed_stage3.add(candidate.candidate_id)
            stage3_evaluations += 1
        finally:
            if progress_callback is not None:
                progress_callback(1)

    stage1_ranked = write_stage1_ranked(output, config)
    if config.stage_mode == "stage1":
        exported = export_stage1_candidates(stage1_ranked, output, config)
    else:
        _write_archive(output, archive)
        exported = export_stage4_candidates(archive, config)
    _write_summary(
        output=output,
        config=config,
        generated=len(candidates),
        stage1_survivors=stage1_survivors,
        stage2_survivors=stage2_survivors,
        stage3_evaluations=stage3_evaluations,
        exported=exported,
        archive=archive,
        stage1_ranked=len(stage1_ranked),
    )
    return DSSV2Result(
        output=output,
        generated=len(candidates),
        stage1_survivors=stage1_survivors,
        stage2_survivors=stage2_survivors,
        stage3_evaluations=stage3_evaluations,
        exported_candidates=exported,
        archive=archive,
    )


def evaluate_stage_scores(
    *,
    candidate: DSSCandidate,
    behavior: DSSBehavior,
    windows: list[DSSWindowSpec],
    window_data: dict[str, StrategyData],
    config: DSSConfig,
    composer: _Composer | None = None,
    novelty_bonus: float = 0.0,
) -> StageScoreResult:
    composer = composer or SignalComposer()
    try:
        generate = composer.build(candidate.trial_config)
    except ValueError:
        score = DSSScore.from_window_scores(
            candidate=candidate,
            window_scores={w.label: _EMPTY_SIGNAL_PENALTY for w in windows},
            trades_by_window={w.label: 0 for w in windows},
        )
        return StageScoreResult(candidate=candidate, behavior=behavior, score=score)

    scores: dict[str, float] = {}
    trades_by_window: dict[str, int] = {}
    for window in windows:
        data = window_data[window.label]
        try:
            signals = generate(data)
            trades = run_dss_backtest(
                signal_df=signals,
                config=candidate.trial_config,
                window_data=data,
                initial_capital=config.initial_capital,
                taker_fee=config.taker_fee,
                maker_fee=config.maker_fee,
                max_positions=config.max_positions,
                risk_base_period=config.risk_base_period,
            )
            scores[window.label] = compute_mandate_score(
                trades,
                initial_capital=config.initial_capital,
                start=window.start,
                end=window.end,
            )
            trades_by_window[window.label] = len(trades)
        except Exception:
            logger.debug("DSS v2 stage score failed for %s", window.label, exc_info=True)
            scores[window.label] = _BACKTEST_ERROR_PENALTY
            trades_by_window[window.label] = 0

    score = DSSScore.from_window_scores(
        candidate=candidate,
        window_scores=scores,
        trades_by_window=trades_by_window,
        novelty_bonus=novelty_bonus,
    )
    return StageScoreResult(candidate=candidate, behavior=behavior, score=score)


def export_stage4_candidates(archive: DSSArchive, config: DSSConfig) -> list[Path]:
    candidates_dir = config.output / "candidates"
    candidates_dir.mkdir(exist_ok=True)
    exports: list[Path] = []
    manifest_rows: list[dict[str, object]] = []

    unique: dict[str, DSSArchiveElite] = {}
    for elite in archive.elites():
        unique.setdefault(elite.candidate.candidate_id, elite)

    for rank, elite in enumerate(list(unique.values())[: config.top_n_candidates], 1):
        candidate = elite.candidate
        safe_cell = elite.behavior.to_label().replace("|", "_").replace("/", "_")
        path = candidates_dir / f"dss_v2_{rank:03d}_{candidate.trigger_name}_{safe_cell}.json"
        payload = {
            "name": "dss_strategy",
            "version": "2.0",
            "candidate_id": candidate.candidate_id,
            "scores": elite.score.window_scores,
            "min_score": elite.score.score_min,
            "robust_score": elite.score.robust_score,
            "behavior_cell": elite.behavior.to_label(),
            "params": candidate.trial_config.to_dict(),
            "backtest_args": {
                "rrr": candidate.rrr,
                "risk_percent": candidate.risk_percent,
                "position_ttl_bars": candidate.position_ttl_bars,
                "risk_base_period": config.risk_base_period,
                "exit_geometry": "sl_rrr",
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        exports.append(path)
        manifest_rows.append(
            {
                "rank": rank,
                "candidate_path": str(path),
                "candidate_id": candidate.candidate_id,
                "behavior_cell": elite.behavior.to_label(),
                "robust_score": elite.score.robust_score,
                "score_min": elite.score.score_min,
                "trigger_name": candidate.trigger_name,
                "filter_names": "+".join(candidate.filter_names),
                "rrr": candidate.rrr,
                "risk_percent": candidate.risk_percent,
                "ttl": candidate.position_ttl_bars,
                "atr_sl_mult": candidate.atr_sl_mult,
                "validation_command": _validation_command(config, path),
            }
        )

    _write_csv(config.output / "candidate_manifest.csv", manifest_rows)
    _write_manifest_md(config.output / "candidate_manifest.md", manifest_rows)
    return exports


def write_stage1_ranked(output: Path, config: DSSConfig) -> list[dict[str, object]]:
    source = output / "stage1_viability.csv"
    if not source.exists():
        return []
    rows: list[dict[str, object]] = []
    near_misses: list[dict[str, object]] = []
    with source.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            scored = dict(row)
            scored["stage1_score"] = stage1_rank_score(scored, config.windows)
            if str(row.get("should_promote", row.get("passed", ""))).lower() == "true":
                rows.append(scored)
            else:
                near_misses.append(scored)
    rows.sort(key=lambda row: cast(float, row["stage1_score"]), reverse=True)
    near_misses.sort(key=lambda row: cast(float, row["stage1_score"]), reverse=True)
    ranked_path = output / "stage1_ranked.csv"
    if rows:
        fieldnames = ["rank", "stage1_score", *[key for key in rows[0] if key != "stage1_score"]]
        with ranked_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for idx, row in enumerate(rows, 1):
                writer.writerow({"rank": idx, **row})
    elif ranked_path.exists():
        ranked_path.unlink()
    near_miss_path = output / "stage1_near_misses.csv"
    if near_misses:
        fieldnames = [
            "rank",
            "stage1_score",
            *[key for key in near_misses[0] if key != "stage1_score"],
        ]
        with near_miss_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for idx, row in enumerate(near_misses, 1):
                writer.writerow({"rank": idx, **row})
    elif near_miss_path.exists():
        near_miss_path.unlink()
    return rows


def export_stage1_candidates(
    ranked_rows: list[dict[str, object]], output: Path, config: DSSConfig
) -> list[Path]:
    candidates_by_id = {
        candidate.candidate_id: candidate
        for candidate in _read_stage0_candidates(output / "stage0_candidates.jsonl")
    }
    candidates_dir = output / "stage1_candidates"
    candidates_dir.mkdir(exist_ok=True)
    exports: list[Path] = []
    manifest_rows: list[dict[str, object]] = []
    for idx, row in enumerate(ranked_rows[: config.top_n_candidates], 1):
        candidate_id = str(row["candidate_id"])
        candidate = candidates_by_id.get(candidate_id)
        if candidate is None:
            continue
        path = candidates_dir / f"stage1_{idx:03d}_{candidate_id}_{candidate.trigger_name}.json"
        payload = {
            "name": "dss_strategy",
            "version": "2.0-stage1",
            "candidate_id": candidate.candidate_id,
            "stage1_score": row["stage1_score"],
            "stage1_metrics": row,
            "params": candidate.trial_config.to_dict(),
            "backtest_args": {
                "rrr": candidate.rrr,
                "risk_percent": candidate.risk_percent,
                "position_ttl_bars": candidate.position_ttl_bars,
                "risk_base_period": config.risk_base_period,
                "exit_geometry": "sl_rrr",
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        exports.append(path)
        manifest_rows.append(
            {
                "rank": idx,
                "candidate_id": candidate.candidate_id,
                "candidate_path": str(path),
                "trigger_name": candidate.trigger_name,
                "filter_names": "+".join(candidate.filter_names),
                "stage1_score": row["stage1_score"],
            }
        )
    if manifest_rows:
        _write_stage1_manifest(output / "stage1_candidate_manifest.md", manifest_rows)
    return exports


def _write_stage1_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# DSS Stage 1 candidate manifest",
        "",
        "These candidates passed Stage 1 only. They are signal-family research artifacts, not promotion-ready backtest results.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['rank']}. {row['candidate_id']}",
                "",
                f"- Path: `{row['candidate_path']}`",
                f"- Trigger: `{row['trigger_name']}`",
                f"- Filters: `{row['filter_names']}`",
                f"- Stage 1 score: `{cast(float, row['stage1_score']):.2f}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _generate_stage0_candidates(
    *,
    search_space: DSSSearchSpace,
    start: int,
    limit: int,
    max_filters: int,
) -> list[DSSCandidate]:
    rng = random.Random(36)
    triggers = list(search_space.trigger_names)
    filters = list(search_space.filter_names)
    out: list[DSSCandidate] = []
    exec_grid = [
        (1.5, 1.0, 24, 0.75),
        (2.0, 1.5, 36, 1.0),
        (2.5, 2.0, 48, 1.5),
        (3.0, 2.5, 60, 2.0),
        (4.0, 3.0, 72, 2.5),
    ]
    filter_depths = [0, 1, 2, min(3, max_filters)]
    for idx in range(start, limit):
        trigger = triggers[idx % len(triggers)]
        depth = filter_depths[(idx // max(len(triggers), 1)) % len(filter_depths)]
        depth = min(depth, max_filters, len(filters))
        chosen_filters = tuple(sorted(rng.sample(filters, depth))) if depth else ()
        rrr, risk, ttl, atr = exec_grid[idx % len(exec_grid)]
        out.append(
            DSSCandidate(
                candidate_id=f"dssv2_{idx + 1:06d}",
                trigger_name=trigger,
                trigger_params={
                    name: _sample_param(pdef, rng)
                    for name, pdef in search_space.trigger_param_bounds.get(trigger, {}).items()
                },
                filter_names=chosen_filters,
                filter_params={
                    name: {
                        pname: _sample_param(pdef, rng)
                        for pname, pdef in search_space.filter_param_bounds.get(name, {}).items()
                    }
                    for name in chosen_filters
                },
                rrr=rrr,
                risk_percent=risk,
                position_ttl_bars=ttl,
                atr_sl_mult=atr,
                generation=0,
            )
        )
    return out


def _sample_param(pdef: ParamDef, rng: random.Random) -> float | int | str:
    if isinstance(pdef, IntParam):
        steps = list(range(pdef.low, pdef.high + 1, pdef.step))
        return rng.choice(steps)
    if isinstance(pdef, FloatParam):
        if pdef.step is None:
            return round(rng.uniform(pdef.low, pdef.high), 6)
        n = round((pdef.high - pdef.low) / pdef.step)
        return round(pdef.low + rng.randint(0, n) * pdef.step, 6)
    if isinstance(pdef, CategoricalParam):
        return rng.choice(list(pdef.choices))
    raise TypeError(f"Unsupported param def: {pdef!r}")


def _proxy_windows(windows: list[DSSWindowSpec]) -> list[DSSWindowSpec]:
    if len(windows) <= 2:
        return windows
    labels = {windows[0].label: windows[0], windows[-1].label: windows[-1]}
    if "2024" in {w.label for w in windows}:
        labels["2024"] = next(w for w in windows if w.label == "2024")
    return list(labels.values())[:2]


def _should_promote_to_stage3(
    result: StageScoreResult,
    archive: DSSArchive,
    config: DSSConfig,
) -> bool:
    if result.score.score_min <= _BACKTEST_ERROR_PENALTY:
        return False
    per_cell_ids = {elite.candidate.candidate_id for elite in archive.best_per_cell()}
    if result.candidate.candidate_id in per_cell_ids:
        return True
    return len(per_cell_ids) < max(5, int(config.n_trials * 0.02))


def _guard_output_dir(output: Path) -> None:
    if (output / "study.journal").exists() and not (output / "state.json").exists():
        raise ValueError(
            "Output directory contains DSS v1 artifacts. DSS v2 cannot resume this run. "
            "Use a new output directory."
        )


def _write_state(output: Path, config: DSSConfig) -> None:
    payload = {
        "version": _STATE_VERSION,
        "n_trials": config.n_trials,
        "catalog": config.catalog,
        "stage_mode": config.stage_mode,
        "min_trades_per_window": config.min_trades_per_window,
        "min_signals_per_week": config.min_signals_per_week,
        "stage1_tp_move_pct": config.stage1_tp_move_pct,
        "stage1_sl_move_pct": config.stage1_sl_move_pct,
        "stage1_reference_atr_pct": config.stage1_reference_atr_pct,
        "windows": [
            {
                "label": window.label,
                "symbol": window.symbol,
                "start": window.start,
                "end": window.end,
            }
            for window in config.windows
        ],
        "specialist_windows": list(config.specialist_windows),
    }
    (output / "state.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


def _read_stage0_candidates(path: Path) -> list[DSSCandidate]:
    if not path.exists():
        return []
    candidates: list[DSSCandidate] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            candidates.append(DSSCandidate.from_dict(json.loads(line)))
    return candidates


def _read_completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as fh:
        return {row["candidate_id"] for row in csv.DictReader(fh) if row.get("candidate_id")}


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _append_stage1(
    output: Path,
    candidate: DSSCandidate,
    result: Stage1Result,
    windows: list[DSSWindowSpec],
) -> None:
    row: dict[str, object] = {
        "candidate_id": candidate.candidate_id,
        "trigger_name": candidate.trigger_name,
        "filter_names": "+".join(candidate.filter_names),
        "passed": result.passed,
        "should_promote": result.should_promote,
        "stage1_score": result.advisory_score if result.advisory_score is not None else "",
        "candidate_class": result.candidate_class,
        "target_window": result.target_window,
        "rejection_reason": result.rejection_reason,
    }
    for window in windows:
        label = window.label
        count = result.signal_counts.get(label, "")
        ratio = result.long_ratios.get(label, "")
        stop = result.median_stop_atr.get(label, "")
        row[f"signals_{label}"] = count
        row[f"long_ratio_{label}"] = ratio
        row[f"median_stop_atr_{label}"] = stop
        metrics = result.barrier_metrics.get(label)
        row[f"barrier_total_{label}"] = metrics.total if metrics else ""
        row[f"barrier_tp_first_rate_{label}"] = metrics.tp_first_rate if metrics else ""
        row[f"barrier_sl_first_rate_{label}"] = metrics.sl_first_rate if metrics else ""
        row[f"barrier_timeout_rate_{label}"] = metrics.timeout_rate if metrics else ""
        row[f"barrier_unresolved_tail_rate_{label}"] = (
            metrics.unresolved_tail_rate if metrics else ""
        )
        row[f"barrier_win_rate_{label}"] = metrics.win_rate if metrics else ""
        row[f"barrier_median_mae_atr_{label}"] = metrics.median_mae_atr if metrics else ""
        row[f"barrier_median_mfe_atr_{label}"] = metrics.median_mfe_atr if metrics else ""
        row[f"barrier_median_mae_pct_{label}"] = metrics.median_mae_pct if metrics else ""
        row[f"barrier_median_mfe_pct_{label}"] = metrics.median_mfe_pct if metrics else ""
        row[f"barrier_median_bars_to_tp_{label}"] = metrics.median_bars_to_tp if metrics else ""
    _append_csv_row(output / "stage1_viability.csv", row)
    if result.passed:
        _append_jsonl(output / "stage1_survivors.jsonl", candidate.to_dict())
    elif result.candidate_class.startswith("specialist:"):
        payload = candidate.to_dict()
        payload["candidate_class"] = result.candidate_class
        payload["target_window"] = result.target_window
        _append_jsonl(output / "stage1_specialists.jsonl", payload)
        _append_csv_row(output / "stage1_specialists.csv", row)
    else:
        _append_csv_row(output / "stage1_rejections.csv", row)


def _append_stage_score(path: Path, result: StageScoreResult, windows: list[DSSWindowSpec]) -> None:
    candidate = result.candidate
    score = result.score
    row: dict[str, object] = {
        "candidate_id": candidate.candidate_id,
        "trigger_name": candidate.trigger_name,
        "filter_names": "+".join(candidate.filter_names),
        "behavior_cell": result.behavior.to_label(),
        "robust_score": score.robust_score,
        "score_min": score.score_min,
        "score_median": score.score_median,
        "score_mean": score.score_mean,
        "score_stdev": score.score_stdev,
        "rrr": candidate.rrr,
        "risk_percent": candidate.risk_percent,
        "position_ttl_bars": candidate.position_ttl_bars,
        "atr_sl_mult": candidate.atr_sl_mult,
    }
    for window in windows:
        row[f"score_{window.label}"] = score.window_scores.get(window.label, "")
        row[f"trades_{window.label}"] = score.trades_by_window.get(window.label, "")
    _append_csv_row(path, row)
    if path.name == "stage2_proxy.csv":
        _append_jsonl(path.with_name("stage2_survivors.jsonl"), candidate.to_dict())


def _append_score_history(path: Path, result: StageScoreResult) -> None:
    _append_csv_row(
        path,
        {
            "candidate_id": result.candidate.candidate_id,
            "robust_score": result.score.robust_score,
            "score_min": result.score.score_min,
            "score_median": result.score.score_median,
        },
    )


def _append_csv_row(path: Path, row: dict[str, object]) -> None:
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_archive(output: Path, archive: DSSArchive) -> None:
    (output / "archive.json").write_text(
        json.dumps(archive.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = ["# DSS v2 archive", "", f"Occupied cells: **{archive.occupied_cells}**", ""]
    for elite in archive.best_per_cell():
        lines.append(
            f"- `{elite.behavior.to_label()}`: `{elite.candidate.candidate_id}` "
            f"robust={elite.score.robust_score:.2f}"
        )
    (output / "archive.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest_md(path: Path, rows: list[dict[str, object]]) -> None:
    lines = ["# DSS v2 candidate manifest", ""]
    if not rows:
        lines.append("No candidates exported.")
    for row in rows:
        lines.extend(
            [
                f"## Rank {row['rank']} — {row['candidate_id']}",
                "",
                f"- Path: `{row['candidate_path']}`",
                f"- Behavior cell: `{row['behavior_cell']}`",
                f"- Robust score: `{cast(float, row['robust_score']):.2f}`",
                "",
                "```bash",
                str(row["validation_command"]),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary(
    *,
    output: Path,
    config: DSSConfig,
    generated: int,
    stage1_survivors: int,
    stage2_survivors: int,
    stage3_evaluations: int,
    exported: list[Path],
    archive: DSSArchive,
    stage1_specialists: int | None = None,
    stage1_ranked: int | None = None,
) -> None:
    if stage1_specialists is None:
        stage1_specialists = _count_csv_rows(output / "stage1_specialists.csv")
    if stage1_ranked is None:
        stage1_ranked = _count_csv_rows(output / "stage1_ranked.csv")
    stage1_near_misses = _count_csv_rows(output / "stage1_near_misses.csv")
    best = archive.elites()[0] if archive.elites() else None
    if config.stage_mode == "stage1":
        verdict = "stage1 shortlist exported" if exported else "no stage1 candidate"
        reason = (
            "Stage 1-only mode stopped before backtest scoring"
            if exported
            else "no candidate passed Stage 1"
        )
    else:
        verdict = "candidates exported" if exported else "no candidate"
        reason = "archive has replay JSONs" if exported else "no archive elite reached export"
    lines = [
        "# DSS v2 run summary",
        "",
        f"Verdict: **{verdict}**",
        f"Reason: {reason}",
        f"Stage mode: **{config.stage_mode}**",
        f"Min signals per week: **{config.min_signals_per_week:g}**",
        f"Generated candidates: **{generated}**",
        f"Stage 1 survivors: **{stage1_survivors}**",
        f"Stage 1 ranked candidates: **{stage1_ranked}**",
        f"Stage 1 near misses: **{stage1_near_misses}**",
        f"Stage 1 specialists: **{stage1_specialists}**",
        f"Stage 2 survivors: **{stage2_survivors}**",
        f"Stage 3 full evaluations: **{stage3_evaluations}**",
        f"Archive occupied cells: **{archive.occupied_cells}**",
        f"Exported candidates: **{len(exported)}**",
        f"Best robust score: **{best.score.robust_score:.2f}**"
        if best
        else "Best robust score: **n/a**",
        f"Best candidate path: `{exported[0]}`" if exported else "Best candidate path: n/a",
        "",
        "## Stage Funnel",
        "",
        "| Stage | Count |",
        "| --- | ---: |",
        f"| Generated | {generated} |",
        f"| Stage 1 survivors | {stage1_survivors} |",
        f"| Stage 1 ranked candidates | {stage1_ranked} |",
        f"| Stage 1 near misses | {stage1_near_misses} |",
        f"| Stage 1 specialists | {stage1_specialists} |",
        f"| Stage 2 survivors | {stage2_survivors} |",
        f"| Stage 3 full evaluations | {stage3_evaluations} |",
        f"| Archive cells | {archive.occupied_cells} |",
        f"| Exported | {len(exported)} |",
        "",
        "## Next Owner Command",
        "",
    ]
    if exported:
        if config.stage_mode == "stage1":
            lines.extend(
                [
                    "Stage 1-only exports are under `stage1_candidates/`. Pick a candidate manually before running validation.",
                    "",
                ]
            )
        else:
            lines.extend(["```bash", _validation_command(config, exported[0]), "```", ""])
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _count_csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open(encoding="utf-8", newline="") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def _validation_command(config: DSSConfig, candidate_path: Path) -> str:
    symbol = config.windows[0].symbol if config.windows else "SOL-USDT-SWAP"
    return (
        "uv run backtester compare-fixed "
        f"--data-dir data --symbol {symbol} "
        f"--strategy {candidate_path} "
        "--from 2025-01-01 --to 2025-12-31 "
        "--output results/dss_v2_eval_2025"
    )
