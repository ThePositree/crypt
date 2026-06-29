"""Exchange snapshot and reconciliation helpers for live execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from crypt.execution.position_state import ExecutionState


@dataclass(frozen=True)
class ExchangeBalance:
    """USDT account balance snapshot."""

    total: float
    free: float
    used: float


@dataclass(frozen=True)
class ExchangePosition:
    """Open exchange position normalized for reconciliation."""

    symbol: str
    contracts: float
    side: str | None = None
    entry_price: float | None = None
    unrealized_pnl: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExchangeOrder:
    """Open exchange order or pending algo order."""

    symbol: str
    order_id: str
    kind: str
    side: str | None = None
    amount: float | None = None
    price: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExchangeSnapshot:
    """Everything live execution needs to know before making decisions."""

    fetched_at: datetime
    balance: ExchangeBalance
    positions: list[ExchangePosition]
    open_orders: list[ExchangeOrder]
    algo_orders: list[ExchangeOrder]
    recent_fills: list[dict[str, Any]] = field(default_factory=list)
    position_mode_hedged: bool = True

    @classmethod
    def empty_dry_run(cls, *, balance: float) -> ExchangeSnapshot:
        """Build a deterministic empty snapshot for unauthenticated dry runs."""
        return cls(
            fetched_at=datetime.now(UTC),
            balance=ExchangeBalance(total=balance, free=balance, used=0.0),
            positions=[],
            open_orders=[],
            algo_orders=[],
            recent_fills=[],
            position_mode_hedged=True,
        )


@dataclass(frozen=True)
class SyncReport:
    """Result of comparing local execution state with exchange state."""

    synced: bool
    blocking_reasons: list[str]
    warnings: list[str]
    fetched_at: datetime


def reconcile_exchange_snapshot(
    *,
    state: ExecutionState,
    snapshot: ExchangeSnapshot,
    symbols: list[str],
) -> SyncReport:
    """Classify local/exchange mismatches before opening new trades."""
    blocking: list[str] = []
    warnings: list[str] = []
    tracked_symbols = set(symbols)
    local_open = state.all_open_positions()
    local_by_symbol = {symbol: state.open_positions_for(symbol) for symbol in tracked_symbols}
    exchange_positions = [p for p in snapshot.positions if p.symbol in tracked_symbols]
    exchange_by_symbol: dict[str, list[ExchangePosition]] = {symbol: [] for symbol in tracked_symbols}
    for pos in exchange_positions:
        exchange_by_symbol.setdefault(pos.symbol, []).append(pos)

    for symbol in sorted(tracked_symbols):
        local_count = len(local_by_symbol.get(symbol, []))
        exchange_count = len(exchange_by_symbol.get(symbol, []))
        if exchange_count and not local_count:
            blocking.append(f"orphan_exchange_position:{symbol}:{exchange_count}")
        if local_count and not exchange_count:
            blocking.append(f"missing_exchange_position:{symbol}:{local_count}")

    tracked_open_symbols = {pos.symbol for pos in local_open}
    for order in [*snapshot.open_orders, *snapshot.algo_orders]:
        if order.symbol not in tracked_symbols:
            continue
        if order.symbol not in tracked_open_symbols:
            blocking.append(f"orphan_order:{order.symbol}:{order.order_id}:{order.kind}")

    if snapshot.balance.total <= 0:
        blocking.append("non_positive_exchange_balance")
    if snapshot.balance.free < 0 or snapshot.balance.used < 0:
        warnings.append("negative_balance_component")
    if not snapshot.position_mode_hedged:
        blocking.append("position_mode_not_long_short")

    return SyncReport(
        synced=not blocking,
        blocking_reasons=blocking,
        warnings=warnings,
        fetched_at=snapshot.fetched_at,
    )
