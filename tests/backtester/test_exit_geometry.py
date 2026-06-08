from __future__ import annotations

import pytest

from backtester.exit_geometry import ExitGeometryConfig, resolve_exit_levels
from backtester.risk_model import BasicRiskModel, EntryContext


def test_tp_pct_mode_derives_sl_from_tp_and_rrr():
    config = ExitGeometryConfig(mode="tp_pct", tp_move_pct=0.015)
    resolved = resolve_exit_levels(
        signal=1,
        entry_price=100.0,
        structural_sl_price=90.0,
        rrr=1.25,
        config=config,
    )

    assert resolved is not None
    assert resolved.tp_price == pytest.approx(101.5)
    assert resolved.sl_price == pytest.approx(98.8)
    assert resolved.sl_dist == pytest.approx(1.2)
    assert resolved.effective_rrr == pytest.approx(1.25)
    assert resolved.structural_sl_capped is False


def test_tp_pct_cap_binds_to_structural_sl():
    config = ExitGeometryConfig(mode="tp_pct", tp_move_pct=0.02, structural_sl_mode="cap")
    resolved = resolve_exit_levels(
        signal=1,
        entry_price=100.0,
        structural_sl_price=99.0,
        rrr=1.0,
        config=config,
    )

    assert resolved is not None
    assert resolved.sl_price == pytest.approx(99.0)
    assert resolved.sl_dist == pytest.approx(1.0)
    assert resolved.tp_price == pytest.approx(102.0)
    assert resolved.structural_sl_capped is True
    assert resolved.effective_rrr == pytest.approx(2.0)


def test_tp_pct_reject_skips_when_derived_sl_wider_than_structural():
    config = ExitGeometryConfig(mode="tp_pct", tp_move_pct=0.02, structural_sl_mode="reject")
    resolved = resolve_exit_levels(
        signal=1,
        entry_price=100.0,
        structural_sl_price=99.5,
        rrr=1.0,
        config=config,
    )

    assert resolved is None


def test_basic_risk_model_tp_pct_uses_resolved_prices():
    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        exit_geometry_config=ExitGeometryConfig(mode="tp_pct", tp_move_pct=0.015),
    )
    result = model.calculate_position(
        EntryContext(
            signal=1,
            sl_price=90.0,
            entry_price=100.0,
            capital=1000.0,
            risk_base_capital=1000.0,
            total_locked_margin=0.0,
            open_positions=0,
            risk_percent=1.0,
            rrr=1.25,
        )
    )

    assert result is not None
    assert result.tp_price == pytest.approx(101.5)
    assert result.sl_price == pytest.approx(98.8)
    assert result.size == pytest.approx(1000.0 * 0.01 / 1.2)
