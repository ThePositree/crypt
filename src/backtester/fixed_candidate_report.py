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
DEFAULT_SIGNAL_QUALITY_WINDOWS = (
    "sol_2025_01:SOL-USDT-SWAP:2025-01-01:2025-02-01",
    "sol_2025_02:SOL-USDT-SWAP:2025-02-01:2025-03-01",
    "sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01",
    "ton_2025_01:TON-USDT-SWAP:2025-01-01:2025-02-01",
    "ton_2025_02:TON-USDT-SWAP:2025-02-01:2025-03-01",
    "ton_2025_03:TON-USDT-SWAP:2025-03-01:2025-04-01",
    "ton_2025_04:TON-USDT-SWAP:2025-04-01:2025-05-01",
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


def parse_signal_quality_window_specs(raw_windows: tuple[str, ...]) -> list[WindowSpec]:
    windows = raw_windows or DEFAULT_SIGNAL_QUALITY_WINDOWS
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
    margin_summary = _margin_summary(trades, initial_capital=params.capital)

    row = {
        "label": window.label,
        "symbol": window.symbol,
        "from": window.start,
        "to": window.end,
        "rrr": params.rrr,
        "ttl": params.ttl,
        "max_positions": params.max_positions,
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
    row.update(margin_summary)
    return row


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
    max_positions_values: list[int],
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
    if not max_positions_values:
        raise ValueError("max_positions_values must not be empty")
    _validate_unique_labels(windows)

    output_path = Path(output_folder)
    runs_path = output_path / "runs"
    output_path.mkdir(parents=True, exist_ok=True)
    runs_path.mkdir(parents=True, exist_ok=True)

    tasks = [
        (
            index,
            window,
            _params_with_execution_values(
                base_params,
                rrr=rrr,
                ttl=ttl,
                max_positions=max_positions,
            ),
        )
        for index, (window, rrr, ttl, max_positions) in enumerate(
            (window, rrr, ttl, max_positions)
            for window in windows
            for rrr in rrr_values
            for ttl in ttl_values
            for max_positions in max_positions_values
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
    error_rows: list[dict[str, Any]] = []
    if jobs == 1 or len(tasks_by_window) <= 1:
        indexed_rows = []
        for window_tasks in tasks_by_window.values():
            try:
                indexed_rows.extend(
                    _run_execution_grid_window_precomputed(
                        tasks=window_tasks,
                        cfg=cfg,
                        data_dir=data_dir,
                        primary_timeframe=primary_timeframe,
                        window_run_dir=runs_path / window_tasks[0][1].label,
                    )
                )
            except Exception as exc:
                error_row = _execution_grid_error_row(window_tasks[0][1], exc)
                error_rows.append(error_row)
                logger.warning(
                    "Execution-grid window %s failed: %s",
                    error_row["label"],
                    error_row["error"],
                )
    else:
        indexed_rows = []
        max_workers = min(jobs, len(tasks_by_window))
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_execution_grid_window_precomputed,
                    tasks=window_tasks,
                    cfg=cfg,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    window_run_dir=runs_path / window_tasks[0][1].label,
                ): window_tasks[0][1]
                for window_tasks in tasks_by_window.values()
            }
            for future in as_completed(futures):
                window = futures[future]
                try:
                    window_rows = future.result()
                except Exception as exc:
                    error_row = _execution_grid_error_row(window, exc)
                    error_rows.append(error_row)
                    logger.warning(
                        "Execution-grid window %s failed: %s",
                        error_row["label"],
                        error_row["error"],
                    )
                    continue
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
    if error_rows:
        errors = pd.DataFrame(error_rows)
        errors_path = output_path / "grid_errors.csv"
        errors.to_csv(errors_path, index=False)
        errors_markdown_path = output_path / "grid_errors.md"
        errors_markdown_path.write_text(_to_markdown_table(errors) + "\n")
        logger.warning(
            "Execution-grid completed with %d failed window(s); errors saved to: %s",
            len(error_rows),
            errors_path,
        )
    logger.info("Execution-grid summary saved to: %s", summary_path)
    logger.info("Execution-grid markdown saved to: %s", markdown_path)
    return summary


def run_signal_quality_diagnostics(
    *,
    windows: list[WindowSpec],
    cfg: StrategyConfig,
    params: FixedCandidateParams,
    data_dir: str,
    primary_timeframe: str,
    output_folder: str,
    jobs: int,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    _validate_unique_labels(windows)

    output_path = Path(output_folder)
    runs_path = output_path / "runs"
    output_path.mkdir(parents=True, exist_ok=True)
    runs_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Running signal-quality diagnostics for %d windows with jobs=%d",
        len(windows),
        jobs,
    )
    signal_rows: list[tuple[int, dict[str, Any]]] = []
    group_frames: list[pd.DataFrame] = []
    error_rows: list[dict[str, Any]] = []

    if jobs == 1 or len(windows) <= 1:
        for index, window in enumerate(windows):
            try:
                signal_row, groups = _run_signal_quality_window(
                    index=index,
                    window=window,
                    cfg=cfg,
                    params=params,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    run_dir=runs_path / window.label,
                )
            except Exception as exc:
                error_row = _execution_grid_error_row(window, exc)
                error_rows.append(error_row)
                logger.warning(
                    "Signal-quality window %s failed: %s",
                    error_row["label"],
                    error_row["error"],
                )
                continue
            signal_rows.append((index, signal_row))
            group_frames.append(groups)
    else:
        max_workers = min(jobs, len(windows))
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_signal_quality_window,
                    index=index,
                    window=window,
                    cfg=cfg,
                    params=params,
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    run_dir=runs_path / window.label,
                ): window
                for index, window in enumerate(windows)
            }
            for future in as_completed(futures):
                window = futures[future]
                try:
                    signal_row, groups = future.result()
                except Exception as exc:
                    error_row = _execution_grid_error_row(window, exc)
                    error_rows.append(error_row)
                    logger.warning(
                        "Signal-quality window %s failed: %s",
                        error_row["label"],
                        error_row["error"],
                    )
                    continue
                signal_rows.append((windows.index(window), signal_row))
                group_frames.append(groups)
                logger.info("Completed signal-quality window %s", window.label)

    signals = pd.DataFrame(_rows_in_window_order(signal_rows))
    signals_path = output_path / "signals.csv"
    signals.to_csv(signals_path, index=False)
    signals_markdown_path = output_path / "signals.md"
    signals_markdown_path.write_text(_to_markdown_table(signals) + "\n")

    groups = (
        pd.concat(group_frames, ignore_index=True)
        if group_frames
        else pd.DataFrame(columns=_signal_quality_group_columns())
    )
    groups_path = output_path / "groups.csv"
    groups.to_csv(groups_path, index=False)
    groups_markdown_path = output_path / "groups.md"
    groups_markdown_path.write_text(_to_markdown_table(groups) + "\n")

    if error_rows:
        errors = pd.DataFrame(error_rows)
        errors_path = output_path / "errors.csv"
        errors.to_csv(errors_path, index=False)
        errors_markdown_path = output_path / "errors.md"
        errors_markdown_path.write_text(_to_markdown_table(errors) + "\n")
        logger.warning(
            "Signal-quality diagnostics completed with %d failed window(s); errors saved to: %s",
            len(error_rows),
            errors_path,
        )

    logger.info("Signal-quality window summary saved to: %s", signals_path)
    logger.info("Signal-quality group summary saved to: %s", groups_path)
    return signals, groups


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


