from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.cli_runner import (
    BacktestArgs,
    StrategyConfig,
    build_cli_data_loader,
    build_strategy_instance,
    export_and_optional_analysis,
    load_ohlcv_via_loader,
    run_backtest,
)
from backtester.data_contracts import StrategyInput
from backtester.tester import Backtester

DEFAULT_WINDOWS = (
    "sol_2025_01:SOL-USDT-SWAP:2025-01-01:2025-02-01",
    "sol_2025_02:SOL-USDT-SWAP:2025-02-01:2025-03-01",
    "sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01",
    "ton_2025_01:TON-USDT-SWAP:2025-01-01:2025-02-01",
    "ton_2025_02:TON-USDT-SWAP:2025-02-01:2025-03-01",
)


@dataclass(frozen=True, slots=True)
class WindowSpec:
    label: str
    symbol: str
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class FixedCandidateParams:
    capital: float
    risk_percent: float
    rrr: float
    ttl: int
    maker_fee: float
    taker_fee: float
    max_positions: int
    max_allowed_leverage: float
    max_allowed_margin: float
    risk_base_period: str
    is_isolated_futures: bool

    def to_backtest_args(self) -> BacktestArgs:
        return BacktestArgs(
            capital=self.capital,
            risk_percent=self.risk_percent,
            rrr=self.rrr,
            maker_fee=self.maker_fee,
            taker_fee=self.taker_fee,
            ttl=self.ttl,
            max_positions=self.max_positions,
            max_allowed_leverage=self.max_allowed_leverage,
            is_isolated_futures=self.is_isolated_futures,
            max_allowed_margin=self.max_allowed_margin,
            risk_base_period=self.risk_base_period,
            max_daily_profit=None,
            max_daily_loss=None,
            trading_begin=None,
            trading_end=None,
        )


def parse_window_spec(raw: str) -> WindowSpec:
    parts = [part.strip() for part in raw.split(":")]
    if len(parts) != 4 or any(part == "" for part in parts):
        raise ValueError("Window must use 'label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD' format")
    return WindowSpec(label=parts[0], symbol=parts[1], start=parts[2], end=parts[3])


def parse_window_specs(raw_windows: tuple[str, ...]) -> list[WindowSpec]:
    windows = raw_windows or DEFAULT_WINDOWS
    return [parse_window_spec(raw) for raw in windows]


def parse_float_values(raw: str) -> list[float]:
    values = [value.strip() for value in raw.split(",")]
    if not values or any(value == "" for value in values):
        raise ValueError("Expected comma-separated float values")
    try:
        return [float(value) for value in values]
    except ValueError as exc:
        raise ValueError("Expected comma-separated float values") from exc


def parse_int_values(raw: str) -> list[int]:
    values = [value.strip() for value in raw.split(",")]
    if not values or any(value == "" for value in values):
        raise ValueError("Expected comma-separated integer values")
    try:
        return [int(value) for value in values]
    except ValueError as exc:
        raise ValueError("Expected comma-separated integer values") from exc


def summarize_fixed_candidate_run(
    *,
    window: WindowSpec,
    params: FixedCandidateParams,
    metrics: dict[str, Any],
    signals: pd.DataFrame,
    trades: pd.DataFrame,
    run_dir: Path,
) -> dict[str, Any]:
    long_pnl = _side_pnl(trades, is_long=True)
    short_pnl = _side_pnl(trades, is_long=False)
    exit_counts = _count_column(trades, "exit_reason")
    signal_counts = _count_column(signals, "signal")
    setup_direction_counts = _count_column(signals, "setup_direction")

    return {
        "label": window.label,
        "symbol": window.symbol,
        "from": window.start,
        "to": window.end,
        "rrr": params.rrr,
        "ttl": params.ttl,
        "risk_percent": params.risk_percent,
        "total_return_pct": metrics.get("total_return_pct", 0.0),
        "profit_factor": metrics.get("profit_factor", 0.0),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
        "total_trades": metrics.get("total_trades", 0),
        "long_trades": _side_count(trades, is_long=True),
        "short_trades": _side_count(trades, is_long=False),
        "long_pnl": round(long_pnl, 2),
        "short_pnl": round(short_pnl, 2),
        "signal_long": int(signal_counts.get(1, 0)),
        "signal_short": int(signal_counts.get(-1, 0)),
        "signal_neutral": int(signal_counts.get(0, 0)),
        "setup_buy": int(setup_direction_counts.get("BUY", 0)),
        "setup_sell": int(setup_direction_counts.get("SELL", 0)),
        "setup_neutral": int(setup_direction_counts.get("HOLD", 0)),
        "exit_take_profit": int(exit_counts.get("take_profit", 0)),
        "exit_stop_loss": int(exit_counts.get("stop_loss", 0)),
        "exit_ttl_expired": int(exit_counts.get("ttl_expired", 0)),
        "run_dir": str(run_dir),
    }


