from __future__ import annotations

import math

# OKX perpetual backtests always model isolated-margin semantics (ADR-0029).
ISOLATED_FUTURES_ALWAYS = True
DEFAULT_MAINTENANCE_MARGIN_RATE = 0.004
DEFAULT_LIQUIDATION_FEE_RATE = 0.0005
DEFAULT_LIQUIDATION_BUFFER_PCT = 0.005
OKX_SOL_USDT_SWAP_TIER_SCHEDULE = "okx_sol_usdt_swap_2026_06_29"


def effective_margin_fraction(
    *,
    max_allowed_margin: float,
    max_positions: int,
) -> float:
    """
    Return the fraction of available balance one entry may lock as margin.

    When ``max_positions > 0``, each slot receives an equal share capped by
    ``max_allowed_margin``. A zero ``max_allowed_margin`` means "derive share
    only from ``max_positions``".
    """

    if max_positions > 0:
        per_position_share = 1.0 / max_positions
        if max_allowed_margin == 0:
            return per_position_share
        return min(max_allowed_margin, per_position_share)
    if max_allowed_margin > 0:
        return max_allowed_margin
    return 1.0


def per_entry_margin_cap(
    *,
    available_balance: float,
    max_allowed_margin: float,
    max_positions: int,
    open_positions: int,
) -> float:
    """
    Maximum margin one new entry may lock given current open positions.
    """

    if available_balance <= 0:
        return 0.0

    fraction = effective_margin_fraction(
        max_allowed_margin=max_allowed_margin,
        max_positions=max_positions,
    )
    if max_positions > 0:
        remaining_slots = max_positions - open_positions
        if remaining_slots <= 0:
            return 0.0
        return available_balance * fraction / remaining_slots
    return available_balance * fraction


def select_leverage_and_locked_margin(
    *,
    position_value: float,
    per_entry_cap: float,
    max_allowed_leverage: float,
) -> tuple[float, float] | None:
    """
    Choose leverage and locked margin for an isolated-futures-style entry.

    Uses the maximum allowed leverage whenever the position fits under the
    per-entry margin cap. This mirrors OKX isolated margin where traders pick
    high leverage to minimize locked collateral instead of the old donor path
    that minimized leverage and therefore maximized margin usage.
    """

    if position_value <= 0 or per_entry_cap <= 0:
        return None

    min_leverage_needed = max(1, math.ceil(position_value / per_entry_cap))
    if min_leverage_needed > max_allowed_leverage:
        return None

    required_leverage = float(max(max_allowed_leverage, 1.0))
    locked_margin = position_value / required_leverage
    if locked_margin > per_entry_cap + 1e-9:
        return None

    return required_leverage, locked_margin


def estimate_linear_liquidation_price(
    *,
    entry_price: float,
    is_long: bool,
    leverage: float,
    maintenance_margin_rate: float,
    liquidation_fee_rate: float,
) -> float | None:
    """Estimate OKX isolated liquidation for a USDT-margined linear swap."""
    combined_rate = maintenance_margin_rate + liquidation_fee_rate
    if entry_price <= 0 or leverage < 1 or not 0 <= combined_rate < 1:
        return None
    if is_long:
        denominator = 1 - combined_rate
        return entry_price * (1 - 1 / leverage) / denominator
    denominator = 1 + combined_rate
    return entry_price * (1 + 1 / leverage) / denominator


def okx_sol_usdt_swap_tier_for_size(position_size: float) -> tuple[float, float]:
    """Return ``(maintenance_margin_rate, max_leverage)`` for OKX SOL-USDT swap size."""
    if position_size <= 0:
        return DEFAULT_MAINTENANCE_MARGIN_RATE, 100.0
    if position_size <= 5_000:
        return 0.004, 100.0
    if position_size <= 10_000:
        return 0.005, 66.66

    tier = min(max(3, math.ceil(position_size / 20_000) + 2), 99)
    maintenance_margin_rate = 0.0075 + (tier - 3) * 0.005
    initial_margin_rate = 0.02 + (tier - 3) * 0.005
    return maintenance_margin_rate, 1.0 / initial_margin_rate


def maintenance_margin_rate_for_size(
    *,
    position_size: float,
    default_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
    tier_schedule: str | None = None,
) -> float:
    """Resolve maintenance margin rate for the configured tier schedule."""
    if not tier_schedule:
        return default_rate
    if tier_schedule == OKX_SOL_USDT_SWAP_TIER_SCHEDULE:
        return okx_sol_usdt_swap_tier_for_size(position_size)[0]
    raise ValueError(f"Unsupported maintenance margin tier schedule: {tier_schedule!r}")


def max_leverage_for_size(
    *,
    position_size: float,
    configured_max_leverage: float,
    tier_schedule: str | None = None,
) -> float:
    """Resolve effective max leverage after exchange tier caps."""
    if not tier_schedule:
        return configured_max_leverage
    if tier_schedule == OKX_SOL_USDT_SWAP_TIER_SCHEDULE:
        return min(configured_max_leverage, okx_sol_usdt_swap_tier_for_size(position_size)[1])
    raise ValueError(f"Unsupported maintenance margin tier schedule: {tier_schedule!r}")


