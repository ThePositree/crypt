from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas_ta as ta

from crypt.engines.base import BaseEngine
from crypt.models import EvaluationContext, Signal, Timeframe, VolRegime

_MIN_H4 = 60
_RANK_WINDOW = 360  # 60 days * 6 H4 bars / day
_HIGH_RANK = 0.85
_LOW_RANK = 0.15


def _rank_pct(series: npt.NDArray[Any], current: float) -> float:
    """
    Percentile rank of `current` within `series`.

    When all values are identical (zero-variance flat-line), returns 0.0
    so the caller maps it to "low" rather than the misleading 1.0.
    """
    if len(series) == 0:
        return 0.5
    if float(np.std(series)) < 1e-12:
        return 0.0
    return float(np.mean(series < current))


class VolatilityEngine(BaseEngine):
    """
    Non-directional engine that classifies volatility regime.

    Always emits direction=neutral, strength=0, confidence=0.
    Sets ``meta["vol_regime"]`` which the orchestrator copies to
    EvaluationContext.vol_regime before the regime engine runs.
    """

    @property
    def name(self) -> str:
        return "volatility"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles.get(Timeframe.H4)

        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history — defaulting to normal vol regime"],
                inputs_missing=["candles[H4]"],
                meta={"vol_regime": "normal"},
            )

        close = h4["c"]
        high = h4["h"]
        low = h4["l"]

        atr_series = ta.atr(high, low, close, length=14)

        if atr_series is None:
            return self._neutral(
                ctx,
                rationale=["ATR calculation failed"],
                inputs_missing=["candles[H4]"],
                meta={"vol_regime": "normal"},
            )

        last_close = float(close.iloc[-1])
        last_atr = float(atr_series.iloc[-1])

        if last_close <= 0 or math.isnan(last_atr) or math.isnan(last_close):
            return self._neutral(
                ctx,
                rationale=["Invalid price/ATR values"],
                meta={"vol_regime": "normal"},
            )

        atr_pct = last_atr / last_close

        # Use the full available history (up to _RANK_WINDOW bars).
        atr_vals = atr_series.dropna().values
        close_vals = close.values[-len(atr_vals) :]
        # Avoid division by zero.
        with np.errstate(invalid="ignore", divide="ignore"):
            atr_pct_history = np.where(close_vals > 0, atr_vals / close_vals, np.nan)
        atr_pct_history = atr_pct_history[~np.isnan(atr_pct_history)]

        if len(atr_pct_history) < 10:
            vol_regime: VolRegime = "normal"
        else:
            # Rank the current ATR% against recent history.
            rank = _rank_pct(atr_pct_history, atr_pct)
            if rank > _HIGH_RANK:
                vol_regime = "high"
            elif rank < _LOW_RANK:
                vol_regime = "low"
            else:
                vol_regime = "normal"
        rationale = [
            f"ATR14={last_atr:.4f}, ATR%={atr_pct:.4%}",
            f"vol_regime={vol_regime}",
        ]

        return self._neutral(
            ctx,
            rationale=rationale,
            meta={"vol_regime": vol_regime},
        )
