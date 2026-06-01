from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd

BULLISH = 1
BEARISH = -1

PivotKind = Literal["swing", "internal"]
PivotSide = Literal["high", "low"]
StructureType = Literal["BOS", "CHOCH"]


@dataclass(frozen=True)
class SMCPivot:
    kind: PivotKind
    side: PivotSide
    level: float
    pivot_time: datetime
    known_at: datetime
    index: int
    crossed: bool = False


@dataclass(frozen=True)
class SMCStructureEvent:
    kind: PivotKind
    event_type: StructureType
    direction: int
    level: float
    event_time: datetime
    known_at: datetime
    pivot: SMCPivot


@dataclass(frozen=True)
class SMCOrderBlock:
    kind: PivotKind
    direction: int
    low: float
    high: float
    origin_time: datetime
    known_at: datetime
    source_event: SMCStructureEvent
    active: bool = True
    mitigated_at: datetime | None = None


@dataclass(frozen=True)
class SMCState:
    swing_bias: int = 0
    internal_bias: int = 0
    pivots: list[SMCPivot] = field(default_factory=list)
    structure_events: list[SMCStructureEvent] = field(default_factory=list)
    order_blocks: list[SMCOrderBlock] = field(default_factory=list)


@dataclass
class _MutablePivot:
    kind: PivotKind
    side: PivotSide
    level: float
    pivot_time: datetime
    known_at: datetime
    index: int
    crossed: bool = False

    def frozen(self) -> SMCPivot:
        return SMCPivot(
            kind=self.kind,
            side=self.side,
            level=self.level,
            pivot_time=self.pivot_time,
            known_at=self.known_at,
            index=self.index,
            crossed=self.crossed,
        )


@dataclass
class _MutableOrderBlock:
    kind: PivotKind
    direction: int
    low: float
    high: float
    origin_time: datetime
    known_at: datetime
    source_event: SMCStructureEvent
    active: bool = True
    mitigated_at: datetime | None = None

    def frozen(self) -> SMCOrderBlock:
        return SMCOrderBlock(
            kind=self.kind,
            direction=self.direction,
            low=self.low,
            high=self.high,
            origin_time=self.origin_time,
            known_at=self.known_at,
            source_event=self.source_event,
            active=self.active,
            mitigated_at=self.mitigated_at,
        )


def analyse_smc(
    candles: pd.DataFrame,
    *,
    tick_time: datetime | None = None,
    swing_length: int = 50,
    internal_length: int = 5,
) -> SMCState:
    """
    Analyse closed candles into SMC structure events.

    The implementation is deliberately explicit rather than vectorised so the
    known-at timing is auditable. A pivot at candle j is only emitted when the
    confirmation candle j + length has closed.
    """
    if candles.empty:
        return SMCState()

    df = _normalise_candles(candles)
    if tick_time is not None:
        df = df[df["known_at"] <= pd.Timestamp(tick_time)]
    if df.empty:
        return SMCState()

    state = _AnalyzerState()
    for i in range(len(df)):
        _update_pivots(df, i, internal_length, "internal", state)
        _update_pivots(df, i, swing_length, "swing", state)
        _update_order_block_mitigation(df, i, state)
        _update_structure(df, i, "internal", state)
        _update_structure(df, i, "swing", state)

    return SMCState(
        swing_bias=state.swing_bias,
        internal_bias=state.internal_bias,
        pivots=state.pivots,
        structure_events=state.structure_events,
        order_blocks=[ob.frozen() for ob in state.order_blocks],
    )


