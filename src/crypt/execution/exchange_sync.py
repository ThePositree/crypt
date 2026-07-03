"""Exchange snapshot and reconciliation helpers for live execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backtester.margin_policy import leverage_is_within_size_tier
from crypt.execution.position_state import ExecutionState


@dataclass(frozen=True)
class ExchangeBalance:
    """USDT account balance snapshot."""

    total: float
    free: float
    used: float
    equity: float | None = None


@dataclass(frozen=True)
class ExchangePosition:
    """Open exchange position normalized for reconciliation."""

    symbol: str
    contracts: float
    side: str | None = None
    entry_price: float | None = None
    liquidation_price: float | None = None
    unrealized_pnl: float | None = None
    leverage: float | None = None
    margin_mode: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExchangeOrder:
    """Open exchange order or pending algo order."""

    symbol: str
    order_id: str
    kind: str
    client_order_id: str = ""
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
    exchange_by_symbol: dict[str, list[ExchangePosition]] = {
        symbol: [] for symbol in tracked_symbols
    }
    for pos in exchange_positions:
        exchange_by_symbol.setdefault(pos.symbol, []).append(pos)

    for symbol in sorted(tracked_symbols):
        local_positions = local_by_symbol.get(symbol, [])
        exchange_symbol_positions = exchange_by_symbol.get(symbol, [])
        local_count = len(local_positions)
        exchange_count = len(exchange_symbol_positions)
        if exchange_count and not local_count:
            blocking.append(f"orphan_exchange_position:{symbol}:{exchange_count}")
        if local_count and not exchange_count:
            blocking.append(f"missing_exchange_position:{symbol}:{local_count}")
        if not local_count or not exchange_count:
            continue
        for side_name, is_long in (("long", True), ("short", False)):
            local_side = [pos for pos in local_positions if pos.is_long is is_long]
            exchange_side = [pos for pos in exchange_symbol_positions if pos.side == side_name]
            if bool(local_side) != bool(exchange_side):
                blocking.append(
                    f"position_side_mismatch:{symbol}:{side_name}:"
                    f"local={len(local_side)}:exchange={len(exchange_side)}"
                )
                continue
            if not local_side:
                continue
            exchange_average_entries = [
                pos.entry_price for pos in exchange_side if pos.entry_price is not None
            ]
            if exchange_average_entries:
                aggregate_entry_price = exchange_average_entries[0]
                aggregate_size = sum(pos.size for pos in local_side)
                leverage = local_side[0].leverage
                for local in local_side:
                    local.aggregate_entry_price = aggregate_entry_price
                    local.locked_margin = (
                        local.size * aggregate_entry_price / leverage if aggregate_size > 0 else 0.0
                    )
            local_contracts = sum(pos.contracts for pos in local_side)
            exchange_contracts = sum(pos.contracts for pos in exchange_side)
            if abs(local_contracts - exchange_contracts) > 1e-8:
                blocking.append(
                    f"position_size_mismatch:{symbol}:{side_name}:"
                    f"local={local_contracts:.8g}:exchange={exchange_contracts:.8g}"
                )
            exchange_leverages = {pos.leverage for pos in exchange_side if pos.leverage is not None}
            if exchange_leverages and any(
                abs(value - local_side[0].leverage) > 1e-8 for value in exchange_leverages
            ):
                blocking.append(
                    f"position_leverage_mismatch:{symbol}:{side_name}:"
                    f"local={local_side[0].leverage:.8g}:"
                    f"exchange={sorted(exchange_leverages)}"
                )
            if any(
                pos.margin_mode is not None and pos.margin_mode != "isolated"
                for pos in exchange_side
            ):
                blocking.append(f"position_margin_mode_not_isolated:{symbol}:{side_name}")
            aggregate_size = sum(pos.size for pos in local_side)
            leverage = local_side[0].leverage
            tier_schedule = local_side[0].maintenance_margin_tier_schedule
            if not leverage_is_within_size_tier(
                position_size=aggregate_size,
                leverage=leverage,
                configured_max_leverage=leverage,
                tier_schedule=tier_schedule,
            ):
                blocking.append(
                    f"unsafe_leverage_tier:{symbol}:{side_name}:"
                    f"size={aggregate_size:.8g}:leverage={leverage:.8g}"
                )
            liquidation_prices = [
                pos.liquidation_price for pos in exchange_side if pos.liquidation_price is not None
            ]
            if liquidation_prices:
                liquidation_price = liquidation_prices[0]
                for local in local_side:
                    local.liquidation_price = liquidation_price
                    buffer_distance = local.entry_price * local.liquidation_buffer_pct
                    unsafe = (
                        liquidation_price > local.sl_price - buffer_distance
                        if is_long
                        else liquidation_price < local.sl_price + buffer_distance
                    )
                    if unsafe:
                        blocking.append(
                            f"unsafe_liquidation:{symbol}:{side_name}:"
                            f"liq={liquidation_price:.8g}:sl={local.sl_price:.8g}"
                        )

    local_client_order_ids = {
        identifier
        for pos in local_open
        for identifier in (
            pos.client_order_id,
            pos.algo_client_order_id,
            pos.trailing_algo_client_order_id,
        )
        if identifier
    }
    local_exchange_order_ids = {
        identifier
        for pos in local_open
        for identifier in (
            pos.entry_order_id,
            pos.stop_algo_order_id,
            pos.take_profit_order_id,
            pos.trailing_algo_order_id,
        )
        if identifier
    }
    exchange_client_order_ids = {
        order.client_order_id for order in snapshot.algo_orders if order.client_order_id
    }
    exchange_algo_order_ids = {order.order_id for order in snapshot.algo_orders}
    exchange_regular_order_ids = {order.order_id for order in snapshot.open_orders}
    for order in [*snapshot.open_orders, *snapshot.algo_orders]:
        if order.symbol not in tracked_symbols:
            continue
        matches_local = (
            order.client_order_id in local_client_order_ids
            if order.client_order_id
            else order.order_id in local_exchange_order_ids
        )
        if not matches_local:
            blocking.append(f"orphan_order:{order.symbol}:{order.order_id}:{order.kind}")
    for local_pos in local_open:
        matching_exchange_position = any(
            exchange_pos.symbol == local_pos.symbol
            and exchange_pos.side == ("long" if local_pos.is_long else "short")
            for exchange_pos in exchange_positions
        )
        if not matching_exchange_position:
            continue
        stop_present = (
            local_pos.stop_algo_order_id in exchange_algo_order_ids
            if local_pos.stop_algo_order_id
            else local_pos.algo_client_order_id in exchange_client_order_ids
            if local_pos.algo_client_order_id
            else False
        )
        if not stop_present:
            blocking.append(
                f"missing_stop_protection:{local_pos.symbol}:"
                f"{local_pos.stop_algo_order_id or local_pos.algo_client_order_id or 'unbound'}"
            )
        combined_tp_present = any(
            order.client_order_id == local_pos.algo_client_order_id
            and bool(order.raw.get("tpTriggerPx"))
            for order in snapshot.algo_orders
            if local_pos.algo_client_order_id
        )
        tp_present = (
            local_pos.take_profit_order_id in exchange_regular_order_ids
            if local_pos.take_profit_order_id
            else combined_tp_present
        )
        if local_pos.fixed_take_profit_enabled and not tp_present:
            blocking.append(
                f"missing_take_profit_protection:{local_pos.symbol}:"
                f"{local_pos.take_profit_order_id or local_pos.algo_client_order_id or 'unbound'}"
            )
        if local_pos.trail_activation_rrr > 0:
            trailing_present = (
                local_pos.trailing_algo_order_id in exchange_algo_order_ids
                if local_pos.trailing_algo_order_id
                else local_pos.trailing_algo_client_order_id in exchange_client_order_ids
            )
            if not trailing_present:
                blocking.append(
                    f"missing_trailing_protection:{local_pos.symbol}:"
                    f"{local_pos.trailing_algo_order_id or local_pos.trailing_algo_client_order_id or 'unbound'}"
                )

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
