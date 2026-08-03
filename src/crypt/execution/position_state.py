"""Live position state plus durable monthly risk-base persistence.

The mutable state file tracks position lifecycle. Immutable per-month checkpoint
files preserve the economic risk anchor independently of that mutable snapshot.

Schema version bumps must preserve backward compatibility or provide a
migration in `_migrate_state`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

_SCHEMA_VERSION = 13
_RISK_BASE_CHECKPOINT_SCHEMA_VERSION = 1


@dataclass
class LivePosition:
    """One open position tracked by the live execution module."""

    position_id: str
    symbol: str
    signal_time: str  # ISO-8601 UTC
    entry_time: str  # ISO-8601 UTC
    entry_price: float
    sl_price: float
    tp_price: float
    size: float  # base asset units (e.g. SOL)
    contracts: float  # OKX contract count, rounded to exchange lot size
    leverage: float
    locked_margin: float
    risk_base_capital: float
    is_long: bool
    ttl_bars: int
    entry_order_id: str | None
    status: Literal["open", "closing", "closed"]
    entry_state: Literal[
        "entry_intent",
        "entry_submitted",
        "entry_filled",
        "protected",
        "entry_aborted",
    ] = "protected"
    aggregate_entry_price: float | None = None
    event_id: str = ""
    client_order_id: str = ""
    algo_client_order_id: str = ""
    close_client_order_id: str = ""
    stop_algo_order_id: str = ""
    take_profit_order_id: str = ""
    trailing_algo_client_order_id: str = ""
    trailing_algo_order_id: str = ""
    selected_strategy: str = ""
    position_group: str = ""
    signal_event: dict[str, object] = field(default_factory=dict)
    liquidation_price: float | None = None
    maintenance_margin_rate: float = 0.004
    liquidation_fee_rate: float = 0.0005
    liquidation_buffer_pct: float = 0.005
    maintenance_margin_tier_schedule: str | None = None
    entry_fee: float = 0.0
    trail_activation_rrr: float = 0.0
    trail_distance_atr: float = 0.0
    trail_activation_price: float | None = None
    trail_callback_spread: float | None = None
    fixed_take_profit_enabled: bool = True
    trail_active: bool = False
    trail_stop_price: float | None = None
    best_favorable_price: float | None = None
    last_sync_status: str = "unknown"
    last_sync_at: str | None = None
    exit_time: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    constituent_realized_pnl: float | None = None
    exit_fee: float | None = None
    close_filled_contracts: float = 0.0
    close_fill_notional: float = 0.0
    close_fee_accum: float = 0.0
    close_attempt: int = 0
    close_order_ids: list[str] = field(default_factory=list)

    @property
    def entry_dt(self) -> datetime:
        return datetime.fromisoformat(self.entry_time)

    @property
    def signal_dt(self) -> datetime:
        return datetime.fromisoformat(self.signal_time)

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        signal_time: datetime,
        entry_time: datetime,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        size: float,
        contracts: float,
        leverage: float,
        locked_margin: float,
        risk_base_capital: float,
        is_long: bool,
        ttl_bars: int,
        entry_order_id: str | None,
        selected_strategy: str = "",
        position_group: str = "",
        signal_event: dict[str, object] | None = None,
        trail_activation_rrr: float = 0.0,
        trail_distance_atr: float = 0.0,
        liquidation_price: float | None = None,
        maintenance_margin_rate: float = 0.004,
        liquidation_fee_rate: float = 0.0005,
        liquidation_buffer_pct: float = 0.005,
        maintenance_margin_tier_schedule: str | None = None,
        event_id: str = "",
        client_order_id: str = "",
        algo_client_order_id: str = "",
        entry_fee: float = 0.0,
        trailing_algo_client_order_id: str = "",
        trail_activation_price: float | None = None,
        trail_callback_spread: float | None = None,
        fixed_take_profit_enabled: bool = True,
    ) -> LivePosition:
        return cls(
            position_id=str(uuid.uuid4()),
            symbol=symbol,
            signal_time=signal_time.isoformat(),
            entry_time=entry_time.isoformat(),
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            size=size,
            contracts=contracts,
            leverage=leverage,
            locked_margin=locked_margin,
            risk_base_capital=risk_base_capital,
            is_long=is_long,
            ttl_bars=ttl_bars,
            entry_order_id=entry_order_id,
            status="open",
            entry_state="entry_intent" if entry_order_id is None else "protected",
            aggregate_entry_price=entry_price,
            event_id=event_id
            or build_event_id(
                symbol=symbol,
                signal_time=signal_time,
                selected_strategy=selected_strategy,
                is_long=is_long,
            ),
            client_order_id=client_order_id,
            algo_client_order_id=algo_client_order_id,
            entry_fee=entry_fee,
            trailing_algo_client_order_id=trailing_algo_client_order_id,
            trail_activation_price=trail_activation_price,
            trail_callback_spread=trail_callback_spread,
            fixed_take_profit_enabled=fixed_take_profit_enabled,
            selected_strategy=selected_strategy,
            position_group=position_group,
            signal_event=signal_event or {},
            liquidation_price=liquidation_price,
            maintenance_margin_rate=maintenance_margin_rate,
            liquidation_fee_rate=liquidation_fee_rate,
            liquidation_buffer_pct=liquidation_buffer_pct,
            maintenance_margin_tier_schedule=maintenance_margin_tier_schedule,
            trail_activation_rrr=trail_activation_rrr,
            trail_distance_atr=trail_distance_atr,
        )


@dataclass
class ExecutionState:
    """Full persistent state of the execution module."""

    schema_version: int
    risk_window_month: tuple[int, int] | None  # (year, month)
    monthly_risk_base: float
    positions: list[LivePosition]
    last_exchange_sync_at: str | None = None
    last_exchange_sync_ok: bool = False
    last_exchange_sync_errors: list[str] = field(default_factory=list)
    last_daily_sync_report_date: str | None = None
    blocked_signal_events_total: int = 0
    blocked_signal_event_ids: list[str] = field(default_factory=list)
    risk_base_continuity_status: str = "unknown"
    risk_base_continuity_error: str | None = None
    generation: int = 0
    state_recovered_from_previous_snapshot: bool = field(default=False, repr=False)

    def open_positions_for(self, symbol: str) -> list[LivePosition]:
        return [p for p in self.positions if p.symbol == symbol and p.status != "closed"]

    def all_open_positions(self) -> list[LivePosition]:
        return [p for p in self.positions if p.status != "closed"]


class RiskBaseCheckpointError(RuntimeError):
    """Raised when an immutable monthly risk checkpoint is invalid or conflicts."""


@dataclass(frozen=True)
class MonthlyRiskBaseCheckpoint:
    """One immutable monthly anchor used for live risk sizing."""

    schema_version: int
    risk_window_month: tuple[int, int]
    monthly_risk_base: float
    created_at: str
    source: str
    state_path: str

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "risk_window_month": list(self.risk_window_month),
            "monthly_risk_base": self.monthly_risk_base,
            "created_at": self.created_at,
            "source": self.source,
            "state_path": self.state_path,
        }
        payload["checkpoint_checksum"] = _payload_checksum(payload)
        return payload


def monthly_risk_base_checkpoint_path(
    checkpoint_dir: Path,
    risk_window_month: tuple[int, int],
    *,
    backup: bool = False,
) -> Path:
    """Return the immutable primary or backup path for one UTC month."""
    year, month = risk_window_month
    if not 1 <= month <= 12:
        raise ValueError(f"risk window month must be 1..12, got {risk_window_month!r}")
    suffix = ".backup.json" if backup else ".json"
    return checkpoint_dir / f"{year:04d}-{month:02d}{suffix}"


def load_monthly_risk_base_checkpoint(
    checkpoint_dir: Path,
    risk_window_month: tuple[int, int],
) -> MonthlyRiskBaseCheckpoint | None:
    """Load and cross-check a primary/backup immutable monthly anchor."""
    paths = (
        monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month),
        monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month, backup=True),
    )
    records: list[MonthlyRiskBaseCheckpoint] = []
    errors: list[str] = []
    missing: list[str] = []
    for path in paths:
        if not path.exists():
            missing.append(path.name)
            continue
        try:
            records.append(_load_checkpoint(path, expected_window=risk_window_month))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")

    if not records:
        if errors:
            raise RiskBaseCheckpointError(
                "monthly risk-base checkpoint is unreadable: " + "; ".join(errors)
            )
        return None
    if errors or missing or len(records) != len(paths):
        details = [*errors]
        if missing:
            details.append("missing " + ", ".join(missing))
        raise RiskBaseCheckpointError(
            "monthly risk-base checkpoint requires matching primary and backup copies: "
            + "; ".join(details)
        )
    try:
        copies_match = paths[0].read_bytes() == paths[1].read_bytes()
    except OSError as exc:
        raise RiskBaseCheckpointError(
            f"monthly risk-base checkpoint copies cannot be re-read for comparison: {exc}"
        ) from exc
    if records[0] != records[1] or not copies_match:
        raise RiskBaseCheckpointError(
            "monthly risk-base checkpoint primary and backup disagree for "
            f"{risk_window_month[0]:04d}-{risk_window_month[1]:02d}"
        )
    return records[0]


def create_monthly_risk_base_checkpoint(
    checkpoint_dir: Path,
    *,
    risk_window_month: tuple[int, int],
    monthly_risk_base: float,
    source: str,
    state_path: Path,
    created_at: datetime | None = None,
) -> MonthlyRiskBaseCheckpoint:
    """Create an immutable primary and backup checkpoint, or verify an existing one."""
    if not math.isfinite(monthly_risk_base) or monthly_risk_base <= 0:
        raise ValueError("monthly risk-base checkpoint must be finite and positive")
    existing = load_monthly_risk_base_checkpoint(checkpoint_dir, risk_window_month)
    if existing is not None:
        if abs(existing.monthly_risk_base - monthly_risk_base) > 1e-9 or existing.state_path != str(
            state_path
        ):
            raise RiskBaseCheckpointError(
                "refusing to replace existing monthly risk checkpoint with a different anchor"
            )
        payload = existing.to_payload()
        _write_immutable_json(
            monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month),
            payload,
        )
        _write_immutable_json(
            monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month, backup=True),
            payload,
        )
        return existing
    checkpoint = MonthlyRiskBaseCheckpoint(
        schema_version=_RISK_BASE_CHECKPOINT_SCHEMA_VERSION,
        risk_window_month=risk_window_month,
        monthly_risk_base=float(monthly_risk_base),
        created_at=(created_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        source=source,
        state_path=str(state_path),
    )
    payload = checkpoint.to_payload()
    _write_immutable_json(
        monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month),
        payload,
    )
    _write_immutable_json(
        monthly_risk_base_checkpoint_path(checkpoint_dir, risk_window_month, backup=True),
        payload,
    )
    return checkpoint


def load_state(path: Path) -> ExecutionState:
    """Load state, falling back to the prior valid snapshot when needed."""
    primary_error: Exception | None = None
    raw: dict[str, Any] | None = None
    recovered_from_previous_snapshot = False
    if path.exists():
        try:
            raw = _load_state_payload(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            primary_error = exc

    backup_path = _previous_state_path(path)
    if raw is None and backup_path.exists():
        try:
            raw = _load_state_payload(backup_path)
            recovered_from_previous_snapshot = True
            raw["state_recovered_from_previous_snapshot"] = True
            if "state_checksum" in raw:
                raw["state_checksum"] = _payload_checksum(raw)
            _write_json_atomically(path, json.dumps(raw, indent=2, sort_keys=True))
        except (OSError, ValueError, json.JSONDecodeError) as backup_error:
            if primary_error is not None:
                raise RuntimeError(
                    "execution state and previous snapshot are unreadable: "
                    f"primary={primary_error}; backup={backup_error}"
                ) from backup_error
            raise
    if raw is None:
        if primary_error is not None:
            raise RuntimeError(f"execution state is unreadable: {primary_error}") from primary_error
        return _empty_state()

    raw = _migrate_state(raw)

    risk_window = raw.get("risk_window_month")
    positions = [LivePosition(**p) for p in raw.get("positions", [])]

    blocked_signal_event_ids_raw = raw.get("blocked_signal_event_ids", [])
    blocked_signal_event_ids = (
        [str(item) for item in blocked_signal_event_ids_raw]
        if isinstance(blocked_signal_event_ids_raw, list)
        else []
    )

    return ExecutionState(
        schema_version=raw.get("schema_version", _SCHEMA_VERSION),
        risk_window_month=(int(risk_window[0]), int(risk_window[1])) if risk_window else None,
        monthly_risk_base=float(raw.get("monthly_risk_base", 0.0)),
        positions=positions,
        last_exchange_sync_at=raw.get("last_exchange_sync_at"),
        last_exchange_sync_ok=bool(raw.get("last_exchange_sync_ok", False)),
        last_exchange_sync_errors=[str(item) for item in raw.get("last_exchange_sync_errors", [])],
        last_daily_sync_report_date=raw.get("last_daily_sync_report_date"),
        blocked_signal_events_total=int(raw.get("blocked_signal_events_total", 0)),
        blocked_signal_event_ids=blocked_signal_event_ids,
        risk_base_continuity_status=str(raw.get("risk_base_continuity_status", "unknown")),
        risk_base_continuity_error=(
            str(raw["risk_base_continuity_error"])
            if raw.get("risk_base_continuity_error") is not None
            else None
        ),
        generation=int(raw.get("generation", 0)),
        state_recovered_from_previous_snapshot=(
            bool(raw.get("state_recovered_from_previous_snapshot", False))
            or recovered_from_previous_snapshot
        ),
    )


def save_state(state: ExecutionState, path: Path) -> None:
    """Durably replace state and retain one validated previous snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _load_state_payload(path)
        _write_json_atomically(_previous_state_path(path), path.read_text(encoding="utf-8"))

    state.schema_version = _SCHEMA_VERSION
    state.generation += 1

    payload: dict[str, object] = {
        "schema_version": state.schema_version,
        "generation": state.generation,
        "risk_window_month": list(state.risk_window_month) if state.risk_window_month else None,
        "monthly_risk_base": state.monthly_risk_base,
        "last_exchange_sync_at": state.last_exchange_sync_at,
        "last_exchange_sync_ok": state.last_exchange_sync_ok,
        "last_exchange_sync_errors": state.last_exchange_sync_errors,
        "last_daily_sync_report_date": state.last_daily_sync_report_date,
        "blocked_signal_events_total": state.blocked_signal_events_total,
        "blocked_signal_event_ids": state.blocked_signal_event_ids,
        "risk_base_continuity_status": state.risk_base_continuity_status,
        "risk_base_continuity_error": state.risk_base_continuity_error,
        "state_recovered_from_previous_snapshot": state.state_recovered_from_previous_snapshot,
        "saved_at": datetime.now(UTC).isoformat(),
        "positions": [asdict(p) for p in state.positions],
    }
    payload["state_checksum"] = _payload_checksum(payload)
    _write_json_atomically(path, json.dumps(payload, indent=2, sort_keys=True))


