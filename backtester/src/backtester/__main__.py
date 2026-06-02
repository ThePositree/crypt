import logging
import os

import click

from backtester.cli_runner import (
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
)

log_level = logging.getLevelNamesMapping().get(
    os.environ.get("LOG_LEVEL", "INFO"), logging.INFO
)

# Configure logging
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtester")


@click.group()
def cli():
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
@click.option("--ttl", type=int, default=0, help="Max position duration")
@click.option("--max-positions", type=int, default=0, help="Max simultaneous positions")
@click.option(
    "--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage"
)
@click.option("--ts-col", type=str, default="timestamp", help="timestamp column name")
@click.option(
    "--analyze-conditions",
    is_flag=True,
    help="Analyze trade conditions and find best predictors",
)
@click.option(
    "--top-predictors", type=int, default=10, help="Number of top predictors to show"
)
@click.option(
    "--create-visualizations",
    is_flag=True,
    help="Create visualizations for trade conditions analysis",
)
@click.option("--create-dashboard", is_flag=True, help="Create summary dashboard")
@click.option(
    "--is-isolated-futures", is_flag=True, help="Enable isolated futures mode"
)
@click.option(
    "--max-allowed-margin", type=float, default=1.0, help="Max allowed margin"
)
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
):
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
                parse_utc_datetime_to_ms(bingx_start_time)
                if bingx_start_time
                else None
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

if __name__ == "__main__":
    cli()
