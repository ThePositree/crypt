from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from tqdm.auto import tqdm

from backtester.mandate_report import build_mandate_report
from backtester.strategy_discovery.features import build_donor_discovery_features

DEFAULT_TRAIN_START = "2022-01-01"
DEFAULT_VALIDATION_START = "2024-01-01"
DEFAULT_STRESS_START = "2025-01-01"

RuleOp = Literal["<=", ">=", "==", "!="]
FeatureGroup = Literal["market_entry", "portfolio_state", "metadata"]
_NUMERIC_RULE_OPS: tuple[RuleOp, ...] = ("<=", ">=")
_CATEGORICAL_RULE_OPS: tuple[RuleOp, ...] = ("==", "!=")

_REQUIRED_COLUMNS = {"entry_time", "exit_time", "pnl_abs"}
_LEAKY_COLUMNS = {
    "signal_time",
    "entry_time",
    "exit_time",
    "exit_price",
    "exit_reason",
    "pnl_abs",
    "pnl_rel",
    "fee_exit",
    "capital_after",
    "holding_bars",
    "exit_bar_index",
    "trail_active",
    "trail_stop_price",
}
_LOW_VALUE_COLUMNS = {
    "router_id",
}
_TIME_PROXY_COLUMNS = {
    "entry_price",
    "fee_entry",
    "sl_price",
    "tp_price",
}
_PORTFOLIO_STATE_COLUMNS = {
    "available_balance_before",
    "capital_before",
    "leverage",
    "locked_margin",
    "open_positions_before",
    "risk_base_capital",
    "size",
    "total_locked_margin_after_entry",
    "total_locked_margin_before",
}


@dataclass(frozen=True, slots=True)
class SplitConfig:
    train_start: str = DEFAULT_TRAIN_START
    validation_start: str = DEFAULT_VALIDATION_START
    stress_start: str = DEFAULT_STRESS_START
    stress_end: str | None = None


@dataclass(frozen=True, slots=True)
class FilterSearchConfig:
    trades_paths: tuple[Path, ...]
    output_dir: Path
    ohlcv_path: Path | None = None
    group_by: str | None = None
    initial_capital: float = 10_000.0
    splits: SplitConfig = SplitConfig()
    min_train_trades: int = 30
    max_categories: int = 20
    top_n: int = 50
    progress: bool = True
    include_catalog_features: bool = False
    include_portfolio_state_features: bool = False
    max_pair_components: int = 30
    max_pair_rules: int = 500


@dataclass(frozen=True, slots=True)
class FilterRule:
    feature: str
    op: RuleOp
    value: float | str | bool

    @property
    def expression(self) -> str:
        value = repr(self.value) if isinstance(self.value, str) else str(self.value)
        return f"{self.feature} {self.op} {value}"


@dataclass(frozen=True, slots=True)
class CompoundFilterRule:
    left: FilterRule
    right: FilterRule

    @property
    def expression(self) -> str:
        return f"({self.left.expression}) AND ({self.right.expression})"


@dataclass(frozen=True, slots=True)
class TradeFilterResearchResult:
    baseline_by_split: pd.DataFrame
    filter_candidates: pd.DataFrame
    top_filters: pd.DataFrame
    output_dir: Path