class _AnalyzerState:
    def __init__(self) -> None:
        self.swing_high: _MutablePivot | None = None
        self.swing_low: _MutablePivot | None = None
        self.internal_high: _MutablePivot | None = None
        self.internal_low: _MutablePivot | None = None
        self.swing_bias = 0
        self.internal_bias = 0
        self.pivots: list[SMCPivot] = []
        self.structure_events: list[SMCStructureEvent] = []
        self.order_blocks: list[_MutableOrderBlock] = []

    def get_pivot(self, kind: PivotKind, side: PivotSide) -> _MutablePivot | None:
        if kind == "swing" and side == "high":
            return self.swing_high
        if kind == "swing" and side == "low":
            return self.swing_low
        if kind == "internal" and side == "high":
            return self.internal_high
        return self.internal_low

    def set_pivot(self, pivot: _MutablePivot) -> None:
        if pivot.kind == "swing" and pivot.side == "high":
            self.swing_high = pivot
        elif pivot.kind == "swing" and pivot.side == "low":
            self.swing_low = pivot
        elif pivot.kind == "internal" and pivot.side == "high":
            self.internal_high = pivot
        else:
            self.internal_low = pivot
        self.pivots.append(pivot.frozen())

    def bias(self, kind: PivotKind) -> int:
        return self.swing_bias if kind == "swing" else self.internal_bias

    def set_bias(self, kind: PivotKind, bias: int) -> None:
        if kind == "swing":
            self.swing_bias = bias
        else:
            self.internal_bias = bias


