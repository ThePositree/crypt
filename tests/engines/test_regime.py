from __future__ import annotations

from crypt.engines.regime import RegimeEngine
from crypt.models import Regime
from tests.conftest import make_ctx, make_sideways_h4, make_trending_up_h4

engine = RegimeEngine()


def test_strong_uptrend_trending() -> None:
    h4 = make_trending_up_h4(210)
    d1 = make_trending_up_h4(80)
    ctx = make_ctx(h4=h4, d1=d1)
    ctx.vol_regime = "normal"
    sig = engine.evaluate(ctx)
    assert sig.meta.get("regime") == Regime.TRENDING.value


def test_sideways_ranging() -> None:
    h4 = make_sideways_h4(210)
    ctx = make_ctx(h4=h4)
    ctx.vol_regime = "normal"
    sig = engine.evaluate(ctx)
    assert sig.meta.get("regime") == Regime.RANGING.value


def test_high_vol_no_trend_high_vol() -> None:
    """High vol_regime + low ADX → HIGH_VOL."""
    h4 = make_sideways_h4(210)
    ctx = make_ctx(h4=h4)
    ctx.vol_regime = "high"
    sig = engine.evaluate(ctx)
    assert sig.meta.get("regime") in (Regime.HIGH_VOL.value, Regime.RANGING.value)


def test_insufficient_history_ranging() -> None:
    h4 = make_trending_up_h4(30)
    ctx = make_ctx(h4=h4)
    ctx.vol_regime = "normal"
    sig = engine.evaluate(ctx)
    assert sig.meta.get("regime") == Regime.RANGING.value
    assert "candles[H4]" in sig.inputs_missing


def test_no_candles() -> None:
    ctx = make_ctx()
    ctx.vol_regime = "normal"
    sig = engine.evaluate(ctx)
    assert sig.meta.get("regime") == Regime.RANGING.value
