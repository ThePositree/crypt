from __future__ import annotations

import pandas as pd

from backtester.trade_chart_report import TradeChartReportConfig, build_trade_chart_report


def test_build_trade_chart_report_from_full_ohlcv_without_trade_gaps(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=8, freq="h", tz="UTC"),
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            "volume": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
        }
    ).to_csv(run_dir / "ohlcv.csv", index=False)

    pd.DataFrame(
        [
            {
                "entry_time": "2025-01-01 01:00:00+00:00",
                "exit_time": "2025-01-01 03:00:00+00:00",
                "entry_price": 102.0,
                "exit_price": 104.0,
                "tp_price": 104.0,
                "sl_price": 100.0,
                "trail_stop_price": "",
                "is_long": True,
                "exit_reason": "take_profit",
                "pnl_abs": 100.0,
                "pnl_rel": 0.01,
                "confidence": 80.0,
                "trigger_type": "h1_structure_break",
                "sl_anchor_type": "pivot",
                "sl_distance_atr": 2.0,
            }
        ]
    ).to_csv(run_dir / "trades.csv", index=False)
    pd.DataFrame([{"total_return_pct": 1.0, "total_trades": 1}]).to_csv(
        run_dir / "metrics.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "tick_time": "2025-01-01 00:00:00+00:00",
                "signal": 1,
                "close": 101.0,
                "decision": "BUY",
                "confidence": 80.0,
                "regime": "trending",
            }
        ]
    ).to_csv(run_dir / "signals.csv", index=False)

    output = build_trade_chart_report(
        TradeChartReportConfig(run_dir=run_dir, title="Smoke trade chart")
    )

    html = output.read_text()
    assert output == run_dir / "trade_chart.html"
    assert "Smoke trade chart" in html
    assert "lightweight-charts@5.2.0" in html
    assert "createSeriesMarkers" in html
    assert '"time": 1735707600' in html  # 2025-01-01 05:00 UTC, between trade times.
    assert '"kind": "tp"' in html
    assert '"kind": "sl"' in html
    assert "Trade Diagnostics" in html
    assert "h1_structure_break" in html