def _run_signal_quality_window(
    *,
    index: int,
    window: WindowSpec,
    cfg: StrategyConfig,
    params: FixedCandidateParams,
    data_dir: str,
    primary_timeframe: str,
    run_dir: Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    worker_logger = logging.getLogger("backtester")
    worker_logger.info(
        "Running signal-quality diagnostics %s %s -> %s",
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

    signals = strategy.generate(df)
    results = _run_backtest_with_precomputed_signals(
        df=df,
        signals=signals,
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
        summarize_signal_quality_window(
            index=index,
            window=window,
            params=params,
            metrics=results.metrics,
            signals=results.signals,
            trades=results.trades,
            run_dir=run_dir,
        ),
        summarize_signal_quality_groups(
            window=window,
            params=params,
            trades=results.trades,
            run_dir=run_dir,
        ),
    )


def summarize_signal_quality_window(
    *,
    index: int,
    window: WindowSpec,
    params: FixedCandidateParams,
    metrics: dict[str, Any],
    signals: pd.DataFrame,
    trades: pd.DataFrame,
    run_dir: Path,
) -> dict[str, Any]:
    signal_counts = _count_column(signals, "signal")
    setup_direction_counts = _count_column(signals, "setup_direction")
    context_bias_counts = _count_column(signals, "context_bias")
    trigger_type_counts = _count_column(signals, "trigger_type")
    anchor_counts = _count_column(signals, "sl_anchor_type")
    sl_source_counts = _count_column(signals, "sl_source_tf")
    filter_counts = _count_column(signals, "signal_filter_reason")
    enriched_trades = _enrich_signal_quality_trades(trades)
    margin_summary = _margin_summary(trades, initial_capital=params.capital)
    stale_trades = (
        int(enriched_trades["stale_anchor"].sum())
        if "stale_anchor" in enriched_trades.columns
        else 0
    )
    reversal_trades = (
        int(enriched_trades["reversal_marker"].sum())
        if "reversal_marker" in enriched_trades.columns
        else 0
    )
    confidence = pd.to_numeric(_column_series(signals, "confidence"), errors="coerce")
    confidence = confidence.dropna()

    row: dict[str, Any] = {
        "window_index": index,
        "label": window.label,
        "symbol": window.symbol,
        "from": window.start,
        "to": window.end,
        "rrr": params.rrr,
        "ttl": params.ttl,
        "max_positions": params.max_positions,
        "risk_percent": params.risk_percent,
        "total_return_pct": metrics.get("total_return_pct", 0.0),
        "profit_factor": metrics.get("profit_factor", 0.0),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
        "total_trades": metrics.get("total_trades", 0),
        "long_trades": _side_count(trades, is_long=True),
        "short_trades": _side_count(trades, is_long=False),
        "long_pnl": round(_side_pnl(trades, is_long=True), 2),
        "short_pnl": round(_side_pnl(trades, is_long=False), 2),
        "signal_long": int(signal_counts.get(1, 0)),
        "signal_short": int(signal_counts.get(-1, 0)),
        "signal_neutral": int(signal_counts.get(0, 0)),
        "setup_buy": int(setup_direction_counts.get("BUY", 0)),
        "setup_sell": int(setup_direction_counts.get("SELL", 0)),
        "setup_neutral": int(setup_direction_counts.get("HOLD", 0)),
        "context_bullish": int(context_bias_counts.get("bullish", 0)),
        "context_bearish": int(context_bias_counts.get("bearish", 0)),
        "context_neutral": int(context_bias_counts.get("neutral", 0)),
        "stale_anchor_trades": stale_trades,
        "reversal_marker_trades": reversal_trades,
        "run_dir": str(run_dir),
    }
    row.update(margin_summary)
    for quantile in (0.5, 0.75, 0.9, 0.95):
        row[f"confidence_p{int(quantile * 100)}"] = (
            float(confidence.quantile(quantile)) if not confidence.empty else 0.0
        )
    row.update(_prefixed_counts(trigger_type_counts, "trigger"))
    row.update(_prefixed_counts(anchor_counts, "anchor"))
    row.update(_prefixed_counts(sl_source_counts, "sl_source"))
    row.update(_prefixed_counts(filter_counts, "filter"))
    return row


def summarize_signal_quality_groups(
    *,
    window: WindowSpec,
    params: FixedCandidateParams,
    trades: pd.DataFrame,
    run_dir: Path,
) -> pd.DataFrame:
    enriched = _enrich_signal_quality_trades(trades)
    if enriched.empty:
        return pd.DataFrame(columns=_signal_quality_group_columns())

    group_columns = (
        "side",
        "setup_month",
        "confidence_bucket",
        "sl_anchor_type",
        "sl_source_tf",
        "anchor_age_bucket",
        "context_setup_alignment",
        "trigger_type",
        "reversal_marker",
        "stale_anchor",
        "signal_filter_reason",
    )
    frames = [
        _summarize_trade_group(
            enriched,
            window=window,
            params=params,
            run_dir=run_dir,
            dimension=column,
        )
        for column in group_columns
    ]
    return pd.concat(frames, ignore_index=True)


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
    max_positions: int | None = None,
) -> FixedCandidateParams:
    return FixedCandidateParams(
        capital=params.capital,
        risk_percent=params.risk_percent,
        rrr=rrr,
        ttl=ttl,
        maker_fee=params.maker_fee,
        taker_fee=params.taker_fee,
        max_positions=params.max_positions if max_positions is None else max_positions,
        max_allowed_leverage=params.max_allowed_leverage,
        max_allowed_margin=params.max_allowed_margin,
        risk_base_period=params.risk_base_period,
        is_isolated_futures=params.is_isolated_futures,
    )


def _candidate_run_label(params: FixedCandidateParams) -> str:
    return f"rrr_{_slug_float(params.rrr)}__ttl_{params.ttl}__maxpos_{params.max_positions}"


def _execution_grid_error_row(window: WindowSpec, exc: Exception) -> dict[str, str]:
    return {
        "label": window.label,
        "symbol": window.symbol,
        "from": window.start,
        "to": window.end,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }


def _slug_float(value: float) -> str:
    return f"{value:g}".replace("-", "m").replace(".", "_")


def _validate_unique_labels(windows: list[WindowSpec]) -> None:
    labels = [window.label for window in windows]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        joined = ", ".join(duplicates)
        raise ValueError(f"Duplicate window labels would overwrite run outputs: {joined}")


def _count_column(df: pd.DataFrame, column: str) -> dict[Any, int]:
    if df.empty or column not in df.columns:
        return {}
    return {
        key: int(value) for key, value in df[column].value_counts(dropna=False).sort_index().items()
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


def _margin_summary(trades: pd.DataFrame, *, initial_capital: float) -> dict[str, Any]:
    if trades.empty:
        return {
            "peak_open_positions": 0,
            "peak_locked_margin": 0.0,
            "peak_locked_margin_pct_initial": 0.0,
            "peak_locked_margin_pct_capital": 0.0,
            "min_available_balance_before": 0.0,
        }

    open_positions_before = pd.to_numeric(
        _column_series(trades, "open_positions_before"),
        errors="coerce",
    )
    if open_positions_before.notna().any():
        peak_open_positions = int(open_positions_before.max()) + 1
    else:
        peak_open_positions = 0

    if "total_locked_margin_after_entry" in trades.columns:
        locked_after_entry = pd.to_numeric(
            trades["total_locked_margin_after_entry"],
            errors="coerce",
        )
    elif {"total_locked_margin_before", "locked_margin"}.issubset(trades.columns):
        locked_after_entry = pd.to_numeric(
            trades["total_locked_margin_before"],
            errors="coerce",
        ).fillna(0.0) + pd.to_numeric(trades["locked_margin"], errors="coerce").fillna(0.0)
    else:
        locked_after_entry = pd.to_numeric(
            _column_series(trades, "locked_margin"),
            errors="coerce",
        )

    valid_locked = locked_after_entry.dropna()
    peak_locked_margin = float(valid_locked.max()) if not valid_locked.empty else 0.0
    peak_locked_margin_pct_initial = (
        peak_locked_margin / initial_capital * 100 if initial_capital > 0 else 0.0
    )

    capital_before = pd.to_numeric(_column_series(trades, "capital_before"), errors="coerce")
    locked_pct_capital = (locked_after_entry / capital_before.replace(0, pd.NA)) * 100
    valid_locked_pct_capital = locked_pct_capital.dropna()
    peak_locked_margin_pct_capital = (
        float(valid_locked_pct_capital.max()) if not valid_locked_pct_capital.empty else 0.0
    )

    available_balance_before = pd.to_numeric(
        _column_series(trades, "available_balance_before"),
        errors="coerce",
    ).dropna()
    min_available_balance_before = (
        float(available_balance_before.min()) if not available_balance_before.empty else 0.0
    )

    return {
        "peak_open_positions": peak_open_positions,
        "peak_locked_margin": round(peak_locked_margin, 2),
        "peak_locked_margin_pct_initial": round(peak_locked_margin_pct_initial, 2),
        "peak_locked_margin_pct_capital": round(peak_locked_margin_pct_capital, 2),
        "min_available_balance_before": round(min_available_balance_before, 2),
    }


def _prefixed_counts(counts: dict[Any, int], prefix: str) -> dict[str, int]:
    return {f"{prefix}_{_slug_count_key(key)}": value for key, value in counts.items()}


def _slug_count_key(key: Any) -> str:
    text = "missing" if pd.isna(key) else str(key)
    return text.lower().replace(" ", "_").replace("-", "_").replace(":", "_").replace("/", "_")


def _enrich_signal_quality_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=_signal_quality_group_columns())

    df = trades.copy()
    df["side"] = df.get("is_long", pd.Series(index=df.index)).map({True: "long", False: "short"})
    df["signal_time_for_group"] = _first_available_datetime(df, ("signal_time", "entry_time"))
    df["setup_month"] = df["signal_time_for_group"].dt.strftime("%Y-%m").fillna("unknown")
    confidence = pd.to_numeric(_column_series(df, "confidence"), errors="coerce")
    df["confidence_bucket"] = pd.cut(
        confidence,
        bins=[0, 25, 40, 55, 70, 85, 101],
        right=False,
        include_lowest=True,
        labels=["0_25", "25_40", "40_55", "55_70", "70_85", "85_101"],
    ).astype("string")
    df["confidence_bucket"] = df["confidence_bucket"].fillna("unknown")

    anchor_known_at = pd.to_datetime(
        _column_series(df, "sl_anchor_known_at"),
        errors="coerce",
        utc=True,
    )
    age_hours = (df["signal_time_for_group"] - anchor_known_at).dt.total_seconds() / 3600
    df["anchor_age_hours"] = age_hours
    df["anchor_age_bucket"] = age_hours.map(_anchor_age_bucket).fillna("unknown")
    df["stale_anchor"] = age_hours.gt(72).fillna(False)
    df["reversal_marker"] = [
        _is_context_reversal(context_bias, side)
        for context_bias, side in zip(
            _column_series(df, "context_bias"),
            df["side"],
            strict=False,
        )
    ]
    df["context_setup_alignment"] = [
        _context_setup_alignment(context_bias, setup_direction)
        for context_bias, setup_direction in zip(
            _column_series(df, "context_bias"),
            _column_series(df, "setup_direction"),
            strict=False,
        )
    ]
    for column in (
        "sl_anchor_type",
        "sl_source_tf",
        "trigger_type",
        "signal_filter_reason",
    ):
        if column not in df.columns:
            df[column] = "missing"
        df[column] = df[column].fillna("none").astype(str)
    return df


def _first_available_datetime(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    result = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    for column in columns:
        if column not in df.columns:
            continue
        values = pd.to_datetime(df[column], errors="coerce", utc=True)
        result = result.fillna(values)
    return result


def _anchor_age_bucket(value: float) -> str:
    if not pd.notna(value):
        return "unknown"
    if value < 6:
        return "fresh_0_6h"
    if value < 24:
        return "recent_6_24h"
    if value < 72:
        return "stale_24_72h"
    return "old_72h_plus"


def _is_context_reversal(context_bias: Any, side: Any) -> bool:
    return (context_bias == "bearish" and side == "long") or (
        context_bias == "bullish" and side == "short"
    )


def _context_setup_alignment(context_bias: Any, setup_direction: Any) -> str:
    if context_bias not in {"bullish", "bearish"}:
        return "neutral"
    if (context_bias == "bullish" and setup_direction == "BUY") or (
        context_bias == "bearish" and setup_direction == "SELL"
    ):
        return "aligned"
    if setup_direction in {"BUY", "SELL"}:
        return "opposed"
    return "neutral"


def _summarize_trade_group(
    trades: pd.DataFrame,
    *,
    window: WindowSpec,
    params: FixedCandidateParams,
    run_dir: Path,
    dimension: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = trades.groupby(dimension, dropna=False)
    for group_value, group in grouped:
        pnl = pd.to_numeric(_column_series(group, "pnl_abs"), errors="coerce")
        exit_reason = _column_series(group, "exit_reason")
        side = _column_series(group, "side")
        rows.append(
            {
                "label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "rrr": params.rrr,
                "ttl": params.ttl,
                "max_positions": params.max_positions,
                "risk_percent": params.risk_percent,
                "dimension": dimension,
                "group": str(group_value),
                "trades": len(group),
                "pnl_sum": round(float(pnl.sum()), 2) if not pnl.empty else 0.0,
                "pnl_mean": round(float(pnl.mean()), 4) if not pnl.empty else 0.0,
                "win_rate": round(float(pnl.gt(0).mean()), 4) if not pnl.empty else 0.0,
                "long_trades": int((side == "long").sum()),
                "short_trades": int((side == "short").sum()),
                "exit_take_profit": int((exit_reason == "take_profit").sum()),
                "exit_stop_loss": int((exit_reason == "stop_loss").sum()),
                "exit_ttl_expired": int((exit_reason == "ttl_expired").sum()),
                "run_dir": str(run_dir),
            }
        )
    return pd.DataFrame(rows, columns=_signal_quality_group_columns())


def _signal_quality_group_columns() -> list[str]:
    return [
        "label",
        "symbol",
        "from",
        "to",
        "rrr",
        "ttl",
        "max_positions",
        "risk_percent",
        "dimension",
        "group",
        "trades",
        "pnl_sum",
        "pnl_mean",
        "win_rate",
        "long_trades",
        "short_trades",
        "exit_take_profit",
        "exit_stop_loss",
        "exit_ttl_expired",
        "run_dir",
    ]


def _column_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(index=df.index, dtype="object")


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
