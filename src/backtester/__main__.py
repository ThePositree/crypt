import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Literal, cast

_SRC_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT_STR = str(_SRC_ROOT)
if _SRC_ROOT_STR in sys.path:
    sys.path.remove(_SRC_ROOT_STR)
# Console scripts do not inherit pytest's pythonpath setting; keep the project
# package ahead of the deprecated stdlib crypt module.
sys.path.insert(0, _SRC_ROOT_STR)

import click  # noqa: E402
import pandas as pd  # noqa: E402
from tqdm.auto import tqdm  # noqa: E402

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
from backtester.data_contracts import StrategyData, StrategyInput  # noqa: E402
from backtester.fixed_candidate_report import (  # noqa: E402
    FixedCandidateParams,
    WindowSpec,
    parse_float_values,
    parse_int_values,
    parse_signal_quality_window_specs,
    parse_window_spec,
    parse_window_specs,
    run_execution_grid_comparison,
    run_fixed_candidate_comparison,
    run_signal_quality_diagnostics,
)
from backtester.negative_oracle_research import (  # noqa: E402
    NegativeOracleConfig,
    run_negative_oracle_research,
)
from backtester.regime_labels import (  # noqa: E402
    build_oracle_label_dataset,
    build_rolling_label_dataset,
    write_oracle_label_outputs,
    write_rolling_label_outputs,
)
from backtester.regime_matrix import (  # noqa: E402
    MatrixBacktestCliParams,
    run_archived_performance_matrix,
)
from backtester.regime_router import (  # noqa: E402
    RouterConfig,
    RouterSearchConfig,
    count_router_candidates,
    evaluate_rolling_router_baselines,
    evaluate_single_strategy_router_search,
    write_rolling_router_report,
    write_single_strategy_router_search_report,
)
from backtester.routed_execution import (  # noqa: E402
    RoutedExecutionConfig,
    evaluate_routed_execution,
    load_matrix_strategy_trades,
    write_routed_execution_report,
)
from backtester.strategy_discovery import (  # noqa: E402
    DiscoveryConfig,
    DiscoveryConversionError,
    DiscoveryWindow,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    load_and_convert_discovery_strategy,
    parameterized_filter_catalog,
    parameterized_trigger_catalog,
    parameterized_trigger_param_space,
    pinescript_filter_catalog,
    pinescript_filter_param_space,
    pinescript_trigger_catalog,
    pinescript_trigger_param_space,
    run_catcma_qd_search,
    run_dss_v2_search,
    run_hyperband_qd_search,
    run_island_qd_search,
    run_smac_qd_search,
    run_strategy_discovery,
)
from backtester.strategy_discovery.dss_config import ParamDef  # noqa: E402
from backtester.strategy_discovery.filters import filter_catalog  # noqa: E402
from backtester.strategy_discovery.parameterized_filters import (  # noqa: E402
    FilterFactory,
    parameterized_filter_param_space,
)
from backtester.strategy_discovery.parameterized_triggers import TriggerFactory  # noqa: E402
from backtester.strategy_discovery.triggers import trigger_catalog  # noqa: E402
from backtester.trade_chart_report import (  # noqa: E402
    TradeChartReportConfig,
    build_trade_chart_report,
)
from backtester.trade_filter_research import (  # noqa: E402
    FilterSearchConfig,
    SplitConfig,
    run_trade_filter_research,
)
from backtester.walk_forward import (  # noqa: E402
    generate_windows,
    run_walk_forward,
    write_walk_forward_report,
)

log_level = logging.getLevelNamesMapping().get(os.environ.get("LOG_LEVEL", "INFO"), logging.INFO)

# Configure logging
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtester")

