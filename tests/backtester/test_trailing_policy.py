from __future__ import annotations

import pandas as pd
import pytest

from backtester.trailing_policy import (
    build_native_trailing_geometry,
    latest_entry_atr14,
    with_closed_atr14,
)


def test_native_trailing_geometry_uses_fixed_entry_atr_spread() -> None:
    geometry = build_native_trailing_geometry(
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        is_long=True,
        activation_rrr=1.0,
        distance_atr=0.25,
        entry_atr=4.0,
    )

    assert geometry.activation_price == pytest.approx(102.0)
    assert geometry.callback_spread == pytest.approx(1.0)
    assert not geometry.fixed_take_profit_enabled


def test_live_entry_atr_matches_next_bar_shifted_backtest_atr() -> None:
    index = pd.date_range("2026-01-01", periods=16, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": range(100, 116),
            "high": range(102, 118),
            "low": range(99, 115),
            "close": range(101, 117),
        },
        index=index,
    )

    live_value = latest_entry_atr14(frame.iloc[:-1])
    backtest_value = with_closed_atr14(frame)["trail_atr"].iloc[-1]

    assert live_value == pytest.approx(backtest_value)
