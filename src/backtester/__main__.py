import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO, Any, Literal, cast

_SRC_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT_STR = str(_SRC_ROOT)
if _SRC_ROOT_STR in sys.path:
    sys.path.remove(_SRC_ROOT_STR)
# Console scripts do not inherit pytest's pythonpath setting; keep the project
# package ahead of the deprecated stdlib crypt module.
sys.path.insert(0, _SRC_ROOT_STR)

import click  # noqa: E402
import pandas as pd  # noqa: E402

from backtester.cli_runner import (  # noqa: E402
    OptimizerSearchArgs,
    build_backtest_args,
    build_cli_data_loader,
    build_strategy_instance,
    candle_timeframe_minutes,
    export_and_optional_analysis,
    load_ohlcv_via_loader,
    load_strategy_config,
    log_strategy_info,
    make_output_folder,
    parse_utc_datetime_to_ms,
    run_backtest,
    run_parameter_optimization,
    strategy_config_candle_timeframe,
)
from backtester.data_contracts import StrategyData, StrategyInput, select_candle_frame  # noqa: E402
from backtester.strategy_discovery import (  # noqa: E402
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    parameterized_filter_catalog,
    parameterized_trigger_catalog,
    parameterized_trigger_param_space,
    pinescript_filter_catalog,
    pinescript_filter_param_space,
    pinescript_trigger_catalog,
    pinescript_trigger_param_space,
    run_catcma_qd_search,
    run_dss_directional_search,
    run_hyperband_qd_search,
    run_island_qd_search,
    run_smac_qd_search,
)
from backtester.strategy_discovery.catalog_timeframes import (  # noqa: E402
    dss_instance_labels,
)
from backtester.strategy_discovery.dss_config import ParamDef  # noqa: E402
from backtester.strategy_discovery.features import select_timeframe_frame  # noqa: E402
from backtester.strategy_discovery.parameterized_filters import (  # noqa: E402
    FilterFactory,
    parameterized_filter_param_space,
)
from backtester.strategy_discovery.parameterized_triggers import TriggerFactory  # noqa: E402

log_level = logging.getLevelNamesMapping().get(os.environ.get("LOG_LEVEL", "INFO"), logging.INFO)

# Configure logging
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtester")

_DSS_MATRIX_DEFAULT_SEEDS = {
    "directional": 73023,
    "catcma_qd": 777,
    "island_qd": 2026,
    "hyperband_qd": 4242,
    "smac_qd": 5151,
}
_DEFAULT_DATA_DIR = "data"
_DEFAULT_SYMBOL = "SOL-USDT-SWAP"
_DEFAULT_OPTUNA_TRIALS = 50_000
_DEFAULT_BACKTEST_WARMUP_DAYS = 30


def _is_full_history_bound(value: str | None) -> bool:
    return value is None or value.strip().lower() in {"", "full", "all"}


def _default_backtest_load_start(from_date: str | None) -> str | None:
    if _is_full_history_bound(from_date):
        return None
    start = pd.Timestamp(from_date)
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    load_start = start - timedelta(days=_DEFAULT_BACKTEST_WARMUP_DAYS)
    return load_start.isoformat().replace("+00:00", "Z")


