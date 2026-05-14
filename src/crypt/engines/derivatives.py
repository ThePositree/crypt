from __future__ import annotations

import numpy as np

from crypt.engines.base import BaseEngine
from crypt.models import (
    Direction,
    EvaluationContext,
    FundingSnapshot,
    LongShortRatioSnapshot,
    OISnapshot,
    Signal,
    Timeframe,
)

_DIRECTION_THRESHOLD = 0.25


class DerivativesEngine(BaseEngine):
    """
    Derivatives positioning view.

    Combines three sub-signals:
      a) Funding extremity (contrarian, weight 0.4)
      b) OI momentum x price direction (trend-confirming, weight 0.4)
      c) Top-trader L/S ratio extremity (mild contrarian, weight 0.2)

    Degrades gracefully when OI or L/S ratio data is missing.
    """

    @property
    def name(self) -> str:
        return "derivatives"

    def evaluate(self, ctx: EvaluationContext) -> Signal:
        inputs_missing: list[str] = []

        # --- a) Funding sub-signal ---
        funding_signal, funding_rationale = self._funding_signal(ctx.funding, inputs_missing)

        if funding_signal is None:
            # No funding data at all — cannot produce a useful signal.
            return self._neutral(
                ctx,
                rationale=["No funding rate data available"],
                inputs_missing=["funding"],
            )

        # --- b) OI sub-signal ---
        oi_signal, oi_rationale = self._oi_signal(ctx.oi, ctx, inputs_missing)

        # --- c) L/S ratio sub-signal ---
        ls_signal, ls_rationale = self._ls_signal(ctx.ls_ratio, inputs_missing)

        # Weight rebalancing when data is missing.
        if "oi" in inputs_missing and "ls_ratio" in inputs_missing:
            w_fund, w_oi, w_ls = 1.0, 0.0, 0.0
        elif "oi" in inputs_missing:
            w_fund, w_oi, w_ls = 0.5, 0.0, 0.5
        elif "ls_ratio" in inputs_missing:
            w_fund, w_oi, w_ls = 0.5, 0.5, 0.0
        else:
            w_fund, w_oi, w_ls = 0.4, 0.4, 0.2

        strength = float(
            np.clip(
                w_fund * (funding_signal or 0.0)
                + w_oi * (oi_signal or 0.0)
                + w_ls * (ls_signal or 0.0),
                -1.0,
                1.0,
            )
        )

        direction: Direction
        if strength >= _DIRECTION_THRESHOLD:
            direction = "bullish"
        elif strength <= -_DIRECTION_THRESHOLD:
            direction = "bearish"
        else:
            direction = "neutral"

        # Confidence.
        confidence = 0.5
        sub_signs = [
            np.sign(s)
            for s in [funding_signal or 0.0, oi_signal or 0.0, ls_signal or 0.0]
            if s != 0.0
        ]
        if len(sub_signs) >= 2 and len(set(sub_signs)) == 1:
            confidence += 0.2
        if "ls_ratio" in inputs_missing:
            confidence -= 0.2
        if "oi" in inputs_missing:
            confidence -= 0.3

        confidence = float(np.clip(confidence, 0.0, 1.0))

        rationale = [
            f"funding_signal={funding_signal:+.3f} ({funding_rationale})",
            f"oi_signal={oi_signal:+.3f} ({oi_rationale})"
            if oi_signal is not None
            else "oi: missing",
            f"ls_signal={ls_signal:+.3f} ({ls_rationale})"
            if ls_signal is not None
            else "ls_ratio: missing",
            f"strength={strength:+.3f}, weights=({w_fund:.1f},{w_oi:.1f},{w_ls:.1f})",
        ]

        return self._signal(
            ctx,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
            inputs_missing=inputs_missing,
        )

    # ------------------------------------------------------------------
    # Sub-signal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _funding_signal(
        funding: list[FundingSnapshot] | None,
        inputs_missing: list[str],
    ) -> tuple[float | None, str]:
        if not funding:
            inputs_missing.append("funding")
            return None, "no data"

        rates = [float(f.rate) for f in funding]
        if len(rates) < 2:
            mean_7d = rates[0]
            std_7d = 1e-9
        else:
            mean_7d = float(np.mean(rates))
            std_7d = float(np.std(rates)) or 1e-9

        current = rates[-1]
        f_z = (current - mean_7d) / std_7d
        signal = float(-np.clip(f_z / 3.0, -1.0, 1.0))
        return signal, f"rate={current:.6f}, z={f_z:.2f}"

    @staticmethod
    def _oi_signal(
        oi: list[OISnapshot] | None,
        ctx: EvaluationContext,
        inputs_missing: list[str],
    ) -> tuple[float | None, str]:
        if not oi or len(oi) < 5:
            inputs_missing.append("oi")
            return None, "no data"

        oi_now = float(oi[-1].oi)
        # Find OI ~4h ago (4 hourly bars back).
        oi_4h_ago = float(oi[-5].oi) if len(oi) >= 5 else oi_now

        if oi_4h_ago == 0:
            inputs_missing.append("oi")
            return None, "zero OI"

        delta_oi_pct = oi_now / oi_4h_ago - 1.0

        # Price direction over the same 4h window using H4 candles.
        h4 = ctx.candles.get(Timeframe.H4)
        if h4 is not None and len(h4) >= 2:
            close_change = float(h4["c"].iloc[-1]) - float(h4["c"].iloc[-2])
            price_sign = float(np.sign(close_change))
        else:
            price_sign = 0.0

        oi_mag = float(np.clip(abs(delta_oi_pct) / 0.05, 0.0, 1.0))
        signal = price_sign * oi_mag
        return signal, f"Δoi%={delta_oi_pct:+.3%}, price_sign={price_sign:+.0f}"

    @staticmethod
    def _ls_signal(
        ls_ratio: list[LongShortRatioSnapshot] | None,
        inputs_missing: list[str],
    ) -> tuple[float | None, str]:
        if not ls_ratio or len(ls_ratio) < 2:
            inputs_missing.append("ls_ratio")
            return None, "no data"

        values = [r.long_ratio for r in ls_ratio]
        mean_48h = float(np.mean(values))
        std_48h = float(np.std(values)) or 1e-9
        current = values[-1]
        ls_z = (current - mean_48h) / std_48h
        signal = float(-np.clip(ls_z / 3.0, -1.0, 1.0))
        return signal, f"ls={current:.3f}, z={ls_z:.2f}"
