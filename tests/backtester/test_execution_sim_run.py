import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from backtester.execution_sim import ExecutionSim, ExitReason, Position
from backtester.results_analyzer import ResultsAnalyzer


def _df_not_enough_bars() -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=1, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "signal": [1],
            "sl_price": [99.0],
        },
        index=idx,
    )


def _base_df(
    *,
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    signals: list[int],
    sl_prices: list[float | float],
    entry_prices: list[float | None] | None = None,
    risk_percents: list[float] | None = None,
    rrrs: list[float] | None = None,
    trail_atrs: list[float] | None = None,
    start: str = "2026-01-01",
    freq: str = "D",
) -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(opens), freq=freq)
    data: dict[str, list] = {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "signal": signals,
        "sl_price": sl_prices,
    }
    if entry_prices is not None:
        data["entry_price"] = entry_prices
    if risk_percents is not None:
        data["risk_percent"] = risk_percents
    if rrrs is not None:
        data["rrr"] = rrrs
    if trail_atrs is not None:
        data["trail_atr"] = trail_atrs
    return pd.DataFrame(data, index=idx)


def test_run_returns_empty_on_not_enough_bars():
    sim = ExecutionSim(initial_capital=1000.0)
    df = _df_not_enough_bars()

    trades = sim.run(df)

    assert isinstance(trades, pd.DataFrame)
    assert trades.empty


def test_per_signal_ttl_overrides_simulator_default() -> None:
    df = _base_df(
        opens=[100.0, 100.0, 100.0, 100.0],
        highs=[100.5, 100.5, 100.5, 100.5],
        lows=[99.5, 99.5, 99.5, 99.5],
        closes=[100.0, 100.0, 100.0, 100.0],
        signals=[1, 0, 0, 0],
        sl_prices=[99.0, 99.0, 99.0, 99.0],
    )
    df["position_ttl_bars"] = 1

    trades = ExecutionSim(
        initial_capital=10_000.0,
        position_ttl_bars=10,
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "ttl_expired"
    assert trades.iloc[0]["position_ttl_bars"] == 1


def test_signal_events_open_multiple_positions_on_one_bar() -> None:
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "signal_events": [
                [
                    {
                        "signal": 1,
                        "sl_price": 99.0,
                        "selected_strategy": "alpha",
                    },
                    {
                        "signal": 1,
                        "sl_price": 98.0,
                        "selected_strategy": "beta",
                    },
                ],
                [],
                [],
            ],
        },
        index=idx,
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        max_positions=0,
        rrr=2.0,
    ).run(df)

    assert len(trades) == 2
    assert trades["selected_strategy"].tolist() == ["alpha", "beta"]
    assert trades["open_positions_before"].tolist() == [0, 1]
    assert trades["total_locked_margin_before"].iloc[1] > 0


