from __future__ import annotations

import pandas as pd
import pytest

from backtester.strategies.filtered_donor_portfolio import (
    PortfolioFilterRule,
    _catalog_features,
    _validate_filter_features_available,
)
from backtester.tester import Backtester


def test_backtester_accepts_signal_events_without_scalar_signal_columns() -> None:
    data = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    def strategy(frame: pd.DataFrame) -> pd.DataFrame:
        output = frame.copy()
        output["signal_events"] = [
            [
                {"signal": 1, "sl_price": 99.0, "selected_strategy": "alpha"},
                {"signal": 1, "sl_price": 98.0, "selected_strategy": "beta"},
            ],
            [],
            [],
        ]
        return output

    result = Backtester(data, strategy).run(
        initial_capital=10_000.0,
        max_positions=0,
    )

    trades = result.get_trades()
    assert len(trades) == 2
    assert trades["selected_strategy"].tolist() == ["alpha", "beta"]


def test_filtered_portfolio_catalog_features_use_previous_closed_bar() -> None:
    index = pd.date_range("2026-01-01 00:00", periods=40, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(len(index))],
            "high": [101.0 + i for i in range(len(index))],
            "low": [99.0 + i for i in range(len(index))],
            "close": [100.5 + i for i in range(len(index))],
            "volume": [1_000.0 + i for i in range(len(index))],
        },
        index=index,
    )

    catalog = _catalog_features(primary)

    assert pd.isna(catalog.iloc[0]["catalog_bb_width_pct"])
    assert catalog.iloc[1]["entry_hour"] == 1
    assert catalog.iloc[1]["entry_dayofweek"] == index[1].dayofweek


def test_filtered_portfolio_rejects_unavailable_filter_features() -> None:
    frames = {"alpha": pd.DataFrame({"signal": [1], "catalog_bb_width_pct": [0.02]})}
    filters = {
        "alpha": [
            PortfolioFilterRule("catalog_bb_width_pct", ">=", 0.01),
            PortfolioFilterRule("confidence", "<=", 7.0),
        ]
    }

    with pytest.raises(ValueError, match="alpha: confidence"):
        _validate_filter_features_available(frames, filters)
