"""Incremental adapter for declarative DSS strategy configurations."""

from __future__ import annotations

import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.incremental_strategy import (
    IncrementalStrategyConfig,
    register_incremental_adapter,
)
from backtester.strategies.dss_strategy import apply_default_dss_execution_stops
from backtester.strategy_discovery.dss_config import (
    DSS_DEFAULT_DIRECTIONAL_SL_MOVE_PCT,
    TrialConfig,
)
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
        trial = TrialConfig.from_dict(config.params)
        primary = (
            data.require_timeframe(trial.trigger_instance.timeframe)
            if isinstance(data, StrategyData)
            else data
        )
        rows = SignalComposer().generate_from_dataset(trial, dataset)
        aligned = signal_df_to_ohlcv_aligned(rows, primary)
        fallback_stop_pct = float(
            config.params.get(
                "directional_sl_move_pct",
                config.params.get("sl_pct", DSS_DEFAULT_DIRECTIONAL_SL_MOVE_PCT),
            )
        )
        raw_atr_sl_mult = config.params.get("atr_sl_mult")
        atr_sl_mult = float(raw_atr_sl_mult) if raw_atr_sl_mult is not None else None
        apply_default_dss_execution_stops(
            aligned,
            primary,
            fallback_stop_pct,
            atr_sl_mult=atr_sl_mult,
        )
        return aligned


register_incremental_adapter("dss_strategy", DSSIncrementalAdapter)