def run_fixed_candidate_comparison(
    *,
    windows: list[WindowSpec],
    cfg: StrategyConfig,
    params: FixedCandidateParams,
    data_dir: str,
    primary_timeframe: str,
    output_folder: str,
    jobs: int,
    logger: logging.Logger,
) -> pd.DataFrame:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    _validate_unique_labels(windows)

    output_path = Path(output_folder)
    runs_path = output_path / "runs"
    output_path.mkdir(parents=True, exist_ok=True)
    runs_path.mkdir(parents=True, exist_ok=True)

    logger.info("Running %d fixed-candidate windows with jobs=%d", len(windows), jobs)
    if jobs == 1 or len(windows) <= 1:
        indexed_rows = [
            _run_fixed_candidate_window(
                index=index,
                window=window,
                cfg=cfg,
                params=params,
                data_dir=data_dir,
                primary_timeframe=primary_timeframe,
                run_dir=runs_path / window.label,
            )
            for index, window in enumerate(windows)
        ]
    else:
        indexed_rows = []
        max_workers = min(jobs, len(windows))
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _run_fixed_candidate_window,
                    index=index,
                    window=window,
                    cfg=cfg,
                    params=params,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    run_dir=runs_path / window.label,
                )
                for index, window in enumerate(windows)
            ]
            for future in as_completed(futures):
                index, row = future.result()
                indexed_rows.append((index, row))
                logger.info("Completed fixed-candidate window %s", row["label"])

    rows = _rows_in_window_order(indexed_rows)
    summary = pd.DataFrame(rows)
    summary_path = output_path / "windows.csv"
    summary.to_csv(summary_path, index=False)
    markdown_path = output_path / "windows.md"
    markdown_path.write_text(_to_markdown_table(summary) + "\n")
    logger.info("Fixed-candidate summary saved to: %s", summary_path)
    logger.info("Fixed-candidate markdown saved to: %s", markdown_path)
    return summary


