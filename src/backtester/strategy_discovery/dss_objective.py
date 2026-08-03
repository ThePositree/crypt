"""DSSObjective — multi-objective Optuna objective for Direct Signal Search.

Each call returns a tuple of mandate_score values, one per window.
The NSGAIISampler maximizes all objectives simultaneously, finding a Pareto
front of regime-robust configurations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import optuna
import pandas as pd

from backtester.mandate_report import (
    MONTHLY_DD_LIMIT_PCT,
    RETURN_FLOOR_PCT,
    build_mandate_report,
)
from backtester.strategy_discovery.dss_cache import DSSSignalCache
from backtester.strategy_discovery.dss_config import (
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    ParamValue,
    TrialConfig,
)
from backtester.strategy_discovery.features import select_timeframe_frame
from backtester.strategy_discovery.signal_composer import SignalComposer, signal_df_to_ohlcv_aligned
from backtester.tester import Backtester

if TYPE_CHECKING:
    from backtester.data_contracts import StrategyData

logger = logging.getLogger(__name__)

_EMPTY_SIGNAL_PENALTY = -10_000.0
_BACKTEST_ERROR_PENALTY = -5_000.0


# ---------------------------------------------------------------------------
# mandate_score computation
# ---------------------------------------------------------------------------


def compute_mandate_score(
    trades: pd.DataFrame,
    *,
    initial_capital: float,
    start: str,
    end: str,
) -> float:
    """Compute mandate_score from a trades DataFrame.

    Identical formula to optimizer._mandate_score (ADR-0031).
    Returns ``_BACKTEST_ERROR_PENALTY`` on any error so failed trials don't
    block the Optuna study.
    """
    if trades.empty:
        return _EMPTY_SIGNAL_PENALTY

    try:
        report = build_mandate_report(
            trades,
            initial_capital=initial_capital,
            start=start,
            end=end,
        )
    except Exception:
        logger.debug("build_mandate_report failed", exc_info=True)
        return _BACKTEST_ERROR_PENALTY

    monthly = report.monthly
    summary_row = report.summary.iloc[0].to_dict() if not report.summary.empty else {}
    if monthly.empty:
        return _EMPTY_SIGNAL_PENALTY

    raw = pd.to_numeric(monthly["raw_monthly_return_pct"], errors="coerce").fillna(0.0)
    drawdowns = pd.to_numeric(monthly["max_drawdown_pct"], errors="coerce").fillna(0.0)

    monthly_shortfall_pct = float((RETURN_FLOOR_PCT - raw).clip(lower=0.0).sum())
    dd_excess_pct = float((MONTHLY_DD_LIMIT_PCT - drawdowns).clip(lower=0.0).sum())
    sum_capped = float(summary_row.get("sum_capped_monthly_return_pct", 0.0))
    months_below = int(summary_row.get("months_below_floor", 0))
    dd_breach_months = int(summary_row.get("dd_breach_months", 0))
    worst_streak = int(summary_row.get("worst_consecutive_losing_months", 0))

    excess_failed_months = max(months_below - 3, 0)
    excess_losing_streak = max(worst_streak - 2, 0)

    return (
        sum_capped
        - monthly_shortfall_pct * 10.0
        - dd_excess_pct * 25.0
        - dd_breach_months * 200.0
        - excess_failed_months * 500.0
        - excess_losing_streak * 500.0
    )


# ---------------------------------------------------------------------------
# Backtest runner for DSS signals
# ---------------------------------------------------------------------------


def run_dss_backtest(
    signal_df: pd.DataFrame,
    config: TrialConfig,
    window_data: StrategyData,
    *,
    initial_capital: float = 10_000.0,
    taker_fee: float = 0.0005,
    maker_fee: float = 0.0002,
    max_positions: int = 1,
    risk_base_period: str = "monthly",
) -> pd.DataFrame:
    """Run a DSS backtest and return the trades DataFrame.

    Parameters
    ----------
    signal_df:
        SignalRow DataFrame from SignalComposer.
    config:
        TrialConfig plus downstream execution defaults.
    window_data:
        StrategyData for the window.
    """
    primary = select_timeframe_frame(window_data, config.trigger_instance.timeframe)

    aligned = signal_df_to_ohlcv_aligned(signal_df, primary)

    def _strategy(_data: Any) -> pd.DataFrame:
        return aligned

    bt = Backtester(window_data, _strategy, ohlcv=primary)
    results = bt.run(
        initial_capital=initial_capital,
        taker_fee=taker_fee,
        maker_fee=maker_fee,
        max_positions=max_positions,
        risk_base_period=risk_base_period,
        exit_geometry="sl_rrr",
        structural_sl_mode="ignore",
    )
    return results.trades if results.trades is not None else pd.DataFrame()


# ---------------------------------------------------------------------------
# Parameter sampling helpers
# ---------------------------------------------------------------------------


def _sample_trial_config(trial: optuna.Trial, search_space: DSSSearchSpace) -> TrialConfig:
    """Sample a TrialConfig from Optuna trial suggestions."""
    trigger_name = trial.suggest_categorical(
        "trigger_name", list(search_space.trigger_names)
    )

    n_filters = trial.suggest_int("n_filters", 0, search_space.max_filters)

    filter_names_raw: list[str] = []
    for i in range(n_filters):
        fn = trial.suggest_categorical(
            f"filter_{i}", list(search_space.filter_names)
        )
        filter_names_raw.append(str(fn))
    filter_names = tuple(sorted(set(filter_names_raw)))

    trigger_params: dict[str, ParamValue] = {}
    trigger_bounds = search_space.trigger_param_bounds
    trigger_name_str = str(trigger_name)
    for pname, pdef in trigger_bounds.get(trigger_name_str, {}).items():
        from backtester.strategy_discovery.dss_config import (
            CategoricalParam,
            FloatParam,
            IntParam,
        )

        param_key = f"tp_{trigger_name_str}_{pname}"
        if isinstance(pdef, IntParam):
            trigger_params[pname] = trial.suggest_int(
                param_key, pdef.low, pdef.high, step=pdef.step
            )
        elif isinstance(pdef, FloatParam):
            if pdef.step is not None:
                trigger_params[pname] = trial.suggest_float(
                    param_key, pdef.low, pdef.high, step=pdef.step
                )
            else:
                trigger_params[pname] = trial.suggest_float(param_key, pdef.low, pdef.high)
        elif isinstance(pdef, CategoricalParam):
            trigger_params[pname] = str(
                trial.suggest_categorical(param_key, list(pdef.choices))
            )

    filter_params: dict[str, dict[str, ParamValue]] = {}
    filter_bounds = search_space.filter_param_bounds
    for fn in filter_names:
        fp: dict[str, ParamValue] = {}
        for pname, pdef in filter_bounds.get(fn, {}).items():
            from backtester.strategy_discovery.dss_config import (
                CategoricalParam,
                FloatParam,
                IntParam,
            )

            param_key = f"fp_{fn}_{pname}"
            if isinstance(pdef, IntParam):
                fp[pname] = trial.suggest_int(
                    param_key, pdef.low, pdef.high, step=pdef.step
                )
            elif isinstance(pdef, FloatParam):
                if pdef.step is not None:
                    fp[pname] = trial.suggest_float(
                        param_key, pdef.low, pdef.high, step=pdef.step
                    )
                else:
                    fp[pname] = trial.suggest_float(param_key, pdef.low, pdef.high)
            elif isinstance(pdef, CategoricalParam):
                fp[pname] = str(
                    trial.suggest_categorical(param_key, list(pdef.choices))
                )
        filter_params[fn] = fp

    return TrialConfig(
        trigger_name=trigger_name_str,
        trigger_params=trigger_params,
        filter_names=filter_names,
        filter_params=filter_params,
    )


# ---------------------------------------------------------------------------
# DSSObjective
# ---------------------------------------------------------------------------


class DSSObjective:
    """Optuna objective function for the DSS multi-objective search.

    Returns a tuple of mandate_score values, one per window. Optuna's
    NSGAIISampler maximises all objectives to find a Pareto front.
    """

    def __init__(
        self,
        windows: list[DSSWindowSpec],
        window_data: dict[str, StrategyData],
        search_space: DSSSearchSpace,
        signal_cache: DSSSignalCache,
        config: DSSConfig,
    ) -> None:
        self._windows = windows
        self._window_data = window_data
        self._search_space = search_space
        self._signal_cache = signal_cache
        self._config = config
        self._composer = SignalComposer()
        self._logger = logging.getLogger(__name__)

    def __call__(self, trial: optuna.Trial) -> tuple[float, ...]:
        try:
            config = _sample_trial_config(trial, self._search_space)
        except Exception:
            self._logger.debug("Config sampling failed", exc_info=True)
            return tuple(_EMPTY_SIGNAL_PENALTY for _ in self._windows)

        generate_fn = None
        try:
            generate_fn = self._composer.build(config)
        except ValueError as exc:
            self._logger.debug("build() failed: %s", exc)
            return tuple(_EMPTY_SIGNAL_PENALTY for _ in self._windows)

        scores: list[float] = []
        for spec in self._windows:
            wdata = self._window_data.get(spec.label)
            if wdata is None:
                self._logger.warning("Window data missing for %s", spec.label)
                scores.append(_EMPTY_SIGNAL_PENALTY)
                continue

            try:
                signal_df = self._signal_cache.get_or_compute(
                    config,
                    spec.label,
                    lambda _wdata=wdata: generate_fn(_wdata),  # type: ignore[misc]
                )
            except Exception:
                self._logger.debug(
                    "Signal generation failed for window %s", spec.label, exc_info=True
                )
                scores.append(_BACKTEST_ERROR_PENALTY)
                continue

            if signal_df.empty or len(signal_df) < self._config.min_trades_per_window:
                scores.append(_EMPTY_SIGNAL_PENALTY)
                continue

            try:
                trades = run_dss_backtest(
                    signal_df=signal_df,
                    config=config,
                    window_data=wdata,
                    initial_capital=self._config.initial_capital,
                    taker_fee=self._config.taker_fee,
                    maker_fee=self._config.maker_fee,
                    max_positions=self._config.max_positions,
                    risk_base_period=self._config.risk_base_period,
                )
            except Exception:
                self._logger.debug(
                    "Backtest failed for window %s", spec.label, exc_info=True
                )
                scores.append(_BACKTEST_ERROR_PENALTY)
                continue

            score = compute_mandate_score(
                trades,
                initial_capital=self._config.initial_capital,
                start=spec.start,
                end=spec.end,
            )
            scores.append(score)

            trial.set_user_attr(f"score_{spec.label}", round(score, 2))
            trial.set_user_attr(f"trades_{spec.label}", len(trades))

        trial.set_user_attr("trigger_name", config.trigger_name)
        trial.set_user_attr("n_filters", len(config.filter_names))
        trial.set_user_attr("filter_names", ",".join(config.filter_names))
        trial.set_user_attr("cache_hits", self._signal_cache.hits)
        trial.set_user_attr("cache_size", self._signal_cache.size)

        return tuple(scores)
