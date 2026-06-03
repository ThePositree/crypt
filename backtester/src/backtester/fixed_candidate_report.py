from __future__ import annotations

import logging
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
    logger: logging.Logger,
) -> pd.DataFrame:
    output_path = Path(output_folder)
    runs_path = output_path / "runs"
    output_path.mkdir(parents=True, exist_ok=True)
    runs_path.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for window in windows:
        logger.info(
            "Running fixed candidate %s %s -> %s",
            window.label,
            window.start,
            window.end,
        )
        df = _load_window_data(
            window=window,
            data_dir=data_dir,
            primary_timeframe=primary_timeframe,
            logger=logger,
        )
        strategy = build_strategy_instance(cfg.name, cfg.params, logger=logger)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {cfg.name}")

        results = run_backtest(
            df=df,
            strategy=strategy,
            args=params.to_backtest_args(),
        )
        run_dir = runs_path / window.label
        export_and_optional_analysis(
            results=results,
            ohlcv_df=df,
            output_folder=str(run_dir),
            analyze_conditions=False,
            top_predictors=10,
            create_visualizations=False,
            create_dashboard=False,
            logger=logger,
        )
        rows.append(
            summarize_fixed_candidate_run(
                window=window,
                params=params,
                metrics=results.metrics,
                signals=results.signals,
                trades=results.trades,
                run_dir=run_dir,
            )
        )

    summary = pd.DataFrame(rows)
    summary_path = output_path / "windows.csv"
    summary.to_csv(summary_path, index=False)
    markdown_path = output_path / "windows.md"
    markdown_path.write_text(_to_markdown_table(summary) + "\n")
    logger.info("Fixed-candidate summary saved to: %s", summary_path)
    logger.info("Fixed-candidate markdown saved to: %s", markdown_path)
    return summary


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
