from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

import pandas as pd


@dataclass(frozen=True, slots=True)
class IntrabarExecutionData:
    """Read-only minute frames used by execution, never by strategy signals."""

    last_1m: pd.DataFrame
    mark_1m: pd.DataFrame


@dataclass(frozen=True, slots=True)
class StrategyData:
    """Richer strategy input for multi-frame or project-aware strategies.

    ``candles_by_timeframe`` is the canonical candle bundle. Components must
    request the timeframe they need instead of relying on a privileged default
    frame.
    """

    candles_by_timeframe: dict[str, pd.DataFrame]
    extras: dict[str, pd.DataFrame]
    metadata: dict[str, Any]
    execution: IntrabarExecutionData | None = None

    def require_timeframe(self, timeframe: str) -> pd.DataFrame:
        """Return a candle frame or raise an explicit missing-data error."""

        key = normalize_timeframe_key(timeframe)
        for existing_key, frame in self.candles_by_timeframe.items():
            if normalize_timeframe_key(existing_key) == key:
                if frame.empty:
                    raise ValueError(f"StrategyData timeframe {timeframe!r} has no candles")
                return frame
        raise ValueError(f"StrategyData timeframe {timeframe!r} is not loaded")

    def optional_timeframe(self, timeframe: str) -> pd.DataFrame:
        """Return a candle frame or an empty frame when the timeframe is absent."""

        key = normalize_timeframe_key(timeframe)
        for existing_key, frame in self.candles_by_timeframe.items():
            if normalize_timeframe_key(existing_key) == key:
                return frame
        return pd.DataFrame()

    def copy(self) -> StrategyData:
        return StrategyData(
            candles_by_timeframe={
                key: value.copy() for key, value in self.candles_by_timeframe.items()
            },
            extras={key: value.copy() for key, value in self.extras.items()},
            metadata=dict(self.metadata),
            execution=self.execution,
        )


StrategyInput: TypeAlias = pd.DataFrame | StrategyData


def select_candle_frame(data: StrategyInput, timeframe: str) -> pd.DataFrame:
    """Return the caller-requested OHLCV frame from plain or bundled input."""

    if isinstance(data, StrategyData):
        return data.require_timeframe(timeframe)
    return data


def normalize_timeframe_key(timeframe: str) -> str:
    value = timeframe.strip().lower()
    aliases = {
        "m1": "1m",
        "1min": "1m",
        "1minute": "1m",
        "m5": "5m",
        "5min": "5m",
        "5minute": "5m",
        "m15": "15m",
        "15min": "15m",
        "15minute": "15m",
        "h1": "1h",
        "1hour": "1h",
        "h4": "4h",
        "4hour": "4h",
        "d1": "1d",
        "1day": "1d",
    }
    return aliases.get(value, value)


def timeframe_minutes(timeframe: str) -> int:
    normalized = normalize_timeframe_key(timeframe)
    values = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
    }
    if normalized not in values:
        raise ValueError(f"Unsupported candle timeframe for minute conversion: {timeframe!r}")
    return values[normalized]


def ttl_minutes_to_bars(ttl_minutes: int, candle_timeframe: str) -> int:
    if ttl_minutes <= 0:
        return 0
    minutes = timeframe_minutes(candle_timeframe)
    return max(1, (ttl_minutes + minutes - 1) // minutes)