_DSS_MATRIX_DEFAULT_SEEDS = {
    "staged": 73023,
    "catcma_qd": 777,
    "island_qd": 2026,
    "hyperband_qd": 4242,
    "smac_qd": 5151,
}
_ROUTER_MATRIX_DEFAULT_SEEDS = {
    "random": 1101,
    "island_qd": 2202,
    "hyperband_qd": 3303,
    "smac_qd": 4404,
}


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
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=0, help="Max position duration")
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
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max allowed margin")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="trade",
    help="Capital window used for risk sizing.",
)
@click.option(
    "--capital-sweep",
    type=click.Choice(["none", "monthly_profit", "trade_profit"], case_sensitive=False),
    default="none",
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
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    help="Exit placement: structural SL+RRR (default) or TP-first percent.",
)
@click.option(
    "--tp-move-pct",
    type=float,
    default=None,
    help="Target gross TP price move decimal (0.015 = 1.5%). Required for tp_pct.",
)
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    help="How structural sl_price constrains TP-first SL.",
)
@click.option(
    "--min-tp-move-pct",
    type=float,
    default=0.004,
    help="Skip entries when tp_move_pct is below this breakeven floor.",
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
    trail_distance_atr: float,
    ttl: int,
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
            load_execution_1m=cfg.backtest_args.get("intrabar_execution_timeframe") == "1m",
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

    if exit_geometry.lower() == "tp_pct" and tp_move_pct is None:
        logger.error("❌ --tp-move-pct is required when --exit-geometry=tp_pct")
        return

    args = build_backtest_args(
        cfg,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr,
        trail_activation_rrr=rrr if trail_distance_atr > 0 else 0.0,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
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


@cli.command("archived-performance-matrix")
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
    default="1h",
    help="Primary execution timeframe for crypt-parquet data.",
)
@click.option("--from", "from_date", default=None, help="Inclusive start UTC.")
@click.option("--to", "to_date", default=None, help="Inclusive end UTC.")
@click.option("--symbol", default="SYMBOL/USDT", help="Trading pair name.")
@click.option(
    "--strategy",
    "strategy_paths",
    multiple=True,
    help="Strategy JSON to include. Repeatable.",
)
@click.option(
    "--include-archive/--no-include-archive",
    default=True,
    show_default=True,
    help="Include every JSON under strategies/archive/.",
)
@click.option(
    "--archive-dir",
    default="strategies/archive",
    show_default=True,
    help="Archive strategy directory used by --include-archive.",
)
@click.option(
    "--bucket",
    type=click.Choice(["day", "week", "month"], case_sensitive=False),
    default="month",
    show_default=True,
    help="Matrix bucket size.",
)
@click.option(
    "--strategy-progress/--no-strategy-progress",
    default=True,
    show_default=True,
    help="Allow strategy-level progress bars when supported by the strategy config.",
)
@click.option(
    "--jobs",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Parallel matrix strategy workers.",
)
@click.option("--output", default=None, help="Output directory.")
@click.option("--capital", type=float, default=10000.0, show_default=True)
@click.option("--maker-fee", type=float, default=0.0002, show_default=True)
@click.option("--taker-fee", type=float, default=0.0005, show_default=True)
@click.option("--max-allowed-leverage", type=float, default=25.0, show_default=True)
@click.option("--max-allowed-margin", type=float, default=1.0, show_default=True)
@click.option("--ts-col", type=str, default="timestamp", help="Timestamp column name.")
def archived_performance_matrix(
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    primary_timeframe: str,
    from_date: str | None,
    to_date: str | None,
    symbol: str,
    strategy_paths: tuple[str, ...],
    include_archive: bool,
    archive_dir: str,
    bucket: str,
    strategy_progress: bool,
    jobs: int,
    output: str | None,
    capital: float,
    maker_fee: float,
    taker_fee: float,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    ts_col: str,
) -> None:
    """Build a time x strategy performance matrix for regime research."""

    paths = _collect_matrix_strategy_paths(strategy_paths, include_archive, Path(archive_dir))
    if not paths:
        raise click.ClickException("No strategy JSONs selected")

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
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    data = load_ohlcv_via_loader(loader, logger=logger)
    if data is None:
        raise click.ClickException("Failed to load OHLCV data")

    if output is None:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output = f"results/regime_matrix_{symbol.lower().replace('-', '_')}_{bucket}_{ts}"
    output_path = Path(output)

    try:
        run_archived_performance_matrix(
            paths=paths,
            data=data,
            output=output_path,
            bucket=bucket,
            from_date=from_date,
            to_date=to_date,
            jobs=jobs,
            cli_params=MatrixBacktestCliParams(
                capital=capital,
                maker_fee=maker_fee,
                taker_fee=taker_fee,
                max_allowed_leverage=max_allowed_leverage,
                max_allowed_margin=max_allowed_margin,
            ),
            strategy_progress=strategy_progress,
            logger=logger,
            on_strategy_start=lambda strategy_id, strategy_path: click.echo(
                f"Matrix strategy starting: {strategy_id} path={strategy_path}"
            ),
            on_strategy_done=lambda strategy_id, trade_count: click.echo(
                f"Matrix strategy done: {strategy_id} trades={trade_count}"
            ),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Matrix saved to: {output_path}")


def _collect_matrix_strategy_paths(
    explicit_paths: tuple[str, ...], include_archive: bool, archive_dir: Path
) -> list[Path]:
    paths: list[Path] = []
    if include_archive and archive_dir.exists():
        paths.extend(sorted(archive_dir.glob("*.json")))
    paths.extend(Path(path) for path in explicit_paths)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


@cli.command("oracle-regime-labels")
@click.option(
    "--matrix-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory produced by archived-performance-matrix.",
)
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
    default="1h",
    help="Primary timeframe for crypt-parquet data.",
)
@click.option("--symbol", default="SOL-USDT-SWAP", help="Trading pair name.")
@click.option("--from", "from_date", default=None, help="Inclusive start UTC.")
@click.option("--to", "to_date", default=None, help="Inclusive end UTC.")
@click.option(
    "--bucket",
    type=click.Choice(["day", "week", "month"], case_sensitive=False),
    default="month",
    help="Bucket size used by the matrix.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <matrix-dir>/oracle_labels.",
)
@click.option("--ts-col", type=str, default="timestamp", help="CSV/parquet timestamp column.")
def oracle_regime_labels(
    matrix_dir: Path,
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    primary_timeframe: str,
    symbol: str,
    from_date: str | None,
    to_date: str | None,
    bucket: str,
    output: Path | None,
    ts_col: str,
) -> None:
    """Build an offline oracle label dataset from a regime matrix."""

    return_path = matrix_dir / "matrix_return_pct.csv"
    if not return_path.exists():
        raise click.ClickException(f"Missing matrix return file: {return_path}")

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
        raise click.ClickException(str(e)) from e

    data = load_ohlcv_via_loader(loader, logger=logger)
    if data is None:
        raise click.ClickException("Could not load OHLCV data")
    ohlcv = data.primary if isinstance(data, StrategyData) else data

    return_matrix = pd.read_csv(return_path)
    dataset = build_oracle_label_dataset(
        return_matrix=return_matrix,
        ohlcv=ohlcv,
        bucket=bucket,
    )
    output_path = output if output is not None else matrix_dir / "oracle_labels"
    write_oracle_label_outputs(output=output_path, dataset=dataset)
    click.echo(f"Oracle labels saved to: {output_path}")


@cli.command("rolling-regime-labels")
@click.option(
    "--matrix-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory produced by archived-performance-matrix with strategy_trades/.",
)
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
    default="1h",
    help="Primary timeframe for crypt-parquet data.",
)
@click.option("--symbol", default="SOL-USDT-SWAP", help="Trading pair name.")
@click.option("--from", "from_date", default=None, help="Inclusive feature start UTC.")
@click.option("--to", "to_date", default=None, help="Inclusive feature end UTC.")
@click.option(
    "--step",
    type=click.Choice(["day", "hour"], case_sensitive=False),
    default="day",
    show_default=True,
    help="Feature row cadence.",
)
@click.option(
    "--horizon-days",
    type=int,
    default=30,
    show_default=True,
    help="Forward label horizon in calendar days.",
)
@click.option(
    "--min-history-days",
    type=int,
    default=90,
    show_default=True,
    help="Minimum prior OHLCV history required before emitting a row.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <matrix-dir>/rolling_labels_<step>_<horizon>d.",
)
@click.option("--ts-col", type=str, default="timestamp", help="CSV/parquet timestamp column.")
def rolling_regime_labels(
    matrix_dir: Path,
    data_source: str,
    csv: str | None,
    parquet: str | None,
    data_dir: str | None,
    primary_timeframe: str,
    symbol: str,
    from_date: str | None,
    to_date: str | None,
    step: str,
    horizon_days: int,
    min_history_days: int,
    output: Path | None,
    ts_col: str,
) -> None:
    """Build rolling forward labels from matrix strategy trade exports."""

    trades_dir = matrix_dir / "strategy_trades"
    if not trades_dir.exists():
        raise click.ClickException(f"Missing strategy trade directory: {trades_dir}")

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
        raise click.ClickException(str(e)) from e

    data = load_ohlcv_via_loader(loader, logger=logger)
    if data is None:
        raise click.ClickException("Could not load OHLCV data")
    ohlcv = data.primary if isinstance(data, StrategyData) else data

    dataset = build_rolling_label_dataset(
        trades_dir=trades_dir,
        ohlcv=ohlcv,
        step=step,
        horizon_days=horizon_days,
        min_history_days=min_history_days,
        start=from_date,
        end=to_date,
    )
    output_path = output or matrix_dir / f"rolling_labels_{step}_{horizon_days}d"
    write_rolling_label_outputs(
        output=output_path,
        dataset=dataset,
        step=step,
        horizon_days=horizon_days,
    )
    click.echo(f"Rolling labels saved to: {output_path}")


@cli.command("rolling-router-baseline")
@click.option(
    "--labels",
    "labels_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to rolling_labels.csv.",
)
@click.option(
    "--validation-start",
    default="2024-01-01",
    show_default=True,
    help="First as-of timestamp to score.",
)
@click.option(
    "--min-available-strategies",
    type=int,
    default=3,
    show_default=True,
    help="Minimum strategies that must cover the label window.",
)
@click.option(
    "--lookback-days",
    type=int,
    default=365,
    show_default=True,
    help="Prior completed-label history used by rolling routers.",
)
@click.option(
    "--knn-k",
    type=int,
    default=7,
    show_default=True,
    help="Neighbors for the feature KNN diagnostic router.",
)
@click.option(
    "--non-overlap-days",
    type=int,
    default=30,
    show_default=True,
    help="Spacing for portfolio-style non-overlap scoring.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <labels-dir>/router_baseline.",
)
def rolling_router_baseline(
    labels_path: Path,
    validation_start: str,
    min_available_strategies: int,
    lookback_days: int,
    knn_k: int,
    non_overlap_days: int,
    output: Path | None,
) -> None:
    """Evaluate simple live-safe routers over rolling regime labels."""

    labels = pd.read_csv(labels_path)
    config = RouterConfig(
        validation_start=validation_start,
        min_available_strategies=min_available_strategies,
        lookback_days=lookback_days,
        knn_k=knn_k,
        non_overlap_days=non_overlap_days,
    )
    dense, summary, non_overlap = evaluate_rolling_router_baselines(labels, config=config)
    output_path = output or labels_path.parent / "router_baseline"
    write_rolling_router_report(
        output=output_path,
        dense=dense,
        summary=summary,
        non_overlap=non_overlap,
        config=config,
    )
    click.echo(f"Rolling router baseline saved to: {output_path}")


