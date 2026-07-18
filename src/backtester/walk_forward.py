"""Walk-forward validation for strategy candidates.

Implements the rolling anchor-point walk-forward analysis described in ADR-0034:
each IS window is independently optimized with Optuna; best params are evaluated
on the immediately following OOS window (no re-optimization).

Typical usage (via CLI):
    backtester walk-forward \\
        --data-dir data --symbol SOL-USDT-SWAP \\
        --from 2022-01-01 --to 2025-12-31 \\
        --is-months 12 --oos-months 6 \\
        --strategy strategies/backtester/.../nr4.json \\
        --trials 50 \\
        --output results/walk_forward

When --trials 0: skip optimization; evaluate each OOS window with base strategy
config params (fast per-year audit, no IS optimization).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from backtester.cli_runner import (
    BacktestArgs,
    OptimizerSearchArgs,
    StrategyConfig,
    _best_backtest_args,
    _best_strategy_params,
    _target_function,
    backtest_run_kwargs,
)
from backtester.data_contracts import StrategyData, StrategyInput
from backtester.optimizer import ParameterOptimizer
from backtester.registry import STRATEGIES
from backtester.tester import Backtester

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WalkForwardWindow:
    """Single IS/OOS window pair."""

    label: str
    symbol: str
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str


@dataclass(frozen=True)
class WindowMetrics:
    """Summary metrics extracted from a single backtest run."""

    total_return_pct: float
    trades: int
    win_rate: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    mandate_score: float


@dataclass
class WalkForwardWindowResult:
    """Outcome of one IS/OOS window in the walk-forward."""

    window: WalkForwardWindow
    best_params: dict[str, Any]
    is_metrics: WindowMetrics
    oos_metrics: WindowMetrics
    # True when the IS optimization was run; False in eval-only mode.
    optimized: bool = True


# ---------------------------------------------------------------------------
# Window generation (ADR-0034 §1)
# ---------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    """Add calendar months to a date without installing dateutil."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    # Clamp day to last day of the target month.
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def generate_windows(
    symbol: str,
    from_date: str,
    to_date: str,
    is_months: int,
    oos_months: int,
) -> list[WalkForwardWindow]:
    """Generate rolling anchor-point IS/OOS window pairs.

    Step = oos_months. The first OOS window starts at ``from_date + is_months``.
    The last window is the one whose OOS end does not exceed ``to_date``.

    Parameters
    ----------
    symbol:
        OKX SWAP symbol (for labelling only; data must be loaded separately).
    from_date, to_date:
        Inclusive date bounds in ``YYYY-MM-DD`` format.
    is_months:
        In-sample window size in calendar months.
    oos_months:
        Out-of-sample window size in calendar months.

    Returns
    -------
    list[WalkForwardWindow]
        Ordered list of window pairs, chronologically ascending OOS start.
    """
    from_dt = date.fromisoformat(from_date)
    to_dt = date.fromisoformat(to_date)

    windows: list[WalkForwardWindow] = []
    oos_start = _add_months(from_dt, is_months)

    while True:
        oos_end = _add_months(oos_start, oos_months) - timedelta(days=1)
        if oos_end > to_dt:
            break

        is_start = _add_months(oos_start, -is_months)
        is_end = oos_start - timedelta(days=1)

        label = (
            f"IS_{is_start.strftime('%Y%m')}_{is_end.strftime('%Y%m')}"
            f"_OOS_{oos_start.strftime('%Y%m')}_{oos_end.strftime('%Y%m')}"
        )

        windows.append(
            WalkForwardWindow(
                label=label,
                symbol=symbol,
                is_start=is_start.isoformat(),
                is_end=is_end.isoformat(),
                oos_start=oos_start.isoformat(),
                oos_end=oos_end.isoformat(),
            )
        )
        oos_start = _add_months(oos_start, oos_months)

    return windows


# ---------------------------------------------------------------------------
# Data slicing helpers
# ---------------------------------------------------------------------------


def _slice_df_by_date(df: Any, start: str, end: str) -> Any:
    """Slice a DataFrame by date range only when it has a DatetimeIndex.

    DataFrames with integer (RangeIndex) or other non-datetime indices are
    returned unchanged — they are lookup tables / feature stores whose rows
    are not individually date-addressable (e.g. extras like oi, ls_ratio).
    """
    import pandas as pd

    if not isinstance(df.index, pd.DatetimeIndex):
        return df
    mask = (df.index >= start) & (df.index <= end)
    return df.loc[mask]