def test_signal_events_request_trailing_atr() -> None:
    idx = pd.date_range("2026-01-01", periods=20, freq="D")
    signal_events = [[] for _ in range(len(idx))]
    signal_events[15] = [
        {
            "signal": 1,
            "sl_price": 99.0,
            "rrr": 2.0,
            "trail_activation_rrr": 1.0,
            "trail_distance_atr": 0.25,
            "selected_strategy": "alpha",
        }
    ]
    df = pd.DataFrame(
        {
            "open": [100.0] * len(idx),
            "high": [100.5] * 17 + [103.0, 103.0, 103.0],
            "low": [99.5] * 17 + [100.5, 100.5, 100.5],
            "close": [100.0] * 17 + [102.0, 102.0, 102.0],
            "signal_events": signal_events,
        },
        index=idx,
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        max_positions=0,
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "trailing_stop"
    assert trades.iloc[0]["trail_activation_rrr"] == 1.0


def test_partial_same_side_close_uses_preserved_okx_average_entry() -> None:
    timestamp = pd.Timestamp("2026-01-01", tz="UTC")
    first = Position(
        signal_time=timestamp,
        entry_time=timestamp,
        entry_price=100.0,
        aggregate_entry_price=150.0,
        risk_base_capital=1_000.0,
        size=1.0,
        tp_price=200.0,
        sl_price=90.0,
        bar_opened=0,
        fee_entry=0.0,
        capital_before=1_000.0,
        leverage=2.0,
        locked_margin=75.0,
        available_balance_before=1_000.0,
        open_positions_before=0,
        total_locked_margin_before=0.0,
        total_locked_margin_after_entry=150.0,
        is_long=True,
        liquidation_price=75.0,
        maintenance_margin_rate=0.004,
        liquidation_fee_rate=0.0005,
        liquidation_buffer_pct=0.005,
        maintenance_margin_tier_schedule=None,
        metadata={},
    )
    remaining = replace(
        first,
        entry_price=200.0,
        tp_price=300.0,
        sl_price=190.0,
        open_positions_before=1,
    )
    history: list[dict] = []
    sim = ExecutionSim(initial_capital=1_000.0, taker_fee=0.0, maker_fee=0.0)

    capital = sim._record_position_exit(
        pos=first,
        exit_reason=ExitReason.TTL_EXPIRED,
        exit_price=150.0,
        capital=1_000.0,
        i=1,
        next_time=timestamp + pd.Timedelta(hours=1),
        trade_history=history,
    )
    sim._refresh_aggregate_liquidation([remaining])

    assert history[0]["entry_price"] == pytest.approx(100.0)
    assert history[0]["aggregate_entry_price"] == pytest.approx(150.0)
    assert history[0]["pnl_abs"] == pytest.approx(0.0)
    assert capital == pytest.approx(1_000.0)
    assert remaining.entry_price == pytest.approx(200.0)
    assert remaining.aggregate_entry_price == pytest.approx(150.0)
    assert remaining.locked_margin == pytest.approx(75.0)


def test_same_side_entry_updates_one_okx_average_and_margin_total() -> None:
    idx = pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0, 91.0, 91.0],
            "high": [101.0, 101.0, 91.0, 91.0],
            "low": [99.0, 95.0, 90.5, 90.5],
            "close": [100.0, 100.0, 91.0, 91.0],
            "volume": 1.0,
            "signal_events": [
                [
                    {
                        "signal": 1,
                        "sl_price": 90.0,
                        "rrr": 20.0,
                        "risk_percent": 1.0,
                    }
                ],
                [
                    {
                        "signal": 1,
                        "sl_price": 90.0,
                        "rrr": 20.0,
                        "risk_percent": 0.1,
                    }
                ],
                [],
                [],
            ],
        },
        index=idx,
    )
    sim = ExecutionSim(
        initial_capital=1_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        max_positions=0,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(frame)

    assert list(trades["exit_reason"]) == ["open", "open"]
    assert list(trades["entry_price"]) == pytest.approx([100.0, 91.0])
    aggregate_entry = (trades["entry_price"] * trades["size"]).sum() / trades["size"].sum()
    assert list(trades["aggregate_entry_price"]) == pytest.approx(
        [aggregate_entry, aggregate_entry]
    )
    assert trades["locked_margin"].sum() == pytest.approx(
        trades["size"].sum() * aggregate_entry / trades["leverage"].iloc[0]
    )


def test_monthly_profit_capital_sweep_banks_profit_before_next_month_entries() -> None:
    idx = pd.to_datetime(
        [
            "2026-01-30",
            "2026-01-31",
            "2026-02-01",
            "2026-02-02",
            "2026-02-03",
        ]
    )
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 101.0, 101.0, 101.0, 101.0],
            "low": [99.5, 100.0, 100.0, 100.0, 100.0],
            "close": [100.0, 100.5, 100.5, 100.5, 100.5],
            "signal": [1, 0, 1, 0, 0],
            "sl_price": [99.0, 99.0, 99.0, 99.0, 99.0],
        },
        index=idx,
    )

    trades = ExecutionSim(
        initial_capital=1000.0,
        risk_percent=10.0,
        rrr=1.0,
        taker_fee=0.0,
        maker_fee=0.0,
        max_allowed_margin=100.0,
        max_allowed_leverage=100.0,
        capital_sweep="monthly_profit",
    ).run(df)

    assert len(trades) == 2
    assert trades["pnl_abs"].tolist() == [100.0, 100.0]
    assert trades["capital_sweep_amount"].tolist() == [100.0, 0.0]
    assert trades.iloc[0]["capital_sweep_month"] == "2026-01"
    assert pd.isna(trades.iloc[1]["capital_sweep_month"])
    assert trades["banked_profit_after"].tolist() == [100.0, 100.0]
    assert trades["capital_before"].tolist() == [1000.0, 1000.0]
    assert trades["risk_base_capital"].tolist() == [1000.0, 1000.0]


