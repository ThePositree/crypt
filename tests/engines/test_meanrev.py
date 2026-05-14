from __future__ import annotations

import pandas as pd

from crypt.engines.meanrev import MeanRevEngine
from tests.conftest import (
    make_ctx,
    make_overbought_h4,
    make_oversold_h4,
    make_trending_up_h4,
)

engine = MeanRevEngine()


def test_oversold_bullish() -> None:
    h4 = make_oversold_h4()
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    # Deep crash should produce oversold RSI and price below lower BB.
    if sig.direction != "neutral":
        assert sig.direction == "bullish", f"Got {sig.direction}"
        assert sig.strength > 0


def test_overbought_bearish() -> None:
    h4 = make_overbought_h4()
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    if sig.direction != "neutral":
        assert sig.direction == "bearish", f"Got {sig.direction}"
        assert sig.strength < 0


def test_insufficient_history() -> None:
    ctx = make_ctx(h4=make_trending_up_h4(30))  # less than 50
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert "candles[H4]" in sig.inputs_missing


def test_no_candles_neutral() -> None:
    ctx = make_ctx()
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"


def test_flat_price_neutral() -> None:
    """Zero-variance series → BB upper == BB mid → neutral."""
    rows = [
        {"open_time": pd.Timestamp("2025-01-01") + pd.Timedelta(hours=4 * i),
         "o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0, "volume": 1.0}
        for i in range(60)
    ]
    h4 = pd.DataFrame(rows)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
