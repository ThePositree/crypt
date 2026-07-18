"""Incremental adapter for declarative DSS strategy configurations."""

from __future__ import annotations

import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.incremental_strategy import (
    IncrementalStrategyConfig,
    register_incremental_adapter,
)
from backtester.strategy_discovery.dss_config import TrialConfig
from backtester.strategy_discovery.features import DiscoveryDataset
from backtester.strategy_discovery.signal_composer import (
    SignalComposer,
    signal_df_to_ohlcv_aligned,
)


class DSSIncrementalAdapter:
    """Evaluate any DSS config against the shared causal feature dataset."""

    def prepare_replay(
        self,
        *,
        data: StrategyInput,
        dataset: DiscoveryDataset,
        config: IncrementalStrategyConfig,
    ) -> pd.DataFrame:
        primary = data.primary if isinstance(data, StrategyData) else data
        trial = TrialConfig.from_dict(config.params)
        rows = SignalComposer().generate_from_dataset(trial, dataset)
        return signal_df_to_ohlcv_aligned(rows, primary)


register_incremental_adapter("dss_strategy", DSSIncrementalAdapter)
