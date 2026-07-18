"""Archived strategy performance matrix utilities."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

from backtester.cli_runner import (
    BacktestArgs,
    StrategyConfig,
    build_backtest_args,
    build_strategy_instance,
    load_strategy_config,
    run_backtest,
)
from backtester.data_contracts import StrategyInput


@dataclass(frozen=True, slots=True)
class MatrixStrategy:
    """Strategy metadata used in matrix outputs."""

    strategy_id: str
    strategy_path: Path
    config: StrategyConfig
    args: BacktestArgs


@dataclass(frozen=True, slots=True)
class MatrixBacktestCliParams:
    """CLI-level backtest defaults applied before strategy JSON overrides."""

    capital: float
    maker_fee: float
    taker_fee: float
    max_allowed_leverage: float
    max_allowed_margin: float


@dataclass(frozen=True, slots=True)
class MatrixStrategyWorkItem:
    """One matrix strategy run unit."""

    index: int
    strategy_id: str
    strategy_path: Path
    config: StrategyConfig
    args: BacktestArgs


@dataclass(frozen=True, slots=True)
class MatrixStrategyResult:
    """Backtest output for one matrix strategy."""

    index: int
    strategy: MatrixStrategy
    trades: pd.DataFrame
    bucket_metrics: pd.DataFrame


def strategy_id_from_path(path: Path) -> str:
    """Return a stable, CSV-friendly strategy id from a JSON path."""

    raw = path.stem.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", raw)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "strategy"


def prepare_matrix_work_items(
    paths: list[Path],
    *,
    cli_params: MatrixBacktestCliParams,
    strategy_progress: bool,
    logger: logging.Logger,
) -> list[MatrixStrategyWorkItem]:
    """Load strategy configs and assign stable matrix ids."""

    work_items: list[MatrixStrategyWorkItem] = []
    used_ids: set[str] = set()
    for index, strategy_path in enumerate(paths):
        cfg = load_strategy_config(str(strategy_path), logger)
        if cfg is None:
            raise ValueError(f"Invalid strategy config: {strategy_path}")
        cfg = matrix_config_with_progress(cfg, enabled=strategy_progress)
        args = build_backtest_args(
            cfg,
            capital=cli_params.capital,
            risk_percent=1.0,
            rrr=2.0,
            trail_activation_rrr=0.0,
            trail_distance_atr=0.0,
            maker_fee=cli_params.maker_fee,
            taker_fee=cli_params.taker_fee,
            ttl=0,
            max_positions=0,
            max_allowed_leverage=cli_params.max_allowed_leverage,
            max_allowed_margin=cli_params.max_allowed_margin,
            risk_base_period="monthly",
            max_daily_profit=None,
            max_daily_loss=None,
            trading_begin=None,
            trading_end=None,
            exit_geometry="sl_rrr",
            tp_move_pct=None,
            structural_sl_mode="cap",
            min_tp_move_pct=0.004,
        )
        strategy_id = unique_strategy_id(strategy_id_from_path(strategy_path), used_ids)
        used_ids.add(strategy_id)
        strategy_instance = build_strategy_instance(cfg.name, cfg.params, logger=logger)
        if strategy_instance is None:
            raise ValueError(f"Could not build strategy: {strategy_path}")
        work_items.append(
            MatrixStrategyWorkItem(
                index=index,
                strategy_id=strategy_id,
                strategy_path=strategy_path,
                config=cfg,
                args=args,
            )
        )
    return work_items


def run_archived_performance_matrix(
    *,
    paths: list[Path],
    data: StrategyInput,
    output: Path,
    bucket: str,
    from_date: str | None,
    to_date: str | None,
    jobs: int,
    cli_params: MatrixBacktestCliParams,
    strategy_progress: bool,
    logger: logging.Logger,
    on_strategy_start: Callable[[str, Path], None] | None = None,
    on_strategy_done: Callable[[str, int], None] | None = None,
) -> None:
    """Run matrix backtests serially or with process-level strategy parallelism."""

    if jobs < 1:
        raise ValueError("jobs must be >= 1")

    output.mkdir(parents=True, exist_ok=True)
    work_items = prepare_matrix_work_items(
        paths,
        cli_params=cli_params,
        strategy_progress=strategy_progress,
        logger=logger,
    )
    if not work_items:
        return

    logger.info("Running %d matrix strategies with jobs=%d", len(work_items), jobs)
    if jobs == 1 or len(work_items) <= 1:
        completed: list[MatrixStrategyResult] = []
        for work in work_items:
            if on_strategy_start is not None:
                on_strategy_start(work.strategy_id, work.strategy_path)
            result = _run_matrix_strategy_worker(
                data=data,
                work=work,
                bucket=bucket,
                start=from_date,
                end=to_date,
            )
            completed.append(result)
            _write_matrix_strategy_output(output=output, result=result, completed=completed)
            if on_strategy_done is not None:
                on_strategy_done(work.strategy_id, len(result.trades))
        return

    completed = []
    max_workers = min(jobs, len(work_items))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _run_matrix_strategy_worker,
                data=data,
                work=work,
                bucket=bucket,
                start=from_date,
                end=to_date,
            ): work
            for work in work_items
        }
        for work in work_items:
            if on_strategy_start is not None:
                on_strategy_start(work.strategy_id, work.strategy_path)
        for future in as_completed(futures):
            work = futures[future]
            result = future.result()
            completed.append(result)
            _write_matrix_strategy_output(output=output, result=result, completed=completed)
            if on_strategy_done is not None:
                on_strategy_done(work.strategy_id, len(result.trades))
            logger.info("Completed matrix strategy %s", work.strategy_id)

    ordered = results_in_strategy_order(completed)
    manifest = build_strategy_manifest([item.strategy for item in ordered])
    bucket_metrics = pd.concat([item.bucket_metrics for item in ordered], ignore_index=True)
    write_matrix_outputs(output=output, manifest=manifest, bucket_metrics=bucket_metrics)


def matrix_config_with_progress(cfg: StrategyConfig, *, enabled: bool) -> StrategyConfig:
    if "progress" not in cfg.params:
        return cfg
    params = dict(cfg.params)
    params["progress"] = enabled
    return StrategyConfig(
        name=cfg.name,
        version=cfg.version,
        params=params,
        backtest_args=cfg.backtest_args,
    )


def unique_strategy_id(base: str, used_ids: set[str]) -> str:
    if base not in used_ids:
        return base
    idx = 2
    while f"{base}_{idx}" in used_ids:
        idx += 1
    return f"{base}_{idx}"


def results_in_strategy_order(results: list[MatrixStrategyResult]) -> list[MatrixStrategyResult]:
    return [item for _, item in sorted((result.index, result) for result in results)]


def build_strategy_manifest(strategies: list[MatrixStrategy]) -> pd.DataFrame:
    """Build a one-row-per-strategy manifest."""

    rows: list[dict[str, Any]] = []
    for item in strategies:
        params = item.config.params
        filters = params.get("filter_names", [])
        if isinstance(filters, list):
            filter_names = "+".join(str(name) for name in filters)
        else:
            filter_names = str(filters)
        rows.append(
            {
                "strategy_id": item.strategy_id,
                "strategy_path": str(item.strategy_path),
                "strategy_name": item.config.name,
                "version": item.config.version,
                "trigger_name": params.get("trigger_name", ""),
                "filter_names": filter_names,
                "risk_percent": item.args.risk_percent,
                "rrr": item.args.rrr,
                "ttl": item.args.ttl,
                "trail_distance_atr": item.args.trail_distance_atr,
                "risk_base_period": item.args.risk_base_period,
            }
        )
    return pd.DataFrame(rows)


def aggregate_strategy_buckets(
    trades: pd.DataFrame,
    *,
    strategy_id: str,
    strategy_path: Path,
    bucket: str,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Aggregate a strategy trade DataFrame into bucket-level metrics."""

    freq = _bucket_freq(bucket)
    periods = _bucket_periods(trades, freq=freq, start=start, end=end)
    if trades.empty:
        return _empty_bucket_rows(
            periods=periods,
            strategy_id=strategy_id,
            strategy_path=strategy_path,
        )

    df = trades.copy()
    if "entry_time" not in df.columns:
        return _empty_bucket_rows(
            periods=periods,
            strategy_id=strategy_id,
            strategy_path=strategy_path,
        )
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["entry_time"])
    df["bucket"] = df["entry_time"].dt.to_period(freq).astype(str)

    rows = []
    for period in periods:
        group = df[df["bucket"] == period]
        rows.append(
            _bucket_row(
                group,
                bucket=period,
                strategy_id=strategy_id,
                strategy_path=strategy_path,
            )
        )
    return pd.DataFrame(rows)


