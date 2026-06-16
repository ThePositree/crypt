"""DSS v2 staged quality-diversity search runner."""

from __future__ import annotations

import csv
import json
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import pandas as pd

from backtester.data_contracts import StrategyData
from backtester.exit_geometry import ExitGeometryConfig, resolve_exit_levels
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
from backtester.strategy_discovery.signal_composer import SignalComposer

logger = logging.getLogger(__name__)

_STATE_VERSION = 2
_MAX_SIGNALS_PER_DAY = 10


class _Composer(Protocol):
    def build(self, config: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class BarrierMetrics:
    total: int
    tp_first: int
    sl_first: int
    timeout: int
    tp_first_rate: float
    sl_first_rate: float
    timeout_rate: float
    win_rate: float
    median_mae_atr: float
    median_mfe_atr: float
    median_bars_to_tp: float


@dataclass(frozen=True, slots=True)
class Stage1Result:
    candidate_id: str
    passed: bool
    rejection_reason: str
    signal_counts: dict[str, int]
    long_ratios: dict[str, float]
    median_stop_atr: dict[str, float]
    barrier_metrics: dict[str, BarrierMetrics]
    behavior: DSSBehavior | None
    candidate_class: str = "rejected"
    target_window: str = ""


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
            if not stage1.passed or stage1.behavior is None:
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
            archive.consider(stage2.candidate, stage2.behavior, stage2.score)

            if not _should_promote_to_stage3(stage2, archive, config):
                continue
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
            archive.consider(stage3.candidate, stage3.behavior, stage3.score)
            completed_stage3.add(candidate.candidate_id)
            stage3_evaluations += 1
        finally:
            if progress_callback is not None:
                progress_callback(1)

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


def evaluate_stage1(
    candidate: DSSCandidate,
    window_data: dict[str, StrategyData],
    config: DSSConfig,
    composer: _Composer | None = None,
) -> Stage1Result:
    composer = composer or SignalComposer()
    try:
        generate = composer.build(candidate.trial_config)
    except ValueError as exc:
        return _stage1_reject(candidate, f"invalid_config:{exc}")

    signal_counts: dict[str, int] = {}
    long_ratios: dict[str, float] = {}
    median_stop_atr: dict[str, float] = {}
    barrier_metrics: dict[str, BarrierMetrics] = {}
    total_signals = 0
    first_rejection_reason = ""
    passing_windows: list[str] = []

    for window in config.windows:
        data = window_data[window.label]
        try:
            signals = generate(data)
        except Exception as exc:
            return _stage1_reject(candidate, f"signal_generation_error:{type(exc).__name__}")
        count = len(signals)
        signal_counts[window.label] = count
        total_signals += count
        if count < config.min_trades_per_window:
            first_rejection_reason = first_rejection_reason or f"too_few_signals:{window.label}"
            if not config.specialist_windows:
                return Stage1Result(
                    candidate_id=candidate.candidate_id,
                    passed=False,
                    rejection_reason=f"too_few_signals:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        if count > _max_signals_for_window(window, data):
            first_rejection_reason = first_rejection_reason or f"overtrading:{window.label}"
            if not config.specialist_windows:
                return Stage1Result(
                    candidate_id=candidate.candidate_id,
                    passed=False,
                    rejection_reason=f"overtrading:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        long_ratios[window.label] = _long_ratio(signals)
        median_stop_atr[window.label] = _median_stop_atr(signals, data.primary)
        metrics = _barrier_metrics(
            signals=signals,
            primary=data.primary,
            rrr=candidate.rrr,
            ttl_bars=candidate.position_ttl_bars,
        )
        barrier_metrics[window.label] = metrics
        if metrics.tp_first_rate < config.min_barrier_tp_first_rate:
            first_rejection_reason = first_rejection_reason or f"weak_barrier_edge:{window.label}"
            if not config.specialist_windows:
                return Stage1Result(
                    candidate_id=candidate.candidate_id,
                    passed=False,
                    rejection_reason=f"weak_barrier_edge:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        if metrics.win_rate < config.min_barrier_win_rate or metrics.tp_first <= metrics.sl_first:
            first_rejection_reason = (
                first_rejection_reason or f"weak_barrier_win_rate:{window.label}"
            )
            if not config.specialist_windows:
                return Stage1Result(
                    candidate_id=candidate.candidate_id,
                    passed=False,
                    rejection_reason=f"weak_barrier_win_rate:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        passing_windows.append(window.label)

    if len(passing_windows) == len(config.windows):
        behavior = _balanced_behavior(
            candidate, total_signals=total_signals, long_ratios=long_ratios
        )
        return Stage1Result(
            candidate_id=candidate.candidate_id,
            passed=True,
            rejection_reason="",
            signal_counts=signal_counts,
            long_ratios=long_ratios,
            median_stop_atr=median_stop_atr,
            barrier_metrics=barrier_metrics,
            behavior=behavior,
            candidate_class="balanced",
        )

    specialist_passing_windows = [
        label for label in passing_windows if label in set(config.specialist_windows)
    ]
    if specialist_passing_windows:
        target_window = _best_specialist_window(specialist_passing_windows, barrier_metrics)
        behavior = _behavior_from_metrics(
            candidate,
            total_signals=total_signals,
            long_ratio=sum(long_ratios.values()) / max(len(long_ratios), 1),
            regime_strength=target_window,
        )
        return Stage1Result(
            candidate_id=candidate.candidate_id,
            passed=False,
            rejection_reason=f"specialist:{target_window}",
            signal_counts=signal_counts,
            long_ratios=long_ratios,
            median_stop_atr=median_stop_atr,
            barrier_metrics=barrier_metrics,
            behavior=behavior,
            candidate_class=f"specialist:{target_window}",
            target_window=target_window,
        )

    return Stage1Result(
        candidate_id=candidate.candidate_id,
        passed=False,
        rejection_reason=first_rejection_reason or "no_viable_window",
        signal_counts=signal_counts,
        long_ratios=long_ratios,
        median_stop_atr=median_stop_atr,
        barrier_metrics=barrier_metrics,
        behavior=None,
    )


def _best_specialist_window(
    passing_windows: list[str], barrier_metrics: dict[str, BarrierMetrics]
) -> str:
    return max(
        passing_windows,
        key=lambda label: (
            barrier_metrics[label].win_rate,
            barrier_metrics[label].tp_first_rate,
            barrier_metrics[label].total,
        ),
    )


def _balanced_behavior(
    candidate: DSSCandidate,
    *,
    total_signals: int,
    long_ratios: dict[str, float],
) -> DSSBehavior:
    return _behavior_from_metrics(
        candidate,
        total_signals=total_signals,
        long_ratio=sum(long_ratios.values()) / max(len(long_ratios), 1),
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


def _stage1_reject(candidate: DSSCandidate, reason: str) -> Stage1Result:
    return Stage1Result(
        candidate_id=candidate.candidate_id,
        passed=False,
        rejection_reason=reason,
        signal_counts={},
        long_ratios={},
        median_stop_atr={},
        barrier_metrics={},
        behavior=None,
    )


def _behavior_from_metrics(
    candidate: DSSCandidate,
    *,
    total_signals: int,
    long_ratio: float,
    regime_strength: str = "balanced",
) -> DSSBehavior:
    if long_ratio >= 0.95:
        side = "long_only"
    elif long_ratio <= 0.05:
        side = "short_only"
    elif long_ratio >= 0.65:
        side = "mixed_long_bias"
    elif long_ratio <= 0.35:
        side = "mixed_short_bias"
    else:
        side = "balanced"
    if total_signals < 100:
        trade_bucket = "low"
    elif total_signals < 400:
        trade_bucket = "medium"
    elif total_signals < 900:
        trade_bucket = "high"
    else:
        trade_bucket = "too_high"
    if candidate.position_ttl_bars <= 30:
        hold = "short"
    elif candidate.position_ttl_bars <= 54:
        hold = "medium"
    else:
        hold = "long"
    if candidate.atr_sl_mult < 1.0:
        risk = "tight_sl"
    elif candidate.atr_sl_mult <= 1.75:
        risk = "medium_sl"
    else:
        risk = "wide_sl"
    depth = len(candidate.filter_names)
    filter_depth = "3plus" if depth >= 3 else str(depth)
    return DSSBehavior(
        trigger_family=candidate.trigger_name,
        side_profile=side,
        trade_count_bucket=trade_bucket,
        hold_time_bucket=hold,
        risk_geometry=risk,
        regime_strength=regime_strength,
        filter_depth=filter_depth,
    )


def _long_ratio(signals: pd.DataFrame) -> float:
    if signals.empty or "side" not in signals:
        return 0.0
    return float((signals["side"] == "long").mean())


def _median_stop_atr(signals: pd.DataFrame, primary: pd.DataFrame) -> float:
    if signals.empty:
        return 0.0
    merged = signals.copy()
    merged["bar_time"] = pd.to_datetime(merged["bar_time"], utc=True)
    values: list[float] = []
    for _, row in merged.iterrows():
        bar_time = row["bar_time"]
        if bar_time not in primary.index:
            continue
        close = float(primary.loc[bar_time, "close"])
        stop = float(row["stop_price"])
        values.append(abs(close - stop) / max(close, 1e-9))
    if not values:
        return 0.0
    return float(pd.Series(values).median())


def _barrier_metrics(
    *,
    signals: pd.DataFrame,
    primary: pd.DataFrame,
    rrr: float,
    ttl_bars: int,
) -> BarrierMetrics:
    if signals.empty or primary.empty:
        return _empty_barrier_metrics()
    required = {"bar_time", "side"}
    if not required.issubset(signals.columns):
        return _empty_barrier_metrics()

    candles = primary.sort_index()
    atr = _entry_atr(candles)
    positions = {timestamp: idx for idx, timestamp in enumerate(candles.index)}
    outcomes = {"tp_first": 0, "sl_first": 0, "timeout": 0}
    mae_values: list[float] = []
    mfe_values: list[float] = []
    bars_to_tp: list[int] = []

    for _, row in signals.iterrows():
        bar_time = pd.Timestamp(row["bar_time"])
        if bar_time.tzinfo is None:
            bar_time = bar_time.tz_localize("UTC")
        else:
            bar_time = bar_time.tz_convert("UTC")
        idx = positions.get(bar_time)
        if idx is None:
            continue
        entry_atr = float(atr.iloc[idx])
        if not pd.notna(entry_atr) or entry_atr <= 0:
            continue
        side = str(row["side"]).lower()
        if idx + 1 >= len(candles):
            continue
        entry = float(candles.iloc[idx + 1]["open"])
        signal = 1 if side == "long" else -1 if side == "short" else 0
        resolved = resolve_exit_levels(
            signal=signal,
            entry_price=entry,
            structural_sl_price=_signal_stop_price(row),
            rrr=rrr,
            config=ExitGeometryConfig(mode="sl_rrr"),
        )
        if resolved is None:
            continue
        outcome, mae_atr, mfe_atr, tp_bars = _first_barrier_outcome(
            candles=candles,
            start_idx=idx,
            side=side,
            entry_atr=entry_atr,
            tp_price=resolved.tp_price,
            sl_price=resolved.sl_price,
            ttl_bars=ttl_bars,
        )
        outcomes[outcome] += 1
        mae_values.append(mae_atr)
        mfe_values.append(mfe_atr)
        if tp_bars is not None:
            bars_to_tp.append(tp_bars)

    total = sum(outcomes.values())
    if total == 0:
        return _empty_barrier_metrics()
    return BarrierMetrics(
        total=total,
        tp_first=outcomes["tp_first"],
        sl_first=outcomes["sl_first"],
        timeout=outcomes["timeout"],
        tp_first_rate=outcomes["tp_first"] / total,
        sl_first_rate=outcomes["sl_first"] / total,
        timeout_rate=outcomes["timeout"] / total,
        win_rate=_barrier_win_rate(outcomes["tp_first"], outcomes["sl_first"]),
        median_mae_atr=float(pd.Series(mae_values).median()) if mae_values else 0.0,
        median_mfe_atr=float(pd.Series(mfe_values).median()) if mfe_values else 0.0,
        median_bars_to_tp=float(pd.Series(bars_to_tp).median()) if bars_to_tp else 0.0,
    )


def _empty_barrier_metrics() -> BarrierMetrics:
    return BarrierMetrics(
        total=0,
        tp_first=0,
        sl_first=0,
        timeout=0,
        tp_first_rate=0.0,
        sl_first_rate=0.0,
        timeout_rate=0.0,
        win_rate=0.0,
        median_mae_atr=0.0,
        median_mfe_atr=0.0,
        median_bars_to_tp=0.0,
    )


def _barrier_win_rate(tp_first: int, sl_first: int) -> float:
    resolved = tp_first + sl_first
    if resolved <= 0:
        return 0.0
    return tp_first / resolved


def _entry_atr(primary: pd.DataFrame, window: int = 14) -> pd.Series:
    previous_close = primary["close"].shift(1)
    true_range = pd.concat(
        [
            primary["high"] - primary["low"],
            (primary["high"] - previous_close).abs(),
            (primary["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=window, min_periods=1).mean()


def _signal_stop_price(row: pd.Series) -> float:
    value = row.get("stop_price")
    if pd.notna(value):
        return float(value)
    return float("nan")


def _first_barrier_outcome(
    *,
    candles: pd.DataFrame,
    start_idx: int,
    side: str,
    entry_atr: float,
    tp_price: float,
    sl_price: float,
    ttl_bars: int,
) -> tuple[str, float, float, int | None]:
    if side not in {"long", "short"}:
        return ("timeout", 0.0, 0.0, None)

    entry = (
        float(candles.iloc[start_idx + 1]["open"]) if start_idx + 1 < len(candles) else float("nan")
    )
    if not pd.notna(entry):
        return ("timeout", 0.0, 0.0, None)

    max_adverse = 0.0
    max_favorable = 0.0
    end_idx = min(len(candles) - 1, start_idx + max(ttl_bars, 1))
    for offset, idx in enumerate(range(start_idx + 1, end_idx + 1), 1):
        high = float(candles.iloc[idx]["high"])
        low = float(candles.iloc[idx]["low"])
        if side == "long":
            favorable = max(0.0, high - entry)
            adverse = max(0.0, entry - low)
            hit_tp = high >= tp_price
            hit_sl = low <= sl_price
        else:
            favorable = max(0.0, entry - low)
            adverse = max(0.0, high - entry)
            hit_tp = low <= tp_price
            hit_sl = high >= sl_price
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)
        if hit_sl:
            return ("sl_first", max_adverse / entry_atr, max_favorable / entry_atr, None)
        if hit_tp:
            return ("tp_first", max_adverse / entry_atr, max_favorable / entry_atr, offset)
    return ("timeout", max_adverse / entry_atr, max_favorable / entry_atr, None)


def _max_signals_for_window(window: DSSWindowSpec, data: StrategyData) -> int:
    del window
    primary = data.primary
    if primary.empty:
        return _MAX_SIGNALS_PER_DAY
    index = pd.DatetimeIndex(primary.index)
    if len(index) <= 1:
        return _MAX_SIGNALS_PER_DAY
    elapsed_days = max((index.max() - index.min()).total_seconds() / 86_400, 0.0)
    covered_days = max(1.0, elapsed_days + 1.0 / 24.0)
    return max(_MAX_SIGNALS_PER_DAY, int(covered_days * _MAX_SIGNALS_PER_DAY))


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
        row[f"barrier_win_rate_{label}"] = metrics.win_rate if metrics else ""
        row[f"barrier_median_mae_atr_{label}"] = metrics.median_mae_atr if metrics else ""
        row[f"barrier_median_mfe_atr_{label}"] = metrics.median_mfe_atr if metrics else ""
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
) -> None:
    if stage1_specialists is None:
        stage1_specialists = _count_csv_rows(output / "stage1_specialists.csv")
    best = archive.elites()[0] if archive.elites() else None
    verdict = "candidates exported" if exported else "no candidate"
    reason = "archive has replay JSONs" if exported else "no archive elite reached export"
    lines = [
        "# DSS v2 run summary",
        "",
        f"Verdict: **{verdict}**",
        f"Reason: {reason}",
        f"Generated candidates: **{generated}**",
        f"Stage 1 survivors: **{stage1_survivors}**",
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
