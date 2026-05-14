from __future__ import annotations

import math

import pandas_ta as ta

from crypt.engines.base import BaseEngine
from crypt.models import EvaluationContext, Regime, Signal, Timeframe

_MIN_H4 = 60
_MIN_D1 = 30
_ADX_TRENDING = 22.0
_ADX_D1_MIN = 18.0
_ADX_HIGH_VOL_GATE = 25.0


class RegimeEngine(BaseEngine):
    """
    Classifies the current market regime for use by the aggregator.

    Priority: HIGH_VOL > TRENDING > RANGING.
    Always emits direction=neutral, strength=0, confidence=0.
    Sets ``meta["regime"]`` which the aggregator reads.

    Requires ctx.vol_regime to be set (by VolatilityEngine) before running.
    """

    @property
    def name(self) -> str:
        return "regime"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles.get(Timeframe.H4)
        vol_regime = ctx.vol_regime or "normal"

        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history — defaulting to RANGING"],
                inputs_missing=["candles[H4]"],
                meta={"regime": Regime.RANGING.value},
            )

        close = h4["c"]
        high = h4["h"]
        low = h4["l"]

        adx_h4_df = ta.adx(high, low, close, length=14)
        adx_h4 = None
        if adx_h4_df is not None:
            val = float(adx_h4_df["ADX_14"].iloc[-1])
            if not math.isnan(val):
                adx_h4 = val

        if adx_h4 is None:
            regime = Regime.RANGING
            rationale = [
                "H4 ADX unavailable — defaulting to RANGING",
                f"vol_regime={vol_regime}",
            ]
            return self._neutral(
                ctx,
                rationale=rationale,
                inputs_missing=["candles[H4]"],
                meta={"regime": regime.value},
            )

        # Optional D1 ADX for confluence.
        adx_d1: float | None = None
        d1 = ctx.candles.get(Timeframe.D1)
        if d1 is not None and len(d1) >= _MIN_D1:
            adx_d1_df = ta.adx(d1["h"], d1["l"], d1["c"], length=14)
            if adx_d1_df is not None:
                val_d1 = float(adx_d1_df["ADX_14"].iloc[-1])
                if not math.isnan(val_d1):
                    adx_d1 = val_d1

        # Regime classification.
        if vol_regime == "high" and adx_h4 < _ADX_HIGH_VOL_GATE:
            regime = Regime.HIGH_VOL
        elif adx_h4 >= _ADX_TRENDING:
            # H4 strong but D1 weak → cautious, treat as ranging.
            regime = (
                Regime.TRENDING if (adx_d1 is None or adx_d1 >= _ADX_D1_MIN) else Regime.RANGING
            )
        else:
            regime = Regime.RANGING

        rationale = [
            f"ADX_H4={adx_h4:.1f}" + (f", ADX_D1={adx_d1:.1f}" if adx_d1 is not None else ""),
            f"vol_regime={vol_regime}",
            f"→ {regime.value}",
        ]

        return self._neutral(
            ctx,
            rationale=rationale,
            meta={"regime": regime.value},
        )