def test_monthly_profit_capital_sweep_is_recorded_without_later_trades() -> None:
    idx = pd.to_datetime(
        [
            "2026-01-10",
            "2026-01-11",
            "2026-01-12",
            "2026-01-13",
            "2026-02-01",
        ]
    )
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 101.0, 101.0, 101.0, 101.0],
            "low": [99.5, 100.0, 100.0, 100.0, 100.0],
            "close": [100.0, 100.5, 100.5, 100.5, 100.5],
            "signal": [1, 0, 0, 0, 0],
            "sl_price": [99.0, 99.0, 99.0, 99.0, 99.0],
        },
        index=idx,
    )

    trades = ExecutionSim(
        initial_capital=1000.0,
        risk_percent=10.0,
        rrr=1.0,
        taker_fee=0.0,
        maker_fee=0.0,
        max_allowed_margin=100.0,
        max_allowed_leverage=100.0,
        capital_sweep="monthly_profit",
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["pnl_abs"] == 100.0
    assert trades.iloc[0]["capital_sweep_amount"] == 100.0
    assert trades.iloc[0]["capital_sweep_month"] == "2026-01"
    assert trades.iloc[0]["banked_profit_after"] == 100.0
    assert trades.iloc[0]["trading_capital_after_sweep"] == 1000.0


def test_position_group_drains_before_new_group_entry() -> None:
    df = _base_df(
        opens=[100.0, 100.0, 100.0, 100.0],
        highs=[100.5, 100.5, 102.5, 102.5],
        lows=[99.5, 99.5, 99.5, 99.5],
        closes=[100.0, 100.0, 102.0, 102.0],
        signals=[1, 1, 0, 0],
        sl_prices=[99.0, 99.0, 99.0, 99.0],
    )
    df["position_group"] = ["a", "b", "b", "b"]
    df["drain_on_group_change"] = True

    trades = ExecutionSim(
        initial_capital=10_000.0,
        rrr=2.0,
        max_positions=0,
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["position_group"] == "a"


def test_per_signal_tp_pct_geometry_overrides_default() -> None:
    df = _base_df(
        opens=[100.0, 100.0, 100.0],
        highs=[100.5, 102.5, 102.5],
        lows=[99.5, 99.5, 99.5],
        closes=[100.0, 102.0, 102.0],
        signals=[1, 0, 0],
        sl_prices=[90.0, 90.0, 90.0],
    )
    df["exit_geometry"] = "tp_pct"
    df["tp_move_pct"] = 0.02
    df["structural_sl_mode"] = "ignore"
    df["min_tp_move_pct"] = 0.004

    trades = ExecutionSim(
        initial_capital=10_000.0,
        rrr=2.0,
        max_allowed_leverage=100.0,
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["tp_price"] == pytest.approx(102.0)


@pytest.mark.parametrize("missing", ["open", "high", "low", "close", "signal", "sl_price"])
def test_run_raises_on_missing_required_columns(missing: str):
    idx = pd.date_range("2026-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "signal": [1, 0],
            "sl_price": [99.0, 100.0],
        },
        index=idx,
    )
    df = df.drop(columns=[missing])

    sim = ExecutionSim(initial_capital=1000.0)

    with pytest.raises(ValueError) as excinfo:
        sim.run(df)

    msg = str(excinfo.value)
    assert "Missing required columns" in msg
    assert missing in msg


def test_run_raises_on_nan_in_risk_percent():
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "signal": [1, 0, 0],
            "sl_price": [99.0, 100.0, 101.0],
            "risk_percent": [1.0, math.nan, 1.0],
        },
        index=idx,
    )

    sim = ExecutionSim(initial_capital=1000.0)

    with pytest.raises(ValueError) as excinfo:
        sim.run(df)

    msg = str(excinfo.value)
    assert "NaN in column 'risk_percent'" in msg
    assert "total NaN count: 1" in msg


def test_run_raises_on_nan_in_rrr():
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "signal": [1, 0, 0],
            "sl_price": [99.0, 100.0, 101.0],
            "rrr": [2.0, math.nan, 2.0],
        },
        index=idx,
    )

    sim = ExecutionSim(initial_capital=1000.0)

    with pytest.raises(ValueError) as excinfo:
        sim.run(df)

    msg = str(excinfo.value)
    assert "NaN in column 'rrr'" in msg
    assert "total NaN count: 1" in msg


def test_signal_zero_or_invalid_sl_skips_entry():
    # First bar has signal but SL >= future entry price -> invalid
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 102.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 101.5, 102.5],
        signals=[1, 0, 0],
        sl_prices=[200.0, 100.0, 101.0],
    )
    sim = ExecutionSim(initial_capital=1000.0)

    trades = sim.run(df)

    assert trades.empty


def test_basic_long_take_profit_path():
    # Long entry from bar 0 at bar 1 open
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]

    # Entry happens on bar 1 at its open
    assert trade["entry_time"] == df.index[1]
    assert trade["entry_price"] == pytest.approx(101.0)
    assert trade["sl_price"] == pytest.approx(95.0)

    risk_value = 1000.0 * (1.0 / 100.0)
    sl_dist = 101.0 - 95.0
    size = risk_value / sl_dist
    position_value = size * 101.0
    fee_entry = position_value * 0.001
    tp_price = 101.0 + sl_dist * 2.0

    assert trade["size"] == pytest.approx(size)
    assert trade["tp_price"] == pytest.approx(tp_price)
    assert trade["fee_entry"] == pytest.approx(fee_entry)

    # Triggered limit TP is conservatively charged as taker.
    exit_value = size * tp_price
    fee_exit = exit_value * 0.001
    pnl_abs = exit_value - position_value - (fee_entry + fee_exit)

    assert trade["exit_reason"] == "take_profit"
    assert trade["exit_price"] == pytest.approx(tp_price)
    assert trade["fee_exit"] == pytest.approx(fee_exit)
    assert trade["pnl_abs"] == pytest.approx(pnl_abs)
    assert trade["capital_before"] == pytest.approx(1000.0)
    assert trade["capital_after"] == pytest.approx(1000.0 + pnl_abs)
    assert trade["leverage"] == pytest.approx(14.0)
    assert trade["locked_margin"] == pytest.approx(position_value / 14.0)
    assert trade["available_balance_before"] == pytest.approx(1000.0)
    assert trade["open_positions_before"] == 0
    assert trade["total_locked_margin_before"] == pytest.approx(0.0)
    assert trade["total_locked_margin_after_entry"] == pytest.approx(position_value / 14.0)
    assert trade["liquidation_price"] < trade["sl_price"] - trade["entry_price"] * 0.005
    assert trade["holding_bars"] == 1
    assert bool(trade["is_long"]) is True