@cli.command("router-search-matrix")
@click.option(
    "--labels",
    "labels_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to rolling_labels.csv.",
)
@click.option("--validation-start", default="2024-01-01", show_default=True)
@click.option(
    "--validation-end",
    default=None,
    help="Exclusive final as-of timestamp; use to preserve a holdout period.",
)
@click.option("--min-available-strategies", type=int, default=6, show_default=True)
@click.option(
    "--algorithms",
    default="random,island_qd,hyperband_qd,smac_qd",
    show_default=True,
    help="Comma-separated router search backends.",
)
@click.option("--max-configs", type=int, default=25_000, show_default=True)
@click.option("--proposal-multiplier", type=int, default=8, show_default=True)
@click.option("--top-predictions", type=int, default=30, show_default=True)
@click.option(
    "--output-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Root output directory.",
)
def router_search_matrix(
    labels_path: Path,
    validation_start: str,
    validation_end: str | None,
    min_available_strategies: int,
    algorithms: str,
    max_configs: int,
    proposal_multiplier: int,
    top_predictions: int,
    output_root: Path | None,
) -> None:
    """Launch several Router Catalog v2 algorithms concurrently."""

    parsed = [value.strip().lower() for value in algorithms.split(",") if value.strip()]
    unknown = sorted(set(parsed) - set(_ROUTER_MATRIX_DEFAULT_SEEDS))
    if unknown:
        raise click.ClickException("Unknown router algorithms: " + ", ".join(unknown))
    if not parsed:
        raise click.ClickException("No router algorithms selected")
    if output_root is None:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_root = Path(f"results/router_matrix_v2_{ts}")
    output_root.mkdir(parents=True, exist_ok=True)

    processes: list[tuple[str, Path, subprocess.Popen[bytes], IO[bytes]]] = []
    try:
        for progress_position, algorithm in enumerate(parsed):
            seed = _ROUTER_MATRIX_DEFAULT_SEEDS[algorithm]
            output = output_root / f"{algorithm}_seed{seed}"
            output.mkdir(parents=True, exist_ok=True)
            log_path = output / "run.log"
            command = [
                sys.executable,
                "-m",
                "backtester",
                "router-search",
                "--labels",
                str(labels_path),
                "--validation-start",
                validation_start,
                "--min-available-strategies",
                str(min_available_strategies),
                "--catalog-version",
                "v2",
                "--algorithm",
                algorithm,
                "--seed",
                str(seed),
                "--proposal-multiplier",
                str(proposal_multiplier),
                "--summary-only",
                "--top-predictions",
                str(top_predictions),
                "--progress-position",
                str(progress_position),
                "--max-configs",
                str(max_configs),
                "--output",
                str(output),
            ]
            if validation_end is not None:
                command.extend(["--validation-end", validation_end])
            log_file = log_path.open("wb")
            process = subprocess.Popen(command, stdout=log_file)
            processes.append((algorithm, log_path, process, log_file))
            click.echo(f"Started {algorithm} pid={process.pid} output={output}")

        failures = []
        for algorithm, log_path, process, log_file in processes:
            code = process.wait()
            log_file.close()
            click.echo(f"Finished {algorithm}: exit={code} log={log_path}")
            if code != 0:
                failures.append(f"{algorithm} exit={code} log={log_path}")
        if failures:
            raise click.ClickException("Router matrix failures: " + "; ".join(failures))
    except KeyboardInterrupt:
        for _algorithm, _log_path, process, log_file in processes:
            if process.poll() is None:
                process.terminate()
            if not log_file.closed:
                log_file.close()
        raise
    finally:
        for _algorithm, _log_path, process, log_file in processes:
            if process.poll() is not None and not log_file.closed:
                log_file.close()


@cli.command("router-search")
@click.option(
    "--labels",
    "labels_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to rolling_labels.csv.",
)
@click.option(
    "--validation-start",
    default="2024-01-01",
    show_default=True,
    help="First as-of timestamp to score.",
)
@click.option(
    "--validation-end",
    default=None,
    help="Exclusive final as-of timestamp; use to preserve a holdout period.",
)
@click.option(
    "--min-available-strategies",
    type=int,
    default=3,
    show_default=True,
    help="Minimum strategies that must cover the label window.",
)
@click.option(
    "--non-overlap-days",
    type=int,
    default=30,
    show_default=True,
    help="Spacing for portfolio-style non-overlap scoring.",
)
@click.option(
    "--catalog-version",
    type=click.Choice(["v1", "v2"], case_sensitive=False),
    default="v1",
    show_default=True,
    help="Router constructor catalog version.",
)
@click.option(
    "--algorithm",
    type=click.Choice(
        ["grid", "random", "island_qd", "hyperband_qd", "smac_qd"],
        case_sensitive=False,
    ),
    default="grid",
    show_default=True,
    help="Router candidate-selection backend.",
)
@click.option(
    "--seed",
    type=int,
    default=2026,
    show_default=True,
    help="Deterministic search seed.",
)
@click.option(
    "--proposal-multiplier",
    type=int,
    default=8,
    show_default=True,
    help="Proposal-pool multiplier for Hyperband-QD and SMAC-QD.",
)
@click.option(
    "--config-offset",
    type=int,
    default=0,
    show_default=True,
    help="Skip this many deterministic router catalog candidates.",
)
@click.option(
    "--max-configs",
    type=int,
    default=2_000,
    show_default=True,
    help="Maximum router catalog candidates to evaluate.",
)
@click.option(
    "--summary-only/--full-predictions",
    default=False,
    show_default=True,
    help="Keep full predictions only for the top shortlist.",
)
@click.option(
    "--top-predictions",
    type=int,
    default=20,
    show_default=True,
    help="Top routers whose daily predictions are retained in summary-only mode.",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    show_default=True,
    help="Show evaluated/total, rate, elapsed time, and ETA.",
)
@click.option(
    "--progress-position",
    type=int,
    default=0,
    hidden=True,
)
@click.option(
    "--count-only",
    is_flag=True,
    help="Print the deterministic catalog size and exit.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <labels-dir>/router_search.",
)
def router_search(
    labels_path: Path,
    validation_start: str,
    validation_end: str | None,
    min_available_strategies: int,
    non_overlap_days: int,
    catalog_version: str,
    algorithm: str,
    seed: int,
    proposal_multiplier: int,
    config_offset: int,
    max_configs: int,
    summary_only: bool,
    top_predictions: int,
    progress: bool,
    progress_position: int,
    count_only: bool,
    output: Path | None,
) -> None:
    """Search single-strategy routers over rolling regime labels."""

    labels = pd.read_csv(labels_path)
    config = RouterSearchConfig(
        validation_start=validation_start,
        validation_end=validation_end,
        min_available_strategies=min_available_strategies,
        non_overlap_days=non_overlap_days,
        catalog_version=catalog_version.lower(),
        algorithm=algorithm.lower(),
        seed=seed,
        proposal_multiplier=proposal_multiplier,
        config_offset=config_offset,
        max_configs=max_configs,
        summary_only=summary_only,
        top_predictions=top_predictions,
        progress=progress,
        progress_position=progress_position,
    )
    if count_only:
        count = count_router_candidates(labels, config=config)
        click.echo(f"Router catalog {config.catalog_version}: {count} configs")
        return
    predictions, dense_summary, offset_sensitivity, utility = (
        evaluate_single_strategy_router_search(labels, config=config)
    )
    output_path = output or labels_path.parent / "router_search"
    write_single_strategy_router_search_report(
        output=output_path,
        predictions=predictions,
        dense_summary=dense_summary,
        offset_sensitivity=offset_sensitivity,
        utility=utility,
        config=config,
    )
    click.echo(f"Router search saved to: {output_path}")


