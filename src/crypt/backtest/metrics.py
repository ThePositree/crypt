"""
Backtest metrics — adapted from backtester/src/backtester/results_analyzer.py.

§18.4 fixes applied during porting:
  🟡 Equity-curve duplicate exit_time fix: removed drop_duplicates(subset="exit_time");
     trades sorted by (exit_time, entry_time) and running capital sum rebuilt.
  🟠 Sharpe warning when n_monthly_samples < 6; trade-level Sharpe added.

Bootstrap CI (docs/backtest.md §10): compute_bootstrap_ci() resamples
verdicts 1000 times to produce 95% CI for any scalar metric.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

# ---------------------------------------------------------------------------
# Core metric computations (ported from ResultsAnalyzer)
# ---------------------------------------------------------------------------


def compute_basic_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Win rate, profit factor, avg win/loss — from ResultsAnalyzer._compute_basic_metrics."""
    total = len(df)
    if total == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_pnl_abs": 0.0,
            "avg_pnl_abs": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": float("inf"),
        }

    wins = df[df["pnl_abs"] > 0]
    losses = df[df["pnl_abs"] < 0]

    win_rate = len(wins) / total
    total_pnl = float(df["pnl_abs"].sum())
    avg_pnl = float(df["pnl_abs"].mean())
    avg_win = float(wins["pnl_abs"].mean()) if len(wins) else 0.0
    avg_loss = float(losses["pnl_abs"].mean()) if len(losses) else 0.0

    loss_sum = float(losses["pnl_abs"].sum())
    profit_factor = abs(float(wins["pnl_abs"].sum()) / loss_sum) if loss_sum != 0 else float("inf")

    return {
        "total_trades": total,
        "win_rate": float(win_rate),
        "total_pnl_abs": total_pnl,
        "avg_pnl_abs": avg_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": float(profit_factor),
    }


def compute_exit_distribution(df: pd.DataFrame) -> dict[str, int]:
    """TP/SL/TTL counts — from ResultsAnalyzer._compute_exit_distribution."""
    return {str(k): int(v) for k, v in df["exit_reason"].value_counts().items()}


def build_equity_curve(df: pd.DataFrame) -> tuple[pd.Series, float, float, float]:
    """
    Build equity curve from trade history.

    §18.4 fix: no drop_duplicates on exit_time.  Sort by (exit_time, entry_time)
    and take a running capital sum so multi-symbol simultaneous exits are all
    represented correctly.

    Returns (equity_curve, initial_capital, final_capital, total_return_pct).
    """
    sorted_df = df.sort_values(["exit_time", "entry_time"])
    equity = sorted_df.set_index("exit_time")["capital_after"]
    equity.index = pd.to_datetime(equity.index, utc=True)

    initial_capital = float(sorted_df.iloc[0]["capital_before"])
    final_capital = float(equity.iloc[-1])
    total_return_pct = (final_capital - initial_capital) / initial_capital * 100
    return equity, initial_capital, final_capital, float(total_return_pct)


def compute_drawdown_metrics(equity_curve: pd.Series) -> dict[str, float]:
    """Rolling peak-to-trough drawdown — from ResultsAnalyzer._compute_drawdown_metrics."""
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return {"max_drawdown": float(drawdown.min())}


def compute_sharpe_ratio(
    equity_curve: pd.Series,
    initial_capital: float,
    risk_free_rate_annual: float = 0.02,
) -> tuple[float, int, str | None]:
    """
    Annualised Sharpe from monthly returns — from ResultsAnalyzer._compute_sharpe_ratio.

    §18.4 fix: if n_monthly_samples < 6 emit a warning string.
    Also returns the trade-level Sharpe for small-sample cases.

    Returns
    -------
    (sharpe_annual, n_monthly_samples, warning_message_or_None)
    """
    monthly_capital = equity_curve.resample("ME").last()
    n = len(monthly_capital)
    warning: str | None = None

    if n < 2:
        return 0.0, n, "⚠ Sharpe ratio requires ≥ 2 months of data — not computed."

    if n < 6:
        warning = f"⚠ Sharpe ratio computed from only {n} months — not statistically reliable."

    monthly_returns = monthly_capital.pct_change(fill_method=None)
    monthly_returns.iloc[0] = (monthly_capital.iloc[0] - initial_capital) / initial_capital
    sd = float(monthly_returns.std())
    if sd == 0:
        return 0.0, n, warning

    mr = float(monthly_returns.mean())
    rfr_monthly = (1 + risk_free_rate_annual) ** (1 / 12) - 1
    sr_annual = (mr - rfr_monthly) / sd * math.sqrt(12)
    return round(float(sr_annual), 4), n, warning