def _slice_strategy_input(data: StrategyInput, start: str, end: str) -> StrategyInput:
    """Return a date-bounded slice of a StrategyInput without copying the full set."""
    if isinstance(data, StrategyData):
        p = data.primary
        mask = (p.index >= start) & (p.index <= end)
        sliced_primary = p.loc[mask]
        sliced_candles = {k: _slice_df_by_date(v, start, end) for k, v in data.candles.items()}
        sliced_extras = {k: _slice_df_by_date(v, start, end) for k, v in data.extras.items()}
        return StrategyData(
            primary=sliced_primary,
            candles=sliced_candles,
            extras=sliced_extras,
            metadata=data.metadata,
        )
    # Plain DataFrame
    import pandas as pd

    if isinstance(data.index, pd.DatetimeIndex):
        return data.loc[(data.index >= start) & (data.index <= end)]
    return data


def _input_is_empty(data: StrategyInput) -> bool:
    primary = data.primary if isinstance(data, StrategyData) else data
    return bool(primary.empty)


def _bar_count(data: StrategyInput) -> int:
    primary = data.primary if isinstance(data, StrategyData) else data
    return len(primary)


# ---------------------------------------------------------------------------
# Metrics extraction
# ---------------------------------------------------------------------------


def _extract_metrics(results: Any) -> WindowMetrics:
    """Pull key metrics from a ResultsAnalyzer."""
    m = results.metrics
    return WindowMetrics(
        total_return_pct=float(m.get("total_return_pct", 0.0)),
        trades=int(m.get("total_trades", 0)),
        win_rate=float(m.get("win_rate", 0.0)),
        max_drawdown=float(m.get("max_drawdown", 0.0)),
        profit_factor=float(m.get("profit_factor", 0.0)),
        sharpe_ratio=float(m.get("sharpe_ratio", -999.0)),
        mandate_score=-float("inf"),
    )


def _run_single_backtest(
    data: StrategyInput,
    cfg: StrategyConfig,
    args: BacktestArgs,
    strategy_params: dict[str, Any],
) -> WindowMetrics:
    """Run one backtest and return extracted metrics."""
    strategy_cls = STRATEGIES[cfg.name]
    strategy_instance = strategy_cls(strategy_params)
    bt = Backtester(data, strategy_instance.generate)
    results = bt.run(**backtest_run_kwargs(args))
    return _extract_metrics(results)


# ---------------------------------------------------------------------------
# Main walk-forward runner
# ---------------------------------------------------------------------------


