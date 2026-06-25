"""Offline regime-router evaluation helpers."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from tqdm.auto import tqdm

FEATURE_COLUMNS = [
    "ret_30d_pct",
    "ret_90d_pct",
    "realized_vol_30d_pct",
    "realized_vol_90d_pct",
    "atr14_pct",
    "atr14_pct_rank_180d",
    "bb_width20_pct",
    "volume_ratio_30d",
    "volume_percentile_90d",
    "close_vs_sma50_pct",
    "close_vs_sma200_pct",
    "sma50_slope_30d_pct",
    "donchian_position_90d",
    "trend_efficiency_30d",
    "choppiness_30d",
]

STATE_SUBSETS: dict[str, tuple[str, ...]] = {
    "trend": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
    ),
    "momentum": (
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
    ),
    "volatility": ("router_ps_squeeze_on",),
    "structure": (
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
        "router_ps_smc_ob_active_side",
    ),
    "session": ("router_ps_killzone_code",),
    "breakout": ("router_ps_trendline_break_side",),
    "trend_momentum": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
    ),
    "trend_volatility": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_squeeze_on",
    ),
    "trend_structure": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
    ),
    "momentum_structure": (
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
    ),
    "volatility_structure": (
        "router_ps_squeeze_on",
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
    ),
    "trend_momentum_volatility": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
        "router_ps_squeeze_on",
    ),
    "trend_momentum_structure": (
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
    ),
}
STATE_SUBSETS["all_core"] = tuple(
    dict.fromkeys(column for columns in STATE_SUBSETS.values() for column in columns)
)


@dataclass(frozen=True, slots=True)
class RouterConfig:
    """Evaluation settings for rolling-label router reports."""

    validation_start: str
    min_available_strategies: int = 3
    lookback_days: int = 365
    top1_weight: float = 0.6
    knn_k: int = 7
    non_overlap_days: int = 30


@dataclass(frozen=True, slots=True)
class RouterSearchConfig:
    """Settings for single-strategy router catalog search."""

    validation_start: str
    validation_end: str | None = None
    min_available_strategies: int = 3
    non_overlap_days: int = 30
    catalog_version: str = "v1"
    algorithm: str = "grid"
    seed: int = 2026
    proposal_multiplier: int = 8
    lookback_days: tuple[int, ...] = (30, 60, 90, 120, 180, 270, 365, 540)
    scoring_methods: tuple[str, ...] = (
        "rolling_mean",
        "rolling_median",
        "rolling_mean_minus_dd",
        "rolling_mean_minus_neg_rate",
        "feature_knn_mean",
        "feature_knn_median",
        "feature_knn_mean_minus_dd",
        "same_state_mean",
        "same_state_mean_minus_dd",
    )
    feature_sets: tuple[str, ...] = ("ohlcv", "pinescript", "mixed")
    knn_k: tuple[int, ...] = (3, 5, 7, 11)
    min_hold_days: tuple[int, ...] = (0, 7, 14, 30)
    switch_margin_thresholds: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0, 5.0)
    min_samples: int = 10
    config_offset: int = 0
    max_configs: int = 2_000
    summary_only: bool = False
    top_predictions: int = 20
    progress: bool = False
    progress_position: int = 0


@dataclass(frozen=True, slots=True)
class RouterCandidate:
    """One single-strategy router candidate."""

    router_id: str
    scoring_method: str
    lookback_days: int
    feature_set: str
    knn_k: int
    state_subset: str = "none"
    state_match_mode: str = "none"
    state_similarity_threshold: float = 1.0
    state_weight_profile: str = "equal"
    ewm_halflife_days: int = 0
    min_samples: int = 10
    min_hold_days: int = 0
    switch_margin_threshold: float = 0.0


@dataclass(frozen=True, slots=True)
class FeatureMatrix:
    """Numeric feature matrix aligned to prepared label rows."""

    columns: tuple[str, ...]
    values: np.ndarray


@dataclass(frozen=True, slots=True)
class RouterSearchData:
    """Numeric return matrix aligned to prepared label rows."""

    strategy_ids: tuple[str, ...]
    strategy_index: dict[str, int]
    returns: np.ndarray
    label_end_ns: np.ndarray
    available_counts: np.ndarray


def evaluate_rolling_router_baselines(
    labels: pd.DataFrame,
    *,
    config: RouterConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate live-safe routers over rolling forward-label rows.

    Dense rows score every eligible label row as a forward-window decision.
    Non-overlap rows keep every Nth row so portfolio-style compounding does not
    double-count overlapping 30-day label windows.
    """

    prepared = _prepare_labels(labels)
    strategy_cols = _strategy_return_columns(prepared)
    if not strategy_cols:
        raise ValueError("rolling labels must contain return_<strategy_id> columns")

    validation_start = pd.Timestamp(config.validation_start, tz="UTC")
    eligible_mask = (prepared["asof"] >= validation_start) & (
        prepared["available_strategy_count"] >= config.min_available_strategies
    )
    eligible = prepared[eligible_mask].copy()
    if eligible.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    dense_rows: list[dict[str, Any]] = []
    for _, row in eligible.iterrows():
        asof = row["asof"]
        train = _training_rows(
            prepared,
            asof=asof,
            lookback_days=config.lookback_days,
            min_available_strategies=config.min_available_strategies,
        )
        available = _available_strategies(row, strategy_cols)
        if not available:
            continue
        dense_rows.extend(
            [
                _score_weights("oracle", row, {str(row["best_strategy"]): 1.0}),
                _score_weights("equal_weight_available", row, _equal_weights(available)),
                _score_weights(
                    "rolling_best_mean",
                    row,
                    _rolling_top_weights(train, available, top_n=1, top1_weight=1.0),
                ),
                _score_weights(
                    "rolling_top2_mean_60_40",
                    row,
                    _rolling_top_weights(
                        train,
                        available,
                        top_n=2,
                        top1_weight=config.top1_weight,
                    ),
                ),
                _score_weights(
                    "feature_knn_top2_60_40",
                    row,
                    _feature_knn_top_weights(
                        train,
                        row,
                        available,
                        k=config.knn_k,
                        top1_weight=config.top1_weight,
                    ),
                ),
            ]
        )

    dense = pd.DataFrame(dense_rows)
    if dense.empty:
        return dense, pd.DataFrame(), pd.DataFrame()
    summary = _summarize_dense(dense)
    non_overlap = _non_overlap_summary(dense, every_days=config.non_overlap_days)
    return dense, summary, non_overlap