@cli.command("router-validate")
@click.option(
    "--predictions",
    "predictions_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to router_search_predictions.csv.",
)
@click.option("--router", required=True, help="Router search-row id to validate.")
@click.option(
    "--matrix-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Archived performance matrix containing strategy_trades/.",
)
@click.option("--from", "from_date", default="2025-01-01", show_default=True)
@click.option("--to", "to_date", default="2026-01-01", show_default=True)
@click.option("--capital", type=float, default=10_000.0, show_default=True)
@click.option(
    "--max-allowed-margin",
    type=click.FloatRange(min=0.0, max=1.0, min_open=True),
    default=1.0,
    show_default=True,
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output directory for routed execution artifacts.",
)
def router_validate(
    predictions_path: Path,
    router: str,
    matrix_dir: Path,
    from_date: str,
    to_date: str,
    capital: float,
    max_allowed_margin: float,
    output: Path,
) -> None:
    """Replay one router through a continuous shared-capital portfolio."""

    predictions = pd.read_csv(predictions_path)
    trades_by_strategy = load_matrix_strategy_trades(matrix_dir)
    try:
        result = evaluate_routed_execution(
            predictions=predictions,
            router=router,
            trades_by_strategy=trades_by_strategy,
            config=RoutedExecutionConfig(
                start=from_date,
                end=to_date,
                initial_capital=capital,
                max_allowed_margin=max_allowed_margin,
            ),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    write_routed_execution_report(output=output, result=result)
    click.echo(f"Routed execution validation saved to: {output}")


@cli.command("router-validate-shortlist")
@click.option(
    "--predictions",
    "predictions_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to router_search_predictions.csv.",
)
@click.option(
    "--shortlist",
    "shortlist_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to router_shortlist.csv.",
)
@click.option(
    "--matrix-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Archived performance matrix containing strategy_trades/.",
)
@click.option("--from", "from_date", default="2025-01-01", show_default=True)
@click.option("--to", "to_date", default="2026-01-01", show_default=True)
@click.option("--capital", type=float, default=10_000.0, show_default=True)
@click.option(
    "--max-allowed-margin",
    type=click.FloatRange(min=0.0, max=1.0, min_open=True),
    default=1.0,
    show_default=True,
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output directory for all routed shortlist reports.",
)
def router_validate_shortlist(
    predictions_path: Path,
    shortlist_path: Path,
    matrix_dir: Path,
    from_date: str,
    to_date: str,
    capital: float,
    max_allowed_margin: float,
    output: Path,
) -> None:
    """Replay every shortlisted router through continuous shared capital."""

    predictions = pd.read_csv(predictions_path)
    shortlist = pd.read_csv(shortlist_path)
    if "router" not in shortlist.columns:
        raise click.ClickException("Shortlist must contain a router column")
    router_ids = shortlist["router"].dropna().astype(str).drop_duplicates().tolist()
    if not router_ids:
        raise click.ClickException("Shortlist contains no routers")
    available = set(predictions.get("router", pd.Series(dtype=str)).astype(str))
    missing = [router_id for router_id in router_ids if router_id not in available]
    if missing:
        raise click.ClickException(
            "Predictions are missing shortlisted routers: " + ", ".join(missing)
        )

    trades_by_strategy = load_matrix_strategy_trades(matrix_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []
    router_items = tqdm(
        router_ids,
        total=len(router_ids),
        desc="router routed-validation",
        unit="router",
        mininterval=1.0,
        dynamic_ncols=True,
    )
    for router_id in router_items:
        router_items.set_postfix(router=router_id, refresh=False)
        try:
            result = evaluate_routed_execution(
                predictions=predictions,
                router=router_id,
                trades_by_strategy=trades_by_strategy,
                config=RoutedExecutionConfig(
                    start=from_date,
                    end=to_date,
                    initial_capital=capital,
                    max_allowed_margin=max_allowed_margin,
                ),
            )
        except ValueError as exc:
            raise click.ClickException(f"{router_id}: {exc}") from exc
        write_routed_execution_report(output=output / router_id, result=result)
        execution = result.execution_summary.iloc[0].to_dict()
        mandate = result.mandate.summary.iloc[0].to_dict()
        summary_rows.append(
            {
                **execution,
                **{f"mandate_{key}": value for key, value in mandate.items()},
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(
        ["total_return_pct", "mandate_worst_monthly_drawdown_pct"],
        ascending=[False, False],
    )
    summary.to_csv(output / "shortlist_execution_summary.csv", index=False)
    click.echo(f"Routed shortlist validation saved to: {output}")


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
@click.option("--rrr-low", type=float, default=1.0, help="RRR search low bound.")
@click.option("--rrr-high", type=float, default=3.0, help="RRR search high bound.")
@click.option("--rrr-step", type=float, default=0.25, help="RRR search step.")
@click.option(
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    help="Exit placement mode. tp_pct is auto-used when tp-move-pct range is set.",
)
@click.option(
    "--tp-move-pct",
    type=float,
    default=None,
    help="Fixed TP move pct when not searching (required for tp_pct without range).",
)
@click.option("--tp-move-pct-low", type=float, default=None, help="TP move pct search low.")
@click.option("--tp-move-pct-high", type=float, default=None, help="TP move pct search high.")
@click.option("--tp-move-pct-step", type=float, default=0.002, help="TP move pct search step.")
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    help="How structural sl_price constrains TP-first SL.",
)
@click.option(
    "--min-tp-move-pct",
    type=float,
    default=0.004,
    help="Breakeven floor for tp_move_pct in TP-first mode.",
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
    risk_percent: float,
    risk_percent_low: float | None,
    risk_percent_high: float | None,
    risk_percent_step: float,
    strategy_param_search: bool,
    daily_limit_search: bool,
    trading_window_search: bool,
    progress: bool,
    export_best_run: bool,
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
        trail_activation_rrr=0.0,
        trail_distance_atr=trail_distance_atr,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
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
    ttl_range = None if ttl_low is None or ttl_high is None else (ttl_low, ttl_high, ttl_step)
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
            position_ttl_bars_range=ttl_range,
            tp_move_pct_range=tp_move_pct_range,
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
    "--trail-distance-atr",
    type=float,
    default=0.0,
    help="Trailing stop distance in ATR units after activation.",
)
@click.option("--ttl", type=int, default=36, help="Fixed position TTL in bars. 0 disables TTL.")
@click.option(
    "--continuous/--isolated-windows",
    default=True,
    show_default=True,
    help=(
        "Continuous (default): one backtest per symbol; open positions carry through "
        "calendar month boundaries — canonical mandate evaluation. Isolated-windows: "
        "reset each window to fresh capital (diagnostic only)."
    ),
)
@click.option(
    "--jobs",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Parallel fixed-window workers.",
)
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
@click.option(
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    help="Exit placement: structural SL+RRR (default) or TP-first percent.",
)
@click.option(
    "--tp-move-pct",
    type=float,
    default=None,
    help="Target gross TP price move decimal (0.015 = 1.5%). Required for tp_pct.",
)
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    help="How structural sl_price constrains TP-first SL.",
)
@click.option(
    "--min-tp-move-pct",
    type=float,
    default=0.004,
    help="Skip entries when tp_move_pct is below this breakeven floor.",
)
def compare_fixed(
    data_dir: str,
    primary_timeframe: str,
    strategy: str,
    windows: tuple[str, ...],
    output: str,
    capital: float,
    risk_percent: float,
    rrr: float,
    trail_distance_atr: float,
    ttl: int,
    continuous: bool,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    exit_geometry: str,
    tp_move_pct: float | None,
    structural_sl_mode: str,
    min_tp_move_pct: float,
) -> None:
    """Run fixed candidate backtests across bounded windows and summarize them."""
    logger.info("🚀 Starting fixed-candidate comparison...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    if exit_geometry.lower() == "tp_pct" and tp_move_pct is None:
        logger.error("❌ --tp-move-pct is required when --exit-geometry=tp_pct")
        return
    try:
        window_specs = parse_window_specs(windows)
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    output_folder = make_output_folder(output)
    use_continuous = continuous or ttl == 0
    if ttl == 0 and not continuous:
        logger.info(
            "ttl=0 forces continuous execution so open positions are not orphaned "
            "at each monthly window boundary."
        )
    elif continuous:
        logger.info(
            "Continuous mandate mode: one backtest per symbol; monthly rows derived "
            "from calendar-month PnL on that run."
        )
    else:
        logger.info("Isolated-window mode (diagnostic): each window resets capital and positions.")
    summary = run_fixed_candidate_comparison(
        windows=window_specs,
        cfg=cfg,
        params=FixedCandidateParams(
            capital=capital,
            risk_percent=risk_percent,
            rrr=rrr,
            trail_activation_rrr=rrr if trail_distance_atr > 0 else 0.0,
            trail_distance_atr=trail_distance_atr,
            ttl=ttl,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=0,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
        ),
        data_dir=data_dir,
        primary_timeframe=primary_timeframe,
        output_folder=output_folder,
        jobs=jobs,
        logger=logger,
        continuous=use_continuous,
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
    "--trail-distance-atr-values",
    default="0",
    show_default=True,
    help="Comma-separated trailing distance ATR values.",
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
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
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
    trail_distance_atr_values: str,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
) -> None:
    """Run a tiny execution-only rrr/ttl grid across bounded windows."""
    logger.info("🚀 Starting execution-grid comparison...")
    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)
    try:
        window_specs = parse_window_specs(windows)
        parsed_rrr_values = parse_float_values(rrr_values)
        parsed_ttl_values = parse_int_values(ttl_values)
        parsed_trail_distance_atr_values = parse_float_values(trail_distance_atr_values)
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
            trail_activation_rrr=(
                parsed_rrr_values[0] if parsed_trail_distance_atr_values[0] > 0 else 0.0
            ),
            trail_distance_atr=parsed_trail_distance_atr_values[0],
            ttl=parsed_ttl_values[0],
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=0,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
        ),
        rrr_values=parsed_rrr_values,
        ttl_values=parsed_ttl_values,
        trail_distance_atr_values=parsed_trail_distance_atr_values,
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
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
def signal_quality(
    data_dir: str,
    primary_timeframe: str,
    strategy: str,
    windows: tuple[str, ...],
    output: str,
    capital: float,
    risk_percent: float,
    rrr: float,
    trail_distance_atr: float,
    ttl: int,
    jobs: int,
    maker_fee: float,
    taker_fee: float,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
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
            trail_activation_rrr=rrr if trail_distance_atr > 0 else 0.0,
            trail_distance_atr=trail_distance_atr,
            ttl=ttl,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            max_positions=0,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
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


@cli.command("walk-forward")
@click.option("--data-dir", required=True, help="Project data directory (crypt-parquet).")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="1h",
    help="Primary execution timeframe.",
)
@click.option("--symbol", required=True, help="OKX SWAP symbol, e.g. SOL-USDT-SWAP.")
@click.option("--from", "from_date", required=True, help="Inclusive start date YYYY-MM-DD.")
@click.option("--to", "to_date", required=True, help="Inclusive end date YYYY-MM-DD.")
@click.option(
    "--is-months",
    type=click.IntRange(min=1),
    default=12,
    show_default=True,
    help="In-sample window size in calendar months.",
)
@click.option(
    "--oos-months",
    type=click.IntRange(min=1),
    default=6,
    show_default=True,
    help="Out-of-sample window size in calendar months.",
)
@click.option("--strategy", required=True, help="Strategy parameters file.")
@click.option("--output", default="results/walk_forward", help="Folder for results.")
@click.option("--capital", type=float, default=10000.0, help="Initial capital.")
@click.option("--maker-fee", type=float, default=0.0002, help="Maker fee.")
@click.option("--taker-fee", type=float, default=0.0005, help="Taker fee.")
@click.option("--max-allowed-leverage", type=float, default=25.0, help="Max allowed leverage.")
@click.option("--max-allowed-margin", type=float, default=1.0, help="Max margin.")
@click.option(
    "--risk-base-period",
    type=click.Choice(["trade", "weekly", "monthly", "backtest"], case_sensitive=False),
    default="monthly",
    help="Capital window used for risk sizing.",
)
@click.option(
    "--trials",
    type=click.IntRange(min=0),
    default=50,
    show_default=True,
    help="Optuna trials per IS window. 0 = eval-only (no optimization).",
)
@click.option("--rrr-low", type=float, default=1.5, show_default=True, help="RRR search low.")
@click.option("--rrr-high", type=float, default=3.5, show_default=True, help="RRR search high.")
@click.option("--rrr-step", type=float, default=0.25, show_default=True, help="RRR search step.")
@click.option("--ttl-low", type=int, default=None, help="TTL search low bound.")
@click.option("--ttl-high", type=int, default=None, help="TTL search high bound.")
@click.option("--ttl-step", type=int, default=1, help="TTL search step.")
@click.option("--risk-percent-low", type=float, default=None, help="Risk percent search low.")
@click.option("--risk-percent-high", type=float, default=None, help="Risk percent search high.")
@click.option("--risk-percent-step", type=float, default=0.25, help="Risk percent search step.")
@click.option(
    "--risk-percent", type=float, default=1.5, help="Fixed risk percent (when not searching)."
)
@click.option("--ttl", type=int, default=36, help="Fixed TTL in bars (when not searching).")
@click.option(
    "--exit-geometry",
    type=click.Choice(["sl_rrr", "tp_pct"], case_sensitive=False),
    default="sl_rrr",
    help="Exit placement mode.",
)
@click.option("--tp-move-pct", type=float, default=None, help="Fixed TP move pct for tp_pct mode.")
@click.option("--tp-move-pct-low", type=float, default=None, help="TP move pct search low.")
@click.option("--tp-move-pct-high", type=float, default=None, help="TP move pct search high.")
@click.option("--tp-move-pct-step", type=float, default=0.002, help="TP move pct search step.")
@click.option(
    "--structural-sl-mode",
    type=click.Choice(["cap", "ignore", "reject"], case_sensitive=False),
    default="cap",
    help="Structural SL mode for tp_pct exit geometry.",
)
@click.option("--min-tp-move-pct", type=float, default=0.004, help="Breakeven floor.")
@click.option(
    "--progress/--no-progress",
    default=False,
    show_default=True,
    help="Show Optuna progress bar per IS window.",
)
def walk_forward(
    data_dir: str,
    primary_timeframe: str,
    symbol: str,
    from_date: str,
    to_date: str,
    is_months: int,
    oos_months: int,
    strategy: str,
    output: str,
    capital: float,
    maker_fee: float,
    taker_fee: float,
    max_allowed_leverage: float,
    max_allowed_margin: float,
    risk_base_period: str,
    trials: int,
    rrr_low: float,
    rrr_high: float,
    rrr_step: float,
    ttl_low: int | None,
    ttl_high: int | None,
    ttl_step: int,
    risk_percent_low: float | None,
    risk_percent_high: float | None,
    risk_percent_step: float,
    risk_percent: float,
    ttl: int,
    exit_geometry: str,
    tp_move_pct: float | None,
    tp_move_pct_low: float | None,
    tp_move_pct_high: float | None,
    tp_move_pct_step: float,
    structural_sl_mode: str,
    min_tp_move_pct: float,
    progress: bool,
) -> None:
    """Walk-forward analysis: optimize on IS window, evaluate on OOS window.

    Answers the question: does the strategy concept generalize out-of-sample,
    or is it overfit to the training period? See ADR-0034.

    Example (full optimization, 6 windows):

        backtester walk-forward \\
          --data-dir data --symbol SOL-USDT-SWAP \\
          --from 2022-01-01 --to 2025-12-31 \\
          --is-months 12 --oos-months 6 \\
          --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \\
          --trials 50 \\
          --ttl-low 24 --ttl-high 60 \\
          --risk-percent-low 1.0 --risk-percent-high 3.0

    Example (eval-only, no optimization):

        backtester walk-forward \\
          --data-dir data --symbol SOL-USDT-SWAP \\
          --from 2022-01-01 --to 2025-12-31 \\
          --is-months 12 --oos-months 12 \\
          --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \\
          --trials 0
    """
    logger.info("Walk-forward analysis — %s  %s → %s", symbol, from_date, to_date)

    cfg = load_strategy_config(strategy, logger)
    if cfg is None:
        return
    log_strategy_info(cfg, logger)

    if (
        exit_geometry.lower() == "tp_pct"
        and tp_move_pct is None
        and (tp_move_pct_low is None or tp_move_pct_high is None)
    ):
        logger.error(
            "❌ --tp-move-pct or --tp-move-pct-low/--tp-move-pct-high required for tp_pct mode"
        )
        return

    # Generate window list first so we can report count before loading data.
    try:
        windows = generate_windows(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            is_months=is_months,
            oos_months=oos_months,
        )
    except ValueError as e:
        logger.error("❌ Window generation failed: %s", e)
        return

    if not windows:
        logger.error(
            "❌ No windows generated. Check that to_date - from_date > is_months + oos_months."
        )
        return

    logger.info(
        "Generated %d windows  (IS=%d months, OOS=%d months)",
        len(windows),
        is_months,
        oos_months,
    )
    for w in windows:
        logger.info("  %s", w.label)

    # Load full data once; walk-forward slices it in memory.
    try:
        loader = build_cli_data_loader(
            "crypt-parquet",
            data_dir=data_dir,
            symbol=symbol,
            primary_timeframe=primary_timeframe,
            start=from_date,
            end=to_date,
        )
    except ValueError as e:
        logger.error("❌ %s", e)
        return

    full_data = load_ohlcv_via_loader(loader, logger=logger)
    if full_data is None:
        return

    # Build BacktestArgs (strategy config overrides CLI defaults).
    base_args = build_backtest_args(
        cfg,
        capital=capital,
        risk_percent=risk_percent,
        rrr=rrr_low,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        ttl=ttl,
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
    )

    ttl_range = None if ttl_low is None or ttl_high is None else (ttl_low, ttl_high, ttl_step)
    risk_percent_range = (
        None
        if risk_percent_low is None or risk_percent_high is None
        else (risk_percent_low, risk_percent_high, risk_percent_step)
    )
    tp_move_pct_range = (
        None
        if tp_move_pct_low is None or tp_move_pct_high is None
        else (tp_move_pct_low, tp_move_pct_high, tp_move_pct_step)
    )

    optimizer_args = OptimizerSearchArgs(
        trials=trials,
        study_name="wf_study",
        target="mandate_score",
        show_progress=progress,
        optimize_strategy_params=False,
        risk_percent_range=risk_percent_range,
        rrr_range=(rrr_low, rrr_high, rrr_step),
        trail_distance_atr_range=None,
        position_ttl_bars_range=ttl_range,
        tp_move_pct_range=tp_move_pct_range,
        optimize_daily_limits=False,
        optimize_trading_window=False,
        export_best_run=False,
    )

    output_folder = Path(make_output_folder(output))
    output_folder.mkdir(parents=True, exist_ok=True)

    results = run_walk_forward(
        windows=windows,
        cfg=cfg,
        base_args=base_args,
        optimizer_args=optimizer_args,
        full_data=full_data,
        output_folder=output_folder,
        logger=logger,
    )

    write_walk_forward_report(
        results=results,
        symbol=symbol,
        is_months=is_months,
        oos_months=oos_months,
        from_date=from_date,
        to_date=to_date,
        output_folder=output_folder,
        logger=logger,
    )

    oos_positive = sum(1 for r in results if r.oos_metrics.total_return_pct > 0)
    logger.info(
        "Walk-forward complete: %d/%d windows OOS-positive. Artifacts: %s",
        oos_positive,
        len(results),
        output_folder,
    )


@cli.command("discover-strategies")
@click.option("--data-dir", required=True, help="Project data directory.")
@click.option(
    "--primary-timeframe",
    type=click.Choice(["1h", "4h", "1d"], case_sensitive=False),
    default="1h",
    help="Primary discovery timeframe for crypt-parquet data.",
)
@click.option("--symbol", default=None, help="Trading pair for contiguous --from/--to mode.")
@click.option("--from", "from_date", default=None, help="Inclusive start UTC.")
@click.option("--to", "to_date", default=None, help="Inclusive end UTC.")
@click.option(
    "--window",
    "windows",
    multiple=True,
    help=(
        "Window as label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD. "
        "May be repeated; overrides --symbol/--from/--to."
    ),
)
@click.option("--output", default="results/discovery", help="Folder for discovery reports.")
@click.option("--label-horizon-bars", type=int, default=24, show_default=True)
@click.option("--label-atr-mult", type=float, default=1.0, show_default=True)
@click.option("--beam-width", type=click.IntRange(min=1), default=20, show_default=True)
@click.option("--max-filter-depth", type=click.IntRange(min=0), default=4, show_default=True)
@click.option("--min-trades-total", type=click.IntRange(min=1), default=50, show_default=True)
@click.option("--min-trades-per-window", type=click.IntRange(min=1), default=10, show_default=True)
@click.option(
    "--keep-sparse-triggers",
    is_flag=True,
    help="Continue filter search even when an unfiltered trigger is below min-trades-total.",
)
def discover_strategies(
    data_dir: str,
    primary_timeframe: str,
    symbol: str | None,
    from_date: str | None,
    to_date: str | None,
    windows: tuple[str, ...],
    output: str,
    label_horizon_bars: int,
    label_atr_mult: float,
    beam_width: int,
    max_filter_depth: int,
    min_trades_total: int,
    min_trades_per_window: int,
    keep_sparse_triggers: bool,
) -> None:
    """Run trigger/filter discovery with fixed ATR-barrier forward labels."""
    logger.info("🚀 Starting strategy discovery...")
    try:
        window_specs = (
            [parse_window_spec(raw) for raw in windows]
            if windows
            else _single_discovery_window_spec(symbol=symbol, from_date=from_date, to_date=to_date)
        )
        discovery_windows = [
            DiscoveryWindow(
                label=window.label,
                symbol=window.symbol,
                start=window.start,
                end=window.end,
                data=_load_discovery_window(
                    data_dir=data_dir,
                    primary_timeframe=primary_timeframe,
                    symbol=window.symbol,
                    start=window.start,
                    end=window.end,
                ),
            )
            for window in window_specs
        ]
        config = DiscoveryConfig(
            output=Path(output),
            primary_timeframe=primary_timeframe,
            label_horizon_bars=label_horizon_bars,
            label_atr_mult=label_atr_mult,
            beam_width=beam_width,
            max_filter_depth=max_filter_depth,
            min_trades_total=min_trades_total,
            min_trades_per_window=min_trades_per_window,
            keep_sparse_triggers=keep_sparse_triggers,
        )
        progress_total = _estimate_discovery_progress_total(
            window_count=len(discovery_windows),
            beam_width=beam_width,
            max_filter_depth=max_filter_depth,
        )
        progress_done = 0

        with click.progressbar(
            length=progress_total,
            label="Discovering strategies",
        ) as bar:

            def update_progress(step: int) -> None:
                nonlocal progress_done
                bounded_step = min(step, progress_total - progress_done)
                if bounded_step > 0:
                    bar.update(bounded_step)
                    progress_done += bounded_step

            output_path = run_strategy_discovery(
                windows=discovery_windows,
                config=config,
                progress_callback=update_progress,
            )
            update_progress(progress_total - progress_done)
    except ValueError as e:
        logger.error("❌ %s", e)
        return
    logger.info("Strategy discovery artifacts saved to: %s", output_path)


@cli.command("convert-discovery-strategy")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Discovery-native rank_*_strategy.json file.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Donor crypt_ensemble strategy JSON output path.",
)
def convert_discovery_strategy_cmd(input_path: Path, output_path: Path) -> None:
    """Convert a discovery-native candidate JSON into a donor crypt_ensemble config."""
    try:
        converted = load_and_convert_discovery_strategy(input_path)
    except DiscoveryConversionError as exc:
        logger.error("❌ %s", exc)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(converted, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Converted discovery strategy saved to: %s", output_path)


def _single_discovery_window_spec(
    *,
    symbol: str | None,
    from_date: str | None,
    to_date: str | None,
) -> list[WindowSpec]:
    if not symbol or not from_date or not to_date:
        raise ValueError("discover-strategies requires --window or --symbol plus --from/--to")
    return [parse_window_spec(f"{symbol.lower().replace('-', '_')}:{symbol}:{from_date}:{to_date}")]


def _load_discovery_window(
    *,
    data_dir: str,
    primary_timeframe: str,
    symbol: str,
    start: str,
    end: str,
) -> StrategyInput:
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir=data_dir,
        symbol=symbol,
        primary_timeframe=primary_timeframe,
        start=start,
        end=end,
    )
    df = load_ohlcv_via_loader(loader, logger=logger)
    if df is None:
        raise ValueError(f"Could not load discovery data for {symbol} {start}..{end}")
    return df


