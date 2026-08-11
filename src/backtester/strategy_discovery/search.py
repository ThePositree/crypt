from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.data_contracts import StrategyInput, select_candle_frame
from backtester.strategy_discovery.events import CandidateKey, DiscoveryEvent, LabeledEvent
from backtester.strategy_discovery.features import DiscoveryDataset, build_discovery_dataset
from backtester.strategy_discovery.filters import filter_catalog
from backtester.strategy_discovery.labeler import LabelConfig, label_events
from backtester.strategy_discovery.report import (
    write_dataframe,
    write_json,
    write_markdown_table,
)
from backtester.strategy_discovery.scoring import discovery_score
from backtester.strategy_discovery.triggers import trigger_catalog


@dataclass(frozen=True, slots=True)
class DiscoveryConfig:
    output: Path
    candle_timeframe: str
    label_horizon_bars: int = 24
    label_atr_mult: float = 1.0
    beam_width: int = 20
    max_filter_depth: int = 4
    min_trades_total: int = 50
    min_trades_per_window: int = 10
    keep_sparse_triggers: bool = False
    best_candidate_count: int = 10


@dataclass(frozen=True, slots=True)
class DiscoveryWindow:
    label: str
    symbol: str
    start: str
    end: str
    data: StrategyInput


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    key: CandidateKey
    depth: int
    raw_events: int
    passed_events: int
    wins: int
    losses: int
    neutral: int
    win_rate: float
    loss_rate: float
    neutral_rate: float
    trades_per_window: dict[str, int]
    windows_passing_min_trades: int
    score: float
    status: str
    reject_counts: dict[str, int]
    events: list[LabeledEvent]

    @property
    def candidate_id(self) -> str:
        return self.key.candidate_id


