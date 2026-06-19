"""Shared DSS Stage 1 signal-viability evaluator."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

import pandas as pd

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.dss_config import (
    DSSBehavior,
    DSSCandidate,
    DSSConfig,
    DSSWindowSpec,
)
from backtester.strategy_discovery.signal_composer import SignalComposer

_MAX_SIGNALS_PER_DAY = 10


class ComposerProtocol(Protocol):
    def build(self, config: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class BarrierMetrics:
    total: int
    tp_first: int
    sl_first: int
    unresolved_tail: int
    tp_first_rate: float
    sl_first_rate: float
    unresolved_tail_rate: float
    win_rate: float
    median_mae_pct: float
    median_mfe_pct: float
    median_bars_to_tp: float

    @property
    def timeout(self) -> int:
        return self.unresolved_tail

    @property
    def timeout_rate(self) -> float:
        return self.unresolved_tail_rate

    @property
    def median_mae_atr(self) -> float:
        return self.median_mae_pct

    @property
    def median_mfe_atr(self) -> float:
        return self.median_mfe_pct


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
    advisory_score: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def should_promote(self) -> bool:
        """Whether this candidate should be passed to the next stage."""
        return self.passed and self.behavior is not None


def evaluate_stage1(
    candidate: DSSCandidate,
    window_data: dict[str, StrategyData],
    config: DSSConfig,
    composer: ComposerProtocol | None = None,
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
        if count > _max_signals_for_window(window, data):
            first_rejection_reason = first_rejection_reason or f"overtrading:{window.label}"
            if not config.specialist_windows:
                return _stage1_result(
                    candidate=candidate,
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
        median_stop_atr[window.label] = 0.0
        metrics = _barrier_metrics(
            signals=signals,
            primary=data.primary,
            tp_move_pct=config.stage1_tp_move_pct,
            sl_move_pct=config.stage1_sl_move_pct,
            reference_atr_pct=config.stage1_reference_atr_pct,
        )
        barrier_metrics[window.label] = metrics
        min_signals = _min_signals_for_window(window, data, config)
        resolved_signals = metrics.tp_first + metrics.sl_first
        if resolved_signals < min_signals:
            first_rejection_reason = first_rejection_reason or f"too_few_signals:{window.label}"
            if not config.specialist_windows:
                return _stage1_result(
                    candidate=candidate,
                    passed=False,
                    rejection_reason=f"too_few_signals:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        if metrics.tp_first_rate < config.min_barrier_tp_first_rate:
            first_rejection_reason = first_rejection_reason or f"weak_barrier_edge:{window.label}"
            if not config.specialist_windows:
                return _stage1_result(
                    candidate=candidate,
                    passed=False,
                    rejection_reason=f"weak_barrier_edge:{window.label}",
                    signal_counts=signal_counts,
                    long_ratios=long_ratios,
                    median_stop_atr=median_stop_atr,
                    barrier_metrics=barrier_metrics,
                    behavior=None,
                )
            continue
        if metrics.win_rate < config.min_barrier_win_rate:
            first_rejection_reason = (
                first_rejection_reason or f"weak_barrier_win_rate:{window.label}"
            )
            if not config.specialist_windows:
                return _stage1_result(
                    candidate=candidate,
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
        return _stage1_result(
            candidate=candidate,
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
        return _stage1_result(
            candidate=candidate,
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

    return _stage1_result(
        candidate=candidate,
        passed=False,
        rejection_reason=first_rejection_reason or "no_viable_window",
        signal_counts=signal_counts,
        long_ratios=long_ratios,
        median_stop_atr=median_stop_atr,
        barrier_metrics=barrier_metrics,
        behavior=None,
    )


def stage1_advisory_score(result: Stage1Result) -> float:
    if result.behavior is None:
        return -10_000.0
    total_signals = sum(result.signal_counts.values())
    windows = max(len(result.signal_counts), 1)
    avg_signals = total_signals / windows
    count_score = 100.0 - abs(avg_signals - 180.0) * 0.25
    bucket_bonus = {
        "low": 25.0,
        "medium": 35.0,
        "high": 5.0,
        "too_high": -80.0,
    }.get(result.behavior.trade_count_bucket, 0.0)
    long_ratio_values = list(result.long_ratios.values())
    if long_ratio_values:
        side_dispersion = max(long_ratio_values) - min(long_ratio_values)
        stability_score = max(0.0, 20.0 - side_dispersion * 20.0)
    else:
        stability_score = 0.0
    barrier_values = list(result.barrier_metrics.values())
    if barrier_values:
        avg_tp_first = sum(item.tp_first_rate for item in barrier_values) / len(barrier_values)
        avg_sl_first = sum(item.sl_first_rate for item in barrier_values) / len(barrier_values)
        avg_unresolved = (
            sum(item.unresolved_tail_rate for item in barrier_values) / len(barrier_values)
        )
        avg_win_rate = sum(item.win_rate for item in barrier_values) / len(barrier_values)
        avg_mae = sum(item.median_mae_pct for item in barrier_values) / len(barrier_values)
        barrier_score = (
            avg_tp_first * 120.0
            + avg_win_rate * 80.0
            - avg_sl_first * 80.0
            - avg_unresolved * 20.0
            - avg_mae * 10.0
        )
    else:
        barrier_score = -50.0
    return count_score + bucket_bonus + stability_score + barrier_score


def stage1_rank_score(row: dict[str, object], windows: list[DSSWindowSpec]) -> float:
    parts: list[float] = []
    for window in windows:
        label = window.label
        win_rate = _row_float(row, f"barrier_win_rate_{label}")
        tp_rate = _row_float(row, f"barrier_tp_first_rate_{label}")
        sl_rate = _row_float(row, f"barrier_sl_first_rate_{label}")
        unresolved_rate = _row_float(row, f"barrier_unresolved_tail_rate_{label}")
        if unresolved_rate == 0.0:
            unresolved_rate = _row_float(row, f"barrier_timeout_rate_{label}")
        signals = max(0.0, _row_float(row, f"signals_{label}"))
        parts.append(
            win_rate * 100.0
            + tp_rate * 50.0
            + math.log1p(signals) * 5.0
            - sl_rate * 25.0
            - unresolved_rate * 10.0
        )
    return float(sum(parts) / max(len(parts), 1))


def _stage1_result(
    *,
    candidate: DSSCandidate,
    passed: bool,
    rejection_reason: str,
    signal_counts: dict[str, int],
    long_ratios: dict[str, float],
    median_stop_atr: dict[str, float],
    barrier_metrics: dict[str, BarrierMetrics],
    behavior: DSSBehavior | None,
    candidate_class: str = "rejected",
    target_window: str = "",
) -> Stage1Result:
    base = Stage1Result(
        candidate_id=candidate.candidate_id,
        passed=passed,
        rejection_reason=rejection_reason,
        signal_counts=signal_counts,
        long_ratios=long_ratios,
        median_stop_atr=median_stop_atr,
        barrier_metrics=barrier_metrics,
        behavior=behavior,
        candidate_class=candidate_class,
        target_window=target_window,
    )
    return Stage1Result(
        candidate_id=base.candidate_id,
        passed=base.passed,
        rejection_reason=base.rejection_reason,
        signal_counts=base.signal_counts,
        long_ratios=base.long_ratios,
        median_stop_atr=base.median_stop_atr,
        barrier_metrics=base.barrier_metrics,
        behavior=base.behavior,
        candidate_class=base.candidate_class,
        target_window=base.target_window,
        advisory_score=stage1_advisory_score(base),
    )


def _stage1_reject(candidate: DSSCandidate, reason: str) -> Stage1Result:
    return _stage1_result(
        candidate=candidate,
        passed=False,
        rejection_reason=reason,
        signal_counts={},
        long_ratios={},
        median_stop_atr={},
        barrier_metrics={},
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
        regime_strength="balanced",
    )


def _behavior_from_metrics(
    candidate: DSSCandidate,
    *,
    total_signals: int,
    long_ratio: float,
    regime_strength: str,
) -> DSSBehavior:
    if long_ratio >= 0.95:
        side_profile = "long_only"
    elif long_ratio <= 0.05:
        side_profile = "short_only"
    elif long_ratio >= 0.65:
        side_profile = "mixed_long_bias"
    elif long_ratio <= 0.35:
        side_profile = "mixed_short_bias"
    else:
        side_profile = "balanced"

    if total_signals < 100:
        trade_bucket = "low"
    elif total_signals < 400:
        trade_bucket = "medium"
    elif total_signals < 900:
        trade_bucket = "high"
    else:
        trade_bucket = "too_high"

    if candidate.position_ttl_bars <= 30:
        hold_bucket = "short"
    elif candidate.position_ttl_bars <= 54:
        hold_bucket = "medium"
    else:
        hold_bucket = "long"

    if candidate.atr_sl_mult < 1.0:
        risk_geometry = "tight_sl"
    elif candidate.atr_sl_mult <= 1.75:
        risk_geometry = "medium_sl"
    else:
        risk_geometry = "wide_sl"
    depth = len(candidate.filter_names)
    filter_depth = "3plus" if depth >= 3 else str(depth)

    return DSSBehavior(
        trigger_family=candidate.trigger_name,
        side_profile=side_profile,
        trade_count_bucket=trade_bucket,
        hold_time_bucket=hold_bucket,
        risk_geometry=risk_geometry,
        regime_strength=regime_strength,
        filter_depth=filter_depth,
    )


def _barrier_metrics(
    *,
    signals: pd.DataFrame,
    primary: pd.DataFrame,
    tp_move_pct: float,
    sl_move_pct: float,
    reference_atr_pct: float,
) -> BarrierMetrics:
    if signals.empty or primary.empty:
        return _empty_barrier_metrics()
    required = {"bar_time", "side"}
    if not required.issubset(signals.columns):
        return _empty_barrier_metrics()
    if reference_atr_pct <= 0:
        return _empty_barrier_metrics()

    candles = primary.sort_index()
    atr = _closed_candle_atr(candles)
    positions = {timestamp: idx for idx, timestamp in enumerate(candles.index)}
    outcomes = {"tp_first": 0, "sl_first": 0, "unresolved_tail": 0}
    mae_values: list[float] = []
    mfe_values: list[float] = []
    bars_to_tp: list[int] = []
    tp_atr_mult = tp_move_pct / reference_atr_pct
    sl_atr_mult = sl_move_pct / reference_atr_pct

    for _, row in signals.iterrows():
        bar_time = pd.Timestamp(row["bar_time"])
        if bar_time.tzinfo is None:
            bar_time = bar_time.tz_localize("UTC")
        else:
            bar_time = bar_time.tz_convert("UTC")
        idx = positions.get(bar_time)
        if idx is None:
            continue
        side = str(row["side"]).lower()
        if idx + 1 >= len(candles):
            continue
        entry = float(candles.iloc[idx + 1]["open"])
        if not pd.notna(entry) or entry <= 0:
            continue
        atr_value = float(atr.iloc[idx])
        if not pd.notna(atr_value) or atr_value <= 0:
            continue
        tp_distance_pct = (atr_value / entry) * tp_atr_mult
        sl_distance_pct = (atr_value / entry) * sl_atr_mult
        if tp_distance_pct <= 0 or sl_distance_pct <= 0:
            continue
        if side == "long":
            tp_price = entry * (1.0 + tp_distance_pct)
            sl_price = entry * (1.0 - sl_distance_pct)
        elif side == "short":
            tp_price = entry * (1.0 - tp_distance_pct)
            sl_price = entry * (1.0 + sl_distance_pct)
        else:
            continue
        outcome, mae_pct, mfe_pct, tp_bars = _first_barrier_outcome(
            candles=candles,
            start_idx=idx,
            side=side,
            entry_price=entry,
            tp_price=tp_price,
            sl_price=sl_price,
        )
        outcomes[outcome] += 1
        mae_values.append(mae_pct)
        mfe_values.append(mfe_pct)
        if tp_bars is not None:
            bars_to_tp.append(tp_bars)

    total = sum(outcomes.values())
    if total == 0:
        return _empty_barrier_metrics()
    return BarrierMetrics(
        total=total,
        tp_first=outcomes["tp_first"],
        sl_first=outcomes["sl_first"],
        unresolved_tail=outcomes["unresolved_tail"],
        tp_first_rate=outcomes["tp_first"] / total,
        sl_first_rate=outcomes["sl_first"] / total,
        unresolved_tail_rate=outcomes["unresolved_tail"] / total,
        win_rate=_barrier_win_rate(outcomes["tp_first"], outcomes["sl_first"]),
        median_mae_pct=float(pd.Series(mae_values).median()) if mae_values else 0.0,
        median_mfe_pct=float(pd.Series(mfe_values).median()) if mfe_values else 0.0,
        median_bars_to_tp=float(pd.Series(bars_to_tp).median()) if bars_to_tp else 0.0,
    )


def _empty_barrier_metrics() -> BarrierMetrics:
    return BarrierMetrics(
        total=0,
        tp_first=0,
        sl_first=0,
        unresolved_tail=0,
        tp_first_rate=0.0,
        sl_first_rate=0.0,
        unresolved_tail_rate=0.0,
        win_rate=0.0,
        median_mae_pct=0.0,
        median_mfe_pct=0.0,
        median_bars_to_tp=0.0,
    )


def _barrier_win_rate(tp_first: int, sl_first: int) -> float:
    resolved = tp_first + sl_first
    if resolved <= 0:
        return 0.0
    return tp_first / resolved


def _closed_candle_atr(primary: pd.DataFrame, window: int = 14) -> pd.Series:
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


def _first_barrier_outcome(
    *,
    candles: pd.DataFrame,
    start_idx: int,
    side: str,
    entry_price: float,
    tp_price: float,
    sl_price: float,
) -> tuple[str, float, float, int | None]:
    if side not in {"long", "short"}:
        return ("unresolved_tail", 0.0, 0.0, None)
    if not pd.notna(entry_price) or entry_price <= 0:
        return ("unresolved_tail", 0.0, 0.0, None)

    max_adverse = 0.0
    max_favorable = 0.0
    for offset, idx in enumerate(range(start_idx + 1, len(candles)), 1):
        high = float(candles.iloc[idx]["high"])
        low = float(candles.iloc[idx]["low"])
        if side == "long":
            favorable = max(0.0, (high - entry_price) / entry_price)
            adverse = max(0.0, (entry_price - low) / entry_price)
            hit_tp = high >= tp_price
            hit_sl = low <= sl_price
        else:
            favorable = max(0.0, (entry_price - low) / entry_price)
            adverse = max(0.0, (high - entry_price) / entry_price)
            hit_tp = low <= tp_price
            hit_sl = high >= sl_price
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)
        if hit_sl:
            return ("sl_first", max_adverse, max_favorable, None)
        if hit_tp:
            return ("tp_first", max_adverse, max_favorable, offset)
    return ("unresolved_tail", max_adverse, max_favorable, None)


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


def _min_signals_for_window(window: DSSWindowSpec, data: StrategyData, config: DSSConfig) -> int:
    del window
    base = max(config.min_trades_per_window, 0)
    if config.min_signals_per_week <= 0:
        return base
    primary = data.primary
    if primary.empty:
        return base
    index = pd.DatetimeIndex(primary.index)
    if len(index) <= 1:
        weeks = 1.0 / 7.0
    else:
        elapsed_days = max((index.max() - index.min()).total_seconds() / 86_400, 0.0)
        weeks = max(1.0 / 7.0, elapsed_days / 7.0)
    return max(base, math.ceil(config.min_signals_per_week * weeks))


def _long_ratio(signals: pd.DataFrame) -> float:
    if signals.empty or "side" not in signals.columns:
        return 0.0
    sides = signals["side"].astype(str).str.lower()
    directional = sides.isin(["long", "short"])
    if not bool(directional.any()):
        return 0.0
    return float((sides[directional] == "long").mean())


def _row_float(row: dict[str, object], key: str) -> float:
    try:
        return float(cast(Any, row.get(key, 0.0) or 0.0))
    except (TypeError, ValueError):
        return 0.0
