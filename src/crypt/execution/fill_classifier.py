"""Classify exchange-side position closures from recent OKX/ccxt fills."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from crypt.execution.position_state import LivePosition

_PRICE_TOLERANCE_PCT = 0.001


@dataclass(frozen=True)
class ClosedPositionFill:
    """Best-effort realized close details for a locally tracked position."""

    exit_time: datetime | None
    exit_price: float | None
    exit_reason: str
    realized_pnl: float | None
    constituent_realized_pnl: float | None
    exit_fee: float | None
    filled_contracts: float = 0.0


def allocate_closed_position_fills(
    *,
    positions: list[LivePosition],
    fills: list[dict[str, Any]],
) -> dict[str, ClosedPositionFill]:
    """Allocate each identified fill to at most one local position."""
    allocated: dict[str, list[dict[str, Any]]] = {
        position.position_id: [] for position in positions
    }
    for fill in fills:
        matches = [position for position in positions if _fill_matches_position(fill, position)]
        if len(matches) == 1:
            allocated[matches[0].position_id].append(fill)
    return {
        position.position_id: classify_closed_position_from_fills(
            pos=position,
            fills=allocated[position.position_id],
        )
        for position in positions
    }


def classify_closed_position_from_fills(
    *,
    pos: LivePosition,
    fills: list[dict[str, Any]],
) -> ClosedPositionFill:
    """Infer close details for a position that is absent from exchange positions."""
    close_side = "sell" if pos.is_long else "buy"
    entry_time = pos.entry_dt.astimezone(UTC)
    candidates: list[dict[str, Any]] = []
    seen_fill_ids: set[str] = set()
    for fill in fills:
        fill_time = _fill_time(fill)
        if (
            not _fill_matches_position(fill, pos)
            or _fill_side(fill) != close_side
            or fill_time is None
            or fill_time < entry_time
        ):
            continue
        identity = _fill_identity(fill)
        if identity in seen_fill_ids:
            continue
        seen_fill_ids.add(identity)
        candidates.append(fill)
    if not candidates:
        return ClosedPositionFill(
            exit_time=None,
            exit_price=None,
            exit_reason="exchange_closed_unknown",
            realized_pnl=None,
            constituent_realized_pnl=None,
            exit_fee=None,
            filled_contracts=0.0,
        )

    weighted_price_numerator = 0.0
    amount_sum = 0.0
    fee_sum = 0.0
    latest_time: datetime | None = None
    for fill in candidates:
        price = _float_or_none(fill.get("price"))
        amount = _float_or_none(fill.get("amount")) or _float_or_none(fill.get("contracts")) or 0.0
        fee_sum += _fill_fee(fill)
        fill_time = _fill_time(fill)
        if fill_time is not None and (latest_time is None or fill_time > latest_time):
            latest_time = fill_time
        if price is None or amount <= 0:
            continue
        weighted_price_numerator += price * amount
        amount_sum += amount

    exit_price = (
        weighted_price_numerator / amount_sum
        if weighted_price_numerator > 0 and amount_sum > 0
        else None
    )
    realized_pnl = _realized_pnl(
        pos=pos,
        exit_price=exit_price,
        exit_fee=fee_sum,
        use_aggregate_entry=True,
    )
    constituent_realized_pnl = _realized_pnl(
        pos=pos,
        exit_price=exit_price,
        exit_fee=fee_sum,
        use_aggregate_entry=False,
    )
    return ClosedPositionFill(
        exit_time=latest_time,
        exit_price=exit_price,
        exit_reason=_exit_reason(pos, exit_price),
        realized_pnl=realized_pnl,
        constituent_realized_pnl=constituent_realized_pnl,
        exit_fee=fee_sum,
        filled_contracts=amount_sum,
    )


def apply_closed_position_fill(pos: LivePosition, fill: ClosedPositionFill) -> None:
    """Persist close classification on a live position."""
    pos.status = "closed"
    pos.exit_time = fill.exit_time.isoformat() if fill.exit_time is not None else None
    pos.exit_price = fill.exit_price
    pos.exit_reason = fill.exit_reason
    pos.realized_pnl = fill.realized_pnl
    pos.constituent_realized_pnl = fill.constituent_realized_pnl
    pos.exit_fee = fill.exit_fee


def _fill_side(fill: dict[str, Any]) -> str | None:
    side = fill.get("side")
    return str(side).lower() if side is not None else None


def _fill_time(fill: dict[str, Any]) -> datetime | None:
    timestamp = _float_or_none(fill.get("timestamp"))
    if timestamp is not None and timestamp > 0:
        return datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    raw_dt = fill.get("datetime")
    if isinstance(raw_dt, str) and raw_dt:
        parsed = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
        return parsed.astimezone(UTC)
    return None


def _fill_fee(fill: dict[str, Any]) -> float:
    fee = fill.get("fee")
    if isinstance(fee, dict):
        return abs(_float_or_none(fee.get("cost")) or 0.0)
    fees = fill.get("fees")
    if isinstance(fees, list):
        return sum(
            abs(_float_or_none(item.get("cost")) or 0.0) for item in fees if isinstance(item, dict)
        )
    return 0.0


def _realized_pnl(
    *,
    pos: LivePosition,
    exit_price: float | None,
    exit_fee: float,
    use_aggregate_entry: bool,
) -> float | None:
    if exit_price is None:
        return None
    entry_price = (pos.aggregate_entry_price or pos.entry_price) if use_aggregate_entry else pos.entry_price
    entry_value = pos.size * entry_price
    exit_value = pos.size * exit_price
    gross = exit_value - entry_value if pos.is_long else entry_value - exit_value
    return gross - pos.entry_fee - exit_fee


def _fill_matches_position(fill: dict[str, Any], pos: LivePosition) -> bool:
    info = fill.get("info")
    raw = info if isinstance(info, dict) else {}

    inst_id = raw.get("instId")
    if inst_id and str(inst_id) != pos.symbol:
        return False

    expected_side = "long" if pos.is_long else "short"
    pos_side = raw.get("posSide")
    if pos_side and str(pos_side).lower() != expected_side:
        return False

    algo_client_id = raw.get("algoClOrdId") or raw.get("attachAlgoClOrdId")
    close_client_id = raw.get("clOrdId") or fill.get("clientOrderId")
    expected_ids = {
        identifier
        for identifier in (
            pos.algo_client_order_id,
            pos.trailing_algo_client_order_id,
            pos.close_client_order_id,
        )
        if identifier
    }
    expected_order_ids = {
        identifier
        for identifier in (
            pos.stop_algo_order_id,
            pos.take_profit_order_id,
            pos.trailing_algo_order_id,
        )
        if identifier
    }
    if expected_ids or expected_order_ids:
        observed_client_ids = {
            str(identifier) for identifier in (algo_client_id, close_client_id) if identifier
        }
        observed_order_ids = {
            str(identifier)
            for identifier in (
                close_client_id,
                raw.get("ordId"),
                raw.get("algoId"),
                fill.get("order"),
            )
            if identifier
        }
        return bool(observed_client_ids & expected_ids or observed_order_ids & expected_order_ids)

    subtype = str(raw.get("subType") or "")
    if subtype:
        return subtype == ("5" if pos.is_long else "6")
    return not raw


def _exit_reason(pos: LivePosition, exit_price: float | None) -> str:
    if exit_price is None:
        return "exchange_closed_unknown"
    if _near(exit_price, pos.sl_price):
        return "stop_loss"
    if _near(exit_price, pos.tp_price):
        return "take_profit"
    if pos.trail_stop_price is not None and _near(exit_price, pos.trail_stop_price):
        return "trailing_stop"
    return "manual_or_exchange_close"


def _near(lhs: float, rhs: float) -> bool:
    tolerance = max(abs(rhs) * _PRICE_TOLERANCE_PCT, 1e-9)
    return abs(lhs - rhs) <= tolerance


def _fill_identity(fill: dict[str, Any]) -> str:
    info = fill.get("info")
    raw = info if isinstance(info, dict) else {}
    for value in (fill.get("id"), raw.get("tradeId"), raw.get("fillId")):
        if value not in (None, ""):
            return f"trade:{value}"
    return "|".join(
        str(value)
        for value in (
            raw.get("ordId") or fill.get("order"),
            fill.get("timestamp"),
            fill.get("side"),
            fill.get("price"),
            fill.get("amount"),
        )
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
