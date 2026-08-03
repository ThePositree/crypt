"""Tests for LivePosition dataclass and JSON state persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from crypt.execution.position_state import (
    ExecutionState,
    LivePosition,
    RiskBaseCheckpointError,
    create_monthly_risk_base_checkpoint,
    load_monthly_risk_base_checkpoint,
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
        closed_pos.status = "closed"
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
            blocked_signal_event_ids=["event-1"],
        )
        path = tmp_path / "state.json"
        save_state(state, path)

        loaded = load_state(path)
        assert loaded.schema_version == 13
        assert loaded.monthly_risk_base == pytest.approx(10_000.0)
        assert loaded.risk_window_month == (2026, 6)
        assert loaded.blocked_signal_events_total == 7
        assert loaded.blocked_signal_event_ids == ["event-1"]
        assert len(loaded.positions) == 1
        assert loaded.positions[0].symbol == "SOL-USDT-SWAP"
        assert loaded.positions[0].entry_price == pytest.approx(145.30)
        assert loaded.generation == 1

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
        assert raw["schema_version"] == 13
        assert isinstance(raw["state_checksum"], str)
        assert len(raw["positions"]) == 1
        assert raw["positions"][0]["symbol"] == "SOL-USDT-SWAP"

    def test_missing_primary_loads_previous_valid_snapshot(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = ExecutionState(
            schema_version=10,
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            positions=[],
        )
        save_state(state, path)
        state.monthly_risk_base = 102.34
        save_state(state, path)

        path.unlink()

        loaded = load_state(path)
        assert loaded.monthly_risk_base == pytest.approx(104.77)
        assert loaded.generation == 1
        assert loaded.state_recovered_from_previous_snapshot
        assert json.loads(path.read_text(encoding="utf-8"))[
            "state_recovered_from_previous_snapshot"
        ]
        save_state(loaded, path)
        assert load_state(path).state_recovered_from_previous_snapshot

    def test_corrupt_primary_is_restored_from_previous_valid_snapshot(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = ExecutionState(
            schema_version=10,
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            positions=[],
        )
        save_state(state, path)
        state.monthly_risk_base = 102.34
        save_state(state, path)
        path.write_text("not valid json", encoding="utf-8")

        loaded = load_state(path)
        assert loaded.monthly_risk_base == pytest.approx(104.77)
        assert json.loads(path.read_text(encoding="utf-8"))["monthly_risk_base"] == pytest.approx(
            104.77
        )


class TestMonthlyRiskBaseCheckpoints:
    def test_checkpoint_roundtrip_creates_primary_and_backup(self, tmp_path: Path) -> None:
        checkpoint = create_monthly_risk_base_checkpoint(
            tmp_path / "checkpoints",
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            source="test",
            state_path=tmp_path / "state.json",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )

        loaded = load_monthly_risk_base_checkpoint(tmp_path / "checkpoints", (2026, 7))

        assert loaded == checkpoint
        assert (tmp_path / "checkpoints" / "2026-07.json").exists()
        assert (tmp_path / "checkpoints" / "2026-07.backup.json").exists()

    def test_checkpoint_refuses_a_different_same_month_anchor(self, tmp_path: Path) -> None:
        directory = tmp_path / "checkpoints"
        create_monthly_risk_base_checkpoint(
            directory,
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            source="test",
            state_path=tmp_path / "state.json",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )

        with pytest.raises(RiskBaseCheckpointError, match="different anchor"):
            create_monthly_risk_base_checkpoint(
                directory,
                risk_window_month=(2026, 7),
                monthly_risk_base=102.34,
                source="test",
                state_path=tmp_path / "state.json",
                created_at=datetime(2026, 7, 2, tzinfo=UTC),
            )

    @pytest.mark.parametrize("missing_name", ["2026-07.json", "2026-07.backup.json"])
    def test_checkpoint_requires_both_primary_and_backup(
        self,
        tmp_path: Path,
        missing_name: str,
    ) -> None:
        directory = tmp_path / "checkpoints"
        create_monthly_risk_base_checkpoint(
            directory,
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            source="test",
            state_path=tmp_path / "state.json",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        (directory / missing_name).unlink()

        with pytest.raises(RiskBaseCheckpointError, match="primary and backup"):
            load_monthly_risk_base_checkpoint(directory, (2026, 7))

    def test_checkpoint_refuses_non_finite_risk_base(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="finite and positive"):
            create_monthly_risk_base_checkpoint(
                tmp_path / "checkpoints",
                risk_window_month=(2026, 7),
                monthly_risk_base=float("nan"),
                source="test",
                state_path=tmp_path / "state.json",
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
            )

    def test_checkpoint_refuses_nonidentical_primary_and_backup_bytes(self, tmp_path: Path) -> None:
        directory = tmp_path / "checkpoints"
        create_monthly_risk_base_checkpoint(
            directory,
            risk_window_month=(2026, 7),
            monthly_risk_base=104.77,
            source="test",
            state_path=tmp_path / "state.json",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        backup_path = directory / "2026-07.backup.json"
        backup_path.write_text(backup_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        with pytest.raises(RiskBaseCheckpointError, match="primary and backup disagree"):
            load_monthly_risk_base_checkpoint(directory, (2026, 7))

    def test_future_state_schema_fails_closed(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 999,
                    "risk_window_month": None,
                    "monthly_risk_base": 0.0,
                    "positions": [],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="newer than supported"):
            load_state(path)