def test_basic_short_take_profit_path():
    # Short entry from bar 0 at bar 1 open
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 103.0, 103.0],
        lows=[99.0, 80.0, 101.0],
        closes=[100.5, 90.0, 102.5],
        signals=[-1, 0, 0],
        sl_prices=[105.0, 100.0, 101.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]

    assert trade["entry_time"] == df.index[1]
    assert bool(trade["is_long"]) is False

    risk_value = 1000.0 * (1.0 / 100.0)
    entry_price = 101.0
    sl_price = 105.0
    sl_dist = sl_price - entry_price
    size = risk_value / sl_dist
    position_value = size * entry_price
    fee_entry = position_value * 0.001
    tp_price = entry_price - sl_dist * 2.0
    exit_value = size * tp_price
    fee_exit = exit_value * 0.001
    pnl_abs = position_value - exit_value - (fee_entry + fee_exit)

    assert trade["entry_price"] == pytest.approx(entry_price)
    assert trade["sl_price"] == pytest.approx(sl_price)
    assert trade["tp_price"] == pytest.approx(tp_price)
    assert trade["size"] == pytest.approx(size)
    assert trade["fee_entry"] == pytest.approx(fee_entry)
    assert trade["exit_price"] == pytest.approx(tp_price)
    assert trade["fee_exit"] == pytest.approx(fee_exit)
    assert trade["pnl_abs"] == pytest.approx(pnl_abs)


def test_long_trailing_stop_activates_and_exits_with_taker_fee():
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 102.0],
        highs=[101.0, 110.0, 103.0, 103.0],
        lows=[99.0, 107.0, 101.0, 101.0],
        closes=[100.5, 108.0, 102.5, 102.5],
        signals=[1, 0, 0, 0],
        sl_prices=[95.0, 100.0, 101.0, 101.0],
        trail_atrs=[2.0, 2.0, 2.0, 2.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.5,
        trail_distance_atr=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "trailing_stop"
    assert trade["exit_price"] == pytest.approx(102.0)
    assert trade["trail_stop_price"] == pytest.approx(108.0)
    assert trade["trail_activation_price"] == pytest.approx(104.0)
    assert trade["trail_callback_spread"] == pytest.approx(2.0)
    assert bool(trade["trail_active"]) is True
    assert trade["fee_exit"] == pytest.approx(trade["size"] * 102.0 * 0.001)


def test_short_trailing_stop_activates_and_exits_with_taker_fee():
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 102.0],
        highs=[101.0, 98.0, 103.0, 103.0],
        lows=[99.0, 95.0, 101.0, 101.0],
        closes=[100.5, 96.0, 102.5, 102.5],
        signals=[-1, 0, 0, 0],
        sl_prices=[105.0, 100.0, 101.0, 101.0],
        trail_atrs=[2.0, 2.0, 2.0, 2.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.5,
        trail_distance_atr=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "trailing_stop"
    assert trade["exit_price"] == pytest.approx(102.0)
    assert trade["trail_stop_price"] == pytest.approx(97.0)
    assert bool(trade["trail_active"]) is True
    assert trade["fee_exit"] == pytest.approx(trade["size"] * 102.0 * 0.001)


def test_per_bar_risk_percent_and_rrr_override_defaults():
    # risk_percent and rrr columns should override instance values
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 150.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
        risk_percents=[5.0, 5.0, 5.0],
        rrrs=[3.0, 3.0, 3.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]

    # risk_value uses 5% of capital, rrr uses 3.0 from column
    risk_value = 1000.0 * (5.0 / 100.0)
    entry_price = 101.0
    sl_price = 95.0
    sl_dist = entry_price - sl_price
    size = risk_value / sl_dist
    tp_price = entry_price + sl_dist * 3.0

    assert trade["size"] == pytest.approx(size)
    assert trade["tp_price"] == pytest.approx(tp_price)


def test_leverage_limit_blocks_position():
    # Make position value big enough so required leverage > max_allowed_leverage
    df = _base_df(
        opens=[10_000.0, 11_000.0, 12_000.0],
        highs=[10_100.0, 11_500.0, 12_500.0],
        lows=[9_900.0, 10_500.0, 11_500.0],
        closes=[10_050.0, 11_000.0, 12_000.0],
        signals=[1, 0, 0],
        sl_prices=[9_000.0, 10_000.0, 11_000.0],
    )
    # Very small max_allowed_margin to force high leverage
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=50.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=2.0,
        max_allowed_margin=0.01,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert trades.empty


def test_fee_too_large_blocks_position():
    # Very high taker_fee so that fee_entry >= 200% of risk_value
    df = _base_df(
        opens=[100.0, 200.0, 300.0],
        highs=[110.0, 220.0, 320.0],
        lows=[90.0, 180.0, 280.0],
        closes=[105.0, 210.0, 310.0],
        signals=[1, 0, 0],
        sl_prices=[50.0, 150.0, 250.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=2.0,  # 200%
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert trades.empty


def test_min_net_exposure_blocks_position():
    # Force net_exposure < min_net_exposure * available_balance
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 102.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 101.5, 102.5],
        signals=[1, 0, 0],
        sl_prices=[99.9, 100.0, 101.0],  # very tight SL
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=1000.0,
        min_net_exposure=2.0,  # require more than the full balance as net exposure
    )

    trades = sim.run(df)

    assert trades.empty


def test_max_positions_limit():
    # Two consecutive signals with max_positions=1
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 103.0],
        highs=[101.0, 150.0, 150.0, 150.0],
        lows=[99.0, 100.0, 101.0, 102.0],
        closes=[100.5, 120.0, 120.0, 120.0],
        signals=[1, 1, 0, 0],
        sl_prices=[95.0, 96.0, 97.0, 98.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    # Current behavior: after first position is closed, second signal can open a new one
    assert len(trades) == 2


def test_stop_loss_for_long_and_short():
    # Long: SL hit on low
    df_long = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 102.0, 103.0],
        lows=[99.0, 95.0, 101.0],
        closes=[100.5, 95.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
    )
    sim_long = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )
    trades_long = sim_long.run(df_long)
    assert len(trades_long) == 1
    assert trades_long.iloc[0]["exit_reason"] == "stop_loss"

    # Short: SL hit on high
    df_short = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 105.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[-1, 0, 0],
        sl_prices=[105.0, 100.0, 101.0],
    )
    sim_short = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )
    trades_short = sim_short.run(df_short)
    assert len(trades_short) == 1
    assert trades_short.iloc[0]["exit_reason"] == "stop_loss"


