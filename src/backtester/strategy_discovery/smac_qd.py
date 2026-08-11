"""SMAC-style random-forest surrogate quality-diversity DSS backend."""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.catcma_qd import (
    _NOVELTY_MUTATION_INTERVAL,
    _mutate_candidate,
    _WeightedModel,
)
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
from backtester.strategy_discovery.dss_directional_search import (
    DirectionalResult,
    DSSDirectionalResult,
    DSSSignalNoveltyTracker,
    _append_csv_row,
    _count_csv_rows,
    _count_directional_survivors,
    _evaluate_directional_candidate,
    _guard_output_dir,
    _instance_base_name,
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

_BOOTSTRAP_RANDOM_EVALUATIONS = 64
_EVALUATION_BATCH_SIZE = 16
_PROPOSAL_POOL_SIZE = 512
_RF_TREES = 96
_MAX_SURROGATE_TRAIN_ROWS = 5_000
_SURROGATE_REFIT_INTERVAL = 512
_ACQUISITION_STD_WEIGHT = 0.75
_DIRECTIONAL_REJECT_PENALTY = -10_000.0


@dataclass(frozen=True, slots=True)
class _SMACObservation:
    candidate: DSSCandidate
    target_score: float
    fidelity: str


@dataclass(frozen=True, slots=True)
class _SMACProposal:
    candidate: DSSCandidate
    predicted_mean: float
    predicted_std: float
    acquisition: float


class _CandidateEncoder:
    """Fixed conditional numeric encoding for random-forest surrogate models."""

    def __init__(self, search_space: DSSSearchSpace) -> None:
        self._search_space = search_space
        self.feature_names = self._build_feature_names(search_space)

    def encode(self, candidate: DSSCandidate) -> list[float]:
        values: list[float] = []
        trigger_label = _candidate_trigger_label(candidate, self._search_space)
        values.extend(
            1.0 if trigger_label == name else 0.0
            for name in self._search_space.trigger_names
        )
        values.extend(
            1.0 if name in candidate.filter_names else 0.0
            for name in self._search_space.filter_names
        )
        values.append(
            _safe_ratio(len(candidate.filter_names), max(self._search_space.max_filters, 1))
        )

        for trigger in self._search_space.trigger_names:
            params = candidate.trigger_params if trigger_label == trigger else {}
            for name, param_def in sorted(
                self._search_space.trigger_param_bounds.get(_instance_base_name(trigger), {}).items()
            ):
                values.append(_normalize_param(params.get(name), param_def))

        for filter_name in self._search_space.filter_names:
            params = (
                candidate.filter_params.get(filter_name, {})
                if filter_name in candidate.filter_names
                else {}
            )
            for name, param_def in sorted(
                self._search_space.filter_param_bounds.get(
                    _instance_base_name(filter_name), {}
                ).items()
            ):
                values.append(_normalize_param(params.get(name), param_def))
        return values

    def _build_feature_names(self, search_space: DSSSearchSpace) -> list[str]:
        names: list[str] = []
        names.extend(f"trigger={name}" for name in search_space.trigger_names)
        names.extend(f"filter={name}" for name in search_space.filter_names)
        names.append("filter_depth")
        for trigger in search_space.trigger_names:
            for name in sorted(search_space.trigger_param_bounds.get(_instance_base_name(trigger), {})):
                names.append(f"trigger_param={trigger}.{name}")
        for filter_name in search_space.filter_names:
            for name in sorted(search_space.filter_param_bounds.get(_instance_base_name(filter_name), {})):
                names.append(f"filter_param={filter_name}.{name}")
        return names


class _RandomForestSurrogate:
    """Random-forest surrogate with tree-dispersion uncertainty."""

    def __init__(self, *, seed: int) -> None:
        self._seed = seed
        self._model: RandomForestRegressor | None = None

    @property
    def fitted(self) -> bool:
        return self._model is not None

    def fit(self, x_rows: list[list[float]], y: list[float]) -> None:
        if len(x_rows) < 2:
            return
        x = np.asarray(x_rows, dtype=float)
        target = np.asarray(y, dtype=float)
        model = RandomForestRegressor(
            n_estimators=_RF_TREES,
            max_features="sqrt",
            min_samples_leaf=2,
            bootstrap=True,
            random_state=self._seed,
            n_jobs=1,
        )
        model.fit(x, target)
        self._model = model

    def predict(self, x_rows: list[list[float]]) -> tuple[list[float], list[float]]:
        if self._model is None:
            return ([0.0] * len(x_rows), [0.0] * len(x_rows))
        x = np.asarray(x_rows, dtype=float)
        estimators = cast(list[Any], self._model.estimators_)
        tree_predictions = np.asarray([tree.predict(x) for tree in estimators], dtype=float)
        means = tree_predictions.mean(axis=0)
        stds = tree_predictions.std(axis=0)
        return (means.astype(float).tolist(), stds.astype(float).tolist())


def run_smac_qd_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSDirectionalResult:
    """Run SMAC-style random-forest infill search with DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    existing_candidates = _read_candidate_rows(output / "candidates.jsonl")
    candidates_by_id = {candidate.candidate_id: candidate for candidate in existing_candidates}
    encoder = _CandidateEncoder(search_space)
    sampler = _WeightedModel(search_space, seed=config.seed)
    surrogate = _RandomForestSurrogate(seed=config.seed)
    observations = _read_observations(output / "smac_qd_observations.csv", candidates_by_id)
    _fit_surrogate(surrogate, encoder, observations)

    composer = SignalComposer()
    archive = DSSArchive()
    generated = len(existing_candidates)
    attempted = len(existing_candidates)
    viability_path = output / "directional_viability.csv"
    evaluated_ids = _read_directional_candidate_ids(viability_path)
    signal_novelty = DSSSignalNoveltyTracker(viability_path)
    evaluated_count = _count_csv_rows(viability_path)
    novelty_parents: list[DSSCandidate] = []
    if evaluated_count and progress_callback is not None:
        progress_callback(evaluated_count)
    directional_survivors = _count_directional_survivors(viability_path)
    generation = generated // _EVALUATION_BATCH_SIZE

    with DSSSearchRuntime(config=config) as runtime:
        for candidate in existing_candidates:
            runtime.record_candidate(candidate, source="resume")

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
            observation = _directional_observation(candidate, directional, is_novel_signal)
            observations.append(observation)
            _append_observation(output, observation)
            if is_novel_signal:
                directional_survivors += 1
                novelty_parents.append(candidate)
            runtime.write_progress(generated=generated, evaluated=evaluated_count)
            if progress_callback is not None:
                progress_callback(1)
        _fit_surrogate(surrogate, encoder, observations)

        while runtime.should_continue(evaluated_count):
            batch_size = runtime.remaining_batch(evaluated_count, _EVALUATION_BATCH_SIZE)
            evaluated_before_batch = evaluated_count
            proposals = _next_proposals(
                sampler=sampler,
                surrogate=surrogate,
                encoder=encoder,
                generated=generated,
                batch_size=batch_size,
                generation=generation,
                existing_keys={candidate.candidate_key for candidate in candidates_by_id.values()},
                observations=len(observations),
            )
            if not proposals:
                if config.n_trials is not None:
                    break
                proposals = [
                    _SMACProposal(
                        candidate=sample_random_directional_candidate(
                            search_space=search_space,
                            candidate_id=f"smac_fallback_{attempted + idx + 1:06d}",
                            generation=generation,
                            max_filters=config.max_filters,
                            seed=config.seed + (attempted + idx + 1) * 1009,
                        ),
                        predicted_mean=0.0,
                        predicted_std=0.0,
                        acquisition=0.0,
                    )
                    for idx in range(batch_size)
                ]

            for proposal in proposals:
                attempted += 1
                source = "smac_qd"
                candidate = proposal.candidate
                if attempted % _NOVELTY_MUTATION_INTERVAL == 0 and novelty_parents:
                    source = "novelty_mutation"
                    candidate = _mutate_candidate(
                        novelty_parents[-1],
                        search_space,
                        candidate_id=f"smac_{attempted:06d}",
                        generation=generation,
                        seed=config.seed + attempted,
                    )
                elif should_use_random_injection(attempted):
                    source = "random_unseen"
                    candidate = sample_random_directional_candidate(
                        search_space=search_space,
                        candidate_id=f"smac_{attempted:06d}",
                        generation=generation,
                        max_filters=config.max_filters,
                        seed=config.seed + attempted * 1009,
                    )
                    proposal = _SMACProposal(
                        candidate=candidate,
                        predicted_mean=0.0,
                        predicted_std=0.0,
                        acquisition=0.0,
                    )
                candidate = DSSCandidate(
                    candidate_id=f"smac_{attempted:06d}",
                    trigger_name=candidate.trigger_name,
                    trigger_timeframe=candidate.trigger_timeframe,
                    trigger_params=candidate.trigger_params,
                    filter_names=candidate.filter_names,
                    filter_timeframes=candidate.filter_timeframes,
                    filter_params=candidate.filter_params,
                    generation=generation,
                )
                if not runtime.record_candidate(candidate, source=source):
                    runtime.write_progress(generated=generated, evaluated=evaluated_count)
                    continue
                generated += 1
                candidates_by_id[candidate.candidate_id] = candidate
                try:
                    _append_proposal(output, proposal, candidate)
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
                    observation = _directional_observation(candidate, directional, is_novel_signal)
                    observations.append(observation)
                    _append_observation(output, observation)
                    if not is_novel_signal:
                        continue
                    directional_survivors += 1
                    novelty_parents.append(candidate)
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
            if _should_refit_surrogate(surrogate, evaluated_count):
                _fit_surrogate(surrogate, encoder, observations)
            generation += 1
            if config.n_trials is None:
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated_count,
                )

        _write_smac_state(output / "backend_state" / "smac_qd_state.csv", encoder, observations)
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


def _next_proposals(
    *,
    sampler: _WeightedModel,
    surrogate: _RandomForestSurrogate,
    encoder: _CandidateEncoder,
    generated: int,
    batch_size: int,
    generation: int,
    existing_keys: set[str],
    observations: int,
) -> list[_SMACProposal]:
    if observations < _BOOTSTRAP_RANDOM_EVALUATIONS or not surrogate.fitted:
        return [
            _SMACProposal(
                candidate=sampler.sample(
                    f"smac_bootstrap_{generated + idx + 1:06d}", generation=generation
                ),
                predicted_mean=0.0,
                predicted_std=0.0,
                acquisition=0.0,
            )
            for idx in range(batch_size)
        ]

    pool: list[DSSCandidate] = []
    attempts = 0
    target_pool = max(_PROPOSAL_POOL_SIZE, batch_size * 8)
    while len(pool) < target_pool and attempts < target_pool * 4:
        attempts += 1
        candidate = sampler.sample(f"smac_pool_{generation}_{attempts:06d}", generation=generation)
        if candidate.candidate_key in existing_keys:
            continue
        pool.append(candidate)
    if not pool:
        return []

    means, stds = surrogate.predict([encoder.encode(candidate) for candidate in pool])
    ranked = sorted(
        (
            _SMACProposal(
                candidate=candidate,
                predicted_mean=mean,
                predicted_std=std,
                acquisition=mean + _ACQUISITION_STD_WEIGHT * std,
            )
            for candidate, mean, std in zip(pool, means, stds, strict=True)
        ),
        key=lambda proposal: proposal.acquisition,
        reverse=True,
    )
    selected: list[_SMACProposal] = []
    seen_shapes: set[tuple[str, tuple[str, ...]]] = set()
    for proposal in ranked:
        shape = (
            _candidate_trigger_label(proposal.candidate, encoder._search_space),
            proposal.candidate.filter_names,
        )
        if shape in seen_shapes:
            continue
        selected.append(proposal)
        seen_shapes.add(shape)
        if len(selected) >= batch_size:
            return selected
    return ranked[:batch_size]


def _fit_surrogate(
    surrogate: _RandomForestSurrogate,
    encoder: _CandidateEncoder,
    observations: list[_SMACObservation],
) -> None:
    if len(observations) < 2:
        return
    train_observations = observations[-_MAX_SURROGATE_TRAIN_ROWS:]
    surrogate.fit(
        [encoder.encode(observation.candidate) for observation in train_observations],
        [observation.target_score for observation in train_observations],
    )


def _should_refit_surrogate(surrogate: _RandomForestSurrogate, evaluated_count: int) -> bool:
    return not surrogate.fitted or evaluated_count % _SURROGATE_REFIT_INTERVAL < _EVALUATION_BATCH_SIZE


def _candidate_trigger_label(candidate: DSSCandidate, search_space: DSSSearchSpace) -> str:
    label = f"{candidate.trigger_name}@{candidate.trigger_timeframe}"
    if label in search_space.trigger_names:
        return label
    if candidate.trigger_name in search_space.trigger_names:
        return candidate.trigger_name
    return label


def _directional_observation(
    candidate: DSSCandidate, result: DirectionalResult, is_novel_signal: bool = True
) -> _SMACObservation:
    if not result.should_promote:
        return _SMACObservation(
            candidate=candidate,
            target_score=_DIRECTIONAL_REJECT_PENALTY,
            fidelity="directional_reject",
        )
    if not is_novel_signal:
        return _SMACObservation(
            candidate=candidate,
            target_score=_DIRECTIONAL_REJECT_PENALTY,
            fidelity="duplicate_signal",
        )
    return _SMACObservation(
        candidate=candidate,
        target_score=float(result.advisory_score) if result.advisory_score is not None else 0.0,
        fidelity="directional_pass",
    )


def _append_proposal(output: Path, proposal: _SMACProposal, candidate: DSSCandidate) -> None:
    _append_csv_row(
        output / "smac_qd_proposals.csv",
        {
            "candidate_id": candidate.candidate_id,
            "trigger_name": candidate.trigger_name,
            "filter_names": "+".join(candidate.filter_names),
            "predicted_mean": proposal.predicted_mean,
            "predicted_std": proposal.predicted_std,
            "acquisition": proposal.acquisition,
        },
    )


def _append_observation(output: Path, observation: _SMACObservation) -> None:
    candidate = observation.candidate
    _append_csv_row(
        output / "smac_qd_observations.csv",
        {
            "candidate_id": candidate.candidate_id,
            "target_score": observation.target_score,
            "fidelity": observation.fidelity,
            "trigger_name": candidate.trigger_name,
            "filter_names": "+".join(candidate.filter_names),
        },
    )


def _read_observations(path: Path, candidates: dict[str, DSSCandidate]) -> list[_SMACObservation]:
    if not path.exists():
        return []
    observations: list[_SMACObservation] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            candidate_id = row.get("candidate_id", "")
            candidate = candidates.get(candidate_id)
            if candidate is None:
                continue
            observations.append(
                _SMACObservation(
                    candidate=candidate,
                    target_score=float(row.get("target_score", _DIRECTIONAL_REJECT_PENALTY)),
                    fidelity=row.get("fidelity", ""),
                )
            )
    return observations


def _write_smac_state(
    path: Path,
    encoder: _CandidateEncoder,
    observations: list[_SMACObservation],
) -> None:
    rows: list[dict[str, object]] = [
        {"metric": "observations", "value": len(observations)},
        {"metric": "features", "value": len(encoder.feature_names)},
        {"metric": "bootstrap_random_evaluations", "value": _BOOTSTRAP_RANDOM_EVALUATIONS},
        {"metric": "rf_trees", "value": _RF_TREES},
        {"metric": "max_surrogate_train_rows", "value": _MAX_SURROGATE_TRAIN_ROWS},
        {"metric": "surrogate_refit_interval", "value": _SURROGATE_REFIT_INTERVAL},
        {"metric": "acquisition_std_weight", "value": _ACQUISITION_STD_WEIGHT},
    ]
    if observations:
        best = max(observations, key=lambda item: item.target_score)
        rows.extend(
            [
                {"metric": "best_candidate_id", "value": best.candidate.candidate_id},
                {"metric": "best_target_score", "value": best.target_score},
                {"metric": "best_fidelity", "value": best.fidelity},
            ]
        )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def _normalize_param(value: ParamValue | None, param_def: ParamDef) -> float:
    if value is None:
        return -1.0
    if isinstance(param_def, IntParam):
        return _safe_ratio(float(value) - param_def.low, max(param_def.high - param_def.low, 1))
    if isinstance(param_def, FloatParam):
        return _safe_ratio(float(value) - param_def.low, max(param_def.high - param_def.low, 1e-9))
    if isinstance(param_def, CategoricalParam):
        choices = list(param_def.choices)
        if value not in choices:
            return -1.0
        return _safe_ratio(choices.index(value), max(len(choices) - 1, 1))
    raise TypeError(f"Unsupported parameter definition: {param_def!r}")


def _normalize_float(value: float, spec: tuple[float, float, float]) -> float:
    low, high, _step = spec
    return _safe_ratio(value - low, max(high - low, 1e-9))


def _normalize_int(value: int, spec: tuple[int, int, int]) -> float:
    low, high, _step = spec
    return _safe_ratio(value - low, max(high - low, 1))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)
