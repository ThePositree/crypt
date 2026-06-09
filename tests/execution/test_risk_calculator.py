"""Tests for LiveRiskCalculator — verifies parity with BasicRiskModel.

Uses the same synthetic data pattern as the backtester engine tests:
construct a minimal scenario, run the calculator, assert the result
matches what ExecutionSim would produce for the same inputs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backtester.risk_model import BasicRiskModel, EntryContext
from crypt.execution.position_state import ExecutionState, LivePosition
from crypt.execution.risk_calculator import LiveRiskCalculator
from crypt.execution.settings import ExecutionSettings


def _settings(**overrides: object) -> ExecutionSettings:
    defaults: dict[str, object] = {
        "exit_geometry": "tp_pct",
        "tp_move_pct": 0.016,
        "rrr": 2.5,
        "ttl_bars": 36,
        "risk_percent": 1.5,
        "max_positions": 1,
        "max_leverage": 25.0,
        "risk_base_period": "monthly",
        "taker_fee": 0.0005,
        "maker_fee": 0.0002,
        "max_allowed_margin": 1.0,
        "min_net_exposure": 0.01,
        "max_capital_risk_pct": 10.0,
        "enabled": False,
        "dry_run": True,
        "strategy_config": "strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json",
        "data_dir": "data",
        "state_path": "data/live_positions.json",
    }
    defaults.update(overrides)
    return ExecutionSettings.model_validate(defaults)


def _empty_state() -> ExecutionState:
    return ExecutionState(
        schema_version=1,
        risk_window_month=None,
        monthly_risk_base=0.0,
        positions=[],
    )


class TestMonthlyRiskBase:
    def test_first_call_sets_monthly_base(self) -> None:
        calc = LiveRiskCalculator(_settings())
        state = _empty_state()
        entry_time = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
        base = calc.update_monthly_risk_base(state, entry_time, 10_000.0)
        assert base == pytest.approx(10_000.0)
        assert state.monthly_risk_base == pytest.approx(10_000.0)
        assert state.risk_window_month == (2026, 6)

    def test_second_call_same_month_reuses_base(self) -> None:
        calc = LiveRiskCalculator(_settings())
        state = _empty_state()
        t1 = datetime(2026, 6, 1, tzinfo=UTC)
        t2 = datetime(2026, 6, 15, tzinfo=UTC)
        calc.update_monthly_risk_base(state, t1, 10_000.0)
        base = calc.update_monthly_risk_base(state, t2, 12_000.0)
        # Capital grew, but base stays at start-of-month
        assert base == pytest.approx(10_000.0)

    def test_new_month_updates_base(self) -> None:
        calc = LiveRiskCalculator(_settings())
        state = _empty_state()
        t_june = datetime(2026, 6, 30, 23, 0, tzinfo=UTC)
        t_july = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
        calc.update_monthly_risk_base(state, t_june, 10_000.0)
        base = calc.update_monthly_risk_base(state, t_july, 11_500.0)
        assert base == pytest.approx(11_500.0)
        assert state.risk_window_month == (2026, 7)


class TestCalculate:
    def _calc_parity(
        self,
        *,
        signal: int,
        sl_price: float,
        entry_price: float,
        capital: float = 10_000.0,
    ) -> None:
        """Assert that LiveRiskCalculator agrees with BasicRiskModel on sizing."""
        from backtester.exit_geometry import exit_geometry_config_from_args

        settings = _settings()
        calc = LiveRiskCalculator(settings)

        egc = exit_geometry_config_from_args(
            exit_geometry="tp_pct",
            tp_move_pct=0.016,
            structural_sl_mode="cap",
        )
        ref_model = BasicRiskModel(
            max_allowed_margin=1.0,
            max_positions=1,
            max_allowed_leverage=25.0,
            exit_geometry_config=egc,
        )
        ref_ctx = EntryContext(
            signal=signal,
            sl_price=sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=capital,
            total_locked_margin=0.0,
            open_positions=0,
            risk_percent=1.5,
            rrr=2.5,
        )
        ref = ref_model.calculate_position(ref_ctx)
        assert ref is not None, "Reference model should not reject this trade"

        decision = calc.calculate(
            signal=signal,
            sl_price=sl_price,
            entry_price=entry_price,
            capital=capital,
            risk_base_capital=capital,
            open_positions=[],
        )
        assert decision is not None, "LiveRiskCalculator should not reject this trade"

        rr = decision.risk_result
        assert rr.size == pytest.approx(ref.size, rel=1e-6)
        assert rr.position_value == pytest.approx(ref.position_value, rel=1e-6)
        assert rr.sl_price == pytest.approx(ref.sl_price, rel=1e-6)
        assert rr.tp_price == pytest.approx(ref.tp_price, rel=1e-6)
        assert rr.required_leverage == pytest.approx(ref.required_leverage, rel=1e-6)

    def test_short_position_matches_reference(self) -> None:
        self._calc_parity(
            signal=-1,
            sl_price=148.0,
            entry_price=145.0,
            capital=10_000.0,
        )

    def test_long_position_matches_reference(self) -> None:
        self._calc_parity(
            signal=1,
            sl_price=142.0,
            entry_price=145.0,
            capital=10_000.0,
        )

    def test_max_positions_guard_rejects(self) -> None:
        calc = LiveRiskCalculator(_settings(max_positions=1))
        existing = [
            LivePosition.create(
                symbol="SOL-USDT-SWAP",
                signal_time=datetime(2026, 6, 1, tzinfo=UTC),
                entry_time=datetime(2026, 6, 1, 1, tzinfo=UTC),
                entry_price=145.0,
                sl_price=143.0,
                tp_price=148.0,
                size=10.0,
                contracts=10,
                leverage=25.0,
                locked_margin=58.0,
                risk_base_capital=10_000.0,
                is_long=False,
                ttl_bars=36,
                entry_order_id=None,
            )
        ]
        decision = calc.calculate(
            signal=-1,
            sl_price=148.0,
            entry_price=145.0,
            capital=10_000.0,
            risk_base_capital=10_000.0,
            open_positions=existing,
        )
        assert decision is None

    def test_neutral_signal_returns_none(self) -> None:
        calc = LiveRiskCalculator(_settings())
        decision = calc.calculate(
            signal=0,
            sl_price=143.0,
            entry_price=145.0,
            capital=10_000.0,
            risk_base_capital=10_000.0,
            open_positions=[],
        )
        assert decision is None