def compute_trade_level_sharpe(df: pd.DataFrame) -> float:
    """
    Trade-level Sharpe: mean(pnl_rel) / std(pnl_rel) * sqrt(annualised_freq).

    More stable than monthly Sharpe for short test slices.
    Annualised trade frequency = trades_per_year.
    """
    if len(df) < 2:
        return 0.0
    pnl = df["pnl_rel"].astype(float)
    std = float(pnl.std())
    if std == 0:
        return 0.0
    mean = float(pnl.mean())
    # Estimate annualised trade frequency.
    date_range = pd.to_datetime(df["exit_time"]).max() - pd.to_datetime(df["entry_time"]).min()
    years = float(date_range.total_seconds()) / (365.25 * 24 * 3600)
    if years <= 0:
        return 0.0
    trades_per_year = len(df) / years
    return round(float(mean / std * math.sqrt(trades_per_year)), 4)


def compute_monthly_returns_pct(
    equity_curve: pd.Series,
    initial_capital: float,
) -> dict[str, dict[str, float]]:
    """Monthly returns table — from ResultsAnalyzer._compute_monthly_returns_pct."""
    monthly_capital = equity_curve.resample("ME").last()
    if len(monthly_capital) == 0:
        return {}
    monthly_returns = monthly_capital.pct_change(fill_method=None).fillna(0) * 100
    monthly_returns.iloc[0] = (monthly_capital.iloc[0] - initial_capital) / initial_capital * 100
    monthly_returns_abs = (monthly_capital - initial_capital) / initial_capital * 100

    return {
        str(period): {
            "ret": round(float(ret), 2),
            "ret_abs": round(float(ret_abs), 2),
        }
        for period, ret, ret_abs in zip(
            monthly_returns.index.strftime("%Y-%m"),
            monthly_returns.values,
            monthly_returns_abs.values,
            strict=False,
        )
    }


