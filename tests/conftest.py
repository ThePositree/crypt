"""Shared pytest fixtures and synthetic data helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from crypt.models import (
    EvaluationContext,
    FundingSnapshot,
    LongShortRatioSnapshot,
    OISnapshot,
    Timeframe,
)

# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------


def make_trending_up_h4(n: int = 210) -> pd.DataFrame:
    """Steady uptrend: +0.5% per candle, low noise."""
    base = 100.0
    prices = [base * (1.005**i) for i in range(n)]
    rows = []
    t = datetime(2025, 1, 1, tzinfo=UTC)
    for i, c in enumerate(prices):
        o = prices[i - 1] if i > 0 else c * 0.995
        h = c * 1.003
        lo = c * 0.997
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": o,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def make_trending_down_h4(n: int = 210) -> pd.DataFrame:
    """Steady downtrend: -0.5% per candle."""
    base = 200.0
    prices = [base * (0.995**i) for i in range(n)]
    rows = []
    t = datetime(2025, 1, 1, tzinfo=UTC)
    for i, c in enumerate(prices):
        o = prices[i - 1] if i > 0 else c * 1.005
        h = c * 1.003
        lo = c * 0.997
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": o,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def make_sideways_h4(n: int = 210) -> pd.DataFrame:
    """Flat oscillating price — low ADX, no trend."""
    rng = np.random.default_rng(42)
    base = 100.0
    rows = []
    t = datetime(2025, 1, 1, tzinfo=UTC)
    c = base
    for i in range(n):
        c = base + rng.uniform(-0.5, 0.5)
        h = c + abs(rng.normal(0, 0.2))
        lo = c - abs(rng.normal(0, 0.2))
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": c,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 500.0,
            }
        )
    return pd.DataFrame(rows)


def make_oversold_h4() -> pd.DataFrame:
    """Sharp crash then flat — RSI should be below 30."""
    rows = []
    t = datetime(2025, 1, 1, tzinfo=UTC)
    c = 100.0
    for i in range(40):
        h, lo = c * 1.002, c * 0.998
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": c,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 1000.0,
            }
        )
    for i in range(20):
        c *= 0.975  # -2.5% per candle
        h, lo = c * 1.002, c * 0.998
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * (40 + i)),
                "o": c,
                "h": h,
                "l": lo,
                "c": c,
                "volume": 2000.0,
            }
        )
    return pd.DataFrame(rows)


def make_overbought_h4() -> pd.DataFrame:
    """Sharp rally then flat — RSI should be above 70."""
    rows = []
    t = datetime(2025, 1, 1, tzinfo=UTC)
    c = 100.0
    for i in range(40):
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * i),
                "o": c,
                "h": c * 1.002,
                "l": c * 0.998,
                "c": c,
                "volume": 1000.0,
            }
        )
    for i in range(20):
        c *= 1.025  # +2.5% per candle
        rows.append(
            {
                "open_time": t + timedelta(hours=4 * (40 + i)),
                "o": c,
                "h": c * 1.002,
                "l": c * 0.998,
                "c": c,
                "volume": 2000.0,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def make_ctx(
    symbol: str = "BTC-USDT-SWAP",
    h4: pd.DataFrame | None = None,
    d1: pd.DataFrame | None = None,
    funding: list[FundingSnapshot] | None = None,
    oi: list[OISnapshot] | None = None,
    ls_ratio: list[LongShortRatioSnapshot] | None = None,
) -> EvaluationContext:
    candles = {}
    if h4 is not None:
        candles[Timeframe.H4] = h4
    if d1 is not None:
        candles[Timeframe.D1] = d1
    return EvaluationContext(
        symbol=symbol,
        tick_time=datetime.now(tz=UTC),
        candles=candles,
        funding=funding,
        oi=oi,
        ls_ratio=ls_ratio,
        taker_volume=None,
    )