def test_nearer_structural_stop_precedes_liquidation_on_last_price_path() -> None:
    df = _base_df(
        opens=[100.0, 100.0, 100.0],
        highs=[101.0, 101.0, 101.0],
        lows=[99.0, 80.0, 99.0],
        closes=[100.0, 90.0, 100.0],
        signals=[1, 0, 0],
        sl_prices=[95.0, 95.0, 95.0],
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=25.0,
        min_net_exposure=0.0,
        bar_exit_policy="worst_case",
    ).run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == pytest.approx(trade["sl_price"])


def test_remaining_position_closes_when_constituent_exit_breaks_liquidation_buffer() -> None:
    timestamp = pd.Timestamp("2026-01-01", tz="UTC")

    def position(
        *,
        entry: float,
        stop: float,
        size: float,
        ttl: int,
    ) -> Position:
        return Position(
            signal_time=timestamp,
            entry_time=timestamp,
            entry_price=entry,
            risk_base_capital=10_000.0,
            size=size,
            tp_price=entry - 10.0,
            sl_price=stop,
            bar_opened=0,
            fee_entry=0.0,
            capital_before=10_000.0,
            leverage=21.0,
            locked_margin=entry * size / 21.0,
            available_balance_before=10_000.0,
            open_positions_before=0,
            total_locked_margin_before=0.0,
            total_locked_margin_after_entry=entry * size / 21.0,
            is_long=False,
            liquidation_price=134.27244187966195,
            maintenance_margin_rate=0.004,
            liquidation_fee_rate=0.0005,
            liquidation_buffer_pct=0.005,
            maintenance_margin_tier_schedule=None,
            metadata={},
            position_ttl_bars=ttl,
        )

    survivor = position(
        entry=124.05470333604543,
        stop=128.7803461450231,
        size=30.342648885906524,
        ttl=0,
    )
    expires = position(
        entry=130.6547307237704,
        stop=133.6157863235054,
        size=74.57151938182729,
        ttl=1,
    )
    sim = ExecutionSim(initial_capital=10_000.0, taker_fee=0.0)
    history: list[dict] = []

    _, remaining = sim._update_active_positions(
        active_positions=[survivor, expires],
        capital=10_000.0,
        i=0,
        current_open=125.0,
        current_high=126.0,
        current_low=124.0,
        trail_atr=None,
        next_open=125.0,
        next_time=timestamp + pd.Timedelta(hours=1),
        trade_history=history,
    )

    assert remaining == []
    assert {trade["exit_reason"] for trade in history} == {
        "ttl_expired",
        "unsafe_liquidation_buffer",
    }


def test_closed_trade_exports_maintenance_margin_tier_schedule() -> None:
    df = _base_df(
        opens=[100.0, 100.0, 100.0],
        highs=[100.5, 101.0, 103.0],
        lows=[99.5, 99.0, 99.0],
        closes=[100.0, 100.0, 102.0],
        signals=[1, 0, 0],
        sl_prices=[99.0, 99.0, 99.0],
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=25.0,
        min_net_exposure=0.0,
        maintenance_margin_tier_schedule="okx_sol_usdt_swap_2026_06_29",
    ).run(df)

    assert len(trades) == 1
    assert trades.iloc[0]["maintenance_margin_tier_schedule"] == ("okx_sol_usdt_swap_2026_06_29")


def test_ttl_expiration_exit():
    # Position never hits TP or SL, should exit by TTL
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 103.0],
        highs=[101.0, 102.0, 103.0, 104.0],
        lows=[99.0, 100.0, 101.0, 102.0],
        closes=[100.5, 101.5, 102.5, 103.5],
        signals=[1, 0, 0, 0],
        sl_prices=[95.0, 96.0, 97.0, 98.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        position_ttl_bars=2,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "ttl_expired"
    assert trade["holding_bars"] == 2


def test_open_positions_are_reported_without_realized_pnl_at_last_bar():
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 102.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 101.5, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 96.0, 97.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "open"
    assert pd.isna(trade["exit_time"])
    assert pd.isna(trade["exit_price"])
    assert pd.isna(trade["pnl_abs"])
    assert pd.isna(trade["capital_after"])
    assert trade["locked_margin"] > 0
    assert trade["available_balance_before"] == pytest.approx(1000.0)
    assert trade["total_locked_margin_after_entry"] == pytest.approx(trade["locked_margin"])


def test_liquidation_safe_common_leverage_rejects_incompatible_wider_stop():
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 103.0, 104.0],
        highs=[101.0, 102.0, 150.0, 150.0, 150.0],
        lows=[99.0, 100.0, 101.0, 102.0, 103.0],
        closes=[100.5, 120.0, 120.0, 120.0, 120.0],
        signals=[1, 1, 0, 0, 0],
        sl_prices=[95.0, 50.0, 97.0, 98.0, 99.0],
    )
    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=10.0,
        rrr=2.0,
        max_positions=2,
        max_allowed_leverage=100.0,
        max_allowed_margin=0.5,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    assert trades["leverage"].tolist() == [14.0]
    assert trades["exit_reason"].tolist() == ["take_profit"]