def run_strategy_discovery(
    *,
    windows: list[DiscoveryWindow],
    config: DiscoveryConfig,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    if not windows:
        raise ValueError("At least one discovery window is required")
    if config.beam_width < 1:
        raise ValueError("beam_width must be >= 1")
    if config.max_filter_depth < 0:
        raise ValueError("max_filter_depth must be >= 0")

    output_path = _timestamped_output(config.output)
    output_path.mkdir(parents=True, exist_ok=False)
    datasets = []
    for window in windows:
        datasets.append(
            build_discovery_dataset(
                data=select_candle_frame(window.data, config.candle_timeframe),
                window_label=window.label,
                symbol=window.symbol,
            )
        )
        _tick(progress_callback)
    labels = LabelConfig(
        horizon_bars=config.label_horizon_bars,
        atr_mult=config.label_atr_mult,
    )
    triggers = trigger_catalog()
    filters = filter_catalog()
    trigger_events: dict[str, dict[str, list[DiscoveryEvent]]] = {}
    for name, trigger in triggers.items():
        event_lists = []
        for dataset in datasets:
            event_lists.append(trigger(dataset))
            _tick(progress_callback)
        trigger_events[name] = _events_by_window(event_lists)
    trigger_labels: dict[str, dict[str, list[LabeledEvent]]] = {}
    for name, events_by_window in trigger_events.items():
        trigger_labels[name] = _label_trigger_events(events_by_window, datasets, labels)
        _tick(progress_callback, len(datasets))

    evaluated: dict[CandidateKey, CandidateEvaluation] = {}
    trace_rows: list[dict[str, Any]] = []
    beam_by_trigger: dict[str, list[CandidateEvaluation]] = {}

    for trigger_name in triggers:
        key = CandidateKey.from_parts(trigger_name, ())
        evaluation = _evaluate_candidate(
            key=key,
            depth=0,
            trigger_events=trigger_events[trigger_name],
            trigger_labels=trigger_labels[trigger_name],
            datasets=datasets,
            filter_names=(),
            config=config,
        )
        _tick(progress_callback)
        evaluated[key] = evaluation
        status = evaluation.status
        if evaluation.passed_events < config.min_trades_total and not config.keep_sparse_triggers:
            status = "dropped_sparse_trigger"
        else:
            beam_by_trigger[trigger_name] = [evaluation]
        trace_rows.append(_trace_row(evaluation, parent_id="", added_filter="", status=status))

    for depth in range(1, config.max_filter_depth + 1):
        next_beam_by_trigger: dict[str, list[CandidateEvaluation]] = {}
        any_extension = False
        for trigger_name, beam in beam_by_trigger.items():
            extensions: list[CandidateEvaluation] = []
            for parent in beam:
                unused_filters = [name for name in filters if name not in parent.key.filter_names]
                for filter_name in unused_filters:
                    filter_names = (*parent.key.filter_names, filter_name)
                    key = CandidateKey.from_parts(trigger_name, filter_names)
                    if key in evaluated:
                        continue
                    evaluation = _evaluate_candidate(
                        key=key,
                        depth=depth,
                        trigger_events=trigger_events[trigger_name],
                        trigger_labels=trigger_labels[trigger_name],
                        datasets=datasets,
                        filter_names=key.filter_names,
                        config=config,
                    )
                    _tick(progress_callback)
                    evaluated[key] = evaluation
                    extensions.append(evaluation)
                    any_extension = True
                    trace_rows.append(
                        _trace_row(
                            evaluation,
                            parent_id=parent.candidate_id,
                            added_filter=filter_name,
                            status=evaluation.status,
                            parent_score=parent.score,
                        )
                    )
            kept = _top_candidates(extensions, config.beam_width)
            if kept:
                next_beam_by_trigger[trigger_name] = kept
        if not any_extension:
            break
        beam_by_trigger = next_beam_by_trigger
        if not beam_by_trigger:
            break

    candidates = _top_candidates(list(evaluated.values()), len(evaluated))
    _export_results(
        output_path=output_path,
        config=config,
        windows=windows,
        candidates=candidates,
        trace_rows=trace_rows,
    )
    _tick(progress_callback)
    return output_path


def _evaluate_candidate(
    *,
    key: CandidateKey,
    depth: int,
    trigger_events: dict[str, list[DiscoveryEvent]],
    trigger_labels: dict[str, list[LabeledEvent]],
    datasets: list[DiscoveryDataset],
    filter_names: tuple[str, ...],
    config: DiscoveryConfig,
) -> CandidateEvaluation:
    filters = filter_catalog()
    dataset_by_window = {dataset.window_label: dataset for dataset in datasets}
    labeled_by_event_id = {labeled.event.event_id: labeled for labeled in _flatten(trigger_labels)}
    passed: list[LabeledEvent] = []
    reject_counts: Counter[str] = Counter()
    for event in _flatten_events(trigger_events):
        keep = True
        dataset = dataset_by_window[event.window_label]
        for filter_name in filter_names:
            result = filters[filter_name](event, dataset)
            if not result.passed:
                reject_counts[f"{filter_name}:{result.reason}"] += 1
                keep = False
                break
        if keep:
            labeled = labeled_by_event_id.get(event.event_id)
            if labeled is not None:
                passed.append(labeled)

    label_counts = Counter(labeled.label for labeled in passed)
    wins = label_counts["win"]
    losses = label_counts["loss"]
    neutral = label_counts["neutral"]
    decisive = wins + losses
    passed_events = len(passed)
    win_rate = wins / decisive if decisive > 0 else 0.0
    loss_rate = losses / decisive if decisive > 0 else 0.0
    neutral_rate = neutral / passed_events if passed_events > 0 else 0.0
    trades_per_window = Counter(labeled.event.window_label for labeled in passed)
    windows_passing = sum(
        1 for count in trades_per_window.values() if count >= config.min_trades_per_window
    )
    score = discovery_score(
        wins=wins,
        losses=losses,
        neutral=neutral,
        passed_events=passed_events,
        windows_passing_min_trades=windows_passing,
        window_count=len(datasets),
    )
    status = "accepted" if passed_events >= config.min_trades_total else "rejected_sparse"
    return CandidateEvaluation(
        key=key,
        depth=depth,
        raw_events=sum(len(events) for events in trigger_events.values()),
        passed_events=passed_events,
        wins=wins,
        losses=losses,
        neutral=neutral,
        win_rate=win_rate,
        loss_rate=loss_rate,
        neutral_rate=neutral_rate,
        trades_per_window=dict(trades_per_window),
        windows_passing_min_trades=windows_passing,
        score=score,
        status=status,
        reject_counts=dict(sorted(reject_counts.items())),
        events=passed,
    )


def _export_results(
    *,
    output_path: Path,
    config: DiscoveryConfig,
    windows: list[DiscoveryWindow],
    candidates: list[CandidateEvaluation],
    trace_rows: list[dict[str, Any]],
) -> None:
    candidate_rows = [_candidate_row(candidate, windows=windows) for candidate in candidates]
    candidates_df = pd.DataFrame(candidate_rows)
    candidate_windows_df = pd.DataFrame(
        [row for candidate in candidates for row in _candidate_window_rows(candidate, windows)]
    )
    trace_df = pd.DataFrame(trace_rows)
    rejected_df = _rejected_dataframe(candidates)

    write_json(
        output_path / "config.json",
        {
            "candle_timeframe": config.candle_timeframe,
            "label_horizon_bars": config.label_horizon_bars,
            "label_atr_mult": config.label_atr_mult,
            "beam_width": config.beam_width,
            "max_filter_depth": config.max_filter_depth,
            "min_trades_total": config.min_trades_total,
            "min_trades_per_window": config.min_trades_per_window,
            "keep_sparse_triggers": config.keep_sparse_triggers,
            "windows": [
                {
                    "label": window.label,
                    "symbol": window.symbol,
                    "from": window.start,
                    "to": window.end,
                }
                for window in windows
            ],
        },
    )
    write_dataframe(output_path / "candidates.csv", candidates_df)
    write_markdown_table(output_path / "candidates.md", candidates_df.head(50))
    write_dataframe(output_path / "candidate_windows.csv", candidate_windows_df)
    write_markdown_table(
        output_path / "candidate_windows.md",
        candidate_windows_df.head(100),
    )
    write_dataframe(output_path / "search_trace.csv", trace_df)
    write_dataframe(output_path / "rejected.csv", rejected_df)

    best_dir = output_path / "best_candidates"
    best_dir.mkdir(parents=True, exist_ok=True)
    accepted = [candidate for candidate in candidates if candidate.status == "accepted"]
    _write_shortlist(
        output_path=output_path,
        best_dir=best_dir,
        name="top_score",
        candidates=accepted[: config.best_candidate_count],
        windows=windows,
        legacy_rank_prefix=True,
    )
    for threshold in (50, 100, 200, 500):
        threshold_candidates = sorted(
            [candidate for candidate in accepted if candidate.passed_events >= threshold],
            key=lambda candidate: (
                candidate.win_rate,
                candidate.passed_events,
                candidate.score,
            ),
            reverse=True,
        )
        _write_shortlist(
            output_path=output_path,
            best_dir=best_dir,
            name=f"top_win_rate_min_{threshold}",
            candidates=threshold_candidates[: config.best_candidate_count],
            windows=windows,
        )
    robust_candidates = sorted(
        [
            candidate
            for candidate in accepted
            if _min_window_win_rate(candidate, windows) >= 0.5
            and candidate.windows_passing_min_trades == len(windows)
        ],
        key=lambda candidate: (
            _min_window_win_rate(candidate, windows),
            candidate.win_rate,
            candidate.passed_events,
        ),
        reverse=True,
    )
    _write_shortlist(
        output_path=output_path,
        best_dir=best_dir,
        name="robust_min_window_win_rate_50",
        candidates=robust_candidates[: config.best_candidate_count],
        windows=windows,
    )


def _write_shortlist(
    *,
    output_path: Path,
    best_dir: Path,
    name: str,
    candidates: list[CandidateEvaluation],
    windows: list[DiscoveryWindow],
    legacy_rank_prefix: bool = False,
) -> None:
    shortlist_df = pd.DataFrame(
        [_candidate_row(candidate, windows=windows) for candidate in candidates]
    )
    write_dataframe(output_path / f"{name}.csv", shortlist_df)
    write_markdown_table(output_path / f"{name}.md", shortlist_df)
    shortlist_dir = best_dir / name
    shortlist_dir.mkdir(parents=True, exist_ok=True)
    for rank, candidate in enumerate(candidates, start=1):
        prefix = shortlist_dir / f"rank_{rank:03d}"
        _write_candidate_artifacts(prefix=prefix, rank=rank, candidate=candidate)
        if legacy_rank_prefix:
            legacy_prefix = best_dir / f"rank_{rank:03d}"
            _write_candidate_artifacts(prefix=legacy_prefix, rank=rank, candidate=candidate)


def _write_candidate_artifacts(
    *,
    prefix: Path,
    rank: int,
    candidate: CandidateEvaluation,
) -> None:
    write_json(prefix.with_name(f"{prefix.name}_strategy.json"), _strategy_payload(candidate))
    events_df = pd.DataFrame([_event_row(labeled) for labeled in candidate.events])
    write_dataframe(prefix.with_name(f"{prefix.name}_events.csv"), events_df)
    report = _candidate_report(rank, candidate)
    prefix.with_name(f"{prefix.name}_report.md").write_text(report + "\n")


def _candidate_window_rows(
    candidate: CandidateEvaluation,
    windows: list[DiscoveryWindow],
) -> list[dict[str, Any]]:
    labels_by_window: dict[str, Counter[str]] = {window.label: Counter() for window in windows}
    for labeled in candidate.events:
        labels_by_window[labeled.event.window_label][labeled.label] += 1
    rows: list[dict[str, Any]] = []
    for window in windows:
        counts = labels_by_window[window.label]
        wins = int(counts["win"])
        losses = int(counts["loss"])
        neutral = int(counts["neutral"])
        decisive = wins + losses
        events = wins + losses + neutral
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "trigger_name": candidate.key.trigger_name,
                "filters": ",".join(candidate.key.filter_names),
                "window_label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "events": events,
                "wins": wins,
                "losses": losses,
                "neutral": neutral,
                "win_rate": wins / decisive if decisive > 0 else 0.0,
            }
        )
    return rows


