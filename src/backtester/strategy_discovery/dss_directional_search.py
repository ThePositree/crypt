"""DSS v3 directional search runner."""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.dss_archive import DSSArchive
from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    FloatParam,
    IntParam,
    ParamDef,
)
from backtester.strategy_discovery.dss_directional import (
    BarrierMetrics,
    DirectionalResult,
    directional_rank_score,
    evaluate_directional_viability,
)
from backtester.strategy_discovery.dss_runtime import DSSSearchRuntime
from backtester.strategy_discovery.signal_composer import SignalComposer

_STATE_VERSION = 3

__all__ = [
    "BarrierMetrics",
    "DSSDirectionalResult",
    "DirectionalResult",
    "evaluate_directional_viability",
    "export_directional_candidates",
    "run_dss_directional_search",
    "write_directional_ranked",
]


@dataclass(frozen=True, slots=True)
class DSSDirectionalResult:
    output: Path
    generated: int
    directional_survivors: int
    exported_candidates: list[Path]
    archive: DSSArchive


def run_dss_directional_search(
    *,
    config: DSSConfig,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    progress_callback: Callable[[int], None] | None = None,
) -> DSSDirectionalResult:
    """Run DSS search and write directional labeling artifacts under config.output."""
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    _guard_output_dir(output)
    _write_state(output, config)

    completed_candidates = _read_candidate_rows(output / "candidates.jsonl")
    candidates_by_id = {candidate.candidate_id: candidate for candidate in completed_candidates}

    composer = SignalComposer()
    archive = DSSArchive()
    viability_path = output / "directional_viability.csv"
    evaluated_ids = _read_directional_candidate_ids(viability_path)
    directional_survivors = _count_directional_survivors(viability_path)
    generated = len(completed_candidates)
    attempted = len(completed_candidates)
    evaluated = _count_csv_rows(viability_path)
    if evaluated and progress_callback is not None:
        progress_callback(evaluated)

    with DSSSearchRuntime(config=config) as runtime:
        for candidate in completed_candidates:
            runtime.record_candidate(candidate, source="resume")

        pending_candidates = [
            candidate
            for candidate in completed_candidates
            if candidate.candidate_id not in evaluated_ids
        ]
        for candidate in pending_candidates:
            if not runtime.should_continue(evaluated):
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
            evaluated += 1
            if directional.should_promote:
                directional_survivors += 1
            runtime.write_progress(generated=generated, evaluated=evaluated)
            if progress_callback is not None:
                progress_callback(1)

        while runtime.should_continue(evaluated):
            batch_size = runtime.remaining_batch(evaluated, 64)
            evaluated_before_batch = evaluated
            candidates = _generate_directional_candidates(
                search_space=search_space,
                start=attempted,
                limit=attempted + batch_size,
                max_filters=config.max_filters,
            )
            for candidate in candidates:
                attempted += 1
                if not runtime.record_candidate(candidate, source="generated"):
                    runtime.write_progress(generated=generated, evaluated=evaluated)
                    continue
                generated += 1
                candidates_by_id[candidate.candidate_id] = candidate
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
                    evaluated += 1
                    if directional.should_promote:
                        directional_survivors += 1
                finally:
                    runtime.write_progress(generated=generated, evaluated=evaluated)
                    if progress_callback is not None:
                        progress_callback(1)

            if evaluated == evaluated_before_batch:
                runtime.write_progress(generated=generated, evaluated=evaluated)
                break
            if config.n_trials is None:
                _refresh_directional_reports(
                    output=output,
                    config=config,
                    runtime=runtime,
                    generated=generated,
                    evaluated=evaluated,
                )
                continue

        directional_ranked, exported = _refresh_directional_reports(
            output=output,
            config=config,
            runtime=runtime,
            generated=generated,
            evaluated=evaluated,
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


def _refresh_directional_reports(
    *,
    output: Path,
    config: DSSConfig,
    runtime: DSSSearchRuntime,
    generated: int,
    evaluated: int,
) -> tuple[list[dict[str, object]], list[Path]]:
    ranked = write_directional_ranked(output, config)
    exported = export_directional_candidates(ranked, output, config)
    runtime.write_progress(generated=generated, evaluated=evaluated, exported=len(exported))
    return ranked, exported


def _evaluate_directional_candidate(
    *,
    output: Path,
    candidate: DSSCandidate,
    window_data: dict[str, StrategyData],
    config: DSSConfig,
    composer: SignalComposer,
    runtime: DSSSearchRuntime,
    append_candidate: bool,
) -> DirectionalResult:
    if append_candidate:
        _append_jsonl(output / "candidates.jsonl", candidate.to_dict())
    result = evaluate_directional_viability(candidate, window_data, config, composer)
    _append_directional_result(output, candidate, result, config.windows)
    runtime.mark_evaluated(
        candidate,
        promoted=result.should_promote,
        score=result.advisory_score,
    )
    return result


def write_directional_ranked(output: Path, config: DSSConfig) -> list[dict[str, object]]:
    source = output / "directional_viability.csv"
    if not source.exists():
        return []
    rows: list[dict[str, object]] = []
    near_misses: list[dict[str, object]] = []
    with source.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            scored = dict(row)
            scored["directional_score"] = directional_rank_score(scored, config.windows)
            if str(row.get("should_promote", row.get("passed", ""))).lower() == "true":
                rows.append(scored)
            else:
                near_misses.append(scored)
    rows.sort(key=lambda row: cast(float, row["directional_score"]), reverse=True)
    near_misses.sort(key=lambda row: cast(float, row["directional_score"]), reverse=True)
    ranked_path = output / "directional_ranked.csv"
    if rows:
        fieldnames = ["rank", "directional_score", *[key for key in rows[0] if key != "directional_score"]]
        with ranked_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for idx, row in enumerate(rows, 1):
                writer.writerow({"rank": idx, **row})
    elif ranked_path.exists():
        ranked_path.unlink()
    near_miss_path = output / "directional_near_misses.csv"
    if near_misses:
        fieldnames = [
            "rank",
            "directional_score",
            *[key for key in near_misses[0] if key != "directional_score"],
        ]
        with near_miss_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for idx, row in enumerate(near_misses, 1):
                writer.writerow({"rank": idx, **row})
    elif near_miss_path.exists():
        near_miss_path.unlink()
    return rows


def export_directional_candidates(
    ranked_rows: list[dict[str, object]], output: Path, config: DSSConfig
) -> list[Path]:
    candidates_by_id = {
        candidate.candidate_id: candidate
        for candidate in _read_candidate_rows(output / "candidates.jsonl")
    }
    candidates_dir = output / "directional_candidates"
    candidates_dir.mkdir(exist_ok=True)
    exports: list[Path] = []
    manifest_rows: list[dict[str, object]] = []
    selected_rows = _select_directional_export_rows(ranked_rows, config.top_n_candidates)
    _write_frequency_archive(output, ranked_rows)
    for idx, row in enumerate(selected_rows, 1):
        candidate_id = str(row["candidate_id"])
        candidate = candidates_by_id.get(candidate_id)
        if candidate is None:
            continue
        path = candidates_dir / f"directional_{idx:03d}_{candidate_id}_{candidate.trigger_name}.json"
        payload = {
            "name": "dss_strategy",
            "version": "3.0-directional",
            "candidate_id": candidate.candidate_id,
            "directional_score": row["directional_score"],
            "directional_metrics": row,
            "params": candidate.trial_config.to_dict(),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        exports.append(path)
        manifest_rows.append(
            {
                "rank": idx,
                "candidate_id": candidate.candidate_id,
                "candidate_path": str(path),
                "trigger_name": candidate.trigger_name,
                "filter_names": "+".join(candidate.filter_names),
                "frequency_class": row.get("frequency_class", ""),
                "directional_score": row["directional_score"],
            }
        )
    if manifest_rows:
        _write_directional_manifest(output / "directional_candidate_manifest.md", manifest_rows)
    return exports


def _write_directional_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# DSS directional candidate manifest",
        "",
        "These candidates passed directional labeling only. They are signal-family research artifacts, not promotion-ready backtest results.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['rank']}. {row['candidate_id']}",
                "",
                f"- Path: `{row['candidate_path']}`",
                f"- Trigger: `{row['trigger_name']}`",
                f"- Filters: `{row['filter_names']}`",
                f"- Frequency class: `{row.get('frequency_class', '')}`",
                f"- Directional score: `{cast(float, row['directional_score']):.2f}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _select_directional_export_rows(
    ranked_rows: list[dict[str, object]], top_n: int
) -> list[dict[str, object]]:
    if top_n <= 0:
        return []
    buckets: dict[str, list[dict[str, object]]] = {}
    for row in ranked_rows:
        buckets.setdefault(str(row.get("frequency_class", "")), []).append(row)

    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    preferred_order = ["sparse", "medium", "frequent", "overactive", "too_sparse", "empty", ""]
    while len(selected) < top_n:
        before = len(selected)
        for frequency_class in preferred_order:
            bucket = buckets.get(frequency_class, [])
            while bucket:
                row = bucket.pop(0)
                candidate_id = str(row.get("candidate_id", ""))
                if candidate_id in seen:
                    continue
                selected.append(row)
                seen.add(candidate_id)
                break
            if len(selected) >= top_n:
                break
        if len(selected) == before:
            break
    return selected


def _write_frequency_archive(output: Path, ranked_rows: list[dict[str, object]]) -> None:
    summary: dict[str, dict[str, object]] = {}
    for row in ranked_rows:
        frequency_class = str(row.get("frequency_class", ""))
        bucket = summary.setdefault(
            frequency_class,
            {"frequency_class": frequency_class, "count": 0, "best_directional_score": ""},
        )
        bucket["count"] = int(cast(int, bucket["count"])) + 1
        score = float(cast(float, row.get("directional_score", 0.0) or 0.0))
        best = bucket["best_directional_score"]
        if best == "" or score > float(cast(float, best)):
            bucket["best_directional_score"] = score
    _write_csv(output / "archive" / "directional_frequency_archive.csv", list(summary.values()))


def _generate_directional_candidates(
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
    filter_depths = [0, 1, 2, min(3, max_filters)]
    for idx in range(start, limit):
        trigger = triggers[idx % len(triggers)]
        depth = filter_depths[(idx // max(len(triggers), 1)) % len(filter_depths)]
        depth = min(depth, max_filters, len(filters))
        chosen_filters = tuple(sorted(rng.sample(filters, depth))) if depth else ()
        out.append(
            DSSCandidate(
                candidate_id=f"dssv3_{idx + 1:06d}",
                trigger_name=_instance_base_name(trigger),
                trigger_params={
                    name: _sample_param(pdef, rng)
                    for name, pdef in search_space.trigger_param_bounds.get(
                        _instance_base_name(trigger), {}
                    ).items()
                },
                filter_names=chosen_filters,
                filter_params={
                    name: {
                        pname: _sample_param(pdef, rng)
                        for pname, pdef in search_space.filter_param_bounds.get(
                            _instance_base_name(name), {}
                        ).items()
                    }
                    for name in chosen_filters
                },
                generation=0,
                trigger_timeframe=_instance_timeframe(trigger),
                filter_timeframes={
                    name: _instance_timeframe(name)
                    for name in chosen_filters
                    if _instance_timeframe(name) != "H1"
                },
            )
        )
    return out


def _instance_base_name(raw_name: str) -> str:
    return raw_name.rsplit("@", 1)[0] if "@" in raw_name else raw_name


def _instance_timeframe(raw_name: str) -> str:
    return raw_name.rsplit("@", 1)[1] if "@" in raw_name else "H1"


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


def _guard_output_dir(output: Path) -> None:
    if (output / "study.journal").exists() and not (output / "state.json").exists():
        raise ValueError(
            "Output directory contains legacy DSS artifacts. DSS v3 cannot resume this run. "
            "Use a new output directory."
        )


def _write_state(output: Path, config: DSSConfig) -> None:
    payload = {
        "version": _STATE_VERSION,
        "n_trials": config.n_trials,
        "catalog": config.catalog,
        "evaluation_mode": "directional",
        "min_trades_per_window": config.min_trades_per_window,
        "min_signals_per_week": config.min_signals_per_week,
        "directional_tp_move_pct": config.directional_tp_move_pct,
        "directional_sl_move_pct": config.directional_sl_move_pct,
        "directional_reference_atr_pct": config.directional_reference_atr_pct,
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


def _read_candidate_rows(path: Path) -> list[DSSCandidate]:
    if not path.exists():
        return []
    candidates: list[DSSCandidate] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            candidates.append(DSSCandidate.from_dict(json.loads(line)))
    return candidates


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _append_directional_result(
    output: Path,
    candidate: DSSCandidate,
    result: DirectionalResult,
    windows: list[DSSWindowSpec],
) -> None:
    row: dict[str, object] = {
        "candidate_id": candidate.candidate_id,
        "trigger_name": candidate.trigger_name,
        "filter_names": "+".join(candidate.filter_names),
        "frequency_class": result.behavior.frequency_class if result.behavior else "",
        "passed": result.passed,
        "should_promote": result.should_promote,
        "directional_score": result.advisory_score if result.advisory_score is not None else "",
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
        row[f"barrier_unresolved_tail_rate_{label}"] = (
            metrics.unresolved_tail_rate if metrics else ""
        )
        row[f"barrier_win_rate_{label}"] = metrics.win_rate if metrics else ""
        row[f"barrier_median_mae_atr_{label}"] = metrics.median_mae_atr if metrics else ""
        row[f"barrier_median_mfe_atr_{label}"] = metrics.median_mfe_atr if metrics else ""
        row[f"barrier_median_mae_pct_{label}"] = metrics.median_mae_pct if metrics else ""
        row[f"barrier_median_mfe_pct_{label}"] = metrics.median_mfe_pct if metrics else ""
        row[f"barrier_median_bars_to_tp_{label}"] = metrics.median_bars_to_tp if metrics else ""
    _append_csv_row(output / "directional_viability.csv", row)
    if result.passed:
        _append_jsonl(output / "directional_survivors.jsonl", candidate.to_dict())
    elif result.candidate_class.startswith("specialist:"):
        payload = candidate.to_dict()
        payload["candidate_class"] = result.candidate_class
        payload["target_window"] = result.target_window
        _append_jsonl(output / "directional_specialists.jsonl", payload)
        _append_csv_row(output / "directional_specialists.csv", row)
    else:
        _append_csv_row(output / "directional_rejections.csv", row)


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


def _write_summary(
    *,
    output: Path,
    config: DSSConfig,
    generated: int,
    directional_survivors: int,
    exported: list[Path],
    archive: DSSArchive,
    directional_specialists: int | None = None,
    directional_ranked: int | None = None,
) -> None:
    _ = archive
    if directional_specialists is None:
        directional_specialists = _count_csv_rows(output / "directional_specialists.csv")
    if directional_ranked is None:
        directional_ranked = _count_csv_rows(output / "directional_ranked.csv")
    directional_near_misses = _count_csv_rows(output / "directional_near_misses.csv")
    verdict = "directional shortlist exported" if exported else "no directional candidate"
    reason = (
        "DSS v3 stops after directional labeling"
        if exported
        else "no candidate passed directional labeling"
    )
    lines = [
        "# DSS v3 run summary",
        "",
        f"Verdict: **{verdict}**",
        f"Reason: {reason}",
        "Evaluator: **directional_labeling_only**",
        f"Min signals per week: **{config.min_signals_per_week:g}**",
        f"Generated candidates: **{generated}**",
        f"Directional survivors: **{directional_survivors}**",
        f"Directional ranked candidates: **{directional_ranked}**",
        f"Directional near misses: **{directional_near_misses}**",
        f"Directional specialists: **{directional_specialists}**",
        f"Exported candidates: **{len(exported)}**",
        f"Best candidate path: `{exported[0]}`" if exported else "Best candidate path: n/a",
        "",
        "## Directional Funnel",
        "",
        "| Step | Count |",
        "| --- | ---: |",
        f"| Generated | {generated} |",
        f"| Directional survivors | {directional_survivors} |",
        f"| Directional ranked candidates | {directional_ranked} |",
        f"| Directional near misses | {directional_near_misses} |",
        f"| Directional specialists | {directional_specialists} |",
        f"| Exported | {len(exported)} |",
        "",
        "## Next Owner Command",
        "",
    ]
    if exported:
        lines.extend(
            [
                "Directional exports are under `directional_candidates/`. Pick a candidate manually before downstream validation.",
                "",
            ]
        )
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _count_csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open(encoding="utf-8", newline="") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def _count_directional_survivors(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open(encoding="utf-8", newline="") as fh:
        return sum(1 for row in csv.DictReader(fh) if str(row.get("should_promote", "")).lower() == "true")


def _read_directional_candidate_ids(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            str(row["candidate_id"])
            for row in csv.DictReader(fh)
            if row.get("candidate_id")
        }