def test_isolated_futures_insufficient_margin_blocks_position():
    # Configure so that required_margin > max_allowed_margin * available_balance
    df = _base_df(
        opens=[1_000.0, 2_000.0, 3_000.0],
        highs=[1_100.0, 2_500.0, 3_500.0],
        lows=[900.0, 1_500.0, 2_500.0],
        closes=[1_050.0, 2_200.0, 3_200.0],
        signals=[1, 0, 0],
        sl_prices=[500.0, 1_500.0, 2_500.0],
    )
    sim = ExecutionSim(
        initial_capital=1_000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=100.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        max_allowed_margin=0.01,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert trades.empty


def test_margin_state_tracks_concurrent_positions_at_entry():
    df = _base_df(
        opens=[100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        highs=[101.0, 109.0, 109.0, 109.0, 109.0, 109.0, 109.0],
        lows=[99.0, 96.0, 96.0, 96.0, 96.0, 96.0, 96.0],
        closes=[100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        signals=[1, 1, 1, 0, 0, 0, 0],
        sl_prices=[95.0, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=0,
        position_ttl_bars=3,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 3
    assert trades["open_positions_before"].tolist() == [0, 1, 2]
    assert trades["available_balance_before"].tolist() == pytest.approx([1000.0, 987.5, 975.15625])
    assert trades["locked_margin"].tolist() == pytest.approx([12.5, 12.34375, 12.189453125])
    assert trades["total_locked_margin_before"].tolist() == pytest.approx([0.0, 12.5, 24.84375])
    assert trades["total_locked_margin_after_entry"].tolist() == pytest.approx(
        [12.5, 24.84375, 37.033203125]
    )
    assert trades["leverage"].tolist() == pytest.approx([16.0, 16.0, 16.0])


def test_trades_dataframe_columns_and_types():
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert not trades.empty

    # Columns are taken from trade_history dict keys in run()
    expected_columns = {
        "signal_time",
        "execution_sequence",
        "entry_time",
        "exit_time",
        "entry_price",
        "aggregate_entry_price",
        "risk_base_capital",
        "exit_price",
        "size",
        "pnl_abs",
        "pnl_rel",
        "fee_entry",
        "fee_exit",
        "tp_price",
        "sl_price",
        "trail_activation_rrr",
        "trail_distance_atr",
        "trail_activation_price",
        "trail_callback_spread",
        "trail_stop_price",
        "trail_active",
        "exit_reason",
        "capital_before",
        "capital_after",
        "holding_bars",
        "position_ttl_bars",
        "position_group",
        "leverage",
        "locked_margin",
        "available_balance_before",
        "open_positions_before",
        "total_locked_margin_before",
        "total_locked_margin_after_entry",
        "is_long",
        "liquidation_price",
        "maintenance_margin_rate",
        "liquidation_fee_rate",
        "liquidation_buffer_pct",
        "maintenance_margin_tier_schedule",
        "entry_bar_index",
        "exit_bar_index",
        "capital_sweep_amount",
        "capital_sweep_month",
        "banked_profit_after",
        "trading_capital_after_sweep",
        "account_capital_at_end",
        "account_capital_at_end_time",
        "account_initial_capital",
    }

    assert set(trades.columns) == expected_columns

    row = trades.iloc[0]
    assert isinstance(row["signal_time"], pd.Timestamp)
    assert isinstance(row["entry_time"], pd.Timestamp)
    assert row["risk_base_capital"] == pytest.approx(1000.0)
    assert isinstance(row["exit_time"], pd.Timestamp)
    assert isinstance(row["is_long"], (bool, np.bool_))  # type: ignore[name-defined]
    assert pd.isna(row["maintenance_margin_tier_schedule"])
    assert isinstance(row["entry_bar_index"], (int, float, np.integer))
    assert isinstance(row["exit_bar_index"], (int, float, np.integer))
    assert row["exit_bar_index"] >= row["entry_bar_index"]
    # holding_bars = (exit_bar_index + 1) - entry_bar_index
    assert row["holding_bars"] == (row["exit_bar_index"] - row["entry_bar_index"]) + 1


def test_run_preserves_signal_metadata_on_trade_rows():
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
    )
    df["confidence"] = [82.0, 0.0, 0.0]
    df["score"] = [0.42, 0.0, 0.0]
    df["regime"] = ["trending", "ranging", "ranging"]
    df["decision"] = ["BUY", "HOLD", "HOLD"]
    df["rationale"] = ["test buy", "hold", "hold"]
    df["strength_trend"] = [0.5, 0.0, 0.0]

    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["signal_time"] == df.index[0]
    assert trade["entry_time"] == df.index[1]
    assert trade["risk_base_capital"] == pytest.approx(1000.0)
    assert trade["confidence"] == pytest.approx(82.0)
    assert trade["score"] == pytest.approx(0.42)
    assert trade["regime"] == "trending"
    assert trade["decision"] == "BUY"
    assert trade["rationale"] == "test buy"
    assert trade["strength_trend"] == pytest.approx(0.5)


def test_monthly_risk_base_uses_window_start_capital_after_prior_loss():
    df = _base_df(
        opens=[100.0, 100.0, 100.0, 100.0],
        highs=[101.0, 101.0, 100.0, 120.0],
        lows=[99.0, 95.0, 99.0, 99.0],
        closes=[100.0, 100.0, 100.0, 100.0],
        signals=[1, 1, 0, 0],
        sl_prices=[95.0, 95.0, 95.0, 95.0],
        start="2026-01-01",
        freq="D",
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=2.0,
        rrr=2.0,
        max_positions=1,
        position_ttl_bars=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        risk_base_period="monthly",
    )

    trades = sim.run(df)

    assert len(trades) == 2
    first, second = trades.iloc[0], trades.iloc[1]
    assert first["pnl_abs"] == pytest.approx(-20.0)
    assert first["capital_after"] == pytest.approx(980.0)
    assert second["risk_base_capital"] == pytest.approx(1000.0)
    assert second["size"] == pytest.approx(4.0)


def test_trade_risk_base_uses_current_capital_after_prior_loss():
    df = _base_df(
        opens=[100.0, 100.0, 100.0, 100.0],
        highs=[101.0, 101.0, 100.0, 120.0],
        lows=[99.0, 95.0, 99.0, 99.0],
        closes=[100.0, 100.0, 100.0, 100.0],
        signals=[1, 1, 0, 0],
        sl_prices=[95.0, 95.0, 95.0, 95.0],
        start="2026-01-01",
        freq="D",
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=2.0,
        rrr=2.0,
        max_positions=1,
        position_ttl_bars=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        risk_base_period="trade",
    )

    trades = sim.run(df)

    assert len(trades) == 2
    assert trades.iloc[1]["risk_base_capital"] == pytest.approx(980.0)
    assert trades.iloc[1]["size"] == pytest.approx(3.92)


def test_intrabar_policy_best_case_prefers_take_profit():
    # Long position where both TP and SL are inside the same bar range.
    # With bar_exit_policy="best_case" we expect TP to be chosen.
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 90.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        bar_exit_policy="best_case",
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]

    # Both TP and SL are inside bar 1 range: high=120 >= tp_price, low=90 <= sl_price.
    assert trade["exit_reason"] == "take_profit"


def test_intrabar_policy_worst_case_prefers_stop_loss():
    # Short position where both TP and SL are inside the same bar range.
    # With bar_exit_policy="worst_case" we expect SL to be chosen.
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 105.0, 103.0],
        lows=[99.0, 80.0, 101.0],
        closes=[100.5, 90.0, 102.5],
        signals=[-1, 0, 0],
        sl_prices=[105.0, 100.0, 101.0],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        bar_exit_policy="worst_case",
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]

    # Both TP and SL are inside bar 1 range: low<=tp_price and high>=sl_price.
    assert trade["exit_reason"] == "stop_loss"


def test_max_daily_profit_blocks_new_entries_after_limit():
    # rrr = 3, max_daily_profit = 4 -> достаточно двух профитных сделок (2 * 3 = 6 > 4)
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 103.0, 104.0],
        # Высокие значения high и low, чтобы всегда срабатывать TP, а SL не задевался
        highs=[200.0, 210.0, 220.0, 230.0, 240.0],
        lows=[96.0, 97.0, 98.0, 99.0, 100.0],
        closes=[150.0, 160.0, 170.0, 180.0, 190.0],
        signals=[1, 1, 1, 1, 1],
        sl_prices=[95.0, 96.0, 97.0, 98.0, 99.0],
        start="2026-01-01",
        freq="h",
    )
    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=3.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        max_daily_profit=4.0,
    )

    trades = sim.run(df)

    # Должно быть ровно две профитные сделки, после чего новые не открываются
    assert len(trades) == 2
    assert all(trades["pnl_abs"] > 0)
    # Обе сделки относятся к одному и тому же дню
    assert trades["entry_time"].dt.normalize().nunique() == 1


