"""Islanded window-specialist quality-diversity DSS backend."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.catcma_qd import (
    _EvaluatedCandidate,
    _select_stage2_candidates,
    _stage1_cheap_score,
    _Stage1Candidate,
    _WeightedModel,
    _write_model_summary,
)
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import DSSConfig, DSSSearchSpace, DSSWindowSpec
from backtester.strategy_discovery.dss_v2 import (
    DSSV2Result,
    StageScoreResult,
    _append_csv_row,
    _append_jsonl,
    _append_score_history,
    _append_stage1,
    _append_stage_score,
    _guard_output_dir,
    _read_completed_ids,
    _read_stage0_candidates,
    _write_archive,
    _write_state,
    _write_summary,
    evaluate_stage1,
    evaluate_stage_scores,
    export_stage4_candidates,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_POPULATION_SIZE = 48
_SPECIALIST_STAGE3_THRESHOLD = -250.0
_ROBUST_CHECK_EVERY_BATCHES = 8


def run_island_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSV2Result:
    """Run window-specialist islands and keep DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_stage3 = _read_completed_ids(output / "stage3_full_scores.csv")
    existing_stage0 = _read_stage0_candidates(output / "stage0_candidates.jsonl")
    model_by_window = {
        window.label: _WeightedModel(search_space, seed=config.seed + idx * 997)
        for idx, window in enumerate(config.windows)
    }
    composer = SignalComposer()
    archive = DSSArchive()
    generated = min(len(existing_stage0), config.n_trials)
    if generated and progress_callback is not None:
        progress_callback(generated)
    stage1_survivors = 0
    stage2_survivors = 0
    stage3_evaluations = 0
    batch_index = generated // _POPULATION_SIZE

    while generated < config.n_trials:
        target = config.windows[batch_index % len(config.windows)]
        model = model_by_window[target.label]
        batch_size = min(_POPULATION_SIZE, config.n_trials - generated)
        stage1_passed: list[_Stage1Candidate] = []
        evaluated: list[_EvaluatedCandidate] = []

        for _ in range(batch_size):
            generated += 1
            candidate = model.sample(
                f"island_{target.label}_{generated:06d}",
                generation=batch_index,
            )
            try:
                _append_jsonl(output / "stage0_candidates.jsonl", candidate.to_dict())
                if candidate.candidate_id in completed_stage3:
                    continue
                stage1 = evaluate_stage1(candidate, window_data, config, composer)
                _append_stage1(output, candidate, stage1, config.windows)
                if not stage1.passed or stage1.behavior is None:
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

        stage2_candidates = _select_stage2_candidates(stage1_passed, batch_size=batch_size)
        for item in stage2_candidates:
            if item.result.behavior is None:
                continue
            candidate = item.candidate
            specialist = evaluate_stage_scores(
                candidate=candidate,
                behavior=item.result.behavior,
                windows=[target],
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=10.0 if archive.occupied_cells == 0 else 0.0,
            )
            _append_stage_score(output / "stage2_proxy.csv", specialist, config.windows)
            _append_island_score(output, target, specialist)
            archive.consider(specialist.candidate, item.result.behavior, specialist.score)
            evaluated.append(
                _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=specialist.score.robust_score,
                    promoted_to_stage3=False,
                )
            )

            should_robust_check = (
                specialist.score.robust_score >= _SPECIALIST_STAGE3_THRESHOLD
                or batch_index % _ROBUST_CHECK_EVERY_BATCHES == 0
            )
            if not should_robust_check:
                continue
            robust = evaluate_stage_scores(
                candidate=candidate,
                behavior=item.result.behavior,
                windows=config.windows,
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=0.0,
            )
            _append_stage_score(output / "stage3_full_scores.csv", robust, config.windows)
            _append_score_history(output / "score_history.csv", robust)
            archive.consider(robust.candidate, item.result.behavior, robust.score)
            completed_stage3.add(candidate.candidate_id)
            stage2_survivors += 1
            stage3_evaluations += 1
            evaluated.append(
                _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=robust.score.robust_score,
                    promoted_to_stage3=True,
                )
            )
        model.update(evaluated)
        batch_index += 1

    _write_archive(output, archive)
    for label, model in model_by_window.items():
        _write_model_summary(output / f"island_qd_state_{label}.csv", model)
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


def _append_island_score(output: Path, target: DSSWindowSpec, result: StageScoreResult) -> None:
    _append_csv_row(
        output / "island_scores.csv",
        {
            "candidate_id": result.candidate.candidate_id,
            "target_window": target.label,
            "trigger_name": result.candidate.trigger_name,
            "filter_names": "+".join(result.candidate.filter_names),
            "robust_score": result.score.robust_score,
            "target_score": result.score.window_scores.get(target.label, ""),
            "target_trades": result.score.trades_by_window.get(target.label, ""),
            "rrr": result.candidate.rrr,
            "risk_percent": result.candidate.risk_percent,
            "position_ttl_bars": result.candidate.position_ttl_bars,
            "atr_sl_mult": result.candidate.atr_sl_mult,
        },
    )
