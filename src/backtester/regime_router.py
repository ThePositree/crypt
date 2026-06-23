"""Offline regime-router evaluation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

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


@dataclass(frozen=True, slots=True)
class RouterConfig:
    """Evaluation settings for rolling-label router reports."""

    validation_start: str
    min_available_strategies: int = 3
    lookback_days: int = 365
    top1_weight: float = 0.6
    knn_k: int = 7
    non_overlap_days: int = 30


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
    eligible = prepared[
        (prepared["asof"] >= validation_start)
        & (prepared["available_strategy_count"] >= config.min_available_strategies)
    ].copy()
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
        & (df["asof"] >= start)
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
        "hit_best": bool(normalized and max(normalized, key=normalized.get) == row["best_strategy"]),
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


def _select_non_overlap_rows(group: pd.DataFrame, *, every_days: int) -> pd.DataFrame:
    sorted_group = group.sort_values("asof").copy()
    selected = []
    next_asof: pd.Timestamp | None = None
    for _, row in sorted_group.iterrows():
        asof = pd.Timestamp(row["asof"])
        if next_asof is None or asof >= next_asof:
            selected.append(row)
            next_asof = asof + pd.Timedelta(days=every_days)
    return pd.DataFrame(selected)


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
