"""Strategy base contract.

This module intentionally contains only the shared strategy interface.
Concrete implementations live in :mod:`backtester.strategies`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyInput


class BaseStrategy(ABC):
    """Base interface for all strategies.

    Parameters
    ----------
    params:
        Strategy-specific parameters (typically sourced from JSON configs or Optuna
        trials).
    """

    def __init__(self, params: dict[str, Any]):
        self.params = params

    @abstractmethod
    def generate(self, data: StrategyInput) -> pd.DataFrame:
        """Generate trading signals for the given OHLCV frame.

        Parameters
        ----------
        data:
            Input OHLCV data indexed by timestamp, or StrategyData for richer
            project-aware strategies.

            Notes
            -----
            Implementations are allowed to mutate ``df`` in-place and return it.

        Returns
        -------
        pd.DataFrame
            Output frame that must include the mandatory columns listed in
            :data:`REQUIRED_SIGNAL_COLUMNS`:

            - ``signal`` : int
                Entry intent. Allowed values are ``-1`` (short), ``0`` (no
                signal), ``1`` (long).
            - ``sl_price`` : float
                Stop-loss price for the signal. For rows where ``signal == 0``,
                ``sl_price`` may be left as ``0.0`` or ``NaN``.

            Optionally, a strategy may add the columns listed in
            :data:`OPTIONAL_RISK_COLUMNS` to override execution risk settings on
            a per-signal basis (supported by the execution engine if present):

            - ``risk_percent`` : float, optional
                Risk per trade in percent units (e.g. ``1.0`` means 1%).
            - ``rrr`` : float, optional
                Reward/Risk ratio used to compute take-profit from SL distance.
            - ``position_ttl_bars`` : int, optional
                Maximum holding period for positions opened by this signal.
            - ``trail_activation_rrr`` / ``trail_distance_atr`` : float, optional
                Per-signal trailing-stop settings.
            - ``exit_geometry`` / ``tp_move_pct`` / ``structural_sl_mode`` :
                optional per-signal exit-placement settings.
            - ``position_group`` / ``drain_on_group_change`` : optional
                Group-aware handoff controls for composite strategies.

            The returned frame must have the same index and number of rows as
            the input ``df``.
        """

    @abstractmethod
    def suggest_params(self, trial: optuna.Trial) -> dict:
        """Suggest strategy parameters for Optuna optimization."""