def test_max_daily_loss_blocks_new_entries_after_limit():
    # rrr = 3, max_daily_loss = 2 -> достаточно одной убыточной сделки (daily_rrr = -1)
    # После второй убыточной сделки daily_rrr = -2, лимит по модулю достигнут.
    df = _base_df(
        opens=[100.0, 101.0, 102.0, 103.0],
        highs=[101.0, 102.0, 103.0, 104.0],
        lows=[50.0, 51.0, 52.0, 53.0],  # всегда бьём SL
        closes=[55.0, 56.0, 57.0, 58.0],
        signals=[1, 1, 1, 1],
        sl_prices=[95.0, 96.0, 97.0, 98.0],
        start="2026-01-01",
        freq="h",
    )
    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=3.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        max_daily_loss=2.0,
    )

    trades = sim.run(df)

    # После достижения лимита по loss новые сделки не открываются
    assert len(trades) >= 1
    assert all(trades["pnl_abs"] < 0)
    # Все сделки в одном дне, и их количество ограничено
    assert trades["entry_time"].dt.normalize().nunique() == 1


def test_trading_hours_blocks_entries_outside_session():
    # Сигналы на каждом баре в течение суток, но торгуем только с 10 до 15 часов
    df = _base_df(
        opens=[100.0] * 24,
        highs=[120.0] * 24,
        lows=[80.0] * 24,
        closes=[110.0] * 24,
        signals=[1] * 24,
        sl_prices=[90.0] * 24,
        start="2026-01-01",
        freq="h",
    )
    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        trading_begin=10,
        trading_end=15,
    )

    trades = sim.run(df)

    # Все входы должны происходить только в допустимые часы
    assert not trades.empty
    entry_hours = trades["entry_time"].dt.hour.unique()
    assert all(10 <= h < 15 for h in entry_hours)


