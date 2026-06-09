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
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

_SCHEMA_VERSION = 1


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
    contracts: int            # OKX contract count
    leverage: float
    locked_margin: float
    risk_base_capital: float
    is_long: bool
    ttl_bars: int
    entry_order_id: str | None
    status: Literal["open", "closing", "closed"]

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
        contracts: int,
        leverage: float,
        locked_margin: float,
        risk_base_capital: float,
        is_long: bool,
        ttl_bars: int,
        entry_order_id: str | None,
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
        )


@dataclass
class ExecutionState:
    """Full persistent state of the execution module."""

    schema_version: int
    risk_window_month: tuple[int, int] | None  # (year, month)
    monthly_risk_base: float
    positions: list[LivePosition]

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
    )


def save_state(state: ExecutionState, path: Path) -> None:
    """Atomically write state to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")

    payload = {
        "schema_version": state.schema_version,
        "risk_window_month": list(state.risk_window_month) if state.risk_window_month else None,
        "monthly_risk_base": state.monthly_risk_base,
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
    # Future migrations go here:
    # if version == 1: ...
    return raw