def evaluate_single_strategy_router_search(
    labels: pd.DataFrame,
    *,
    config: RouterSearchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Search live-safe routers that always select one strategy."""

    if config.config_offset < 0:
        raise ValueError("config_offset must be >= 0")
    if config.max_configs <= 0:
        raise ValueError("max_configs must be positive")
    if config.proposal_multiplier < 2:
        raise ValueError("proposal_multiplier must be >= 2")
    if config.top_predictions < 0:
        raise ValueError("top_predictions must be >= 0")

    prepared = _prepare_labels(labels)
    strategy_cols = _strategy_return_columns(prepared)
    if not strategy_cols:
        raise ValueError("rolling labels must contain return_<strategy_id> columns")

    validation_start = pd.Timestamp(config.validation_start, tz="UTC")
    eligible_mask = (prepared["asof"] >= validation_start) & (
        prepared["available_strategy_count"] >= config.min_available_strategies
    )
    if config.validation_end is not None:
        eligible_mask &= prepared["asof"] < pd.Timestamp(config.validation_end, tz="UTC")
    eligible = prepared[eligible_mask].copy()
    if eligible.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    search_data = _router_search_data(prepared, strategy_cols)
    candidates = _select_router_candidates(
        config=config,
        prepared=prepared,
        eligible=eligible,
        strategy_cols=strategy_cols,
        search_data=search_data,
    )
    if not candidates:
        empty = pd.DataFrame()
        return empty, empty, empty, empty
    score_cache: dict[tuple[Any, ...], tuple[dict[str, float], dict[str, int]]] = {}
    feature_cache: dict[str, FeatureMatrix] = {}
    if config.summary_only:
        dense_records: list[dict[str, Any]] = []
        utility_records: list[dict[str, Any]] = []
        candidate_by_id = {candidate.router_id: candidate for candidate in candidates}
        last_signature: tuple[Any, ...] | None = None
        candidate_items = tqdm(
            candidates,
            total=len(candidates),
            desc=f"router-search {config.algorithm}",
            unit="router",
            mininterval=1.0,
            dynamic_ncols=True,
            position=config.progress_position,
            disable=not config.progress,
        )
        for candidate in candidate_items:
            signature = _candidate_score_signature(candidate)
            if signature != last_signature:
                score_cache.clear()
                last_signature = signature
            frame = _evaluate_router_candidate(
                prepared=prepared,
                eligible=eligible,
                strategy_cols=strategy_cols,
                candidate=candidate,
                config=config,
                score_cache=score_cache,
                feature_cache=feature_cache,
                search_data=search_data,
            )
            dense = _summarize_router_search_dense(frame)
            offsets = _offset_sensitivity(frame, every_days=config.non_overlap_days)
            utility = _router_utility_summary(offsets)
            dense_records.append(dense.iloc[0].to_dict())
            utility_records.append(utility.iloc[0].to_dict())

        dense_summary = pd.DataFrame(dense_records)
        utility = pd.DataFrame(utility_records).sort_values("utility_score", ascending=False)
        top_ids = utility.head(config.top_predictions)["router"].tolist()
        score_cache.clear()
        top_frames = []
        top_offsets = []
        top_items = tqdm(
            top_ids,
            total=len(top_ids),
            desc="router-search shortlist",
            unit="router",
            mininterval=1.0,
            dynamic_ncols=True,
            position=config.progress_position,
            disable=not config.progress,
        )
        for router_id in top_items:
            frame = _evaluate_router_candidate(
                prepared=prepared,
                eligible=eligible,
                strategy_cols=strategy_cols,
                candidate=candidate_by_id[router_id],
                config=config,
                score_cache=score_cache,
                feature_cache=feature_cache,
                search_data=search_data,
            )
            top_frames.append(frame)
            top_offsets.append(_offset_sensitivity(frame, every_days=config.non_overlap_days))
        predictions = pd.concat(top_frames, ignore_index=True) if top_frames else pd.DataFrame()
        offset_sensitivity = (
            pd.concat(top_offsets, ignore_index=True) if top_offsets else pd.DataFrame()
        )
        return predictions, dense_summary, offset_sensitivity, utility

    candidate_items = tqdm(
        candidates,
        total=len(candidates),
        desc=f"router-search {config.algorithm}",
        unit="router",
        mininterval=1.0,
        dynamic_ncols=True,
        position=config.progress_position,
        disable=not config.progress,
    )
    frames = [
        _evaluate_router_candidate(
            prepared=prepared,
            eligible=eligible,
            strategy_cols=strategy_cols,
            candidate=candidate,
            config=config,
            score_cache=score_cache,
            feature_cache=feature_cache,
            search_data=search_data,
        )
        for candidate in candidate_items
    ]
    predictions = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if predictions.empty:
        empty = pd.DataFrame()
        return predictions, empty, empty, empty

    dense_summary = _summarize_router_search_dense(predictions)
    offset_sensitivity = _offset_sensitivity(predictions, every_days=config.non_overlap_days)
    utility = _router_utility_summary(offset_sensitivity)
    return predictions, dense_summary, offset_sensitivity, utility


def count_router_candidates(labels: pd.DataFrame, *, config: RouterSearchConfig) -> int:
    """Count deterministic router candidates without evaluating them."""

    prepared = _prepare_labels(labels)
    return sum(1 for _ in _router_candidates(config, prepared))


def evaluate_frozen_router_candidate(
    labels: pd.DataFrame,
    *,
    candidate: RouterCandidate,
    config: RouterSearchConfig,
) -> pd.DataFrame:
    """Evaluate one frozen router candidate over eligible label rows."""

    prepared = _prepare_labels(labels)
    strategy_cols = _strategy_return_columns(prepared)
    if not strategy_cols:
        raise ValueError("rolling labels must contain return_<strategy_id> columns")
    validation_start = pd.Timestamp(config.validation_start, tz="UTC")
    eligible_mask = (prepared["asof"] >= validation_start) & (
        prepared["available_strategy_count"] >= config.min_available_strategies
    )
    if config.validation_end is not None:
        eligible_mask &= prepared["asof"] < pd.Timestamp(config.validation_end, tz="UTC")
    eligible = prepared[eligible_mask].copy()
    if eligible.empty:
        return pd.DataFrame()
    return _evaluate_router_candidate(
        prepared=prepared,
        eligible=eligible,
        strategy_cols=strategy_cols,
        candidate=candidate,
        config=config,
        score_cache={},
        feature_cache={},
        search_data=_router_search_data(prepared, strategy_cols),
    )


def _select_router_candidates(
    *,
    config: RouterSearchConfig,
    prepared: pd.DataFrame,
    eligible: pd.DataFrame,
    strategy_cols: list[str],
    search_data: RouterSearchData,
) -> list[RouterCandidate]:
    algorithm = config.algorithm.lower()
    if algorithm == "grid":
        return list(
            islice(
                _router_candidates(config, prepared),
                config.config_offset,
                config.config_offset + config.max_configs,
            )
        )
    if algorithm == "random":
        return _reservoir_candidates(config, prepared, config.max_configs)
    if algorithm == "island_qd":
        return _island_candidates(config, prepared)
    if algorithm in {"hyperband_qd", "smac_qd"}:
        pool_size = config.max_configs * max(config.proposal_multiplier, 2)
        pool = _reservoir_candidates(config, prepared, pool_size)
        if algorithm == "hyperband_qd":
            return _hyperband_candidates(
                pool=pool,
                budget=config.max_configs,
                prepared=prepared,
                eligible=eligible,
                strategy_cols=strategy_cols,
                config=config,
                search_data=search_data,
            )
        return _smac_candidates(
            pool=pool,
            budget=config.max_configs,
            prepared=prepared,
            eligible=eligible,
            strategy_cols=strategy_cols,
            config=config,
            search_data=search_data,
        )
    raise ValueError(f"Unsupported router search algorithm: {config.algorithm}")


def _reservoir_candidates(
    config: RouterSearchConfig,
    prepared: pd.DataFrame,
    count: int,
) -> list[RouterCandidate]:
    rng = random.Random(config.seed)
    reservoir: list[RouterCandidate] = []
    candidate_items = tqdm(
        _router_candidates(config, prepared),
        desc=f"router-search {config.algorithm} catalog",
        unit="config",
        mininterval=1.0,
        dynamic_ncols=True,
        position=config.progress_position,
        disable=not config.progress,
    )
    for index, candidate in enumerate(candidate_items):
        if index < config.config_offset:
            continue
        seen = index - config.config_offset
        if len(reservoir) < count:
            reservoir.append(candidate)
            continue
        replacement = rng.randint(0, seen)
        if replacement < count:
            reservoir[replacement] = candidate
    return reservoir


def _island_candidates(config: RouterSearchConfig, prepared: pd.DataFrame) -> list[RouterCandidate]:
    candidates = _router_candidates(config, prepared)
    islands: dict[str, list[RouterCandidate]] = {}
    seen_by_island: dict[str, int] = {}
    rng_by_island: dict[str, random.Random] = {}
    target_per_island = max(1, math.ceil(config.max_configs / 32))
    candidate_items = tqdm(
        candidates,
        desc="router-search island_qd catalog",
        unit="config",
        mininterval=1.0,
        dynamic_ncols=True,
        position=config.progress_position,
        disable=not config.progress,
    )
    for index, candidate in enumerate(candidate_items):
        if index < config.config_offset:
            continue
        island = _router_island(candidate)
        reservoir = islands.setdefault(island, [])
        seen = seen_by_island.get(island, 0)
        rng = rng_by_island.setdefault(
            island, random.Random(config.seed + _stable_text_seed(island))
        )
        if len(reservoir) < target_per_island:
            reservoir.append(candidate)
        else:
            replacement = rng.randint(0, seen)
            if replacement < target_per_island:
                reservoir[replacement] = candidate
        seen_by_island[island] = seen + 1

    selected: list[RouterCandidate] = []
    island_names = sorted(islands)
    position = 0
    while len(selected) < config.max_configs and island_names:
        next_names = []
        for island in island_names:
            reservoir = islands[island]
            if position < len(reservoir):
                selected.append(reservoir[position])
                next_names.append(island)
                if len(selected) >= config.max_configs:
                    break
        island_names = next_names
        position += 1
    return selected


def _router_island(candidate: RouterCandidate) -> str:
    family = (
        candidate.state_subset if candidate.state_subset != "none" else candidate.scoring_method
    )
    return f"{family}|{candidate.lookback_days}|{candidate.state_match_mode}"


def _stable_text_seed(value: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(value))


def _hyperband_candidates(
    *,
    pool: list[RouterCandidate],
    budget: int,
    prepared: pd.DataFrame,
    eligible: pd.DataFrame,
    strategy_cols: list[str],
    config: RouterSearchConfig,
    search_data: RouterSearchData,
) -> list[RouterCandidate]:
    survivors = pool
    for stride, keep_fraction in ((14, 0.25), (7, 0.5), (3, 1.0)):
        target = (
            budget if keep_fraction == 1.0 else max(budget, int(len(survivors) * keep_fraction))
        )
        scored = _proxy_score_candidates(
            candidates=survivors,
            prepared=prepared,
            eligible=eligible.iloc[::stride],
            strategy_cols=strategy_cols,
            config=config,
            search_data=search_data,
            progress=config.progress,
            phase=f"router-search hyperband stride={stride}",
        )
        survivors = [candidate for candidate, _score in scored[:target]]
        if len(survivors) <= budget:
            break
    return survivors[:budget]


def _smac_candidates(
    *,
    pool: list[RouterCandidate],
    budget: int,
    prepared: pd.DataFrame,
    eligible: pd.DataFrame,
    strategy_cols: list[str],
    config: RouterSearchConfig,
    search_data: RouterSearchData,
) -> list[RouterCandidate]:
    if len(pool) <= budget:
        return pool
    rng = random.Random(config.seed)
    bootstrap_size = min(len(pool), max(64, budget // 5))
    bootstrap = rng.sample(pool, bootstrap_size)
    observations = _proxy_score_candidates(
        candidates=bootstrap,
        prepared=prepared,
        eligible=eligible.iloc[::7],
        strategy_cols=strategy_cols,
        config=config,
        search_data=search_data,
        progress=config.progress,
        phase="router-search smac bootstrap",
    )
    observed_ids = {candidate.router_id for candidate, _score in observations}
    remaining = [candidate for candidate in pool if candidate.router_id not in observed_ids]
    selected = [candidate for candidate, _score in observations]
    while len(selected) < budget and remaining:
        features = np.asarray(
            [_encode_router_candidate(candidate) for candidate, _score in observations],
            dtype="float64",
        )
        targets = np.asarray([score for _candidate, score in observations], dtype="float64")
        model = RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=config.seed + len(selected),
            n_jobs=1,
        )
        model.fit(features, targets)
        proposal_pool = (
            rng.sample(remaining, min(len(remaining), max(2_000, budget * 2)))
            if len(remaining) > 2_000
            else remaining
        )
        proposal_features = np.asarray(
            [_encode_router_candidate(candidate) for candidate in proposal_pool],
            dtype="float64",
        )
        tree_predictions = np.vstack(
            [estimator.predict(proposal_features) for estimator in model.estimators_]
        )
        acquisition = tree_predictions.mean(axis=0) + tree_predictions.std(axis=0)
        batch_size = min(64, budget - len(selected), len(proposal_pool))
        chosen_indices = np.argpartition(acquisition, -batch_size)[-batch_size:]
        chosen = [proposal_pool[index] for index in chosen_indices]
        new_observations = _proxy_score_candidates(
            candidates=chosen,
            prepared=prepared,
            eligible=eligible.iloc[::7],
            strategy_cols=strategy_cols,
            config=config,
            search_data=search_data,
            progress=config.progress,
            phase=f"router-search smac selected={len(selected)}/{budget}",
        )
        observations.extend(new_observations)
        selected.extend(chosen)
        chosen_ids = {candidate.router_id for candidate in chosen}
        remaining = [candidate for candidate in remaining if candidate.router_id not in chosen_ids]
    return selected[:budget]


def _proxy_score_candidates(
    *,
    candidates: list[RouterCandidate],
    prepared: pd.DataFrame,
    eligible: pd.DataFrame,
    strategy_cols: list[str],
    config: RouterSearchConfig,
    search_data: RouterSearchData,
    progress: bool,
    phase: str,
) -> list[tuple[RouterCandidate, float]]:
    score_cache: dict[tuple[Any, ...], tuple[dict[str, float], dict[str, int]]] = {}
    feature_cache: dict[str, FeatureMatrix] = {}
    scored = []
    candidate_items = tqdm(
        candidates,
        total=len(candidates),
        desc=phase,
        unit="router",
        mininterval=1.0,
        dynamic_ncols=True,
        position=config.progress_position,
        disable=not progress,
        leave=False,
    )
    for candidate in candidate_items:
        frame = _evaluate_router_candidate(
            prepared=prepared,
            eligible=eligible,
            strategy_cols=strategy_cols,
            candidate=candidate,
            config=config,
            score_cache=score_cache,
            feature_cache=feature_cache,
            search_data=search_data,
        )
        returns = pd.to_numeric(frame["selected_return_pct"], errors="coerce")
        proxy = (
            float(returns.mean())
            - abs(_returns_max_drawdown_pct(returns)) * 0.5
            - float((returns < 0).mean() * 5.0)
            - float(frame["switched"].sum()) * 0.01
        )
        scored.append((candidate, proxy))
    return sorted(scored, key=lambda item: item[1], reverse=True)


def _encode_router_candidate(candidate: RouterCandidate) -> list[float]:
    return [
        float(_stable_text_seed(candidate.scoring_method) % 1000),
        float(candidate.lookback_days),
        float(_stable_text_seed(candidate.feature_set) % 100),
        float(_stable_text_seed(candidate.state_subset) % 1000),
        float(_stable_text_seed(candidate.state_match_mode) % 100),
        float(candidate.state_similarity_threshold),
        float(_stable_text_seed(candidate.state_weight_profile) % 100),
        float(candidate.ewm_halflife_days),
        float(candidate.min_samples),
        float(candidate.min_hold_days),
        float(candidate.switch_margin_threshold),
    ]


def _candidate_score_signature(candidate: RouterCandidate) -> tuple[Any, ...]:
    return (
        candidate.scoring_method,
        candidate.lookback_days,
        candidate.feature_set,
        candidate.knn_k,
        candidate.state_subset,
        candidate.state_match_mode,
        candidate.state_similarity_threshold,
        candidate.state_weight_profile,
        candidate.ewm_halflife_days,
    )


def write_rolling_router_report(
    *,
    output: Path,
    dense: pd.DataFrame,
    summary: pd.DataFrame,
    non_overlap: pd.DataFrame,
    config: RouterConfig,
) -> None:
    """Write router evaluation artifacts."""

    output.mkdir(parents=True, exist_ok=True)
    dense.to_csv(output / "router_predictions.csv", index=False)
    summary.to_csv(output / "router_dense_scores.csv", index=False)
    non_overlap.to_csv(output / "router_non_overlap_scores.csv", index=False)
    _write_report(
        output / "router_report.md",
        dense=dense,
        summary=summary,
        non_overlap=non_overlap,
        config=config,
    )


def write_single_strategy_router_search_report(
    *,
    output: Path,
    predictions: pd.DataFrame,
    dense_summary: pd.DataFrame,
    offset_sensitivity: pd.DataFrame,
    utility: pd.DataFrame,
    config: RouterSearchConfig,
) -> None:
    """Write single-strategy router search artifacts."""

    output.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output / "router_search_predictions.csv", index=False)
    dense_summary.to_csv(output / "router_search_dense_scores.csv", index=False)
    offset_sensitivity.to_csv(output / "router_offset_sensitivity.csv", index=False)
    utility.to_csv(output / "router_utility_scores.csv", index=False)
    _router_shortlist(
        dense_summary=dense_summary,
        utility=utility,
        limit=config.top_predictions,
    ).to_csv(output / "router_shortlist.csv", index=False)
    _write_router_search_report(
        output / "router_search_report.md",
        dense_summary=dense_summary,
        offset_sensitivity=offset_sensitivity,
        utility=utility,
        config=config,
    )


def _router_candidates(
    config: RouterSearchConfig, labels: pd.DataFrame
) -> Iterable[RouterCandidate]:
    if config.catalog_version == "v2":
        yield from _router_candidates_v2(config, labels)
        return
    if config.catalog_version != "v1":
        raise ValueError(f"Unsupported router catalog version: {config.catalog_version}")
    yield from _router_candidates_v1(config, labels)


def _router_candidates_v1(
    config: RouterSearchConfig, labels: pd.DataFrame
) -> Iterable[RouterCandidate]:
    feature_methods = {"feature_knn_mean", "feature_knn_median", "feature_knn_mean_minus_dd"}
    state_methods = {"same_state_mean", "same_state_mean_minus_dd"}
    score_specs: list[tuple[str, int, str, int]] = []
    counter = 0
    for lookback in config.lookback_days:
        for method in config.scoring_methods:
            feature_sets = (
                config.feature_sets if method in feature_methods | state_methods else ("none",)
            )
            k_values = config.knn_k if method in feature_methods else (0,)
            for feature_set in feature_sets:
                if method in feature_methods and not _feature_columns(labels, feature_set):
                    continue
                if method in state_methods and not _state_columns(labels, feature_set):
                    continue
                for knn_k in k_values:
                    score_specs.append((method, lookback, feature_set, knn_k))

    policy_specs = [
        (min_hold, switch_margin)
        for min_hold in config.min_hold_days
        for switch_margin in config.switch_margin_thresholds
    ]

    for min_hold, switch_margin in policy_specs:
        for method, lookback, feature_set, knn_k in score_specs:
            counter += 1
            yield RouterCandidate(
                router_id=f"router_{counter:06d}",
                scoring_method=method,
                lookback_days=lookback,
                feature_set=feature_set,
                knn_k=knn_k,
                min_samples=config.min_samples,
                min_hold_days=min_hold,
                switch_margin_threshold=switch_margin,
            )


def _router_candidates_v2(
    _config: RouterSearchConfig, labels: pd.DataFrame
) -> Iterable[RouterCandidate]:
    lookbacks = (30, 45, 60, 90, 120, 180, 270, 365, 540, 720)
    holds = (0, 3, 7, 14, 21, 30, 45, 60)
    margins = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0)
    min_samples_values = (3, 5, 10, 20, 30)
    rolling_methods = (
        "rolling_mean",
        "rolling_median",
        "rolling_mean_minus_dd",
        "rolling_median_minus_dd",
        "rolling_mean_minus_neg_rate",
        "rolling_q25",
        "rolling_q40",
        "rolling_mean_minus_std",
        "rolling_downside_ratio",
    )
    state_methods = (
        "same_state_mean",
        "same_state_median",
        "same_state_mean_minus_dd",
        "same_state_median_minus_dd",
        "same_state_q25",
        "same_state_mean_minus_std",
        "same_state_downside_ratio",
    )
    score_specs: list[RouterCandidate] = []
    for method in rolling_methods:
        for lookback in lookbacks:
            score_specs.append(
                RouterCandidate(
                    router_id="",
                    scoring_method=method,
                    lookback_days=lookback,
                    feature_set="none",
                    knn_k=0,
                )
            )
    for half_life in (7, 14, 30, 60, 90, 180):
        for lookback in lookbacks:
            score_specs.append(
                RouterCandidate(
                    router_id="",
                    scoring_method="rolling_ewm_mean",
                    lookback_days=lookback,
                    feature_set="none",
                    knn_k=0,
                    ewm_halflife_days=half_life,
                )
            )
    for subset_name, columns in STATE_SUBSETS.items():
        if not all(column in labels.columns for column in columns):
            continue
        for match_mode, thresholds in (
            ("exact", (1.0,)),
            ("similarity", (0.5, 0.65, 0.8)),
        ):
            for threshold in thresholds:
                weight_profiles = (
                    ("equal",)
                    if match_mode == "exact"
                    else ("equal", "trend_heavy", "momentum_heavy", "structure_heavy")
                )
                for weight_profile in weight_profiles:
                    for method in state_methods:
                        for lookback in lookbacks:
                            score_specs.append(
                                RouterCandidate(
                                    router_id="",
                                    scoring_method=method,
                                    lookback_days=lookback,
                                    feature_set="pinescript",
                                    knn_k=0,
                                    state_subset=subset_name,
                                    state_match_mode=match_mode,
                                    state_similarity_threshold=threshold,
                                    state_weight_profile=weight_profile,
                                )
                            )

    counter = 0
    for score in score_specs:
        for min_samples in min_samples_values:
            for hold in holds:
                for margin in margins:
                    counter += 1
                    yield RouterCandidate(
                        router_id=f"router_v2_{counter:07d}",
                        scoring_method=score.scoring_method,
                        lookback_days=score.lookback_days,
                        feature_set=score.feature_set,
                        knn_k=score.knn_k,
                        state_subset=score.state_subset,
                        state_match_mode=score.state_match_mode,
                        state_similarity_threshold=score.state_similarity_threshold,
                        state_weight_profile=score.state_weight_profile,
                        ewm_halflife_days=score.ewm_halflife_days,
                        min_samples=min_samples,
                        min_hold_days=hold,
                        switch_margin_threshold=margin,
                    )


def _evaluate_router_candidate(
    *,
    prepared: pd.DataFrame,
    eligible: pd.DataFrame,
    strategy_cols: list[str],
    candidate: RouterCandidate,
    config: RouterSearchConfig,
    score_cache: dict[tuple[Any, ...], tuple[dict[str, float], dict[str, int]]],
    feature_cache: dict[str, FeatureMatrix],
    search_data: RouterSearchData,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    held_strategy = ""
    held_since: pd.Timestamp | None = None
    previous_selected = ""
    for _, row in eligible.iterrows():
        asof = row["asof"]
        available = _available_strategies(row, strategy_cols)
        cache_key = (
            candidate.scoring_method,
            candidate.lookback_days,
            candidate.feature_set,
            candidate.knn_k,
            candidate.state_subset,
            candidate.state_match_mode,
            candidate.state_similarity_threshold,
            candidate.state_weight_profile,
            candidate.ewm_halflife_days,
            asof,
        )
        cached = score_cache.get(cache_key)
        if cached is None:
            train_positions = _training_positions(
                search_data,
                asof=asof,
                lookback_days=candidate.lookback_days,
                min_available_strategies=config.min_available_strategies,
            )
            cached = _candidate_scores(
                prepared=prepared,
                train_positions=train_positions,
                row=row,
                available=available,
                candidate=candidate,
                feature_cache=feature_cache,
                search_data=search_data,
            )
            score_cache[cache_key] = cached
        scores, sample_counts = cached
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        raw_strategy = ranked[0][0] if ranked else (available[0] if available else "")
        best_score = ranked[0][1] if ranked else math.nan
        second_score = ranked[1][1] if len(ranked) > 1 else math.nan
        score_margin = best_score - second_score if not math.isnan(second_score) else math.nan
        raw_samples = sample_counts.get(raw_strategy, 0)

        selected_strategy = raw_strategy
        if raw_samples < candidate.min_samples and available:
            selected_strategy = available[0]

        if selected_strategy and held_strategy and held_strategy in available:
            held_days = (asof - held_since).days if held_since is not None else 0
            held_score = scores.get(held_strategy, -math.inf)
            improvement = best_score - held_score
            if (
                held_days < candidate.min_hold_days
                or improvement < candidate.switch_margin_threshold
            ):
                selected_strategy = held_strategy

        if selected_strategy != held_strategy:
            held_strategy = selected_strategy
            held_since = asof

        selected_return = float(row.get(f"return_{selected_strategy}", 0.0))
        best_return = float(row["best_return_pct"])
        switched = bool(previous_selected and selected_strategy != previous_selected)
        previous_selected = selected_strategy
        rows.append(
            {
                "router": candidate.router_id,
                "asof": asof.isoformat(),
                "label_end": row["label_end"].isoformat(),
                "selected_strategy": selected_strategy,
                "raw_strategy": raw_strategy,
                "switched": switched,
                "selected_return_pct": selected_return,
                "best_strategy": row["best_strategy"],
                "best_return_pct": best_return,
                "regret_pct": best_return - selected_return,
                "best_score": best_score,
                "second_score": second_score,
                "score_margin": score_margin,
                "score_samples": raw_samples,
                "scoring_method": candidate.scoring_method,
                "lookback_days": candidate.lookback_days,
                "feature_set": candidate.feature_set,
                "knn_k": candidate.knn_k,
                "state_subset": candidate.state_subset,
                "state_match_mode": candidate.state_match_mode,
                "state_similarity_threshold": candidate.state_similarity_threshold,
                "state_weight_profile": candidate.state_weight_profile,
                "ewm_halflife_days": candidate.ewm_halflife_days,
                "min_samples": candidate.min_samples,
                "min_hold_days": candidate.min_hold_days,
                "switch_margin_threshold": candidate.switch_margin_threshold,
            }
        )
    return pd.DataFrame(rows)


def _candidate_scores(
    *,
    prepared: pd.DataFrame,
    train_positions: np.ndarray,
    row: pd.Series,
    available: list[str],
    candidate: RouterCandidate,
    feature_cache: dict[str, FeatureMatrix],
    search_data: RouterSearchData,
) -> tuple[dict[str, float], dict[str, int]]:
    if len(train_positions) == 0 or not available:
        return {}, {}
    score_positions = train_positions
    if candidate.scoring_method.startswith("feature_knn"):
        score_positions = _nearest_feature_positions_fast(
            prepared=prepared,
            train_positions=train_positions,
            row=row,
            feature_set=candidate.feature_set,
            k=candidate.knn_k,
            feature_cache=feature_cache,
        )
    elif candidate.scoring_method.startswith("same_state"):
        state_cols = _candidate_state_columns(prepared, candidate)
        score_positions = _same_state_positions(
            prepared=prepared,
            train_positions=train_positions,
            row=row,
            state_cols=state_cols,
            match_mode=candidate.state_match_mode,
            similarity_threshold=candidate.state_similarity_threshold,
            weight_profile=candidate.state_weight_profile,
        )

    scores: dict[str, float] = {}
    samples: dict[str, int] = {}
    for strategy in available:
        strategy_idx = search_data.strategy_index.get(strategy)
        if strategy_idx is None:
            continue
        values = search_data.returns[score_positions, strategy_idx]
        returns = values[~np.isnan(values)]
        samples[strategy] = len(returns)
        if len(returns) == 0:
            continue
        scores[strategy] = _score_return_array(
            returns,
            candidate.scoring_method,
            positions=score_positions[~np.isnan(values)],
            search_data=search_data,
            candidate=candidate,
        )
    return scores, samples


def _router_search_data(prepared: pd.DataFrame, strategy_cols: list[str]) -> RouterSearchData:
    strategy_ids = tuple(column.removeprefix("return_") for column in strategy_cols)
    returns = (
        prepared.loc[:, strategy_cols]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype="float64")
    )
    return RouterSearchData(
        strategy_ids=strategy_ids,
        strategy_index={strategy: index for index, strategy in enumerate(strategy_ids)},
        returns=returns,
        label_end_ns=prepared["label_end"].astype("int64").to_numpy(),
        available_counts=prepared["available_strategy_count"].to_numpy(dtype="int64"),
    )


def _training_positions(
    search_data: RouterSearchData,
    *,
    asof: pd.Timestamp,
    lookback_days: int,
    min_available_strategies: int,
) -> np.ndarray:
    asof_ns = asof.value
    start_ns = (asof - pd.Timedelta(days=lookback_days)).value
    mask = (
        (search_data.label_end_ns <= asof_ns)
        & (search_data.label_end_ns >= start_ns)
        & (search_data.available_counts >= min_available_strategies)
    )
    return np.flatnonzero(mask)


def _score_return_series(returns: pd.Series, method: str) -> float:
    if method.endswith("median"):
        return float(returns.median())
    mean = float(returns.mean())
    if method.endswith("mean_minus_dd"):
        return mean - abs(_returns_max_drawdown_pct(returns))
    if method.endswith("mean_minus_neg_rate"):
        return mean - float((returns < 0).mean() * 10.0)
    return mean


def _score_return_array(
    returns: np.ndarray,
    method: str,
    *,
    positions: np.ndarray,
    search_data: RouterSearchData,
    candidate: RouterCandidate,
) -> float:
    if method.endswith("ewm_mean"):
        latest = np.max(search_data.label_end_ns[positions])
        age_days = (latest - search_data.label_end_ns[positions]) / (86_400 * 1e9)
        weights = np.power(0.5, age_days / max(candidate.ewm_halflife_days, 1))
        return float(np.average(returns, weights=weights))
    if method.endswith("median"):
        return float(np.median(returns))
    if method.endswith("q25"):
        return float(np.quantile(returns, 0.25))
    if method.endswith("q40"):
        return float(np.quantile(returns, 0.40))
    mean = float(np.mean(returns))
    if method.endswith("mean_minus_dd"):
        return mean - abs(_returns_array_max_drawdown_pct(returns))
    if method.endswith("median_minus_dd"):
        return float(np.median(returns)) - abs(_returns_array_max_drawdown_pct(returns))
    if method.endswith("mean_minus_neg_rate"):
        return mean - float(np.mean(returns < 0) * 10.0)
    if method.endswith("mean_minus_std"):
        return mean - float(np.std(returns))
    if method.endswith("downside_ratio"):
        downside = returns[returns < 0]
        downside_deviation = float(np.std(downside)) if len(downside) > 1 else 0.0
        return mean / max(downside_deviation, 0.1)
    return mean


def _feature_columns(df: pd.DataFrame, feature_set: str) -> list[str]:
    ohlcv_cols = [column for column in FEATURE_COLUMNS if column in df.columns]
    pine_cols = [column for column in df.columns if column.startswith("router_ps_")]
    if feature_set == "ohlcv":
        return ohlcv_cols
    if feature_set == "pinescript":
        return pine_cols
    if feature_set == "mixed":
        return ohlcv_cols + pine_cols
    return []


def _state_columns(df: pd.DataFrame, feature_set: str) -> list[str]:
    candidates = [
        "router_ps_supertrend_dir",
        "router_ps_di_side",
        "router_ps_adx_strong",
        "router_ps_squeeze_on",
        "router_ps_wavetrend_zone",
        "router_ps_macd_phase",
        "router_ps_trendline_break_side",
        "router_ps_killzone_code",
        "router_ps_smc_internal_bias",
        "router_ps_smc_swing_bias",
        "router_ps_smc_zone_code",
        "router_ps_smc_ob_active_side",
    ]
    if feature_set not in {"pinescript", "mixed"}:
        return []
    return [column for column in candidates if column in df.columns]


def _candidate_state_columns(df: pd.DataFrame, candidate: RouterCandidate) -> list[str]:
    if candidate.state_subset in STATE_SUBSETS:
        return [column for column in STATE_SUBSETS[candidate.state_subset] if column in df.columns]
    return _state_columns(df, candidate.feature_set)


def _nearest_feature_rows(
    *,
    train: pd.DataFrame,
    row: pd.Series,
    feature_cols: list[str],
    k: int,
) -> pd.DataFrame:
    if not feature_cols:
        return train
    train_features = train[feature_cols].apply(pd.to_numeric, errors="coerce")
    current = pd.to_numeric(row[feature_cols], errors="coerce")
    valid_cols = [
        column
        for column in feature_cols
        if not pd.isna(current[column]) and train_features[column].notna().sum() >= 5
    ]
    if not valid_cols:
        return train
    subset = train_features[valid_cols].copy()
    means = subset.mean()
    stds = subset.std(ddof=0).replace(0.0, 1.0)
    z_train = (subset - means) / stds
    z_current = (current[valid_cols] - means) / stds
    distances = ((z_train - z_current) ** 2).sum(axis=1).pow(0.5)
    return train.loc[distances.sort_values().head(k).index]


def _nearest_feature_positions_fast(
    *,
    prepared: pd.DataFrame,
    train_positions: np.ndarray,
    row: pd.Series,
    feature_set: str,
    k: int,
    feature_cache: dict[str, FeatureMatrix],
) -> np.ndarray:
    matrix = feature_cache.get(feature_set)
    if matrix is None:
        columns = tuple(_feature_columns(prepared, feature_set))
        values = (
            prepared.loc[:, list(columns)]
            .apply(pd.to_numeric, errors="coerce")
            .to_numpy(dtype="float64")
            if columns
            else np.empty((len(prepared), 0), dtype="float64")
        )
        matrix = FeatureMatrix(columns=columns, values=values)
        feature_cache[feature_set] = matrix
    if not matrix.columns:
        return train_positions

    current_position = int(row.name)
    train_values = matrix.values[train_positions]
    current_values = matrix.values[current_position]
    valid_cols = (~np.isnan(current_values)) & (np.sum(~np.isnan(train_values), axis=0) >= 5)
    if not np.any(valid_cols):
        return train_positions

    subset = train_values[:, valid_cols]
    current = current_values[valid_cols]
    means = np.nanmean(subset, axis=0)
    stds = np.nanstd(subset, axis=0)
    stds = np.where(stds == 0.0, 1.0, stds)
    z_train = (subset - means) / stds
    z_current = (current - means) / stds
    diffs = z_train - z_current
    diffs = np.where(np.isnan(diffs), 0.0, diffs)
    distances = np.sqrt(np.sum(diffs * diffs, axis=1))
    take = min(k, len(distances))
    if take <= 0:
        return train_positions
    nearest_order = np.argpartition(distances, take - 1)[:take]
    return train_positions[nearest_order]


def _same_state_rows(
    *,
    train: pd.DataFrame,
    row: pd.Series,
    state_cols: list[str],
) -> pd.DataFrame:
    if not state_cols:
        return train
    mask = pd.Series(True, index=train.index)
    for column in state_cols:
        value = row[column]
        if pd.isna(value):
            continue
        mask &= train[column] == value
    subset = train[mask]
    return subset if not subset.empty else train


def _same_state_positions(
    *,
    prepared: pd.DataFrame,
    train_positions: np.ndarray,
    row: pd.Series,
    state_cols: list[str],
    match_mode: str = "exact",
    similarity_threshold: float = 1.0,
    weight_profile: str = "equal",
) -> np.ndarray:
    if not state_cols:
        return train_positions
    if match_mode == "similarity":
        matches = np.zeros(len(train_positions), dtype="float64")
        compared = np.zeros(len(train_positions), dtype="float64")
        for column in state_cols:
            value = row[column]
            if pd.isna(value):
                continue
            train_values = prepared[column].to_numpy()[train_positions]
            valid = ~pd.isna(train_values)
            weight = _state_column_weight(column, weight_profile)
            compared += valid * weight
            matches += (valid & (train_values == value)) * weight
        similarity = np.divide(
            matches,
            compared,
            out=np.zeros_like(matches),
            where=compared > 0,
        )
        mask = similarity >= similarity_threshold
        if not np.any(mask):
            return train_positions
        return train_positions[mask]

    mask = np.ones(len(train_positions), dtype=bool)
    for column in state_cols:
        value = row[column]
        if pd.isna(value):
            continue
        mask &= prepared[column].to_numpy()[train_positions] == value
    if not np.any(mask):
        return train_positions
    return train_positions[mask]


def _state_column_weight(column: str, profile: str) -> float:
    if profile == "trend_heavy" and any(
        token in column for token in ("supertrend", "di_side", "adx")
    ):
        return 3.0
    if profile == "momentum_heavy" and any(token in column for token in ("wavetrend", "macd")):
        return 3.0
    if profile == "structure_heavy" and "smc_" in column:
        return 3.0
    return 1.0


def _summarize_router_search_dense(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for router, group in predictions.groupby("router", sort=False):
        returns = pd.to_numeric(group["selected_return_pct"], errors="coerce")
        regret = pd.to_numeric(group["regret_pct"], errors="coerce")
        first = group.iloc[0]
        rows.append(
            {
                "router": router,
                "rows": len(group),
                "avg_forward_return_pct": float(returns.mean()),
                "median_forward_return_pct": float(returns.median()),
                "worst_forward_return_pct": float(returns.min()),
                "negative_rows": int((returns < 0).sum()),
                "switches": int(group["switched"].sum()),
                "avg_regret_pct": float(regret.mean()),
                "scoring_method": first["scoring_method"],
                "lookback_days": int(first["lookback_days"]),
                "feature_set": first["feature_set"],
                "knn_k": int(first["knn_k"]),
                "state_subset": first["state_subset"],
                "state_match_mode": first["state_match_mode"],
                "state_similarity_threshold": float(first["state_similarity_threshold"]),
                "state_weight_profile": first["state_weight_profile"],
                "ewm_halflife_days": int(first["ewm_halflife_days"]),
                "min_samples": int(first["min_samples"]),
                "min_hold_days": int(first["min_hold_days"]),
                "switch_margin_threshold": float(first["switch_margin_threshold"]),
            }
        )
    return pd.DataFrame(rows).sort_values("avg_forward_return_pct", ascending=False)


def _offset_sensitivity(predictions: pd.DataFrame, *, every_days: int) -> pd.DataFrame:
    rows = []
    for router, group in predictions.groupby("router", sort=False):
        for offset in range(every_days):
            selected = _select_non_overlap_rows(group, every_days=every_days, offset_days=offset)
            if selected.empty:
                rows.append(
                    {
                        "router": router,
                        "offset_days": offset,
                        "periods": 0,
                        "total_return_pct": 0.0,
                        "oracle_total_return_pct": 0.0,
                        "oracle_gap_pct": 0.0,
                        "oracle_capture_ratio": 1.0,
                        "mean_regret_pct": 0.0,
                        "p90_regret_pct": 0.0,
                        "worst_regret_pct": 0.0,
                        "oracle_hit_rate": 0.0,
                        "max_drawdown_pct": 0.0,
                        "negative_periods": 0,
                        "switches": 0,
                    }
                )
                continue
            returns = pd.to_numeric(selected["selected_return_pct"], errors="coerce")
            oracle_returns = pd.to_numeric(selected["best_return_pct"], errors="coerce")
            regret = pd.to_numeric(selected["regret_pct"], errors="coerce")
            equity = _compound_returns(returns)
            oracle_equity = _compound_returns(oracle_returns)
            router_total_return = (
                (float(equity.iloc[-1]) / 10_000.0 - 1.0) * 100.0 if len(equity) else 0.0
            )
            oracle_total_return = (
                (float(oracle_equity.iloc[-1]) / 10_000.0 - 1.0) * 100.0
                if len(oracle_equity)
                else 0.0
            )
            oracle_growth = 1.0 + oracle_total_return / 100.0
            router_growth = 1.0 + router_total_return / 100.0
            rows.append(
                {
                    "router": router,
                    "offset_days": offset,
                    "periods": len(selected),
                    "total_return_pct": router_total_return,
                    "oracle_total_return_pct": oracle_total_return,
                    "oracle_gap_pct": oracle_total_return - router_total_return,
                    "oracle_capture_ratio": (
                        router_growth / oracle_growth if oracle_growth > 0 else math.nan
                    ),
                    "mean_regret_pct": float(regret.mean()),
                    "p90_regret_pct": float(regret.quantile(0.90)),
                    "worst_regret_pct": float(regret.max()),
                    "oracle_hit_rate": float(
                        selected["selected_strategy"].eq(selected["best_strategy"]).mean()
                    ),
                    "max_drawdown_pct": _max_drawdown_pct(equity),
                    "negative_periods": int((returns < 0).sum()),
                    "switches": int(
                        selected["selected_strategy"]
                        .ne(selected["selected_strategy"].shift())
                        .sum()
                        - 1
                    )
                    if len(selected)
                    else 0,
                }
            )
    return pd.DataFrame(rows)


def _router_utility_summary(offset_sensitivity: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for router, group in offset_sensitivity.groupby("router", sort=False):
        returns = pd.to_numeric(group["total_return_pct"], errors="coerce")
        drawdowns = pd.to_numeric(group["max_drawdown_pct"], errors="coerce")
        negative = pd.to_numeric(group["negative_periods"], errors="coerce")
        switches = pd.to_numeric(group["switches"], errors="coerce")
        oracle_returns = pd.to_numeric(group["oracle_total_return_pct"], errors="coerce")
        oracle_gaps = pd.to_numeric(group["oracle_gap_pct"], errors="coerce")
        capture = pd.to_numeric(group["oracle_capture_ratio"], errors="coerce")
        mean_regret = pd.to_numeric(group["mean_regret_pct"], errors="coerce")
        p90_regret = pd.to_numeric(group["p90_regret_pct"], errors="coerce")
        worst_regret = pd.to_numeric(group["worst_regret_pct"], errors="coerce")
        hit_rate = pd.to_numeric(group["oracle_hit_rate"], errors="coerce")
        return_iqr = float(returns.quantile(0.75) - returns.quantile(0.25))
        worst_dd = float(drawdowns.min())
        utility = (
            -float(mean_regret.median())
            - float(mean_regret.quantile(0.90))
            - float(worst_regret.median()) * 0.25
            - abs(worst_dd) * 0.10
            - float(switches.median()) * 0.10
        )
        first = group.iloc[0]
        rows.append(
            {
                "router": router,
                "utility_score": utility,
                "scoring_objective": "oracle_regret_v1",
                "median_mean_regret_pct": float(mean_regret.median()),
                "p90_mean_regret_pct": float(mean_regret.quantile(0.90)),
                "median_p90_regret_pct": float(p90_regret.median()),
                "median_worst_regret_pct": float(worst_regret.median()),
                "median_oracle_hit_rate": float(hit_rate.median()),
                "median_oracle_capture_ratio": float(capture.median()),
                "median_oracle_total_return_pct": float(oracle_returns.median()),
                "median_oracle_gap_pct": float(oracle_gaps.median()),
                "median_total_return_pct": float(returns.median()),
                "min_total_return_pct": float(returns.min()),
                "max_total_return_pct": float(returns.max()),
                "return_iqr_pct": return_iqr,
                "worst_max_drawdown_pct": worst_dd,
                "median_max_drawdown_pct": float(drawdowns.median()),
                "median_negative_periods": float(negative.median()),
                "median_switches": float(switches.median()),
                "offsets": len(group),
                "periods_median": float(group["periods"].median()),
                "example_offset": int(first["offset_days"]),
            }
        )
    return pd.DataFrame(rows).sort_values("utility_score", ascending=False)


def _router_shortlist(
    *,
    dense_summary: pd.DataFrame,
    utility: pd.DataFrame,
    limit: int,
) -> pd.DataFrame:
    """Merge top oracle-regret scores with complete frozen router parameters."""

    if limit <= 0 or utility.empty or dense_summary.empty:
        return pd.DataFrame()
    top = utility.head(limit).copy()
    params = dense_summary.drop_duplicates("router", keep="first")
    return top.merge(params, on="router", how="left", suffixes=("", "_dense"))


def _returns_max_drawdown_pct(returns: pd.Series) -> float:
    return _max_drawdown_pct(_compound_returns(returns))


def _returns_array_max_drawdown_pct(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    equity = 10_000.0 * np.cumprod(1.0 + returns / 100.0)
    peaks = np.maximum.accumulate(equity)
    drawdowns = equity / peaks - 1.0
    return float(np.min(drawdowns) * 100.0)


def _prepare_labels(labels: pd.DataFrame) -> pd.DataFrame:
    df = labels.copy()
    for column in ["asof", "label_end"]:
        if column not in df.columns:
            raise ValueError(f"rolling labels missing column: {column}")
        df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    df = df.dropna(subset=["asof", "label_end"]).sort_values("asof").reset_index(drop=True)
    if "available_strategy_count" not in df.columns:
        strategy_cols = _strategy_return_columns(df)
        df["available_strategy_count"] = df[strategy_cols].notna().sum(axis=1)
    return df


def _strategy_return_columns(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.columns
        if column.startswith("return_") and column != "return_dispersion_pct"
    ]


def _training_rows(
    df: pd.DataFrame,
    *,
    asof: pd.Timestamp,
    lookback_days: int,
    min_available_strategies: int,
) -> pd.DataFrame:
    start = asof - pd.Timedelta(days=lookback_days)
    return df[
        (df["label_end"] <= asof)
        & (df["label_end"] >= start)
        & (df["available_strategy_count"] >= min_available_strategies)
    ].copy()


def _available_strategies(row: pd.Series, strategy_cols: list[str]) -> list[str]:
    available: list[str] = []
    for column in strategy_cols:
        value = row[column]
        if not pd.isna(value):
            available.append(column.removeprefix("return_"))
    return available


def _equal_weights(strategies: list[str]) -> dict[str, float]:
    if not strategies:
        return {}
    weight = 1.0 / len(strategies)
    return dict.fromkeys(strategies, weight)


def _rolling_top_weights(
    train: pd.DataFrame,
    available: list[str],
    *,
    top_n: int,
    top1_weight: float,
) -> dict[str, float]:
    if train.empty:
        return _fallback_top_weights(available, top_n=top_n, top1_weight=top1_weight)
    means = _strategy_means(train, available)
    if means.empty:
        return _fallback_top_weights(available, top_n=top_n, top1_weight=top1_weight)
    selected = means.sort_values(ascending=False).head(top_n).index.tolist()
    return _top_weights(selected, top1_weight=top1_weight)


def _feature_knn_top_weights(
    train: pd.DataFrame,
    row: pd.Series,
    available: list[str],
    *,
    k: int,
    top1_weight: float,
) -> dict[str, float]:
    if train.empty:
        return _rolling_top_weights(train, available, top_n=2, top1_weight=top1_weight)
    feature_cols = [column for column in FEATURE_COLUMNS if column in train.columns]
    if not feature_cols:
        return _rolling_top_weights(train, available, top_n=2, top1_weight=top1_weight)

    train_features = train[feature_cols].apply(pd.to_numeric, errors="coerce")
    current = pd.to_numeric(row[feature_cols], errors="coerce")
    valid_cols = [
        column
        for column in feature_cols
        if not pd.isna(current[column]) and train_features[column].notna().sum() >= 5
    ]
    if not valid_cols:
        return _rolling_top_weights(train, available, top_n=2, top1_weight=top1_weight)

    subset = train_features[valid_cols].copy()
    means = subset.mean()
    stds = subset.std(ddof=0).replace(0.0, 1.0)
    z_train = (subset - means) / stds
    z_current = (current[valid_cols] - means) / stds
    distances = ((z_train - z_current) ** 2).sum(axis=1).pow(0.5)
    neighbors = train.loc[distances.sort_values().head(k).index]
    means_by_strategy = _strategy_means(neighbors, available)
    if means_by_strategy.empty:
        return _rolling_top_weights(train, available, top_n=2, top1_weight=top1_weight)
    selected = means_by_strategy.sort_values(ascending=False).head(2).index.tolist()
    return _top_weights(selected, top1_weight=top1_weight)


def _strategy_means(train: pd.DataFrame, strategies: list[str]) -> pd.Series:
    values = {
        strategy: pd.to_numeric(train.get(f"return_{strategy}"), errors="coerce").mean()
        for strategy in strategies
        if f"return_{strategy}" in train.columns
    }
    return pd.Series(values, dtype=float).dropna()


def _fallback_top_weights(
    available: list[str], *, top_n: int, top1_weight: float
) -> dict[str, float]:
    return _top_weights(available[:top_n], top1_weight=top1_weight)


def _top_weights(strategies: list[str], *, top1_weight: float) -> dict[str, float]:
    if not strategies:
        return {}
    if len(strategies) == 1:
        return {strategies[0]: 1.0}
    remaining = max(0.0, 1.0 - top1_weight)
    tail_weight = remaining / (len(strategies) - 1)
    return {
        strategy: (top1_weight if index == 0 else tail_weight)
        for index, strategy in enumerate(strategies)
    }


def _score_weights(name: str, row: pd.Series, weights: dict[str, float]) -> dict[str, Any]:
    selected_return = 0.0
    selected = []
    normalized = _normalize_weights(weights)
    for strategy, weight in normalized.items():
        value = row.get(f"return_{strategy}", math.nan)
        if pd.isna(value):
            continue
        selected_return += float(value) * weight
        selected.append(f"{strategy}:{weight:.2f}")
    best_return = float(row["best_return_pct"])
    return {
        "router": name,
        "asof": row["asof"].isoformat(),
        "label_end": row["label_end"].isoformat(),
        "available_strategy_count": int(row["available_strategy_count"]),
        "best_strategy": row["best_strategy"],
        "best_return_pct": best_return,
        "selected_return_pct": selected_return,
        "regret_pct": best_return - selected_return,
        "hit_best": bool(
            normalized and max(normalized, key=normalized.get) == row["best_strategy"]
        ),
        "negative_selected": selected_return < 0,
        "weights": ";".join(selected),
    }


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(value for value in weights.values() if value > 0)
    if total <= 0:
        return {}
    return {key: value / total for key, value in weights.items() if value > 0}


def _summarize_dense(dense: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for router, group in dense.groupby("router", sort=False):
        returns = pd.to_numeric(group["selected_return_pct"], errors="coerce")
        regret = pd.to_numeric(group["regret_pct"], errors="coerce")
        rows.append(
            {
                "router": router,
                "rows": len(group),
                "avg_forward_return_pct": float(returns.mean()),
                "median_forward_return_pct": float(returns.median()),
                "worst_forward_return_pct": float(returns.min()),
                "negative_rows": int((returns < 0).sum()),
                "hit_best_rate": float(group["hit_best"].mean()),
                "avg_regret_pct": float(regret.mean()),
                "p25_forward_return_pct": float(returns.quantile(0.25)),
                "p75_forward_return_pct": float(returns.quantile(0.75)),
            }
        )
    return pd.DataFrame(rows).sort_values("avg_forward_return_pct", ascending=False)


def _non_overlap_summary(dense: pd.DataFrame, *, every_days: int) -> pd.DataFrame:
    rows = []
    for router, group in dense.groupby("router", sort=False):
        selected = _select_non_overlap_rows(group, every_days=every_days)
        returns = pd.to_numeric(selected["selected_return_pct"], errors="coerce")
        equity = _compound_returns(returns)
        rows.append(
            {
                "router": router,
                "periods": len(selected),
                "final_capital": float(equity.iloc[-1]) if len(equity) else 10_000.0,
                "total_return_pct": (
                    (float(equity.iloc[-1]) / 10_000.0 - 1.0) * 100.0 if len(equity) else 0.0
                ),
                "max_drawdown_pct": _max_drawdown_pct(equity),
                "negative_periods": int((returns < 0).sum()),
                "avg_period_return_pct": float(returns.mean()) if len(returns) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("total_return_pct", ascending=False)


def _select_non_overlap_rows(
    group: pd.DataFrame, *, every_days: int, offset_days: int = 0
) -> pd.DataFrame:
    sorted_group = group.sort_values("asof").copy()
    if sorted_group.empty:
        return sorted_group
    asofs = pd.to_datetime(sorted_group["asof"], utc=True).to_numpy()
    selected_positions: list[int] = []
    next_asof = asofs[0] + np.timedelta64(offset_days, "D")
    step = np.timedelta64(every_days, "D")
    for position, asof in enumerate(asofs):
        if asof >= next_asof:
            selected_positions.append(position)
            next_asof = asof + step
    return sorted_group.iloc[selected_positions]


def _compound_returns(returns: pd.Series) -> pd.Series:
    capital = 10_000.0
    values = []
    for value in returns.fillna(0.0):
        capital *= 1.0 + float(value) / 100.0
        values.append(capital)
    return pd.Series(values, dtype=float)


def _max_drawdown_pct(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min() * 100.0)


def _write_report(
    path: Path,
    *,
    dense: pd.DataFrame,
    summary: pd.DataFrame,
    non_overlap: pd.DataFrame,
    config: RouterConfig,
) -> None:
    if dense.empty:
        path.write_text("# Rolling Router Baseline\n\nNo rows.\n", encoding="utf-8")
        return

    lines = [
        "# Rolling Router Baseline",
        "",
        f"Validation start: **{config.validation_start}**",
        f"Minimum available strategies: **{config.min_available_strategies}**",
        f"Lookback: **{config.lookback_days}d**",
        "",
        "Dense rows score every eligible daily 30d-forward label. Non-overlap rows",
        "sample every configured horizon so returns are not compounded across",
        "overlapping future windows.",
        "",
        "## Dense Scores",
        "",
        _markdown_table(
            summary,
            [
                "router",
                "rows",
                "avg_forward_return_pct",
                "worst_forward_return_pct",
                "negative_rows",
                "hit_best_rate",
                "avg_regret_pct",
            ],
        ),
        "",
        "## Non-Overlap Scores",
        "",
        _markdown_table(
            non_overlap,
            [
                "router",
                "periods",
                "final_capital",
                "total_return_pct",
                "max_drawdown_pct",
                "negative_periods",
                "avg_period_return_pct",
            ],
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_router_search_report(
    path: Path,
    *,
    dense_summary: pd.DataFrame,
    offset_sensitivity: pd.DataFrame,
    utility: pd.DataFrame,
    config: RouterSearchConfig,
) -> None:
    if utility.empty:
        path.write_text("# Single-Strategy Router Search\n\nNo rows.\n", encoding="utf-8")
        return

    best = utility.head(20)
    top_routers = best["router"].tolist()
    dense_top = dense_summary[dense_summary["router"].isin(top_routers)].copy()
    offset_top = offset_sensitivity[offset_sensitivity["router"].isin(top_routers)].copy()
    lines = [
        "# Single-Strategy Router Search",
        "",
        "Routers select exactly one archived strategy; they never split capital",
        "between strategies and never choose cash.",
        "",
        f"Validation start: **{config.validation_start}**",
        f"Validation end: **{config.validation_end or 'open'}**",
        f"Minimum available strategies: **{config.min_available_strategies}**",
        f"Catalog version: **{config.catalog_version}**",
        f"Search algorithm: **{config.algorithm}**",
        f"Seed: **{config.seed}**",
        f"Non-overlap offsets: **0..{config.non_overlap_days - 1}d**",
        f"Catalog config offset: **{config.config_offset}**",
        f"Max configs evaluated: **{config.max_configs}**",
        f"Summary-only mode: **{config.summary_only}**",
        "",
        "Utility primarily minimizes robust regret to the single-strategy",
        "oracle. Drawdown and switch count are secondary penalties.",
        "",
        "## Top Utility Routers",
        "",
        _markdown_table(
            best,
            [
                "router",
                "utility_score",
                "median_mean_regret_pct",
                "p90_mean_regret_pct",
                "median_worst_regret_pct",
                "median_oracle_hit_rate",
                "median_oracle_capture_ratio",
                "median_oracle_gap_pct",
                "median_total_return_pct",
                "worst_max_drawdown_pct",
                "median_switches",
            ],
        ),
        "",
        "## Top Dense Diagnostics",
        "",
        _markdown_table(
            dense_top.sort_values("router"),
            [
                "router",
                "avg_forward_return_pct",
                "worst_forward_return_pct",
                "negative_rows",
                "switches",
                "scoring_method",
                "lookback_days",
                "feature_set",
                "state_subset",
                "state_match_mode",
                "state_similarity_threshold",
                "state_weight_profile",
                "ewm_halflife_days",
                "min_samples",
                "min_hold_days",
                "switch_margin_threshold",
            ],
        ),
        "",
        "## Top Offset Ranges",
        "",
        _markdown_table(
            _router_utility_summary(offset_top),
            [
                "router",
                "median_mean_regret_pct",
                "p90_mean_regret_pct",
                "median_oracle_hit_rate",
                "median_oracle_capture_ratio",
                "median_total_return_pct",
                "min_total_return_pct",
                "worst_max_drawdown_pct",
                "median_switches",
            ],
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "No rows."
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df[columns].iterrows():
        values = [_format_table_value(row[column]) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_table_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
