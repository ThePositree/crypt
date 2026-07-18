from __future__ import annotations

import pandas as pd

from backtester.results_analyzer import ResultsAnalyzer


def test_results_analyzer_drawdown_uses_window_start_not_rolling_peak():
    trades = pd.DataFrame(
        {
            "exit_time": pd.to_datetime(
                ["2025-01-05", "2025-01-10", "2025-01-15"],
                utc=True,
            ),
            "entry_time": pd.to_datetime(
                ["2025-01-04", "2025-01-09", "2025-01-14"],
                utc=True,
            ),
            "capital_before": [10000.0, 10000.0, 12000.0],
            "capital_after": [12000.0, 11000.0, 11500.0],
            "pnl_abs": [2000.0, -1000.0, 500.0],
            "exit_reason": ["take_profit", "stop_loss", "take_profit"],
            "holding_bars": [1, 1, 1],
            "is_long": [True, True, True],
        }
    )

    analyzer = ResultsAnalyzer(trades)
    metrics = analyzer.generate()

    # Peak was 12000 then 11000, but never below window start 10000.
    assert metrics["max_drawdown"] == 0.0
    assert metrics["peak_to_trough_drawdown"] == -8.33


def test_results_analyzer_drawdown_when_realized_equity_dips_below_start():
    trades = pd.DataFrame(
        {
            "exit_time": pd.to_datetime(["2025-01-05", "2025-01-10"], utc=True),
            "entry_time": pd.to_datetime(["2025-01-04", "2025-01-09"], utc=True),
            "capital_before": [10000.0, 9900.0],
            "capital_after": [9900.0, 9950.0],
            "pnl_abs": [-100.0, 50.0],
            "exit_reason": ["stop_loss", "take_profit"],
            "holding_bars": [1, 1],
            "is_long": [True, True],
        }
    )

    analyzer = ResultsAnalyzer(trades)
    metrics = analyzer.generate()

    assert metrics["max_drawdown"] == -1.0
    assert metrics["peak_to_trough_drawdown"] == -1.0


def test_results_report_labels_both_drawdown_definitions(capsys):
    trades = pd.DataFrame(
        {
            "exit_time": pd.to_datetime(
                ["2025-01-05", "2025-01-10"],
                utc=True,
            ),
            "entry_time": pd.to_datetime(
                ["2025-01-04", "2025-01-09"],
                utc=True,
            ),
            "capital_before": [10000.0, 12000.0],
            "capital_after": [12000.0, 11000.0],
            "pnl_abs": [2000.0, -1000.0],
            "exit_reason": ["take_profit", "stop_loss"],
            "holding_bars": [1, 1],
            "is_long": [True, True],
        }
    )
    analyzer = ResultsAnalyzer(trades)
    analyzer.generate()

    analyzer.print_report()

    output = capsys.readouterr().out
    assert "Drawdown Below Start: 0.0%" in output
    assert "Peak-to-Trough DD:    -8.33%" in output
