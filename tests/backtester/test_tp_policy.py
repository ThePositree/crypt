import pandas as pd
import pytest

from backtester.execution_sim import ExecutionSim
from backtester.strategies.filtered_donor_portfolio import _tp_policy_for_strategy
from backtester.tp_policy import TpPolicyConfig, adjust_tp_rrr


def test_disabled_policy_preserves_original_geometry() -> None:
    decision = adjust_tp_rrr(
        signal=-1,
        entry_price=73.15,
        sl_price=74.48,
        original_rrr=4.0,
        last_touch_bars=2_000,
        policy=TpPolicyConfig(enabled=False),
    )

    assert decision.effective_rrr == pytest.approx(4.0)
    assert decision.adjusted is False
    assert decision.reason == "disabled"


def test_component_can_mount_portfolio_wide_and_unmount_one_donor() -> None:
    config = {
        "enabled": True,
        "min_original_rrr": 4.0,
        "adjusted_rrr": 3.0,
        "strategies": {"donor_b": {"enabled": False}},
    }

    assert _tp_policy_for_strategy(config, "donor_a").enabled is True
    assert _tp_policy_for_strategy(config, "donor_b").enabled is False


def test_component_can_mount_only_one_donor() -> None:
    config = {
        "enabled": False,
        "strategies": {"donor_b": {"enabled": True, "adjusted_rrr": 2.5}},
    }

    assert _tp_policy_for_strategy(config, "donor_a").enabled is False
    donor_b = _tp_policy_for_strategy(config, "donor_b")
    assert donor_b.enabled is True
    assert donor_b.adjusted_rrr == pytest.approx(2.5)


def test_policy_adjusts_wide_target_without_removing_entry() -> None:
    decision = adjust_tp_rrr(
        signal=-1,
        entry_price=73.15,
        sl_price=74.48,
        original_rrr=4.0,
        last_touch_bars=None,
        policy=TpPolicyConfig(
            enabled=True,
            min_original_rrr=4.0,
            min_tp_distance_pct=0.07,
            min_last_touch_bars=None,
            adjusted_rrr=3.0,
        ),
    )

    assert decision.adjusted is True
    assert decision.effective_rrr == pytest.approx(3.0)
    assert decision.reason == "adjusted_distance"
    assert decision.tp_distance_pct == pytest.approx(0.0727, rel=1e-3)


def test_policy_can_trigger_on_stale_level_when_distance_is_below_floor() -> None:
    decision = adjust_tp_rrr(
        signal=1,
        entry_price=100.0,
        sl_price=95.0,
        original_rrr=4.0,
        last_touch_bars=720,
        policy=TpPolicyConfig(
            enabled=True,
            min_original_rrr=4.0,
            min_tp_distance_pct=0.30,
            min_last_touch_bars=720,
            adjusted_rrr=2.5,
        ),
    )

    assert decision.adjusted is True
    assert decision.effective_rrr == pytest.approx(2.5)
    assert decision.reason == "adjusted_recency"


def test_missing_recency_does_not_satisfy_recency_condition() -> None:
    decision = adjust_tp_rrr(
        signal=1,
        entry_price=100.0,
        sl_price=98.0,
        original_rrr=4.0,
        last_touch_bars=None,
        policy=TpPolicyConfig(
            enabled=True,
            min_original_rrr=4.0,
            min_tp_distance_pct=None,
            min_last_touch_bars=720,
            adjusted_rrr=2.5,
        ),
    )

    assert decision.adjusted is False
    assert decision.reason == "reachability_conditions_not_met"


def test_execution_sim_records_adjusted_geometry_and_keeps_risk_size() -> None:
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0, 108.0, 110.0],
            "high": [101.0, 108.0, 111.0, 111.0],
            "low": [99.0, 99.0, 107.0, 109.0],
            "close": [100.0, 107.0, 110.0, 110.0],
            "volume": [1.0] * 4,
            "signal_events": [
                [
                    {
                        "signal": 1,
                        "sl_price": 95.0,
                        "rrr": 4.0,
                        "tp_policy_enabled": True,
                        "tp_policy_min_original_rrr": 4.0,
                        "tp_policy_min_distance_pct": 0.15,
                        "tp_policy_min_last_touch_bars": None,
                        "tp_policy_adjusted_rrr": 2.0,
                    }
                ],
                [],
                [],
                [],
            ],
        },
        index=index,
    )
    trades = ExecutionSim(
        initial_capital=1_000.0,
        risk_percent=1.0,
        max_positions=1,
        min_net_exposure=0.0,
    ).run(frame)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["original_rrr"] == pytest.approx(4.0)
    assert trade["effective_rrr"] == pytest.approx(2.0)
    assert bool(trade["tp_adjusted"]) is True
    assert trade["tp_adjustment_reason"] == "adjusted_distance"
    assert trade["tp_price"] == pytest.approx(110.0)
