"""Islanded window-specialist quality-diversity DSS backend."""

from __future__ import annotations

from collections.abc import Callable

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.catcma_qd import (
    _NOVELTY_MUTATION_INTERVAL,
    _directional_cheap_score,
    _EvaluatedCandidate,
    _mutate_candidate,
    _WeightedModel,
    _write_model_summary,
)
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import DSSCandidate, DSSConfig, DSSSearchSpace
from backtester.strategy_discovery.dss_directional_search import (
    DSSDirectionalResult,
    _count_csv_rows,
    _count_directional_survivors,
    _evaluate_directional_candidate,
    _guard_output_dir,
    _read_candidate_rows,
    _read_directional_candidate_ids,
    _refresh_directional_reports,
    _write_state,
    _write_summary,
)
from backtester.strategy_discovery.dss_runtime import (
    DSSSearchRuntime,
    should_use_random_injection,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_POPULATION_SIZE = 48


def run_island_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSDirectionalResult:
    """Run window-specialist islands and keep DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    model_by_window = {
        window.label: _WeightedModel(search_space, seed=config.seed + idx * 997)
        for idx, window in enumerate(config.windows)
    }
    composer = SignalComposer()
    archive = DSSArchive()
    existing_candidates = _read_candidate_rows(output / "candidates.jsonl")
    generated = len(existing_candidates)
    attempted = len(existing_candidates)
    viability_path = output / "directional_viability.csv"
    evaluated_ids = _read_directional_candidate_ids(viability_path)
    evaluated_count = _count_csv_rows(viability_path)
    novelty_parents: list[DSSCandidate] = []
    if evaluated_count and progress_callback is not None:
        progress_callback(evaluated_count)
    directional_survivors = _count_directional_survivors(viability_path)
    batch_index = generated // _POPULATION_SIZE

    with DSSSearchRuntime(config=config) as runtime:
        for candidate in existing_candidates:
            runtime.record_candidate(candidate, source="resume")

        pending_candidates = [
            candidate
            for candidate in existing_candidates
            if candidate.candidate_id not in evaluated_ids
        ]
        for candidate in pending_candidates:
            if not runtime.should_continue(evaluated_count):
                break
            directional = _evaluate_directional_candidate(
                output=output,
                candidate=candidate,
                window_data=window_data,
                config=config,
                composer=composer,
                runtime=runtime,
                append_candidate=False,
            )
            evaluated_count += 1
            if directional.should_promote:
                directional_survivors += 1
                novelty_parents.append(candidate)
                evaluated_item = _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=_directional_cheap_score(directional),
                )
                for model in model_by_window.values():
                    model.update([evaluated_item])
            runtime.write_progress(generated=generated, evaluated=evaluated_count)
            if progress_callback is not None:
                progress_callback(1)

        while runtime.should_continue(evaluated_count):
            target = config.windows[batch_index % len(config.windows)]
            model = model_by_window[target.label]
            batch_size = runtime.remaining_batch(evaluated_count, _POPULATION_SIZE)
            evaluated_before_batch = evaluated_count
            evaluated: list[_EvaluatedCandidate] = []

            for _ in range(batch_size):
                attempted += 1
                if attempted % _NOVELTY_MUTATION_INTERVAL == 0 and novelty_parents:
                    source = "novelty_mutation"
                    candidate = _mutate_candidate(
                        novelty_parents[-1],
                        search_space,
                        candidate_id=f"island_{target.label}_{attempted:06d}",
                        generation=batch_index,
                        seed=config.seed + attempted,
                    )
                else:
                    source = (
                        "random_unseen" if should_use_random_injection(attempted) else "island_qd"
                    )
                    candidate = model.sample(
                        f"island_{target.label}_{attempted:06d}",
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
                        append_candidate=True,
                    )
                    evaluated_count += 1
                    if not directional.should_promote:
                        continue
                    directional_survivors += 1
                    novelty_parents.append(candidate)
                    evaluated.append(
                        _EvaluatedCandidate(
                            candidate=candidate,
                            robust_score=_directional_cheap_score(directional),
                        )
                    )
                finally:
                    runtime.write_progress(generated=generated, evaluated=evaluated_count)
                    if progress_callback is not None:
                        progress_callback(1)

            if evaluated_count == evaluated_before_batch:
                runtime.write_progress(generated=generated, evaluated=evaluated_count)
                break
            model.update(evaluated)
            batch_index += 1
            if config.n_trials is None:
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated_count,
                )

        for label, model in model_by_window.items():
            _write_model_summary(output / "backend_state" / f"island_qd_state_{label}.csv", model)
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
