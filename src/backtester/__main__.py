import logging
import os
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT_STR = str(_SRC_ROOT)
if _SRC_ROOT_STR in sys.path:
    sys.path.remove(_SRC_ROOT_STR)
# Console scripts do not inherit pytest's pythonpath setting; keep the project
# package ahead of the deprecated stdlib crypt module.
sys.path.insert(0, _SRC_ROOT_STR)

import click  # noqa: E402

from backtester.cli_runner import (  # noqa: E402
    OptimizerSearchArgs,
    build_backtest_args,
    build_cli_data_loader,
    build_strategy_instance,
    export_and_optional_analysis,
    load_ohlcv_via_loader,
    load_strategy_config,
    log_strategy_info,
    make_output_folder,
    parse_utc_datetime_to_ms,
    run_backtest,
    run_parameter_optimization,
)
from backtester.fixed_candidate_report import (  # noqa: E402
    FixedCandidateParams,
    parse_float_values,
    parse_int_values,
    parse_signal_quality_window_specs,
    parse_window_specs,
    run_execution_grid_comparison,
    run_fixed_candidate_comparison,
    run_signal_quality_diagnostics,
)
from backtester.trade_chart_report import (  # noqa: E402
    TradeChartReportConfig,
    build_trade_chart_report,
)

log_level = logging.getLevelNamesMapping().get(os.environ.get("LOG_LEVEL", "INFO"), logging.INFO)