def _min_window_win_rate(
    candidate: CandidateEvaluation,
    windows: list[DiscoveryWindow],
) -> float:
    rows = _candidate_window_rows(candidate, windows)
    if not rows:
        return 0.0
    return min(float(row["win_rate"]) for row in rows)


def _window_win_rate_summary(
    candidate: CandidateEvaluation,
    windows: list[DiscoveryWindow],
) -> dict[str, float | int]:
    rows = _candidate_window_rows(candidate, windows)
    rates = [float(row["win_rate"]) for row in rows]
    event_counts = [int(row["events"]) for row in rows]
    if not rows:
        return {
            "min_window_win_rate": 0.0,
            "max_window_win_rate": 0.0,
            "windows_win_rate_ge_50": 0,
            "windows_win_rate_ge_55": 0,
            "windows_win_rate_ge_60": 0,
            "min_window_events": 0,
        }
    return {
        "min_window_win_rate": min(rates),
        "max_window_win_rate": max(rates),
        "windows_win_rate_ge_50": sum(rate >= 0.5 for rate in rates),
        "windows_win_rate_ge_55": sum(rate >= 0.55 for rate in rates),
        "windows_win_rate_ge_60": sum(rate >= 0.6 for rate in rates),
        "min_window_events": min(event_counts),
    }


