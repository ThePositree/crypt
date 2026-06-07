import pandas as pd

from backtester.results_analyzer import ResultsAnalyzer


def _trades_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if not df.empty:
        df["entry_time"] = pd.to_datetime(df["entry_time"])
        df["exit_time"] = pd.to_datetime(df["exit_time"])
    return df


def test_generate_no_trades_returns_error():
    analyzer = ResultsAnalyzer(pd.DataFrame())
    assert analyzer.generate() == {"error": "no_trades", "total_trades": 0}
    assert analyzer.metrics == {"error": "no_trades", "total_trades": 0}


def test_export_no_trades_preserves_metrics_and_signal_diagnostics(tmp_path):
    signals = pd.DataFrame(
        {
            "signal": [0, 0, 0],
            "decision": ["BUY", "SELL", "HOLD"],
            "confidence": [74, 55, 0],
            "regime": ["trending", "ranging", "ranging"],
        },
        index=pd.to_datetime(
            [
                "2026-01-01 04:00:00",
                "2026-01-01 08:00:00",
                "2026-01-01 12:00:00",
            ],
            utc=True,
        ),
    )
    signals.index.name = "tick_time"
    analyzer = ResultsAnalyzer(pd.DataFrame(), signal_df=signals)
    analyzer.generate()

    analyzer.export_results(str(tmp_path))

    metrics = pd.read_csv(tmp_path / "metrics.csv")
    exported_signals = pd.read_csv(tmp_path / "signals.csv")
    diagnostics = pd.read_csv(tmp_path / "signal_diagnostics.csv")

    assert metrics.to_dict("records") == [{"error": "no_trades", "total_trades": 0}]
    assert len(exported_signals) == 3
    assert "tick_time" in exported_signals.columns
    assert {
        ("rows", "all", 3),
        ("signal_count", "0", 3),
        ("decision_count", "BUY", 1),
        ("decision_count", "SELL", 1),
        ("confidence", "max", 74.0),
        ("confidence_quantile", "p50", 55.0),
    }.issubset(
        {
            (row["metric"], str(row["bucket"]), row["value"])
            for row in diagnostics.to_dict("records")
        }
    )
    assert not (tmp_path / "trade_diagnostics.csv").exists()


def test_export_trades_writes_trade_diagnostics(tmp_path):
    df = _trades_df(
        [
            {
                "entry_time": "2026-01-01 00:00:00",
                "exit_time": "2026-01-02 00:00:00",
                "entry_price": 100.0,
                "exit_price": 101.0,
                "pnl_abs": -1.0,
                "pnl_rel": -0.01,
                "exit_reason": "ttl_expired",
                "capital_before": 1000.0,
                "capital_after": 999.0,
                "holding_bars": 6,
                "is_long": True,
                "sl_distance_atr": 4.0,
                "sl_anchor_type": "order_block",
                "locked_margin": 100.0,
                "available_balance_before": 1000.0,
                "open_positions_before": 0,
                "total_locked_margin_before": 0.0,
                "total_locked_margin_after_entry": 100.0,
            },
            {
                "entry_time": "2026-01-03 00:00:00",
                "exit_time": "2026-01-03 12:00:00",
                "entry_price": 100.0,
                "exit_price": 90.0,
                "pnl_abs": 8.0,
                "pnl_rel": 0.08,
                "exit_reason": "take_profit",
                "capital_before": 999.0,
                "capital_after": 1007.0,
                "holding_bars": 3,
                "is_long": False,
                "sl_distance_atr": 1.0,
                "sl_anchor_type": "pivot",
                "locked_margin": 250.0,
                "available_balance_before": 900.0,
                "open_positions_before": 1,
                "total_locked_margin_before": 100.0,
                "total_locked_margin_after_entry": 350.0,
            },
        ]
    )
    analyzer = ResultsAnalyzer(df)
    analyzer.generate()

    analyzer.export_results(str(tmp_path))

    diagnostics = pd.read_csv(tmp_path / "trade_diagnostics.csv")
    records = {
        (row["section"], row["group"], row["metric"]): row["value"]
        for row in diagnostics.to_dict("records")
    }
    assert records[("summary", "all", "trades")] == 2
    assert records[("exit_reason", "ttl_expired", "count")] == 1
    assert records[("exit_reason", "ttl_expired", "share")] == 0.5
    assert records[("side_exit_reason", "long:ttl_expired", "count")] == 1
    assert records[("margin", "all", "peak_open_positions")] == 2
    assert records[("margin", "all", "peak_locked_margin")] == 350.0
    assert records[("margin", "all", "peak_locked_margin_pct_initial")] == 35.0
    assert records[("margin", "all", "min_available_balance_before")] == 900.0
    assert records[("sl_distance_atr_by_exit", "ttl_expired", "p50")] == 4.0
    assert records[("sl_anchor", "order_block", "distance_atr_p50")] == 4.0


