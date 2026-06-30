from __future__ import annotations

import pytest

from backtester.margin_policy import (
    OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    aggregate_liquidation_is_beyond_stops,
    effective_margin_fraction,
    estimate_linear_liquidation_price,
    leverage_is_within_size_tier,
    liquidation_is_beyond_stop,
    maintenance_margin_rate_for_size,
    max_leverage_for_size,
    per_entry_margin_cap,
    select_leverage_and_locked_margin,
    select_liquidation_safe_leverage_and_locked_margin,
)
from backtester.risk_model import BasicRiskModel, EntryContext


def test_effective_margin_fraction_prefers_finite_position_share() -> None:
    assert effective_margin_fraction(max_allowed_margin=1.0, max_positions=2) == pytest.approx(0.5)
    assert effective_margin_fraction(max_allowed_margin=0.25, max_positions=4) == pytest.approx(
        0.25
    )
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


def test_okx_linear_liquidation_estimate_matches_live_sol_position() -> None:
    liquidation = estimate_linear_liquidation_price(
        entry_price=73.91,
        is_long=True,
        leverage=25.0,
        maintenance_margin_rate=0.004,
        liquidation_fee_rate=0.0005,
    )

    assert liquidation == pytest.approx(71.28433450527373, abs=0.02)


def test_okx_sol_tier_schedule_raises_mmr_after_tier_one() -> None:
    assert maintenance_margin_rate_for_size(
        position_size=5_000.0,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    ) == pytest.approx(0.004)
    assert maintenance_margin_rate_for_size(
        position_size=5_000.01,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    ) == pytest.approx(0.005)
    assert maintenance_margin_rate_for_size(
        position_size=120_000.01,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    ) == pytest.approx(0.0375)


def test_okx_sol_tier_schedule_caps_effective_leverage() -> None:
    assert max_leverage_for_size(
        position_size=80_000.0,
        configured_max_leverage=25.0,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    ) == pytest.approx(25.0)
    assert max_leverage_for_size(
        position_size=100_000.01,
        configured_max_leverage=25.0,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    ) == pytest.approx(22.2222222222)


def test_okx_sol_aggregate_size_can_make_existing_leverage_invalid() -> None:
    assert leverage_is_within_size_tier(
        position_size=100_000.0,
        leverage=25.0,
        configured_max_leverage=25.0,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    )
    assert not leverage_is_within_size_tier(
        position_size=100_000.01,
        leverage=25.0,
        configured_max_leverage=25.0,
        tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    )


def test_aggregate_liquidation_uses_total_size_tier() -> None:
    no_tier = aggregate_liquidation_is_beyond_stops(
        entries_and_stops=[(100.0, 3_000.0, 95.0), (100.0, 3_000.0, 95.0)],
        is_long=True,
        leverage=20.0,
        maintenance_margin_rate=0.004,
    )[1]
    tiered = aggregate_liquidation_is_beyond_stops(
        entries_and_stops=[(100.0, 3_000.0, 95.0), (100.0, 3_000.0, 95.0)],
        is_long=True,
        leverage=20.0,
        maintenance_margin_rate=0.004,
        maintenance_margin_tier_schedule=OKX_SOL_USDT_SWAP_TIER_SCHEDULE,
    )[1]

    assert no_tier is not None and tiered is not None
    assert tiered > no_tier


def test_liquidation_safe_selector_reduces_leverage_below_structural_stop() -> None:
    selected = select_liquidation_safe_leverage_and_locked_margin(
        position_value=30.5,
        per_entry_cap=105.0,
        max_allowed_leverage=25.0,
        entry_price=73.91,
        stop_price=70.9484,
        is_long=True,
        maintenance_margin_rate=0.004,
        liquidation_fee_rate=0.0005,
        liquidation_buffer_pct=0.005,
    )

    assert selected is not None
    leverage, locked_margin, liquidation = selected
    assert leverage == 20.0
    assert locked_margin == pytest.approx(1.525)
    assert liquidation_is_beyond_stop(
        entry_price=73.91,
        stop_price=70.9484,
        liquidation_price=liquidation,
        is_long=True,
        buffer_pct=0.005,
    )


def test_existing_unsafe_leverage_rejects_new_entry() -> None:
    selected = select_liquidation_safe_leverage_and_locked_margin(
        position_value=30.5,
        per_entry_cap=105.0,
        max_allowed_leverage=25.0,
        entry_price=73.91,
        stop_price=70.9484,
        is_long=True,
        existing_leverage=25.0,
    )

    assert selected is None


def test_side_aggregate_liquidation_must_clear_every_stop() -> None:
    safe, liquidation = aggregate_liquidation_is_beyond_stops(
        entries_and_stops=[
            (100.0, 1.0, 95.0),
            (110.0, 1.0, 106.0),
        ],
        is_long=True,
        leverage=20.0,
    )

    assert liquidation is not None
    assert not safe
