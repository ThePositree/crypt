"""Tests for LivePosition dataclass and JSON state persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from crypt.execution.position_state import (
    ExecutionState,
    LivePosition,
    load_state,
    save_state,
)


def _make_position(
    symbol: str = "SOL-USDT-SWAP",
    is_long: bool = False,
) -> LivePosition:
    return LivePosition.create(
        symbol=symbol,
        signal_time=datetime(2026, 6, 9, 14, 0, tzinfo=UTC),
        entry_time=datetime(2026, 6, 9, 15, 0, tzinfo=UTC),
        entry_price=145.30,
        sl_price=143.00,
        tp_price=148.05,
        size=68.97,
        contracts=68,
        leverage=25.0,
        locked_margin=394.85,
        risk_base_capital=10_000.0,
        is_long=is_long,
        ttl_bars=36,
        entry_order_id="test-order-id",
    )


class TestLivePosition:
    def test_create_assigns_uuid(self) -> None:
        pos = _make_position()
        assert len(pos.position_id) == 36  # UUID4

    def test_create_default_status_is_open(self) -> None:
        pos = _make_position()
        assert pos.status == "open"

    def test_entry_dt_parses_isoformat(self) -> None:
        pos = _make_position()
        dt = pos.entry_dt
        assert dt.year == 2026
        assert dt.hour == 15

    def test_signal_dt_parses_isoformat(self) -> None:
        pos = _make_position()
        dt = pos.signal_dt
        assert dt.hour == 14


class TestExecutionState:
    def test_open_positions_for_filters_by_symbol(self) -> None:
        sol = _make_position("SOL-USDT-SWAP")
        ton = _make_position("TON-USDT-SWAP")
        state = ExecutionState(
            schema_version=1,
            risk_window_month=None,
            monthly_risk_base=0.0,
            positions=[sol, ton],
        )
        sol_open = state.open_positions_for("SOL-USDT-SWAP")
        assert len(sol_open) == 1
        assert sol_open[0].symbol == "SOL-USDT-SWAP"

    def test_all_open_positions_excludes_closed(self) -> None:
        open_pos = _make_position()
        closed_pos = _make_position()
        closed_pos.status = "closed"  # type: ignore[misc]
        state = ExecutionState(
            schema_version=1,
            risk_window_month=None,
            monthly_risk_base=0.0,
            positions=[open_pos, closed_pos],
        )
        assert len(state.all_open_positions()) == 1


class TestStatePersistence:
    def test_roundtrip(self, tmp_path: Path) -> None:
        pos = _make_position()
        state = ExecutionState(
            schema_version=1,
            risk_window_month=(2026, 6),
            monthly_risk_base=10_000.0,
            positions=[pos],
            blocked_signal_events_total=7,
        )
        path = tmp_path / "state.json"
        save_state(state, path)

        loaded = load_state(path)
        assert loaded.monthly_risk_base == pytest.approx(10_000.0)
        assert loaded.risk_window_month == (2026, 6)
        assert loaded.blocked_signal_events_total == 7
        assert len(loaded.positions) == 1
        assert loaded.positions[0].symbol == "SOL-USDT-SWAP"
        assert loaded.positions[0].entry_price == pytest.approx(145.30)

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        state = load_state(tmp_path / "missing.json")
        assert state.positions == []
        assert state.monthly_risk_base == 0.0
        assert state.risk_window_month is None

    def test_atomic_write(self, tmp_path: Path) -> None:
        """Save should not leave a .tmp file behind."""
        path = tmp_path / "state.json"
        state = ExecutionState(
            schema_version=1,
            risk_window_month=None,
            monthly_risk_base=0.0,
            positions=[],
        )
        save_state(state, path)
        assert path.exists()
        assert not path.with_suffix(".tmp").exists()

    def test_state_file_is_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        pos = _make_position()
        state = ExecutionState(
            schema_version=1,
            risk_window_month=(2026, 6),
            monthly_risk_base=9_500.0,
            positions=[pos],
        )
        save_state(state, path)
        raw = json.loads(path.read_text())
        assert raw["schema_version"] == 1
        assert len(raw["positions"]) == 1
        assert raw["positions"][0]["symbol"] == "SOL-USDT-SWAP"
