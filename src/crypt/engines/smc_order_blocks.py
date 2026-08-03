from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd

from crypt.engines.base import BaseEngine
from crypt.models import Direction, EvaluationContext, Signal, Timeframe
from crypt.structure.smc import BULLISH, SMCOrderBlock, SMCStructureEvent, analyse_smc_cached

_MIN_H4 = 60
_MAX_CONFIDENCE = 0.85
_MAX_ZONE_WIDTH_ATR = 3.0


class SMCOrderBlocksEngine(BaseEngine):
    """Retest engine for active SMC order-block zones."""

    critical_inputs: ClassVar[list[str]] = ["candles[H4]"]

    @property
    def name(self) -> str:
        return "smc_order_blocks"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles_by_timeframe.get(Timeframe.H4)
        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history for SMC order blocks"],
                inputs_missing=["candles[H4]"],
            )

        state = analyse_smc_cached(h4, tick_time=ctx.tick_time)
        visible = h4[pd.to_datetime(h4["open_time"], utc=True) < pd.Timestamp(ctx.tick_time)]
        if visible.empty:
            return self._neutral(ctx, rationale=["No closed H4 candle at tick_time"])

        last = visible.sort_values("open_time").iloc[-1]
        atr14 = _atr14(visible)
        if atr14 <= 0:
            return self._neutral(
                ctx, rationale=["ATR14 unavailable for SMC order-block width filter"]
            )

        active_blocks = [
            block
            for block in state.order_blocks
            if block.active
            and block.known_at <= ctx.tick_time
            and (block.high - block.low) <= _MAX_ZONE_WIDTH_ATR * atr14
            and _touches_zone(block, last)
        ]
        if not active_blocks:
            return self._neutral(
                ctx,
                rationale=["No active SMC order block retest"],
                meta={"swing_bias": state.swing_bias, "internal_bias": state.internal_bias},
            )

        latest_event = _latest_structure_event(state.structure_events)
        candidate = _select_candidate(active_blocks, last, latest_event)
        if candidate is None:
            return self._neutral(
                ctx,
                rationale=[
                    "Both bullish and bearish order blocks retested without structure tie-break"
                ],
                meta={"swing_bias": state.swing_bias, "internal_bias": state.internal_bias},
            )

        non_neutral_biases = [b for b in (state.swing_bias, state.internal_bias) if b != 0]
        if non_neutral_biases and all(b != candidate.direction for b in non_neutral_biases):
            return self._neutral(
                ctx,
                rationale=["SMC order block conflicts with current structure bias"],
                meta={
                    "zone_low": candidate.low,
                    "zone_high": candidate.high,
                    "origin_time": candidate.origin_time.isoformat(),
                    "swing_bias": state.swing_bias,
                    "internal_bias": state.internal_bias,
                },
            )

        close = float(last["c"])
        strength_abs = 0.65
        confidence = 0.50
        if state.swing_bias == state.internal_bias == candidate.direction:
            strength_abs += 0.15
            confidence += 0.15
        if _rejects_from_zone(candidate, close):
            strength_abs += 0.10
            confidence += 0.10

        sign = 1.0 if candidate.direction == BULLISH else -1.0
        strength = float(np.clip(sign * strength_abs, -1.0, 1.0))
        confidence = float(np.clip(confidence, 0.0, _MAX_CONFIDENCE))
        direction: Direction = "bullish" if candidate.direction == BULLISH else "bearish"
        distance = _distance_to_zone_atr(candidate, close, atr14)

        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=[
                f"{candidate.kind} {'bullish' if candidate.direction == BULLISH else 'bearish'} order-block retest",
                f"zone={candidate.low:.4f}-{candidate.high:.4f}, distance={distance:.2f} ATR",
                f"swing_bias={state.swing_bias}, internal_bias={state.internal_bias}",
            ],
            meta={
                "zone_low": candidate.low,
                "zone_high": candidate.high,
                "origin_time": candidate.origin_time.isoformat(),
                "known_at": candidate.known_at.isoformat(),
                "distance_to_zone_atr": distance,
                "structure_event_type": candidate.source_event.event_type,
                "structure_kind": candidate.kind,
                "bias": candidate.direction,
                "swing_bias": state.swing_bias,
                "internal_bias": state.internal_bias,
            },
        )


def _touches_zone(block: SMCOrderBlock, candle: pd.Series) -> bool:
    high = float(candle["h"])
    low = float(candle["l"])
    close = float(candle["c"])
    if block.direction == BULLISH:
        return low <= block.high and close >= block.low
    return high >= block.low and close <= block.high


def _rejects_from_zone(block: SMCOrderBlock, close: float) -> bool:
    if block.direction == BULLISH:
        return close > block.high
    return close < block.low


def _select_candidate(
    blocks: list[SMCOrderBlock],
    candle: pd.Series,
    latest_event: SMCStructureEvent | None,
) -> SMCOrderBlock | None:
    directions = {block.direction for block in blocks}
    if len(directions) > 1:
        if latest_event is None:
            return None
        aligned = [block for block in blocks if block.direction == latest_event.direction]
        if not aligned:
            return None
        blocks = aligned

    close = float(candle["c"])
    return min(blocks, key=lambda block: (_raw_distance_to_zone(block, close), block.known_at))


def _raw_distance_to_zone(block: SMCOrderBlock, close: float) -> float:
    if block.low <= close <= block.high:
        return 0.0
    return min(abs(close - block.low), abs(close - block.high))


def _distance_to_zone_atr(block: SMCOrderBlock, close: float, atr: float) -> float:
    return round(_raw_distance_to_zone(block, close) / atr, 4) if atr > 0 else 0.0


def _latest_structure_event(events: list[SMCStructureEvent]) -> SMCStructureEvent | None:
    if not events:
        return None
    return sorted(events, key=lambda e: (e.known_at, 1 if e.kind == "swing" else 0))[-1]


def _atr14(candles: pd.DataFrame) -> float:
    df = candles.sort_values("open_time").tail(15)
    high = df["h"].astype(float)
    low = df["l"].astype(float)
    close = df["c"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    value = float(tr.tail(14).mean())
    return value if np.isfinite(value) else 0.0
