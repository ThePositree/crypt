from __future__ import annotations

from datetime import timedelta
from typing import ClassVar

import numpy as np

from crypt.engines.base import BaseEngine
from crypt.models import Direction, EvaluationContext, Signal, Timeframe
from crypt.structure.smc import BULLISH, SMCStructureEvent, analyse_smc_cached

_MIN_H4 = 60
_MAX_EVENT_AGE_BARS = 12
_H4 = timedelta(hours=4)

_EVENT_WEIGHTS: dict[tuple[str, str], float] = {
    ("internal", "CHOCH"): 0.45,
    ("internal", "BOS"): 0.60,
    ("swing", "CHOCH"): 0.75,
    ("swing", "BOS"): 0.90,
}


class SMCStructureEngine(BaseEngine):
    """Directional engine based on confirmed SMC BOS/CHoCH events."""

    critical_inputs: ClassVar[list[str]] = ["candles[H4]"]

    @property
    def name(self) -> str:
        return "smc_structure"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles_by_timeframe.get(Timeframe.H4)
        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history for SMC structure"],
                inputs_missing=["candles[H4]"],
            )

        state = analyse_smc_cached(h4, tick_time=ctx.tick_time)
        event = _latest_structure_event(state.structure_events)
        if event is None:
            return self._neutral(
                ctx,
                rationale=["No confirmed BOS/CHoCH structure event"],
                meta={"swing_bias": state.swing_bias, "internal_bias": state.internal_bias},
            )

        age_bars = max(0.0, (ctx.tick_time - event.known_at) / _H4)
        if age_bars > _MAX_EVENT_AGE_BARS:
            return self._neutral(
                ctx,
                rationale=[f"Latest SMC event is stale ({age_bars:.1f} H4 bars old)"],
                meta={
                    "event_type": event.event_type,
                    "structure_kind": event.kind,
                    "event_time": event.event_time.isoformat(),
                    "known_at": event.known_at.isoformat(),
                    "swing_bias": state.swing_bias,
                    "internal_bias": state.internal_bias,
                },
            )

        base = _EVENT_WEIGHTS[(event.kind, event.event_type)]
        magnitude = max(0.20, base - 0.10 * age_bars)
        sign = 1.0 if event.direction == BULLISH else -1.0
        strength = float(np.clip(sign * magnitude, -1.0, 1.0))

        confidence = abs(strength)
        if state.swing_bias != 0 and state.swing_bias == state.internal_bias == event.direction:
            confidence += 0.10
        if (
            event.event_type == "CHOCH"
            and event.kind == "internal"
            and state.swing_bias not in (0, event.direction)
        ):
            confidence -= 0.15
        confidence = float(np.clip(confidence, 0.0, 1.0))

        direction: Direction = "bullish" if event.direction == BULLISH else "bearish"
        rationale = [
            f"{event.kind} {event.event_type} {'bullish' if event.direction == BULLISH else 'bearish'} at {event.level:.4f}",
            f"age={age_bars:.1f} H4 bars, swing_bias={state.swing_bias}, internal_bias={state.internal_bias}",
            f"strength={strength:+.3f}, confidence={confidence:.2f}",
        ]
        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
            meta={
                "event_type": event.event_type,
                "structure_kind": event.kind,
                "event_time": event.event_time.isoformat(),
                "known_at": event.known_at.isoformat(),
                "broken_level": event.level,
                "swing_bias": state.swing_bias,
                "internal_bias": state.internal_bias,
            },
        )


def _latest_structure_event(events: list[SMCStructureEvent]) -> SMCStructureEvent | None:
    if not events:
        return None
    return sorted(events, key=lambda e: (e.known_at, 1 if e.kind == "swing" else 0))[-1]
