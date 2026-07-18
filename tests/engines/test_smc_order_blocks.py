from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from crypt.engines.smc_order_blocks import SMCOrderBlocksEngine
from tests.conftest import make_ctx


def _bullish_retest_candles(*, mitigate: bool = False) -> pd.DataFrame:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(70):
        close = 100.0
        high = 102.0
        low = 98.0
        if i == 55:
            close = 102.0
            high = 106.0
            low = 100.0
        elif 56 <= i <= 60:
            close = 100.0
            high = 101.0
            low = 99.0
        elif i == 61:
            close = 107.0
            high = 108.0
            low = 103.0
        elif 62 <= i <= 64:
            close = 104.0
            high = 105.0
            low = 102.0
        elif i == 65:
            close = 102.0
            high = 103.0
            low = 100.0
        if mitigate and i == 62:
            close = 101.0
            high = 104.0
            low = 98.5
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


def test_smc_order_blocks_bullish_retest_signal() -> None:
    h4 = _bullish_retest_candles()
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[65] + timedelta(hours=4)

    sig = SMCOrderBlocksEngine().evaluate(ctx)

    assert sig.direction == "bullish"
    assert sig.strength > 0
    assert sig.confidence > 0
    assert sig.meta["zone_low"] == 99.0
    assert sig.meta["zone_high"] == 101.0


def test_smc_order_blocks_no_signal_before_retest_close() -> None:
    h4 = _bullish_retest_candles()
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[64] + timedelta(hours=4)

    sig = SMCOrderBlocksEngine().evaluate(ctx)

    assert sig.direction == "neutral"


def test_smc_order_blocks_mitigated_block_ignored() -> None:
    h4 = _bullish_retest_candles(mitigate=True)
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[65] + timedelta(hours=4)

    sig = SMCOrderBlocksEngine().evaluate(ctx)

    assert sig.direction == "neutral"


def test_smc_order_blocks_missing_h4_neutral() -> None:
    sig = SMCOrderBlocksEngine().evaluate(make_ctx())

    assert sig.direction == "neutral"
    assert "candles[H4]" in sig.inputs_missing