def _migrate_state(raw: dict[str, Any]) -> dict[str, Any]:
    """Upgrade old schema versions to the current one in-place."""
    try:
        version = int(raw.get("schema_version", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid execution state schema {raw.get('schema_version')!r}") from exc
    if version == _SCHEMA_VERSION:
        return raw
    if version < _SCHEMA_VERSION:
        raw["schema_version"] = _SCHEMA_VERSION
        raw.setdefault("last_exchange_sync_at", None)
        raw.setdefault("last_exchange_sync_ok", False)
        raw.setdefault("last_exchange_sync_errors", [])
        raw.setdefault("last_daily_sync_report_date", None)
        raw.setdefault("blocked_signal_events_total", 0)
        raw.setdefault("blocked_signal_event_ids", [])
        raw.setdefault("risk_base_continuity_status", "unknown")
        raw.setdefault("risk_base_continuity_error", None)
        raw.setdefault("generation", 0)
        raw.setdefault("state_recovered_from_previous_snapshot", False)
        for pos in raw.get("positions", []):
            if version < 13 and "ttl_bars" in pos:
                pos["ttl_bars"] = int(pos["ttl_bars"]) * 60
            pos.setdefault("selected_strategy", "")
            pos.setdefault("position_group", "")
            pos.setdefault("signal_event", {})
            pos.setdefault("liquidation_price", None)
            pos.setdefault("maintenance_margin_rate", 0.004)
            pos.setdefault("liquidation_fee_rate", 0.0005)
            pos.setdefault("liquidation_buffer_pct", 0.005)
            pos.setdefault("maintenance_margin_tier_schedule", None)
            pos.setdefault("trail_activation_rrr", 0.0)
            pos.setdefault("trail_distance_atr", 0.0)
            pos.setdefault("trail_active", False)
            pos.setdefault("trail_stop_price", None)
            pos.setdefault("best_favorable_price", None)
            pos.setdefault("last_sync_status", "unknown")
            pos.setdefault("last_sync_at", None)
            pos.setdefault("exit_time", None)
            pos.setdefault("exit_price", None)
            pos.setdefault("exit_reason", None)
            pos.setdefault("realized_pnl", None)
            pos.setdefault("constituent_realized_pnl", None)
            pos.setdefault("exit_fee", None)
            signal_time = datetime.fromisoformat(str(pos["signal_time"]))
            pos.setdefault(
                "event_id",
                build_event_id(
                    symbol=str(pos["symbol"]),
                    signal_time=signal_time,
                    selected_strategy=str(pos.get("selected_strategy", "")),
                    is_long=bool(pos["is_long"]),
                ),
            )
            pos.setdefault("client_order_id", "")
            pos.setdefault("algo_client_order_id", "")
            pos.setdefault("close_client_order_id", "")
            pos.setdefault("stop_algo_order_id", "")
            pos.setdefault("take_profit_order_id", "")
            pos.setdefault("trailing_algo_client_order_id", "")
            pos.setdefault("trailing_algo_order_id", "")
            pos.setdefault("entry_fee", 0.0)
            pos.setdefault("aggregate_entry_price", pos.get("entry_price"))
            pos.setdefault("trail_activation_price", None)
            pos.setdefault("trail_callback_spread", None)
            pos.setdefault("fixed_take_profit_enabled", True)
            pos.setdefault(
                "entry_state",
                "protected" if pos.get("entry_order_id") else "entry_intent",
            )
            pos.setdefault("close_filled_contracts", 0.0)
            pos.setdefault("close_fill_notional", 0.0)
            pos.setdefault("close_fee_accum", 0.0)
            pos.setdefault("close_attempt", 0)
            pos.setdefault("close_order_ids", [])
        return raw
    raise ValueError(f"execution state schema {version} is newer than supported {_SCHEMA_VERSION}")


def _empty_state() -> ExecutionState:
    return ExecutionState(
        schema_version=_SCHEMA_VERSION,
        risk_window_month=None,
        monthly_risk_base=0.0,
        positions=[],
        last_exchange_sync_at=None,
        last_exchange_sync_ok=False,
        last_exchange_sync_errors=[],
        last_daily_sync_report_date=None,
        blocked_signal_events_total=0,
    )


def _previous_state_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.previous{path.suffix}")


def _load_state_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("state JSON root must be an object")
    _validate_payload_checksum(raw, key="state_checksum")
    return raw


def _load_checkpoint(
    path: Path,
    *,
    expected_window: tuple[int, int],
) -> MonthlyRiskBaseCheckpoint:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("checkpoint JSON root must be an object")
    if "checkpoint_checksum" not in raw:
        raise ValueError("checkpoint_checksum is required for checkpoint schema 1")
    _validate_payload_checksum(raw, key="checkpoint_checksum")
    if int(raw.get("schema_version", 0)) != _RISK_BASE_CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported checkpoint schema {raw.get('schema_version')!r}")
    risk_window = raw.get("risk_window_month")
    if not isinstance(risk_window, list) or len(risk_window) != 2:
        raise ValueError("checkpoint risk_window_month must be a two-item list")
    resolved_window = (int(risk_window[0]), int(risk_window[1]))
    if resolved_window != expected_window:
        raise ValueError(
            f"checkpoint month {resolved_window!r} does not match expected {expected_window!r}"
        )
    monthly_risk_base = float(raw.get("monthly_risk_base", 0.0))
    if not math.isfinite(monthly_risk_base) or monthly_risk_base <= 0:
        raise ValueError("checkpoint monthly_risk_base must be finite and positive")
    return MonthlyRiskBaseCheckpoint(
        schema_version=int(raw["schema_version"]),
        risk_window_month=resolved_window,
        monthly_risk_base=monthly_risk_base,
        created_at=str(raw.get("created_at", "")),
        source=str(raw.get("source", "")),
        state_path=str(raw.get("state_path", "")),
    )


def _payload_checksum(payload: dict[str, object]) -> str:
    canonical = {
        key: value
        for key, value in payload.items()
        if key not in {"state_checksum", "checkpoint_checksum"}
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_payload_checksum(payload: dict[str, object], *, key: str) -> None:
    checksum = payload.get(key)
    if checksum is None:
        return
    if not isinstance(checksum, str) or checksum != _payload_checksum(payload):
        raise ValueError(f"{key} does not match payload")


def _write_json_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
        _fsync_directory(path.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def _write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise RiskBaseCheckpointError(
                f"refusing to overwrite immutable monthly risk checkpoint {path}"
            )
        return

    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    text = json.dumps(payload, indent=2, sort_keys=True)
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError as exc:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != payload:
                raise RiskBaseCheckpointError(
                    f"refusing to overwrite immutable monthly risk checkpoint {path}"
                ) from exc
        _fsync_directory(path.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_event_id(
    *,
    symbol: str,
    signal_time: datetime,
    selected_strategy: str,
    is_long: bool,
) -> str:
    """Build a deterministic identity for one strategy event."""
    payload = "|".join(
        [
            symbol,
            signal_time.astimezone(UTC).isoformat(),
            selected_strategy,
            "long" if is_long else "short",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
