from __future__ import annotations

import pandas as pd

from backtester.trade_analyzer import TradeAnalyzer


def test_trade_analyzer_chikou_span_uses_lagged_close_not_future_close() -> None:
    index = pd.date_range("2024-01-01", periods=60, freq="min", tz="UTC")
    close = [float(value) for value in range(60)]
    ohlcv = pd.DataFrame(
        {
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "volume": 1_000.0,
        },
        index=index,
    )

    analyzer = TradeAnalyzer(pd.DataFrame(), ohlcv)
    analyzer.precompute_all_metrics()

    assert analyzer.precomputed_metrics_df is not None
    row = analyzer.precomputed_metrics_df.iloc[30]
    assert row["chikou_span"] == ohlcv["close"].iloc[4]
    assert row["chikou_span"] != ohlcv["close"].iloc[56]
