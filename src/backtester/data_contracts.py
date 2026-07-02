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
    """Richer strategy input for multi-frame or project-aware strategies."""

    primary: pd.DataFrame
    candles: dict[str, pd.DataFrame]
    extras: dict[str, pd.DataFrame]
    metadata: dict[str, Any]
    execution: IntrabarExecutionData | None = None

    def copy(self) -> StrategyData:
        return StrategyData(
            primary=self.primary.copy(),
            candles={key: value.copy() for key, value in self.candles.items()},
            extras={key: value.copy() for key, value in self.extras.items()},
            metadata=dict(self.metadata),
            execution=self.execution,
        )


StrategyInput: TypeAlias = pd.DataFrame | StrategyData