def _normalise_candles(candles: pd.DataFrame) -> pd.DataFrame:
    required = ["open_time", "o", "h", "l", "c"]
    missing = [col for col in required if col not in candles.columns]
    if missing:
        return pd.DataFrame(columns=[*required, "known_at"])

    df = candles[required].copy()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.sort_values("open_time").drop_duplicates("open_time", keep="last")
    for col in ["o", "h", "l", "c"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open_time", "o", "h", "l", "c"]).reset_index(drop=True)

    delta = _infer_bar_delta(df["open_time"])
    df["known_at"] = df["open_time"] + delta
    return df


def _infer_bar_delta(times: pd.Series) -> pd.Timedelta:
    if len(times) >= 2:
        diffs = times.diff().dropna()
        if not diffs.empty:
            return diffs.mode().iloc[0]
    return pd.Timedelta(timedelta(hours=4))


def _update_pivots(
    df: pd.DataFrame,
    i: int,
    length: int,
    kind: PivotKind,
    state: _AnalyzerState,
) -> None:
    if length <= 0 or i < length * 2:
        return

    j = i - length
    candidate_high = float(df.at[j, "h"])
    candidate_low = float(df.at[j, "l"])
    left_high = df.loc[j - length : j - 1, "h"]
    left_low = df.loc[j - length : j - 1, "l"]
    right_high = df.loc[j + 1 : i, "h"]
    right_low = df.loc[j + 1 : i, "l"]
    if left_high.empty or left_low.empty or right_high.empty or right_low.empty:
        return

    known_at = df.at[i, "known_at"].to_pydatetime()
    pivot_time = df.at[j, "open_time"].to_pydatetime()

    if candidate_high > float(left_high.max()) and candidate_high > float(right_high.max()):
        state.set_pivot(
            _MutablePivot(
                kind=kind,
                side="high",
                level=candidate_high,
                pivot_time=pivot_time,
                known_at=known_at,
                index=j,
            )
        )
    if candidate_low < float(left_low.min()) and candidate_low < float(right_low.min()):
        state.set_pivot(
            _MutablePivot(
                kind=kind,
                side="low",
                level=candidate_low,
                pivot_time=pivot_time,
                known_at=known_at,
                index=j,
            )
        )


def _update_structure(
    df: pd.DataFrame,
    i: int,
    kind: PivotKind,
    state: _AnalyzerState,
) -> None:
    close = float(df.at[i, "c"])
    prev_close = float(df.at[i - 1, "c"]) if i > 0 else close
    event_time = df.at[i, "open_time"].to_pydatetime()
    known_at = df.at[i, "known_at"].to_pydatetime()

    high_pivot = state.get_pivot(kind, "high")
    if (
        high_pivot is not None
        and not high_pivot.crossed
        and prev_close <= high_pivot.level
        and close > high_pivot.level
    ):
        event_type: StructureType = "CHOCH" if state.bias(kind) == BEARISH else "BOS"
        high_pivot.crossed = True
        state.set_bias(kind, BULLISH)
        event = SMCStructureEvent(
            kind=kind,
            event_type=event_type,
            direction=BULLISH,
            level=high_pivot.level,
            event_time=event_time,
            known_at=known_at,
            pivot=high_pivot.frozen(),
        )
        state.structure_events.append(event)
        _create_order_block(df, i, event, state)

    low_pivot = state.get_pivot(kind, "low")
    if (
        low_pivot is not None
        and not low_pivot.crossed
        and prev_close >= low_pivot.level
        and close < low_pivot.level
    ):
        event_type = "CHOCH" if state.bias(kind) == BULLISH else "BOS"
        low_pivot.crossed = True
        state.set_bias(kind, BEARISH)
        event = SMCStructureEvent(
            kind=kind,
            event_type=event_type,
            direction=BEARISH,
            level=low_pivot.level,
            event_time=event_time,
            known_at=known_at,
            pivot=low_pivot.frozen(),
        )
        state.structure_events.append(event)
        _create_order_block(df, i, event, state)


def _create_order_block(
    df: pd.DataFrame,
    break_index: int,
    event: SMCStructureEvent,
    state: _AnalyzerState,
) -> None:
    start = min(event.pivot.index, break_index)
    end = max(event.pivot.index, break_index)
    window = df.loc[start:end].copy()
    if window.empty:
        return

    window = _with_parsed_order_block_bounds(window, df)
    if event.direction == BULLISH:
        origin_idx = window["parsed_l"].astype(float).idxmin()
    else:
        origin_idx = window["parsed_h"].astype(float).idxmax()

    low = float(min(window.at[origin_idx, "parsed_l"], window.at[origin_idx, "parsed_h"]))
    high = float(max(window.at[origin_idx, "parsed_l"], window.at[origin_idx, "parsed_h"]))
    if low >= high:
        return

    state.order_blocks.append(
        _MutableOrderBlock(
            kind=event.kind,
            direction=event.direction,
            low=low,
            high=high,
            origin_time=df.at[origin_idx, "open_time"].to_pydatetime(),
            known_at=event.known_at,
            source_event=event,
        )
    )


def _with_parsed_order_block_bounds(window: pd.DataFrame, full_df: pd.DataFrame) -> pd.DataFrame:
    result = window.copy()
    result["parsed_h"] = result["h"]
    result["parsed_l"] = result["l"]

    tr = _true_range(full_df)
    volatility = tr.rolling(window=200, min_periods=1).mean()
    for idx in result.index:
        candle_range = float(result.at[idx, "h"] - result.at[idx, "l"])
        vol = float(volatility.loc[idx]) if idx in volatility.index else 0.0
        if vol > 0 and candle_range >= 2.0 * vol:
            result.at[idx, "parsed_h"] = max(float(result.at[idx, "o"]), float(result.at[idx, "c"]))
            result.at[idx, "parsed_l"] = min(float(result.at[idx, "o"]), float(result.at[idx, "c"]))
    return result


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["h"].astype(float)
    low = df["l"].astype(float)
    close = df["c"].astype(float)
    prev_close = close.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _update_order_block_mitigation(
    df: pd.DataFrame,
    i: int,
    state: _AnalyzerState,
) -> None:
    low = float(df.at[i, "l"])
    high = float(df.at[i, "h"])
    known_at = df.at[i, "known_at"].to_pydatetime()
    for block in state.order_blocks:
        if not block.active or block.known_at >= known_at:
            continue
        if (block.direction == BULLISH and low < block.low) or (
            block.direction == BEARISH and high > block.high
        ):
            block.active = False
            block.mitigated_at = known_at