def run_trade_filter_research(config: FilterSearchConfig) -> TradeFilterResearchResult:
    if not config.trades_paths:
        raise ValueError("at least one trades path is required")
    if config.initial_capital <= 0:
        raise ValueError("initial_capital must be > 0")

    trades = load_trade_artifacts(config.trades_paths)
    prepared = prepare_trade_features(trades)
    if config.include_catalog_features:
        if config.ohlcv_path is None:
            raise ValueError("--ohlcv is required when --include-catalog-features is set")
        prepared = attach_catalog_features(prepared, config.ohlcv_path)
    if config.group_by is not None and config.group_by not in prepared.columns:
        raise ValueError(f"--group-by column not found in trades: {config.group_by}")
    split_end = _stress_end(prepared, config.splits)

    baseline_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    rule_count = 0
    for group_value, group_frame in _research_groups(prepared, group_by=config.group_by):
        baseline = _baseline_by_split(
            group_frame,
            splits=config.splits,
            stress_end=split_end,
            initial_capital=config.initial_capital,
        )
        if config.group_by is not None:
            baseline.insert(0, "group_value", group_value)
            baseline.insert(0, "group_by", config.group_by)
        baseline_frames.append(baseline)

        candidates, group_rule_count = _evaluate_rule_set(
            group_frame,
            baseline=baseline,
            group_value=group_value,
            config=config,
            stress_end=split_end,
        )
        rule_count += group_rule_count
        if not candidates.empty:
            candidate_frames.append(candidates)

    baseline = (
        pd.concat(baseline_frames, ignore_index=True)
        if baseline_frames
        else pd.DataFrame()
    )
    candidates = (
        pd.concat(candidate_frames, ignore_index=True)
        if candidate_frames
        else pd.DataFrame()
    )
    if not candidates.empty:
        candidates = _sort_candidates(candidates)
    top_filters = _validation_shortlist(candidates, top_n=config.top_n)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    baseline.to_csv(config.output_dir / "baseline_by_split.csv", index=False)
    candidates.to_csv(config.output_dir / "filter_candidates.csv", index=False)
    top_filters.to_csv(config.output_dir / "top_filters.csv", index=False)
    (config.output_dir / "report.md").write_text(
        _markdown_report(
            baseline=baseline,
            top_filters=top_filters,
            config=config,
            stress_end=split_end,
            feature_count=len(
                _entry_feature_columns(
                    prepared,
                    include_portfolio_state_features=config.include_portfolio_state_features,
                )
            ),
            rule_count=rule_count,
        )
    )

    return TradeFilterResearchResult(
        baseline_by_split=baseline,
        filter_candidates=candidates,
        top_filters=top_filters,
        output_dir=config.output_dir,
    )


def _research_groups(
    prepared: pd.DataFrame,
    *,
    group_by: str | None,
) -> list[tuple[str | None, pd.DataFrame]]:
    if group_by is None:
        return [(None, prepared)]
    groups: list[tuple[str | None, pd.DataFrame]] = []
    for raw_value, group_frame in prepared.groupby(group_by, dropna=False, sort=True):
        value = "<NA>" if pd.isna(raw_value) else str(raw_value)
        groups.append((value, group_frame.reset_index(drop=True)))
    return groups


def _evaluate_rule_set(
    prepared: pd.DataFrame,
    *,
    baseline: pd.DataFrame,
    group_value: str | None,
    config: FilterSearchConfig,
    stress_end: str,
) -> tuple[pd.DataFrame, int]:
    train = _split_frame(
        prepared,
        start=config.splits.train_start,
        end=config.splits.validation_start,
    )
    if config.group_by is not None and config.group_by in train.columns:
        train = train.drop(columns=[config.group_by])

    rules = generate_candidate_rules(
        train,
        min_train_trades=config.min_train_trades,
        max_categories=config.max_categories,
        include_portfolio_state_features=config.include_portfolio_state_features,
    )
    rows = []
    rule_iterable = tqdm(
        rules,
        desc=_progress_label("trade-filter rules", group_value),
        unit="rule",
        disable=not config.progress,
    )
    for rule in rule_iterable:
        rows.append(
            _evaluate_rule(
                rule,
                prepared,
                splits=config.splits,
                stress_end=stress_end,
                initial_capital=config.initial_capital,
            )
        )
    candidates = pd.DataFrame(rows)
    if not candidates.empty:
        candidates = _add_baseline_deltas(candidates, baseline)
        candidates = _sort_candidates(candidates)

    pair_rules = generate_pair_candidate_rules(
        single_candidates=candidates,
        max_components=config.max_pair_components,
        max_pair_rules=config.max_pair_rules,
    )
    pair_rows = []
    pair_iterable = tqdm(
        pair_rules,
        desc=_progress_label("trade-filter pair rules", group_value),
        unit="rule",
        disable=not config.progress,
    )
    for rule in pair_iterable:
        pair_rows.append(
            _evaluate_rule(
                rule,
                prepared,
                splits=config.splits,
                stress_end=stress_end,
                initial_capital=config.initial_capital,
            )
        )
    if pair_rows:
        pair_candidates = _add_baseline_deltas(pd.DataFrame(pair_rows), baseline)
        candidates = pd.concat([candidates, pair_candidates], ignore_index=True)
        candidates = _sort_candidates(candidates)

    if config.group_by is not None and not candidates.empty:
        candidates.insert(0, "group_value", group_value)
        candidates.insert(0, "group_by", config.group_by)
    return candidates, len(rules) + len(pair_rules)