# Configure logging
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtester")


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
    default="csv",
    help="Data source: csv, bingx, parquet, or crypt-parquet.",
)
@click.option(
    "--csv",
    default=None,
    help="Path to OHLCV CSV file (required if --data-source=csv)",
)
@click.option(
    "--parquet",
    default=None,
    help="Path to OHLCV Parquet file (required if --data-source=parquet)",
)
@click.option(
    "--data-dir",
    default=None,
    help="Project data directory (required if --data-source=crypt-parquet)",
)
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="4h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option(
    "--from",
    "from_date",
    default=None,
    help="Inclusive crypt-parquet start date/time in UTC.",
)
@click.option(
    "--to",
    "to_date",
    default=None,
    help="Inclusive crypt-parquet end date/time in UTC.",
)
@click.option("--symbol", default="SYMBOL/USDT", help="Trading pair name (for report)")
@click.option("--strategy", required=True, help="Strategy parameters file")
@click.option("--output", default="results/backtesting", help="Folder to save results")
@click.option("--capital", type=float, default=10000.0, help="Initial capital")
@click.option(
    "--risk-percent",
    type=float,
    default=1.0,
    help="Risk Percent (ignored if defined in strategy params)",
)
@click.option(
    "--rrr",
    type=float,
    default=2.0,
    help="Reward/Risk Ratio (ignored if defined in strategy params)",
)
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee")
@click.option(
    "--trail-activation-rrr",
    type=float,
    default=0.0,
    help="RRR threshold that activates trailing stop. 0 disables trailing.",
)
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=0, help="Max position duration")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage")
@click.option("--ts-col", type=str, default="timestamp", help="timestamp column name")
@click.option(
    "--analyze-conditions",
    is_flag=True,
    help="Analyze trade conditions and find best predictors",
)
@click.option("--top-predictors", type=int, default=10, help="Number of top predictors to show")
@click.option(
    "--create-visualizations",
    is_flag=True,
    help="Create visualizations for trade conditions analysis",
)
@click.option("--create-dashboard", is_flag=True, help="Create summary dashboard")
@click.option("--is-isolated-futures", is_flag=True, help="Enable isolated futures mode")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max allowed margin")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="trade",
    help="Capital window used for risk sizing.",
)
@click.option(
    "--max-daily-profit",
    type=float,
    default=None,
    help="Daily profit limit in RRR; disable new entries when exceeded.",
)
@click.option(
    "--max-daily-loss",
    type=float,
    default=None,
    help="Daily loss limit in RRR; disable new entries when exceeded.",
)
@click.option(
    "--trading-begin",
    type=int,
    default=None,
    help="Trading window start hour (0-23, UTC). Entries only when hour >= this.",
)
@click.option(
    "--trading-end",
    type=int,
    default=None,
    help="Trading window end hour (0-24, UTC). Entries only when hour < this.",
)
@click.option(
    "--bingx-symbol",
    type=str,
    default=None,
    help="BingX symbol, e.g. BTC-USDT (required if --data-source=bingx).",
)
@click.option(
    "--bingx-interval",
    type=str,
    default=None,
    help="BingX kline interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w (required if --data-source=bingx).",
)
@click.option(
    "--bingx-start-time",
    type=str,
    default=None,
    help="Start time UTC, format: YYYY-MM-DD HH:MM:SS (required if --data-source=bingx).",
)
@click.option(
    "--bingx-end-time",
    type=str,
    default=None,
    help="End time UTC, format: YYYY-MM-DD HH:MM:SS (required if --data-source=bingx).",
)
@click.option(
    "--bingx-api-key",
    type=str,
    default=None,
    help="BingX API key (required if --data-source=bingx).",
)
@click.option(
    "--bingx-api-secret",
    type=str,
    default=None,
    help="BingX API secret (required if --data-source=bingx).",
)
@click.option(
    "--bingx-base-url",
    type=str,
    default="https://open-api.bingx.com",
    help="BingX API base URL.",
)
@click.option(
    "--bingx-time-zone",
    type=int,
    default=0,
    help="BingX time zone offset (0 or 8).",
)
@click.option(
    "--bingx-recv-window",
    type=int,
    default=30000,
    help="BingX request valid time window in ms.",
)
@click.option(
    "--bingx-cache-dir",
    type=str,
    default=None,
    help="Optional directory path for caching BingX OHLCV responses on disk.",
)
def run(
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    primary_timeframe: str,
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
    trail_activation_rrr: float,
    trail_distance_atr: float,
    ttl: int,
    max_positions: int,
    max_allowed_leverage: float,
    ts_col: str,
    analyze_conditions: bool,
    top_predictors: int,
    create_visualizations: bool,
    create_dashboard: bool,
    is_isolated_futures: bool,
    max_allowed_margin: float,
    risk_base_period: str,
    max_daily_profit: float | None,
    max_daily_loss: float | None,
    trading_begin: int | None,
    trading_end: int | None,
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

    try:
        loader = build_cli_data_loader(
            data_source,
            csv_path=csv,
            parquet_path=parquet,
            data_dir=data_dir,
            symbol=symbol,
            primary_timeframe=primary_timeframe,
            start=from_date,
            end=to_date,
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
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    df = load_ohlcv_via_loader(loader, logger=logger)
    if df is None:
        return

    strategy_instance = build_strategy_instance(cfg.name, cfg.params, logger=logger)
    if strategy_instance is None:
        return

    args = build_backtest_args(
        cfg,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr,
        trail_activation_rrr=trail_activation_rrr,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
        max_positions=max_positions,
        max_allowed_leverage=max_allowed_leverage,
        is_isolated_futures=is_isolated_futures,
        max_allowed_margin=max_allowed_margin,
        risk_base_period=risk_base_period,
        max_daily_profit=max_daily_profit,
        max_daily_loss=max_daily_loss,
        trading_begin=trading_begin,
        trading_end=trading_end,
    )

    results = run_backtest(df=df, strategy=strategy_instance, args=args)

    results.print_report()

    output_folder = make_output_folder(output)
    export_and_optional_analysis(
        results=results,
        ohlcv_df=df,
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
    help="Data source: csv, parquet, or crypt-parquet.",
)
@click.option("--csv", default=None, help="Path to OHLCV CSV file.")
@click.option("--parquet", default=None, help="Path to OHLCV Parquet file.")
@click.option("--data-dir", default=None, help="Project data directory.")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="4h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option("--from", "from_date", default=None, help="Inclusive start UTC.")
@click.option("--to", "to_date", default=None, help="Inclusive end UTC.")
@click.option("--symbol", default="SYMBOL/USDT", help="Trading pair name.")
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option("--output", default="results/optimization", help="Folder for results.")
@click.option("--capital", type=float, default=10000.0, help="Initial capital.")
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--ttl", type=int, default=20, help="Fixed TTL if no TTL range.")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="trade",
    help="Capital window used for risk sizing.",
)
@click.option("--ts-col", type=str, default="timestamp", help="timestamp column name")
@click.option("--trials", type=int, default=25, help="Number of Optuna trials.")
@click.option("--study-name", default="optimization", help="Optuna study/log name.")
@click.option(
    "--target",
    type=click.Choice(
        ["total_return_pct", "profit_factor", "sharpe_ratio", "max_drawdown"],
        case_sensitive=False,
    ),
    default="total_return_pct",
    help="Objective metric.",
)
@click.option("--rrr-low", type=float, default=1.0, help="RRR search low bound.")
@click.option("--rrr-high", type=float, default=3.0, help="RRR search high bound.")
@click.option("--rrr-step", type=float, default=0.25, help="RRR search step.")
@click.option(
    "--trail-activation-rrr",
    type=float,
    default=0.0,
    help="Fixed trailing activation RRR when activation values are not provided.",
)
@click.option(
    "--trail-activation-rrr-values",
    default=None,
    help="Comma-separated trailing activation RRR values. Include 0 to test fixed TP.",
)
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Fixed trailing distance in ATR units when distance range is not provided.",
)
@click.option("--trail-distance-atr-low", type=float, default=None, help="Trail ATR low.")
@click.option("--trail-distance-atr-high", type=float, default=None, help="Trail ATR high.")
@click.option("--trail-distance-atr-step", type=float, default=0.5, help="Trail ATR step.")
@click.option(
    "--max-positions-values",
    default=None,
    help=(
        "Comma-separated max simultaneous positions values. "
        "Overrides max-positions low/high/step when set."
    ),
)
@click.option(
    "--max-positions-low",
    type=int,
    default=None,
    help="Max-positions search low bound.",
)
@click.option(
    "--max-positions-high",
    type=int,
    default=None,
    help="Max-positions search high bound.",
)
@click.option(
    "--max-positions-step",
    type=int,
    default=1,
    help="Max-positions search step.",
)
@click.option("--ttl-low", type=int, default=None, help="TTL search low bound.")
@click.option("--ttl-high", type=int, default=None, help="TTL search high bound.")
@click.option("--ttl-step", type=int, default=1, help="TTL search step.")
@click.option(
    "--risk-percent",
    type=float,
    default=1.0,
    help="Fixed risk percent when risk search is disabled.",
)
@click.option("--risk-percent-low", type=float, default=None, help="Risk search low.")
@click.option("--risk-percent-high", type=float, default=None, help="Risk search high.")
@click.option("--risk-percent-step", type=float, default=0.1, help="Risk search step.")
@click.option(
    "--strategy-param-search/--no-strategy-param-search",
    default=False,
    help="Allow strategy.suggest_params() during optimization.",
)
@click.option(
    "--daily-limit-search/--no-daily-limit-search",
    default=False,
    help="Optimize max daily profit/loss limits.",
)
@click.option(
    "--trading-window-search/--no-trading-window-search",
    default=False,
    help="Optimize trading window hours.",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show Optuna progress bar.",
)
@click.option(
    "--export-best-run/--no-export-best-run",
    default=True,
    help="Export best-run diagnostics after optimization.",
)
@click.option("--is-isolated-futures", is_flag=True, help="Enable isolated futures.")
def optimize(
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    primary_timeframe: str,
    from_date: str | None,
    to_date: str | None,
    symbol: str,
    strategy: str,
    output: str,
    capital: float,
    maker_fee: float,
    taker_fee: float,
    ttl: int,
    max_positions: int,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    ts_col: str,
    trials: int,
    study_name: str,
    target: str,
    rrr_low: float,
    rrr_high: float,
    rrr_step: float,
    trail_activation_rrr: float,
    trail_activation_rrr_values: str | None,
    trail_distance_atr: float,
    trail_distance_atr_low: float | None,
    trail_distance_atr_high: float | None,
    trail_distance_atr_step: float,
    max_positions_values: str | None,
    max_positions_low: int | None,
    max_positions_high: int | None,
    max_positions_step: int,
    ttl_low: int | None,
    ttl_high: int | None,
    ttl_step: int,
    risk_percent: float,
    risk_percent_low: float | None,
    risk_percent_high: float | None,
    risk_percent_step: float,
    strategy_param_search: bool,
    daily_limit_search: bool,
    trading_window_search: bool,
    progress: bool,
    export_best_run: bool,
    is_isolated_futures: bool,
) -> None:
    """Run bounded parameter optimization via the donor ParameterOptimizer."""
    logger.info("🚀 Starting optimization via CLI...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)

    try:
        loader = build_cli_data_loader(
            data_source,
            csv_path=csv,
            parquet_path=parquet,
            data_dir=data_dir,
            symbol=symbol,
            primary_timeframe=primary_timeframe,
            start=from_date,
            end=to_date,
            ts_col=ts_col,
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    df = load_ohlcv_via_loader(loader, logger=logger)
    if df is None:
        return

    backtest_args = build_backtest_args(
        cfg,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr_low,
        trail_activation_rrr=trail_activation_rrr,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
        max_positions=max_positions,
        max_allowed_leverage=max_allowed_leverage,
        is_isolated_futures=is_isolated_futures,
        max_allowed_margin=max_allowed_margin,
        risk_base_period=risk_base_period,
        max_daily_profit=None,
        max_daily_loss=None,
        trading_begin=None,
        trading_end=None,
    )
    if risk_percent_low is None or risk_percent_high is None:
        risk_percent_range = None
    else:
        risk_percent_range = (
            risk_percent_low,
            risk_percent_high,
            risk_percent_step,
        )
    ttl_range = None if ttl_low is None or ttl_high is None else (ttl_low, ttl_high, ttl_step)
    if max_positions_low is None or max_positions_high is None:
        max_positions_range = None
    else:
        max_positions_range = (
            max_positions_low,
            max_positions_high,
            max_positions_step,
        )
    if trail_distance_atr_low is None or trail_distance_atr_high is None:
        trail_distance_atr_range = None
    else:
        trail_distance_atr_range = (
            trail_distance_atr_low,
            trail_distance_atr_high,
            trail_distance_atr_step,
        )
    try:
        parsed_max_positions_values = (
            tuple(parse_int_values(max_positions_values))
            if max_positions_values is not None
            else None
        )
        parsed_trail_activation_rrr_values = (
            tuple(parse_float_values(trail_activation_rrr_values))
            if trail_activation_rrr_values is not None
            else None
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    output_folder = make_output_folder(output)
    run_parameter_optimization(
        df=df,
        cfg=cfg,
        backtest_args=backtest_args,
        optimizer_args=OptimizerSearchArgs(
            trials=trials,
            study_name=study_name,
            target=target,
            show_progress=progress,
            optimize_strategy_params=strategy_param_search,
            risk_percent_range=risk_percent_range,
            rrr_range=(rrr_low, rrr_high, rrr_step),
            trail_activation_rrr_values=parsed_trail_activation_rrr_values,
            trail_distance_atr_range=trail_distance_atr_range,
            max_positions_values=parsed_max_positions_values,
            max_positions_range=max_positions_range,
            position_ttl_bars_range=ttl_range,
            optimize_daily_limits=daily_limit_search,
            optimize_trading_window=trading_window_search,
            export_best_run=export_best_run,
        ),
        output_folder=output_folder,
        logger=logger,
    )


@cli.command("compare-fixed")
@click.option("--data-dir", required=True, help="Project data directory.")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="1h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option(
    "--window",
    "windows",
    multiple=True,
    help=(
        "Window as label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD. "
        "May be repeated; defaults to SOL Jan/Feb/Mar and TON Jan/Feb 2025."
    ),
)
@click.option("--output", default="results/fixed_candidate", help="Folder for results.")
@click.option("--capital", type=float, default=10000.0, help="Initial capital.")
@click.option("--risk-percent", type=float, default=1.0, help="Fixed risk percent.")
@click.option("--rrr", type=float, default=1.25, help="Fixed reward/risk ratio.")
@click.option(
    "--trail-activation-rrr",
    type=float,
    default=0.0,
    help="RRR threshold that activates trailing stop. 0 disables trailing.",
)
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=36, help="Fixed position TTL in bars.")
@click.option(
    "--jobs",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Parallel fixed-window workers.",
)
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
@click.option("--is-isolated-futures", is_flag=True, help="Enable isolated futures.")
def compare_fixed(
    data_dir: str,
    primary_timeframe: str,
    strategy: str,
    windows: tuple[str, ...],
    output: str,
    capital: float,
    risk_percent: float,
    rrr: float,
    trail_activation_rrr: float,
    trail_distance_atr: float,
    ttl: int,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_positions: int,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    is_isolated_futures: bool,
) -> None:
    """Run fixed candidate backtests across bounded windows and summarize them."""
    logger.info("🚀 Starting fixed-candidate comparison...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    try:
        window_specs = parse_window_specs(windows)
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    output_folder = make_output_folder(output)
    summary = run_fixed_candidate_comparison(
        windows=window_specs,
        cfg=cfg,
        params=FixedCandidateParams(
            capital=capital,
            risk_percent=risk_percent,
            rrr=rrr,
            trail_activation_rrr=trail_activation_rrr,
            trail_distance_atr=trail_distance_atr,
            ttl=ttl,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=max_positions,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            is_isolated_futures=is_isolated_futures,
        ),
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        output_folder=output_folder,
        jobs=jobs,
        logger=logger,
    )
    logger.info("Completed %d fixed-candidate windows", len(summary))


@cli.command("compare-grid")
@click.option("--data-dir", required=True, help="Project data directory.")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="1h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option(
    "--window",
    "windows",
    multiple=True,
    help=(
        "Window as label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD. "
        "May be repeated; defaults to SOL Jan/Feb/Mar and TON Jan/Feb 2025."
    ),
)
@click.option("--output", default="results/execution_grid", help="Folder for results.")
@click.option("--capital", type=float, default=10000.0, help="Initial capital.")
@click.option("--risk-percent", type=float, default=1.0, help="Fixed risk percent.")
@click.option(
    "--rrr-values",
    default="1.0,1.25,1.5",
    show_default=True,
    help="Comma-separated reward/risk values.",
)
@click.option(
    "--ttl-values",
    default="30,36,42",
    show_default=True,
    help="Comma-separated position TTL values in bars.",
)
@click.option(
    "--trail-activation-rrr-values",
    default="0",
    show_default=True,
    help="Comma-separated trailing activation RRR values. 0 disables trailing.",
)
@click.option(
    "--trail-distance-atr-values",
    default="0",
    show_default=True,
    help="Comma-separated trailing distance ATR values.",
)
@click.option(
    "--max-positions-values",
    default=None,
    help=("Comma-separated max simultaneous positions values. Defaults to fixed --max-positions."),
)
@click.option(
    "--jobs",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Parallel grid workers.",
)
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
@click.option("--is-isolated-futures", is_flag=True, help="Enable isolated futures.")
def compare_grid(
    data_dir: str,
    primary_timeframe: str,
    strategy: str,
    windows: tuple[str, ...],
    output: str,
    capital: float,
    risk_percent: float,
    rrr_values: str,
    ttl_values: str,
    trail_activation_rrr_values: str,
    trail_distance_atr_values: str,
    max_positions_values: str | None,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_positions: int,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    is_isolated_futures: bool,
) -> None:
    """Run a tiny execution-only rrr/ttl/max_positions grid across bounded windows."""
    logger.info("🚀 Starting execution-grid comparison...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    try:
        window_specs = parse_window_specs(windows)
        parsed_rrr_values = parse_float_values(rrr_values)
        parsed_ttl_values = parse_int_values(ttl_values)
        parsed_trail_activation_rrr_values = parse_float_values(trail_activation_rrr_values)
        parsed_trail_distance_atr_values = parse_float_values(trail_distance_atr_values)
        parsed_max_positions_values = (
            parse_int_values(max_positions_values)
            if max_positions_values is not None
            else [max_positions]
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    output_folder = make_output_folder(output)
    summary = run_execution_grid_comparison(
        windows=window_specs,
        cfg=cfg,
        base_params=FixedCandidateParams(
            capital=capital,
            risk_percent=risk_percent,
            rrr=parsed_rrr_values[0],
            trail_activation_rrr=parsed_trail_activation_rrr_values[0],
            trail_distance_atr=parsed_trail_distance_atr_values[0],
            ttl=parsed_ttl_values[0],
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=max_positions,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            is_isolated_futures=is_isolated_futures,
        ),
        rrr_values=parsed_rrr_values,
        ttl_values=parsed_ttl_values,
        trail_activation_rrr_values=parsed_trail_activation_rrr_values,
        trail_distance_atr_values=parsed_trail_distance_atr_values,
        max_positions_values=parsed_max_positions_values,
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        output_folder=output_folder,
        jobs=jobs,
        logger=logger,
    )
    logger.info("Completed %d execution-grid candidates", len(summary))


@cli.command("signal-quality")
@click.option("--data-dir", required=True, help="Project data directory.")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="1h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option(
    "--window",
    "windows",
    multiple=True,
    help=(
        "Window as label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD. May be repeated; "
        "defaults to SOL Jan/Feb/Mar and TON Jan/Feb/Mar/Apr 2025."
    ),
)
@click.option("--output", default="results/signal_quality", help="Folder for diagnostics.")
@click.option("--capital", type=float, default=10000.0, help="Initial capital.")
@click.option("--risk-percent", type=float, default=1.0, help="Fixed risk percent.")
@click.option("--rrr", type=float, default=1.25, help="Fixed reward/risk ratio.")
@click.option(
    "--trail-activation-rrr",
    type=float,
    default=0.0,
    help="RRR threshold that activates trailing stop. 0 disables trailing.",
)
@click.option(
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=36, help="Fixed position TTL in bars.")
@click.option(
    "--jobs",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Parallel diagnostic workers.",
)
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
@click.option("--is-isolated-futures", is_flag=True, help="Enable isolated futures.")
def signal_quality(
    data_dir: str,
    primary_timeframe: str,
    strategy: str,
    windows: tuple[str, ...],
    output: str,
    capital: float,
    risk_percent: float,
    rrr: float,
    trail_activation_rrr: float,
    trail_distance_atr: float,
    ttl: int,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_positions: int,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    is_isolated_futures: bool,
) -> None:
    """Run report-only H1 signal-quality diagnostics across bounded windows."""
    logger.info("🚀 Starting signal-quality diagnostics...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    try:
        window_specs = parse_signal_quality_window_specs(windows)
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    output_folder = make_output_folder(output)
    signals, groups, setup_attribution = run_signal_quality_diagnostics(
        windows=window_specs,
        cfg=cfg,
        params=FixedCandidateParams(
            capital=capital,
            risk_percent=risk_percent,
            rrr=rrr,
            trail_activation_rrr=trail_activation_rrr,
            trail_distance_atr=trail_distance_atr,
            ttl=ttl,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=max_positions,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            is_isolated_futures=is_isolated_futures,
        ),
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        output_folder=output_folder,
        jobs=jobs,
        logger=logger,
    )
    logger.info(
        "Completed signal-quality diagnostics: %d windows, %d groups, %d setup attribution rows",
        len(signals),
        len(groups),
        len(setup_attribution),
    )


@cli.command("trade-chart")
@click.option("--run-dir", required=True, help="Completed run directory with trades.csv.")
@click.option(
    "--output", default=None, help="HTML output path. Defaults to run-dir/trade_chart.html."
)
@click.option(
    "--ohlcv",
    default=None,
    help="Optional full OHLCV CSV or Parquet file. Defaults to run-dir/ohlcv.csv.",
)
@click.option("--timestamp-col", default="timestamp", help="OHLCV timestamp column.")
@click.option("--title", default=None, help="Report title.")
def trade_chart(
    run_dir: str,
    output: str | None,
    ohlcv: str | None,
    timestamp_col: str,
    title: str | None,
) -> None:
    """Regenerate the interactive TradingView trade chart for a run artifact."""
    logger.info("🚀 Building trade chart report...")
    try:
        output_path = build_trade_chart_report(
            TradeChartReportConfig(
                run_dir=Path(run_dir),
                output_path=Path(output) if output else None,
                ohlcv_path=Path(ohlcv) if ohlcv else None,
                timestamp_col=timestamp_col,
                title=title,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        logger.error("❌ %s", e)
        return
    logger.info("Trade chart report saved to: %s", output_path)


if __name__ == "__main__":
    cli()
