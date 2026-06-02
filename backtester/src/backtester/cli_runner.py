"""CLI runner helpers.

This module contains the orchestration building blocks used by the Click CLI
entrypoint in :mod:`backtester.__main__`.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.data_loader import (
    BaseDataLoader,
    BingxApiDataLoader,
    CryptParquetDataLoader,
    CsvDataLoader,
    ParquetDataLoader,
)
from backtester.registry import STRATEGIES
from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategy import BaseStrategy
from backtester.tester import Backtester


def parse_utc_datetime_to_ms(s: str) -> int:
    """Parse datetime string 'YYYY-MM-DD HH:MM:SS' (UTC) to milliseconds since epoch."""
    dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
    return int(dt.replace(tzinfo=UTC).timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Parsed strategy configuration loaded from JSON.

    Parameters
    ----------
    name:
        Strategy registry key (see :data:`backtester.registry.STRATEGIES`).
    version:
        Optional version string for logging/reporting.
    params:
        Strategy constructor params.
    backtest_args:
        Optional backtest overrides (only a subset is applied by the CLI).
    """

    name: str
    version: str
    params: dict[str, Any]
    backtest_args: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BacktestArgs:
    """Arguments passed to :meth:`backtester.tester.Backtester.run`.

    Parameters
    ----------
    capital:
        Initial capital.
    risk_percent:
        Risk percent per trade (in percent units, e.g. 1.0 means 1%).
    rrr:
        Reward/Risk ratio.
    maker_fee:
        Maker fee rate.
    taker_fee:
        Taker fee rate.
    ttl:
        Position TTL in bars.
    max_positions:
        Maximum simultaneous positions.
    max_allowed_leverage:
        Maximum allowed leverage.
    is_isolated_futures:
        Enable isolated futures mode.
    max_allowed_margin:
        Maximum allowed margin.
    risk_base_period:
        Capital window used for risk sizing: trade, weekly, monthly, or backtest.
    max_daily_profit:
        Optional daily profit limit (RRR); new positions disabled when exceeded.
    max_daily_loss:
        Optional daily loss limit (RRR); new positions disabled when exceeded.
    trading_begin:
        Optional start hour (0-23) for trading window; entries only when hour >= this.
    trading_end:
        Optional end hour (0-24) for trading window; entries only when hour < this.
    """

    capital: float
    risk_percent: float
    rrr: float
    maker_fee: float
    taker_fee: float
    ttl: int
    max_positions: int
    max_allowed_leverage: float
    is_isolated_futures: bool
    max_allowed_margin: float
    risk_base_period: str
    max_daily_profit: float | None = None
    max_daily_loss: float | None = None
    trading_begin: int | None = None
    trading_end: int | None = None


def load_strategy_config(path: str, logger: logging.Logger) -> StrategyConfig | None:
    """Load and validate a strategy JSON config.

    Parameters
    ----------
    path:
        Path to a JSON file.
    logger:
        Logger to use for user-facing errors.

    Returns
    -------
    StrategyConfig | None
        Parsed config or ``None`` if validation failed (error already logged).
    """

    if not os.path.exists(path):
        logger.error("❌ File not found: %s", path)
        return None

    try:
        with open(path, "r") as f:
            raw = json.load(f)
    except Exception:
        logger.exception("❌ Failed to load strategy params JSON: %s", path)
        return None

    if not raw or not isinstance(raw, dict):
        logger.error("❌ Invalid strategy parameters")
        return None

    name = raw.get("name")
    if not name or not isinstance(name, str):
        logger.error("❌ Strategy name not found in params")
        return None

    version = raw.get("version", "undefined")
    if not isinstance(version, str):
        version = str(version)

    params = raw.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        logger.error("❌ Strategy params must be an object/dict")
        return None

    backtest_args = raw.get("backtest_args", {})
    if backtest_args is None:
        backtest_args = {}
    if not isinstance(backtest_args, dict):
        logger.error("❌ backtest_args must be an object/dict")
        return None

    return StrategyConfig(
        name=name, version=version, params=params, backtest_args=backtest_args
    )


# Keys accepted in strategy JSON backtest_args (must match BacktestArgs fields).
_BACKTEST_ARG_KEYS = frozenset(
    {
        "capital",
        "risk_percent",
        "rrr",
        "maker_fee",
        "taker_fee",
        "ttl",
        "max_positions",
        "max_allowed_leverage",
        "is_isolated_futures",
        "max_allowed_margin",
        "risk_base_period",
        "max_daily_profit",
        "max_daily_loss",
        "trading_begin",
        "trading_end",
    }
)


