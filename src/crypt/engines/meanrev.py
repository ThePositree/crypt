from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
import pandas_ta as ta

from crypt.engines.base import BaseEngine
from crypt.models import Direction, EvaluationContext, Signal, Timeframe

_MIN_H4 = 50


class MeanRevEngine(BaseEngine):
    """
    Mean-reversion / contrarian view.

    Bullish when RSI14 ≤ 30 AND close ≤ lower Bollinger Band(20, 2).
    Bearish when RSI14 ≥ 70 AND close ≥ upper Bollinger Band(20, 2).
    """

    critical_inputs: ClassVar[list[str]] = ["candles[H4]"]

    @property
    def name(self) -> str:
        return "meanrev"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        h4 = ctx.candles.get(Timeframe.H4)
        if h4 is None or len(h4) < _MIN_H4:
            return self._neutral(
                ctx,
                rationale=["Insufficient H4 history (need ≥ 50 closed candles)"],
                inputs_missing=["candles[H4]"],
            )

        close = h4["c"]

        rsi_series = ta.rsi(close, length=14)
        bb_df = ta.bbands(close, length=20, std=2.0)  # type: ignore[arg-type]
        if rsi_series is None or bb_df is None:
            return self._neutral(
                ctx,
                rationale=["Indicator calculation failed"],
                inputs_missing=["candles[H4]"],
            )

        rsi14 = float(rsi_series.iloc[-1])
        close_val = float(close.iloc[-1])

        # BBands column names vary by pandas-ta version: BBL_20_2.0 or BBL_20_2.0_2.0.
        # Find by prefix to be version-agnostic.
        bb_lower_col = next((c for c in bb_df.columns if c.startswith("BBL_")), None)
        bb_mid_col = next((c for c in bb_df.columns if c.startswith("BBM_")), None)
        bb_upper_col = next((c for c in bb_df.columns if c.startswith("BBU_")), None)
        if bb_lower_col is None or bb_mid_col is None or bb_upper_col is None:
            return self._neutral(
                ctx,
                rationale=["BB column lookup failed"],
                inputs_missing=["bollinger"],
            )
        bb_lower = float(bb_df[bb_lower_col].iloc[-1])
        bb_mid = float(bb_df[bb_mid_col].iloc[-1])
        bb_upper = float(bb_df[bb_upper_col].iloc[-1])

        if any(math.isnan(v) for v in [rsi14, bb_lower, bb_mid, bb_upper]):
            return self._neutral(
                ctx,
                rationale=["NaN indicator values"],
                inputs_missing=["candles[H4]"],
            )

        # Zero-variance guard.
        if bb_upper == bb_mid:
            return self._neutral(
                ctx,
                rationale=["Zero BB width (flat price)"],
                inputs_missing=["bollinger"],
            )

        oversold = rsi14 <= 30 and close_val <= bb_lower
        overbought = rsi14 >= 70 and close_val >= bb_upper

        if not oversold and not overbought:
            return self._neutral(
                ctx,
                rationale=[
                    f"RSI14={rsi14:.1f}, close={close_val:.4f}",
                    f"BB: [{bb_lower:.4f}, {bb_mid:.4f}, {bb_upper:.4f}] — no extreme",
                ],
            )

        # Strength calculation.
        rsi_extreme = max(0.0, 30.0 - rsi14) + max(0.0, rsi14 - 70.0)
        if overbought:
            bb_extreme = max(0.0, (close_val - bb_upper) / (bb_upper - bb_mid))
        else:
            bb_extreme = max(0.0, (bb_lower - close_val) / (bb_mid - bb_lower))
        raw = float(np.clip((rsi_extreme / 30.0 + bb_extreme) / 2.0, 0.0, 1.0))
        strength = -raw if overbought else raw

        # Confidence.
        confidence = 0.4
        # Regime-based confidence adjustments are applied by the aggregator
        # via the regime signal. Only the early-extreme RSI bonus is computed here.
        # Regime engine hasn't run yet at this point, so leave regime-based
        # adjustments to the aggregator via the regime signal.
        # Check how many consecutive candles RSI has been in extreme territory.
        rsi_arr = rsi_series.dropna().values
        if len(rsi_arr) >= 2:
            if overbought:
                consecutive = int(np.sum(np.cumprod((rsi_arr[-2::-1] >= 70).astype(int))))
            else:
                consecutive = int(np.sum(np.cumprod((rsi_arr[-2::-1] <= 30).astype(int))))
            if consecutive <= 2:
                confidence += 0.1

        confidence = float(np.clip(confidence, 0.0, 1.0))
        direction: Direction = "bearish" if overbought else "bullish"

        rationale = [
            f"RSI14={rsi14:.1f}, close={close_val:.4f}",
            f"BB: [{bb_lower:.4f}, {bb_mid:.4f}, {bb_upper:.4f}]",
            f"{'overbought' if overbought else 'oversold'}: strength={strength:+.3f}",
        ]

        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
        )
