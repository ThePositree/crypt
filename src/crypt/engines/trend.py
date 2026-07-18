from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
import pandas_ta as ta

from crypt.engines.base import BaseEngine
from crypt.models import Direction, EvaluationContext, Signal, Timeframe

_MIN_H4 = 200
_MIN_D1 = 60
_ADX_THRESHOLD = 18.0
_ADX_STRONG = 25.0


class TrendEngine(BaseEngine):
    """
    Trend-follower view.

    Bullish when EMA50_H4 > EMA200_H4 and ADX(14) >= 18.
    Bearish when EMA50_H4 < EMA200_H4 and ADX(14) >= 18.
    Neutral otherwise.

    Strength: sign(EMA50 - EMA200) * |gap / (3 * ATR14)| * clip(ADX/30, 0, 1).
    Confidence: base 0.5 ± adjustments for D1 confluence, ADX strength, regime.
    """

    critical_inputs: ClassVar[list[str]] = ["candles[H4]"]

    @property
    def name(self) -> str:
        return "trend"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles.get(Timeframe.H4)
        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history (need ≥ 200 closed candles)"],
                inputs_missing=["candles[H4]"],
            )

        close = h4["c"]
        high = h4["h"]
        low = h4["l"]

        ema50_series = ta.ema(close, length=50)
        ema200_series = ta.ema(close, length=200)
        adx_df = ta.adx(high, low, close, length=14)
        atr_series = ta.atr(high, low, close, length=14)

        if ema50_series is None or ema200_series is None or adx_df is None or atr_series is None:
            return self._neutral(
                ctx,
                rationale=["Indicator calculation failed (insufficient data)"],
                inputs_missing=["candles[H4]"],
            )

        ema50 = float(ema50_series.iloc[-1])
        ema200 = float(ema200_series.iloc[-1])
        adx14 = float(adx_df["ADX_14"].iloc[-1])
        atr14 = float(atr_series.iloc[-1])

        if math.isnan(ema50) or math.isnan(ema200) or math.isnan(adx14):
            return self._neutral(
                ctx,
                rationale=["NaN indicator values (not enough history)"],
                inputs_missing=["candles[H4]"],
            )

        if adx14 < _ADX_THRESHOLD:
            return self._neutral(
                ctx,
                rationale=[f"ADX14={adx14:.1f} below threshold {_ADX_THRESHOLD} — no clear trend"],
            )

        ema_gap = ema50 - ema200
        direction: Direction = "bullish" if ema_gap > 0 else "bearish"

        # Strength: normalise gap by 3*ATR, scale by ADX/30.
        if atr14 > 0 and not math.isnan(atr14):
            raw_strength = np.sign(ema_gap) * min(1.0, abs(ema_gap) / (3.0 * atr14))
        else:
            raw_strength = float(np.sign(ema_gap))
        adx_scale = float(np.clip(adx14 / 30.0, 0.0, 1.0))
        strength = float(np.clip(raw_strength * adx_scale, -1.0, 1.0))

        # Confidence.
        confidence = 0.5
        if adx14 >= _ADX_STRONG:
            confidence += 0.1

        # Higher-timeframe confluence: D1 EMA50 vs EMA200.
        d1 = ctx.candles.get(Timeframe.D1)
        if d1 is not None and len(d1) >= _MIN_D1:
            d1_ema50 = ta.ema(d1["c"], length=50)
            d1_ema200 = ta.ema(d1["c"], length=200)
            if d1_ema50 is not None and d1_ema200 is not None:
                d1_gap = float(d1_ema50.iloc[-1]) - float(d1_ema200.iloc[-1])
                if (ema_gap > 0 and d1_gap > 0) or (ema_gap < 0 and d1_gap < 0):
                    confidence += 0.2

        # Regime penalty — regime engine hasn't run yet, so check ctx.vol_regime
        # as a proxy for HIGH_VOL (regime detector itself applies the final penalty).
        # We do not penalise here for RANGING — the aggregator weight handles that.
        confidence = float(np.clip(confidence, 0.0, 1.0))

        rationale = [
            f"EMA50={ema50:.4f}, EMA200={ema200:.4f}, gap={ema_gap:+.4f}",
            f"ADX14={adx14:.1f}, ATR14={atr14:.4f}",
            f"strength={strength:+.3f}, confidence={confidence:.2f}",
        ]

        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
        )