def run_walk_forward(
    *,
    windows: list[WalkForwardWindow],
    cfg: StrategyConfig,
    base_args: BacktestArgs,
    optimizer_args: OptimizerSearchArgs,
    full_data: StrategyInput,
    output_folder: Path,
    logger: logging.Logger | None = None,
) -> list[WalkForwardWindowResult]:
    if logger is None:
        logger = logging.getLogger(__name__)
    """Run walk-forward analysis across all windows.

    For each window:
      1. Slice IS data and run Optuna (or use base params when trials=0).
      2. Slice OOS data and run one backtest with IS-best params.
      3. Record IS and OOS metrics.

    Parameters
    ----------
    windows:
        Ordered list of IS/OOS window pairs (from ``generate_windows``).
    cfg:
        Strategy config (name + params).
    base_args:
        Base BacktestArgs (capital, fees, leverage limits, etc.).
    optimizer_args:
        Optuna search-space config. If ``trials == 0``, skip optimization.
    full_data:
        Full historical StrategyInput already loaded (will be sliced in memory).
    output_folder:
        Root path for per-window artifacts.
    logger:
        Logger for progress messages.

    Returns
    -------
    list[WalkForwardWindowResult]
        One result per completed window (skipped windows are not included).
    """
    if cfg.name not in STRATEGIES:
        available = ", ".join(sorted(STRATEGIES.keys()))
        raise ValueError(f"Unknown strategy '{cfg.name}'. Available: {available}")

    strategy_cls = STRATEGIES[cfg.name]
    target = _target_function(optimizer_args.target)
    eval_only = optimizer_args.trials == 0
    results: list[WalkForwardWindowResult] = []

    for i, window in enumerate(windows):
        logger.info(
            "Walk-forward %d/%d  %s  IS: %s → %s  OOS: %s → %s",
            i + 1,
            len(windows),
            window.label,
            window.is_start,
            window.is_end,
            window.oos_start,
            window.oos_end,
        )

        is_data = _slice_strategy_input(full_data, window.is_start, window.is_end)
        oos_data = _slice_strategy_input(full_data, window.oos_start, window.oos_end)

        is_bars = _bar_count(is_data)
        oos_bars = _bar_count(oos_data)
        min_bars = 100

        if is_bars < min_bars or oos_bars < min_bars:
            logger.warning(
                "Skipping %s: IS=%d bars, OOS=%d bars (min %d required)",
                window.label,
                is_bars,
                oos_bars,
                min_bars,
            )
            continue

        window_dir = output_folder / "windows" / window.label
        window_dir.mkdir(parents=True, exist_ok=True)

        if eval_only:
            # Evaluation-only mode: use base strategy config params.
            best_params: dict[str, Any] = {}
            strategy_params = dict(cfg.params)
            is_metrics = _run_single_backtest(is_data, cfg, base_args, strategy_params)
            logger.info("IS (eval-only): return=%.1f%% trades=%d", is_metrics.total_return_pct, is_metrics.trades)
        else:
            # Optimize on IS window.
            logger.info("  Optimizing on IS (%d bars)…", is_bars)
            optimizer = ParameterOptimizer(
                df=is_data,
                strategy_class=strategy_cls,
                target=target,
                initial_capital=base_args.capital,
                taker_fee=base_args.taker_fee,
                maker_fee=base_args.maker_fee,
                position_ttl_bars=base_args.ttl,
                max_allowed_margin=base_args.max_allowed_margin,
                risk_base_period=base_args.risk_base_period,
                strategy_params=cfg.params,
                optimize_strategy_params=optimizer_args.optimize_strategy_params,
                risk_percent=base_args.risk_percent,
                risk_percent_range=optimizer_args.risk_percent_range,
                rrr_range=optimizer_args.rrr_range,
                trail_activation_rrr=base_args.trail_activation_rrr,
                trail_distance_atr=base_args.trail_distance_atr,
                trail_distance_atr_range=optimizer_args.trail_distance_atr_range,
                position_ttl_bars_range=optimizer_args.position_ttl_bars_range,
                tp_move_pct_range=optimizer_args.tp_move_pct_range,
                exit_geometry=base_args.exit_geometry,
                tp_move_pct=base_args.tp_move_pct,
                structural_sl_mode=base_args.structural_sl_mode,
                min_tp_move_pct=base_args.min_tp_move_pct,
                optimize_daily_limits=optimizer_args.optimize_daily_limits,
                optimize_trading_window=optimizer_args.optimize_trading_window,
            )

            study_path = window_dir / "study"
            best_params, study = optimizer.optimize(
                n_trials=optimizer_args.trials,
                show_progress=optimizer_args.show_progress,
                name=str(study_path),
            )

            # Persist IS optimization artifacts.
            trials_df = study.trials_dataframe()
            trials_df.to_csv(window_dir / "is_trials.csv", index=False)

            best_trial = study.best_trial
            best_payload = {
                "number": best_trial.number,
                "value": best_trial.value,
                "params": best_params,
                "user_attrs": dict(best_trial.user_attrs),
            }
            (window_dir / "is_best_trial.json").write_text(
                json.dumps(best_payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            strategy_params = _best_strategy_params(cfg=cfg, best_params=best_params)
            is_args = _best_backtest_args(base=base_args, best_params=best_params)
            is_metrics = _run_single_backtest(is_data, cfg, is_args, strategy_params)
            logger.info(
                "  IS best: return=%.1f%% trades=%d  params=%s",
                is_metrics.total_return_pct,
                is_metrics.trades,
                {k: v for k, v in best_params.items() if k in ("rrr", "risk_percent", "position_ttl_bars")},
            )

        # Evaluate on OOS window.
        logger.info("  Evaluating on OOS (%d bars)…", oos_bars)
        if eval_only:
            oos_args = base_args
        else:
            oos_args = _best_backtest_args(base=base_args, best_params=best_params)
        oos_metrics = _run_single_backtest(oos_data, cfg, oos_args, strategy_params)

        logger.info(
            "  OOS:  return=%.1f%%  trades=%d  win=%.1f%%  dd=%.1f%%",
            oos_metrics.total_return_pct,
            oos_metrics.trades,
            oos_metrics.win_rate,
            oos_metrics.max_drawdown,
        )

        # Persist OOS metrics.
        oos_payload = {
            "window": asdict(window),
            "best_params": best_params,
            "is_metrics": asdict(is_metrics),
            "oos_metrics": asdict(oos_metrics),
            "optimized": not eval_only,
        }
        (window_dir / "oos_metrics.json").write_text(
            json.dumps(oos_payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

        results.append(
            WalkForwardWindowResult(
                window=window,
                best_params=best_params,
                is_metrics=is_metrics,
                oos_metrics=oos_metrics,
                optimized=not eval_only,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def write_walk_forward_report(
    *,
    results: list[WalkForwardWindowResult],
    symbol: str,
    is_months: int,
    oos_months: int,
    from_date: str,
    to_date: str,
    output_folder: Path,
    logger: logging.Logger | None = None,
) -> None:
    if logger is None:
        logger = logging.getLogger(__name__)
    """Write summary.md and summary.json to output_folder."""

    # ---- JSON summary ----
    summary_payload = {
        "symbol": symbol,
        "is_months": is_months,
        "oos_months": oos_months,
        "from_date": from_date,
        "to_date": to_date,
        "total_windows": len(results),
        "windows": [
            {
                "label": r.window.label,
                "is_start": r.window.is_start,
                "is_end": r.window.is_end,
                "oos_start": r.window.oos_start,
                "oos_end": r.window.oos_end,
                "optimized": r.optimized,
                "best_params": r.best_params,
                "is": asdict(r.is_metrics),
                "oos": asdict(r.oos_metrics),
                "degradation": _degradation(r.is_metrics.total_return_pct, r.oos_metrics.total_return_pct),
            }
            for r in results
        ],
    }
    summary_json = output_folder / "summary.json"
    summary_json.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    logger.info("Walk-forward summary JSON → %s", summary_json)

    # ---- Markdown report ----
    md = _build_markdown_report(results, symbol=symbol, is_months=is_months, oos_months=oos_months, from_date=from_date, to_date=to_date)
    summary_md = output_folder / "summary.md"
    summary_md.write_text(md, encoding="utf-8")
    logger.info("Walk-forward summary MD  → %s", summary_md)


def _degradation(is_ret: float, oos_ret: float) -> float | None:
    """OOS/IS ratio; None when IS is near zero (division guard)."""
    if abs(is_ret) < 0.5:
        return None
    return round(oos_ret / is_ret, 3)


def _sign(v: float) -> str:
    return "+" if v >= 0 else ""


def _build_markdown_report(
    results: list[WalkForwardWindowResult],
    *,
    symbol: str,
    is_months: int,
    oos_months: int,
    from_date: str,
    to_date: str,
) -> str:
    mode = "optimized per IS window" if results and results[0].optimized else "eval-only (base params)"
    lines = [
        f"# Walk-forward analysis — {symbol}",
        "",
        f"IS window: **{is_months} months** | OOS window: **{oos_months} months** | "
        f"Range: {from_date} → {to_date} | Mode: {mode}",
        "",
    ]

    if not results:
        lines.append("_No windows completed (insufficient data)._")
        return "\n".join(lines)

    # Table header
    lines += [
        "| # | IS period | OOS period | IS return | OOS return | Degrad | OOS trades | OOS win% | OOS DD% |",
        "|---|-----------|------------|-----------|------------|--------|------------|----------|---------|",
    ]

    oos_positive = 0
    oos_returns = []

    for i, r in enumerate(results, 1):
        w = r.window
        is_ret = r.is_metrics.total_return_pct
        oos_ret = r.oos_metrics.total_return_pct
        deg = _degradation(is_ret, oos_ret)
        deg_str = f"{deg:.2f}" if deg is not None else "—"

        if oos_ret > 0:
            oos_positive += 1
        oos_returns.append(oos_ret)

        lines.append(
            f"| {i} "
            f"| {w.is_start[:7]}→{w.is_end[:7]} "
            f"| {w.oos_start[:7]}→{w.oos_end[:7]} "
            f"| {_sign(is_ret)}{is_ret:.1f}% "
            f"| {_sign(oos_ret)}{oos_ret:.1f}% "
            f"| {deg_str} "
            f"| {r.oos_metrics.trades} "
            f"| {r.oos_metrics.win_rate:.1f}% "
            f"| {r.oos_metrics.max_drawdown:.1f}% |"
        )

    n = len(results)
    avg_oos = sum(oos_returns) / n if n else 0.0
    pct_positive = oos_positive / n * 100 if n else 0.0

    lines += [
        "",
        "## Summary",
        "",
        f"- **OOS windows positive:** {oos_positive}/{n} ({pct_positive:.0f}%)",
        f"- **Average OOS return:** {_sign(avg_oos)}{avg_oos:.1f}%",
        f"- **Min OOS return:** {min(oos_returns, default=0.0):.1f}%",
        f"- **Max OOS return:** {max(oos_returns, default=0.0):.1f}%",
        "",
    ]

    # Interpretation hint
    if pct_positive >= 70:
        verdict = "Strong OOS generalization. The concept appears to have genuine edge across regimes."
    elif pct_positive >= 50:
        verdict = "Moderate OOS generalization. The edge is real but regime-dependent; consider a regime filter."
    elif pct_positive >= 30:
        verdict = "Weak OOS generalization. The concept is marginal; high risk of forward curve-fit."
    else:
        verdict = "Poor OOS generalization. The strategy is likely overfit to specific market regimes. Discard or redesign."

    lines += [f"**Interpretation:** {verdict}", ""]
    return "\n".join(lines)
