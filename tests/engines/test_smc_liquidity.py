from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from crypt.engines.smc_liquidity import SMCLiquidityEngine
from tests.conftest import make_ctx


def _equal_high_sweep_candles() -> pd.DataFrame:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(75):
        open_ = 100.0
        close = 100.0
        high = 102.0
        low = 98.0
        if i == 45:
            open_ = 103.0
            close = 104.0
            high = 110.0
            low = 99.0
        elif 46 <= i <= 50:
            high = 103.0
            low = 97.0
        elif i == 55:
            open_ = 103.0
            close = 104.0
            high = 110.2
            low = 99.0
        elif 56 <= i <= 60:
            high = 103.0
            low = 97.0
        elif i == 62:
            open_ = 108.5
            close = 107.0
            high = 112.0
            low = 106.0
        rows.append(
            {
                "open_time": t0 + timedelta(hours=4 * i),
                "o": open_,
                "h": high,
                "l": low,
                "c": close,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def _equal_low_sweep_candles() -> pd.DataFrame:
    df = _equal_high_sweep_candles()
    for idx in range(len(df)):
        df.loc[idx, ["o", "h", "l", "c"]] = [100.0, 102.0, 98.0, 100.0]
    for idx in (45, 55):
        df.loc[idx, ["o", "h", "l", "c"]] = [97.0, 101.0, 90.0 + (0.2 if idx == 55 else 0.0), 96.0]
    for idx in range(46, 51):
        df.loc[idx, ["h", "l"]] = [103.0, 97.0]
    for idx in range(56, 61):
        df.loc[idx, ["h", "l"]] = [103.0, 97.0]
    df.loc[62, ["o", "h", "l", "c"]] = [91.5, 94.0, 88.0, 93.0]
    return df


def test_smc_liquidity_equal_high_sweep_emits_bearish() -> None:
    h4 = _equal_high_sweep_candles()
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[62] + timedelta(hours=4)

    sig = SMCLiquidityEngine().evaluate(ctx)

    assert sig.direction == "bearish"
    assert sig.strength < 0
    assert sig.confidence > 0
    assert sig.meta["level_type"] == "equal"


def test_smc_liquidity_no_signal_before_sweep_close() -> None:
    h4 = _equal_high_sweep_candles()
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[62]

    sig = SMCLiquidityEngine().evaluate(ctx)

    assert sig.direction == "neutral"


def test_smc_liquidity_equal_low_sweep_emits_bullish() -> None:
    h4 = _equal_low_sweep_candles()
    ctx = make_ctx(h4=h4)
    ctx.tick_time = h4["open_time"].iloc[62] + timedelta(hours=4)

    sig = SMCLiquidityEngine().evaluate(ctx)

    assert sig.direction == "bullish"
    assert sig.strength > 0
    assert sig.meta["level_type"] == "equal"


def test_smc_liquidity_missing_h4_neutral() -> None:
    sig = SMCLiquidityEngine().evaluate(make_ctx())

    assert sig.direction == "neutral"
    assert "candles[H4]" in sig.inputs_missing