def build_backtest_args(
    cfg: StrategyConfig | None, **cli_kwargs: Any
) -> BacktestArgs:
    """Build BacktestArgs from CLI kwargs, with strategy ``backtest_args`` overrides.

    Any key present in the strategy JSON ``backtest_args`` overrides the
    corresponding CLI value. Only keys that are valid BacktestArgs fields
    are applied.

    Parameters
    ----------
    cfg : StrategyConfig | None
        Loaded strategy config; if None, no overrides are applied.
    **cli_kwargs : Any
        Backtest parameters as passed from the CLI (same names as BacktestArgs).

    Returns
    -------
    BacktestArgs
        Merged arguments for :meth:`backtester.tester.Backtester.run`.
    """
    kwargs = dict(cli_kwargs)
    if cfg is not None:
        for key in _BACKTEST_ARG_KEYS:
            if key in cfg.backtest_args:
                kwargs[key] = cfg.backtest_args[key]
    return BacktestArgs(**kwargs)


def log_strategy_info(cfg: StrategyConfig, logger: logging.Logger) -> None:
    """Log strategy metadata and parameters."""

    logger.info("  Strategy %s:", cfg.name)
    logger.info("    Version: %s", cfg.version)
    if len(cfg.params) == 0:
        logger.info("    ⚠️ No strategy parameters found")

    for key, value in cfg.params.items():
        if isinstance(value, float):
            logger.info("    %s: %.4f", key, value)
        else:
            logger.info("    %s: %s", key, value)


def load_ohlcv_via_loader(
    loader: BaseDataLoader, *, logger: logging.Logger
) -> StrategyInput | None:
    """Load OHLCV data using any BaseDataLoader instance.

    Parameters
    ----------
    loader : BaseDataLoader
        Loader instance (e.g. CsvDataLoader, BingxApiDataLoader).
    logger : logging.Logger
        Logger for user-facing messages.

    Returns
    -------
    StrategyInput | None
        Loaded OHLCV DataFrame/StrategyData or ``None`` on error.
    """
    try:
        df = loader.load()
        bars = len(df.primary) if isinstance(df, StrategyData) else len(df)
        logger.info("  ✅ Loaded %d bars", bars)
        return df
    except Exception:
        logger.exception("❌ Data loading error")
        return None


def build_cli_data_loader(
    data_source: str,
    *,
    csv_path: str | None = None,
    parquet_path: str | None = None,
    data_dir: str | None = None,
    symbol: str | None = None,
    primary_timeframe: str = "4h",
    ts_col: str = "timestamp",
    bingx_symbol: str | None = None,
    bingx_interval: str | None = None,
    bingx_start_time_ms: int | None = None,
    bingx_end_time_ms: int | None = None,
    bingx_api_key: str | None = None,
    bingx_api_secret: str | None = None,
    bingx_base_url: str = "https://open-api.bingx.com",
    bingx_time_zone: int = 0,
    bingx_recv_window: int = 30_000,
    bingx_cache_dir: str | None = None,
) -> BaseDataLoader:
    """Build a data loader for CLI based on data source and kwargs.

    Parameters
    ----------
    data_source : str
        One of ``\"csv\"``, ``\"bingx\"``, ``\"parquet\"``, or
        ``\"crypt-parquet\"``.
    csv_path : str, optional
        Path to CSV file (required when data_source is ``\"csv\"``).
    ts_col : str, default \"timestamp\"
        Timestamp column name for CSV.
    bingx_symbol : str, optional
        BingX symbol, e.g. ``\"BTC-USDT\"`` (required for bingx).
    bingx_interval : str, optional
        BingX kline interval, e.g. ``\"1m\"``, ``\"1h\"`` (required for bingx).
    bingx_start_time_ms : int, optional
        Start time in milliseconds since epoch (required for bingx).
    bingx_end_time_ms : int, optional
        End time in milliseconds since epoch (required for bingx).
    bingx_api_key : str, optional
        BingX API key (required for bingx).
    bingx_api_secret : str, optional
        BingX API secret (required for bingx).
    bingx_base_url : str, optional
        BingX API base URL.
    bingx_time_zone : int, optional
        Time zone offset (0 or 8).
    bingx_recv_window : int, optional
        Request valid time window in ms.
    bingx_cache_dir : str, optional
        Optional directory for on-disk caching when using the BingX API source.

    Returns
    -------
    BaseDataLoader
        Configured loader instance.

    Raises
    ------
    ValueError
        If data_source is unsupported or required parameters are missing.
    """
    source = data_source.lower()
    if source == "csv":
        if not csv_path:
            raise ValueError("CSV data source requires --csv (path to CSV file)")
        return CsvDataLoader(
            filepath=csv_path,
            timestamp_col=ts_col,
            time_format="%Y-%m-%d %H:%M:%S",
        )
    if source == "parquet":
        if not parquet_path:
            raise ValueError("Parquet data source requires --parquet")
        return ParquetDataLoader(filepath=parquet_path, timestamp_col=ts_col)
    if source == "crypt-parquet":
        missing = []
        if not data_dir:
            missing.append("--data-dir")
        if not symbol:
            missing.append("--symbol")
        if missing:
            raise ValueError(
                f"crypt-parquet data source requires: {', '.join(missing)}"
            )
        return CryptParquetDataLoader(
            data_dir=data_dir,
            symbol=symbol,
            primary_timeframe=primary_timeframe,
        )
    if source == "bingx":
        missing = []
        if not bingx_symbol:
            missing.append("--bingx-symbol")
        if not bingx_interval:
            missing.append("--bingx-interval")
        if bingx_start_time_ms is None:
            missing.append("--bingx-start-time")
        if bingx_end_time_ms is None:
            missing.append("--bingx-end-time")
        if not bingx_api_key:
            missing.append("--bingx-api-key")
        if not bingx_api_secret:
            missing.append("--bingx-api-secret")
        if missing:
            raise ValueError(
                f"BingX data source requires: {', '.join(missing)}"
            )
        return BingxApiDataLoader(
            symbol=bingx_symbol,
            interval=bingx_interval,
            start_time=bingx_start_time_ms,
            end_time=bingx_end_time_ms,
            api_key=bingx_api_key,
            api_secret=bingx_api_secret,
            base_url=bingx_base_url,
            time_zone=bingx_time_zone,
            recv_window=bingx_recv_window,
            cache_dir=bingx_cache_dir,
        )
    raise ValueError(f"Unsupported data source: {data_source!r}")


