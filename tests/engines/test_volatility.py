from __future__ import annotations

from datetime import UTC

import pandas as pd

from crypt.engines.volatility import VolatilityEngine
from tests.conftest import make_ctx, make_sideways_h4

engine = VolatilityEngine()


def test_stable_vol_emits_neutral_direction() -> None:
    """Volatility engine always emits neutral direction regardless of vol regime."""
    h4 = make_sideways_h4(210)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert sig.strength == 0.0
    assert sig.meta.get("vol_regime") in ("low", "normal", "high")


def test_very_stable_vol_low_or_normal() -> None:
    """Series with perfectly uniform 0.5% range → low or normal vol regime."""
    from datetime import datetime, timedelta

    import pandas as pd

    rows = []
    c = 100.0
    t = datetime(2025, 1, 1, tzinfo=UTC)
    for i in range(210):
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": c,
                "h": c * 1.005,
                "l": c * 0.995,
                "c": c,
                "volume": 1.0,
            }
        )
    h4 = pd.DataFrame(rows)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert sig.meta.get("vol_regime") in ("low", "normal")


def test_vol_spike_at_end_high() -> None:
    """Series where the last 10 bars have 10x normal ATR → should be 'high'."""

    rows = []
    base_c = 100.0
    c = base_c
    from datetime import datetime, timedelta

    t = datetime(2025, 1, 1, tzinfo=UTC)
    # 350 candles of stable 0.5% range.
    for i in range(350):
        h = c * 1.005
        lo = c * 0.995
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": c,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 1.0,
            }
        )
    # 10 candles of 5% range.
    for i in range(10):
        h = c * 1.05
        lo = c * 0.95
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * (350 + i)),
                "o": c,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 1.0,
            }
        )

    h4 = pd.DataFrame(rows)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.meta.get("vol_regime") == "high", f"Expected high, got {sig.meta}"


def test_insufficient_history_normal() -> None:
    h4 = make_sideways_h4(30)
    ctx = make_ctx(h4=h4)
    sig = engine.evaluate(ctx)
    assert sig.meta.get("vol_regime") == "normal"
    assert "candles[H4]" in sig.inputs_missing


def test_no_candles() -> None:
    ctx = make_ctx()
    sig = engine.evaluate(ctx)
    assert sig.meta.get("vol_regime") == "normal"