def run_execution_grid_comparison(
    *,
    windows: list[WindowSpec],
    cfg: StrategyConfig,
    base_params: FixedCandidateParams,
    rrr_values: list[float],
    ttl_values: list[int],
    data_dir: str,
    primary_timeframe: str,
    output_folder: str,
    jobs: int,
    logger: logging.Logger,
) -> pd.DataFrame:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if not rrr_values:
        raise ValueError("rrr_values must not be empty")
    if not ttl_values:
        raise ValueError("ttl_values must not be empty")
    _validate_unique_labels(windows)

    output_path = Path(output_folder)
    runs_path = output_path / "runs"
    output_path.mkdir(parents=True, exist_ok=True)
    runs_path.mkdir(parents=True, exist_ok=True)

    tasks = [
        (
            index,
            window,
            _params_with_execution_values(base_params, rrr=rrr, ttl=ttl),
        )
        for index, (window, rrr, ttl) in enumerate(
            (window, rrr, ttl)
            for window in windows
            for rrr in rrr_values
            for ttl in ttl_values
        )
    ]
    tasks_by_window: dict[str, list[tuple[int, WindowSpec, FixedCandidateParams]]] = {}
    for task in tasks:
        _, window, _ = task
        tasks_by_window.setdefault(window.label, []).append(task)

    logger.info(
        "Running %d execution-grid candidates across %d windows with jobs=%d",
        len(tasks),
        len(tasks_by_window),
        jobs,
    )
    if jobs == 1 or len(tasks_by_window) <= 1:
        indexed_rows = []
        for window_tasks in tasks_by_window.values():
            indexed_rows.extend(
                _run_execution_grid_window_precomputed(
                    tasks=window_tasks,
                    cfg=cfg,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    window_run_dir=runs_path / window_tasks[0][1].label,
                )
            )
    else:
        indexed_rows = []
        max_workers = min(jobs, len(tasks_by_window))
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _run_execution_grid_window_precomputed,
                    tasks=window_tasks,
                    cfg=cfg,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    window_run_dir=runs_path / window_tasks[0][1].label,
                )
                for window_tasks in tasks_by_window.values()
            ]
            for future in as_completed(futures):
                window_rows = future.result()
                indexed_rows.extend(window_rows)
                if window_rows:
                    logger.info(
                        "Completed execution-grid window %s (%d candidates)",
                        window_rows[0][1]["label"],
                        len(window_rows),
                    )

    rows = _rows_in_window_order(indexed_rows)
    summary = pd.DataFrame(rows)
    summary_path = output_path / "grid.csv"
    summary.to_csv(summary_path, index=False)
    markdown_path = output_path / "grid.md"
    markdown_path.write_text(_to_markdown_table(summary) + "\n")
    logger.info("Execution-grid summary saved to: %s", summary_path)
    logger.info("Execution-grid markdown saved to: %s", markdown_path)
    return summary


def _run_fixed_candidate_window(
    *,
    index: int,
    window: WindowSpec,
    cfg: StrategyConfig,
    params: FixedCandidateParams,
    data_dir: str,
    primary_timeframe: str,
    run_dir: Path,
) -> tuple[int, dict[str, Any]]:
    worker_logger = logging.getLogger("backtester")
    worker_logger.info(
        "Running fixed candidate %s %s -> %s",
        window.label,
        window.start,
        window.end,
    )
    df = _load_window_data(
        window=window,
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        logger=worker_logger,
    )
    strategy = build_strategy_instance(cfg.name, cfg.params, logger=worker_logger)
    if strategy is None:
        raise ValueError(f"Unknown strategy: {cfg.name}")

    results = run_backtest(
        df=df,
        strategy=strategy,
        args=params.to_backtest_args(),
    )
    export_and_optional_analysis(
        results=results,
        ohlcv_df=df,
        output_folder=str(run_dir),
        analyze_conditions=False,
        top_predictors=10,
        create_visualizations=False,
        create_dashboard=False,
        logger=worker_logger,
    )
    return (
        index,
        summarize_fixed_candidate_run(
            window=window,
            params=params,
            metrics=results.metrics,
            signals=results.signals,
            trades=results.trades,
            run_dir=run_dir,
        ),
    )


def _run_execution_grid_window_precomputed(
    *,
    tasks: list[tuple[int, WindowSpec, FixedCandidateParams]],
    cfg: StrategyConfig,
    data_dir: str,
    primary_timeframe: str,
    window_run_dir: Path,
) -> list[tuple[int, dict[str, Any]]]:
    if not tasks:
        return []

    _, first_window, _ = tasks[0]
    if any(window != first_window for _, window, _ in tasks):
        raise ValueError("precomputed execution grid tasks must share one window")

    worker_logger = logging.getLogger("backtester")
    worker_logger.info(
        "Running execution grid %s %s -> %s with one signal build",
        first_window.label,
        first_window.start,
        first_window.end,
    )
    df = _load_window_data(
        window=first_window,
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        logger=worker_logger,
    )
    strategy = build_strategy_instance(cfg.name, cfg.params, logger=worker_logger)
    if strategy is None:
        raise ValueError(f"Unknown strategy: {cfg.name}")

    signals = strategy.generate(df)
    indexed_rows: list[tuple[int, dict[str, Any]]] = []
    for index, window, params in tasks:
        results = _run_backtest_with_precomputed_signals(
            df=df,
            signals=signals,
            args=params.to_backtest_args(),
        )
        run_dir = window_run_dir / _candidate_run_label(params)
        export_and_optional_analysis(
            results=results,
            ohlcv_df=df,
            output_folder=str(run_dir),
            analyze_conditions=False,
            top_predictors=10,
            create_visualizations=False,
            create_dashboard=False,
            logger=worker_logger,
        )
        indexed_rows.append(
            (
                index,
                summarize_fixed_candidate_run(
                    window=window,
                    params=params,
                    metrics=results.metrics,
                    signals=results.signals,
                    trades=results.trades,
                    run_dir=run_dir,
                ),
            )
        )
    return indexed_rows