def load_ohlcv_csv(
    path: str, *, ts_col: str, logger: logging.Logger
) -> pd.DataFrame | None:
    """Load OHLCV data from a CSV file (thin wrapper over CsvDataLoader)."""
    if not os.path.exists(path):
        logger.error("❌ File not found: %s", path)
        return None
    loader = CsvDataLoader(
        filepath=path,
        timestamp_col=ts_col,
        time_format="%Y-%m-%d %H:%M:%S",
    )
    return load_ohlcv_via_loader(loader, logger=logger)


def build_strategy_instance(
    name: str, params: dict[str, Any], *, logger: logging.Logger
) -> BaseStrategy | None:
    """Instantiate a strategy by registry key."""

    if name not in STRATEGIES:
        available = ", ".join(sorted(STRATEGIES.keys()))
        logger.error("❌ Unknown strategy '%s'. Available: %s", name, available)
        return None

    strategy_cls = STRATEGIES[name]
    return strategy_cls(params)


def run_backtest(*, df: StrategyInput, strategy: BaseStrategy, args: BacktestArgs):
    """Run the backtest and return an analyzer instance."""

    bt = Backtester(df, strategy.generate)
    return bt.run(
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


def make_output_folder(base: str) -> str:
    """Create timestamped output folder path."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return os.path.join(base, timestamp)


def export_and_optional_analysis(
    *,
    results: ResultsAnalyzer,
    ohlcv_df: StrategyInput,
    output_folder: str,
    analyze_conditions: bool,
    top_predictors: int,
    create_visualizations: bool,
    create_dashboard: bool,
    logger: logging.Logger,
) -> None:
    """Export results and optionally analyze trade conditions.

    Without analysis: always exports results.
    With analysis: exports results only when predictors were found (non-empty).
    """

    primary_df = ohlcv_df.primary if isinstance(ohlcv_df, StrategyData) else ohlcv_df

    if not analyze_conditions:
        results.export_results(output_folder, ohlcv_df=primary_df)
        logger.info("📁 Results saved to: %s", output_folder)
        return

    logger.info("🔍 Analyzing trade conditions...")
    try:
        trade_analyzer = results.analyze_trade_conditions(primary_df)
        if not trade_analyzer:
            logger.warning("⚠️ Trade conditions analysis failed")
            return

        best_predictors = results.find_best_predictors(top_predictors)
        if best_predictors.empty:
            logger.warning("⚠️ No predictors found - insufficient data")
            return

        logger.info("🏆 Top predictors found:")
        for _, row in best_predictors.head(5).iterrows():
            logger.info(
                "  %s: AUC=%.3f, KS=%.3f",
                row["metric_name"],
                row["auc_score"],
                row["ks_statistic"],
            )

        results.export_results(output_folder, ohlcv_df=primary_df)

        conditions_file = os.path.join(output_folder, "trade_conditions_analysis.csv")
        best_predictors.to_csv(conditions_file, index=False)
        logger.info("📊 Trade conditions analysis saved to: %s", conditions_file)

        conditions_report = results.get_trade_conditions_report()
        logger.info("\n%s", conditions_report)

        if create_visualizations or create_dashboard:
            logger.info("🎨 Creating visualizations...")
            try:
                if create_visualizations:
                    results.create_visualizations(output_folder, "trade_analysis")
                    logger.info("📊 Visualizations created successfully")

                if create_dashboard:
                    results.create_summary_dashboard(output_folder, "summary_dashboard")
                    logger.info("📈 Summary dashboard created successfully")

            except Exception as e:
                logger.exception("❌ Error creating visualizations: %s", e)

    except Exception as e:
        logger.exception("❌ Error during trade conditions analysis: %s", e)