def _sort_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    return candidates.sort_values(
        [
            "robust_forward_pass",
            "robust_forward_score",
            "stress_score_delta",
            "validation_score_delta",
        ],
        ascending=[False, False, False, False],
        kind="mergesort",
    ).reset_index(drop=True)


def _progress_label(label: str, group_value: str | None) -> str:
    return label if group_value is None else f"{label} [{group_value}]"


def load_trade_artifacts(paths: tuple[Path, ...]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            frame = pd.DataFrame(columns=sorted(_REQUIRED_COLUMNS))
        missing = sorted(_REQUIRED_COLUMNS - set(frame.columns))
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        frame = frame.copy()
        frame["source_path"] = str(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def prepare_trade_features(trades: pd.DataFrame) -> pd.DataFrame:
    prepared = trades.copy()
    prepared["entry_time"] = pd.to_datetime(prepared["entry_time"], utc=True, errors="coerce")
    prepared["exit_time"] = pd.to_datetime(prepared["exit_time"], utc=True, errors="coerce")
    prepared["pnl_abs"] = pd.to_numeric(prepared["pnl_abs"], errors="coerce").fillna(0.0)
    prepared = prepared.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(
        drop=True
    )

    prepared["entry_hour"] = prepared["entry_time"].dt.hour
    prepared["entry_dayofweek"] = prepared["entry_time"].dt.dayofweek

    if {"entry_price", "sl_price"}.issubset(prepared.columns):
        entry = pd.to_numeric(prepared["entry_price"], errors="coerce")
        stop = pd.to_numeric(prepared["sl_price"], errors="coerce")
        prepared["stop_distance_pct"] = (entry - stop).abs() / entry.abs()
    if {"entry_price", "tp_price"}.issubset(prepared.columns):
        entry = pd.to_numeric(prepared["entry_price"], errors="coerce")
        take = pd.to_numeric(prepared["tp_price"], errors="coerce")
        prepared["tp_distance_pct"] = (take - entry).abs() / entry.abs()
    if {"stop_distance_pct", "tp_distance_pct"}.issubset(prepared.columns):
        stop_distance = pd.to_numeric(prepared["stop_distance_pct"], errors="coerce")
        tp_distance = pd.to_numeric(prepared["tp_distance_pct"], errors="coerce")
        prepared["reward_to_risk"] = tp_distance / stop_distance.replace(0.0, pd.NA)

    return prepared


def attach_catalog_features(trades: pd.DataFrame, ohlcv_path: Path) -> pd.DataFrame:
    """Attach catalog-like closed-candle features known at trade entry time."""
    ohlcv = _load_ohlcv(ohlcv_path)
    features = build_donor_discovery_features(primary=ohlcv, h4=None, d1=None)
    catalog = pd.DataFrame(index=features.index)
    catalog["catalog_atr_pct"] = features["atr_pct"]
    catalog["catalog_volatility_rank"] = features["volatility_rank"]
    catalog["catalog_trend_strength_atr"] = features["trend_strength_atr"]
    catalog["catalog_rsi14"] = features["rsi14"]
    catalog["catalog_bb_width_pct"] = features["bb_width_pct"]
    catalog["catalog_body_to_range"] = features["body_to_range"]
    catalog["catalog_bar_range_atr"] = features["bar_range_atr"]
    catalog["catalog_roc10"] = features["roc10"]
    catalog["catalog_volume_ratio_20"] = features["volume_ratio_20"]
    catalog["catalog_ema_stack_long"] = features["ema_stack_long"].astype("boolean")
    catalog["catalog_ema_stack_short"] = features["ema_stack_short"].astype("boolean")
    catalog["catalog_bb_squeeze"] = (features["bb_width_rank_20"] <= 0.25).astype(
        "boolean"
    )
    catalog["catalog_bb_wide"] = (features["bb_width_rank_20"] >= 0.75).astype(
        "boolean"
    )
    catalog["catalog_volume_above_median"] = (
        features["volume_ratio_20"] >= 1.0
    ).astype("boolean")
    catalog["catalog_session_london"] = features["hour_utc"].between(7, 16).astype(
        "boolean"
    )
    catalog["catalog_session_ny"] = features["hour_utc"].between(13, 21).astype(
        "boolean"
    )
    catalog = catalog.reset_index(names="catalog_time").sort_values("catalog_time")

    prepared = trades.sort_values("entry_time").reset_index(drop=True)
    merged = pd.merge_asof(
        prepared,
        catalog,
        left_on="entry_time",
        right_on="catalog_time",
        direction="backward",
        allow_exact_matches=False,
    )
    return merged.drop(columns=["catalog_time"])


def _load_ohlcv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)

    time_column = next(
        (
            column
            for column in ("open_time", "timestamp", "datetime", "time", "date")
            if column in frame
        ),
        None,
    )
    if time_column is not None:
        frame[time_column] = pd.to_datetime(frame[time_column], utc=True, errors="coerce")
        frame = frame.dropna(subset=[time_column]).set_index(time_column)
    elif not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("OHLCV must have a datetime index or timestamp/datetime/time/date column")
    else:
        frame.index = pd.to_datetime(frame.index, utc=True, errors="coerce")
        frame = frame[frame.index.notna()]

    frame = frame.sort_index()
    required = ["open", "high", "low", "close", "volume"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"OHLCV is missing required columns: {sorted(missing)}")
    return frame[required]


def generate_candidate_rules(
    train: pd.DataFrame,
    *,
    min_train_trades: int,
    max_categories: int,
    include_portfolio_state_features: bool = False,
) -> list[FilterRule]:
    rules: list[FilterRule] = []
    if train.empty:
        return rules

    for column in _entry_feature_columns(
        train,
        include_portfolio_state_features=include_portfolio_state_features,
    ):
        series = train[column]
        if pd.api.types.is_bool_dtype(series):
            values = series.dropna().astype(str)
            for value in sorted(values.unique()):
                for bool_op in _CATEGORICAL_RULE_OPS:
                    rule = FilterRule(feature=column, op=bool_op, value=value)
                    if int(_rule_mask(train, rule).sum()) >= min_train_trades:
                        rules.append(rule)
            continue

        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if numeric.nunique(dropna=True) < 2:
                continue
            thresholds = numeric.quantile([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
            for raw_threshold in thresholds.dropna().unique():
                threshold = float(raw_threshold)
                for numeric_op in _NUMERIC_RULE_OPS:
                    rule = FilterRule(feature=column, op=numeric_op, value=threshold)
                    if int(_rule_mask(train, rule).sum()) >= min_train_trades:
                        rules.append(rule)
            continue

        values = series.dropna().astype(str)
        if values.nunique(dropna=True) < 2 or values.nunique(dropna=True) > max_categories:
            continue
        for value in sorted(values.unique()):
            for categorical_op in _CATEGORICAL_RULE_OPS:
                rule = FilterRule(feature=column, op=categorical_op, value=value)
                if int(_rule_mask(train, rule).sum()) >= min_train_trades:
                    rules.append(rule)

    return _dedupe_rules(rules)


def generate_pair_candidate_rules(
    *,
    single_candidates: pd.DataFrame,
    max_components: int,
    max_pair_rules: int,
) -> list[CompoundFilterRule]:
    if single_candidates.empty or max_components <= 1 or max_pair_rules <= 0:
        return []
    required = {"rule_kind", "feature", "op", "value", "train_trade_count"}
    if not required.issubset(single_candidates.columns):
        return []

    singles = single_candidates[single_candidates["rule_kind"] == "single"].copy()
    if singles.empty:
        return []
    singles = singles[
        pd.to_numeric(singles["train_trade_count"], errors="coerce").fillna(0.0) > 0.0
    ].head(max_components)

    rules: list[FilterRule] = []
    for _, row in singles.iterrows():
        raw_op = str(row["op"])
        if raw_op not in _NUMERIC_RULE_OPS and raw_op not in _CATEGORICAL_RULE_OPS:
            continue
        op = raw_op
        value = row["value"]
        if op in _NUMERIC_RULE_OPS:
            value = float(value)
        rules.append(FilterRule(feature=str(row["feature"]), op=op, value=value))

    pairs: list[CompoundFilterRule] = []
    seen: set[tuple[str, str]] = set()
    for left_idx, left in enumerate(rules):
        for right in rules[left_idx + 1 :]:
            if left.feature == right.feature:
                continue
            ordered = sorted([left.expression, right.expression])
            key = (ordered[0], ordered[1])
            if key in seen:
                continue
            seen.add(key)
            pairs.append(CompoundFilterRule(left=left, right=right))
            if len(pairs) >= max_pair_rules:
                return pairs
    return pairs


def _entry_feature_columns(
    frame: pd.DataFrame,
    *,
    include_portfolio_state_features: bool,
) -> list[str]:
    blocked = _LEAKY_COLUMNS | _LOW_VALUE_COLUMNS | _TIME_PROXY_COLUMNS
    columns: list[str] = []
    for column in frame.columns:
        if column in blocked:
            continue
        if column in _PORTFOLIO_STATE_COLUMNS and not include_portfolio_state_features:
            continue
        if column.endswith(("_time", "_bar_index")):
            continue
        if column.startswith("fee_") and column != "fee_entry":
            continue
        if column.startswith(("pnl_", "exit_")):
            continue
        columns.append(column)
    return columns


def _feature_group(feature: str) -> FeatureGroup:
    if feature in _PORTFOLIO_STATE_COLUMNS:
        return "portfolio_state"
    if feature in {"source_path"}:
        return "metadata"
    return "market_entry"


def _validation_shortlist(candidates: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    return candidates.sort_values(
        [
            "robust_forward_pass",
            "robust_forward_score",
            "stress_score_delta",
            "validation_score_delta",
        ],
        ascending=[False, False, False, False],
        kind="mergesort",
    ).head(top_n).reset_index(drop=True)


def _evaluate_rule(
    rule: FilterRule | CompoundFilterRule,
    trades: pd.DataFrame,
    *,
    splits: SplitConfig,
    stress_end: str,
    initial_capital: float,
) -> dict[str, Any]:
    filtered = trades[_rule_mask(trades, rule)].copy()
    row: dict[str, Any] = {
        **_rule_identity(rule),
        "expression": rule.expression,
        "kept_trades_total": len(filtered),
        "removed_trades_total": len(trades) - len(filtered),
    }
    for split_name, start, end in _split_specs(splits=splits, stress_end=stress_end):
        row.update(
            _prefix_metrics(
                split_name,
                _split_metrics(
                    filtered,
                    start=start,
                    end=end,
                    initial_capital=initial_capital,
                ),
            )
        )
    return row


def _rule_identity(rule: FilterRule | CompoundFilterRule) -> dict[str, Any]:
    if isinstance(rule, FilterRule):
        return {
            "rule_kind": "single",
            "feature": rule.feature,
            "feature_group": _feature_group(rule.feature),
            "op": rule.op,
            "value": rule.value,
        }
    groups = sorted({_feature_group(rule.left.feature), _feature_group(rule.right.feature)})
    return {
        "rule_kind": "pair",
        "feature": f"{rule.left.feature}&{rule.right.feature}",
        "feature_group": "+".join(groups),
        "op": "and",
        "value": f"{rule.left.expression} && {rule.right.expression}",
    }


def _add_baseline_deltas(candidates: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    enriched = candidates.copy()
    baselines = {str(row["split"]): row.to_dict() for _, row in baseline.iterrows()}
    for split in ("train", "validation", "stress"):
        baseline_row = baselines.get(split, {})
        for metric, delta_name in (
            ("return_pct", "return_delta_pct"),
            ("score", "score_delta"),
            ("months_passing_floor", "months_passing_floor_delta"),
            ("worst_monthly_drawdown_pct", "worst_monthly_drawdown_delta_pct"),
        ):
            candidate_col = f"{split}_{metric}"
            delta_col = f"{split}_{delta_name}"
            if candidate_col not in enriched.columns:
                continue
            baseline_value = float(baseline_row.get(metric, 0.0))
            enriched[delta_col] = pd.to_numeric(
                enriched[candidate_col],
                errors="coerce",
            ).fillna(0.0) - baseline_value

    enriched["robust_forward_pass"] = (
        (enriched.get("validation_score_delta", 0.0) > 0.0)
        & (enriched.get("stress_score_delta", 0.0) > 0.0)
        & (enriched.get("validation_return_delta_pct", 0.0) > 0.0)
        & (enriched.get("stress_return_delta_pct", 0.0) > 0.0)
        & (enriched.get("stress_months_passing_floor_delta", 0.0) >= 0.0)
        & (enriched.get("stress_worst_monthly_drawdown_delta_pct", 0.0) >= 0.0)
    )
    enriched["robust_forward_score"] = (
        pd.to_numeric(enriched.get("validation_score_delta", 0.0), errors="coerce").fillna(0.0)
        + pd.to_numeric(enriched.get("stress_score_delta", 0.0), errors="coerce").fillna(0.0)
        + pd.to_numeric(
            enriched.get("validation_months_passing_floor_delta", 0.0),
            errors="coerce",
        ).fillna(0.0)
        * 50.0
        + pd.to_numeric(
            enriched.get("stress_months_passing_floor_delta", 0.0),
            errors="coerce",
        ).fillna(0.0)
        * 100.0
        + pd.to_numeric(
            enriched.get("stress_worst_monthly_drawdown_delta_pct", 0.0),
            errors="coerce",
        ).fillna(0.0)
        * 10.0
    ).round(4)
    return enriched


def _baseline_by_split(
    trades: pd.DataFrame,
    *,
    splits: SplitConfig,
    stress_end: str,
    initial_capital: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_name, start, end in _split_specs(splits=splits, stress_end=stress_end):
        rows.append(
            {
                "split": split_name,
                "start": start,
                "end": end,
                **_split_metrics(trades, start=start, end=end, initial_capital=initial_capital),
            }
        )
    return pd.DataFrame(rows)


def _split_metrics(
    trades: pd.DataFrame,
    *,
    start: str,
    end: str,
    initial_capital: float,
) -> dict[str, Any]:
    split = _split_frame(trades, start=start, end=end)
    total_pnl = float(split["pnl_abs"].sum()) if "pnl_abs" in split.columns else 0.0
    wins = split[pd.to_numeric(split["pnl_abs"], errors="coerce").fillna(0.0) > 0.0]
    losses = split[pd.to_numeric(split["pnl_abs"], errors="coerce").fillna(0.0) < 0.0]
    gross_win = float(wins["pnl_abs"].sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses["pnl_abs"].sum())) if not losses.empty else 0.0
    profit_factor = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    report = build_mandate_report(
        split,
        initial_capital=initial_capital,
        start=start,
        end=end,
    )
    summary = report.summary.iloc[0].to_dict()
    monthly = report.monthly
    shortfall = (
        float((15.0 - pd.to_numeric(monthly["raw_monthly_return_pct"], errors="coerce")).clip(lower=0.0).sum())
        if not monthly.empty
        else 0.0
    )
    score = (
        float(summary.get("sum_capped_monthly_return_pct", 0.0))
        - shortfall * 10.0
        - float(summary.get("dd_breach_months", 0)) * 200.0
        - max(float(summary.get("worst_consecutive_losing_months", 0)) - 1.0, 0.0) * 50.0
    )
    return {
        "trade_count": len(split),
        "total_pnl_abs": round(total_pnl, 2),
        "return_pct": round(total_pnl / initial_capital * 100.0, 2),
        "win_rate_pct": round(len(wins) / len(split) * 100.0, 2) if len(split) else 0.0,
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else profit_factor,
        "mandate_verdict": str(summary.get("verdict", "discard")),
        "months_passing_floor": int(summary.get("months_passing_floor", 0)),
        "months_below_floor": int(summary.get("months_below_floor", 0)),
        "worst_monthly_drawdown_pct": float(summary.get("worst_monthly_drawdown_pct", 0.0)),
        "score": round(score, 4),
    }


def _split_frame(frame: pd.DataFrame, *, start: str, end: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    entry = pd.to_datetime(frame["entry_time"], utc=True, errors="coerce")
    return frame[(entry >= start_ts) & (entry < end_ts)].copy()


def _split_specs(
    *,
    splits: SplitConfig,
    stress_end: str,
) -> list[tuple[str, str, str]]:
    return [
        ("train", splits.train_start, splits.validation_start),
        ("validation", splits.validation_start, splits.stress_start),
        ("stress", splits.stress_start, stress_end),
    ]


def _stress_end(trades: pd.DataFrame, splits: SplitConfig) -> str:
    if splits.stress_end is not None:
        return splits.stress_end
    if trades.empty:
        return "2026-01-01"
    latest = pd.to_datetime(trades["entry_time"], utc=True, errors="coerce").max()
    if pd.isna(latest):
        return "2026-01-01"
    return str((latest + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))


def _rule_mask(frame: pd.DataFrame, rule: FilterRule | CompoundFilterRule) -> pd.Series:
    if isinstance(rule, CompoundFilterRule):
        return _rule_mask(frame, rule.left) & _rule_mask(frame, rule.right)
    if rule.feature not in frame.columns:
        return pd.Series(False, index=frame.index)
    series = frame[rule.feature]
    if rule.op in {"<=", ">="}:
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_value = float(rule.value)
        if rule.op == "<=":
            return numeric <= numeric_value
        return numeric >= numeric_value
    values = series.astype(str)
    text_value = str(rule.value)
    if rule.op == "==":
        return values == text_value
    return values != text_value


def _dedupe_rules(rules: list[FilterRule]) -> list[FilterRule]:
    seen: set[tuple[str, RuleOp, str]] = set()
    deduped: list[FilterRule] = []
    for rule in rules:
        key = (rule.feature, rule.op, str(rule.value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)
    return deduped


def _prefix_metrics(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def _markdown_report(
    *,
    baseline: pd.DataFrame,
    top_filters: pd.DataFrame,
    config: FilterSearchConfig,
    stress_end: str,
    feature_count: int,
    rule_count: int,
) -> str:
    lines = [
        "# Trade filter research report",
        "",
        "## Inputs",
        "",
        f"- Trades files: {len(config.trades_paths)}",
        f"- Initial capital: ${config.initial_capital:,.2f}",
        f"- Train: {config.splits.train_start} → {config.splits.validation_start}",
        f"- Validation: {config.splits.validation_start} → {config.splits.stress_start}",
        f"- Stress: {config.splits.stress_start} → {stress_end}",
        f"- Group by: {config.group_by or 'disabled'}",
        f"- Catalog features included: {config.include_catalog_features}",
        f"- Entry-known features considered: {feature_count}",
        f"- Portfolio-state features included: {config.include_portfolio_state_features}",
        f"- Candidate rules tested: {rule_count}",
        "",
        "## Baseline by split",
        "",
        _to_markdown_table(baseline),
        "",
        "## Top filters by robust forward score",
        "",
        _to_markdown_table(top_filters.head(20)),
        "",
        "## Interpretation guardrails",
        "",
        "- Rules are fit only on the train split; validation/stress are forward checks.",
        "- Top filters must improve validation and stress versus baseline to pass the robust-forward guard.",
        "- Portfolio-state features are excluded by default because they can proxy time, capital, and equity-curve state.",
        "- PnL, exit reason, exit price, and holding duration are blocked as leaky features.",
        "- This report deletes trades from an existing artifact; it is not a final portfolio simulation.",
        "- Any promising filter must be implemented in the strategy/router and re-run through `backtester run`.",
        "",
    ]
    return "\n".join(lines)


def _to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    rendered = frame.copy()
    rendered = rendered.fillna("")
    columns = [str(column) for column in rendered.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in rendered.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in rendered.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