def test_entry_price_within_bar_used_as_entry_and_time_current_bar():
    # Custom entry_price inside bar range, should be used with current bar timestamp
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
        entry_prices=[100.5, None, None],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    # Entry must happen on bar 0 with its custom price
    assert trade["entry_time"] == df.index[0]
    assert trade["entry_price"] == pytest.approx(100.5)
    assert trade["entry_bar_index"] == 0


def test_entry_price_outside_bar_raises_value_error():
    # entry_price above high should be rejected
    df = _base_df(
        opens=[100.0, 101.0],
        highs=[101.0, 102.0],
        lows=[99.0, 100.0],
        closes=[100.5, 101.5],
        signals=[1, 0],
        sl_prices=[95.0, 96.0],
        entry_prices=[200.0, None],
    )
    sim = ExecutionSim(initial_capital=1000.0)

    with pytest.raises(ValueError) as excinfo:
        sim.run(df)

    msg = str(excinfo.value)
    assert "Invalid entry_price" in msg
    # Exact representation may depend on numpy/pandas, so only check core parts
    assert "entry_price=" in msg
    assert "low=" in msg
    assert "high=" in msg


def test_entry_price_nan_on_signal_bar_falls_back_to_next_open():
    # If entry_price is NaN on signal bar, simulator should use next_open/next_time
    df = _base_df(
        opens=[100.0, 101.0, 102.0],
        highs=[101.0, 120.0, 103.0],
        lows=[99.0, 100.0, 101.0],
        closes=[100.5, 110.0, 102.5],
        signals=[1, 0, 0],
        sl_prices=[95.0, 100.0, 101.0],
        entry_prices=[math.nan, None, None],
    )
    sim = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.001,
        maker_fee=0.0002,
        risk_percent=1.0,
        rrr=2.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    )

    trades = sim.run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    # Should behave like the basic long path: entry at next bar open
    assert trade["entry_time"] == df.index[1]
    assert trade["entry_price"] == pytest.approx(101.0)


def test_entry_fee_is_debited_before_next_same_bar_entry() -> None:
    idx = pd.date_range("2026-01-01", periods=2, freq="h")
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [100.5, 100.5],
            "low": [99.5, 99.5],
            "close": [100.0, 100.0],
            "signal_events": [
                [
                    {"signal": 1, "sl_price": 99.0, "selected_strategy": "first"},
                    {"signal": 1, "sl_price": 99.0, "selected_strategy": "second"},
                ],
                [],
            ],
        },
        index=idx,
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0005,
        risk_percent=1.0,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    ).run(df)

    assert len(trades) == 2
    first, second = trades.iloc[0], trades.iloc[1]
    assert first["fee_entry"] == pytest.approx(5.0)
    assert second["capital_before"] == pytest.approx(9_995.0)
    assert second["size"] < first["size"]


def test_precision_policy_rounds_size_protection_and_trailing_geometry() -> None:
    df = _base_df(
        opens=[100.0, 100.0],
        highs=[100.5, 100.5],
        lows=[99.5, 99.5],
        closes=[100.0, 100.0],
        signals=[1, 0],
        sl_prices=[98.934, 99.0],
        trail_atrs=[1.234, 1.234],
        freq="h",
    )

    trades = ExecutionSim(
        initial_capital=10_000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=1.0,
        trail_distance_atr=0.33,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        instrument_precision_policy="okx_sol_usdt_swap_2026_07_01",
    ).run(df)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["size"] == pytest.approx(93.80)
    assert trade["sl_price"] == pytest.approx(98.93)
    assert trade["tp_price"] == pytest.approx(102.13)
    assert trade["trail_activation_price"] == pytest.approx(101.07)
    assert trade["trail_callback_spread"] == pytest.approx(0.41)


def test_open_position_entry_fee_reduces_reported_ending_capital() -> None:
    df = _base_df(
        opens=[100.0, 100.0],
        highs=[100.5, 100.5],
        lows=[99.5, 99.5],
        closes=[100.0, 100.0],
        signals=[1, 0],
        sl_prices=[99.0, 99.0],
        freq="h",
    )
    trades = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0005,
        risk_percent=1.0,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
    ).run(df)

    metrics = ResultsAnalyzer(trades).generate()
    entry_fee = float(trades.iloc[0]["fee_entry"])

    assert trades.iloc[0]["exit_reason"] == "open"
    assert metrics["final_capital"] == pytest.approx(10_000.0 - entry_fee)
    assert metrics["total_pnl_abs"] == pytest.approx(-entry_fee, abs=0.01)