def _trim_frame_to_execution_window(
    frame: pd.DataFrame,
    *,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    output = frame
    if start is not None:
        start_ts = pd.Timestamp(start)
        start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
        output = output.loc[output.index >= start_ts]
    if end is not None:
        end_ts = pd.Timestamp(end)
        end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
        output = output.loc[output.index <= end_ts]
    return output
_DEFAULT_OPTUNA_RRR_LOW = 1.0
_DEFAULT_OPTUNA_RRR_HIGH = 10.0
_DEFAULT_OPTUNA_RRR_STEP = 0.25
_DEFAULT_OPTUNA_RISK_LOW = 0.25
_DEFAULT_OPTUNA_RISK_HIGH = 3.0
_DEFAULT_OPTUNA_RISK_STEP = 0.25
_DEFAULT_OPTUNA_TTL_MINUTES_LOW = 60
_DEFAULT_OPTUNA_TTL_MINUTES_HIGH = 10_080
_DEFAULT_OPTUNA_TTL_MINUTES_STEP = 60
_DEFAULT_OPTUNA_TRAIL_ATR_LOW = 0.5
_DEFAULT_OPTUNA_TRAIL_ATR_HIGH = 10.0
_DEFAULT_OPTUNA_TRAIL_ATR_STEP = 0.5
_DEFAULT_OPTUNA_TP_MOVE_LOW = 0.004
_DEFAULT_OPTUNA_TP_MOVE_HIGH = 0.14
_DEFAULT_OPTUNA_TP_MOVE_STEP = 0.002


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--data-source",
    type=click.Choice(
        ["csv", "bingx", "parquet", "crypt-parquet"],
        case_sensitive=False,
    ),
    default="crypt-parquet",
    hidden=True,
    help="Data source: csv, bingx, parquet, or crypt-parquet.",
)
@click.option(
    "--csv",
    default=None,
    hidden=True,
    help="Path to OHLCV CSV file (required if --data-source=csv)",
)
@click.option(
    "--parquet",
    default=None,
    hidden=True,
    help="Path to OHLCV Parquet file (required if --data-source=parquet)",
)
@click.option(
    "--data-dir",
    default=_DEFAULT_DATA_DIR,
    show_default=True,
    help="Project data directory.",
)
@click.option(
    "--from",
    "from_date",
    default=None,
    help="Inclusive start date/time in UTC. Omit or pass full for full history.",
)
@click.option(
    "--to",
    "to_date",
    default=None,
    help="Inclusive end date/time in UTC. Omit or pass full for full history.",
)
@click.option("--symbol", default=_DEFAULT_SYMBOL, show_default=True, help="Trading pair name.")
@click.option("--strategy", required=True, help="Strategy parameters file")
@click.option("--output", default="results/backtesting", help="Folder to save results")
@click.option("--capital", type=float, default=10000.0, show_default=True, help="Initial capital")
@click.option(
    "--risk-percent",
    type=float,
    default=1.0,
    hidden=True,
    help="Risk Percent (ignored if defined in strategy params)",
)
@click.option(
    "--rrr",
    type=float,
    default=2.0,
    hidden=True,
    help="Reward/Risk Ratio (ignored if defined in strategy params)",
)
@click.option("--maker-fee", type=float, default=0.0002, hidden=True, help="Maker fee")
@click.option("--taker-fee", type=float, default=0.0005, hidden=True, help="Taker fee")
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    hidden=True,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=0, hidden=True, help="Legacy max position duration in bars.")
@click.option("--ttl-minutes", type=int, default=None, hidden=True, help="Max position duration in minutes.")
@click.option("--max-allowed-leverage", type=float, default=25.0, hidden=True, help="Max allowed leverage")
@click.option("--ts-col", type=str, default="timestamp", hidden=True, help="timestamp column name")
@click.option(
    "--analyze-conditions",
    is_flag=True,
    hidden=True,
    help="Analyze trade conditions and find best predictors",
)
@click.option("--top-predictors", type=int, default=10, hidden=True, help="Number of top predictors to show")
@click.option(
    "--create-visualizations",
    is_flag=True,
    hidden=True,
    help="Create visualizations for trade conditions analysis",
)
@click.option("--create-dashboard", is_flag=True, hidden=True, help="Create summary dashboard")
@click.option("--max-allowed-margin", type=float, default=1.0, hidden=True, help="Max allowed margin")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    hidden=True,
    help="Capital window used for risk sizing.",
)
@click.option(
    "--capital-sweep",
    type=click.Choice(["none", "monthly_profit", "trade_profit"], case_sensitive=False),
    default="none",
    hidden=True,
    help=(
        "Capital withdrawal mode. monthly_profit banks realized profit "
        "above initial capital at month boundaries; trade_profit banks it "
        "after each profitable closed trade."
    ),
)
@click.option(
    "--max-daily-profit",
    type=float,
    default=None,
    hidden=True,
    help="Daily profit limit in RRR; disable new entries when exceeded.",
)
@click.option(
    "--max-daily-loss",
    type=float,
    default=None,
    hidden=True,
    help="Daily loss limit in RRR; disable new entries when exceeded.",
)
@click.option(
    "--trading-begin",
    type=int,
    default=None,
    hidden=True,
    help="Trading window start hour (0-23, UTC). Entries only when hour >= this.",
)
@click.option(
    "--trading-end",
    type=int,
    default=None,
    hidden=True,
    help="Trading window end hour (0-24, UTC). Entries only when hour < this.",
)
@click.option(
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    hidden=True,
    help="Exit placement: structural SL+RRR (default) or TP-first percent.",
)
@click.option(
    "--tp-move-pct",
    type=float,
    default=None,
    hidden=True,
    help="Target gross TP price move decimal (0.015 = 1.5%). Required for tp_pct.",
)
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    hidden=True,
    help="How structural sl_price constrains TP-first SL.",
)
@click.option(
    "--min-tp-move-pct",
    type=float,
    default=0.004,
    hidden=True,
    help="Skip entries when tp_move_pct is below this breakeven floor.",
)
@click.option(
    "--bingx-symbol",
    type=str,
    default=None,
    hidden=True,
    help="BingX symbol, e.g. BTC-USDT (required if --data-source=bingx).",
)
@click.option(
    "--bingx-interval",
    type=str,
    default=None,
    hidden=True,
    help="BingX kline interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w (required if --data-source=bingx).",
)
@click.option(
    "--bingx-start-time",
    type=str,
    default=None,
    hidden=True,
    help="Start time UTC, format: YYYY-MM-DD HH:MM:SS (required if --data-source=bingx).",
)
@click.option(
    "--bingx-end-time",
    type=str,
    default=None,
    hidden=True,
    help="End time UTC, format: YYYY-MM-DD HH:MM:SS (required if --data-source=bingx).",
)
@click.option(
    "--bingx-api-key",
    type=str,
    default=None,
    hidden=True,
    help="BingX API key (required if --data-source=bingx).",
)
@click.option(
    "--bingx-api-secret",
    type=str,
    default=None,
    hidden=True,
    help="BingX API secret (required if --data-source=bingx).",
)
@click.option(
    "--bingx-base-url",
    type=str,
    default="https://open-api.bingx.com",
    hidden=True,
    help="BingX API base URL.",
)
@click.option(
    "--bingx-time-zone",
    type=int,
    default=0,
    hidden=True,
    help="BingX time zone offset (0 or 8).",
)
@click.option(
    "--bingx-recv-window",
    type=int,
    default=30000,
    hidden=True,
    help="BingX request valid time window in ms.",
)
@click.option(
    "--bingx-cache-dir",
    type=str,
    default=None,
    hidden=True,
    help="Optional directory path for caching BingX OHLCV responses on disk.",
)
def run(
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    from_date: str | None,
    to_date: str | None,
    symbol: str,
    strategy: str,
    output: str,
    capital: float,
    risk_percent: float,
    rrr: float,
    maker_fee: float,
    taker_fee: float,
    trail_distance_atr: float,
    ttl: int,
    ttl_minutes: int | None,
    max_allowed_leverage: float,
    ts_col: str,
    analyze_conditions: bool,
    top_predictors: int,
    create_visualizations: bool,
    create_dashboard: bool,
    max_allowed_margin: float,
    risk_base_period: str,
    capital_sweep: str,
    max_daily_profit: float | None,
    max_daily_loss: float | None,
    trading_begin: int | None,
    trading_end: int | None,
    exit_geometry: str,
    tp_move_pct: float | None,
    structural_sl_mode: str,
    min_tp_move_pct: float,
    bingx_symbol: str | None,
    bingx_interval: str | None,
    bingx_start_time: str | None,
    bingx_end_time: str | None,
    bingx_api_key: str | None,
    bingx_api_secret: str | None,
    bingx_base_url: str,
    bingx_time_zone: int,
    bingx_recv_window: int,
    bingx_cache_dir: str | None,
) -> None:
    """Run backtesting via CLI"""
    logger.info("🚀 Starting backtest via CLI...")
    ctx = click.get_current_context()
    explicit_cli_keys = {
        key
        for key in (
            "capital",
            "risk_percent",
            "rrr",
            "maker_fee",
            "taker_fee",
            "trail_distance_atr",
            "ttl",
            "ttl_minutes",
            "max_allowed_leverage",
            "max_allowed_margin",
            "risk_base_period",
            "capital_sweep",
            "max_daily_profit",
            "max_daily_loss",
            "trading_begin",
            "trading_end",
            "exit_geometry",
            "tp_move_pct",
            "structural_sl_mode",
            "min_tp_move_pct",
        )
        if ctx.get_parameter_source(key) is click.core.ParameterSource.COMMANDLINE
    }
    logger.info("  Data source: %s", data_source)
    if data_source.lower() == "csv":
        logger.info("  File: %s", csv)
    elif data_source.lower() == "parquet":
        logger.info("  File: %s", parquet)
    else:
        logger.info("  Pair: %s", symbol)

    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return

    log_strategy_info(cfg, logger)
    candle_timeframe = strategy_config_candle_timeframe(cfg)
    logger.info("  Candle timeframe: %s", candle_timeframe)
    load_start = _default_backtest_load_start(from_date)
    load_end = None if _is_full_history_bound(to_date) else to_date
    execution_start = None if _is_full_history_bound(from_date) else from_date
    execution_end = None if _is_full_history_bound(to_date) else to_date
    if load_start != execution_start:
        logger.info("  Warmup start: %s", load_start)

    try:
        loader = build_cli_data_loader(
            data_source,
            csv_path=csv,
            parquet_path=parquet,
            data_dir=data_dir,
            symbol=symbol,
            candle_timeframe=candle_timeframe,
            start=load_start,
            end=load_end,
            ts_col=ts_col,
            bingx_symbol=bingx_symbol,
            bingx_interval=bingx_interval,
            bingx_start_time_ms=(
                parse_utc_datetime_to_ms(bingx_start_time) if bingx_start_time else None
            ),
            bingx_end_time_ms=(
                parse_utc_datetime_to_ms(bingx_end_time) if bingx_end_time else None
            ),
            bingx_api_key=bingx_api_key,
            bingx_api_secret=bingx_api_secret,
            bingx_base_url=bingx_base_url,
            bingx_time_zone=bingx_time_zone,
            bingx_recv_window=bingx_recv_window,
            bingx_cache_dir=bingx_cache_dir,
            load_execution_1m=cfg.backtest_args.get("intrabar_execution_timeframe") == "1m",
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    df = load_ohlcv_via_loader(loader, logger=logger, candle_timeframe=candle_timeframe)
    if df is None:
        return
    ohlcv = select_candle_frame(df, candle_timeframe)

    strategy_instance = build_strategy_instance(cfg.name, cfg.params, logger=logger)
    if strategy_instance is None:
        return

    if exit_geometry.lower() == "tp_pct" and tp_move_pct is None:
        logger.error("❌ --tp-move-pct is required when --exit-geometry=tp_pct")
        return

    args = build_backtest_args(
        cfg,
        candle_timeframe=candle_timeframe,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr,
        trail_activation_rrr=rrr if trail_distance_atr > 0 else 0.0,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
        **({"ttl_minutes": ttl_minutes} if ttl_minutes is not None else {}),
        max_positions=0,
        max_allowed_leverage=max_allowed_leverage,
        max_allowed_margin=max_allowed_margin,
        risk_base_period=risk_base_period,
        capital_sweep=capital_sweep,
        max_daily_profit=max_daily_profit,
        max_daily_loss=max_daily_loss,
        trading_begin=trading_begin,
        trading_end=trading_end,
        exit_geometry=exit_geometry,
        tp_move_pct=tp_move_pct,
        structural_sl_mode=structural_sl_mode,
        min_tp_move_pct=min_tp_move_pct,
        execution_start=execution_start,
        execution_end=execution_end,
        _explicit_cli_keys=explicit_cli_keys,
    )

    results = run_backtest(df=df, strategy=strategy_instance, args=args, ohlcv=ohlcv, progress=True)
    export_ohlcv = _trim_frame_to_execution_window(
        ohlcv,
        start=execution_start,
        end=execution_end,
    )

    results.print_report()

    output_folder = make_output_folder(output)
    export_and_optional_analysis(
        results=results,
        ohlcv_df=export_ohlcv,
        output_folder=output_folder,
        analyze_conditions=analyze_conditions,
        top_predictors=top_predictors,
        create_visualizations=create_visualizations,
        create_dashboard=create_dashboard,
        logger=logger,
    )


@cli.command()
@click.option(
    "--data-source",
    type=click.Choice(["csv", "parquet", "crypt-parquet"], case_sensitive=False),
    default="crypt-parquet",
    hidden=True,
    help="Data source: csv, parquet, or crypt-parquet.",
)
@click.option("--csv", default=None, hidden=True, help="Path to OHLCV CSV file.")
@click.option("--parquet", default=None, hidden=True, help="Path to OHLCV Parquet file.")
@click.option("--data-dir", default=_DEFAULT_DATA_DIR, show_default=True, help="Project data directory.")
@click.option("--from", "from_date", default=None, help="Inclusive start UTC. Omit or pass full for full history.")
@click.option("--to", "to_date", default=None, help="Inclusive end UTC. Omit or pass full for full history.")
@click.option("--symbol", default=_DEFAULT_SYMBOL, show_default=True, help="Trading pair name.")
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option("--output", default="results/optimization", help="Folder for results.")
@click.option("--capital", type=float, default=10000.0, show_default=True, help="Initial capital.")
@click.option("--maker-fee", type=float, default=0.0002, hidden=True, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, hidden=True, help="Taker fee.")
@click.option("--ttl", type=int, default=20, hidden=True, help="Legacy fixed TTL bars if no TTL range.")
@click.option("--ttl-minutes", type=int, default=None, hidden=True, help="Fixed TTL minutes if no TTL range.")
@click.option("--max-allowed-leverage", type=float, default=25.0, hidden=True, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, hidden=True, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    hidden=True,
    help="Capital window used for risk sizing.",
)
@click.option("--ts-col", type=str, default="timestamp", hidden=True, help="timestamp column name")
@click.option("--trials", type=int, default=_DEFAULT_OPTUNA_TRIALS, show_default=True, help="Number of Optuna trials.")
@click.option("--study-name", default="optimization", hidden=True, help="Optuna study/log name.")
@click.option("--rrr-low", type=float, default=_DEFAULT_OPTUNA_RRR_LOW, hidden=True, help="RRR search low bound.")
@click.option("--rrr-high", type=float, default=_DEFAULT_OPTUNA_RRR_HIGH, hidden=True, help="RRR search high bound.")
@click.option("--rrr-step", type=float, default=_DEFAULT_OPTUNA_RRR_STEP, hidden=True, help="RRR search step.")
@click.option(
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    hidden=True,
    help="Exit placement mode. tp_pct is auto-used when tp-move-pct range is set.",
)
@click.option(
    "--tp-move-pct",
    type=float,
    default=None,
    hidden=True,
    help="Fixed TP move pct when not searching (required for tp_pct without range).",
)
@click.option("--tp-move-pct-low", type=float, default=_DEFAULT_OPTUNA_TP_MOVE_LOW, hidden=True, help="TP move pct search low.")
@click.option("--tp-move-pct-high", type=float, default=_DEFAULT_OPTUNA_TP_MOVE_HIGH, hidden=True, help="TP move pct search high.")
@click.option("--tp-move-pct-step", type=float, default=_DEFAULT_OPTUNA_TP_MOVE_STEP, hidden=True, help="TP move pct search step.")
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    hidden=True,
    help="How structural sl_price constrains TP-first SL.",
)
@click.option(
    "--min-tp-move-pct",
    type=float,
    default=0.004,
    hidden=True,
    help="Breakeven floor for tp_move_pct in TP-first mode.",
)
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    hidden=True,
    help="Fixed trailing distance in ATR units when distance range is not provided.",
)
@click.option("--trail-distance-atr-low", type=float, default=_DEFAULT_OPTUNA_TRAIL_ATR_LOW, hidden=True, help="Trail ATR low.")
@click.option("--trail-distance-atr-high", type=float, default=_DEFAULT_OPTUNA_TRAIL_ATR_HIGH, hidden=True, help="Trail ATR high.")
@click.option("--trail-distance-atr-step", type=float, default=_DEFAULT_OPTUNA_TRAIL_ATR_STEP, hidden=True, help="Trail ATR step.")
@click.option("--ttl-low", type=int, default=None, hidden=True, help="Legacy TTL bars search low bound.")
@click.option("--ttl-high", type=int, default=None, hidden=True, help="Legacy TTL bars search high bound.")
@click.option("--ttl-step", type=int, default=1, hidden=True, help="Legacy TTL bars search step.")
@click.option("--ttl-minutes-low", type=int, default=_DEFAULT_OPTUNA_TTL_MINUTES_LOW, hidden=True, help="TTL minutes search low bound.")
@click.option("--ttl-minutes-high", type=int, default=_DEFAULT_OPTUNA_TTL_MINUTES_HIGH, hidden=True, help="TTL minutes search high bound.")
@click.option("--ttl-minutes-step", type=int, default=_DEFAULT_OPTUNA_TTL_MINUTES_STEP, hidden=True, help="TTL minutes search step.")
@click.option(
    "--risk-percent",
    type=float,
    default=1.0,
    hidden=True,
    help="Fixed risk percent when risk search is disabled.",
)
@click.option("--risk-percent-low", type=float, default=_DEFAULT_OPTUNA_RISK_LOW, hidden=True, help="Risk search low.")
@click.option("--risk-percent-high", type=float, default=_DEFAULT_OPTUNA_RISK_HIGH, hidden=True, help="Risk search high.")
@click.option("--risk-percent-step", type=float, default=_DEFAULT_OPTUNA_RISK_STEP, hidden=True, help="Risk search step.")
@click.option(
    "--strategy-param-search/--no-strategy-param-search",
    default=False,
    hidden=True,
    help="Allow strategy.suggest_params() during optimization.",
)
@click.option(
    "--daily-limit-search/--no-daily-limit-search",
    default=False,
    hidden=True,
    help="Optimize max daily profit/loss limits.",
)
@click.option(
    "--trading-window-search/--no-trading-window-search",
    default=False,
    hidden=True,
    help="Optimize trading window hours.",
)
@click.option(
    "--exit-family-search/--no-exit-family-search",
    default=True,
    hidden=True,
    help="Optimize exit family: sl_rrr, sl_rrr_trailing, or tp_pct.",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    hidden=True,
    help="Show Optuna progress bar.",
)
@click.option(
    "--export-best-run/--no-export-best-run",
    default=True,
    hidden=True,
    help="Export best-run diagnostics after optimization.",
)
def optimize(
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    from_date: str | None,
    to_date: str | None,
    symbol: str,
    strategy: str,
    output: str,
    capital: float,
    maker_fee: float,
    taker_fee: float,
    ttl: int,
    ttl_minutes: int | None,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    ts_col: str,
    trials: int,
    study_name: str,
    rrr_low: float,
    rrr_high: float,
    rrr_step: float,
    exit_geometry: str,
    tp_move_pct: float | None,
    tp_move_pct_low: float | None,
    tp_move_pct_high: float | None,
    tp_move_pct_step: float,
    structural_sl_mode: str,
    min_tp_move_pct: float,
    trail_distance_atr: float,
    trail_distance_atr_low: float | None,
    trail_distance_atr_high: float | None,
    trail_distance_atr_step: float,
    ttl_low: int | None,
    ttl_high: int | None,
    ttl_step: int,
    ttl_minutes_low: int | None,
    ttl_minutes_high: int | None,
    ttl_minutes_step: int,
    risk_percent: float,
    risk_percent_low: float | None,
    risk_percent_high: float | None,
    risk_percent_step: float,
    strategy_param_search: bool,
    daily_limit_search: bool,
    trading_window_search: bool,
    exit_family_search: bool,
    progress: bool,
    export_best_run: bool,
) -> None:
    """Run bounded parameter optimization via the donor ParameterOptimizer."""
    logger.info("🚀 Starting optimization via CLI...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    candle_timeframe = strategy_config_candle_timeframe(cfg)
    logger.info("  Candle timeframe: %s", candle_timeframe)
    load_start = _default_backtest_load_start(from_date)
    load_end = None if _is_full_history_bound(to_date) else to_date
    execution_start = None if _is_full_history_bound(from_date) else from_date
    execution_end = None if _is_full_history_bound(to_date) else to_date
    if load_start != execution_start:
        logger.info("  Warmup start: %s", load_start)

    try:
        loader = build_cli_data_loader(
            data_source,
            csv_path=csv,
            parquet_path=parquet,
            data_dir=data_dir,
            symbol=symbol,
            candle_timeframe=candle_timeframe,
            start=load_start,
            end=load_end,
            ts_col=ts_col,
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    df = load_ohlcv_via_loader(loader, logger=logger, candle_timeframe=candle_timeframe)
    if df is None:
        return
    ohlcv = select_candle_frame(df, candle_timeframe)

    backtest_args = build_backtest_args(
        cfg,
        candle_timeframe=candle_timeframe,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr_low,
        trail_activation_rrr=0.0,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
        **({"ttl_minutes": ttl_minutes} if ttl_minutes is not None else {}),
        max_positions=0,
        max_allowed_leverage=max_allowed_leverage,
        max_allowed_margin=max_allowed_margin,
        risk_base_period=risk_base_period,
        max_daily_profit=None,
        max_daily_loss=None,
        trading_begin=None,
        trading_end=None,
        exit_geometry=exit_geometry,
        tp_move_pct=tp_move_pct,
        structural_sl_mode=structural_sl_mode,
        min_tp_move_pct=min_tp_move_pct,
        execution_start=execution_start,
        execution_end=execution_end,
    )
    if tp_move_pct_low is not None and tp_move_pct_high is not None:
        tp_move_pct_range = (tp_move_pct_low, tp_move_pct_high, tp_move_pct_step)
    else:
        tp_move_pct_range = None
    if exit_geometry.lower() == "tp_pct" and tp_move_pct is None and tp_move_pct_range is None:
        logger.error(
            "❌ tp_pct mode requires --tp-move-pct or --tp-move-pct-low/--tp-move-pct-high"
        )
        return
    if risk_percent_low is None or risk_percent_high is None:
        risk_percent_range = None
    else:
        risk_percent_range = (
            risk_percent_low,
            risk_percent_high,
            risk_percent_step,
        )
    if ttl_minutes_low is not None and ttl_minutes_high is not None:
        ttl_minutes_range = (ttl_minutes_low, ttl_minutes_high, ttl_minutes_step)
    elif ttl_low is not None and ttl_high is not None:
        candle_minutes = candle_timeframe_minutes(candle_timeframe)
        ttl_minutes_range = (
            ttl_low * candle_minutes,
            ttl_high * candle_minutes,
            ttl_step * candle_minutes,
        )
    else:
        ttl_minutes_range = None
    if trail_distance_atr_low is None or trail_distance_atr_high is None:
        trail_distance_atr_range = None
    else:
        trail_distance_atr_range = (
            trail_distance_atr_low,
            trail_distance_atr_high,
            trail_distance_atr_step,
        )
    output_folder = make_output_folder(output)
    run_parameter_optimization(
        df=df,
        ohlcv=ohlcv,
        cfg=cfg,
        backtest_args=backtest_args,
        optimizer_args=OptimizerSearchArgs(
            trials=trials,
            study_name=study_name,
            target="mandate_score",
            show_progress=progress,
            optimize_strategy_params=strategy_param_search,
            risk_percent_range=risk_percent_range,
            rrr_range=(rrr_low, rrr_high, rrr_step),
            trail_distance_atr_range=trail_distance_atr_range,
            position_ttl_minutes_range=ttl_minutes_range,
            tp_move_pct_range=tp_move_pct_range,
            exit_family_search=exit_family_search,
            exit_families=("sl_rrr", "sl_rrr_trailing", "tp_pct"),
            optimize_daily_limits=daily_limit_search,
            optimize_trading_window=trading_window_search,
            export_best_run=export_best_run,
        ),
        output_folder=output_folder,
        logger=logger,
    )


def _load_discovery_window(
    *,
    data_dir: str,
    candle_timeframe: str,
    symbol: str,
    start: str,
    end: str,
) -> StrategyInput:
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir=data_dir,
        symbol=symbol,
        candle_timeframe=candle_timeframe,
        start=start,
        end=end,
    )
    df = load_ohlcv_via_loader(loader, logger=logger, candle_timeframe=candle_timeframe)
    if df is None:
        raise ValueError(f"Could not load discovery data for {symbol} {start}..{end}")
    return df



def _parse_dss_matrix_algorithms(raw: str) -> list[str]:
    algorithms = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not algorithms:
        raise click.ClickException("--algorithms must contain at least one algorithm")
    if algorithms == ["all"]:
        return list(_DSS_MATRIX_DEFAULT_SEEDS)

    allowed = set(_DSS_MATRIX_DEFAULT_SEEDS)
    unknown = sorted(set(algorithms) - allowed)
    if unknown:
        raise click.ClickException(
            "--algorithms contains unknown value(s): "
            + ", ".join(unknown)
            + ". Allowed: "
            + ", ".join(sorted(allowed))
        )
    return algorithms


def _dss_required_timeframes(search_space: DSSSearchSpace) -> tuple[str, ...]:
    required: set[str] = set()
    for label in (*search_space.trigger_names, *search_space.filter_names):
        if "@" in label:
            required.add(label.rsplit("@", 1)[1])
    return tuple(sorted(required))


def _validate_dss_required_candles(
    *,
    search_space: DSSSearchSpace,
    window_data: dict[str, StrategyData],
    windows: list[DSSWindowSpec],
    data_dir: str,
) -> None:
    missing: list[str] = []
    for timeframe in _dss_required_timeframes(search_space):
        for window_label, data in window_data.items():
            try:
                select_timeframe_frame(data, timeframe)
            except ValueError as exc:
                missing.append(f"{window_label}:{timeframe} ({exc})")
    if missing:
        backfill_hint = _dss_backfill_hint(data_dir=data_dir, windows=windows)
        raise click.ClickException(
            "DSS search space requires candle timeframes that are not loaded: "
            + "; ".join(missing)
            + ". Backfill the missing OHLCV candles before launching, or restrict the DSS "
            "timeframe search space.\n"
            + backfill_hint
        )


def _dss_backfill_hint(*, data_dir: str, windows: list[DSSWindowSpec]) -> str:
    by_symbol: dict[str, list[DSSWindowSpec]] = {}
    for window in windows:
        by_symbol.setdefault(window.symbol, []).append(window)

    commands: list[str] = ["Suggested non-interactive backfill command(s):"]
    for symbol, symbol_windows in sorted(by_symbol.items()):
        start = min(pd.Timestamp(window.start).date() for window in symbol_windows)
        end = max(pd.Timestamp(window.end).date() for window in symbol_windows) + timedelta(days=1)
        commands.append(
            "PYTHONPATH=src uv run python -m crypt.backfill "
            f"--symbol {symbol} "
            f"--from {start.isoformat()} "
            f"--to {end.isoformat()} "
            "--data-types ohlcv "
            f"--data-dir {data_dir}"
        )
    return "\n".join(commands)


def _build_dss_search_space(catalog: str) -> DSSSearchSpace:
    t_catalog, f_catalog, t_param_space, f_param_space = _dss_catalogs(catalog.lower())
    dss_timeframes = ("15m", "H1", "H4", "D1")
    return DSSSearchSpace(
        trigger_names=dss_instance_labels(
            tuple(sorted(t_catalog.keys())), dss_timeframes, role="trigger"
        ),
        filter_names=dss_instance_labels(tuple(sorted(f_catalog.keys())), dss_timeframes, role="filter"),
        trigger_param_bounds=dict(t_param_space),
        filter_param_bounds=dict(f_param_space),
        max_filters=4,
        trigger_timeframes=dss_timeframes,
        filter_timeframes=dss_timeframes,
    )


def _preflight_dss_matrix_candles(
    *,
    data_dir: str,
    symbols: tuple[str, ...],
    windows_spec: str,
    candle_timeframe: str,
    catalog: str,
) -> None:
    search_space = _build_dss_search_space(catalog)
    all_windows: list[DSSWindowSpec] = []
    window_data: dict[str, StrategyData] = {}
    raw_specs = [s.strip() for s in windows_spec.split(",") if s.strip()]
    for symbol in symbols:
        for raw in raw_specs:
            try:
                spec = DSSWindowSpec.parse(raw, symbol)
            except (ValueError, TypeError) as exc:
                raise click.ClickException(f"Invalid window spec {raw!r}: {exc}") from exc
            all_windows.append(spec)
            try:
                data_input = _load_discovery_window(
                    data_dir=data_dir,
                    candle_timeframe=candle_timeframe,
                    symbol=spec.symbol,
                    start=spec.start,
                    end=spec.end,
                )
            except (ValueError, FileNotFoundError) as exc:
                raise click.ClickException(f"Failed to load window {spec.label}: {exc}") from exc
            key = f"{spec.symbol}:{spec.label}"
            if isinstance(data_input, StrategyData):
                window_data[key] = StrategyData(
                    candles_by_timeframe=data_input.candles_by_timeframe,
                    extras=data_input.extras,
                    metadata={**data_input.metadata, "symbol": spec.symbol, "window_label": key},
                    execution=data_input.execution,
                )
            else:
                window_data[key] = StrategyData(
                    candles_by_timeframe={candle_timeframe: data_input},
                    extras={},
                    metadata={"symbol": spec.symbol, "window_label": key},
                )
    if not all_windows:
        raise click.ClickException(f"No windows parsed from --windows {windows_spec!r}")
    _validate_dss_required_candles(
        search_space=search_space,
        window_data=window_data,
        windows=all_windows,
        data_dir=data_dir,
    )


@cli.command("search-signals-matrix")
@click.option("--data-dir", default=_DEFAULT_DATA_DIR, show_default=True, help="Project data directory.")
@click.option(
    "--symbol",
    "symbols",
    multiple=True,
    default=(_DEFAULT_SYMBOL,),
    show_default=True,
    help="Symbol to search on. Passed through to search-signals.",
)
@click.option(
    "--windows",
    "windows_spec",
    default="2022,2023,2024,2025H1",
    show_default=True,
    help="Comma-separated window specs passed through to search-signals.",
)
@click.option(
    "--candle-timeframe",
    type=click.Choice(["15m", "1h", "4h"], case_sensitive=False),
    default="1h",
    hidden=True,
    help="Caller-supplied OHLCV timeframe.",
)
@click.option(
    "--n-trials",
    type=int,
    default=None,
    help="Per-algorithm candidate budget. Omit for endless resumable DSS matrix search.",
)
@click.option(
    "--n-jobs-per-algorithm",
    type=click.IntRange(min=1),
    default=1,
    hidden=True,
    help="Worker count passed to each child search-signals process.",
)
@click.option(
    "--algorithms",
    default="all",
    show_default=True,
    help="Comma-separated DSS algorithms to launch in parallel, or all.",
)
@click.option(
    "--catalog",
    type=click.Choice(["legacy", "pinescript_v1", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Trigger/filter catalog to search.",
)
@click.option("--output-root", default=None, help="Root directory for per-algorithm outputs.")
@click.option("--top-n", type=int, default=20, hidden=True)
@click.option("--min-trades", type=int, default=20, hidden=True)
@click.option("--min-signals-per-week", type=float, default=0.0, hidden=True)
@click.option(
    "--directional-min-wr",
    "directional_min_wr",
    type=click.FloatRange(min=0.0, max=1.0),
    default=0.45,
    show_default=True,
    help="Minimum directional barrier win rate required in each window.",
)
@click.option("--capital", type=float, default=10_000.0, hidden=True)
@click.option("--risk-base-period", default="monthly", hidden=True)
@click.option("--specialist-windows", default="", hidden=True)
def search_signals_matrix(
    data_dir: str,
    symbols: tuple[str, ...],
    windows_spec: str,
    candle_timeframe: str,
    n_trials: int | None,
    n_jobs_per_algorithm: int,
    algorithms: str,
    catalog: str,
    output_root: str | None,
    top_n: int,
    min_trades: int,
    min_signals_per_week: float,
    directional_min_wr: float,
    capital: float,
    risk_base_period: str,
    specialist_windows: str,
) -> None:
    """Launch several DSS search-signals algorithms concurrently."""
    parsed_algorithms = _parse_dss_matrix_algorithms(algorithms)
    _preflight_dss_matrix_candles(
        data_dir=data_dir,
        symbols=symbols,
        windows_spec=windows_spec,
        candle_timeframe=candle_timeframe,
        catalog=catalog,
    )
    if output_root is None:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_root = f"results/dss_matrix_{catalog.lower()}_directional_{ts}"
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    click.echo(
        "Launching DSS matrix: "
        f"{len(parsed_algorithms)} algorithms x {n_jobs_per_algorithm} jobs each "
        f"({len(parsed_algorithms) * n_jobs_per_algorithm} workers requested), "
        f"mode={'endless' if n_trials is None else f'bounded:{n_trials}'}"
    )
    click.echo(f"Output root: {root}")

    processes: list[tuple[str, Path, subprocess.Popen[bytes], IO[bytes]]] = []
    try:
        for algorithm in parsed_algorithms:
            seed = _DSS_MATRIX_DEFAULT_SEEDS[algorithm]
            output_dir = root / f"{algorithm}_seed{seed}"
            output_dir.mkdir(parents=True, exist_ok=True)
            log_path = output_dir / "run.log"
            cmd = [
                sys.executable,
                "-m",
                "backtester",
                "search-signals",
                "--data-dir",
                data_dir,
                "--windows",
                windows_spec,
                "--candle-timeframe",
                candle_timeframe,
                "--n-jobs",
                str(n_jobs_per_algorithm),
                "--algorithm",
                algorithm,
                "--catalog",
                catalog.lower(),
                "--seed",
                str(seed),
                "--output",
                str(output_dir),
                "--top-n",
                str(top_n),
                "--min-trades",
                str(min_trades),
                "--min-signals-per-week",
                str(min_signals_per_week),
                "--directional-min-wr",
                str(directional_min_wr),
                "--capital",
                str(capital),
                "--risk-base-period",
                risk_base_period,
                "--specialist-windows",
                specialist_windows,
            ]
            if n_trials is not None:
                cmd.extend(["--n-trials", str(n_trials)])
            for symbol in symbols:
                cmd.extend(["--symbol", symbol])

            log_file: IO[bytes] = log_path.open("wb")
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            processes.append((algorithm, log_path, process, log_file))
            click.echo(f"Started {algorithm} pid={process.pid} output={output_dir}")

        failures: list[str] = []
        for algorithm, log_path, process, log_file in processes:
            code = process.wait()
            log_file.close()
            status = "ok" if code == 0 else f"failed:{code}"
            click.echo(f"Finished {algorithm}: {status} log={log_path}")
            if code != 0:
                failures.append(f"{algorithm} exit={code} log={log_path}")

        if failures:
            raise click.ClickException("DSS matrix failures: " + "; ".join(failures))
    except KeyboardInterrupt:
        for _algorithm, _log_path, process, log_file in processes:
            if process.poll() is None:
                process.terminate()
            log_file.close()
        raise
    finally:
        for _algorithm, _log_path, process, log_file in processes:
            if process.poll() is not None and not log_file.closed:
                log_file.close()


@cli.command("search-signals")
@click.option(
    "--data-dir",
    default=_DEFAULT_DATA_DIR,
    show_default=True,
    help="Project data directory.",
)
@click.option(
    "--symbol",
    "symbols",
    multiple=True,
    default=(_DEFAULT_SYMBOL,),
    show_default=True,
    help="Symbol to search on. Repeatable: --symbol SOL-USDT-SWAP --symbol TON-USDT-SWAP",
)
@click.option(
    "--windows",
    "windows_spec",
    default="2022,2023,2024,2025H1",
    show_default=True,
    help="Comma-separated window specs: YYYY, YYYYH1/H2, or label:start:end.",
)
@click.option(
    "--candle-timeframe",
    type=click.Choice(["15m", "1h", "4h"], case_sensitive=False),
    default="1h",
    hidden=True,
    help="Caller-supplied OHLCV timeframe.",
)
@click.option(
    "--n-trials",
    type=int,
    default=None,
    help="Total candidate-generation budget. Omit for endless resumable search.",
)
@click.option("--n-jobs", type=int, default=1, hidden=True, help="Parallel workers where safe.")
@click.option("--max-filters", default=None, hidden=True)
@click.option("--sampler", default=None, hidden=True)
@click.option("--resume", "resume_journal", default=None, hidden=True)
@click.option(
    "--output",
    "output_dir",
    default=None,
    help="Output directory. Defaults to results/dss_{timestamp}/.",
)
@click.option(
    "--top-n",
    type=int,
    default=20,
    hidden=True,
    help="Top-N candidates to export as JSON.",
)
@click.option("--accept-min-score", default=None, hidden=True)
@click.option(
    "--algorithm",
    type=click.Choice(
        ["directional", "catcma_qd", "island_qd", "hyperband_qd", "smac_qd"], case_sensitive=False
    ),
    default="directional",
    show_default=True,
    help="DSS backend: directional, CatCMA-QD, Island-QD, Hyperband-QD, or SMAC-QD.",
)
@click.option(
    "--catalog",
    type=click.Choice(["legacy", "pinescript_v1", "all"], case_sensitive=False),
    default="legacy",
    show_default=True,
    help="Trigger/filter catalog to search.",
)
@click.option(
    "--seed",
    type=int,
    default=36,
    hidden=True,
    help="Candidate generator seed.",
)
@click.option(
    "--min-trades",
    type=int,
    default=20,
    hidden=True,
    help="Absolute min resolved directional signals per window; effective threshold also uses --min-signals-per-week.",
)
@click.option(
    "--min-signals-per-week",
    type=float,
    default=0.0,
    hidden=True,
    help="Min directional signal frequency per week in each window.",
)
@click.option(
    "--directional-min-wr",
    "directional_min_wr",
    type=click.FloatRange(min=0.0, max=1.0),
    default=None,
    show_default=True,
    help="Minimum directional barrier win rate required in each window.",
)
@click.option(
    "--capital",
    type=float,
    default=10_000.0,
    hidden=True,
    help="Initial capital for backtests.",
)
@click.option("--risk-base-period", default="monthly", hidden=True)
@click.option(
    "--specialist-windows",
    default="",
    hidden=True,
    help=(
        "Comma-separated window labels to preserve as specialist diagnostics. "
        "Empty keeps the fast all-window early-reject path."
    ),
)
def search_signals(
    data_dir: str,
    symbols: tuple[str, ...],
    windows_spec: str,
    candle_timeframe: str,
    n_trials: int | None,
    n_jobs: int,
    max_filters: str | None,
    sampler: str | None,
    resume_journal: str | None,
    output_dir: str | None,
    top_n: int,
    accept_min_score: str | None,
    algorithm: str,
    catalog: str,
    seed: int,
    min_trades: int,
    min_signals_per_week: float,
    directional_min_wr: float | None,
    capital: float,
    risk_base_period: str,
    specialist_windows: str,
) -> None:
    """Direct Signal Search v3: directional quality-diversity discovery.

    Searches trigger + filter signal candidates with directional labeling only.

    Example:

        backtester search-signals \\
            --data-dir data \\
            --symbol SOL-USDT-SWAP \\
            --windows 2022,2023,2024,2025H1 \\
            --n-trials 50000 \\
            --output results/dss_sol/
    """
    removed_options = {
        "--sampler": sampler,
        "--resume": resume_journal,
        "--accept-min-score": accept_min_score,
        "--max-filters": max_filters,
    }
    used_removed = [name for name, value in removed_options.items() if value is not None]
    if used_removed:
        raise click.ClickException(
            "DSS directional search removed the old Optuna sampler path; removed option(s): "
            f"{', '.join(used_removed)}. Use the simplified search-signals command."
        )

    previous_disable = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        raw_specs = [s.strip() for s in windows_spec.split(",") if s.strip()]
        dss_windows: list[DSSWindowSpec] = []
        multi_symbol = len(symbols) > 1
        for symbol in symbols:
            for raw in raw_specs:
                try:
                    parsed = DSSWindowSpec.parse(raw, symbol)
                except (ValueError, TypeError) as exc:
                    raise click.ClickException(f"Invalid window spec {raw!r}: {exc}") from exc
                if multi_symbol:
                    parsed = DSSWindowSpec(
                        label=f"{symbol}:{parsed.label}",
                        symbol=parsed.symbol,
                        start=parsed.start,
                        end=parsed.end,
                    )
                dss_windows.append(parsed)

        if not dss_windows:
            raise click.ClickException(f"No windows parsed from --windows {windows_spec!r}")
        raw_specialist_window_labels = tuple(
            label.strip() for label in specialist_windows.split(",") if label.strip()
        )
        if multi_symbol:
            specialist_window_labels = tuple(
                window.label
                for window in dss_windows
                if window.label in raw_specialist_window_labels
                or window.label.rsplit(":", 1)[-1] in raw_specialist_window_labels
            )
        else:
            specialist_window_labels = raw_specialist_window_labels
        unknown_specialist_windows = sorted(
            set(raw_specialist_window_labels)
            - {window.label for window in dss_windows}
            - {window.label.rsplit(":", 1)[-1] for window in dss_windows}
        )
        if unknown_specialist_windows:
            raise click.ClickException(
                "--specialist-windows contains labels not present in --windows: "
                + ", ".join(unknown_specialist_windows)
            )

        if output_dir is None:
            from datetime import UTC, datetime

            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            output_dir = f"results/dss_{ts}"
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        window_data: dict[str, StrategyData] = {}
        for spec in dss_windows:
            try:
                data_input = _load_discovery_window(
                    data_dir=data_dir,
                    candle_timeframe=candle_timeframe,
                    symbol=spec.symbol,
                    start=spec.start,
                    end=spec.end,
                )
            except (ValueError, FileNotFoundError) as exc:
                raise click.ClickException(f"Failed to load window {spec.label}: {exc}") from exc
            if isinstance(data_input, StrategyData):
                window_data[spec.label] = StrategyData(
                    candles_by_timeframe=data_input.candles_by_timeframe,
                    extras=data_input.extras,
                    metadata={
                        **data_input.metadata,
                        "symbol": spec.symbol,
                        "window_label": spec.label,
                    },
                    execution=data_input.execution,
                )
            else:
                window_data[spec.label] = StrategyData(
                    candles_by_timeframe={candle_timeframe: data_input},
                    extras={},
                    metadata={"symbol": spec.symbol, "window_label": spec.label},
                )

        search_space = _build_dss_search_space(catalog.lower())
        _validate_dss_required_candles(
            search_space=search_space,
            window_data=window_data,
            windows=dss_windows,
            data_dir=data_dir,
        )

        dss_config = DSSConfig(
            output=output_path,
            windows=dss_windows,
            n_trials=n_trials,
            n_jobs=n_jobs,
            max_filters=4,
            min_trades_per_window=min_trades,
            min_signals_per_week=min_signals_per_week,
            min_barrier_win_rate=directional_min_wr if directional_min_wr is not None else 0.45,
            top_n_candidates=top_n,
            initial_capital=capital,
            max_positions=0,
            risk_base_period=risk_base_period,
            specialist_windows=specialist_window_labels,
            catalog=cast(Literal["legacy", "pinescript_v1", "all"], catalog.lower()),
            algorithm=cast(
                Literal["directional", "catcma_qd", "island_qd", "hyperband_qd", "smac_qd"],
                algorithm.lower(),
            ),
            seed=seed,
        )

        if dss_config.algorithm == "catcma_qd":
            runner = run_catcma_qd_search
            label = "DSS CatCMA-QD"
        elif dss_config.algorithm == "island_qd":
            runner = run_island_qd_search
            label = "DSS Island-QD"
        elif dss_config.algorithm == "hyperband_qd":
            runner = run_hyperband_qd_search
            label = "DSS Hyperband-QD"
        elif dss_config.algorithm == "smac_qd":
            runner = run_smac_qd_search
            label = "DSS SMAC-QD"
        else:
            runner = run_dss_directional_search
            label = "DSS directional"
        if n_trials is None:
            click.echo(f"{label} endless mode; progress: {output_path / 'progress.json'}")
            try:
                runner(
                    config=dss_config,
                    search_space=search_space,
                    window_data=window_data,
                    progress_callback=None,
                )
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc
        else:
            progress_bar: Any = click.progressbar(length=n_trials, label=label, show_pos=True)
            with progress_bar as bar:
                try:
                    runner(
                        config=dss_config,
                        search_space=search_space,
                        window_data=window_data,
                        progress_callback=bar.update,
                    )
                except ValueError as exc:
                    raise click.ClickException(str(exc)) from exc
    finally:
        logging.disable(previous_disable)


def _dss_catalogs(
    catalog: str,
) -> tuple[
    dict[str, TriggerFactory],
    dict[str, FilterFactory],
    dict[str, dict[str, ParamDef]],
    dict[str, dict[str, ParamDef]],
]:
    legacy_triggers = parameterized_trigger_catalog()
    legacy_filters = parameterized_filter_catalog()
    legacy_trigger_params = parameterized_trigger_param_space()
    legacy_filter_params = parameterized_filter_param_space()
    ps_triggers = pinescript_trigger_catalog()
    ps_filters = pinescript_filter_catalog()
    ps_trigger_params = pinescript_trigger_param_space()
    ps_filter_params = pinescript_filter_param_space()
    if catalog == "legacy":
        return legacy_triggers, legacy_filters, legacy_trigger_params, legacy_filter_params
    if catalog == "pinescript_v1":
        return ps_triggers, ps_filters, ps_trigger_params, ps_filter_params
    if catalog == "all":
        return (
            {**legacy_triggers, **ps_triggers},
            {**legacy_filters, **ps_filters},
            {**legacy_trigger_params, **ps_trigger_params},
            {**legacy_filter_params, **ps_filter_params},
        )
    raise click.ClickException(f"Unknown DSS catalog: {catalog}")


if __name__ == "__main__":
    cli()
