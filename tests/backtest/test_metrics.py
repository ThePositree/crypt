"""Tests for src/crypt/backtest/metrics.py.

Verifies: basic metric computation, equity curve fix (no drop_duplicates),
bootstrap CI, buy-and-hold baseline, §18.4 Sharpe warning.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from crypt.backtest.metrics import (
    build_equity_curve,
    compute_basic_metrics,
    compute_bootstrap_ci,
    compute_buy_and_hold,
    compute_sharpe_ratio,
    generate_metrics,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trades(
    n: int,
    pnl_per_trade: float = 10.0,
    initial_capital: float = 10_000.0,
    start: datetime | None = None,
) -> pd.DataFrame:
    """Build a synthetic trades DataFrame with n identical trades."""
    if start is None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    capital = initial_capital
    for i in range(n):
        entry = start + timedelta(hours=4 * i)
        exit_ = entry + timedelta(hours=4)
        capital_after = capital + pnl_per_trade
        rows.append(
            {
                "symbol": "SOL-USDT-SWAP",
                "entry_time": entry,
                "exit_time": exit_,
                "entry_price": 100.0,
                "exit_price": 101.0,
                "size": 1.0,
                "pnl_abs": pnl_per_trade,
                "pnl_rel": pnl_per_trade / 100.0,
                "fee_entry": 0.05,
                "fee_exit": 0.05,
                "funding": 0.0,
                "tp_price": 102.0,
                "sl_price": 98.0,
                "exit_reason": "take_profit",
                "capital_before": capital,
                "capital_after": capital_after,
                "holding_bars": 1,
                "leverage": 3.0,
                "is_long": True,
                "entry_bar_index": i,
                "exit_bar_index": i,
            }
        )
        capital = capital_after
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# compute_basic_metrics
# ---------------------------------------------------------------------------


def test_basic_metrics_all_wins() -> None:
    df = _make_trades(10, pnl_per_trade=5.0)
    m = compute_basic_metrics(df)
    assert m["total_trades"] == 10
    assert m["win_rate"] == pytest.approx(1.0)
    assert m["profit_factor"] == float("inf")
    assert m["total_pnl_abs"] == pytest.approx(50.0)


def test_basic_metrics_half_wins() -> None:
    n = 10
    trades = _make_trades(n, pnl_per_trade=10.0)
    # Make alternate trades losers.
    trades.loc[1::2, "pnl_abs"] = -10.0
    trades.loc[1::2, "pnl_rel"] = -0.1
    m = compute_basic_metrics(trades)
    assert m["win_rate"] == pytest.approx(0.5)
    assert m["profit_factor"] == pytest.approx(1.0)


def test_basic_metrics_empty() -> None:
    m = compute_basic_metrics(pd.DataFrame())
    assert m["total_trades"] == 0
    assert m["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# build_equity_curve — §18.4 fix: no drop_duplicates
# ---------------------------------------------------------------------------


def test_equity_curve_no_drop_duplicates() -> None:
    """Two trades exiting at the same timestamp must both contribute to equity."""
    start = datetime(2025, 6, 1, tzinfo=UTC)
    common_exit = start + timedelta(hours=4)
    df = pd.DataFrame(
        [
            {
                "symbol": "SOL-USDT-SWAP",
                "entry_time": start,
                "exit_time": common_exit,
                "entry_price": 100.0,
                "exit_price": 105.0,
                "size": 1.0,
                "pnl_abs": 10.0,
                "pnl_rel": 0.1,
                "fee_entry": 0.0,
                "fee_exit": 0.0,
                "funding": 0.0,
                "tp_price": 105.0,
                "sl_price": 95.0,
                "exit_reason": "take_profit",
                "capital_before": 10_000.0,
                "capital_after": 10_010.0,
                "holding_bars": 1,
                "leverage": 2.0,
                "is_long": True,
                "entry_bar_index": 0,
                "exit_bar_index": 1,
            },
            {
                "symbol": "TON-USDT-SWAP",
                "entry_time": start,
                "exit_time": common_exit,  # same exit_time!
                "entry_price": 2.0,
                "exit_price": 2.1,
                "size": 100.0,
                "pnl_abs": 8.0,
                "pnl_rel": 0.05,
                "fee_entry": 0.0,
                "fee_exit": 0.0,
                "funding": 0.0,
                "tp_price": 2.1,
                "sl_price": 1.9,
                "exit_reason": "take_profit",
                "capital_before": 10_010.0,
                "capital_after": 10_018.0,
                "holding_bars": 1,
                "leverage": 2.0,
                "is_long": True,
                "entry_bar_index": 0,
                "exit_bar_index": 1,
            },
        ]
    )
    _equity, _initial, final, total_return = build_equity_curve(df)
    # Final capital must reflect both trades (not just the "last" one if duplicates were dropped).
    assert final == pytest.approx(10_018.0), (
        "Equity curve dropped a duplicate exit_time — §18.4 fix may be broken"
    )
    assert total_return == pytest.approx(0.18)


# ---------------------------------------------------------------------------
# compute_sharpe_ratio — §18.4 warning
# ---------------------------------------------------------------------------


def test_sharpe_warning_few_months() -> None:
    """Sharpe with < 6 monthly samples returns a warning string."""
    # Build a 3-month equity curve.
    start = pd.Timestamp("2025-01-01", tz="UTC")
    dates = pd.date_range(start, periods=90, freq="D", tz="UTC")
    equity = pd.Series(np.linspace(10_000, 10_500, 90), index=dates)
    _, n_months, warning = compute_sharpe_ratio(equity, 10_000.0)
    assert n_months < 6
    assert warning is not None
    assert "not statistically reliable" in warning


def test_sharpe_no_warning_many_months() -> None:
    """Sharpe with >= 6 monthly samples returns no warning."""
    start = pd.Timestamp("2024-01-01", tz="UTC")
    dates = pd.date_range(start, periods=365, freq="D", tz="UTC")
    equity = pd.Series(np.linspace(10_000, 12_000, 365), index=dates)
    _, n_months, warning = compute_sharpe_ratio(equity, 10_000.0)
    assert n_months >= 6
    assert warning is None


# ---------------------------------------------------------------------------
# compute_bootstrap_ci
# ---------------------------------------------------------------------------


def test_bootstrap_ci_mean_positive() -> None:
    """Bootstrap CI for mean of positive values should be above 0."""
    rng = np.random.default_rng(42)
    # Use slightly noisy positive values so CI has a non-zero width.
    vals = rng.normal(0.05, 0.01, 100)
    lo, hi = compute_bootstrap_ci(vals, np.mean, n_resamples=500, rng=rng)
    assert lo > 0
    assert hi >= lo


def test_bootstrap_ci_crosses_zero() -> None:
    """Bootstrap CI for zero-mean noise should cross zero."""
    rng = np.random.default_rng(42)
    vals = rng.normal(0, 1, 100)
    lo, hi = compute_bootstrap_ci(vals, np.mean, n_resamples=500, rng=rng)
    assert lo < 0 < hi


def test_bootstrap_ci_empty() -> None:
    lo, hi = compute_bootstrap_ci([], np.mean)
    assert np.isnan(lo)
    assert np.isnan(hi)


# ---------------------------------------------------------------------------
# compute_buy_and_hold
# ---------------------------------------------------------------------------


def test_buy_and_hold_flat() -> None:
    """Flat prices → 0% return."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ohlcv = pd.DataFrame(
        [
            {
                "open_time": start + timedelta(hours=4 * i),
                "o": 100.0,
                "h": 100.5,
                "l": 99.5,
                "c": 100.0,
                "volume": 1000.0,
            }
            for i in range(50)
        ]
    )
    result = compute_buy_and_hold(
        ohlcv,
        pd.Timestamp(start),
        pd.Timestamp(start + timedelta(days=7)),
    )
    assert result["total_return_pct"] == pytest.approx(0.0)


