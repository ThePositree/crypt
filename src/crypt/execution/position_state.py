"""LivePosition dataclass and atomic JSON state persistence.

The state file at `data/live_positions.json` is the source of truth for
which positions are currently open. It is written atomically (write tmp →
rename) so a crash never leaves a corrupt file.

Schema version bumps must preserve backward compatibility or provide a
migration in `_migrate_state`.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

_SCHEMA_VERSION = 2


@dataclass
class LivePosition:
    """One open position tracked by the live execution module."""

    position_id: str
    symbol: str
    signal_time: str          # ISO-8601 UTC
    entry_time: str           # ISO-8601 UTC
    entry_price: float
    sl_price: float
    tp_price: float
    size: float               # base asset units (e.g. SOL)
    contracts: float          # OKX contract count, rounded to exchange lot size
    leverage: float
    locked_margin: float
    risk_base_capital: float
    is_long: bool
    ttl_bars: int
    entry_order_id: str | None
    status: Literal["open", "closing", "closed"]
    selected_strategy: str = ""
    position_group: str = ""
    signal_event: dict[str, object] = field(default_factory=dict)
    trail_activation_rrr: float = 0.0
    trail_distance_atr: float = 0.0
    trail_active: bool = False
    trail_stop_price: float | None = None
    best_favorable_price: float | None = None
    last_sync_status: str = "unknown"
    last_sync_at: str | None = None
    exit_time: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    exit_fee: float | None = None

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
            selected_strategy=selected_strategy,
            position_group=position_group,
            signal_event=signal_event or {},
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

    def open_positions_for(self, symbol: str) -> list[LivePosition]:
        return [p for p in self.positions if p.symbol == symbol and p.status == "open"]

    def all_open_positions(self) -> list[LivePosition]:
        return [p for p in self.positions if p.status == "open"]


def load_state(path: Path) -> ExecutionState:
    """Load state from disk, returning an empty state if the file does not exist."""
    if not path.exists():
        return ExecutionState(
            schema_version=_SCHEMA_VERSION,
            risk_window_month=None,
            monthly_risk_base=0.0,
            positions=[],
            last_exchange_sync_at=None,
            last_exchange_sync_ok=False,
            last_exchange_sync_errors=[],
            last_daily_sync_report_date=None,
        )

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw = _migrate_state(raw)

    risk_window = raw.get("risk_window_month")
    positions = [LivePosition(**p) for p in raw.get("positions", [])]

    return ExecutionState(
        schema_version=raw.get("schema_version", _SCHEMA_VERSION),
        risk_window_month=(int(risk_window[0]), int(risk_window[1])) if risk_window else None,
        monthly_risk_base=float(raw.get("monthly_risk_base", 0.0)),
        positions=positions,
        last_exchange_sync_at=raw.get("last_exchange_sync_at"),
        last_exchange_sync_ok=bool(raw.get("last_exchange_sync_ok", False)),
        last_exchange_sync_errors=[str(item) for item in raw.get("last_exchange_sync_errors", [])],
        last_daily_sync_report_date=raw.get("last_daily_sync_report_date"),
    )


def save_state(state: ExecutionState, path: Path) -> None:
    """Atomically write state to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")

    payload = {
        "schema_version": state.schema_version,
        "risk_window_month": list(state.risk_window_month) if state.risk_window_month else None,
        "monthly_risk_base": state.monthly_risk_base,
        "last_exchange_sync_at": state.last_exchange_sync_at,
        "last_exchange_sync_ok": state.last_exchange_sync_ok,
        "last_exchange_sync_errors": state.last_exchange_sync_errors,
        "last_daily_sync_report_date": state.last_daily_sync_report_date,
        "saved_at": datetime.now(UTC).isoformat(),
        "positions": [asdict(p) for p in state.positions],
    }
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _migrate_state(raw: dict) -> dict:  # type: ignore[type-arg]
    """Upgrade old schema versions to the current one in-place."""
    version = raw.get("schema_version", 0)
    if version == _SCHEMA_VERSION:
        return raw
    if version <= 1:
        raw["schema_version"] = _SCHEMA_VERSION
        raw.setdefault("last_exchange_sync_at", None)
        raw.setdefault("last_exchange_sync_ok", False)
        raw.setdefault("last_exchange_sync_errors", [])
        raw.setdefault("last_daily_sync_report_date", None)
        for pos in raw.get("positions", []):
            pos.setdefault("selected_strategy", "")
            pos.setdefault("position_group", "")
            pos.setdefault("signal_event", {})
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
            pos.setdefault("exit_fee", None)
        return raw
    return raw
