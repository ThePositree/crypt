"""
Backtest harness CLI entry point — docs/backtest.md §3, §5.

Usage:
    uv run python -m crypt.backtest \\
        --from 2025-01-01 \\
        --to   2026-05-01 \\
        --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \\
        --weights config/weights.yaml \\
        --report-dir reports/backtest_2026-05/ \\
        [--no-fees] [--slippage-bps 5] [--walk-forward-folds 5] [--seed 42]

Exit codes:
    0 — completed and report written.
    1 — data preconditions failed.
    2 — runtime error.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm

from crypt.aggregator.ensemble import aggregate
from crypt.aggregator.weights import WeightsConfig
from crypt.backtest.execution_sim import ExecutionSim, ZeroFundingModel
from crypt.backtest.labels import compute_labels
from crypt.backtest.metrics import (
    compute_buy_and_hold,
    compute_random_direction_baseline,
    generate_metrics,
)
from crypt.backtest.optimizer import (
    OptResult,
    aggregate_weights_across_folds,
    run_optimizer,
)
from crypt.backtest.recorder import BacktestRecorder
from crypt.backtest.replay import ReplayContextBuilder, ReplayParquetStore
from crypt.backtest.report import build_report, write_report
from crypt.backtest.walkforward import generate_folds, slice_verdicts
from crypt.data.store import ParquetStore
from crypt.decision.filters import DecisionFilter
from crypt.engines.derivatives import DerivativesEngine
from crypt.engines.meanrev import MeanRevEngine
from crypt.engines.regime import RegimeEngine
from crypt.engines.smc_liquidity import SMCLiquidityEngine
from crypt.engines.smc_order_blocks import SMCOrderBlocksEngine
from crypt.engines.smc_structure import SMCStructureEngine
from crypt.engines.trend import TrendEngine
from crypt.engines.volatility import VolatilityEngine
from crypt.models import EvaluationContext, Regime, Signal, Timeframe, VolRegime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_H4_BARS_WARMUP = 250  # EMA-200 + buffer
_D1_BARS_WARMUP = 60

# ATR multiplier for SL price (matches paper trading spec §5).
_SL_ATR_MULT = 2.0
# RRR for position sizing in execution sim.
_DEFAULT_RRR = 2.0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="crypt backtest harness (M2) — docs/backtest.md",
    )
    p.add_argument(
        "--from", dest="from_dt", required=True, help="Start date (ISO, e.g. 2025-01-01)"
    )
    p.add_argument("--to", dest="to_dt", required=True, help="End date (ISO, e.g. 2026-05-01)")
    p.add_argument(
        "--symbols",
        default="SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP",
        help="Comma-separated OKX instIds",
    )
    p.add_argument("--weights", default="config/weights.yaml", help="Path to weights YAML")
    p.add_argument("--report-dir", default="reports/backtest/", help="Output directory for report")
    p.add_argument("--data-dir", default="data", help="Parquet data directory")
    p.add_argument("--no-fees", action="store_true", help="Skip fee model (debugging only)")
    p.add_argument(
        "--slippage-bps", type=float, default=5.0, help="Slippage in basis points (default 5)"
    )
    p.add_argument(
        "--walk-forward-folds", type=int, default=5, help="Walk-forward folds (default 5)"
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    p.add_argument(
        "--position-ttl-bars", type=int, default=6, help="Position TTL in H4 bars (default 6)"
    )
    p.add_argument(
        "--initial-capital", type=float, default=10_000.0, help="Initial capital (default 10000)"
    )
    p.add_argument("--quiet", action="store_true", help="Suppress per-tick console output")
    p.add_argument(
        "--no-optimize", action="store_true", help="Skip weight optimization (just replay + report)"
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Data preconditions (§4)
# ---------------------------------------------------------------------------


def _check_preconditions(
    store: ParquetStore,
    symbols: list[str],
    from_dt: datetime,
    to_dt: datetime,
) -> bool:
    """Return True if all preconditions pass, else log errors and return False."""
    ok = True
    h4_warmup_start = from_dt - timedelta(hours=4 * _H4_BARS_WARMUP)
    d1_warmup_start = from_dt - timedelta(days=_D1_BARS_WARMUP)

    for sym in symbols:
        h4 = store.load_candles(sym, Timeframe.H4, limit=None)
        if h4.empty:
            logger.error("Precondition FAIL: no H4 candles for {}", sym)
            ok = False
            continue

        h4_times = pd.to_datetime(h4["open_time"], utc=True)
        if h4_times.min() > _utc_timestamp(h4_warmup_start):
            logger.error(
                "Precondition FAIL: {} H4 history starts at {} — need data from {} for warm-up",
                sym,
                h4_times.min().date(),
                h4_warmup_start.date(),
            )
            ok = False

        if h4_times.max() < _utc_timestamp(to_dt) - timedelta(hours=4):
            logger.error(
                "Precondition FAIL: {} H4 history ends at {} — need coverage to {}",
                sym,
                h4_times.max().date(),
                to_dt.date(),
            )
            ok = False

        d1 = store.load_candles(sym, Timeframe.D1, limit=None)
        if d1.empty:
            logger.error("Precondition FAIL: no D1 candles for {}", sym)
            ok = False
            continue

        d1_times = pd.to_datetime(d1["open_time"], utc=True)
        if d1_times.min() > _utc_timestamp(d1_warmup_start):
            logger.error(
                "Precondition FAIL: {} D1 history starts at {} — need data from {} for warm-up",
                sym,
                d1_times.min().date(),
                d1_warmup_start.date(),
            )
            ok = False

        if d1_times.max() < _utc_timestamp(to_dt) - timedelta(days=1):
            logger.error(
                "Precondition FAIL: {} D1 history ends at {} — need coverage to {}",
                sym,
                d1_times.max().date(),
                to_dt.date(),
            )
            ok = False

    return ok


def _utc_timestamp(dt: datetime | pd.Timestamp) -> pd.Timestamp:
    """Convert naive or aware datetimes to a UTC pandas Timestamp."""
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


# ---------------------------------------------------------------------------
# H4 tick iterator
# ---------------------------------------------------------------------------


def _h4_boundaries(from_dt: datetime, to_dt: datetime) -> list[datetime]:
    """Return all H4-aligned UTC datetimes in [from_dt, to_dt)."""
    start = _snap_to_h4(from_dt)
    ticks: list[datetime] = []
    t = start
    while t < to_dt:
        ticks.append(t)
        t += timedelta(hours=4)
    return ticks


def _snap_to_h4(dt: datetime) -> datetime:
    """Round dt up to the next H4 boundary."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    total_hours = int(dt.timestamp() // 3600)
    snapped_hours = ((total_hours + 3) // 4) * 4
    return datetime.fromtimestamp(snapped_hours * 3600, tz=UTC)


# ---------------------------------------------------------------------------
# Replay loop
# ---------------------------------------------------------------------------


def _run_replay(
    store: ParquetStore,
    symbols: list[str],
    from_dt: datetime,
    to_dt: datetime,
    weights_cfg: WeightsConfig,
    quiet: bool = False,
) -> tuple[BacktestRecorder, dict[str, pd.DataFrame]]:
    """
    Run the full replay loop for [from_dt, to_dt).

    Returns:
        recorder — all verdicts (all symbols, all ticks)
        h4_ohlcv_by_sym — full H4 OHLCV DataFrame per symbol (for labels + sim)
    """
    replay_store = ReplayParquetStore(store)
    ctx_builder = ReplayContextBuilder(replay_store)
    decision_filter = DecisionFilter(confidence_threshold=0, cooldown_hours=0)

    trend_eng = TrendEngine()
    meanrev_eng = MeanRevEngine()
    deriv_eng = DerivativesEngine()
    smc_structure_eng = SMCStructureEngine()
    smc_order_blocks_eng = SMCOrderBlocksEngine()
    smc_liquidity_eng = SMCLiquidityEngine()
    vol_eng = VolatilityEngine()
    regime_eng = RegimeEngine()

    recorder = BacktestRecorder()
    ticks = _h4_boundaries(from_dt, to_dt)

    # Pre-load full H4 OHLCV for labels computation (needed after replay).
    h4_ohlcv_by_sym: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = store.load_candles(sym, Timeframe.H4, limit=None)
        if not df.empty:
            h4_ohlcv_by_sym[sym] = df

    desc = f"Replay {from_dt.date()} → {to_dt.date()}"
    for tick_time in tqdm(ticks, desc=desc, disable=quiet):
        for sym in symbols:
            try:
                ctx: EvaluationContext = ctx_builder.build(sym, tick_time)

                vol_signal: Signal = vol_eng.evaluate(ctx)
                vol_regime: VolRegime = str(vol_signal.meta.get("vol_regime", "normal"))  # type: ignore[assignment]
                ctx.vol_regime = vol_regime

                regime_signal: Signal = regime_eng.evaluate(ctx)
                regime_str: str = str(regime_signal.meta.get("regime", "RANGING"))
                regime = Regime(regime_str)

                trend_signal = trend_eng.evaluate(ctx)
                meanrev_signal = meanrev_eng.evaluate(ctx)
                deriv_signal = deriv_eng.evaluate(ctx)
                smc_structure_signal = smc_structure_eng.evaluate(ctx)
                smc_order_blocks_signal = smc_order_blocks_eng.evaluate(ctx)
                smc_liquidity_signal = smc_liquidity_eng.evaluate(ctx)

                all_signals: list[Signal] = [
                    trend_signal,
                    meanrev_signal,
                    deriv_signal,
                    smc_structure_signal,
                    smc_order_blocks_signal,
                    smc_liquidity_signal,
                    vol_signal,
                    regime_signal,
                ]

                verdict = aggregate(
                    signals=all_signals,
                    regime=regime,
                    weights_cfg=weights_cfg,
                    symbol=sym,
                    vol_regime=vol_regime,
                )
                verdict = verdict.model_copy(update={"produced_at": tick_time})
                guarded = decision_filter.apply_guard(verdict)
                recorder.record(guarded)

            except Exception as exc:
                logger.warning("Replay tick {} {}: {}", tick_time, sym, exc)

    return recorder, h4_ohlcv_by_sym


# ---------------------------------------------------------------------------
# Build simulation DataFrame for ExecutionSim
# ---------------------------------------------------------------------------


def _build_sim_df(
    verdicts_df: pd.DataFrame,
    h4_ohlcv: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge verdicts with H4 OHLCV to build the ExecutionSim input DataFrame.

    ExecutionSim expects: open, high, low, close, signal, sl_price, symbol.
    signal: +1 BUY, -1 SELL, 0 HOLD.
    sl_price: entry_price +/- SL_ATR_MULT * ATR(14).
    """
    if h4_ohlcv.empty or verdicts_df.empty:
        return pd.DataFrame()

    # Build a full H4 price frame indexed by tick_time (= bar close time).
    ohlcv = h4_ohlcv.copy()
    ohlcv["open_time"] = pd.to_datetime(ohlcv["open_time"], utc=True)
    # tick_time = bar close time = open_time + 4h
    ohlcv["tick_time"] = ohlcv["open_time"] + timedelta(hours=4)
    ohlcv = ohlcv.set_index("tick_time").sort_index()

    # Compute ATR(14) on H4 bars.
    high = ohlcv["h"].astype(float)
    low = ohlcv["l"].astype(float)
    close = ohlcv["c"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(
        axis=1
    )
    atr = tr.rolling(14, min_periods=1).mean()
    ohlcv["atr"] = atr

    vdf = verdicts_df.copy()
    vdf["tick_time"] = pd.to_datetime(vdf["tick_time"], utc=True)

    merged = vdf.merge(
        ohlcv[["o", "h", "l", "c", "atr"]].rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close"}
        ),
        left_on="tick_time",
        right_index=True,
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()

    signal_map = {"BUY": 1, "SELL": -1, "HOLD": 0}
    merged["signal"] = merged["decision"].map(signal_map).fillna(0).astype(int)

    # SL price: entry = close at tick_time (the bar that just closed).
    # For BUY: sl = close - SL_ATR_MULT * atr  (below entry)
    # For SELL: sl = close + SL_ATR_MULT * atr  (above entry)
    merged["entry_price"] = merged["close"].astype(float)
    merged["sl_price"] = np.where(
        merged["signal"] == 1,
        merged["close"] - _SL_ATR_MULT * merged["atr"],
        np.where(
            merged["signal"] == -1,
            merged["close"] + _SL_ATR_MULT * merged["atr"],
            merged["close"],  # HOLD — not used
        ),
    )

    return merged.set_index("tick_time").sort_index()


# ---------------------------------------------------------------------------
# Build funding model
# ---------------------------------------------------------------------------


def _build_funding_model(symbols: list[str]) -> dict[str, ZeroFundingModel]:
    # Funding data removed per ADR-0016 — always use ZeroFundingModel.
    return {sym: ZeroFundingModel() for sym in symbols}


# ---------------------------------------------------------------------------
# Git / metadata helpers
# ---------------------------------------------------------------------------


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _file_sha(path: str) -> str:
    try:
        with Path(path).open("rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:12]
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Return exit code: 0=OK, 1=preconditions, 2=runtime error."""
    args = _parse_args(argv)

    # Parse date arguments.
    try:
        from_dt = datetime.fromisoformat(args.from_dt).replace(tzinfo=UTC)
        to_dt = datetime.fromisoformat(args.to_dt).replace(tzinfo=UTC)
    except ValueError as exc:
        logger.error("Invalid date format: {}", exc)
        return 1

    if to_dt <= from_dt:
        logger.error("--to must be after --from")
        return 1

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        logger.error("No symbols provided")
        return 1

    data_dir = Path(args.data_dir)
    report_dir = Path(args.report_dir)
    weights_path = Path(args.weights)
    rng = np.random.default_rng(args.seed)

    if args.walk_forward_folds == 1:
        logger.warning(
            "WARNING: --walk-forward-folds 1 produces a single train/test split. "
            "This result is not robust to regime variation."
        )

    # Setup.
    store = ParquetStore(data_dir)
    weights_cfg = WeightsConfig.load(weights_path)

    # §4: Preconditions.
    logger.info("Checking data preconditions for {} symbols ...", len(symbols))
    if not _check_preconditions(store, symbols, from_dt, to_dt):
        logger.error(
            "Data preconditions failed. Run: uv run python -m crypt.backfill "
            "--symbol <sym> --from {} --to {}",
            from_dt.date(),
            to_dt.date(),
        )
        return 1

    logger.info(
        "Preconditions OK. Starting replay {} → {} for {}", from_dt.date(), to_dt.date(), symbols
    )

    try:
        # §5: Replay loop.
        recorder, h4_ohlcv_by_sym = _run_replay(
            store, symbols, from_dt, to_dt, weights_cfg, quiet=args.quiet
        )
        logger.info("Replay complete: {} verdicts", len(recorder))

        verdicts_df = recorder.to_dataframe()
        if verdicts_df.empty:
            logger.error("No verdicts produced by replay loop")
            return 2

        # §6: Forward labels (per symbol).
        labelled_dfs: list[pd.DataFrame] = []
        for sym in symbols:
            sym_verdicts = verdicts_df[verdicts_df["symbol"] == sym].copy()
            ohlcv = h4_ohlcv_by_sym.get(sym, pd.DataFrame())
            if not ohlcv.empty:
                labelled = compute_labels(sym_verdicts, ohlcv)
                if not labelled.empty:
                    labelled_dfs.append(labelled)

        all_labelled = (
            pd.concat(labelled_dfs, ignore_index=True) if labelled_dfs else pd.DataFrame()
        )

        # Build combined sim DataFrame (all symbols, time-ordered).
        sim_dfs: list[pd.DataFrame] = []
        for sym in symbols:
            sym_verdicts = verdicts_df[verdicts_df["symbol"] == sym].copy()
            ohlcv = h4_ohlcv_by_sym.get(sym, pd.DataFrame())
            if not ohlcv.empty and not sym_verdicts.empty:
                sim_df = _build_sim_df(sym_verdicts, ohlcv)
                if not sim_df.empty:
                    sim_df["symbol"] = sym
                    sim_dfs.append(sim_df)

        combined_sim_df = pd.DataFrame()
        if sim_dfs:
            combined_sim_df = pd.concat(sim_dfs).sort_index()

        # Funding removed per ADR-0016; always ZeroFundingModel.
        funding_models = _build_funding_model(symbols)
        funding_model = _MultiSymbolFundingModel(funding_models)

        # Fee/slippage config.
        taker_fee = 0.0005 if not args.no_fees else 0.0
        maker_fee = 0.0002 if not args.no_fees else 0.0

        # §7: Walk-forward folds.
        folds = generate_folds(from_dt, to_dt, args.walk_forward_folds)
        logger.info("Generated {} walk-forward folds", len(folds))

        fold_results: list[dict[str, Any]] = []
        fold_weights_list: list[dict[str, Any]] = []
        any_guard_fired = False
        overall_violations: list[str] = []

        for fold in folds:
            logger.info(
                "Fold {}: train={} → {}, test={} → {}",
                fold.fold_index,
                fold.train_from.date(),
                fold.train_to.date(),
                fold.test_from.date(),
                fold.test_to.date(),
            )

            train_labelled = slice_verdicts(all_labelled, fold.train_from, fold.train_to)
            test_labelled = slice_verdicts(all_labelled, fold.test_from, fold.test_to)

            # §9: Weight optimisation (unless --no-optimize).
            opt_result: OptResult | None = None
            if not args.no_optimize and not train_labelled.empty and not test_labelled.empty:
                logger.info(
                    "Fold {}: optimizing weights on {} train verdicts ...",
                    fold.fold_index,
                    len(train_labelled),
                )
                opt_result = run_optimizer(train_labelled, test_labelled)
                fold_weights_list.append(opt_result.weights)
                if opt_result.guard_fired:
                    any_guard_fired = True
                    overall_violations.extend(opt_result.guard_violations)

            # Run ExecutionSim on test slice with optimal weights.
            test_sim_df = pd.DataFrame()
            if not combined_sim_df.empty:
                # If we have optimal weights, re-run verdict decisions with them.
                if opt_result and not opt_result.guard_fired and opt_result.weights:
                    # Re-apply decisions from test labelled verdicts
                    from crypt.backtest.optimizer import _apply_weights

                    test_verdicts_refined = _apply_weights(
                        slice_verdicts(verdicts_df, fold.test_from, fold.test_to),
                        opt_result.weights,
                    )
                    # Build sim df from refined decisions
                    sym_sim_dfs = []
                    for sym in symbols:
                        sym_v = test_verdicts_refined[test_verdicts_refined["symbol"] == sym].copy()
                        ohlcv = h4_ohlcv_by_sym.get(sym, pd.DataFrame())
                        if not ohlcv.empty and not sym_v.empty:
                            s_df = _build_sim_df(sym_v, ohlcv)
                            if not s_df.empty:
                                s_df["symbol"] = sym
                                sym_sim_dfs.append(s_df)
                    if sym_sim_dfs:
                        test_sim_df = pd.concat(sym_sim_dfs).sort_index()
                else:
                    mask_lo = combined_sim_df.index >= _utc_timestamp(fold.test_from)
                    mask_hi = combined_sim_df.index < _utc_timestamp(fold.test_to)
                    test_sim_df = combined_sim_df[mask_lo & mask_hi]

            trades_df = pd.DataFrame()
            if not test_sim_df.empty:
                sim = ExecutionSim(
                    initial_capital=args.initial_capital,
                    taker_fee=taker_fee,
                    maker_fee=maker_fee,
                    risk_percent=1.0,
                    rrr=_DEFAULT_RRR,
                    position_ttl_bars=args.position_ttl_bars,
                    sl_pessimism_pct=0.0,
                    is_isolated_futures=True,
                    bar_exit_policy="worst_case",
                    funding_model=funding_model,
                )
                trades_df = sim.run(test_sim_df)

            # Compute metrics.
            fold_metrics = generate_metrics(
                trades_df,
                labelled_verdicts=test_labelled if not test_labelled.empty else None,
                n_bootstrap=1000,
                rng=rng,
            )

            # Build equity charts.
            from crypt.backtest.report import _per_symbol_equity_charts

            eq_charts = _per_symbol_equity_charts(trades_df, f"Fold {fold.fold_index}")

            fold_results.append(
                {
                    "fold_index": fold.fold_index,
                    "train_from": str(fold.train_from.date()),
                    "train_to": str(fold.train_to.date()),
                    "test_from": str(fold.test_from.date()),
                    "test_to": str(fold.test_to.date()),
                    "trades_df": trades_df,
                    "metrics": fold_metrics,
                    "labelled_verdicts": test_labelled,
                    "equity_charts": eq_charts,
                }
            )

        # §10/11: Aggregate metrics across all test trades.
        all_test_trades = (
            pd.concat(
                [fr["trades_df"] for fr in fold_results if not fr["trades_df"].empty],
                ignore_index=True,
            )
            if any(not fr["trades_df"].empty for fr in fold_results)
            else pd.DataFrame()
        )

        all_test_labelled = (
            pd.concat(
                [
                    fr["labelled_verdicts"]
                    for fr in fold_results
                    if not fr["labelled_verdicts"].empty
                ],
                ignore_index=True,
            )
            if any(not fr["labelled_verdicts"].empty for fr in fold_results)
            else pd.DataFrame()
        )

        aggregate_metrics = generate_metrics(
            all_test_trades,
            labelled_verdicts=all_test_labelled if not all_test_labelled.empty else None,
            n_bootstrap=1000,
            rng=rng,
        )

        # §11: Baselines.
        baselines: dict[str, Any] = {}
        for sym in symbols:
            ohlcv = h4_ohlcv_by_sym.get(sym)
            if ohlcv is not None:
                bah = compute_buy_and_hold(
                    ohlcv,
                    from_dt=_utc_timestamp(from_dt),
                    to_dt=_utc_timestamp(to_dt),
                )
                baselines[f"Buy-and-hold {sym}"] = bah

        baselines["Always HOLD"] = {
            "total_return_pct": 0.0,
            "max_drawdown": 0.0,
            "note": "zero cost baseline",
        }

        if not all_test_labelled.empty:
            rand = compute_random_direction_baseline(
                all_test_labelled, n_seeds=100, rng_seed=args.seed
            )
            baselines["Random direction"] = {
                "total_return_pct": round(rand["expectancy_h24_mean"] * 100, 2),
                "max_drawdown": "N/A",
                "note": f"same alert frequency, random direction; hit_rate={rand['hit_rate_mean']:.2%}",
            }

        # §13: Recommended weights.
        recommended_weights: dict[str, Any] = {}
        optimal_weights: dict[str, Any] = {}
        if fold_weights_list:
            recommended_weights = aggregate_weights_across_folds(fold_weights_list)
            optimal_weights = fold_weights_list[-1] if fold_weights_list else {}

        # Build metadata.
        meta: dict[str, Any] = {
            "generated_at": datetime.now(UTC).isoformat(),
            "git_sha": _git_sha(),
            "weights_sha": _file_sha(str(weights_path)),
            "from_dt": str(from_dt.date()),
            "to_dt": str(to_dt.date()),
            "symbols": ", ".join(symbols),
            "n_folds": args.walk_forward_folds,
            "seed": args.seed,
            "slippage_bps": args.slippage_bps,
            "no_fees": args.no_fees,
            "initial_capital": args.initial_capital,
            "position_ttl_bars": args.position_ttl_bars,
            "total_verdicts": len(verdicts_df),
            "total_test_trades": len(all_test_trades),
        }

        # §12: Report.
        report_html = build_report(
            meta=meta,
            fold_results=fold_results,
            aggregate_metrics=aggregate_metrics,
            baselines=baselines,
            recommended_weights=recommended_weights,
            guard_violations=overall_violations,
        )

        write_report(
            report_dir=report_dir,
            report_html=report_html,
            meta=meta,
            trades_df=all_test_trades,
            verdicts_df=verdicts_df,
            optimal_weights=optimal_weights,
            recommended_weights=recommended_weights,
            guard_fired=any_guard_fired,
        )

        logger.info("Report written to {}", report_dir)

        if any_guard_fired:
            logger.warning(
                "Sanity guard fired — weights written to weights.candidate.yaml. Violations: {}",
                "; ".join(overall_violations),
            )

    except Exception as exc:
        logger.exception("Runtime error in backtest harness: {}", exc)
        return 2

    return 0


# ---------------------------------------------------------------------------
# Multi-symbol funding model dispatcher
# ---------------------------------------------------------------------------


class _MultiSymbolFundingModel:
    """Routes charge() calls to the correct per-symbol funding model."""

    def __init__(
        self,
        models: dict[str, ZeroFundingModel],
    ) -> None:
        self._models = models
        self._zero = ZeroFundingModel()

    def charge(self, position_value: float, symbol: str, bar_ts: pd.Timestamp) -> float:
        m = self._models.get(symbol, self._zero)
        return m.charge(position_value, symbol, bar_ts)


if __name__ == "__main__":
    sys.exit(main())