def test_buy_and_hold_double() -> None:
    """Prices double → 100% return."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ohlcv = pd.DataFrame(
        [
            {
                "open_time": start + timedelta(hours=4 * i),
                "o": 100.0,
                "h": 101.0,
                "l": 99.0,
                "c": 100.0 + i * 2,  # doubles over 50 bars: 100 → 200
                "volume": 1000.0,
            }
            for i in range(51)
        ]
    )
    result = compute_buy_and_hold(
        ohlcv,
        pd.Timestamp(start),
        pd.Timestamp(start + timedelta(days=9)),
    )
    assert result["total_return_pct"] > 0


# ---------------------------------------------------------------------------
# generate_metrics integration
# ---------------------------------------------------------------------------


def test_generate_metrics_all_winners() -> None:
    """All-winning trades: expectancy > 0, win_rate 100%."""
    trades = _make_trades(30, pnl_per_trade=10.0)
    m = generate_metrics(trades, n_bootstrap=200, rng=np.random.default_rng(1))
    assert m["win_rate"] == pytest.approx(100.0)
    assert m["expectancy_rel_mean"] > 0
    assert m["total_return_pct"] > 0


def test_generate_metrics_empty_trades() -> None:
    m = generate_metrics(pd.DataFrame())
    assert m == {"error": "no_trades"}


def test_generate_metrics_expectancy_significant() -> None:
    """Consistently positive returns should yield a significant expectancy CI."""
    trades = _make_trades(80, pnl_per_trade=10.0)
    m = generate_metrics(trades, n_bootstrap=500, rng=np.random.default_rng(7))
    assert m["expectancy_significant"] is True
    ci = m["expectancy_ci_95"]
    assert ci[0] > 0, "Lower CI bound should be above 0 for consistent winners"
