"""Causal, optional take-profit reachability adjustments.

The policy is deliberately pure so the historical execution simulator and
live executor apply the same decision after the actual entry price is known.
It may inspect only signal-time inputs; realized PnL and future candles are
never part of the decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TpPolicyConfig:
    """Configuration copied into an actionable signal event."""

    enabled: bool = False
    min_original_rrr: float = 4.0
    min_tp_distance_pct: float | None = 0.07
    min_last_touch_bars: int | None = 720
    adjusted_rrr: float = 3.0

    def __post_init__(self) -> None:
        if self.min_original_rrr <= 0:
            raise ValueError("tp_policy min_original_rrr must be > 0")
        if self.min_tp_distance_pct is not None and self.min_tp_distance_pct <= 0:
            raise ValueError("tp_policy min_tp_distance_pct must be > 0")
        if self.min_last_touch_bars is not None and self.min_last_touch_bars < 0:
            raise ValueError("tp_policy min_last_touch_bars must be >= 0")
        if self.adjusted_rrr <= 0:
            raise ValueError("tp_policy adjusted_rrr must be > 0")
        if self.min_tp_distance_pct is None and self.min_last_touch_bars is None:
            raise ValueError("tp_policy requires a distance or recency condition")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> TpPolicyConfig:
        """Parse a portfolio or event mapping, preserving disabled defaults."""

        if raw is None:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            min_original_rrr=float(raw.get("min_original_rrr", 4.0)),
            min_tp_distance_pct=(
                _optional_positive_float(raw, "min_tp_distance_pct")
                if "min_tp_distance_pct" in raw
                else 0.07
            ),
            min_last_touch_bars=(
                _optional_non_negative_int(raw, "min_last_touch_bars")
                if "min_last_touch_bars" in raw
                else 720
            ),
            adjusted_rrr=float(raw.get("adjusted_rrr", 3.0)),
        )

    @classmethod
    def from_event(cls, event: Mapping[str, Any] | None) -> TpPolicyConfig:
        """Read flattened policy fields carried by a signal event."""

        if event is None:
            return cls()
        raw = event.get("tp_policy")
        if isinstance(raw, Mapping):
            return cls.from_mapping(raw)
        if not any(key in event for key in _EVENT_POLICY_KEYS):
            return cls()
        return cls.from_mapping(
            {
                "enabled": event.get("tp_policy_enabled", False),
                "min_original_rrr": event.get("tp_policy_min_original_rrr", 4.0),
                "min_tp_distance_pct": event.get("tp_policy_min_distance_pct", 0.07),
                "min_last_touch_bars": event.get("tp_policy_min_last_touch_bars", 720),
                "adjusted_rrr": event.get("tp_policy_adjusted_rrr", 3.0),
            }
        )

    def as_event_fields(self) -> dict[str, Any]:
        """Return scalar fields safe to put in a dataframe event payload."""

        return {
            "tp_policy_enabled": self.enabled,
            "tp_policy_min_original_rrr": self.min_original_rrr,
            "tp_policy_min_distance_pct": self.min_tp_distance_pct,
            "tp_policy_min_last_touch_bars": self.min_last_touch_bars,
            "tp_policy_adjusted_rrr": self.adjusted_rrr,
        }


@dataclass(frozen=True, slots=True)
class TpPolicyDecision:
    """The deterministic result of applying a TP policy to one entry."""

    original_rrr: float
    effective_rrr: float
    adjusted: bool
    reason: str
    tp_distance_pct: float
    last_touch_bars: int | None


_EVENT_POLICY_KEYS = (
    "tp_policy_enabled",
    "tp_policy_min_original_rrr",
    "tp_policy_min_distance_pct",
    "tp_policy_min_last_touch_bars",
    "tp_policy_adjusted_rrr",
)


def adjust_tp_rrr(
    *,
    signal: int,
    entry_price: float,
    sl_price: float,
    original_rrr: float,
    last_touch_bars: int | None,
    policy: TpPolicyConfig,
) -> TpPolicyDecision:
    """Return effective RRR using only entry-known geometry and recency."""

    if signal not in (1, -1):
        raise ValueError("tp_policy signal must be 1 or -1")
    if entry_price <= 0 or sl_price <= 0:
        raise ValueError("tp_policy prices must be positive")
    if original_rrr <= 0:
        raise ValueError("original_rrr must be > 0")
    tp_distance_pct = abs(entry_price - sl_price) * original_rrr / entry_price

    if not policy.enabled:
        return TpPolicyDecision(
            original_rrr=original_rrr,
            effective_rrr=original_rrr,
            adjusted=False,
            reason="disabled",
            tp_distance_pct=tp_distance_pct,
            last_touch_bars=last_touch_bars,
        )
    if original_rrr < policy.min_original_rrr:
        reason = "original_rrr_below_threshold"
    else:
        distance_hit = (
            policy.min_tp_distance_pct is not None and tp_distance_pct >= policy.min_tp_distance_pct
        )
        recency_hit = (
            policy.min_last_touch_bars is not None
            and last_touch_bars is not None
            and last_touch_bars >= policy.min_last_touch_bars
        )
        if distance_hit or recency_hit:
            effective_rrr = min(original_rrr, policy.adjusted_rrr)
            reason_parts = []
            if distance_hit:
                reason_parts.append("distance")
            if recency_hit:
                reason_parts.append("recency")
            return TpPolicyDecision(
                original_rrr=original_rrr,
                effective_rrr=effective_rrr,
                adjusted=effective_rrr < original_rrr,
                reason="adjusted_" + "_and_".join(reason_parts),
                tp_distance_pct=tp_distance_pct,
                last_touch_bars=last_touch_bars,
            )
        reason = "reachability_conditions_not_met"

    return TpPolicyDecision(
        original_rrr=original_rrr,
        effective_rrr=original_rrr,
        adjusted=False,
        reason=reason,
        tp_distance_pct=tp_distance_pct,
        last_touch_bars=last_touch_bars,
    )


def _optional_positive_float(raw: Mapping[str, Any], key: str) -> float | None:
    value = raw.get(key)
    if value is None:
        return None
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"tp_policy {key} must be > 0")
    return parsed


def _optional_non_negative_int(raw: Mapping[str, Any], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"tp_policy {key} must be >= 0")
    return parsed
