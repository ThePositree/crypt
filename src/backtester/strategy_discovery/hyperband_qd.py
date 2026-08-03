"""Hyperband-style quality-diversity DSS backend."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.catcma_qd import (
    _NOVELTY_MUTATION_INTERVAL,
    _directional_feedback_score,
    _DirectionalCandidate,
    _EvaluatedCandidate,
    _mutate_candidate,
    _WeightedModel,
    _write_model_summary,
)
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import DSSConfig, DSSSearchSpace
from backtester.strategy_discovery.dss_directional_search import (
    DSSDirectionalResult,
    DSSSignalNoveltyTracker,
    _append_csv_row,
    _count_csv_rows,
    _count_directional_survivors,
    _evaluate_directional_candidate,
    _guard_output_dir,
    _is_novel_directional,
    _read_candidate_rows,
    _read_directional_candidate_ids,
    _refresh_directional_reports,
    _write_state,
    _write_summary,
    sample_random_directional_candidate,
)
from backtester.strategy_discovery.dss_runtime import (
    DSSSearchRuntime,
    should_use_random_injection,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_POPULATION_SIZE = 64
_RUNG1_FRACTION = 0.30


class _RungCandidate:
    def __init__(self, directional: _DirectionalCandidate) -> None:
        self.directional = directional


def run_hyperband_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSDirectionalResult:
    """Run a successive-halving QD backend with DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    model = _WeightedModel(search_space, seed=config.seed)
    composer = SignalComposer()
    archive = DSSArchive()
    existing_candidates = _read_candidate_rows(output / "candidates.jsonl")
    generated = len(existing_candidates)
    attempted = len(existing_candidates)
    viability_path = output / "directional_viability.csv"
    evaluated_ids = _read_directional_candidate_ids(viability_path)
    signal_novelty = DSSSignalNoveltyTracker(viability_path)
    evaluated_count = _count_csv_rows(viability_path)
    novelty_parents: list[_DirectionalCandidate] = []
    if evaluated_count and progress_callback is not None:
        progress_callback(evaluated_count)
    batch_index = generated // _POPULATION_SIZE
    directional_survivors = _count_directional_survivors(viability_path)

    with DSSSearchRuntime(config=config) as runtime:
        for candidate in existing_candidates:
            runtime.record_candidate(candidate, source="resume")

        pending_evaluated: list[_EvaluatedCandidate] = []
        for candidate in (
            item for item in existing_candidates if item.candidate_id not in evaluated_ids
        ):
            if not runtime.should_continue(evaluated_count):
                break
            directional = _evaluate_directional_candidate(
                output=output,
                candidate=candidate,
                window_data=window_data,
                config=config,
                composer=composer,
                runtime=runtime,
                signal_novelty=signal_novelty,
                append_candidate=False,
            )
            evaluated_count += 1
            is_novel_signal = _is_novel_directional(directional)
            directional_item = _DirectionalCandidate(
                candidate=candidate,
                result=directional,
                cheap_score=_directional_feedback_score(directional, is_novel_signal),
            )
            pending_evaluated.append(
                _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=directional_item.cheap_score,
                )
            )
            if directional.should_promote and is_novel_signal:
                directional_survivors += 1
                novelty_parents.append(directional_item)
            runtime.write_progress(generated=generated, evaluated=evaluated_count)
            if progress_callback is not None:
                progress_callback(1)
        model.update(pending_evaluated)

        while runtime.should_continue(evaluated_count):
            batch_size = runtime.remaining_batch(evaluated_count, _POPULATION_SIZE)
            evaluated_before_batch = evaluated_count
            directional_passed: list[_DirectionalCandidate] = []
            evaluated_for_model: list[_EvaluatedCandidate] = []

            for _ in range(batch_size):
                attempted += 1
                if attempted % _NOVELTY_MUTATION_INTERVAL == 0 and novelty_parents:
                    source = "novelty_mutation"
                    candidate = _mutate_candidate(
                        novelty_parents[-1].candidate,
                        search_space,
                        candidate_id=f"hyperband_{attempted:06d}",
                        generation=batch_index,
                        seed=config.seed + attempted,
                    )
                else:
                    source = (
                        "random_unseen"
                        if should_use_random_injection(attempted)
                        else "hyperband_qd"
                    )
                    if source == "random_unseen":
                        candidate = sample_random_directional_candidate(
                            search_space=search_space,
                            candidate_id=f"hyperband_{attempted:06d}",
                            generation=batch_index,
                            max_filters=config.max_filters,
                            seed=config.seed + attempted * 1009,
                        )
                    else:
                        candidate = model.sample(
                            f"hyperband_{attempted:06d}",
                            generation=batch_index,
                        )
                if not runtime.record_candidate(candidate, source=source):
                    runtime.write_progress(generated=generated, evaluated=evaluated_count)
                    continue
                generated += 1
                try:
                    directional = _evaluate_directional_candidate(
                        output=output,
                        candidate=candidate,
                        window_data=window_data,
                        config=config,
                        composer=composer,
                        runtime=runtime,
                        signal_novelty=signal_novelty,
                        append_candidate=True,
                    )
                    evaluated_count += 1
                    is_novel_signal = _is_novel_directional(directional)
                    directional_item = _DirectionalCandidate(
                        candidate=candidate,
                        result=directional,
                        cheap_score=_directional_feedback_score(directional, is_novel_signal),
                    )
                    evaluated_for_model.append(
                        _EvaluatedCandidate(
                            candidate=candidate,
                            robust_score=directional_item.cheap_score,
                        )
                    )
                    if not directional.should_promote or not is_novel_signal:
                        continue
                    directional_survivors += 1
                    directional_passed.append(directional_item)
                    novelty_parents.append(directional_item)
                finally:
                    runtime.write_progress(generated=generated, evaluated=evaluated_count)
                    if progress_callback is not None:
                        progress_callback(1)

            if evaluated_count == evaluated_before_batch:
                runtime.write_progress(generated=generated, evaluated=evaluated_count)
                break
            rung1_items = _select_rung_promotions(
                [_RungCandidate(item) for item in directional_passed],
                fraction=_RUNG1_FRACTION,
                minimum=3,
                score_getter=lambda item: item.directional.cheap_score,
            )
            _append_rung_rows(
                output,
                batch_index,
                0,
                [_RungCandidate(item) for item in directional_passed],
                rung1_items,
            )

            model.update(evaluated_for_model)
            batch_index += 1
            if config.n_trials is None:
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated_count,
                )

        _write_model_summary(output / "backend_state" / "hyperband_qd_state.csv", model)
        directional_ranked, exported = _refresh_directional_reports(
            output=output,
            config=config,
            runtime=runtime,
            generated=generated,
            evaluated=evaluated_count,
        )
    _write_summary(
        output=output,
        config=config,
        generated=generated,
        directional_survivors=directional_survivors,
        exported=exported,
        archive=archive,
        directional_ranked=len(directional_ranked),
    )
    return DSSDirectionalResult(
        output=output,
        generated=generated,
        directional_survivors=directional_survivors,
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
        behavior = item.directional.result.behavior
        if behavior is None or behavior.cell_key in seen_cells:
            continue
        selected.append(item)
        selected_ids.add(item.directional.candidate.candidate_id)
        seen_cells.add(behavior.cell_key)
        if len(selected) >= budget:
            return selected

    for item in ranked:
        candidate_id = item.directional.candidate.candidate_id
        if candidate_id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= budget:
            return selected
    return selected


def _score_or_penalty(item: _RungCandidate) -> float:
    return item.directional.cheap_score


def _append_rung_rows(
    output: Path,
    batch_index: int,
    rung: int,
    candidates: list[_RungCandidate],
    promoted: list[_RungCandidate],
) -> None:
    promoted_ids = {item.directional.candidate.candidate_id for item in promoted}
    for item in candidates:
        _append_csv_row(
            output / "hyperband_rungs.csv",
            {
                "batch": batch_index,
                "rung": rung,
                "candidate_id": item.directional.candidate.candidate_id,
                "trigger_name": item.directional.candidate.trigger_name,
                "filter_names": "+".join(item.directional.candidate.filter_names),
                "behavior_cell": (
                    item.directional.result.behavior.to_label()
                    if item.directional.result.behavior is not None
                    else ""
                ),
                "score": _score_or_penalty(item),
                "promoted": item.directional.candidate.candidate_id in promoted_ids,
            },
        )