def _candidate_row(
    candidate: CandidateEvaluation,
    *,
    windows: list[DiscoveryWindow] | None = None,
) -> dict[str, Any]:
    row = {
        "candidate_id": candidate.candidate_id,
        "trigger_name": candidate.key.trigger_name,
        "filters": ",".join(candidate.key.filter_names),
        "depth": candidate.depth,
        "raw_events": candidate.raw_events,
        "passed_events": candidate.passed_events,
        "wins": candidate.wins,
        "losses": candidate.losses,
        "neutral": candidate.neutral,
        "win_rate": candidate.win_rate,
        "loss_rate": candidate.loss_rate,
        "neutral_rate": candidate.neutral_rate,
        "windows_passing_min_trades": candidate.windows_passing_min_trades,
        "trades_per_window": json.dumps(candidate.trades_per_window, sort_keys=True),
        "score": candidate.score,
        "status": candidate.status,
        "reject_counts": json.dumps(candidate.reject_counts, sort_keys=True),
    }
    if windows is not None:
        row.update(_window_win_rate_summary(candidate, windows))
    return row


def _event_row(labeled: LabeledEvent) -> dict[str, Any]:
    event = labeled.event
    return {
        "event_time": event.event_time.isoformat(),
        "window_label": event.window_label,
        "symbol": event.symbol,
        "side": event.side,
        "trigger_name": event.trigger_name,
        "entry_reference_price": event.entry_reference_price,
        "label": labeled.label,
        "label_reason": labeled.label_reason,
        "atr": labeled.atr,
        "metadata": json.dumps(event.metadata, sort_keys=True, default=str),
    }


