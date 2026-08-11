from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtester.strategy_discovery.events import DiscoveryEvent, Label, LabeledEvent
from backtester.strategy_discovery.features import DiscoveryDataset


@dataclass(frozen=True, slots=True)
class LabelConfig:
    horizon_bars: int = 24
    atr_mult: float = 1.0
    same_bar_policy: Label = "loss"


def label_events(
    *,
    events: list[DiscoveryEvent],
    dataset: DiscoveryDataset,
    config: LabelConfig,
) -> list[LabeledEvent]:
    return [_label_event(event, dataset, config) for event in events]


def _label_event(
    event: DiscoveryEvent,
    dataset: DiscoveryDataset,
    config: LabelConfig,
) -> LabeledEvent:
    df = dataset.ohlcv
    if event.event_time not in df.index:
        return _neutral(event, "event_time_missing", atr=0.0)
    event_position = df.index.get_loc(event.event_time)
    if not isinstance(event_position, int):
        return _neutral(event, "event_time_not_unique", atr=0.0)
    atr_value = dataset.features.loc[event.event_time, "atr"]
    if pd.isna(atr_value) or float(atr_value) <= 0:
        return _neutral(event, "missing_atr", atr=0.0)

    horizon = df.iloc[event_position + 1 : event_position + 1 + config.horizon_bars]
    if horizon.empty:
        return _neutral(event, "no_forward_bars", atr=float(atr_value))

    distance = float(atr_value) * config.atr_mult
    entry = event.entry_reference_price
    if event.side == "long":
        favorable = entry + distance
        adverse = entry - distance
        favorable_hits = horizon["high"] >= favorable
        adverse_hits = horizon["low"] <= adverse
    else:
        favorable = entry - distance
        adverse = entry + distance
        favorable_hits = horizon["low"] <= favorable
        adverse_hits = horizon["high"] >= adverse

    for bar_time in horizon.index:
        hit_favorable = bool(favorable_hits.loc[bar_time])
        hit_adverse = bool(adverse_hits.loc[bar_time])
        if hit_favorable and hit_adverse:
            return LabeledEvent(
                event=event,
                label=config.same_bar_policy,
                label_reason="same_bar_both_barriers",
                favorable_bar_time=pd.Timestamp(bar_time),
                adverse_bar_time=pd.Timestamp(bar_time),
                atr=float(atr_value),
            )
        if hit_favorable:
            return LabeledEvent(
                event=event,
                label="win",
                label_reason="favorable_barrier_first",
                favorable_bar_time=pd.Timestamp(bar_time),
                adverse_bar_time=None,
                atr=float(atr_value),
            )
        if hit_adverse:
            return LabeledEvent(
                event=event,
                label="loss",
                label_reason="adverse_barrier_first",
                favorable_bar_time=None,
                adverse_bar_time=pd.Timestamp(bar_time),
                atr=float(atr_value),
            )

    return _neutral(event, "barrier_not_hit", atr=float(atr_value))


def _neutral(event: DiscoveryEvent, reason: str, *, atr: float) -> LabeledEvent:
    return LabeledEvent(
        event=event,
        label="neutral",
        label_reason=reason,
        favorable_bar_time=None,
        adverse_bar_time=None,
        atr=atr,
    )
