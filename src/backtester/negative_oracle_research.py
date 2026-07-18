from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from backtester.trade_filter_research import (
    CompoundFilterRule,
    FilterRule,
    _rule_mask,
    generate_candidate_rules,
    generate_pair_candidate_rules,
    load_trade_artifacts,
    prepare_trade_features,
)


@dataclass(frozen=True, slots=True)
class NegativeOracleConfig:
    trades_path: Path
    output_dir: Path
    train_start: str = "2022-01-01"
    validation_start: str = "2024-01-01"
    stress_start: str = "2025-01-01"
    min_train_trades: int = 30
    max_categories: int = 30
    max_pair_components: int = 40
    max_pair_rules: int = 800
    top_n: int = 100
    progress: bool = True


@dataclass(frozen=True, slots=True)
class NegativeOracleResult:
    output_dir: Path
    rules: pd.DataFrame


def run_negative_oracle_research(config: NegativeOracleConfig) -> NegativeOracleResult:
    trades = prepare_trade_features(load_trade_artifacts((config.trades_path,)))
    if trades.empty:
        raise ValueError("No trades found")
    if "entry_time" not in trades.columns or "pnl_abs" not in trades.columns:
        raise ValueError("trades.csv must contain entry_time and pnl_abs")

    train = _split_frame(
        trades,
        start=config.train_start,
        end=config.validation_start,
    )
    single_rules = generate_candidate_rules(
        train,
        min_train_trades=config.min_train_trades,
        max_categories=config.max_categories,
        include_portfolio_state_features=False,
    )

    single_rows = _evaluate_rules(
        trades=trades,
        rules=single_rules,
        config=config,
        rule_kind="single",
        progress_label="negative oracle single rules",
    )
    single_df = pd.DataFrame(single_rows)

    pair_rules = generate_pair_candidate_rules(
        single_candidates=single_df.sort_values(
            ["train_delta_abs", "train_loser_loss_removed_abs"],
            ascending=False,
        )
        if not single_df.empty
        else single_df,
        max_components=config.max_pair_components,
        max_pair_rules=config.max_pair_rules,
    )
    pair_rows = _evaluate_rules(
        trades=trades,
        rules=pair_rules,
        config=config,
        rule_kind="pair",
        progress_label="negative oracle pair rules",
    )

    rules = pd.DataFrame([*single_rows, *pair_rows])
    if not rules.empty:
        rules["robust_negative_pass"] = (
            (rules["train_delta_abs"] > 0.0)
            & (rules["validation_delta_abs"] > 0.0)
            & (rules["stress_delta_abs"] > 0.0)
            & (rules["validation_blocked_trades"] >= config.min_train_trades)
        )
        rules["robust_negative_score"] = (
            rules["validation_delta_abs"]
            + rules["stress_delta_abs"]
            + rules["train_delta_abs"].clip(upper=rules["validation_delta_abs"].abs() * 2.0)
            - rules["stress_winner_profit_cut_abs"].clip(lower=0.0)
        )
        rules = rules.sort_values(
            [
                "robust_negative_pass",
                "robust_negative_score",
                "validation_delta_abs",
                "stress_delta_abs",
            ],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    rules.to_csv(config.output_dir / "negative_rules.csv", index=False)
    rules.head(config.top_n).to_csv(config.output_dir / "top_negative_rules.csv", index=False)
    (config.output_dir / "report.md").write_text(
        _markdown_report(trades=trades, rules=rules, top_n=config.top_n),
        encoding="utf-8",
    )
    return NegativeOracleResult(output_dir=config.output_dir, rules=rules)


def _evaluate_rules(
    *,
    trades: pd.DataFrame,
    rules: list[FilterRule] | list[CompoundFilterRule],
    config: NegativeOracleConfig,
    rule_kind: str,
    progress_label: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    iterator = tqdm(
        rules,
        total=len(rules),
        desc=progress_label,
        unit="rule",
        disable=not config.progress,
    )
    for rule in iterator:
        rows.append(_evaluate_rule(trades=trades, rule=rule, config=config, rule_kind=rule_kind))
    return rows


def _evaluate_rule(
    *,
    trades: pd.DataFrame,
    rule: FilterRule | CompoundFilterRule,
    config: NegativeOracleConfig,
    rule_kind: str,
) -> dict[str, Any]:
    mask = _rule_mask(trades, rule)
    row: dict[str, Any] = {
        "rule_kind": rule_kind,
        "feature": getattr(rule, "feature", ""),
        "op": getattr(rule, "op", "and"),
        "value": getattr(rule, "value", ""),
        "expression": rule.expression,
        "blocked_trades_total": int(mask.sum()),
        "kept_trades_total": int((~mask).sum()),
        "total_delta_abs": float(-trades.loc[mask, "pnl_abs"].sum()),
    }
    for split_name, start, end in _split_specs(config):
        split = _split_frame(trades, start=start, end=end)
        split_mask = mask.loc[split.index] if not split.empty else pd.Series(dtype=bool)
        row.update(_prefix_metrics(split_name, split, split_mask))
    row["train_trade_count"] = row["train_blocked_trades"]
    return row


def _prefix_metrics(prefix: str, split: pd.DataFrame, blocked_mask: pd.Series) -> dict[str, Any]:
    if split.empty:
        return {
            f"{prefix}_trades": 0,
            f"{prefix}_blocked_trades": 0,
            f"{prefix}_blocked_pnl_abs": 0.0,
            f"{prefix}_delta_abs": 0.0,
            f"{prefix}_loser_loss_removed_abs": 0.0,
            f"{prefix}_winner_profit_cut_abs": 0.0,
        }
    blocked = split.loc[blocked_mask]
    blocked_pnl = pd.to_numeric(blocked["pnl_abs"], errors="coerce").fillna(0.0)
    loser_loss = float(-blocked_pnl[blocked_pnl < 0].sum())
    winner_profit = float(blocked_pnl[blocked_pnl > 0].sum())
    return {
        f"{prefix}_trades": len(split),
        f"{prefix}_blocked_trades": len(blocked),
        f"{prefix}_blocked_pnl_abs": float(blocked_pnl.sum()),
        f"{prefix}_delta_abs": float(-blocked_pnl.sum()),
        f"{prefix}_loser_loss_removed_abs": loser_loss,
        f"{prefix}_winner_profit_cut_abs": winner_profit,
    }


def _split_frame(trades: pd.DataFrame, *, start: str, end: str | None) -> pd.DataFrame:
    entry = pd.to_datetime(trades["entry_time"], utc=True, errors="coerce")
    start_ts = pd.Timestamp(start, tz="UTC")
    mask = entry >= start_ts
    if end is not None:
        mask &= entry < pd.Timestamp(end, tz="UTC")
    return trades.loc[mask].copy()


def _split_specs(config: NegativeOracleConfig) -> tuple[tuple[str, str, str | None], ...]:
    return (
        ("train", config.train_start, config.validation_start),
        ("validation", config.validation_start, config.stress_start),
        ("stress", config.stress_start, None),
    )


def _markdown_report(*, trades: pd.DataFrame, rules: pd.DataFrame, top_n: int) -> str:
    total_pnl = float(pd.to_numeric(trades["pnl_abs"], errors="coerce").fillna(0.0).sum())
    lines = [
        "# Negative oracle research",
        "",
        f"- Trades: {len(trades)}",
        f"- Baseline PnL: ${total_pnl:,.2f}",
        f"- Rules tested: {len(rules)}",
        "",
    ]
    if rules.empty:
        lines.append("No rules generated.")
        return "\n".join(lines)

    robust = rules[rules["robust_negative_pass"]].head(top_n)
    table = robust if not robust.empty else rules.head(top_n)
    lines.extend(
        [
            "## Top skip rules",
            "",
            _to_markdown_table(
                table[
                    [
                        "expression",
                        "blocked_trades_total",
                        "train_delta_abs",
                        "validation_delta_abs",
                        "stress_delta_abs",
                        "validation_loser_loss_removed_abs",
                        "validation_winner_profit_cut_abs",
                        "stress_loser_loss_removed_abs",
                        "stress_winner_profit_cut_abs",
                        "robust_negative_pass",
                    ]
                ]
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    columns = list(frame.columns)
    rows = ["| " + " | ".join(columns) + " |"]
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for _, row in frame.iterrows():
        values = [_format_markdown_value(row[column]) for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _format_markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")
