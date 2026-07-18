from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

Side = Literal["long", "short"]
Label = Literal["win", "loss", "neutral"]


@dataclass(frozen=True, slots=True)
class DiscoveryEvent:
    event_time: pd.Timestamp
    side: Side
    trigger_name: str
    entry_reference_price: float
    window_label: str
    symbol: str
    metadata: dict[str, Any]

    @property
    def event_id(self) -> str:
        return (
            f"{self.window_label}|{self.symbol}|{self.trigger_name}|"
            f"{self.event_time.isoformat()}|{self.side}"
        )


@dataclass(frozen=True, slots=True)
class FilterResult:
    passed: bool
    filter_name: str
    reason: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LabeledEvent:
    event: DiscoveryEvent
    label: Label
    label_reason: str
    favorable_bar_time: pd.Timestamp | None
    adverse_bar_time: pd.Timestamp | None
    atr: float


@dataclass(frozen=True, slots=True)
class CandidateKey:
    trigger_name: str
    filter_names: tuple[str, ...]

    @classmethod
    def from_parts(cls, trigger_name: str, filter_names: tuple[str, ...]) -> CandidateKey:
        return cls(trigger_name=trigger_name, filter_names=tuple(sorted(filter_names)))

    @property
    def candidate_id(self) -> str:
        if not self.filter_names:
            return self.trigger_name
        return f"{self.trigger_name}__{'__'.join(self.filter_names)}"
