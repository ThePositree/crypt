from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar

import numpy as np
import pandas as pd

from crypt.engines.base import BaseEngine
from crypt.models import Direction, EvaluationContext, Signal, Timeframe
from crypt.structure.smc import SMCLiquiditySweep, analyse_smc_cached

_MIN_H4 = 60
_MAX_SWEEP_AGE_BARS = 3
_H4 = timedelta(hours=4)
_MAX_CONFIDENCE = 0.80


class SMCLiquidityEngine(BaseEngine):
    """Reversal engine for equal-level and swing-level liquidity sweeps."""

    critical_inputs: ClassVar[list[str]] = ["candles[H4]"]

    @property
    def name(self) -> str:
        return "smc_liquidity"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles_by_timeframe.get(Timeframe.H4)
        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history for SMC liquidity"],
                inputs_missing=["candles[H4]"],
            )

        state = analyse_smc_cached(h4, tick_time=ctx.tick_time)
        sweep = _latest_fresh_sweep(state.liquidity_sweeps, ctx.tick_time)
        if sweep is None:
            return self._neutral(
                ctx,
                rationale=["No fresh SMC liquidity sweep"],
                meta={
                    "liquidity_levels": len(state.liquidity_levels),
                    "liquidity_sweeps": len(state.liquidity_sweeps),
                },
            )

        visible = h4[pd.to_datetime(h4["open_time"], utc=True) < pd.Timestamp(ctx.tick_time)]
        if visible.empty:
            return self._neutral(ctx, rationale=["No closed H4 candle at tick_time"])
        last = visible.sort_values("open_time").iloc[-1]

        if sweep.ambiguous and not _clear_rejection(last, sweep.side):
            return self._neutral(
                ctx,
                rationale=["Ambiguous same-candle high/low liquidity sweep"],
                meta={
                    "swept_level": sweep.level,
                    "level_type": sweep.level_type,
                    "event_time": sweep.event_time.isoformat(),
                    "wick_distance_atr": sweep.wick_distance_atr,
                },
            )

        direction: Direction = "bearish" if sweep.side == "high" else "bullish"
        sign = -1.0 if sweep.side == "high" else 1.0
        strength_abs = 0.70 if sweep.level_type == "swing" else 0.55
        if _rejects_in_signal_direction(last, direction):
            strength_abs += 0.10

        strength = float(np.clip(sign * strength_abs, -1.0, 1.0))
        confidence = float(np.clip(0.45 + abs(strength) * 0.35, 0.0, _MAX_CONFIDENCE))

        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=[
                f"{sweep.level_type} {'high' if sweep.side == 'high' else 'low'} liquidity sweep",
                f"level={sweep.level:.4f}, wick_distance={sweep.wick_distance_atr:.2f} ATR",
                f"strength={strength:+.3f}, confidence={confidence:.2f}",
            ],
            meta={
                "swept_level": sweep.level,
                "level_type": sweep.level_type,
                "event_time": sweep.event_time.isoformat(),
                "known_at": sweep.known_at.isoformat(),
                "wick_distance_atr": sweep.wick_distance_atr,
            },
        )


def _latest_fresh_sweep(
    sweeps: list[SMCLiquiditySweep],
    tick_time: datetime,
) -> SMCLiquiditySweep | None:
    fresh = [
        sweep
        for sweep in sweeps
        if sweep.known_at <= tick_time
        and max(0.0, (tick_time - sweep.known_at) / _H4) <= _MAX_SWEEP_AGE_BARS
    ]
    if not fresh:
        return None
    return sorted(fresh, key=lambda sweep: (sweep.known_at, sweep.level_type == "swing"))[-1]


def _clear_rejection(candle: pd.Series, swept_side: str) -> bool:
    candle_range = float(candle["h"]) - float(candle["l"])
    if candle_range <= 0:
        return False
    body = abs(float(candle["c"]) - float(candle["o"]))
    if body <= 0.5 * candle_range:
        return False
    return _rejects_in_signal_direction(candle, "bearish" if swept_side == "high" else "bullish")


def _rejects_in_signal_direction(candle: pd.Series, direction: Direction) -> bool:
    open_ = float(candle["o"])
    close = float(candle["c"])
    if direction == "bearish":
        return close < open_
    if direction == "bullish":
        return close > open_
    return False
