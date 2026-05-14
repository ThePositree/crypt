from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from crypt.aggregator.weights import SCORING_ENGINES, WeightsConfig
from crypt.models import Regime, Signal, Verdict, VolRegime


def aggregate(
    signals: list[Signal],
    regime: Regime,
    weights_cfg: WeightsConfig,
    symbol: str,
    vol_regime: VolRegime = "normal",
) -> Verdict:
    """
    Combine per-engine Signals into a single Verdict.

    Never raises — any unexpected state produces a HOLD with an explanatory
    rationale.
    """
    try:
        return _aggregate_inner(signals, regime, weights_cfg, symbol, vol_regime)
    except Exception as exc:
        return Verdict(
            symbol=symbol,
            decision="HOLD",
            confidence=0,
            score=0.0,
            regime=regime,
            breakdown=signals,
            rationale=f"Aggregator error: {exc}",
            produced_at=datetime.now(tz=UTC),
        )


def _aggregate_inner(
    signals: list[Signal],
    regime: Regime,
    weights_cfg: WeightsConfig,
    symbol: str,
    vol_regime: VolRegime,
) -> Verdict:
    # Index signals by engine name; keep only the scoring ones.
    sig_map = {s.engine: s for s in signals if s.engine in SCORING_ENGINES}

    base_weights = weights_cfg.engine_weights(regime)

    # Renormalise weights when an engine is absent or all-missing.
    active_engines = [eng for eng in SCORING_ENGINES if eng in sig_map]
    missing_engines = [eng for eng in SCORING_ENGINES if eng not in sig_map]

    if not active_engines:
        return Verdict(
            symbol=symbol,
            decision="HOLD",
            confidence=0,
            score=0.0,
            regime=regime,
            breakdown=signals,
            rationale="No scoring engines produced signals",
            produced_at=datetime.now(tz=UTC),
        )

    # Rebalance weights across active engines.
    active_weight_sum = sum(base_weights[eng] for eng in active_engines)
    if active_weight_sum <= 0:
        equal = 1.0 / len(active_engines)
        eff_weights = dict.fromkeys(active_engines, equal)
    else:
        eff_weights = {eng: base_weights[eng] / active_weight_sum for eng in active_engines}

    # Weighted sum of strengths → score.
    score = 0.0
    for eng in active_engines:
        sig = sig_map[eng]
        score += eff_weights[eng] * sig.strength
    score = float(np.clip(score, -1.0, 1.0))

    # Confidence calculation.
    base_conf = 0.0
    for eng in active_engines:
        sig = sig_map[eng]
        w = eff_weights[eng]
        # Neutral signals (strength == 0) contribute less to confidence.
        conf_factor = 1.0 if sig.strength != 0.0 else 0.5
        base_conf += w * sig.confidence * conf_factor

    score_sign = float(np.sign(score)) if score != 0.0 else 0.0
    aligned = [
        eng
        for eng in active_engines
        if score_sign != 0 and float(np.sign(sig_map[eng].strength)) == score_sign
    ]
    alignment = len(aligned) / len(active_engines) if active_engines else 0.0

    vol_mult = weights_cfg.vol_multiplier(vol_regime)
    raw_conf = base_conf * (0.5 + 0.5 * alignment) * vol_mult
    confidence = round(float(np.clip(raw_conf * 100, 0.0, 100.0)))

    # Decision.
    threshold = weights_cfg.threshold(regime)
    if score >= threshold:
        decision = "BUY"
    elif score <= -threshold:
        decision = "SELL"
    else:
        decision = "HOLD"

    # Human-readable rationale.
    lines = [
        f"Regime: {regime.value} | vol: {vol_regime} | decision: {decision} ({confidence}%)",
        f"Score: {score:+.3f} (threshold: ±{threshold})",
    ]
    # Sort contributing signals by absolute contribution descending.
    contributions = [
        (eng, eff_weights[eng] * abs(sig_map[eng].strength), sig_map[eng]) for eng in active_engines
    ]
    contributions.sort(key=lambda x: x[1], reverse=True)
    for eng, _contrib, sig in contributions:
        lines.append(
            f"  {eng}: {sig.direction} "
            f"(strength={sig.strength:+.3f}, w={eff_weights[eng]:.2f}, "
            f"conf={sig.confidence:.2f})"
        )
    if missing_engines:
        lines.append(f"  Missing engines: {', '.join(missing_engines)}")
    for sig in signals:
        if sig.inputs_missing:
            lines.append(f"  {sig.engine} missing inputs: {', '.join(sig.inputs_missing)}")

    return Verdict(
        symbol=symbol,
        decision=decision,
        confidence=confidence,
        score=score,
        regime=regime,
        breakdown=sorted(signals, key=lambda s: abs(s.strength), reverse=True),
        rationale="\n".join(lines),
        produced_at=datetime.now(tz=UTC),
    )
