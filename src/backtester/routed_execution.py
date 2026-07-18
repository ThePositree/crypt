"""Continuous portfolio replay for single-strategy router selections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.mandate_report import MandateReport, build_mandate_report


@dataclass(frozen=True, slots=True)
class RoutedExecutionConfig:
    start: str = "2025-01-01"
    end: str = "2026-01-01"
    initial_capital: float = 10_000.0
    max_allowed_margin: float = 1.0


@dataclass(frozen=True, slots=True)
class RoutedExecutionResult:
    routed_trades: pd.DataFrame
    rejected_entries: pd.DataFrame
    selection_timeline: pd.DataFrame
    execution_summary: pd.DataFrame
    mandate: MandateReport


def load_matrix_strategy_trades(matrix_dir: Path) -> dict[str, pd.DataFrame]:
    """Load one trade DataFrame per strategy from a matrix artifact."""

    trades_dir = matrix_dir / "strategy_trades"
    if not trades_dir.exists():
        raise ValueError(f"Missing strategy trade directory: {trades_dir}")
    result: dict[str, pd.DataFrame] = {}
    for path in sorted(trades_dir.glob("*.csv")):
        try:
            result[path.stem] = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            result[path.stem] = pd.DataFrame()
    if not result:
        raise ValueError(f"No strategy trade CSVs found under: {trades_dir}")
    return result


def evaluate_routed_execution(
    *,
    predictions: pd.DataFrame,
    router: str,
    trades_by_strategy: dict[str, pd.DataFrame],
    config: RoutedExecutionConfig,
) -> RoutedExecutionResult:
    """Replay selected strategy trades through one shared portfolio."""

    _validate_config(config)
    start = pd.Timestamp(config.start, tz="UTC")
    end = pd.Timestamp(config.end, tz="UTC")
    selections = _prepare_selections(
        predictions,
        router=router,
        strategy_ids=set(trades_by_strategy),
        start=start,
        end=end,
    )
    entries = _prepare_source_entries(
        trades_by_strategy,
        selections=selections,
        start=start,
        end=end,
    )
    routed, rejected, diagnostics = _replay_entries(
        entries,
        initial_capital=config.initial_capital,
        max_allowed_margin=config.max_allowed_margin,
    )
    mandate = build_mandate_report(
        routed,
        initial_capital=config.initial_capital,
        start=config.start,
        end=config.end,
    )
    summary = _execution_summary(
        router=router,
        selections=selections,
        entries=entries,
        routed=routed,
        rejected=rejected,
        diagnostics=diagnostics,
        config=config,
        start=start,
        end=end,
    )
    return RoutedExecutionResult(
        routed_trades=routed,
        rejected_entries=rejected,
        selection_timeline=selections,
        execution_summary=summary,
        mandate=mandate,
    )


def write_routed_execution_report(*, output: Path, result: RoutedExecutionResult) -> None:
    """Write routed trades, mandate diagnostics, and a compact report."""

    output.mkdir(parents=True, exist_ok=True)
    result.routed_trades.to_csv(output / "routed_trades.csv", index=False)
    result.rejected_entries.to_csv(output / "rejected_entries.csv", index=False)
    result.selection_timeline.to_csv(output / "selection_timeline.csv", index=False)
    result.execution_summary.to_csv(output / "execution_summary.csv", index=False)
    result.mandate.monthly.to_csv(output / "monthly_mandate.csv", index=False)
    result.mandate.summary.to_csv(output / "mandate_summary.csv", index=False)

    report = [
        "# Routed Execution Validation",
        "",
        "Exactly one strategy is selected at every decision point. Position",
        "handoffs use drain semantics, so two strategies are never open",
        "simultaneously.",
        "",
        "## Execution Summary",
        "",
        _markdown_table(result.execution_summary),
        "",
        "## Mandate Summary",
        "",
        _markdown_table(result.mandate.summary),
        "",
        "## Monthly Mandate",
        "",
        _markdown_table(result.mandate.monthly),
        "",
        "The report is a replay of archived trades. It is not a fresh OHLCV",
        "multi-strategy simulation; see `docs/routed_execution_validation.md`.",
        "",
    ]
    (output / "report.md").write_text("\n".join(report), encoding="utf-8")


def _validate_config(config: RoutedExecutionConfig) -> None:
    if config.initial_capital <= 0:
        raise ValueError("initial_capital must be > 0")
    if not 0 < config.max_allowed_margin <= 1:
        raise ValueError("max_allowed_margin must be in (0, 1]")
    if pd.Timestamp(config.end) <= pd.Timestamp(config.start):
        raise ValueError("end must be after start")


def _prepare_selections(
    predictions: pd.DataFrame,
    *,
    router: str,
    strategy_ids: set[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    required = {"router", "asof", "selected_strategy"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Router predictions missing columns: {', '.join(missing)}")

    frame = predictions[predictions["router"] == router].copy()
    if frame.empty:
        raise ValueError(f"Router not found in predictions: {router}")
    frame["asof"] = pd.to_datetime(frame["asof"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["asof"]).sort_values("asof")
    frame = frame.drop_duplicates("asof", keep="last")
    frame["selected_strategy"] = frame["selected_strategy"].astype(str).str.strip()
    invalid = frame[
        frame["selected_strategy"].str.lower().isin({"", "cash", "none", "nan"})
    ]
    if not invalid.empty:
        raise ValueError("Router predictions contain cash or empty selections")
    unknown = sorted(set(frame["selected_strategy"]) - strategy_ids)
    if unknown:
        raise ValueError("Router selects strategies missing from matrix: " + ", ".join(unknown))

    prior = frame[frame["asof"] <= start].tail(1)
    within = frame[(frame["asof"] > start) & (frame["asof"] < end)]
    timeline = pd.concat([prior, within], ignore_index=True)
    if timeline.empty or timeline.iloc[0]["asof"] > start:
        raise ValueError(f"No router selection is available at validation start {start}")
    return timeline[["router", "asof", "selected_strategy"]].reset_index(drop=True)


def _prepare_source_entries(
    trades_by_strategy: dict[str, pd.DataFrame],
    *,
    selections: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for strategy_id, source in trades_by_strategy.items():
        if source.empty:
            continue
        required = {
            "entry_time",
            "exit_time",
            "pnl_abs",
            "risk_base_capital",
            "locked_margin",
        }
        missing = sorted(required - set(source.columns))
        if missing:
            raise ValueError(
                f"Strategy {strategy_id} trades missing columns: {', '.join(missing)}"
            )
        frame = source.copy()
        decision_column = "signal_time" if "signal_time" in frame.columns else "entry_time"
        for column in {decision_column, "entry_time", "exit_time"}:
            frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)
        frame = frame.dropna(subset=[decision_column, "entry_time", "exit_time"])
        frame = frame[(frame[decision_column] >= start) & (frame[decision_column] < end)]
        if frame.empty:
            continue
        frame["decision_time"] = frame[decision_column]
        frame["source_strategy"] = strategy_id
        frame["source_trade_id"] = [f"{strategy_id}:{index}" for index in frame.index]
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    entries = pd.concat(frames, ignore_index=True).sort_values("decision_time")
    matched = pd.merge_asof(
        entries,
        selections[["asof", "selected_strategy"]].sort_values("asof"),
        left_on="decision_time",
        right_on="asof",
        direction="backward",
    )
    if matched["selected_strategy"].isna().any():
        raise ValueError("Some source trades have no router selection at decision time")
    matched["router_selected"] = (
        matched["source_strategy"] == matched["selected_strategy"]
    )
    return matched.reset_index(drop=True)


def _replay_entries(
    entries: pd.DataFrame,
    *,
    initial_capital: float,
    max_allowed_margin: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if entries.empty:
        return pd.DataFrame(), pd.DataFrame(), _empty_diagnostics(initial_capital)

    events: list[tuple[pd.Timestamp, int, int]] = []
    for index, row in entries[entries["router_selected"]].iterrows():
        events.append((row["entry_time"], 1, index))
        events.append((row["exit_time"], 0, index))
    events.sort(key=lambda item: (item[0], item[1], item[2]))

    capital = initial_capital
    active: dict[int, dict[str, Any]] = {}
    routed_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    risk_window_key: tuple[int, int] | None = None
    risk_window_capital = initial_capital
    peak_locked_margin = 0.0
    peak_locked_margin_pct = 0.0
    max_concurrent_positions = 0

    for event_time, event_kind, index in events:
        row = entries.loc[index]
        if event_kind == 0:
            position = active.pop(index, None)
            if position is None:
                continue
            pnl_abs = float(row["pnl_abs"]) * position["scale"]
            capital_before_exit = capital
            capital += pnl_abs
            output_row = row.to_dict()
            output_row.update(
                {
                    "source_pnl_abs": float(row["pnl_abs"]),
                    "source_risk_base_capital": float(row["risk_base_capital"]),
                    "source_locked_margin": float(row["locked_margin"]),
                    "scale": position["scale"],
                    "pnl_abs": pnl_abs,
                    "risk_base_capital": position["routed_risk_base"],
                    "locked_margin": position["locked_margin"],
                    "capital_before": capital_before_exit,
                    "capital_after": capital,
                }
            )
            routed_rows.append(output_row)
            continue

        active_strategies = {item["strategy"] for item in active.values()}
        if active_strategies and row["source_strategy"] not in active_strategies:
            rejected_rows.append(_rejection_row(row, reason="draining_previous_strategy"))
            continue

        window_key = (int(event_time.year), int(event_time.month))
        if risk_window_key != window_key:
            risk_window_key = window_key
            risk_window_capital = capital
        source_risk_base = float(row["risk_base_capital"])
        if source_risk_base <= 0:
            rejected_rows.append(_rejection_row(row, reason="invalid_source_risk_base"))
            continue
        scale = risk_window_capital / source_risk_base
        locked_margin = float(row["locked_margin"]) * scale
        current_locked = sum(float(item["locked_margin"]) for item in active.values())
        allowed_margin = max(capital, 0.0) * max_allowed_margin
        if current_locked + locked_margin > allowed_margin:
            rejected_rows.append(
                _rejection_row(
                    row,
                    reason="margin_limit",
                    routed_locked_margin=locked_margin,
                    total_locked_margin_before=current_locked,
                    allowed_locked_margin=allowed_margin,
                )
            )
            continue

        active[index] = {
            "strategy": row["source_strategy"],
            "scale": scale,
            "routed_risk_base": risk_window_capital,
            "locked_margin": locked_margin,
        }
        total_locked = current_locked + locked_margin
        peak_locked_margin = max(peak_locked_margin, total_locked)
        if capital > 0:
            peak_locked_margin_pct = max(
                peak_locked_margin_pct,
                total_locked / capital * 100.0,
            )
        max_concurrent_positions = max(max_concurrent_positions, len(active))

    diagnostics = {
        "initial_capital": initial_capital,
        "final_capital": capital,
        "peak_locked_margin": peak_locked_margin,
        "peak_locked_margin_pct": peak_locked_margin_pct,
        "max_concurrent_positions": max_concurrent_positions,
    }
    routed = pd.DataFrame(routed_rows)
    if not routed.empty:
        routed = routed.sort_values("exit_time").reset_index(drop=True)
    rejected = pd.DataFrame(rejected_rows)
    if not rejected.empty:
        rejected = rejected.sort_values("entry_time").reset_index(drop=True)
    return routed, rejected, diagnostics


def _rejection_row(row: pd.Series, *, reason: str, **extra: Any) -> dict[str, Any]:
    result = {
        "source_trade_id": row["source_trade_id"],
        "source_strategy": row["source_strategy"],
        "selected_strategy": row["selected_strategy"],
        "decision_time": row["decision_time"],
        "entry_time": row["entry_time"],
        "exit_time": row["exit_time"],
        "reason": reason,
    }
    result.update(extra)
    return result


def _execution_summary(
    *,
    router: str,
    selections: pd.DataFrame,
    entries: pd.DataFrame,
    routed: pd.DataFrame,
    rejected: pd.DataFrame,
    diagnostics: dict[str, Any],
    config: RoutedExecutionConfig,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    selected = selections[
        (selections["asof"] >= start) & (selections["asof"] < end)
    ]["selected_strategy"]
    if selected.empty:
        selected = selections.tail(1)["selected_strategy"]
    switches = int(selected.ne(selected.shift()).sum() - 1) if len(selected) else 0
    final_capital = float(diagnostics["final_capital"])
    total_return_pct = (final_capital / config.initial_capital - 1.0) * 100.0
    rejection_counts = (
        rejected["reason"].value_counts().to_dict() if not rejected.empty else {}
    )
    last_prediction = selections["asof"].max()
    staleness_days = max((end - last_prediction).total_seconds() / 86400.0, 0.0)
    active_candidates = (
        int(entries["router_selected"].sum()) if not entries.empty else 0
    )
    inactive_entries = (
        int((~entries["router_selected"]).sum()) if not entries.empty else 0
    )
    return pd.DataFrame(
        [
            {
                "router": router,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "initial_capital": config.initial_capital,
                "final_capital": round(final_capital, 2),
                "total_return_pct": round(total_return_pct, 2),
                "accepted_trades": len(routed),
                "selected_candidate_entries": active_candidates,
                "inactive_strategy_entries": inactive_entries,
                "rejected_entries": len(rejected),
                "drain_rejections": int(
                    rejection_counts.get("draining_previous_strategy", 0)
                ),
                "margin_rejections": int(rejection_counts.get("margin_limit", 0)),
                "router_switches": max(switches, 0),
                "selected_strategies": int(selected.nunique()),
                "max_concurrent_positions": int(
                    diagnostics["max_concurrent_positions"]
                ),
                "peak_locked_margin": round(
                    float(diagnostics["peak_locked_margin"]), 2
                ),
                "peak_locked_margin_pct": round(
                    float(diagnostics["peak_locked_margin_pct"]), 2
                ),
                "last_prediction_asof": last_prediction.isoformat(),
                "max_selection_staleness_days": round(staleness_days, 2),
                "selection_carry_forward": True,
                "switch_policy": "drain",
            }
        ]
    )


def _empty_diagnostics(initial_capital: float) -> dict[str, Any]:
    return {
        "initial_capital": initial_capital,
        "final_capital": initial_capital,
        "peak_locked_margin": 0.0,
        "peak_locked_margin_pct": 0.0,
        "max_concurrent_positions": 0,
    }


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for values in frame.itertuples(index=False, name=None):
        cells = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