def leverage_is_within_size_tier(
    *,
    position_size: float,
    leverage: float,
    configured_max_leverage: float,
    tier_schedule: str | None = None,
) -> bool:
    """Return whether leverage is allowed for this aggregate position size."""
    return leverage <= max_leverage_for_size(
        position_size=position_size,
        configured_max_leverage=configured_max_leverage,
        tier_schedule=tier_schedule,
    ) + 1e-9


def liquidation_is_beyond_stop(
    *,
    entry_price: float,
    stop_price: float,
    liquidation_price: float,
    is_long: bool,
    buffer_pct: float,
) -> bool:
    """Return whether liquidation is safely farther from entry than the SL."""
    buffer_distance = entry_price * buffer_pct
    if is_long:
        return liquidation_price <= stop_price - buffer_distance
    return liquidation_price >= stop_price + buffer_distance


def aggregate_linear_liquidation_price(
    *,
    entries: list[tuple[float, float]],
    is_long: bool,
    leverage: float,
    maintenance_margin_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
    liquidation_fee_rate: float = DEFAULT_LIQUIDATION_FEE_RATE,
    maintenance_margin_tier_schedule: str | None = None,
) -> float | None:
    """Estimate one OKX side-aggregated liquidation price."""
    total_size = sum(size for _, size in entries if size > 0)
    if total_size <= 0:
        return None
    resolved_maintenance_margin_rate = maintenance_margin_rate_for_size(
        position_size=total_size,
        default_rate=maintenance_margin_rate,
        tier_schedule=maintenance_margin_tier_schedule,
    )
    weighted_entry = sum(price * size for price, size in entries if size > 0) / total_size
    return estimate_linear_liquidation_price(
        entry_price=weighted_entry,
        is_long=is_long,
        leverage=leverage,
        maintenance_margin_rate=resolved_maintenance_margin_rate,
        liquidation_fee_rate=liquidation_fee_rate,
    )


def aggregate_liquidation_is_beyond_stops(
    *,
    entries_and_stops: list[tuple[float, float, float]],
    is_long: bool,
    leverage: float,
    maintenance_margin_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
    liquidation_fee_rate: float = DEFAULT_LIQUIDATION_FEE_RATE,
    buffer_pct: float = DEFAULT_LIQUIDATION_BUFFER_PCT,
    maintenance_margin_tier_schedule: str | None = None,
) -> tuple[bool, float | None]:
    liquidation_price = aggregate_linear_liquidation_price(
        entries=[(entry, size) for entry, size, _ in entries_and_stops],
        is_long=is_long,
        leverage=leverage,
        maintenance_margin_rate=maintenance_margin_rate,
        liquidation_fee_rate=liquidation_fee_rate,
        maintenance_margin_tier_schedule=maintenance_margin_tier_schedule,
    )
    if liquidation_price is None:
        return False, None
    safe = all(
        liquidation_is_beyond_stop(
            entry_price=entry,
            stop_price=stop,
            liquidation_price=liquidation_price,
            is_long=is_long,
            buffer_pct=buffer_pct,
        )
        for entry, _, stop in entries_and_stops
    )
    return safe, liquidation_price


def select_liquidation_safe_leverage_and_locked_margin(
    *,
    position_value: float,
    position_size: float | None = None,
    per_entry_cap: float,
    max_allowed_leverage: float,
    entry_price: float,
    stop_price: float,
    is_long: bool,
    maintenance_margin_rate: float = DEFAULT_MAINTENANCE_MARGIN_RATE,
    liquidation_fee_rate: float = DEFAULT_LIQUIDATION_FEE_RATE,
    liquidation_buffer_pct: float = DEFAULT_LIQUIDATION_BUFFER_PCT,
    maintenance_margin_tier_schedule: str | None = None,
    existing_leverage: float | None = None,
) -> tuple[float, float, float] | None:
    """Choose the highest affordable leverage whose liquidation is beyond SL."""
    if position_value <= 0 or per_entry_cap <= 0 or liquidation_buffer_pct < 0:
        return None

    resolved_position_size = (
        position_size if position_size is not None else position_value / entry_price
    )
    effective_max_leverage = max_leverage_for_size(
        position_size=resolved_position_size,
        configured_max_leverage=max_allowed_leverage,
        tier_schedule=maintenance_margin_tier_schedule,
    )
    resolved_maintenance_margin_rate = maintenance_margin_rate_for_size(
        position_size=resolved_position_size,
        default_rate=maintenance_margin_rate,
        tier_schedule=maintenance_margin_tier_schedule,
    )

    if existing_leverage is not None:
        candidates = [existing_leverage]
    else:
        maximum = math.floor(effective_max_leverage)
        candidates = [float(leverage) for leverage in range(maximum, 0, -1)]

    for leverage in candidates:
        if leverage < 1 or leverage > effective_max_leverage:
            continue
        locked_margin = position_value / leverage
        if locked_margin > per_entry_cap + 1e-9:
            continue
        liquidation_price = estimate_linear_liquidation_price(
            entry_price=entry_price,
            is_long=is_long,
            leverage=leverage,
            maintenance_margin_rate=resolved_maintenance_margin_rate,
            liquidation_fee_rate=liquidation_fee_rate,
        )
        if liquidation_price is None:
            continue
        if liquidation_is_beyond_stop(
            entry_price=entry_price,
            stop_price=stop_price,
            liquidation_price=liquidation_price,
            is_long=is_long,
            buffer_pct=liquidation_buffer_pct,
        ):
            return leverage, locked_margin, liquidation_price
    return None
