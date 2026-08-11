"""Generic incremental-strategy adapter contract and registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from backtester.data_contracts import StrategyInput
from backtester.strategy_discovery.features import DiscoveryDataset


@dataclass(frozen=True, slots=True)
class IncrementalStrategyConfig:
    """Configuration passed to a registered strategy-type adapter."""

    strategy_id: str
    params: dict[str, Any]
    execution: Any


class IncrementalStrategyAdapter(Protocol):
    """Strategy-type plugin consumed by the generic router runtime."""

    def prepare_replay(
        self,
        *,
        data: StrategyInput,
        dataset: DiscoveryDataset,
        config: IncrementalStrategyConfig,
    ) -> pd.DataFrame:
        """Return a causal signal frame indexed like the supplied candles."""


AdapterFactory = Callable[[], IncrementalStrategyAdapter]
_ADAPTERS: dict[str, AdapterFactory] = {}


def register_incremental_adapter(
    strategy_name: str,
    factory: AdapterFactory,
) -> None:
    """Register one adapter for a strategy class, not a strategy instance."""

    if not strategy_name:
        raise ValueError("strategy_name must not be empty")
    _ADAPTERS[strategy_name] = factory


def build_incremental_adapter(strategy_name: str) -> IncrementalStrategyAdapter:
    """Build the adapter registered for a strategy config's ``name``."""

    factory = _ADAPTERS.get(strategy_name)
    if factory is None:
        available = ", ".join(sorted(_ADAPTERS))
        raise ValueError(
            f"No incremental adapter registered for {strategy_name!r}. Available: {available}"
        )
    return factory()