def _run_backtest_with_precomputed_signals(
    *,
    df: StrategyInput,
    signals: pd.DataFrame,
    args: BacktestArgs,
):
    return Backtester(df, lambda _df: signals.copy()).run(
        initial_capital=args.capital,
        taker_fee=args.taker_fee,
        maker_fee=args.maker_fee,
        risk_percent=args.risk_percent,
        rrr=args.rrr,
        max_positions=args.max_positions,
        position_ttl_bars=args.ttl,
        max_allowed_leverage=args.max_allowed_leverage,
        is_isolated_futures=args.is_isolated_futures,
        max_allowed_margin=args.max_allowed_margin,
        risk_base_period=args.risk_base_period,
        max_daily_profit=args.max_daily_profit,
        max_daily_loss=args.max_daily_loss,
        trading_begin=args.trading_begin,
        trading_end=args.trading_end,
    )


def _load_window_data(
    *,
    window: WindowSpec,
    data_dir: str,
    primary_timeframe: str,
    logger: logging.Logger,
) -> StrategyInput:
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir=data_dir,
        symbol=window.symbol,
        primary_timeframe=primary_timeframe,
        start=window.start,
        end=window.end,
    )
    df = load_ohlcv_via_loader(loader, logger=logger)
    if df is None:
        raise ValueError(f"Failed to load data for {window.label}")
    return df


def _rows_in_window_order(
    indexed_rows: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [row for _, row in sorted(indexed_rows, key=lambda item: item[0])]


def _params_with_execution_values(
    params: FixedCandidateParams,
    *,
    rrr: float,
    ttl: int,
) -> FixedCandidateParams:
    return FixedCandidateParams(
        capital=params.capital,
        risk_percent=params.risk_percent,
        rrr=rrr,
        ttl=ttl,
        maker_fee=params.maker_fee,
        taker_fee=params.taker_fee,
        max_positions=params.max_positions,
        max_allowed_leverage=params.max_allowed_leverage,
        max_allowed_margin=params.max_allowed_margin,
        risk_base_period=params.risk_base_period,
        is_isolated_futures=params.is_isolated_futures,
    )


def _candidate_run_label(params: FixedCandidateParams) -> str:
    return f"rrr_{_slug_float(params.rrr)}__ttl_{params.ttl}"


def _slug_float(value: float) -> str:
    return f"{value:g}".replace("-", "m").replace(".", "_")


def _validate_unique_labels(windows: list[WindowSpec]) -> None:
    labels = [window.label for window in windows]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        joined = ", ".join(duplicates)
        raise ValueError(
            f"Duplicate window labels would overwrite run outputs: {joined}"
        )


def _count_column(df: pd.DataFrame, column: str) -> dict[Any, int]:
    if df.empty or column not in df.columns:
        return {}
    return {
        key: int(value)
        for key, value in df[column].value_counts(dropna=False).sort_index().items()
    }


def _side_count(trades: pd.DataFrame, *, is_long: bool) -> int:
    if trades.empty or "is_long" not in trades.columns:
        return 0
    return int((trades["is_long"] == is_long).sum())


def _side_pnl(trades: pd.DataFrame, *, is_long: bool) -> float:
    if trades.empty or not {"is_long", "pnl_abs"}.issubset(trades.columns):
        return 0.0
    pnl = pd.to_numeric(
        trades.loc[trades["is_long"] == is_long, "pnl_abs"],
        errors="coerce",
    )
    return float(pnl.sum()) if not pnl.empty else 0.0


def _to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "| empty |\n|---|"
    columns = [str(column) for column in df.columns]
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
    return "\n".join(rows)