def pivot_metric(bucket_metrics: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Return a wide bucket x strategy pivot for one metric."""

    if bucket_metrics.empty:
        return pd.DataFrame()
    pivot = bucket_metrics.pivot(index="bucket", columns="strategy_id", values=metric)
    return pivot.reset_index()


def write_matrix_outputs(
    *,
    output: Path,
    manifest: pd.DataFrame,
    bucket_metrics: pd.DataFrame,
) -> None:
    """Write matrix CSVs and summary."""

    output.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output / "strategy_manifest.csv", index=False)
    bucket_metrics.to_csv(output / "bucket_metrics.csv", index=False)
    pivot_metric(bucket_metrics, "return_pct").to_csv(output / "matrix_return_pct.csv", index=False)
    pivot_metric(bucket_metrics, "trade_count").to_csv(
        output / "matrix_trade_count.csv", index=False
    )
    _write_summary(output / "summary.md", manifest=manifest, bucket_metrics=bucket_metrics)


def write_strategy_trades(
    *,
    output: Path,
    strategy_id: str,
    trades: pd.DataFrame,
) -> Path:
    """Write raw trades for one matrix strategy."""

    trades_dir = output / "strategy_trades"
    trades_dir.mkdir(parents=True, exist_ok=True)
    path = trades_dir / f"{strategy_id}.csv"
    trades.to_csv(path, index=False)
    return path


def _bucket_freq(bucket: str) -> str:
    normalized = bucket.lower()
    if normalized == "day":
        return "D"
    if normalized == "week":
        return "W"
    if normalized == "month":
        return "M"
    raise ValueError(f"Unsupported bucket {bucket!r}; expected day, week, or month")


def _bucket_periods(
    trades: pd.DataFrame, *, freq: str, start: str | None, end: str | None
) -> list[str]:
    if start is not None and end is not None:
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        return cast(
            list[str],
            pd.period_range(start=start_ts, end=end_ts, freq=freq).astype(str).tolist(),
        )

    if trades.empty or "entry_time" not in trades.columns:
        return []
    entry = pd.to_datetime(trades["entry_time"], utc=True, errors="coerce").dropna()
    if entry.empty:
        return []
    return cast(
        list[str],
        pd.period_range(start=entry.min(), end=entry.max(), freq=freq).astype(str).tolist(),
    )


def _empty_bucket_rows(
    *, periods: list[str], strategy_id: str, strategy_path: Path
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            _bucket_row(
                pd.DataFrame(),
                bucket=period,
                strategy_id=strategy_id,
                strategy_path=strategy_path,
            )
            for period in periods
        ]
    )


def _bucket_row(
    group: pd.DataFrame, *, bucket: str, strategy_id: str, strategy_path: Path
) -> dict[str, Any]:
    pnl = _numeric(group, "pnl_abs")
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_win = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    start_capital = _bucket_start_capital(group)
    capital_after = _numeric(group, "capital_after")
    is_long = _bool_series(group, "is_long")
    exit_counts = _exit_counts(group)

    return {
        "bucket": bucket,
        "strategy_id": strategy_id,
        "strategy_path": str(strategy_path),
        "return_pct": (float(pnl.sum()) / start_capital * 100.0) if start_capital > 0 else 0.0,
        "pnl_abs": float(pnl.sum()),
        "trade_count": len(group),
        "win_rate": (len(wins) / len(pnl) * 100.0) if len(pnl) else 0.0,
        "profit_factor": gross_win / gross_loss
        if gross_loss > 0
        else (gross_win if gross_win else 0.0),
        "avg_trade": float(pnl.mean()) if len(pnl) else 0.0,
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "max_drawdown_pct": _max_drawdown_pct(capital_after),
        "long_trades": int(is_long.sum()) if len(is_long) else 0,
        "short_trades": int((~is_long).sum()) if len(is_long) else 0,
        "long_pnl_abs": float(pnl[is_long].sum()) if len(is_long) else 0.0,
        "short_pnl_abs": float(pnl[~is_long].sum()) if len(is_long) else 0.0,
        "avg_holding_bars": _mean_numeric(group, "holding_bars"),
        "exposure_bars": float(_numeric(group, "holding_bars").sum()),
        **exit_counts,
    }


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def _mean_numeric(df: pd.DataFrame, column: str) -> float:
    values = _numeric(df, column)
    return float(values.mean()) if len(values) else 0.0


def _bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df.columns:
        return pd.Series(dtype=bool)
    return df[column].fillna(False).astype(bool)


def _bucket_start_capital(group: pd.DataFrame) -> float:
    if group.empty:
        return 0.0
    capital_before = _numeric(group, "capital_before")
    if len(capital_before) and float(capital_before.iloc[0]) > 0:
        return float(capital_before.iloc[0])
    risk_base = _numeric(group, "risk_base_capital")
    if len(risk_base) and float(risk_base.iloc[0]) > 0:
        return float(risk_base.iloc[0])
    return 0.0


def _max_drawdown_pct(capital_after: pd.Series) -> float:
    if capital_after.empty:
        return 0.0
    running_peak = capital_after.cummax()
    drawdown = (capital_after - running_peak) / running_peak.replace(0.0, pd.NA) * 100.0
    return float(drawdown.min()) if not drawdown.empty else 0.0


def _exit_counts(group: pd.DataFrame) -> dict[str, int]:
    wanted = {
        "stop_loss": "exit_stop_loss",
        "take_profit": "exit_take_profit",
        "trailing_stop": "exit_trailing_stop",
        "ttl_expired": "exit_ttl_expired",
        "open": "exit_open",
    }
    counts = dict.fromkeys([*wanted.values(), "exit_other"], 0)
    if group.empty or "exit_reason" not in group.columns:
        return counts
    raw = group["exit_reason"].fillna("").astype(str)
    value_counts = raw.value_counts().to_dict()
    for reason, count in value_counts.items():
        column = wanted.get(reason, "exit_other")
        counts[column] += int(count)
    return counts


def _write_summary(path: Path, *, manifest: pd.DataFrame, bucket_metrics: pd.DataFrame) -> None:
    strategy_count = len(manifest)
    bucket_count = bucket_metrics["bucket"].nunique() if not bucket_metrics.empty else 0
    total_trades = int(bucket_metrics["trade_count"].sum()) if not bucket_metrics.empty else 0
    lines = [
        "# Archived Strategy Performance Matrix",
        "",
        f"Strategies: **{strategy_count}**",
        f"Buckets: **{bucket_count}**",
        f"Total trades: **{total_trades}**",
        "",
        "Files:",
        "",
        "- `strategy_manifest.csv`",
        "- `bucket_metrics.csv`",
        "- `matrix_return_pct.csv`",
        "- `matrix_trade_count.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_matrix_strategy_worker(
    *,
    data: StrategyInput,
    work: MatrixStrategyWorkItem,
    bucket: str,
    start: str | None,
    end: str | None,
) -> MatrixStrategyResult:
    worker_logger = logging.getLogger("backtester")
    strategy_instance = build_strategy_instance(
        work.config.name,
        work.config.params,
        logger=worker_logger,
    )
    if strategy_instance is None:
        raise ValueError(f"Could not build strategy: {work.strategy_path}")

    results = run_backtest(df=data, strategy=strategy_instance, args=work.args)
    trades = results.trades if results.trades is not None else pd.DataFrame()
    bucket_metrics = aggregate_strategy_buckets(
        trades,
        strategy_id=work.strategy_id,
        strategy_path=work.strategy_path,
        bucket=bucket,
        start=start,
        end=end,
    )
    strategy = MatrixStrategy(
        strategy_id=work.strategy_id,
        strategy_path=work.strategy_path,
        config=work.config,
        args=work.args,
    )
    return MatrixStrategyResult(
        index=work.index,
        strategy=strategy,
        trades=trades,
        bucket_metrics=bucket_metrics,
    )


def _write_matrix_strategy_output(
    *,
    output: Path,
    result: MatrixStrategyResult,
    completed: list[MatrixStrategyResult],
) -> None:
    write_strategy_trades(
        output=output,
        strategy_id=result.strategy.strategy_id,
        trades=result.trades,
    )
    ordered = results_in_strategy_order(completed)
    manifest = build_strategy_manifest([item.strategy for item in ordered])
    bucket_metrics = pd.concat([item.bucket_metrics for item in ordered], ignore_index=True)
    write_matrix_outputs(output=output, manifest=manifest, bucket_metrics=bucket_metrics)
