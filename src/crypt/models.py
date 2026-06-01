from __future__ import annotations

import dataclasses
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Timeframe(StrEnum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class Regime(StrEnum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    HIGH_VOL = "HIGH_VOL"


Direction = Literal["bullish", "bearish", "neutral"]
Decision = Literal["BUY", "SELL", "HOLD"]
VolRegime = Literal["low", "normal", "high"]


# ---------------------------------------------------------------------------
# Raw exchange snapshots (Pydantic — validated on ingestion)
# ---------------------------------------------------------------------------


class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe
    open_time: datetime
    o: Decimal
    h: Decimal
    low: Decimal
    c: Decimal
    volume: Decimal
    closed: bool = True


class FundingSnapshot(BaseModel):
    symbol: str
    ts: datetime
    rate: Decimal
    next_fund_time: datetime | None = None


class OISnapshot(BaseModel):
    symbol: str
    ts: datetime
    oi: Decimal


class LongShortRatioSnapshot(BaseModel):
    symbol: str
    ts: datetime
    long_ratio: float
    short_ratio: float


class TakerVolumeSnapshot(BaseModel):
    symbol: str
    ts: datetime
    buy_vol: Decimal
    sell_vol: Decimal


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


class Signal(BaseModel):
    engine: str
    symbol: str
    direction: Direction
    strength: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    inputs_missing: list[str] = Field(default_factory=list)
    # Subset of inputs_missing that are critical for this engine's output.
    # Populated by BaseEngine._signal / _neutral from each engine's
    # critical_inputs ClassVar. Used by DecisionFilter to downgrade verdicts
    # whose primary data dependency is absent.
    critical_missing: list[str] = Field(default_factory=list)
    meta: dict[str, object] = Field(default_factory=dict)
    produced_at: datetime


# ---------------------------------------------------------------------------
# Aggregator output
# ---------------------------------------------------------------------------


class Verdict(BaseModel):
    symbol: str
    decision: Decision
    confidence: int = Field(ge=0, le=100)
    score: float = Field(ge=-1.0, le=1.0)
    regime: Regime
    breakdown: list[Signal]
    rationale: str
    produced_at: datetime


# ---------------------------------------------------------------------------
# Evaluation context (per symbol, per tick)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class EvaluationContext:
    """
    Immutable snapshot of all data available for one symbol at one tick.

    ``candles`` maps each Timeframe to a closed-candle DataFrame with columns:
    ``open_time, o, h, l, c, volume`` (all float64 except open_time=datetime64).
    Only closed candles are stored; engines must NOT drop the last row themselves.
    """

    symbol: str
    tick_time: datetime

    # Keyed by Timeframe; may be empty/missing for a given timeframe.
    candles: dict[Timeframe, pd.DataFrame]

    # Open interest: 1h bars, oldest first. None if fetch failed.
    oi: list[OISnapshot] | None

    # Top-trader long/short ratio: hourly, oldest first. None if fetch failed.
    ls_ratio: list[LongShortRatioSnapshot] | None

    # Taker buy/sell volume: hourly, oldest first. None if fetch failed.
    taker_volume: list[TakerVolumeSnapshot] | None

    # Set by the volatility engine before the regime engine runs.
    vol_regime: VolRegime | None = None
