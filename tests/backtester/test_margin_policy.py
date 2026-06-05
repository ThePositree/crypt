from __future__ import annotations

import pytest

from backtester.margin_policy import (
    effective_margin_fraction,
    per_entry_margin_cap,
    select_leverage_and_locked_margin,
)
from backtester.risk_model import BasicRiskModel, EntryContext


def test_effective_margin_fraction_prefers_finite_position_share() -> None:
    assert effective_margin_fraction(max_allowed_margin=1.0, max_positions=2) == pytest.approx(0.5)
    assert effective_margin_fraction(max_allowed_margin=0.25, max_positions=4) == pytest.approx(0.25)
    assert effective_margin_fraction(max_allowed_margin=0.0, max_positions=5) == pytest.approx(0.2)


def test_per_entry_margin_cap_splits_remaining_slots() -> None:
    cap = per_entry_margin_cap(
        available_balance=10_000.0,
        max_allowed_margin=1.0,
        max_positions=2,
        open_positions=1,
    )
    assert cap == pytest.approx(5_000.0)


def test_select_leverage_prefers_max_allowed_when_position_fits() -> None:
    result = select_leverage_and_locked_margin(
        position_value=40_000.0,
        per_entry_cap=10_000.0,
        max_allowed_leverage=25.0,
    )
    assert result is not None
    leverage, locked = result
    assert leverage == pytest.approx(25.0)
    assert locked == pytest.approx(1_600.0)


def test_select_leverage_rejects_when_min_needed_exceeds_cap() -> None:
    assert (
        select_leverage_and_locked_margin(
            position_value=400_000.0,
            per_entry_cap=10_000.0,
            max_allowed_leverage=25.0,
        )
        is None
    )


def test_locked_margin_scales_monotonically_with_risk_percent() -> None:
    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=25.0,
    )
    locked_values: list[float] = []
    for risk_percent in (1.0, 0.5, 0.25):
        result = model.calculate_position(
            EntryContext(
                signal=-1,
                sl_price=200.5,
                entry_price=200.0,
                capital=10_000.0,
                risk_base_capital=10_000.0,
                total_locked_margin=0.0,
                open_positions=0,
                risk_percent=risk_percent,
                rrr=1.5,
            )
        )
        assert result is not None
        locked_values.append(result.locked_margin)

    assert locked_values[0] > locked_values[1] > locked_values[2]


def test_max_positions_one_allows_low_peak_margin_at_reduced_risk() -> None:
    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=25.0,
    )
    high = model.calculate_position(
        EntryContext(
            signal=-1,
            sl_price=200.5,
            entry_price=200.0,
            capital=10_000.0,
            risk_base_capital=10_000.0,
            total_locked_margin=0.0,
            open_positions=0,
            risk_percent=1.0,
            rrr=1.5,
        )
    )
    low = model.calculate_position(
        EntryContext(
            signal=-1,
            sl_price=200.5,
            entry_price=200.0,
            capital=10_000.0,
            risk_base_capital=10_000.0,
            total_locked_margin=0.0,
            open_positions=0,
            risk_percent=0.25,
            rrr=1.5,
        )
    )
    assert high is not None and low is not None
    assert high.locked_margin / 10_000.0 > 0.10
    assert low.locked_margin / 10_000.0 < high.locked_margin / 10_000.0
