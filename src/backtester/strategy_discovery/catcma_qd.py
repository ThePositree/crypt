"""Experimental CatCMA-inspired quality-diversity DSS backend."""

from __future__ import annotations

import csv
import random
from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    FloatParam,
    IntParam,
    ParamDef,
    ParamValue,
)
from backtester.strategy_discovery.dss_stage1 import stage1_advisory_score
from backtester.strategy_discovery.dss_v2 import (
    DSSV2Result,
    Stage1Result,
    _append_jsonl,
    _append_score_history,
    _append_stage1,
    _append_stage_score,
    _guard_output_dir,
    _proxy_windows,
    _read_completed_ids,
    _read_stage0_candidates,
    _should_promote_to_stage3,
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

_PARAM_FLOOR = 0.03
_ELITE_FRACTION = 0.25
_DEFAULT_POPULATION_SIZE = 48
_STAGE2_BATCH_FRACTION = 0.12
_T = TypeVar("_T", bound=Hashable)


@dataclass(frozen=True, slots=True)
class _EvaluatedCandidate:
    candidate: DSSCandidate
    robust_score: float
    promoted_to_stage3: bool


@dataclass(frozen=True, slots=True)
class _Stage1Candidate:
    candidate: DSSCandidate
    result: Stage1Result
    cheap_score: float


class _WeightedModel:
    """Small mixed-variable distribution model inspired by CatCMAwM."""

    def __init__(self, search_space: DSSSearchSpace, *, seed: int) -> None:
        self._search_space = search_space
        self._rng = random.Random(seed)
        self._trigger_weights = _uniform_weights(search_space.trigger_names)
        self._filter_weights = _uniform_weights(search_space.filter_names)
        self._depth_weights = _uniform_weights(tuple(range(search_space.max_filters + 1)))
        self._param_weights: dict[tuple[str, str, str], dict[Hashable, float]] = {}
        self._init_param_weights("trigger", search_space.trigger_param_bounds)
        self._init_param_weights("filter", search_space.filter_param_bounds)

    def sample(self, candidate_id: str, *, generation: int) -> DSSCandidate:
        trigger = str(_weighted_choice(self._trigger_weights, self._rng))
        depth = int(_weighted_choice(self._depth_weights, self._rng))
        depth = min(depth, self._search_space.max_filters, len(self._search_space.filter_names))
        filters = tuple(sorted(self._sample_filters(depth)))
        return DSSCandidate(
            candidate_id=candidate_id,
            trigger_name=trigger,
            trigger_params=self._sample_param_group("trigger", trigger),
            filter_names=filters,
            filter_params={name: self._sample_param_group("filter", name) for name in filters},
            generation=generation,
        )

    def update(self, evaluated: list[_EvaluatedCandidate]) -> None:
        if not evaluated:
            return
        ranked = sorted(evaluated, key=lambda item: item.robust_score, reverse=True)
        elite_count = max(1, int(len(ranked) * _ELITE_FRACTION))
        elites = ranked[:elite_count]
        self._trigger_weights = _update_weights(
            self._trigger_weights,
            [elite.candidate.trigger_name for elite in elites],
        )
        self._filter_weights = _update_weights(
            self._filter_weights,
            [filter_name for elite in elites for filter_name in elite.candidate.filter_names],
        )
        self._depth_weights = _update_weights(
            self._depth_weights,
            [len(elite.candidate.filter_names) for elite in elites],
        )
        for elite in elites:
            self._update_param_group(
                "trigger", elite.candidate.trigger_name, elite.candidate.trigger_params
            )
            for filter_name, params in elite.candidate.filter_params.items():
                self._update_param_group("filter", filter_name, params)

    def _init_param_weights(
        self,
        namespace: str,
        bounds: dict[str, dict[str, ParamDef]],
    ) -> None:
        for owner, params in bounds.items():
            for param_name, param_def in params.items():
                self._param_weights[(namespace, owner, param_name)] = _uniform_weights(
                    tuple(_param_choices(param_def))
                )

    def _sample_filters(self, depth: int) -> list[str]:
        selected: list[str] = []
        available = dict(self._filter_weights)
        for _ in range(depth):
            if not available:
                break
            picked = str(_weighted_choice(available, self._rng))
            selected.append(picked)
            available.pop(picked, None)
        return selected

    def _sample_param_group(self, namespace: str, owner: str) -> dict[str, ParamValue]:
        out: dict[str, ParamValue] = {}
        bounds = (
            self._search_space.trigger_param_bounds
            if namespace == "trigger"
            else self._search_space.filter_param_bounds
        )
        for param_name in bounds.get(owner, {}):
            value = _weighted_choice(self._param_weights[(namespace, owner, param_name)], self._rng)
            if not isinstance(value, (str, int, float)):
                raise TypeError(f"Unsupported sampled parameter value: {value!r}")
            out[param_name] = value
        return out

    def _update_param_group(
        self,
        namespace: str,
        owner: str,
        params: dict[str, ParamValue],
    ) -> None:
        for param_name, value in params.items():
            key = (namespace, owner, param_name)
            if key in self._param_weights:
                self._param_weights[key] = _update_weights(self._param_weights[key], [value])


def run_catcma_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSV2Result:
    """Run the experimental CatCMA-QD backend with DSS-compatible artifacts."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_stage3 = _read_completed_ids(output / "stage3_full_scores.csv")
    existing_stage0 = _read_stage0_candidates(output / "stage0_candidates.jsonl")
    model = _WeightedModel(search_space, seed=config.seed)
    composer = SignalComposer()
    archive = DSSArchive()
    stage1_survivors = 0
    stage2_survivors = 0
    stage3_evaluations = 0
    generated = min(len(existing_stage0), config.n_trials)
    if generated and progress_callback is not None:
        progress_callback(generated)
    generation = generated // _DEFAULT_POPULATION_SIZE

    while generated < config.n_trials:
        batch_size = min(_DEFAULT_POPULATION_SIZE, config.n_trials - generated)
        stage1_passed: list[_Stage1Candidate] = []
        evaluated: list[_EvaluatedCandidate] = []
        for _ in range(batch_size):
            generated += 1
            candidate = model.sample(f"catcma_{generated:06d}", generation=generation)
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
            generation += 1
            continue

        stage2_candidates = _select_stage2_candidates(stage1_passed, batch_size=batch_size)
        for item in stage2_candidates:
            if item.result.behavior is None:
                continue
            candidate = item.candidate
            stage2 = evaluate_stage_scores(
                candidate=candidate,
                behavior=item.result.behavior,
                windows=_proxy_windows(config.windows),
                window_data=window_data,
                config=config,
                composer=composer,
                novelty_bonus=10.0 if archive.occupied_cells == 0 else 0.0,
            )
            _append_stage_score(output / "stage2_proxy.csv", stage2, config.windows)
            archive.consider(stage2.candidate, stage2.behavior, stage2.score)
            evaluated.append(
                _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=stage2.score.robust_score,
                    promoted_to_stage3=False,
                )
            )

            if not _should_promote_to_stage3(stage2, archive, config):
                continue
            stage2_survivors += 1

            stage3 = evaluate_stage_scores(
                candidate=candidate,
                behavior=item.result.behavior,
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
            evaluated.append(
                _EvaluatedCandidate(
                    candidate=candidate,
                    robust_score=stage3.score.robust_score,
                    promoted_to_stage3=True,
                )
            )
        model.update(evaluated)
        generation += 1

    _write_model_summary(output / "catcma_qd_state.csv", model)
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


def _select_stage2_candidates(
    candidates: list[_Stage1Candidate],
    *,
    batch_size: int,
) -> list[_Stage1Candidate]:
    if not candidates:
        return []
    budget = max(3, int(batch_size * _STAGE2_BATCH_FRACTION))
    budget = min(budget, len(candidates))
    ranked = sorted(candidates, key=lambda item: item.cheap_score, reverse=True)
    selected: list[_Stage1Candidate] = []
    seen_cells: set[tuple[str, str, str, str, str]] = set()

    for item in ranked:
        behavior = item.result.behavior
        if behavior is None or behavior.cell_key in seen_cells:
            continue
        selected.append(item)
        seen_cells.add(behavior.cell_key)
        if len(selected) >= budget:
            return selected

    selected_ids = {item.candidate.candidate_id for item in selected}
    for item in ranked:
        if item.candidate.candidate_id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= budget:
            return selected
    return selected


def _stage1_cheap_score(result: Stage1Result) -> float:
    if result.advisory_score is not None:
        return result.advisory_score
    return stage1_advisory_score(result)


def _write_model_summary(path: Path, model: _WeightedModel) -> None:
    rows: list[dict[str, object]] = []
    _extend_weight_rows(rows, "trigger", model._trigger_weights)
    _extend_weight_rows(rows, "filter", model._filter_weights)
    _extend_weight_rows(rows, "depth", model._depth_weights)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["namespace", "value", "weight"])
        writer.writeheader()
        writer.writerows(rows)


def _extend_weight_rows(
    rows: list[dict[str, object]],
    namespace: str,
    weights: Mapping[_T, float],
) -> None:
    for value, weight in weights.items():
        rows.append({"namespace": namespace, "value": value, "weight": weight})


def _uniform_weights(values: tuple[_T, ...]) -> dict[_T, float]:
    if not values:
        return {}
    weight = 1.0 / len(values)
    return dict.fromkeys(values, weight)


def _update_weights(
    current: dict[_T, float],
    observed: list[_T],
) -> dict[_T, float]:
    if not current or not observed:
        return current
    counts = dict.fromkeys(current, _PARAM_FLOOR)
    for value in observed:
        if value in counts:
            counts[value] += 1.0
    total = sum(counts.values())
    return {key: value / total for key, value in counts.items()}


def _weighted_choice(weights: dict[_T, float], rng: random.Random) -> _T:
    if not weights:
        raise ValueError("Cannot sample from empty weights")
    items = list(weights.items())
    total = sum(weight for _, weight in items)
    threshold = rng.random() * total
    cumulative = 0.0
    for value, weight in items:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return items[-1][0]


def _float_grid(spec: tuple[float, float, float]) -> tuple[float, ...]:
    low, high, step = spec
    values: list[float] = []
    current = low
    while current <= high + step / 10:
        values.append(round(current, 6))
        current += step
    return tuple(values)


def _int_grid(spec: tuple[int, int, int]) -> tuple[int, ...]:
    low, high, step = spec
    return tuple(range(low, high + 1, step))


def _param_choices(param_def: ParamDef) -> list[Hashable]:
    if isinstance(param_def, IntParam):
        return list(_int_grid((param_def.low, param_def.high, param_def.step)))
    if isinstance(param_def, FloatParam):
        if param_def.step is None:
            return [
                round(param_def.low + (param_def.high - param_def.low) * i / 4, 6) for i in range(5)
            ]
        return list(_float_grid((param_def.low, param_def.high, param_def.step)))
    if isinstance(param_def, CategoricalParam):
        return list(param_def.choices)
    raise TypeError(f"Unsupported param definition: {param_def!r}")
