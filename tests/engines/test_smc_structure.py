from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from crypt.engines.smc_structure import SMCStructureEngine
from tests.conftest import make_ctx


def _engine_bos_candles() -> pd.DataFrame:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(70):
        close = 100.0
        high = 102.0
        low = 98.0
        if i == 55:
            close = 104.0
            high = 110.0
            low = 99.0
        elif 56 <= i <= 63:
            close = 100.0
            high = 105.0
            low = 97.0
        elif i == 64:
            close = 111.0
            high = 112.0
            low = 100.0
        rows.append(
            {
                "open_time": t0 + timedelta(hours=4 * i),
                "o": close,
                "h": high,
                "l": low,
                "c": close,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def test_smc_structure_bullish_bos_signal() -> None:
    h4 = _engine_bos_candles()
    tick_time = h4["open_time"].iloc[64] + timedelta(hours=4)
    ctx = make_ctx(h4=h4)
    ctx.tick_time = tick_time

    sig = SMCStructureEngine().evaluate(ctx)

    assert sig.direction == "bullish"
    assert sig.strength > 0
    assert sig.meta["event_type"] == "BOS"


def test_smc_structure_no_lookahead_before_break_close() -> None:
    h4 = _engine_bos_candles()
    tick_time = h4["open_time"].iloc[63] + timedelta(hours=4)
    ctx = make_ctx(h4=h4)
    ctx.tick_time = tick_time

    sig = SMCStructureEngine().evaluate(ctx)

    assert sig.direction == "neutral"


def test_smc_structure_missing_h4_neutral() -> None:
    sig = SMCStructureEngine().evaluate(make_ctx())

    assert sig.direction == "neutral"
    assert "candles[H4]" in sig.inputs_missing