def _strategy_payload(candidate: CandidateEvaluation) -> dict[str, Any]:
    return {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": candidate.key.trigger_name,
            "filters": list(candidate.key.filter_names),
            "note": "Discovery-native candidate; convert before donor execution backtests.",
        },
        "metrics": _candidate_row(candidate, windows=None),
    }


def _candidate_report(rank: int, candidate: CandidateEvaluation) -> str:
    lines = [
        f"# Discovery candidate rank {rank:03d}",
        "",
        f"- Candidate: `{candidate.candidate_id}`",
        f"- Trigger: `{candidate.key.trigger_name}`",
        f"- Filters: `{', '.join(candidate.key.filter_names) or 'none'}`",
        f"- Score: `{candidate.score:.6f}`",
        f"- Passed events: `{candidate.passed_events}`",
        f"- Win rate: `{candidate.win_rate:.2%}`",
        f"- Wins / losses / neutral: `{candidate.wins}` / `{candidate.losses}` / `{candidate.neutral}`",
        f"- Trades per window: `{json.dumps(candidate.trades_per_window, sort_keys=True)}`",
        "",
        "This is a discovery-native shortlist item, not a mandate candidate.",
    ]
    return "\n".join(lines)


def _rejected_dataframe(candidates: list[CandidateEvaluation]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        for reason, count in candidate.reject_counts.items():
            filter_name, reject_reason = reason.split(":", 1)
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "trigger_name": candidate.key.trigger_name,
                    "filters": ",".join(candidate.key.filter_names),
                    "filter_name": filter_name,
                    "reason": reject_reason,
                    "count": count,
                }
            )
    return pd.DataFrame(rows)


def _trace_row(
    evaluation: CandidateEvaluation,
    *,
    parent_id: str,
    added_filter: str,
    status: str,
    parent_score: float | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": evaluation.candidate_id,
        "depth": evaluation.depth,
        "parent_candidate_id": parent_id,
        "added_filter": added_filter,
        "parent_score": parent_score,
        "score": evaluation.score,
        "score_delta": None if parent_score is None else evaluation.score - parent_score,
        "passed_events": evaluation.passed_events,
        "win_rate": evaluation.win_rate,
        "status": status,
    }


def _top_candidates(
    candidates: list[CandidateEvaluation],
    limit: int,
) -> list[CandidateEvaluation]:
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.status == "accepted",
            candidate.score,
            candidate.passed_events,
            candidate.win_rate,
        ),
        reverse=True,
    )[:limit]


def _timestamped_output(base: Path) -> Path:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    return base / timestamp


def _events_by_window(event_lists: list[list[DiscoveryEvent]]) -> dict[str, list[DiscoveryEvent]]:
    result: dict[str, list[DiscoveryEvent]] = {}
    for events in event_lists:
        if events:
            result[events[0].window_label] = events
    return result


def _label_trigger_events(
    events_by_window: dict[str, list[DiscoveryEvent]],
    datasets: list[DiscoveryDataset],
    config: LabelConfig,
) -> dict[str, list[LabeledEvent]]:
    dataset_by_window = {dataset.window_label: dataset for dataset in datasets}
    return {
        window_label: label_events(
            events=events,
            dataset=dataset_by_window[window_label],
            config=config,
        )
        for window_label, events in events_by_window.items()
    }


def _flatten(labels_by_window: dict[str, list[LabeledEvent]]) -> list[LabeledEvent]:
    return [labeled for labels in labels_by_window.values() for labeled in labels]


def _flatten_events(events_by_window: dict[str, list[DiscoveryEvent]]) -> list[DiscoveryEvent]:
    return [event for events in events_by_window.values() for event in events]


def _tick(progress_callback: Callable[[int], None] | None, step: int = 1) -> None:
    if progress_callback is not None and step > 0:
        progress_callback(step)
