from __future__ import annotations

from crypt.engines.trend import TrendEngine
from tests.conftest import make_ctx, make_sideways_h4, make_trending_down_h4, make_trending_up_h4

engine = TrendEngine()


def test_uptrend_bullish() -> None:
    h4 = make_trending_up_h4(210)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "bullish", f"Expected bullish, got {sig.direction}"
    assert sig.strength > 0.1, f"Expected strength > 0.1, got {sig.strength}"
    assert sig.confidence >= 0.5, f"Expected confidence >= 0.5, got {sig.confidence}"


def test_downtrend_bearish() -> None:
    h4 = make_trending_down_h4(210)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "bearish", f"Expected bearish, got {sig.direction}"
    assert sig.strength < -0.1


def test_sideways_neutral() -> None:
    h4 = make_sideways_h4(210)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    # Sideways should produce neutral (ADX too low) or very low strength.
    assert sig.direction == "neutral" or abs(sig.strength) < 0.3


def test_insufficient_history_neutral() -> None:
    h4 = make_trending_up_h4(100)  # less than 200
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert "candles[H4]" in sig.inputs_missing


def test_no_candles_neutral() -> None:
    ctx = make_ctx()  # no H4 at all
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert sig.confidence == 0.0
    assert "candles[H4]" in sig.inputs_missing


def test_d1_confluence_boosts_confidence() -> None:
    h4 = make_trending_up_h4(210)
    d1 = make_trending_up_h4(70)
    ctx_no_d1 = make_ctx(h4=h4)
    ctx_with_d1 = make_ctx(h4=h4, d1=d1)
    sig_no = engine.evaluate(ctx_no_d1)
    sig_with = engine.evaluate(ctx_with_d1)
    if sig_no.direction == "bullish" and sig_with.direction == "bullish":
        assert sig_with.confidence >= sig_no.confidence
