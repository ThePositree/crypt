from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from crypt.aggregator.ensemble import aggregate
from crypt.aggregator.weights import WeightsConfig
from crypt.models import Regime, Signal

_CFG = WeightsConfig.load(Path("config/weights.yaml"))

_NOW = datetime.now(tz=UTC)
_SYM = "BTC-USDT-SWAP"


def _sig(engine: str, direction: str, strength: float, confidence: float) -> Signal:
    return Signal(
        engine=engine,
        symbol=_SYM,
        direction=direction,  # type: ignore[arg-type]
        strength=strength,
        confidence=confidence,
        produced_at=_NOW,
    )


def test_all_bullish_buy() -> None:
    signals = [
        _sig("trend", "bullish", 0.8, 0.8),
        _sig("meanrev", "bullish", 0.6, 0.7),
        _sig("derivatives", "bullish", 0.7, 0.7),
    ]
    verdict = aggregate(signals, Regime.TRENDING, _CFG, _SYM)
    assert verdict.decision == "BUY"
    assert verdict.confidence >= 50


def test_all_bearish_sell() -> None:
    signals = [
        _sig("trend", "bearish", -0.8, 0.8),
        _sig("meanrev", "bearish", -0.6, 0.7),
        _sig("derivatives", "bearish", -0.7, 0.7),
    ]
    verdict = aggregate(signals, Regime.TRENDING, _CFG, _SYM)
    assert verdict.decision == "SELL"


def test_trend_dominant_in_trending_regime() -> None:
    # In TRENDING regime, trend weight >> meanrev.
    signals = [
        _sig("trend", "bullish", 0.8, 0.8),
        _sig("meanrev", "bearish", -0.6, 0.7),
        _sig("derivatives", "bullish", 0.3, 0.5),
    ]
    verdict = aggregate(signals, Regime.TRENDING, _CFG, _SYM)
    # Trend weight 0.55 * 0.8 dominates meanrev 0.05 * (-0.6).
    assert verdict.decision in ("BUY", "HOLD")
    assert verdict.score > 0


def test_meanrev_dominant_in_ranging_regime() -> None:
    signals = [
        _sig("trend", "bearish", -0.5, 0.6),
        _sig("meanrev", "bullish", 0.8, 0.8),
        _sig("derivatives", "neutral", 0.0, 0.3),
    ]
    verdict = aggregate(signals, Regime.RANGING, _CFG, _SYM)
    # meanrev weight 0.50 * 0.8 should overcome trend 0.15 * (-0.5).
    assert verdict.score > 0


def test_all_neutral_hold() -> None:
    signals = [
        _sig("trend", "neutral", 0.0, 0.0),
        _sig("meanrev", "neutral", 0.0, 0.0),
        _sig("derivatives", "neutral", 0.0, 0.0),
    ]
    verdict = aggregate(signals, Regime.RANGING, _CFG, _SYM)
    assert verdict.decision == "HOLD"
    assert verdict.confidence < 50


def test_missing_derivatives_renormalises() -> None:
    # No derivatives signal — weights should renormalise across trend+meanrev.
    signals = [
        _sig("trend", "bullish", 0.8, 0.8),
        _sig("meanrev", "bullish", 0.6, 0.7),
    ]
    verdict = aggregate(signals, Regime.TRENDING, _CFG, _SYM)
    assert verdict.decision in ("BUY", "HOLD")
    assert -1.0 <= verdict.score <= 1.0


def test_high_vol_regime_raises_threshold() -> None:
    # In HIGH_VOL, threshold is 0.45 — moderate signals should produce HOLD.
    signals = [
        _sig("trend", "bullish", 0.3, 0.6),
        _sig("meanrev", "neutral", 0.0, 0.3),
        _sig("derivatives", "bullish", 0.3, 0.5),
    ]
    verdict = aggregate(signals, Regime.HIGH_VOL, _CFG, _SYM)
    # Score likely below 0.45 → HOLD.
    assert verdict.decision == "HOLD"


def test_aggregate_never_raises() -> None:
    """Even with garbage inputs, aggregate must return a Verdict (not raise)."""
    verdict = aggregate([], Regime.RANGING, _CFG, _SYM)
    assert verdict.decision == "HOLD"
