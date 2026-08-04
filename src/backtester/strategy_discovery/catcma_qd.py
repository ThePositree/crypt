"""CatCMAwM quality-diversity DSS backend."""

from __future__ import annotations

import csv
import random
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from cmaes import CatCMAwM

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
from backtester.strategy_discovery.dss_directional import directional_advisory_score
from backtester.strategy_discovery.dss_directional_search import (
    DirectionalResult,
    DSSDirectionalResult,
    DSSSignalNoveltyTracker,
    _count_csv_rows,
    _count_directional_survivors,
    _evaluate_directional_candidate,
    _guard_output_dir,
    _instance_base_name,
    _instance_timeframe,
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

_DEFAULT_POPULATION_SIZE = 48
_STAGE2_BATCH_FRACTION = 0.12
_NOVELTY_MUTATION_INTERVAL = 10
_DUPLICATE_SIGNAL_FEEDBACK_SCORE = -10_000.0


@dataclass(frozen=True, slots=True)
class _EvaluatedCandidate:
    candidate: DSSCandidate
    robust_score: float


@dataclass(frozen=True, slots=True)
class _DirectionalCandidate:
    candidate: DSSCandidate
    result: DirectionalResult
    cheap_score: float


@dataclass(frozen=True, slots=True)
class _CategoricalSlot:
    namespace: str
    owner: str
    name: str
    choices: tuple[Hashable, ...]


@dataclass(frozen=True, slots=True)
class _NumericSlot:
    namespace: str
    owner: str
    name: str
    choices: tuple[int | float, ...] | None
    low: float | None = None
    high: float | None = None


class _WeightedModel:
    """DSS candidate sampler backed by cmaes.CatCMAwM."""

    def __init__(self, search_space: DSSSearchSpace, *, seed: int) -> None:
        self._search_space = search_space
        self._seed = seed
        self._x_slots: list[_NumericSlot] = []
        self._z_slots: list[_NumericSlot] = []
        self._c_slots: list[_CategoricalSlot] = []
        self._asked: dict[str, Any] = {}
        self._feedback: list[tuple[Any, float]] = []
        self._tell_count = 0
        self._init_schema()
        self._optimizer = self._new_optimizer()

    @property
    def backend_name(self) -> str:
        return "cmaes.CatCMAwM"

    def sample(self, candidate_id: str, *, generation: int) -> DSSCandidate:
        solution = self._optimizer.ask()
        self._asked[candidate_id] = solution
        return self._decode_solution(candidate_id, solution, generation=generation)

    def update(self, evaluated: list[_EvaluatedCandidate]) -> None:
        if not evaluated:
            return
        for item in evaluated:
            solution = self._asked.pop(item.candidate.candidate_id, None)
            if solution is None:
                continue
            self._feedback.append((solution, -item.robust_score))

        while len(self._feedback) >= self._optimizer.population_size:
            batch = self._feedback[: self._optimizer.population_size]
            del self._feedback[: self._optimizer.population_size]
            self._optimizer.tell(batch)
            self._tell_count += 1
            if self._optimizer.should_stop():
                self._optimizer = self._new_optimizer(seed_offset=self._tell_count)
                self._feedback.clear()
                self._asked.clear()

    def _init_schema(self) -> None:
        trigger_choices: tuple[Hashable, ...] = tuple(self._search_space.trigger_names)
        if not trigger_choices:
            raise ValueError("CatCMAwM DSS search requires at least one trigger")
        if len(trigger_choices) >= 2:
            self._c_slots.append(_CategoricalSlot("structure", "", "trigger", trigger_choices))

        depth_choices: tuple[Hashable, ...] = tuple(range(self._search_space.max_filters + 1))
        if len(depth_choices) >= 2:
            self._c_slots.append(
                _CategoricalSlot(
                    "structure",
                    "",
                    "depth",
                    depth_choices,
                )
            )

        filter_choices: tuple[Hashable, ...] = ("", *self._search_space.filter_names)
        if len(filter_choices) >= 2:
            for slot_idx in range(self._search_space.max_filters):
                self._c_slots.append(
                    _CategoricalSlot("structure", "", f"filter_slot_{slot_idx}", filter_choices)
                )

        self._init_param_slots("trigger", self._search_space.trigger_param_bounds)
        self._init_param_slots("filter", self._search_space.filter_param_bounds)
        if not self._x_slots and not self._z_slots and not self._c_slots:
            self._c_slots.append(_CategoricalSlot("internal", "", "noop", (0, 1)))

    def _init_param_slots(
        self,
        namespace: str,
        bounds: dict[str, dict[str, ParamDef]],
    ) -> None:
        for owner, params in sorted(bounds.items()):
            for param_name, param_def in sorted(params.items()):
                if isinstance(param_def, CategoricalParam):
                    choices = tuple(param_def.choices)
                    if len(choices) >= 2:
                        self._c_slots.append(
                            _CategoricalSlot(
                                namespace,
                                owner,
                                param_name,
                                choices,
                            )
                        )
                elif isinstance(param_def, IntParam):
                    int_choices: tuple[int | float, ...] = tuple(
                        _int_grid((param_def.low, param_def.high, param_def.step))
                    )
                    if len(int_choices) >= 2:
                        self._z_slots.append(
                            _NumericSlot(
                                namespace,
                                owner,
                                param_name,
                                int_choices,
                            )
                        )
                elif isinstance(param_def, FloatParam) and param_def.step is not None:
                    float_choices: tuple[int | float, ...] = tuple(
                        _float_grid((param_def.low, param_def.high, param_def.step))
                    )
                    if len(float_choices) >= 2:
                        self._z_slots.append(
                            _NumericSlot(
                                namespace,
                                owner,
                                param_name,
                                float_choices,
                            )
                        )
                elif isinstance(param_def, FloatParam) and param_def.low != param_def.high:
                    self._x_slots.append(
                        _NumericSlot(
                            namespace,
                            owner,
                            param_name,
                            None,
                            low=param_def.low,
                            high=param_def.high,
                        )
                    )
                else:
                    raise TypeError(f"Unsupported param definition: {param_def!r}")

    def _new_optimizer(self, *, seed_offset: int = 0) -> CatCMAwM:
        x_space = [[slot.low, slot.high] for slot in self._x_slots]
        z_space = [list(slot.choices or ()) for slot in self._z_slots]
        c_space = [len(slot.choices) for slot in self._c_slots]
        return CatCMAwM(
            x_space=x_space or None,
            z_space=z_space or None,
            c_space=c_space or None,
            population_size=_DEFAULT_POPULATION_SIZE,
            seed=self._seed + seed_offset,
        )

    def _decode_solution(
        self,
        candidate_id: str,
        solution: Any,
        *,
        generation: int,
    ) -> DSSCandidate:
        c_values = self._categorical_values(solution)
        z_values = self._numeric_values(solution.z)
        x_values = self._numeric_values(solution.x)

        trigger = str(
            self._choice_from_c_values(
                c_values,
                namespace="structure",
                owner="",
                name="trigger",
                default=self._search_space.trigger_names[0],
            )
        )
        depth_value = self._choice_from_c_values(
            c_values,
            namespace="structure",
            owner="",
            name="depth",
            default=0,
        )
        if not isinstance(depth_value, (int, float)):
            raise TypeError(f"Unsupported CatCMAwM depth value: {depth_value!r}")
        depth = int(depth_value)
        selected_filters = self._decode_filter_slots(c_values)
        filters = tuple(sorted(selected_filters[:depth]))
        trigger_name = _instance_base_name(trigger)

        trigger_params: dict[str, ParamValue] = {}
        filter_params: dict[str, dict[str, ParamValue]] = {name: {} for name in filters}
        self._decode_params(
            c_values=c_values,
            z_values=z_values,
            x_values=x_values,
            trigger_name=trigger_name,
            filter_names=filters,
            trigger_params=trigger_params,
            filter_params=filter_params,
        )
        return DSSCandidate(
            candidate_id=candidate_id,
            trigger_name=trigger_name,
            trigger_timeframe=_instance_timeframe(trigger),
            trigger_params=trigger_params,
            filter_names=filters,
            filter_timeframes={
                name: _instance_timeframe(name)
                for name in filters
                if _instance_timeframe(name) != "H1"
            },
            filter_params=filter_params,
            generation=generation,
        )

    def _decode_filter_slots(self, c_values: dict[tuple[str, str, str], Hashable]) -> list[str]:
        selected: list[str] = []
        for slot_idx in range(self._search_space.max_filters):
            picked = str(
                self._choice_from_c_values(
                    c_values,
                    namespace="structure",
                    owner="",
                    name=f"filter_slot_{slot_idx}",
                    default="",
                )
            )
            if picked and picked not in selected:
                selected.append(picked)
        return selected

    def _decode_params(
        self,
        *,
        c_values: dict[tuple[str, str, str], Hashable],
        z_values: list[float],
        x_values: list[float],
        trigger_name: str,
        filter_names: tuple[str, ...],
        trigger_params: dict[str, ParamValue],
        filter_params: dict[str, dict[str, ParamValue]],
    ) -> None:
        active_filters = {_instance_base_name(name): name for name in filter_names}
        for c_slot in self._c_slots:
            if c_slot.namespace == "structure":
                continue
            value = c_values[(c_slot.namespace, c_slot.owner, c_slot.name)]
            self._assign_param(
                c_slot, value, trigger_name, active_filters, trigger_params, filter_params
            )
        for z_slot, value in zip(self._z_slots, z_values, strict=True):
            self._assign_param(
                z_slot, value, trigger_name, active_filters, trigger_params, filter_params
            )
        for x_slot, value in zip(self._x_slots, x_values, strict=True):
            self._assign_param(
                x_slot,
                round(value, 6),
                trigger_name,
                active_filters,
                trigger_params,
                filter_params,
            )
        self._assign_deterministic_params(
            trigger_name=trigger_name,
            active_filters=active_filters,
            trigger_params=trigger_params,
            filter_params=filter_params,
        )

    def _assign_param(
        self,
        slot: _CategoricalSlot | _NumericSlot,
        value: Hashable | float,
        trigger_name: str,
        active_filters: dict[str, str],
        trigger_params: dict[str, ParamValue],
        filter_params: dict[str, dict[str, ParamValue]],
    ) -> None:
        if not isinstance(value, (str, int, float)):
            raise TypeError(f"Unsupported CatCMAwM parameter value: {value!r}")
        if slot.namespace == "trigger" and slot.owner == trigger_name:
            trigger_params[slot.name] = value
        elif slot.namespace == "filter" and slot.owner in active_filters:
            filter_params.setdefault(active_filters[slot.owner], {})[slot.name] = value

    def _assign_deterministic_params(
        self,
        *,
        trigger_name: str,
        active_filters: dict[str, str],
        trigger_params: dict[str, ParamValue],
        filter_params: dict[str, dict[str, ParamValue]],
    ) -> None:
        self._assign_deterministic_param_group(
            self._search_space.trigger_param_bounds.get(trigger_name, {}),
            trigger_params,
        )
        for base_name, instance_name in active_filters.items():
            self._assign_deterministic_param_group(
                self._search_space.filter_param_bounds.get(base_name, {}),
                filter_params.setdefault(instance_name, {}),
            )

    def _assign_deterministic_param_group(
        self,
        bounds: dict[str, ParamDef],
        params: dict[str, ParamValue],
    ) -> None:
        for param_name, param_def in bounds.items():
            if param_name in params:
                continue
            choices = _param_choices(param_def)
            if len(choices) == 1:
                value = choices[0]
                if not isinstance(value, (str, int, float)):
                    raise TypeError(f"Unsupported CatCMAwM parameter value: {value!r}")
                params[param_name] = value

    def _categorical_values(self, solution: Any) -> dict[tuple[str, str, str], Hashable]:
        if solution.c is None:
            return {}
        out: dict[tuple[str, str, str], Hashable] = {}
        for row, slot in zip(solution.c, self._c_slots, strict=True):
            idx = int(np.asarray(row[: len(slot.choices)]).argmax())
            out[(slot.namespace, slot.owner, slot.name)] = slot.choices[idx]
        return out

    def _choice_from_c_values(
        self,
        c_values: dict[tuple[str, str, str], Hashable],
        *,
        namespace: str,
        owner: str,
        name: str,
        default: Hashable,
    ) -> Hashable:
        return c_values.get((namespace, owner, name), default)

    def _numeric_values(self, values: np.ndarray[Any, Any] | None) -> list[float]:
        if values is None:
            return []
        return [float(value) for value in values.tolist()]


def run_catcma_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSDirectionalResult:
    """Run the experimental CatCMA-QD backend with DSS-compatible artifacts."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    model = _WeightedModel(search_space, seed=config.seed)
    composer = SignalComposer()
    archive = DSSArchive()
    viability_path = output / "directional_viability.csv"
    evaluated_ids = _read_directional_candidate_ids(viability_path)
    signal_novelty = DSSSignalNoveltyTracker(viability_path)
    directional_survivors = _count_directional_survivors(viability_path)
    existing_candidates = _read_candidate_rows(output / "candidates.jsonl")
    generated = len(existing_candidates)
    attempted = len(existing_candidates)
    evaluated_count = _count_csv_rows(viability_path)
    novelty_parents: list[DSSCandidate] = []
    if evaluated_count and progress_callback is not None:
        progress_callback(evaluated_count)
    generation = generated // _DEFAULT_POPULATION_SIZE

    with DSSSearchRuntime(config=config) as runtime:
        for candidate in existing_candidates:
            runtime.record_candidate(candidate, source="resume")

        pending_candidates = [
            candidate
            for candidate in existing_candidates
            if candidate.candidate_id not in evaluated_ids
        ]
        pending_evaluated: list[_EvaluatedCandidate] = []
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
                signal_novelty=signal_novelty,
                append_candidate=False,
            )
            evaluated_count += 1
            if directional.should_promote:
                is_novel_signal = _is_novel_directional(directional)
                pending_evaluated.append(
                    _EvaluatedCandidate(
                        candidate=candidate,
                        robust_score=_directional_feedback_score(directional, is_novel_signal),
                    )
                )
                if is_novel_signal:
                    directional_survivors += 1
                    novelty_parents.append(candidate)
            runtime.write_progress(generated=generated, evaluated=evaluated_count)
            if progress_callback is not None:
                progress_callback(1)
        model.update(pending_evaluated)

        while runtime.should_continue(evaluated_count):
            batch_size = runtime.remaining_batch(evaluated_count, _DEFAULT_POPULATION_SIZE)
            evaluated_before_batch = evaluated_count
            directional_passed: list[_DirectionalCandidate] = []
            evaluated: list[_EvaluatedCandidate] = []
            for _ in range(batch_size):
                attempted += 1
                source = "catcma_qd"
                if attempted % _NOVELTY_MUTATION_INTERVAL == 0 and novelty_parents:
                    source = "novelty_mutation"
                    candidate = _mutate_candidate(
                        novelty_parents[-1],
                        search_space,
                        candidate_id=f"catcma_{attempted:06d}",
                        generation=generation,
                        seed=config.seed + attempted,
                    )
                else:
                    source = (
                        "random_unseen"
                        if should_use_random_injection(attempted)
                        else "catcma_qd"
                    )
                    if source == "random_unseen":
                        candidate = sample_random_directional_candidate(
                            search_space=search_space,
                            candidate_id=f"catcma_{attempted:06d}",
                            generation=generation,
                            max_filters=config.max_filters,
                            seed=config.seed + attempted * 1009,
                        )
                    else:
                        candidate = model.sample(f"catcma_{attempted:06d}", generation=generation)
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
                    feedback_score = _directional_feedback_score(directional, is_novel_signal)
                    if not directional.should_promote:
                        evaluated.append(
                            _EvaluatedCandidate(
                                candidate=candidate,
                                robust_score=feedback_score,
                            )
                        )
                        continue
                    evaluated.append(
                        _EvaluatedCandidate(
                            candidate=candidate,
                            robust_score=feedback_score,
                        )
                    )
                    if not is_novel_signal:
                        continue
                    directional_survivors += 1
                    novelty_parents.append(candidate)
                    directional_passed.append(
                        _DirectionalCandidate(
                            candidate=candidate,
                            result=directional,
                            cheap_score=feedback_score,
                        )
                    )
                finally:
                    runtime.write_progress(generated=generated, evaluated=evaluated_count)
                    if progress_callback is not None:
                        progress_callback(1)

            if evaluated_count == evaluated_before_batch:
                runtime.write_progress(generated=generated, evaluated=evaluated_count)
                if config.n_trials is not None:
                    break
                generation += 1
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated_count,
                )
                continue
            model.update(evaluated)
            generation += 1
            if config.n_trials is None:
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated_count,
                )

        _write_model_summary(output / "backend_state" / "catcma_qd_state.csv", model)
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


def _select_directional_feedback_candidates(
    candidates: list[_DirectionalCandidate],
    *,
    batch_size: int,
) -> list[_DirectionalCandidate]:
    if not candidates:
        return []
    budget = max(3, int(batch_size * _STAGE2_BATCH_FRACTION))
    budget = min(budget, len(candidates))
    ranked = sorted(candidates, key=lambda item: item.cheap_score, reverse=True)
    selected: list[_DirectionalCandidate] = []
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


def _directional_cheap_score(result: DirectionalResult) -> float:
    if result.advisory_score is not None:
        return result.advisory_score
    return directional_advisory_score(result)


def _directional_feedback_score(result: DirectionalResult, is_novel_signal: bool) -> float:
    if result.should_promote and not is_novel_signal:
        return _DUPLICATE_SIGNAL_FEEDBACK_SCORE
    return _directional_cheap_score(result)


def _mutate_candidate(
    parent: DSSCandidate,
    search_space: DSSSearchSpace,
    *,
    candidate_id: str,
    generation: int,
    seed: int,
) -> DSSCandidate:
    rng = random.Random(seed)
    trigger_name = parent.trigger_name
    trigger_timeframe = parent.trigger_timeframe
    trigger_params = dict(parent.trigger_params)
    filter_names = list(parent.filter_names)
    filter_params = {name: dict(params) for name, params in parent.filter_params.items()}

    operation = rng.choice(["trigger", "add_filter", "drop_filter", "param"])
    if operation == "trigger" and search_space.trigger_names:
        picked_trigger = str(rng.choice(search_space.trigger_names))
        trigger_name = _instance_base_name(picked_trigger)
        trigger_timeframe = _instance_timeframe(picked_trigger)
        trigger_params = {
            name: _sample_param_choice(param_def, rng)
            for name, param_def in search_space.trigger_param_bounds.get(
                _instance_base_name(picked_trigger), {}
            ).items()
        }
    elif operation == "add_filter" and len(filter_names) < search_space.max_filters:
        choices = [name for name in search_space.filter_names if name not in filter_names]
        if choices:
            picked = str(rng.choice(choices))
            filter_names.append(picked)
            filter_params[picked] = {
                name: _sample_param_choice(param_def, rng)
                for name, param_def in search_space.filter_param_bounds.get(
                    _instance_base_name(picked), {}
                ).items()
            }
    elif operation == "drop_filter" and filter_names:
        dropped = str(rng.choice(filter_names))
        filter_names.remove(dropped)
        filter_params.pop(dropped, None)
    else:
        owners = [("trigger", trigger_name)] + [("filter", name) for name in filter_names]
        namespace, owner = rng.choice(owners)
        bounds = (
            search_space.trigger_param_bounds
            if namespace == "trigger"
            else search_space.filter_param_bounds
        )
        params = trigger_params if namespace == "trigger" else filter_params.setdefault(owner, {})
        base_owner = _instance_base_name(owner)
        if bounds.get(base_owner):
            param_name = rng.choice(tuple(bounds[base_owner]))
            params[param_name] = _sample_param_choice(bounds[base_owner][param_name], rng)

    return DSSCandidate(
        candidate_id=candidate_id,
        trigger_name=trigger_name,
        trigger_timeframe=trigger_timeframe,
        trigger_params=trigger_params,
        filter_names=tuple(sorted(filter_names)),
        filter_timeframes={
            name: _instance_timeframe(name)
            for name in filter_names
            if _instance_timeframe(name) != "H1"
        },
        filter_params={name: filter_params.get(name, {}) for name in filter_names},
        generation=generation,
        parent_ids=(parent.candidate_id,),
    )


def _sample_param_choice(param_def: ParamDef, rng: random.Random) -> ParamValue:
    value = rng.choice(_param_choices(param_def))
    if not isinstance(value, (float, int, str)):
        raise TypeError(f"Unsupported mutation parameter value: {value!r}")
    return value


def _write_model_summary(path: Path, model: _WeightedModel) -> None:
    rows: list[dict[str, object]] = []
    rows.append({"namespace": "backend", "value": model.backend_name, "weight": 1.0})
    rows.append(
        {
            "namespace": "population_size",
            "value": model._optimizer.population_size,
            "weight": 1.0,
        }
    )
    rows.append({"namespace": "tell_count", "value": model._tell_count, "weight": 1.0})
    rows.append({"namespace": "pending_feedback", "value": len(model._feedback), "weight": 1.0})
    if model._c_slots and hasattr(model._optimizer, "_q"):
        optimizer: Any = model._optimizer
        cat_probabilities = optimizer._q
        for slot, row in zip(model._c_slots, cat_probabilities, strict=True):
            for idx, value in enumerate(slot.choices):
                rows.append(
                    {
                        "namespace": f"{slot.namespace}:{slot.owner}:{slot.name}",
                        "value": value,
                        "weight": float(row[idx]),
                    }
                )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["namespace", "value", "weight"])
        writer.writeheader()
        writer.writerows(rows)


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
