from __future__ import annotations

import math

# OKX perpetual backtests always model isolated-margin semantics (ADR-0029).
ISOLATED_FUTURES_ALWAYS = True


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