def compute_side_metrics(df: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    """Metrics for long/short sides — from ResultsAnalyzer._compute_side_metrics."""

    def _subset_metrics(sub: pd.DataFrame) -> dict[str, Any]:
        if sub.empty:
            return {
                "count": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "profit_factor": "inf",
            }
        basic = compute_basic_metrics(sub)
        pf = basic["profit_factor"]
        return {
            "count": int(basic["total_trades"]),
            "win_rate": round(float(basic["win_rate"]) * 100, 2),
            "total_pnl": round(float(basic["total_pnl_abs"]), 2),
            "avg_pnl": round(float(basic["avg_pnl_abs"]), 2),
            "profit_factor": round(float(pf), 2) if pf != float("inf") else "inf",
        }

    longs = df[df["is_long"].astype(bool)]
    shorts = df[~df["is_long"].astype(bool)]
    return _subset_metrics(longs), _subset_metrics(shorts)


# ---------------------------------------------------------------------------
# Hit-rate metrics from forward-labelled verdicts (docs/backtest.md §6)
# ---------------------------------------------------------------------------


def compute_hit_rate_metrics(labelled_df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute direction hit rate and expectancy from forward-labelled verdicts.

    Input must come from labels.compute_labels() — expects columns:
    decision, return_h4, return_h24, return_h96, hit_h4, hit_h24, hit_h96.
    """
    alerts = labelled_df[labelled_df["decision"].isin(("BUY", "SELL"))]
    if alerts.empty:
        return {"total_alerts": 0}

    def _hit_rate(col: str) -> float:
        hits = alerts[col].dropna()
        return round(float(hits.astype(float).mean()), 4) if len(hits) else 0.0

    def _expectancy(ret_col: str, direction_col: str = "decision") -> dict[str, float]:
        """Raw mean return aligned with the signal direction."""
        rows = alerts[[direction_col, ret_col]].dropna()
        sign = rows[direction_col].map({"BUY": 1.0, "SELL": -1.0})
        pnl = rows[ret_col].astype(float) * sign
        return {
            "mean": round(float(pnl.mean()), 6) if len(pnl) else 0.0,
            "std": round(float(pnl.std()), 6) if len(pnl) > 1 else 0.0,
        }

    return {
        "total_alerts": len(alerts),
        "buy_count": int((alerts["decision"] == "BUY").sum()),
        "sell_count": int((alerts["decision"] == "SELL").sum()),
        "hit_rate_h4": _hit_rate("hit_h4"),
        "hit_rate_h24": _hit_rate("hit_h24"),
        "hit_rate_h96": _hit_rate("hit_h96"),
        "expectancy_h4": _expectancy("return_h4"),
        "expectancy_h24": _expectancy("return_h24"),
        "expectancy_h96": _expectancy("return_h96"),
    }


# ---------------------------------------------------------------------------
# Bootstrap CI (docs/backtest.md §10)
# ---------------------------------------------------------------------------


def compute_bootstrap_ci(
    values: npt.NDArray[np.float64] | list[float],
    metric_fn: Callable[[npt.NDArray[np.float64]], float],
    n_resamples: int = 1000,
    ci: float = 0.95,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """
    95% bootstrap CI for a scalar metric.

    Parameters
    ----------
    values:
        1-D array of trade-level values (e.g., pnl_net).
    metric_fn:
        Function mapping a 1-D array to a scalar (e.g., np.mean).
    n_resamples:
        Number of bootstrap resamples (default 1000).
    ci:
        Confidence level (default 0.95 → 2.5th/97.5th percentile).
    rng:
        Optional seeded RNG for reproducibility.

    Returns
    -------
    (lower, upper) confidence interval bounds.
    """
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return float("nan"), float("nan")

    gen = rng or np.random.default_rng()
    bootstrap_stats = np.array(
        [metric_fn(gen.choice(arr, size=len(arr), replace=True)) for _ in range(n_resamples)]
    )
    alpha = (1 - ci) / 2
    lower = float(np.percentile(bootstrap_stats, alpha * 100))
    upper = float(np.percentile(bootstrap_stats, (1 - alpha) * 100))
    return lower, upper


# ---------------------------------------------------------------------------
# Baseline comparisons (docs/backtest.md §11)
# ---------------------------------------------------------------------------


def compute_buy_and_hold(
    h4_ohlcv: pd.DataFrame,
    from_dt: pd.Timestamp,
    to_dt: pd.Timestamp,
) -> dict[str, float]:
    """Buy-and-hold baseline: long from from_dt to to_dt, no fees."""
    df = h4_ohlcv.copy()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    window = df[(df["open_time"] >= from_dt) & (df["open_time"] <= to_dt)]
    if window.empty:
        return {"total_return_pct": 0.0, "max_drawdown": 0.0}

    entry_price = float(window.iloc[0]["c"])
    exit_price = float(window.iloc[-1]["c"])
    if entry_price == 0:
        return {"total_return_pct": 0.0, "max_drawdown": 0.0}

    total_return_pct = (exit_price - entry_price) / entry_price * 100

    # Max drawdown from close prices.
    closes = window["c"].astype(float)
    rolling_max = closes.cummax()
    dd = ((closes - rolling_max) / rolling_max * 100).min()

    return {
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown": round(float(dd), 2),
    }


def compute_random_direction_baseline(
    labelled_df: pd.DataFrame,
    n_seeds: int = 100,
    rng_seed: int = 42,
) -> dict[str, float]:
    """
    Random-direction baseline: same alert frequency, random BUY/SELL direction.
    Averaged over n_seeds.

    Uses h24 horizon as the default return horizon.
    """
    alerts = labelled_df[labelled_df["decision"].isin(("BUY", "SELL"))]
    if alerts.empty:
        return {"expectancy_h24_mean": 0.0, "hit_rate_mean": 0.5}

    returns_h24 = alerts["return_h24"].astype(float).values
    rng = np.random.default_rng(rng_seed)
    all_exp: list[float] = []
    all_hit: list[float] = []

    for _ in range(n_seeds):
        rand_sign = rng.choice([-1.0, 1.0], size=len(returns_h24))
        pnl = returns_h24 * rand_sign
        all_exp.append(float(np.mean(pnl)))
        all_hit.append(float(np.mean(pnl > 0)))

    return {
        "expectancy_h24_mean": round(float(np.mean(all_exp)), 6),
        "hit_rate_mean": round(float(np.mean(all_hit)), 4),
    }


# ---------------------------------------------------------------------------
# Full result assembly
# ---------------------------------------------------------------------------


def generate_metrics(
    trades_df: pd.DataFrame,
    labelled_verdicts: pd.DataFrame | None = None,
    risk_free_rate_annual: float = 0.02,
    n_bootstrap: int = 1000,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """
    Generate a complete metrics dict from a trades DataFrame.

    Parameters
    ----------
    trades_df:
        Output of ExecutionSim.run().
    labelled_verdicts:
        Output of labels.compute_labels() — optional; provides hit-rate metrics.
    risk_free_rate_annual:
        Annual RFR for Sharpe calculation.
    n_bootstrap:
        Bootstrap resamples for CI computation.
    rng:
        Optional seeded RNG for reproducibility.

    Returns
    -------
    dict with all headline metrics (see docs/backtest.md §12.1).
    """
    if trades_df.empty:
        return {"error": "no_trades"}

    df = trades_df.copy()
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)

    basic = compute_basic_metrics(df)
    exit_dist = compute_exit_distribution(df)
    equity_curve, initial_capital, final_capital, total_return_pct = build_equity_curve(df)
    drawdown = compute_drawdown_metrics(equity_curve)
    sharpe_annual, n_months, sharpe_warning = compute_sharpe_ratio(
        equity_curve, initial_capital, risk_free_rate_annual
    )
    trade_sharpe = compute_trade_level_sharpe(df)
    monthly_returns = compute_monthly_returns_pct(equity_curve, initial_capital)
    long_m, short_m = compute_side_metrics(df)
    avg_holding_bars = round(float(df["holding_bars"].mean()), 1)

    # Bootstrap CI on expectancy (pnl_rel as proxy).
    pnl_rel = df["pnl_rel"].astype(float).values
    exp_ci_lo, exp_ci_hi = compute_bootstrap_ci(pnl_rel, np.mean, n_resamples=n_bootstrap, rng=rng)
    expectancy_significant = not (exp_ci_lo <= 0 <= exp_ci_hi)

    # Forward-label hit rates (if available).
    hit_rate_metrics: dict[str, Any] = {}
    if labelled_verdicts is not None and not labelled_verdicts.empty:
        hit_rate_metrics = compute_hit_rate_metrics(labelled_verdicts)

    pf = basic["profit_factor"]
    result: dict[str, Any] = {
        "total_trades": int(basic["total_trades"]),
        "win_rate": round(float(basic["win_rate"]) * 100, 2),
        "total_pnl_abs": round(float(basic["total_pnl_abs"]), 2),
        "total_return_pct": round(total_return_pct, 2),
        "avg_pnl_abs": round(float(basic["avg_pnl_abs"]), 2),
        "avg_win": round(float(basic["avg_win"]), 2),
        "avg_loss": round(float(basic["avg_loss"]), 2),
        "profit_factor": round(float(pf), 2) if pf != float("inf") else "inf",
        "max_drawdown": round(float(drawdown["max_drawdown"]) * 100, 2),
        "sharpe_ratio": sharpe_annual,
        "sharpe_monthly_samples": n_months,
        "sharpe_warning": sharpe_warning,
        "trade_level_sharpe": trade_sharpe,
        "avg_holding_bars": avg_holding_bars,
        "exit_distribution": exit_dist,
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
        "monthly_returns_pct": monthly_returns,
        "long_metrics": long_m,
        "short_metrics": short_m,
        "expectancy_rel_mean": round(float(np.mean(pnl_rel)), 6),
        "expectancy_ci_95": (round(exp_ci_lo, 6), round(exp_ci_hi, 6)),
        "expectancy_significant": expectancy_significant,
        **hit_rate_metrics,
    }
    return result
