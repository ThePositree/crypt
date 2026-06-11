"""DSSStrategy — registered backtester strategy that replays a DSS TrialConfig.

Used by ``compare-fixed``, ``walk-forward``, and ``optimize`` when the candidate
JSON references ``"name": "dss_strategy"``.

Params dict (from candidate JSON ``params`` key) must contain all fields of
TrialConfig: trigger_name, trigger_params, filter_names, filter_params,
rrr, risk_percent, position_ttl_bars, atr_sl_mult.
"""

from __future__ import annotations

import logging
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyInput
from backtester.strategy import BaseStrategy
from backtester.strategy_discovery.dss_config import TrialConfig
from backtester.strategy_discovery.signal_composer import (
    SignalComposer,
    signal_df_to_ohlcv_aligned,
)

logger = logging.getLogger(__name__)


class DSSStrategy(BaseStrategy):
    """Replay a DSS trial config as a donor-compatible strategy.

    The strategy generates signals using the parameterized trigger + filter
    stack from ``TrialConfig`` and converts them to the OHLCV-aligned format
    expected by ``ExecutionSim``.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self._config = TrialConfig.from_dict(params)
        self._composer = SignalComposer()
        self._generate_fn = self._composer.build(self._config)

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        from backtester.data_contracts import StrategyData

        primary = data.primary if isinstance(data, StrategyData) else data

        try:
            signal_df = self._generate_fn(data)
        except Exception:
            logger.warning("DSSStrategy.generate() failed; returning zero signals", exc_info=True)
            return pd.DataFrame(
                {"signal": 0, "sl_price": 0.0},
                index=primary.index,
            )

        return signal_df_to_ohlcv_aligned(signal_df, primary)

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:  # noqa: ARG002
        """DSS strategy parameters are fixed; no Optuna suggestions."""
        return {}