def test_export_results_with_ohlcv_writes_trade_chart_and_full_candles(tmp_path):
    trades = _trades_df(
        [
            {
                "entry_time": "2026-01-01 01:00:00",
                "exit_time": "2026-01-01 03:00:00",
                "entry_price": 102.0,
                "exit_price": 104.0,
                "tp_price": 104.0,
                "sl_price": 100.0,
                "pnl_abs": 10.0,
                "pnl_rel": 0.01,
                "exit_reason": "take_profit",
                "capital_before": 1000.0,
                "capital_after": 1010.0,
                "holding_bars": 3,
                "is_long": True,
                "entry_bar_index": 1,
                "exit_bar_index": 3,
            }
        ]
    )
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1.0, 2.0, 3.0, 4.0, 5.0],
        },
        index=pd.date_range("2026-01-01", periods=5, freq="h", tz="UTC"),
    )
    analyzer = ResultsAnalyzer(trades)
    analyzer.generate()

    analyzer.export_results(str(tmp_path), ohlcv_df=ohlcv)

    assert (tmp_path / "ohlcv.csv").exists()
    html = (tmp_path / "trade_chart.html").read_text()
    assert "lightweight-charts@5.2.0" in html
    assert '"time": 1767225600' in html
    assert '"time": 1767240000' in html
    assert '"kind": "entry"' in html


def test_generate_profit_factor_inf_when_no_losses():
    df = _trades_df(
        [
            {
                "entry_time": "2026-01-01 00:00:00",
                "exit_time": "2026-01-02 00:00:00",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "pnl_abs": 10.0,
                "pnl_rel": 0.1,
                "exit_reason": "take_profit",
                "capital_before": 1000.0,
                "capital_after": 1010.0,
                "holding_bars": 5,
                "is_long": True,
            },
            {
                "entry_time": "2026-01-03 00:00:00",
                "exit_time": "2026-01-04 00:00:00",
                "entry_price": 200.0,
                "exit_price": 210.0,
                "pnl_abs": 20.0,
                "pnl_rel": 0.1,
                "exit_reason": "take_profit",
                "capital_before": 1010.0,
                "capital_after": 1030.0,
                "holding_bars": 7,
                "is_long": True,
            },
        ]
    )
    m = ResultsAnalyzer(df).generate()
    assert m["total_trades"] == 2
    assert m["win_rate"] == 100.0
    assert m["profit_factor"] == "inf"
    assert m["max_drawdown"] == 0.0


def test_generate_long_short_metrics_have_expected_shape():
    df = _trades_df(
        [
            # long win
            {
                "entry_time": "2026-01-01 00:00:00",
                "exit_time": "2026-01-01 01:00:00",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "pnl_abs": 10.0,
                "pnl_rel": 0.1,
                "exit_reason": "take_profit",
                "capital_before": 1000.0,
                "capital_after": 1010.0,
                "holding_bars": 5,
                "is_long": True,
            },
            # long loss
            {
                "entry_time": "2026-01-02 00:00:00",
                "exit_time": "2026-01-02 01:00:00",
                "entry_price": 100.0,
                "exit_price": 95.0,
                "pnl_abs": -5.0,
                "pnl_rel": -0.05,
                "exit_reason": "stop_loss",
                "capital_before": 1010.0,
                "capital_after": 1005.0,
                "holding_bars": 4,
                "is_long": True,
            },
            # short win
            {
                "entry_time": "2026-01-03 00:00:00",
                "exit_time": "2026-01-03 01:00:00",
                "entry_price": 100.0,
                "exit_price": 90.0,
                "pnl_abs": 8.0,
                "pnl_rel": 0.08,
                "exit_reason": "take_profit",
                "capital_before": 1005.0,
                "capital_after": 1013.0,
                "holding_bars": 6,
                "is_long": False,
            },
        ]
    )
    m = ResultsAnalyzer(df).generate()

    assert set(m["long_metrics"].keys()) == {
        "count",
        "win_rate",
        "total_pnl",
        "avg_pnl",
        "profit_factor",
    }
    assert set(m["short_metrics"].keys()) == {
        "count",
        "win_rate",
        "total_pnl",
        "avg_pnl",
        "profit_factor",
    }

    assert m["long_metrics"]["count"] == 2
    assert m["short_metrics"]["count"] == 1
    assert m["short_metrics"]["profit_factor"] == "inf"
    assert m["long_metrics"]["profit_factor"] != "inf"


def test_generate_monthly_returns_pct_keys_and_first_point_logic():
    df = _trades_df(
        [
            {
                "entry_time": "2026-01-10 00:00:00",
                "exit_time": "2026-01-31 12:00:00",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "pnl_abs": 100.0,
                "pnl_rel": 0.1,
                "exit_reason": "take_profit",
                "capital_before": 1000.0,
                "capital_after": 1100.0,
                "holding_bars": 10,
                "is_long": True,
            },
            {
                "entry_time": "2026-02-01 00:00:00",
                "exit_time": "2026-02-28 12:00:00",
                "entry_price": 100.0,
                "exit_price": 105.0,
                "pnl_abs": 50.0,
                "pnl_rel": 0.05,
                "exit_reason": "take_profit",
                "capital_before": 1100.0,
                "capital_after": 1150.0,
                "holding_bars": 8,
                "is_long": True,
            },
        ]
    )
    m = ResultsAnalyzer(df).generate()
    mr = m["monthly_returns_pct"]
    assert set(mr.keys()) == {"2026-01", "2026-02"}
    assert mr["2026-01"]["ret"] == 10.0
    assert mr["2026-01"]["ret_abs"] == 10.0
