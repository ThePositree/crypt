"""DSS catalog role/timeframe eligibility declarations."""

from __future__ import annotations

from typing import Literal

DSSRole = Literal["trigger", "filter"]

_INTRADAY = ("15m", "H1")
_SWING = ("H1", "H4")
_CONTEXT = ("H1", "H4", "D1")
_ENTRY = ("15m", "H1", "H4")

_TRIGGER_TIMEFRAMES: dict[str, tuple[str, ...]] = {
    "pt_vwap_reclaim": _INTRADAY,
    "pt_volume_spike": _INTRADAY,
    "pt_ps_vixfix_reversal": _INTRADAY,
    "pt_ps_pivot_volume_break": _INTRADAY,
    "pt_order_block_retest": _ENTRY,
    "pt_structure_break": _ENTRY,
    "pt_pivot_reclaim": _ENTRY,
}

_FILTER_TIMEFRAMES: dict[str, tuple[str, ...]] = {
    "pf_session": _INTRADAY,
    "pf_ps_killzone_session": _INTRADAY,
    "pf_vwap_proximity": _INTRADAY,
    "pf_context_aligned": _CONTEXT,
    "pf_trend_ema_stack": _CONTEXT,
    "pf_ps_smc_bias": _CONTEXT,
    "pf_anchor_age": _SWING,
    "pf_avoid_large_move": _SWING,
    "pf_trend_strength": _SWING,
}


def dss_instance_labels(
    names: tuple[str, ...],
    timeframes: tuple[str, ...],
    *,
    role: DSSRole,
) -> tuple[str, ...]:
    labels: list[str] = []
    for name in names:
        allowed = dss_supported_timeframes(name, role=role)
        labels.extend(f"{name}@{timeframe}" for timeframe in timeframes if timeframe in allowed)
    return tuple(labels)


def dss_supported_timeframes(name: str, *, role: DSSRole) -> tuple[str, ...]:
    """Return declared DSS search timeframes for a catalog block and role."""

    if role == "trigger":
        if name.startswith("pt_ps_smc_"):
            return _ENTRY
        return _TRIGGER_TIMEFRAMES.get(name, _ENTRY)
    if name.startswith("pf_ps_smc_"):
        return _ENTRY
    return _FILTER_TIMEFRAMES.get(name, _ENTRY)
