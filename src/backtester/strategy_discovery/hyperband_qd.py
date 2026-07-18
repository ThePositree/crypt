"""Hyperband-style quality-diversity DSS backend."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.catcma_qd import (
    _EvaluatedCandidate,
    _stage1_cheap_score,
    _Stage1Candidate,
    _WeightedModel,
    _write_model_summary,
)
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import DSSConfig, DSSSearchSpace
from backtester.strategy_discovery.dss_v2 import (
    DSSV2Result,
    StageScoreResult,
    _append_csv_row,
    _append_jsonl,
    _append_score_history,
    _append_stage1,
    _append_stage_score,
    _guard_output_dir,
    _proxy_windows,
    _read_completed_ids,
    _read_stage0_candidates,
    _write_archive,
    _write_state,
    _write_summary,
    evaluate_stage1,
    evaluate_stage_scores,
    export_stage1_candidates,
    export_stage4_candidates,
    write_stage1_ranked,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_POPULATION_SIZE = 64
_RUNG1_FRACTION = 0.30
_RUNG2_FRACTION = 0.20
_RUNG3_FRACTION = 0.10


@dataclass(frozen=True, slots=True)
class _RungCandidate:
    stage1: _Stage1Candidate
    score: StageScoreResult | None = None


def run_hyperband_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSV2Result:
    """Run a successive-halving QD backend with DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_stage3 = _read_completed_ids(output / "stage3_full_scores.csv")
    existing_stage0 = _read_stage0_candidates(output / "stage0_candidates.jsonl")
    model = _WeightedModel(search_space, seed=config.seed)
    composer = SignalComposer()
    archive = DSSArchive()
    generated = min(len(existing_stage0), config.n_trials)
    if generated and progress_callback is not None:
        progress_callback(generated)
    batch_index = generated // _POPULATION_SIZE
    stage1_survivors = 0
    stage2_survivors = 0
    stage3_evaluations = 0

    while generated < config.n_trials:
        batch_size = min(_POPULATION_SIZE, config.n_trials - generated)
        stage1_passed: list[_Stage1Candidate] = []
        evaluated_for_model: list[_EvaluatedCandidate] = []

        for _ in range(batch_size):
            generated += 1
            candidate = model.sample(f"hyperband_{generated:06d}", generation=batch_index)
            try:
                _append_jsonl(output / "stage0_candidates.jsonl", candidate.to_dict())
                if candidate.candidate_id in completed_stage3:
                    continue
                stage1 = evaluate_stage1(candidate, window_data, config, composer)
                _append_stage1(output, candidate, stage1, config.windows)
                if not stage1.should_promote:
                    continue
                stage1_survivors += 1
                stage1_passed.append(
                    _Stage1Candidate(
                        candidate=candidate,
                        result=stage1,
                        cheap_score=_stage1_cheap_score(stage1),
                    )
                )
            finally:
                if progress_callback is not None:
                    progress_callback(1)

        if config.stage_mode == "stage1":
            batch_index += 1
            continue

        rung1_items = _select_rung_promotions(
            [_RungCandidate(item) for item in stage1_passed],
            fraction=_RUNG1_FRACTION,
            minimum=3,
            score_getter=lambda item: item.stage1.cheap_score,
        )
        _append_rung_rows(
            output,
            batch_index,
            0,
            [_RungCandidate(item) for item in stage1_passed],
            rung1_items,
        )

        rung1_scored: list[_RungCandidate] = []
        first_proxy_window = _proxy_windows(config.windows)[:1]
        for item in rung1_items:
            behavior = item.stage1.result.behavior
            if behavior is None:
                continue
            score = evaluate_stage_scores(
                candidate=item.stage1.candidate,
                behavior=behavior,
                windows=first_proxy_window,
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=10.0 if archive.occupied_cells == 0 else 0.0,
            )
            _append_stage_score(output / "stage2_proxy.csv", score, config.windows)
            archive.consider(score.candidate, behavior, score.score)
            rung1_scored.append(_RungCandidate(item.stage1, score))
            evaluated_for_model.append(
                _EvaluatedCandidate(
                    candidate=score.candidate,
                    robust_score=score.score.robust_score,
                    promoted_to_stage3=False,
                )
            )

        rung2_items = _select_rung_promotions(
            rung1_scored,
            fraction=_RUNG2_FRACTION,
            minimum=2,
            score_getter=_score_or_penalty,
        )
        _append_rung_rows(output, batch_index, 1, rung1_scored, rung2_items)

        rung2_scored: list[_RungCandidate] = []
        proxy_windows = _proxy_windows(config.windows)
        for item in rung2_items:
            behavior = item.stage1.result.behavior
            if behavior is None:
                continue
            score = evaluate_stage_scores(
                candidate=item.stage1.candidate,
                behavior=behavior,
                windows=proxy_windows,
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=0.0,
            )
            _append_stage_score(output / "stage2_proxy.csv", score, config.windows)
            archive.consider(score.candidate, behavior, score.score)
            rung2_scored.append(_RungCandidate(item.stage1, score))
            evaluated_for_model.append(
                _EvaluatedCandidate(
                    candidate=score.candidate,
                    robust_score=score.score.robust_score,
                    promoted_to_stage3=False,
                )
            )

        rung3_items = _select_rung_promotions(
            rung2_scored,
            fraction=_RUNG3_FRACTION,
            minimum=1,
            score_getter=_score_or_penalty,
        )
        _append_rung_rows(output, batch_index, 2, rung2_scored, rung3_items)

        for item in rung3_items:
            behavior = item.stage1.result.behavior
            if behavior is None:
                continue
            full = evaluate_stage_scores(
                candidate=item.stage1.candidate,
                behavior=behavior,
                windows=config.windows,
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=0.0,
            )
            _append_stage_score(output / "stage3_full_scores.csv", full, config.windows)
            _append_score_history(output / "score_history.csv", full)
            archive.consider(full.candidate, behavior, full.score)
            completed_stage3.add(full.candidate.candidate_id)
            stage2_survivors += 1
            stage3_evaluations += 1
            evaluated_for_model.append(
                _EvaluatedCandidate(
                    candidate=full.candidate,
                    robust_score=full.score.robust_score,
                    promoted_to_stage3=True,
                )
            )

        model.update(evaluated_for_model)
        batch_index += 1

    _write_model_summary(output / "hyperband_qd_state.csv", model)
    stage1_ranked = write_stage1_ranked(output, config)
    if config.stage_mode == "stage1":
        exported = export_stage1_candidates(stage1_ranked, output, config)
    else:
        _write_archive(output, archive)
        exported = export_stage4_candidates(archive, config)
    _write_summary(
        output=output,
        config=config,
        generated=generated,
        stage1_survivors=stage1_survivors,
        stage2_survivors=stage2_survivors,
        stage3_evaluations=stage3_evaluations,
        exported=exported,
        archive=archive,
        stage1_ranked=len(stage1_ranked),
    )
    return DSSV2Result(
        output=output,
        generated=generated,
        stage1_survivors=stage1_survivors,
        stage2_survivors=stage2_survivors,
        stage3_evaluations=stage3_evaluations,
        exported_candidates=exported,
        archive=archive,
    )


