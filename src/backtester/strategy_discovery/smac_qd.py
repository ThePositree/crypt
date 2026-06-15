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
from backtester.strategy_discovery.catcma_qd import _WeightedModel
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
from backtester.strategy_discovery.dss_objective import _EMPTY_SIGNAL_PENALTY
from backtester.strategy_discovery.dss_v2 import (
    DSSV2Result,
    _append_csv_row,
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
    export_stage4_candidates,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_BOOTSTRAP_RANDOM_EVALUATIONS = 64
_EVALUATION_BATCH_SIZE = 16
_PROPOSAL_POOL_SIZE = 512
_RF_TREES = 96
_ACQUISITION_STD_WEIGHT = 0.75


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
        values.extend(
            1.0 if candidate.trigger_name == name else 0.0
            for name in self._search_space.trigger_names
        )
        values.extend(
            1.0 if name in candidate.filter_names else 0.0
            for name in self._search_space.filter_names
        )
        values.append(
            _safe_ratio(len(candidate.filter_names), max(self._search_space.max_filters, 1))
        )
        values.append(_normalize_float(candidate.rrr, self._search_space.rrr_range))
        values.append(
            _normalize_float(candidate.risk_percent, self._search_space.risk_percent_range)
        )
        values.append(
            _normalize_int(candidate.position_ttl_bars, self._search_space.position_ttl_bars_range)
        )
        values.append(_normalize_float(candidate.atr_sl_mult, self._search_space.atr_sl_mult_range))

        for trigger in self._search_space.trigger_names:
            params = candidate.trigger_params if candidate.trigger_name == trigger else {}
            for name, param_def in sorted(
                self._search_space.trigger_param_bounds.get(trigger, {}).items()
            ):
                values.append(_normalize_param(params.get(name), param_def))

        for filter_name in self._search_space.filter_names:
            params = (
                candidate.filter_params.get(filter_name, {})
                if filter_name in candidate.filter_names
                else {}
            )
            for name, param_def in sorted(
                self._search_space.filter_param_bounds.get(filter_name, {}).items()
            ):
                values.append(_normalize_param(params.get(name), param_def))
        return values

    def _build_feature_names(self, search_space: DSSSearchSpace) -> list[str]:
        names: list[str] = []
        names.extend(f"trigger={name}" for name in search_space.trigger_names)
        names.extend(f"filter={name}" for name in search_space.filter_names)
        names.extend(["filter_depth", "rrr", "risk_percent", "position_ttl_bars", "atr_sl_mult"])
        for trigger in search_space.trigger_names:
            for name in sorted(search_space.trigger_param_bounds.get(trigger, {})):
                names.append(f"trigger_param={trigger}.{name}")
        for filter_name in search_space.filter_names:
            for name in sorted(search_space.filter_param_bounds.get(filter_name, {})):
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
) -> DSSV2Result:
    """Run SMAC-style random-forest infill search with DSS-compatible outputs."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_stage3 = _read_completed_ids(output / "stage3_full_scores.csv")
    existing_stage0 = _read_stage0_candidates(output / "stage0_candidates.jsonl")
    stage0_by_id = {candidate.candidate_id: candidate for candidate in existing_stage0}
    encoder = _CandidateEncoder(search_space)
    sampler = _WeightedModel(search_space, seed=config.seed)
    surrogate = _RandomForestSurrogate(seed=config.seed)
    observations = _read_observations(output / "smac_qd_observations.csv", stage0_by_id)
    _fit_surrogate(surrogate, encoder, observations)

    composer = SignalComposer()
    archive = DSSArchive()
    generated = min(len(existing_stage0), config.n_trials)
    if generated and progress_callback is not None:
        progress_callback(generated)
    stage1_survivors = 0
    stage2_survivors = 0
    stage3_evaluations = 0
    generation = generated // _EVALUATION_BATCH_SIZE

    while generated < config.n_trials:
        batch_size = min(_EVALUATION_BATCH_SIZE, config.n_trials - generated)
        proposals = _next_proposals(
            sampler=sampler,
            surrogate=surrogate,
            encoder=encoder,
            generated=generated,
            batch_size=batch_size,
            generation=generation,
            existing_keys={candidate.candidate_key for candidate in stage0_by_id.values()},
            observations=len(observations),
        )

        for proposal in proposals:
            generated += 1
            candidate = proposal.candidate
            candidate = DSSCandidate(
                candidate_id=f"smac_{generated:06d}",
                trigger_name=candidate.trigger_name,
                trigger_params=candidate.trigger_params,
                filter_names=candidate.filter_names,
                filter_params=candidate.filter_params,
                rrr=candidate.rrr,
                risk_percent=candidate.risk_percent,
                position_ttl_bars=candidate.position_ttl_bars,
                atr_sl_mult=candidate.atr_sl_mult,
                generation=generation,
            )
            stage0_by_id[candidate.candidate_id] = candidate
            try:
                _append_jsonl(output / "stage0_candidates.jsonl", candidate.to_dict())
                _append_proposal(output, proposal, candidate)
                if candidate.candidate_id in completed_stage3:
                    continue
                stage1 = evaluate_stage1(candidate, window_data, config, composer)
                _append_stage1(output, candidate, stage1, config.windows)
                if not stage1.passed or stage1.behavior is None:
                    observation = _SMACObservation(
                        candidate=candidate,
                        target_score=_EMPTY_SIGNAL_PENALTY,
                        fidelity="stage1_reject",
                    )
                    observations.append(observation)
                    _append_observation(output, observation)
                    continue
                stage1_survivors += 1

                stage2 = evaluate_stage_scores(
                    candidate=candidate,
                    behavior=stage1.behavior,
                    windows=_proxy_windows(config.windows),
                    window_data=window_data,
                    config=config,
                    composer=composer,
                    novelty_bonus=10.0 if archive.occupied_cells == 0 else 0.0,
                )
                _append_stage_score(output / "stage2_proxy.csv", stage2, config.windows)
                archive.consider(stage2.candidate, stage1.behavior, stage2.score)
                target_score = stage2.score.robust_score
                fidelity = "stage2_proxy"

                if _should_promote_to_stage3(stage2, archive, config):
                    stage2_survivors += 1
                    stage3 = evaluate_stage_scores(
                        candidate=candidate,
                        behavior=stage1.behavior,
                        windows=config.windows,
                        window_data=window_data,
                        config=config,
                        composer=composer,
                        novelty_bonus=0.0,
                    )
                    _append_stage_score(output / "stage3_full_scores.csv", stage3, config.windows)
                    _append_score_history(output / "score_history.csv", stage3)
                    archive.consider(stage3.candidate, stage1.behavior, stage3.score)
                    completed_stage3.add(candidate.candidate_id)
                    stage3_evaluations += 1
                    target_score = stage3.score.robust_score
                    fidelity = "stage3_full"

                observation = _SMACObservation(
                    candidate=candidate,
                    target_score=target_score,
                    fidelity=fidelity,
                )
                observations.append(observation)
                _append_observation(output, observation)
            finally:
                if progress_callback is not None:
                    progress_callback(1)

        _fit_surrogate(surrogate, encoder, observations)
        generation += 1

    _write_archive(output, archive)
    _write_smac_state(output / "smac_qd_state.csv", encoder, observations)
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
    seen_shapes: set[tuple[str, tuple[str, ...], float, int]] = set()
    for proposal in ranked:
        shape = (
            proposal.candidate.trigger_name,
            proposal.candidate.filter_names,
            proposal.candidate.rrr,
            proposal.candidate.position_ttl_bars,
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
    surrogate.fit(
        [encoder.encode(observation.candidate) for observation in observations],
        [observation.target_score for observation in observations],
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
            "rrr": candidate.rrr,
            "risk_percent": candidate.risk_percent,
            "position_ttl_bars": candidate.position_ttl_bars,
            "atr_sl_mult": candidate.atr_sl_mult,
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
            "rrr": candidate.rrr,
            "risk_percent": candidate.risk_percent,
            "position_ttl_bars": candidate.position_ttl_bars,
            "atr_sl_mult": candidate.atr_sl_mult,
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
                    target_score=float(row.get("target_score", _EMPTY_SIGNAL_PENALTY)),
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
