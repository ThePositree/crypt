from __future__ import annotations

import pandas as pd
import pytest

from backtester.data_contracts import IntrabarExecutionData
from backtester.execution_sim import ExecutionSim


def _h1_signal_frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 125.0, 101.0],
            "low": [99.0, 85.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
            "signal": [1, 0, 0],
            "sl_price": [90.0, 0.0, 0.0],
        },
        index=index,
    )


def _minute_data(*, mark_liquidation: bool = False) -> IntrabarExecutionData:
    index = pd.date_range("2026-01-01", periods=120, freq="1min", tz="UTC")
    last = pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1.0,
        },
        index=index,
    )
    last.loc[index[60], "high"] = 121.0
    last.loc[index[61], "low"] = 89.0
    last.loc[index[62], ["high", "low"]] = [125.0, 85.0]
    mark = last.copy()
    mark.loc[:, ["open", "high", "low", "close"]] = 100.0
    if mark_liquidation:
        last.loc[index[60], "high"] = 101.0
        mark.loc[index[60], "low"] = 0.0
    return IntrabarExecutionData(last_1m=last, mark_1m=mark)


def _sim() -> ExecutionSim:
    return ExecutionSim(
        initial_capital=1_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        intrabar_execution_timeframe="1m",
    )


def test_minute_path_resolves_take_profit_before_later_stop() -> None:
    trades = _sim().run(_h1_signal_frame(), intrabar_data=_minute_data())

    assert trades.loc[0, "exit_reason"] == "take_profit"
    assert trades.loc[0, "exit_price"] == pytest.approx(120.0)
    assert trades.loc[0, "exit_time"] == pd.Timestamp("2026-01-01 01:00:00+00:00")


def test_minute_mark_price_drives_liquidation() -> None:
    trades = _sim().run(
        _h1_signal_frame(),
        intrabar_data=_minute_data(mark_liquidation=True),
    )

    assert trades.loc[0, "exit_reason"] == "liquidation"


def test_minute_execution_rejects_missing_candle() -> None:
    data = _minute_data()
    incomplete = IntrabarExecutionData(
        last_1m=data.last_1m.drop(data.last_1m.index[17]),
        mark_1m=data.mark_1m,
    )

    with pytest.raises(ValueError, match="last 1m execution coverage is incomplete"):
        _sim().run(_h1_signal_frame(), intrabar_data=incomplete)


def test_minute_execution_rejects_h1_aggregation_mismatch() -> None:
    data = _minute_data()
    mismatched_last = data.last_1m.copy()
    mismatched_last.loc[mismatched_last.index[5], "high"] = 999.0

    with pytest.raises(ValueError, match="do not aggregate to primary H1"):
        _sim().run(
            _h1_signal_frame(),
            intrabar_data=IntrabarExecutionData(
                last_1m=mismatched_last,
                mark_1m=data.mark_1m,
            ),
        )


def test_minute_execution_accepts_exchange_open_aggregation_difference() -> None:
    data = _minute_data()
    different_open = data.last_1m.copy()
    different_open.loc[different_open.index[0], "open"] = 100.5

    trades = _sim().run(
        _h1_signal_frame(),
        intrabar_data=IntrabarExecutionData(
            last_1m=different_open,
            mark_1m=data.mark_1m,
        ),
    )

    assert trades.loc[0, "exit_reason"] == "take_profit"