def _select_rung_promotions(
    candidates: list[_RungCandidate],
    *,
    fraction: float,
    minimum: int,
    score_getter: Callable[[_RungCandidate], float],
) -> list[_RungCandidate]:
    """Promote a capped, behavior-diverse slice to the next budget rung."""
    if not candidates:
        return []
    budget = max(minimum, int(len(candidates) * fraction))
    budget = min(budget, len(candidates))
    ranked = sorted(candidates, key=score_getter, reverse=True)
    selected: list[_RungCandidate] = []
    selected_ids: set[str] = set()
    seen_cells: set[tuple[str, str, str, str, str]] = set()

    for item in ranked:
        behavior = item.stage1.result.behavior
        if behavior is None or behavior.cell_key in seen_cells:
            continue
        selected.append(item)
        selected_ids.add(item.stage1.candidate.candidate_id)
        seen_cells.add(behavior.cell_key)
        if len(selected) >= budget:
            return selected

    for item in ranked:
        candidate_id = item.stage1.candidate.candidate_id
        if candidate_id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= budget:
            return selected
    return selected


def _score_or_penalty(item: _RungCandidate) -> float:
    if item.score is None:
        return -10_000.0
    return item.score.score.robust_score


def _append_rung_rows(
    output: Path,
    batch_index: int,
    rung: int,
    candidates: list[_RungCandidate],
    promoted: list[_RungCandidate],
) -> None:
    promoted_ids = {item.stage1.candidate.candidate_id for item in promoted}
    for item in candidates:
        _append_csv_row(
            output / "hyperband_rungs.csv",
            {
                "batch": batch_index,
                "rung": rung,
                "candidate_id": item.stage1.candidate.candidate_id,
                "trigger_name": item.stage1.candidate.trigger_name,
                "filter_names": "+".join(item.stage1.candidate.filter_names),
                "behavior_cell": (
                    item.stage1.result.behavior.to_label()
                    if item.stage1.result.behavior is not None
                    else ""
                ),
                "score": _score_or_penalty(item),
                "promoted": item.stage1.candidate.candidate_id in promoted_ids,
            },
        )
