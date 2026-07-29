"""Regression tests for fail-closed live monthly risk-base continuity."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from crypt.execution.position_state import (
    ExecutionState,
    create_monthly_risk_base_checkpoint,
    load_monthly_risk_base_checkpoint,
    load_state,
    save_state,
)
from crypt.execution.risk_base_continuity import (
    MonthlyRiskBaseContinuity,
    RiskBaseContinuityError,
)


def _state(
    *,
    window: tuple[int, int] | None = (2026, 7),
    base: float = 104.77,
) -> ExecutionState:
    return ExecutionState(
        schema_version=12,
        risk_window_month=window,
        monthly_risk_base=base,
        positions=[],
    )


def _guard(
    tmp_path: Path,
    *,
    allow_adoption: bool = False,
    expected_month: str | None = None,
    expected_base: float | None = None,
) -> MonthlyRiskBaseContinuity:
    return MonthlyRiskBaseContinuity(
        checkpoint_dir=tmp_path / "checkpoints",
        state_path=tmp_path / "live_positions.json",
        allow_adopt_existing_state=allow_adoption,
        adopt_expected_month=expected_month,
        adopt_expected_base=expected_base,
    )


def _checkpoint(tmp_path: Path, *, base: float = 104.77) -> None:
    create_monthly_risk_base_checkpoint(
        tmp_path / "checkpoints",
        risk_window_month=(2026, 7),
        monthly_risk_base=base,
        source="test",
        state_path=tmp_path / "live_positions.json",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )


def test_missing_state_recovers_same_month_anchor_from_checkpoint(tmp_path: Path) -> None:
    _checkpoint(tmp_path)
    state = _state(window=None, base=0.0)

    resolution = _guard(tmp_path).verify_startup(
        state,
        now=datetime(2026, 7, 15, tzinfo=UTC),
        exchange_sync_ok=True,
    )

    assert resolution.action == "recovered"
    assert resolution.risk_base == pytest.approx(104.77)
    assert state.risk_window_month == (2026, 7)
    assert state.monthly_risk_base == pytest.approx(104.77)


def test_same_month_state_checkpoint_conflict_fails_closed(tmp_path: Path) -> None:
    _checkpoint(tmp_path, base=104.77)

    with pytest.raises(RiskBaseContinuityError, match="disagree"):
        _guard(tmp_path).verify_startup(
            _state(base=102.34),
            now=datetime(2026, 7, 15, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_current_month_state_without_checkpoint_needs_explicit_adoption(tmp_path: Path) -> None:
    with pytest.raises(RiskBaseContinuityError, match="explicit adoption"):
        _guard(tmp_path).verify_startup(
            _state(),
            now=datetime(2026, 7, 15, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_explicit_adoption_records_current_state_without_rewriting_base(tmp_path: Path) -> None:
    state = _state(base=102.3381502678064)

    resolution = _guard(
        tmp_path,
        allow_adoption=True,
        expected_month="2026-07",
        expected_base=102.3381502678064,
    ).verify_startup(
        state,
        now=datetime(2026, 7, 28, tzinfo=UTC),
        exchange_sync_ok=True,
    )

    checkpoint = load_monthly_risk_base_checkpoint(tmp_path / "checkpoints", (2026, 7))
    assert resolution.action == "adopted"
    assert state.monthly_risk_base == pytest.approx(102.3381502678064)
    assert checkpoint is not None
    assert checkpoint.monthly_risk_base == pytest.approx(102.3381502678064)
    assert checkpoint.source == "operator_adopted_existing_state"


def test_adoption_requires_clean_exchange_sync(tmp_path: Path) -> None:
    with pytest.raises(RiskBaseContinuityError, match="sync is blocked"):
        _guard(
            tmp_path,
            allow_adoption=True,
            expected_month="2026-07",
            expected_base=104.77,
        ).verify_startup(
            _state(),
            now=datetime(2026, 7, 28, tzinfo=UTC),
            exchange_sync_ok=False,
        )


def test_verified_previous_month_creates_next_month_anchor_only_at_rollover_entry(
    tmp_path: Path,
) -> None:
    _checkpoint(tmp_path)
    state = _state()

    resolution = _guard(tmp_path).resolve_for_entry(
        state,
        entry_time=datetime(2026, 8, 1, 1, tzinfo=UTC),
        current_capital=101.48,
        exchange_sync_ok=True,
    )

    august = load_monthly_risk_base_checkpoint(tmp_path / "checkpoints", (2026, 8))
    assert resolution.action == "rolled_over"
    assert state.risk_window_month == (2026, 8)
    assert state.monthly_risk_base == pytest.approx(101.48)
    assert august is not None
    assert august.monthly_risk_base == pytest.approx(101.48)


def test_empty_state_without_checkpoint_never_uses_current_balance(tmp_path: Path) -> None:
    with pytest.raises(RiskBaseContinuityError, match="refusing to re-anchor"):
        _guard(tmp_path).resolve_for_entry(
            _state(window=None, base=0.0),
            entry_time=datetime(2026, 7, 15, tzinfo=UTC),
            current_capital=102.34,
            exchange_sync_ok=True,
        )


def test_adoption_requires_an_exact_operator_manifest(tmp_path: Path) -> None:
    with pytest.raises(
        RiskBaseContinuityError, match="explicit expected month and exact risk base"
    ):
        _guard(tmp_path, allow_adoption=True).verify_startup(
            _state(),
            now=datetime(2026, 7, 28, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_adoption_refuses_a_previous_state_snapshot(tmp_path: Path) -> None:
    state = _state(base=102.3381502678064)
    state.state_recovered_from_previous_snapshot = True

    with pytest.raises(RiskBaseContinuityError, match="previous mutable state snapshot"):
        _guard(
            tmp_path,
            allow_adoption=True,
            expected_month="2026-07",
            expected_base=102.3381502678064,
        ).verify_startup(
            state,
            now=datetime(2026, 7, 28, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_recovered_snapshot_taint_survives_save_and_restart_before_adoption(
    tmp_path: Path,
) -> None:
    path = tmp_path / "live_positions.json"
    state = _state(base=102.3381502678064)
    save_state(state, path)
    state.monthly_risk_base = 99.0
    save_state(state, path)
    path.unlink()

    recovered = load_state(path)
    assert recovered.state_recovered_from_previous_snapshot
    guard = _guard(
        tmp_path,
        allow_adoption=True,
        expected_month="2026-07",
        expected_base=102.3381502678064,
    )
    with pytest.raises(RiskBaseContinuityError, match="previous mutable state snapshot"):
        guard.verify_startup(
            recovered,
            now=datetime(2026, 7, 28, tzinfo=UTC),
            exchange_sync_ok=True,
        )
    save_state(recovered, path)
    reloaded = load_state(path)
    assert reloaded.state_recovered_from_previous_snapshot

    with pytest.raises(RiskBaseContinuityError, match="previous mutable state snapshot"):
        guard.verify_startup(
            reloaded,
            now=datetime(2026, 7, 28, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_checkpoint_with_a_different_state_path_fails_closed(tmp_path: Path) -> None:
    create_monthly_risk_base_checkpoint(
        tmp_path / "checkpoints",
        risk_window_month=(2026, 7),
        monthly_risk_base=104.77,
        source="test",
        state_path=tmp_path / "other_live_positions.json",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    with pytest.raises(RiskBaseContinuityError, match="different state path"):
        _guard(tmp_path).verify_startup(
            _state(window=None, base=0.0),
            now=datetime(2026, 7, 15, tzinfo=UTC),
            exchange_sync_ok=True,
        )


def test_rollover_requires_clean_exchange_sync_even_when_an_entry_is_requested(
    tmp_path: Path,
) -> None:
    _checkpoint(tmp_path)

    with pytest.raises(RiskBaseContinuityError, match="exchange sync is blocked"):
        _guard(tmp_path).resolve_for_entry(
            _state(),
            entry_time=datetime(2026, 8, 1, 1, tzinfo=UTC),
            current_capital=101.48,
            exchange_sync_ok=False,
        )
