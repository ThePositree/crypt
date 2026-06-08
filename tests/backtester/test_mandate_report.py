from __future__ import annotations

import pandas as pd

from backtester.mandate_report import build_mandate_report, build_mandate_summary


def test_monthly_mandate_caps_positive_outliers_and_counts_gates():
    trades = pd.DataFrame(
        {
            "exit_time": [
                "2025-01-05T00:00:00+00:00",
                "2025-01-10T00:00:00+00:00",
                "2025-02-03T00:00:00+00:00",
                "2025-02-04T00:00:00+00:00",
            ],
            "entry_time": [
                "2025-01-05T00:00:00+00:00",
                "2025-01-10T00:00:00+00:00",
                "2025-02-03T00:00:00+00:00",
                "2025-02-04T00:00:00+00:00",
            ],
            "pnl_abs": [2500.0, 500.0, -1200.0, 200.0],
            "exit_reason": ["take_profit", "take_profit", "stop_loss", "take_profit"],
        }
    )

    report = build_mandate_report(
        trades,
        initial_capital=10000.0,
        start="2025-01-01",
        end="2025-04-01",
    )
    monthly = report.monthly.set_index("month")

    assert monthly.loc["2025-01", "raw_monthly_return_pct"] == 30.0
    assert monthly.loc["2025-01", "capped_monthly_return_pct"] == 20.0
    assert monthly.loc["2025-01", "excess_return_pct"] == 10.0
    assert bool(monthly.loc["2025-01", "passes_return_floor"])
    assert monthly.loc["2025-02", "raw_monthly_return_pct"] == -10.0
    assert monthly.loc["2025-02", "max_drawdown_pct"] == -9.23
    assert not bool(monthly.loc["2025-02", "breaches_monthly_dd"])
    assert monthly.loc["2025-02", "stop_loss_count"] == 1
    assert monthly.loc["2025-03", "trade_count"] == 0
    assert monthly.loc["2025-03", "raw_monthly_return_pct"] == 0.0


def test_mandate_summary_discards_when_too_many_months_below_floor():
    monthly = pd.DataFrame(
        {
            "passes_return_floor": [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
                False,
                False,
                False,
            ],
            "is_losing_month": [False] * 12,
            "breaches_monthly_dd": [False] * 12,
            "max_drawdown_pct": [0.0] * 12,
            "capped_monthly_return_pct": [15.0] * 8 + [0.0] * 4,
        }
    )

    summary = build_mandate_summary(monthly)

    assert summary.loc[0, "verdict"] == "discard"
    assert summary.loc[0, "months_below_floor"] == 4


def test_mandate_summary_promotes_when_all_gates_pass():
    monthly = pd.DataFrame(
        {
            "passes_return_floor": [True] * 9 + [False] * 3,
            "is_losing_month": [False] * 12,
            "breaches_monthly_dd": [False] * 12,
            "max_drawdown_pct": [-2.0] * 12,
            "capped_monthly_return_pct": [16.0] * 9 + [5.0] * 3,
        }
    )

    summary = build_mandate_summary(monthly, large_losing_day_count=10)

    assert summary.loc[0, "verdict"] == "promote"
    assert summary.loc[0, "months_passing_floor"] == 9


def test_mandate_summary_archives_monthly_drawdown_breach_before_full_optuna():
    monthly = pd.DataFrame(
        {
            "passes_return_floor": [True] * 9 + [False] * 3,
            "is_losing_month": [False] * 12,
            "breaches_monthly_dd": [False, True] + [False] * 10,
            "max_drawdown_pct": [-2.0, -11.0] + [-2.0] * 10,
            "capped_monthly_return_pct": [16.0] * 12,
        }
    )

    summary = build_mandate_summary(monthly)

    assert summary.loc[0, "verdict"] == "archive"
    assert summary.loc[0, "dd_breach_months"] == 1


def test_mandate_trade_count_includes_open_entries_without_realized_pnl():
    trades = pd.DataFrame(
        {
            "entry_time": [
                "2025-01-10T00:00:00+00:00",
                "2025-01-20T00:00:00+00:00",
            ],
            "exit_time": ["2025-01-11T00:00:00+00:00", pd.NaT],
            "pnl_abs": [1000.0, pd.NA],
            "exit_reason": ["take_profit", "open"],
        }
    )

    report = build_mandate_report(
        trades,
        initial_capital=10000.0,
        start="2025-01-01",
        end="2025-02-01",
    )

    row = report.monthly.iloc[0]
    assert row["trade_count"] == 2
    assert row["raw_monthly_return_pct"] == 10.0