def _estimate_discovery_progress_total(
    *,
    window_count: int,
    beam_width: int,
    max_filter_depth: int,
) -> int:
    trigger_count = len(trigger_catalog())
    filter_count = len(filter_catalog())
    dataset_steps = window_count
    trigger_steps = trigger_count * window_count
    label_steps = trigger_count * window_count
    initial_eval_steps = trigger_count
    depth_one_steps = trigger_count * filter_count if max_filter_depth >= 1 else 0
    deeper_steps = trigger_count * beam_width * filter_count * max(max_filter_depth - 1, 0)
    export_steps = 1
    return max(
        dataset_steps
        + trigger_steps
        + label_steps
        + initial_eval_steps
        + depth_one_steps
        + deeper_steps
        + export_steps,
        1,
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


@cli.command("trade-filter-research")
@click.option(
    "--trades",
    "trades_paths",
    multiple=True,
    required=True,
    help="Path to trades.csv or a completed run directory containing trades.csv. Repeatable.",
)
@click.option("--output", required=True, help="Output directory for the research report.")
@click.option(
    "--ohlcv",
    "ohlcv_path",
    default=None,
    help=(
        "Optional OHLCV CSV/parquet path used with --include-catalog-features. "
        "A completed run directory usually contains ohlcv.csv."
    ),
)
@click.option(
    "--group-by",
    default=None,
    help=(
        "Optional trade column for separate filter searches, for example "
        "selected_strategy."
    ),
)
@click.option("--capital", type=float, default=10_000.0, show_default=True)
@click.option("--train-start", default="2022-01-01", show_default=True)
@click.option("--validation-start", default="2024-01-01", show_default=True)
@click.option("--stress-start", default="2025-01-01", show_default=True)
@click.option(
    "--stress-end",
    default=None,
    help="Exclusive stress end date. Defaults to one day after the latest supplied trade.",
)
@click.option("--min-train-trades", type=int, default=30, show_default=True)
@click.option("--max-categories", type=int, default=20, show_default=True)
@click.option("--top-n", type=int, default=50, show_default=True)
@click.option(
    "--max-pair-components",
    type=int,
    default=30,
    show_default=True,
    help="How many best single rules to combine into pair rules.",
)
@click.option(
    "--max-pair-rules",
    type=int,
    default=500,
    show_default=True,
    help="Maximum number of two-rule combinations to evaluate.",
)
@click.option(
    "--include-catalog-features",
    is_flag=True,
    help=(
        "Attach closed-candle discovery/catalog features at entry time and test them "
        "as take/skip filters."
    ),
)
@click.option(
    "--include-portfolio-state-features",
    is_flag=True,
    help=(
        "Include size/capital/margin/open-position fields. Off by default because "
        "they can proxy time and equity-curve state."
    ),
)
@click.option("--no-progress", is_flag=True, help="Disable progress bar output.")
def trade_filter_research(
    trades_paths: tuple[str, ...],
    output: str,
    ohlcv_path: str | None,
    group_by: str | None,
    capital: float,
    train_start: str,
    validation_start: str,
    stress_start: str,
    stress_end: str | None,
    min_train_trades: int,
    max_categories: int,
    top_n: int,
    max_pair_components: int,
    max_pair_rules: int,
    include_catalog_features: bool,
    include_portfolio_state_features: bool,
    no_progress: bool,
) -> None:
    """Search entry-known take/skip filters over existing trade artifacts."""
    resolved_trades = tuple(_resolve_trades_path(Path(path)) for path in trades_paths)
    try:
        result = run_trade_filter_research(
            FilterSearchConfig(
                trades_paths=resolved_trades,
                output_dir=Path(output),
                ohlcv_path=Path(ohlcv_path) if ohlcv_path is not None else None,
                group_by=group_by,
                initial_capital=capital,
                splits=SplitConfig(
                    train_start=train_start,
                    validation_start=validation_start,
                    stress_start=stress_start,
                    stress_end=stress_end,
                ),
                min_train_trades=min_train_trades,
                max_categories=max_categories,
                top_n=top_n,
                max_pair_components=max_pair_components,
                max_pair_rules=max_pair_rules,
                include_catalog_features=include_catalog_features,
                include_portfolio_state_features=include_portfolio_state_features,
                progress=not no_progress,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    click.echo(f"Trade filter research saved to: {result.output_dir}")
    click.echo(f"Rules tested: {len(result.filter_candidates)}")
    if not result.top_filters.empty:
        best = result.top_filters.iloc[0]
        click.echo(
            "Best robust-forward rule: "
            f"{best['expression']} | "
            f"pass={best['robust_forward_pass']} "
            f"train={best['train_return_pct']}% "
            f"validation={best['validation_return_pct']}% "
            f"stress={best['stress_return_pct']}%"
        )


@cli.command("negative-oracle-research")
@click.option(
    "--trades",
    "trades_path",
    required=True,
    help="Path to trades.csv or a completed run directory containing trades.csv.",
)
@click.option("--output", required=True, help="Output directory for the research report.")
@click.option("--train-start", default="2022-01-01", show_default=True)
@click.option("--validation-start", default="2024-01-01", show_default=True)
@click.option("--stress-start", default="2025-01-01", show_default=True)
@click.option("--min-train-trades", type=int, default=30, show_default=True)
@click.option("--max-categories", type=int, default=30, show_default=True)
@click.option("--max-pair-components", type=int, default=40, show_default=True)
@click.option("--max-pair-rules", type=int, default=800, show_default=True)
@click.option("--top-n", type=int, default=100, show_default=True)
@click.option("--no-progress", is_flag=True, help="Disable progress bar output.")
def negative_oracle_research(
    trades_path: str,
    output: str,
    train_start: str,
    validation_start: str,
    stress_start: str,
    min_train_trades: int,
    max_categories: int,
    max_pair_components: int,
    max_pair_rules: int,
    top_n: int,
    no_progress: bool,
) -> None:
    """Find entry-known skip rules that remove repeatable losing trades."""
    resolved_trades = _resolve_trades_path(Path(trades_path))
    try:
        result = run_negative_oracle_research(
            NegativeOracleConfig(
                trades_path=resolved_trades,
                output_dir=Path(output),
                train_start=train_start,
                validation_start=validation_start,
                stress_start=stress_start,
                min_train_trades=min_train_trades,
                max_categories=max_categories,
                max_pair_components=max_pair_components,
                max_pair_rules=max_pair_rules,
                top_n=top_n,
                progress=not no_progress,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    click.echo(f"Negative oracle research saved to: {result.output_dir}")
    click.echo(f"Rules tested: {len(result.rules)}")
    if not result.rules.empty:
        best = result.rules.iloc[0]
        click.echo(
            "Best skip rule: "
            f"{best['expression']} | "
            f"validation=${best['validation_delta_abs']:.2f} "
            f"stress=${best['stress_delta_abs']:.2f} "
            f"pass={best['robust_negative_pass']}"
        )


def _resolve_trades_path(path: Path) -> Path:
    if path.is_dir():
        return path / "trades.csv"
    return path


def _parse_dss_matrix_algorithms(raw: str) -> list[str]:
    algorithms = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not algorithms:
        raise click.ClickException("--algorithms must contain at least one algorithm")

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


@cli.command("search-signals-matrix")
@click.option("--data-dir", required=True, help="Project data directory (crypt-parquet layout).")
@click.option(
    "--symbol",
    "symbols",
    multiple=True,
    required=True,
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
    "--primary-timeframe",
    type=click.Choice(["1h", "4h"], case_sensitive=False),
    default="1h",
    show_default=True,
    help="Primary execution timeframe.",
)
@click.option("--n-trials", type=int, default=50_000, show_default=True)
@click.option(
    "--n-jobs-per-algorithm",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Worker count passed to each child search-signals process.",
)
@click.option(
    "--algorithms",
    default="staged,catcma_qd,island_qd,hyperband_qd,smac_qd",
    show_default=True,
    help="Comma-separated DSS algorithms to launch in parallel.",
)
@click.option(
    "--catalog",
    type=click.Choice(["legacy", "pinescript_v1", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Trigger/filter catalog to search.",
)
@click.option(
    "--stage-mode",
    type=click.Choice(["full", "stage1"], case_sensitive=False),
    default="stage1",
    show_default=True,
    help="Stage mode passed to each child search.",
)
@click.option("--output-root", default=None, help="Root directory for per-algorithm outputs.")
@click.option("--top-n", type=int, default=20, show_default=True)
@click.option("--min-trades", type=int, default=20, show_default=True)
@click.option("--min-signals-per-week", type=float, default=4.0, show_default=True)
@click.option(
    "--stage1-min-wr",
    type=click.FloatRange(min=0.0, max=1.0),
    default=0.55,
    show_default=True,
    help="Minimum Stage 1 barrier win rate required in each window.",
)
@click.option("--capital", type=float, default=10_000.0, show_default=True)
@click.option("--risk-base-period", default="monthly", show_default=True)
@click.option("--specialist-windows", default="", show_default=True)
def search_signals_matrix(
    data_dir: str,
    symbols: tuple[str, ...],
    windows_spec: str,
    primary_timeframe: str,
    n_trials: int,
    n_jobs_per_algorithm: int,
    algorithms: str,
    catalog: str,
    stage_mode: str,
    output_root: str | None,
    top_n: int,
    min_trades: int,
    min_signals_per_week: float,
    stage1_min_wr: float,
    capital: float,
    risk_base_period: str,
    specialist_windows: str,
) -> None:
    """Launch several DSS search-signals algorithms concurrently."""
    parsed_algorithms = _parse_dss_matrix_algorithms(algorithms)
    if output_root is None:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_root = f"results/dss_matrix_{catalog.lower()}_{stage_mode.lower()}_{ts}"
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    click.echo(
        "Launching DSS matrix: "
        f"{len(parsed_algorithms)} algorithms x {n_jobs_per_algorithm} jobs each "
        f"({len(parsed_algorithms) * n_jobs_per_algorithm} workers requested)"
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
                "--primary-timeframe",
                primary_timeframe,
                "--n-trials",
                str(n_trials),
                "--n-jobs",
                str(n_jobs_per_algorithm),
                "--algorithm",
                algorithm,
                "--catalog",
                catalog.lower(),
                "--stage-mode",
                stage_mode.lower(),
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
                "--stage1-min-wr",
                str(stage1_min_wr),
                "--capital",
                str(capital),
                "--risk-base-period",
                risk_base_period,
                "--specialist-windows",
                specialist_windows,
            ]
            for symbol in symbols:
                cmd.extend(["--symbol", symbol])

            log_file = log_path.open("wb")
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
    required=True,
    help="Project data directory (crypt-parquet layout).",
)
@click.option(
    "--symbol",
    "symbols",
    multiple=True,
    required=True,
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
    "--primary-timeframe",
    type=click.Choice(["1h", "4h"], case_sensitive=False),
    default="1h",
    show_default=True,
    help="Primary execution timeframe.",
)
@click.option(
    "--n-trials",
    type=int,
    default=50_000,
    show_default=True,
    help="Total candidate-generation budget.",
)
@click.option(
    "--n-jobs", type=int, default=1, show_default=True, help="Parallel workers where safe."
)
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
    show_default=True,
    help="Top-N candidates to export as JSON.",
)
@click.option("--accept-min-score", default=None, hidden=True)
@click.option(
    "--algorithm",
    type=click.Choice(
        ["staged", "catcma_qd", "island_qd", "hyperband_qd", "smac_qd"], case_sensitive=False
    ),
    default="staged",
    show_default=True,
    help="DSS backend: staged, CatCMA-QD, Island-QD, Hyperband-QD, or SMAC-QD.",
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
    show_default=True,
    help="Candidate generator seed.",
)
@click.option(
    "--min-trades",
    type=int,
    default=20,
    show_default=True,
    help="Absolute min signals per window; effective Stage 1 threshold also uses --min-signals-per-week.",
)
@click.option(
    "--min-signals-per-week",
    type=float,
    default=0.0,
    show_default=True,
    help="Min Stage 1 signal frequency per week in each window.",
)
@click.option(
    "--stage1-min-wr",
    type=click.FloatRange(min=0.0, max=1.0),
    default=0.55,
    show_default=True,
    help="Minimum Stage 1 barrier win rate required in each window.",
)
@click.option(
    "--stage-mode",
    type=click.Choice(["full", "stage1"], case_sensitive=False),
    default="stage1",
    show_default=True,
    help="Use stage1 to stop after signal/barrier ranking without backtests.",
)
@click.option(
    "--capital",
    type=float,
    default=10_000.0,
    show_default=True,
    help="Initial capital for backtests.",
)
@click.option("--risk-base-period", default="monthly", show_default=True)
@click.option(
    "--specialist-windows",
    default="",
    show_default=True,
    help=(
        "Comma-separated window labels to preserve as specialist diagnostics. "
        "Empty keeps the fast all-window early-reject path."
    ),
)
def search_signals(
    data_dir: str,
    symbols: tuple[str, ...],
    windows_spec: str,
    primary_timeframe: str,
    n_trials: int,
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
    stage1_min_wr: float,
    stage_mode: str,
    capital: float,
    risk_base_period: str,
    specialist_windows: str,
) -> None:
    """Direct Signal Search v2: staged quality-diversity strategy discovery.

    Searches trigger + filter + execution parameters through staged viability,
    proxy, full-score, and archive/export phases.

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
            "DSS v2 replaced the old Optuna sampler path; removed option(s): "
            f"{', '.join(used_removed)}. Use the simplified search-signals command."
        )

    previous_disable = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        symbol = symbols[0]

        raw_specs = [s.strip() for s in windows_spec.split(",") if s.strip()]
        dss_windows: list[DSSWindowSpec] = []
        for raw in raw_specs:
            try:
                dss_windows.append(DSSWindowSpec.parse(raw, symbol))
            except (ValueError, TypeError) as exc:
                raise click.ClickException(f"Invalid window spec {raw!r}: {exc}") from exc

        if not dss_windows:
            raise click.ClickException(f"No windows parsed from --windows {windows_spec!r}")
        specialist_window_labels = tuple(
            label.strip() for label in specialist_windows.split(",") if label.strip()
        )
        unknown_specialist_windows = sorted(
            set(specialist_window_labels) - {window.label for window in dss_windows}
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
                    primary_timeframe=primary_timeframe,
                    symbol=spec.symbol,
                    start=spec.start,
                    end=spec.end,
                )
            except (ValueError, FileNotFoundError) as exc:
                raise click.ClickException(f"Failed to load window {spec.label}: {exc}") from exc
            if isinstance(data_input, StrategyData):
                window_data[spec.label] = StrategyData(
                    primary=data_input.primary,
                    candles=data_input.candles,
                    extras=data_input.extras,
                    metadata={**data_input.metadata, "symbol": symbol},
                )
            else:
                window_data[spec.label] = StrategyData(
                    primary=data_input,
                    candles={},
                    extras={},
                    metadata={"symbol": symbol},
                )

        t_catalog, f_catalog, t_param_space, f_param_space = _dss_catalogs(catalog.lower())

        search_space = DSSSearchSpace(
            trigger_names=tuple(sorted(t_catalog.keys())),
            filter_names=tuple(sorted(f_catalog.keys())),
            trigger_param_bounds=dict(t_param_space),
            filter_param_bounds=dict(f_param_space),
            max_filters=4,
        )

        dss_config = DSSConfig(
            output=output_path,
            windows=dss_windows,
            n_trials=n_trials,
            n_jobs=n_jobs,
            max_filters=4,
            min_trades_per_window=min_trades,
            min_signals_per_week=min_signals_per_week,
            min_barrier_win_rate=stage1_min_wr,
            top_n_candidates=top_n,
            initial_capital=capital,
            max_positions=0,
            risk_base_period=risk_base_period,
            specialist_windows=specialist_window_labels,
            catalog=cast(Literal["legacy", "pinescript_v1", "all"], catalog.lower()),
            stage_mode=cast(Literal["full", "stage1"], stage_mode.lower()),
            algorithm=cast(
                Literal["staged", "catcma_qd", "island_qd", "hyperband_qd", "smac_qd"],
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
            runner = run_dss_v2_search
            label = "DSS v2"
        with click.progressbar(length=n_trials, label=label, show_pos=True) as bar:
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
