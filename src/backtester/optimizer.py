import json
import logging
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import optuna
import pandas as pd
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend

from backtester.data_contracts import StrategyInput, timeframe_minutes, ttl_minutes_to_bars
from backtester.execution_context import (
    StrategyExecutionContext,
    attach_execution_context,
    execution_context_from_run_kwargs,
)
from backtester.fast_exit_optimizer import FastExitEvaluation, FastExitGeometryEvaluator
from backtester.mandate_report import MONTHLY_DD_LIMIT_PCT, RETURN_FLOOR_PCT, build_mandate_report
from backtester.progress import format_duration
from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategy import BaseStrategy
from backtester.tester import Backtester

FloatRange = tuple[float, float, float]
IntRange = tuple[int, int, int]
ExitFamily = Literal["sl_rrr", "sl_rrr_trailing", "tp_pct"]


def _mandate_score(
    *,
    total_return_pct: float,
    max_drawdown_pct: float,
    peak_to_trough_drawdown_pct: float,
    sum_capped_monthly_return_pct: float,
    monthly_shortfall_pct: float,
    dd_excess_pct: float,
    months_below_floor: int,
    dd_breach_months: int,
    worst_consecutive_losing_months: int,
) -> float:
    downside_dd_pct = abs(min(max_drawdown_pct, 0.0))
    peak_to_trough_dd_pct = abs(min(peak_to_trough_drawdown_pct, 0.0))
    excess_failed_months = max(months_below_floor - 12, 0)
    excess_losing_streak = max(worst_consecutive_losing_months - 2, 0)
    return (
        total_return_pct * 100.0
        + sum_capped_monthly_return_pct * 10.0
        - monthly_shortfall_pct * 1.5
        - dd_excess_pct * 35.0
        - dd_breach_months * 150.0
        - excess_failed_months * 75.0
        - excess_losing_streak * 250.0
        - (downside_dd_pct**2) * 85.0
        - peak_to_trough_dd_pct * 35.0
    )


def _empty_mandate_attrs() -> dict[str, Any]:
    return {
        "mandate_score": -float("inf"),
        "min_monthly_return": -100.0,
        "monthly_shortfall_pct": 0.0,
        "mandate_months_passing_floor": 0,
        "mandate_months_below_floor": 0,
        "mandate_dd_breach_months": 0,
        "mandate_worst_consecutive_losing_months": 0,
        "mandate_worst_monthly_drawdown_pct": 0.0,
        "mandate_avg_capped_monthly_return_pct": 0.0,
        "mandate_sum_capped_monthly_return_pct": 0.0,
        "mandate_verdict": "discard",
    }


@dataclass
class TargetFunction:
    fn: Callable[[ResultsAnalyzer], float]
    direction: Literal["maximize", "minimize"] | list[Literal["maximize", "minimize"]]
    name: str = ""


@dataclass(frozen=True, slots=True)
class FastSearchTrial:
    number: int
    value: float
    params: dict[str, Any]
    user_attrs: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FastSearchStudy:
    trials: list[FastSearchTrial]
    best_trial: FastSearchTrial

    def trials_dataframe(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for trial in self.trials:
            row: dict[str, Any] = {
                "number": trial.number,
                "value": trial.value,
                "state": "COMPLETE",
            }
            row.update({f"params_{key}": value for key, value in trial.params.items()})
            row.update({f"user_attrs_{key}": value for key, value in trial.user_attrs.items()})
            rows.append(row)
        return pd.DataFrame(rows)


class ParameterOptimizer:
    """
    Оптимизатор параметров стратегии.
    """

    def __init__(
        self,
        df: StrategyInput,
        ohlcv: pd.DataFrame,
        strategy_class: type[BaseStrategy],
        target: TargetFunction,
        initial_capital: float = 1000.0,
        taker_fee: float = 0.001,
        maker_fee: float = 0.0002,
        position_ttl_bars: int = 20,
        position_ttl_minutes: int | None = None,
        candle_timeframe: str = "1h",
        min_net_exposure: float = 0.01,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        risk_free_rate_annual: float = 0.02,
        strategy_params: dict[str, Any] | None = None,
        optimize_strategy_params: bool = True,
        risk_percent: float = 1.0,
        risk_percent_range: FloatRange | None = (0.1, 0.5, 0.1),
        rrr_range: FloatRange | None = (1.0, 5.0, 1.0),
        trail_activation_rrr: float = 0.0,
        trail_distance_atr: float = 0.0,
        trail_distance_atr_range: FloatRange | None = None,
        position_ttl_bars_range: IntRange | None = None,
        position_ttl_minutes_range: IntRange | None = None,
        tp_move_pct_range: FloatRange | None = None,
        exit_family_search: bool = False,
        exit_families: tuple[ExitFamily, ...] = ("sl_rrr", "sl_rrr_trailing", "tp_pct"),
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
        optimize_daily_limits: bool = True,
        optimize_trading_window: bool = True,
    ):
        self.df = df
        self.ohlcv = ohlcv
        self.strategy_class = strategy_class
        self.target = target
        self.initial_capital = initial_capital
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.position_ttl_bars = position_ttl_bars
        self.candle_timeframe = candle_timeframe
        self.position_ttl_minutes = (
            int(position_ttl_minutes)
            if position_ttl_minutes is not None
            else int(position_ttl_bars) * timeframe_minutes(candle_timeframe)
        )
        self.min_net_exposure = min_net_exposure
        self.max_allowed_margin = max_allowed_margin
        self.risk_base_period = risk_base_period
        self.risk_free_rate_annual = risk_free_rate_annual
        self.strategy_params = dict(strategy_params or {})
        self.optimize_strategy_params = optimize_strategy_params
        self.risk_percent = risk_percent
        self.risk_percent_range = risk_percent_range
        self.rrr_range = rrr_range
        self.trail_activation_rrr = trail_activation_rrr
        self.trail_distance_atr = trail_distance_atr
        self.trail_distance_atr_range = trail_distance_atr_range
        self.position_ttl_bars_range = position_ttl_bars_range
        self.position_ttl_minutes_range: IntRange | None
        if position_ttl_minutes_range is not None:
            self.position_ttl_minutes_range = position_ttl_minutes_range
        elif position_ttl_bars_range is not None:
            minutes = timeframe_minutes(candle_timeframe)
            low, high, step = position_ttl_bars_range
            self.position_ttl_minutes_range = (low * minutes, high * minutes, step * minutes)
        else:
            self.position_ttl_minutes_range = None
        self.tp_move_pct_range = tp_move_pct_range
        self.exit_family_search = exit_family_search
        self.exit_families = exit_families
        self.exit_geometry = exit_geometry
        self.tp_move_pct = tp_move_pct
        self.structural_sl_mode = structural_sl_mode
        self.min_tp_move_pct = min_tp_move_pct
        self.optimize_daily_limits = optimize_daily_limits
        self.optimize_trading_window = optimize_trading_window
        self._signal_cache: dict[str, pd.DataFrame] = {}
        self._fast_exit_evaluator: FastExitGeometryEvaluator | None = None
        self._logger = logging.getLogger(__name__)

    def _objective(self, trial: optuna.Trial) -> float:
        try:
            # 1. Подбираем ПАРАМЕТРЫ СТРАТЕГИИ
            suggested_strategy_params = (
                self.strategy_class(self.strategy_params).suggest_params(trial)
                if self.optimize_strategy_params
                else {}
            )
            strategy_params = {
                **self.strategy_params,
                **suggested_strategy_params,
            }

            # 2. Подбираем ПАРАМЕТРЫ РИСКА (относятся к тестеру)
            risk_percent = self._suggest_float_or_fixed(
                trial,
                "risk_percent",
                self.risk_percent_range,
                self.risk_percent,
            )
            rrr = self._suggest_float_or_fixed(trial, "rrr", self.rrr_range, 2.0)
            exit_family = self._suggest_exit_family(trial)
            trail_distance_atr = 0.0
            if exit_family == "sl_rrr_trailing" or not self.exit_family_search:
                trail_distance_atr = self._suggest_float_or_fixed(
                    trial,
                    "trail_distance_atr",
                    self.trail_distance_atr_range,
                    self.trail_distance_atr,
                )
            trail_activation_rrr = rrr if trail_distance_atr > 0 else 0.0
            max_positions = 0
            position_ttl_minutes = self._suggest_int_or_fixed(
                trial,
                "position_ttl_minutes",
                self.position_ttl_minutes_range,
                self.position_ttl_minutes,
            )
            position_ttl_bars = ttl_minutes_to_bars(position_ttl_minutes, self.candle_timeframe)
            tp_move_pct: float | None = None
            exit_geometry = "tp_pct" if exit_family == "tp_pct" else "sl_rrr"
            if exit_family == "tp_pct":
                fixed_tp = self.tp_move_pct if self.tp_move_pct is not None else 0.015
                tp_move_pct = self._suggest_float_or_fixed(
                    trial,
                    "tp_move_pct",
                    self.tp_move_pct_range,
                    fixed_tp,
                )
                exit_geometry = "tp_pct"

            strategy_instance = self.strategy_class(strategy_params)
            execution_context = execution_context_from_run_kwargs(
                exit_geometry=exit_geometry,
                tp_move_pct=tp_move_pct if exit_geometry == "tp_pct" else None,
                structural_sl_mode=self.structural_sl_mode,
                min_tp_move_pct=self.min_tp_move_pct,
            )
            cache_execution_context = (
                execution_context
                if getattr(self.strategy_class, "signals_depend_on_execution_context", True)
                else None
            )
            strategy_cache_key = self._strategy_cache_key(
                strategy_params,
                cache_execution_context,
            )

            def strategy(df: StrategyInput) -> pd.DataFrame:
                cached = self._signal_cache.get(strategy_cache_key)
                if cached is not None:
                    return cached.copy()
                strategy_input = attach_execution_context(df, execution_context)
                generated = strategy_instance.generate(strategy_input)
                self._signal_cache[strategy_cache_key] = generated.copy()
                return generated

            # 3. Подбираем лимиты по дню и окно торговли (ExecutionSim)
            max_daily_profit = None
            max_daily_loss = None
            if self.optimize_daily_limits:
                max_daily_profit = trial.suggest_float("max_daily_profit", rrr, 15.0, step=1)
                max_daily_loss = trial.suggest_float(
                    "max_daily_loss",
                    max(1.0, rrr // 2),
                    min(5.0, max_daily_profit),
                    step=1,
                )
            trading_begin = None
            trading_end = None
            if self.optimize_trading_window:
                trading_begin = trial.suggest_int("trading_begin", 0, 20)
                trading_end = trial.suggest_int("trading_end", trading_begin + 3, 24)

            # 4. Запускаем полный бэктест или быстрый scorer для fixed-entry DSS.
            fast_evaluator = self._get_fast_exit_evaluator(
                strategy=strategy,
                execution_context=execution_context,
            )
            if (
                fast_evaluator is not None
                and max_daily_profit is None
                and max_daily_loss is None
                and trading_begin is None
                and trading_end is None
                and max_positions == 0
            ):
                fast_evaluation = fast_evaluator.evaluate(
                    risk_percent=risk_percent,
                    rrr=rrr,
                    exit_family=exit_family,
                    position_ttl_bars=position_ttl_bars,
                    trail_distance_atr=trail_distance_atr,
                    tp_move_pct=tp_move_pct if exit_geometry == "tp_pct" else None,
                )
                m = fast_evaluation.metrics
                mandate_attrs = fast_evaluation.mandate_attrs
            else:
                bt = Backtester(self.df, strategy, ohlcv=self.ohlcv)
                results = bt.run(
                    initial_capital=self.initial_capital,
                    taker_fee=self.taker_fee,
                    maker_fee=self.maker_fee,
                    risk_percent=risk_percent,
                    rrr=rrr,
                    trail_activation_rrr=trail_activation_rrr,
                    trail_distance_atr=trail_distance_atr,
                    max_positions=max_positions,
                    position_ttl_bars=position_ttl_bars,
                    position_ttl_minutes=position_ttl_minutes,
                    min_net_exposure=self.min_net_exposure,
                    max_allowed_margin=self.max_allowed_margin,
                    risk_base_period=self.risk_base_period,
                    max_daily_profit=max_daily_profit,
                    max_daily_loss=max_daily_loss,
                    trading_begin=trading_begin,
                    trading_end=trading_end,
                    exit_geometry=exit_geometry,
                    tp_move_pct=tp_move_pct if exit_geometry == "tp_pct" else None,
                    structural_sl_mode=self.structural_sl_mode,
                    min_tp_move_pct=self.min_tp_move_pct,
                    risk_free_rate_annual=self.risk_free_rate_annual,
                    log_summary=False,
                )
                m = results.metrics
                mandate_attrs = self._mandate_trial_attrs(results)

            trial.set_user_attr("total_return_pct", m.get("total_return_pct", -100))
            trial.set_user_attr("trail_activation_rrr", trail_activation_rrr)
            trial.set_user_attr("trail_distance_atr", trail_distance_atr)
            trial.set_user_attr("max_positions", 0)
            trial.set_user_attr("position_ttl_minutes", position_ttl_minutes)
            trial.set_user_attr("position_ttl_bars", position_ttl_bars)
            if tp_move_pct is not None:
                trial.set_user_attr("tp_move_pct", tp_move_pct)
            trial.set_user_attr("exit_family", exit_family)
            trial.set_user_attr("exit_geometry", exit_geometry)
            trial.set_user_attr("signal_cache_size", len(self._signal_cache))
            for name, value in mandate_attrs.items():
                trial.set_user_attr(name, value)
            trial.set_user_attr("max_drawdown", m.get("max_drawdown", -100))
            trial.set_user_attr("total_trades", m.get("total_trades", 0))
            trial.set_user_attr("sharpe_ratio", m.get("sharpe_ratio", -999.0))
            if self.target.name == "mandate_score":
                return float(mandate_attrs["mandate_score"])
            if fast_evaluator is not None:
                return float(m.get("total_return_pct", -float("inf")))
            return self.target.fn(results)

        except Exception as e:
            self._logger.debug(f"Ошибка в итерации: {e}")
            return -float("inf")

    def _get_fast_exit_evaluator(
        self,
        *,
        strategy: Callable[[StrategyInput], pd.DataFrame],
        execution_context: StrategyExecutionContext,
    ) -> FastExitGeometryEvaluator | None:
        if self._fast_exit_evaluator is not None:
            return self._fast_exit_evaluator
        if getattr(self.strategy_class, "signals_depend_on_execution_context", True):
            return None
        if self.optimize_strategy_params or self.optimize_daily_limits or self.optimize_trading_window:
            return None
        signal_df = strategy(attach_execution_context(self.df, execution_context))
        try:
            self._fast_exit_evaluator = FastExitGeometryEvaluator(
                signal_df=signal_df,
                initial_capital=self.initial_capital,
                taker_fee=self.taker_fee,
                candle_timeframe=self.candle_timeframe,
                risk_base_period=self.risk_base_period,
                risk_free_rate_annual=self.risk_free_rate_annual,
            )
        except ValueError as exc:
            self._logger.debug("Fast exit evaluator disabled: %s", exc)
            return None
        signal_count = int((signal_df["signal"] != 0).sum()) if "signal" in signal_df else 0
        self._logger.info(
            "Fast exit evaluator enabled: fixed signals=%d bars=%d",
            signal_count,
            len(signal_df),
        )
        return self._fast_exit_evaluator

    def _suggest_exit_family(self, trial: optuna.Trial) -> ExitFamily:
        if self.exit_family_search:
            return trial.suggest_categorical("exit_family", list(self.exit_families))  # type: ignore[return-value]
        if self.exit_geometry == "tp_pct" or self.tp_move_pct_range is not None:
            return "tp_pct"
        if self.trail_distance_atr_range is not None or self.trail_distance_atr > 0:
            return "sl_rrr_trailing"
        return "sl_rrr"

    def _mandate_trial_attrs(self, results: ResultsAnalyzer) -> dict[str, Any]:
        primary = self.ohlcv
        if primary.empty:
            return _empty_mandate_attrs()

        index = pd.to_datetime(primary.index, errors="coerce")
        index = index.dropna()
        if index.empty:
            return _empty_mandate_attrs()

        start = str(index.min().date())
        end = str(index.max().date())
        if pd.Timestamp(end) <= pd.Timestamp(start):
            end = str((pd.Timestamp(start) + pd.Timedelta(days=1)).date())

        try:
            report = build_mandate_report(
                results.trades,
                initial_capital=self.initial_capital,
                start=start,
                end=end,
            )
        except (AttributeError, KeyError, ValueError, TypeError):
            return _empty_mandate_attrs()

        monthly = report.monthly
        summary = report.summary.iloc[0].to_dict() if not report.summary.empty else {}
        if monthly.empty:
            return _empty_mandate_attrs()

        raw = pd.to_numeric(monthly["raw_monthly_return_pct"], errors="coerce").fillna(0.0)
        drawdowns = pd.to_numeric(monthly["max_drawdown_pct"], errors="coerce").fillna(0.0)
        min_monthly_return = float(raw.min()) if not raw.empty else -100.0
        monthly_shortfall_pct = float((RETURN_FLOOR_PCT - raw).clip(lower=0.0).sum())
        dd_excess_pct = float((MONTHLY_DD_LIMIT_PCT - drawdowns).clip(lower=0.0).sum())
        mandate_score = _mandate_score(
            total_return_pct=float(results.metrics.get("total_return_pct", 0.0)),
            max_drawdown_pct=float(results.metrics.get("max_drawdown", 0.0)),
            peak_to_trough_drawdown_pct=float(
                results.metrics.get("peak_to_trough_drawdown", 0.0)
            ),
            sum_capped_monthly_return_pct=float(
                summary.get("sum_capped_monthly_return_pct", 0.0)
            ),
            monthly_shortfall_pct=monthly_shortfall_pct,
            dd_excess_pct=dd_excess_pct,
            months_below_floor=int(summary.get("months_below_floor", 0)),
            dd_breach_months=int(summary.get("dd_breach_months", 0)),
            worst_consecutive_losing_months=int(
                summary.get("worst_consecutive_losing_months", 0)
            ),
        )

        return {
            "mandate_score": round(mandate_score, 4),
            "min_monthly_return": round(min_monthly_return, 2),
            "monthly_shortfall_pct": round(monthly_shortfall_pct, 2),
            "mandate_months_passing_floor": int(summary.get("months_passing_floor", 0)),
            "mandate_months_below_floor": int(summary.get("months_below_floor", 0)),
            "mandate_dd_breach_months": int(summary.get("dd_breach_months", 0)),
            "mandate_worst_consecutive_losing_months": int(
                summary.get("worst_consecutive_losing_months", 0)
            ),
            "mandate_worst_monthly_drawdown_pct": float(
                summary.get("worst_monthly_drawdown_pct", 0.0)
            ),
            "mandate_avg_capped_monthly_return_pct": float(
                summary.get("avg_capped_monthly_return_pct", 0.0)
            ),
            "mandate_sum_capped_monthly_return_pct": float(
                summary.get("sum_capped_monthly_return_pct", 0.0)
            ),
            "mandate_verdict": str(summary.get("verdict", "discard")),
        }

    @staticmethod
    def _suggest_float_or_fixed(
        trial: optuna.Trial,
        name: str,
        value_range: FloatRange | None,
        fixed: float,
    ) -> float:
        if value_range is None:
            return fixed
        low, high, step = value_range
        return trial.suggest_float(name, low, high, step=step)

    @staticmethod
    def _suggest_int_or_fixed(
        trial: optuna.Trial,
        name: str,
        value_range: IntRange | None,
        fixed: int,
    ) -> int:
        if value_range is None:
            return fixed
        low, high, step = value_range
        return trial.suggest_int(name, low, high, step=step)

    @staticmethod
    def _strategy_cache_key(
        params: dict[str, Any],
        execution_context: StrategyExecutionContext | None = None,
    ) -> str:
        payload: dict[str, Any] = dict(params)
        if execution_context is not None:
            payload["_execution_context"] = execution_context.cache_key_payload()
        return json.dumps(payload, sort_keys=True, default=str)

    def cached_signals_for_params(
        self,
        params: dict[str, Any],
        *,
        execution_context: StrategyExecutionContext | None = None,
    ) -> pd.DataFrame | None:
        cached = self._signal_cache.get(
            self._strategy_cache_key(params, execution_context),
        )
        if cached is None:
            return None
        return cached.copy()

    def optimize(
        self,
        n_trials: int = 50,
        show_progress: bool = True,
        name: str = "no_name",
    ) -> tuple[dict[str, Any], optuna.Study | FastSearchStudy]:
        if self._can_use_fast_native_search():
            return self._optimize_fast_native(n_trials=n_trials, show_progress=show_progress)

        use_fast_in_memory_storage = self._can_use_fast_in_memory_storage()
        study_kwargs: dict[str, Any] = {}
        if isinstance(d := self.target.direction, list):
            study_kwargs["sampler"] = optuna.samplers.NSGAIIISampler()
            study_kwargs["directions"] = d
        else:
            if use_fast_in_memory_storage:
                study_kwargs["sampler"] = optuna.samplers.RandomSampler(seed=20260804)
            else:
                study_kwargs["sampler"] = optuna.samplers.TPESampler()
                study_kwargs["pruner"] = optuna.pruners.HyperbandPruner()
            study_kwargs["direction"] = d

        storage: JournalStorage | None = None
        if not use_fast_in_memory_storage:
            journal_path = Path(f"{name}.log")
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            storage = JournalStorage(JournalFileBackend(str(journal_path)))
        started_at = time.monotonic()
        last_progress_log_at = started_at
        logger = logging.getLogger(__name__)
        old_optuna_verbosity = optuna.logging.get_verbosity()
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def _log_progress(study: optuna.Study, _trial: optuna.trial.FrozenTrial) -> None:
            nonlocal last_progress_log_at
            if not show_progress:
                return
            completed = max(len(study.trials) - initial_trials, 0)
            if completed <= 0:
                return
            elapsed = time.monotonic() - started_at
            rate = completed / elapsed if elapsed > 0 else 0.0
            remaining = max(n_trials - completed, 0)
            eta = remaining / rate if rate > 0 else None
            best_value = "n/a"
            with suppress(ValueError):
                best_value = f"{study.best_value:.6g}"
            now = time.monotonic()
            if completed == 1 or completed == n_trials or now - last_progress_log_at >= 30.0:
                logger.info(
                    "Optuna progress: %d/%d trials elapsed=%s rate=%.3f trials/s eta=%s best=%s",
                    completed,
                    n_trials,
                    format_duration(elapsed),
                    rate,
                    format_duration(eta),
                    best_value,
                )
                last_progress_log_at = now

        if show_progress:
            logger.info("Optuna progress: started total=%d trials", n_trials)
        if use_fast_in_memory_storage:
            logger.info("Optuna storage: in-memory fast fixed-signal search")
        try:
            if storage is None:
                study = optuna.create_study(study_name=name, **study_kwargs)
            else:
                study = optuna.create_study(
                    study_name=name,
                    storage=storage,
                    load_if_exists=True,
                    **study_kwargs,
                )
            initial_trials = len(study.trials)
            study.optimize(
                self._objective,
                n_trials=n_trials,
                show_progress_bar=False,
                n_jobs=1,
                callbacks=[_log_progress],
            )
            if show_progress:
                elapsed = time.monotonic() - started_at
                logger.info("Optuna progress: finished elapsed=%s", format_duration(elapsed))
            return study.best_params, study
        finally:
            optuna.logging.set_verbosity(old_optuna_verbosity)

    def _can_use_fast_in_memory_storage(self) -> bool:
        return (
            not getattr(self.strategy_class, "signals_depend_on_execution_context", True)
            and not self.optimize_strategy_params
            and not self.optimize_daily_limits
            and not self.optimize_trading_window
        )

    def _can_use_fast_native_search(self) -> bool:
        return (
            self._can_use_fast_in_memory_storage()
            and not isinstance(self.target.direction, list)
            and self.target.name == "mandate_score"
        )

    def _optimize_fast_native(
        self,
        *,
        n_trials: int,
        show_progress: bool,
    ) -> tuple[dict[str, Any], FastSearchStudy]:
        logger = logging.getLogger(__name__)
        started_at = time.monotonic()
        last_progress_log_at = started_at
        if show_progress:
            logger.info("Fast optimizer progress: started total=%d trials", n_trials)

        strategy_params = dict(self.strategy_params)
        strategy_instance = self.strategy_class(strategy_params)
        signal_execution_context = execution_context_from_run_kwargs(
            exit_geometry=self.exit_geometry,
            tp_move_pct=self.tp_move_pct if self.exit_geometry == "tp_pct" else None,
            structural_sl_mode=self.structural_sl_mode,
            min_tp_move_pct=self.min_tp_move_pct,
        )
        signal_df = strategy_instance.generate(attach_execution_context(self.df, signal_execution_context))
        self._signal_cache[
            self._strategy_cache_key(strategy_params, None)
        ] = signal_df.copy()
        evaluator = FastExitGeometryEvaluator(
            signal_df=signal_df,
            initial_capital=self.initial_capital,
            taker_fee=self.taker_fee,
            candle_timeframe=self.candle_timeframe,
            risk_base_period=self.risk_base_period,
            risk_free_rate_annual=self.risk_free_rate_annual,
        )
        logger.info(
            "Fast native optimizer enabled: fixed signals=%d bars=%d",
            int((signal_df["signal"] != 0).sum()) if "signal" in signal_df else 0,
            len(signal_df),
        )

        rng = np.random.default_rng(20260804)
        trials: list[FastSearchTrial] = []
        elite_trials: list[FastSearchTrial] = []
        elite_metric_keys: set[tuple[object, ...]] = set()
        seen_param_keys: set[tuple[object, ...]] = set()
        sample_source_counts: dict[str, int] = {}
        best_trial: FastSearchTrial | None = None
        warmup_trials = self._fast_native_warmup_trials(n_trials)
        logger.info(
            "Fast native sampler: adaptive random_warmup=%d elite_size=%d random_explore=20%%",
            warmup_trials,
            128,
        )
        for number in range(n_trials):
            sampled, sample_source = self._sample_fast_native_candidate(
                rng=rng,
                elite_trials=elite_trials,
                seen_param_keys=seen_param_keys,
                trial_number=number,
                warmup_trials=warmup_trials,
            )
            sample_source_counts[sample_source] = sample_source_counts.get(sample_source, 0) + 1
            evaluation = evaluator.evaluate(
                risk_percent=float(sampled["risk_percent"]),
                rrr=float(sampled["rrr"]),
                exit_family=sampled["exit_family"],
                position_ttl_bars=int(sampled["position_ttl_bars"]),
                trail_distance_atr=float(sampled.get("trail_distance_atr", 0.0)),
                tp_move_pct=sampled.get("tp_move_pct"),
            )
            value = float(evaluation.mandate_attrs["mandate_score"])
            user_attrs: dict[str, Any] = {
                **evaluation.mandate_attrs,
                "total_return_pct": evaluation.metrics.get("total_return_pct", -100),
                "trail_activation_rrr": sampled.get("trail_activation_rrr", 0.0),
                "trail_distance_atr": sampled.get("trail_distance_atr", 0.0),
                "max_positions": 0,
                "position_ttl_minutes": sampled["position_ttl_minutes"],
                "position_ttl_bars": sampled["position_ttl_bars"],
                "exit_family": sampled["exit_family"],
                "exit_geometry": sampled["exit_geometry"],
                "signal_cache_size": len(self._signal_cache),
                "max_drawdown": evaluation.metrics.get("max_drawdown", -100),
                "total_trades": evaluation.metrics.get("total_trades", 0),
                "sharpe_ratio": evaluation.metrics.get("sharpe_ratio", -999.0),
                "objective_source": "fast_native_proxy",
                "sample_source": sample_source,
            }
            if sampled.get("tp_move_pct") is not None:
                user_attrs["tp_move_pct"] = sampled["tp_move_pct"]
            params = {
                key: value
                for key, value in sampled.items()
                if key
                in {
                    "risk_percent",
                    "rrr",
                    "exit_family",
                    "position_ttl_minutes",
                    "trail_distance_atr",
                    "tp_move_pct",
                }
            }
            trial = FastSearchTrial(
                number=number,
                value=value,
                params=params,
                user_attrs=user_attrs,
            )
            trials.append(trial)
            if best_trial is None or trial.value > best_trial.value:
                best_trial = trial
            metric_key = self._fast_metric_key(evaluation)
            if metric_key not in elite_metric_keys:
                elite_trials.append(trial)
                elite_metric_keys.add(metric_key)
                elite_trials.sort(key=lambda item: item.value, reverse=True)
                if len(elite_trials) > 128:
                    elite_trials.pop()
                    elite_metric_keys = {
                        self._fast_trial_metric_key(item)
                        for item in elite_trials
                    }

            if show_progress:
                completed = number + 1
                now = time.monotonic()
                if completed == 1 or completed == n_trials or now - last_progress_log_at >= 30.0:
                    elapsed = now - started_at
                    rate = completed / elapsed if elapsed > 0 else 0.0
                    remaining = max(n_trials - completed, 0)
                    eta = remaining / rate if rate > 0 else None
                    best_value = best_trial.value if best_trial is not None else float("nan")
                    source_summary = ", ".join(
                        f"{key}={value}" for key, value in sorted(sample_source_counts.items())
                    )
                    logger.info(
                        "Fast optimizer progress: %d/%d trials elapsed=%s rate=%.3f trials/s eta=%s best=%.6g seen=%d sources=%s",
                        completed,
                        n_trials,
                        format_duration(elapsed),
                        rate,
                        format_duration(eta),
                        best_value,
                        len(seen_param_keys),
                        source_summary,
                    )
                    last_progress_log_at = now

        if best_trial is None:
            raise RuntimeError("fast optimizer produced no trials")
        if show_progress:
            logger.info(
                "Fast optimizer progress: finished elapsed=%s",
                format_duration(time.monotonic() - started_at),
            )
        return dict(best_trial.params), FastSearchStudy(trials=trials, best_trial=best_trial)

    @staticmethod
    def _fast_native_warmup_trials(n_trials: int) -> int:
        if n_trials <= 0:
            return 0
        return min(n_trials, max(2_048, min(20_000, n_trials // 20)))

    def _sample_fast_native_candidate(
        self,
        *,
        rng: np.random.Generator,
        elite_trials: list[FastSearchTrial],
        seen_param_keys: set[tuple[object, ...]],
        trial_number: int,
        warmup_trials: int,
    ) -> tuple[dict[str, Any], str]:
        use_random = (
            trial_number < warmup_trials
            or not elite_trials
            or rng.random() < 0.20
        )
        for _attempt in range(100):
            if use_random:
                sampled = self._sample_fast_native_params(rng)
                source = "random_unseen"
            else:
                sampled = self._mutate_fast_native_elite(rng, elite_trials)
                source = "elite_mutation"
            key = self._fast_param_key(sampled)
            if key not in seen_param_keys:
                seen_param_keys.add(key)
                return sampled, source
            use_random = rng.random() < 0.35

        sampled = self._sample_fast_native_params(rng)
        key = self._fast_param_key(sampled)
        seen_param_keys.add(key)
        return sampled, "random_duplicate_fallback"

    def _mutate_fast_native_elite(
        self,
        rng: np.random.Generator,
        elite_trials: list[FastSearchTrial],
    ) -> dict[str, Any]:
        elite_index = min(int(rng.exponential(scale=12.0)), len(elite_trials) - 1)
        parent = elite_trials[elite_index].params
        exit_family = str(parent.get("exit_family", self._sample_exit_family(rng)))
        if self.exit_family_search and rng.random() < 0.08:
            exit_family = self._sample_exit_family(rng)

        risk_percent = self._mutate_float_value(
            rng,
            self.risk_percent_range,
            float(parent.get("risk_percent", self.risk_percent)),
            radius=2,
        )
        rrr = self._mutate_float_value(
            rng,
            self.rrr_range,
            float(parent.get("rrr", 2.0)),
            radius=4,
        )
        position_ttl_minutes = self._mutate_int_value(
            rng,
            self.position_ttl_minutes_range,
            int(parent.get("position_ttl_minutes", self.position_ttl_minutes)),
            radius=12,
        )
        sampled: dict[str, Any] = {
            "risk_percent": risk_percent,
            "rrr": rrr,
            "exit_family": exit_family,
            "position_ttl_minutes": position_ttl_minutes,
            "position_ttl_bars": ttl_minutes_to_bars(
                position_ttl_minutes,
                self.candle_timeframe,
            ),
            "exit_geometry": "tp_pct" if exit_family == "tp_pct" else "sl_rrr",
        }

        if exit_family == "sl_rrr_trailing" or not self.exit_family_search:
            sampled["trail_distance_atr"] = self._mutate_float_value(
                rng,
                self.trail_distance_atr_range,
                float(parent.get("trail_distance_atr", self.trail_distance_atr)),
                radius=3,
            )
            sampled["trail_activation_rrr"] = rrr if sampled["trail_distance_atr"] > 0 else 0.0
        else:
            sampled["trail_distance_atr"] = 0.0
            sampled["trail_activation_rrr"] = 0.0

        if exit_family == "tp_pct":
            fixed_tp = self.tp_move_pct if self.tp_move_pct is not None else 0.015
            sampled["tp_move_pct"] = self._mutate_float_value(
                rng,
                self.tp_move_pct_range,
                float(parent.get("tp_move_pct", fixed_tp)),
                radius=6,
            )
        return sampled

    @staticmethod
    def _fast_param_key(sampled: dict[str, Any]) -> tuple[object, ...]:
        return (
            sampled.get("exit_family"),
            sampled.get("risk_percent"),
            sampled.get("rrr"),
            sampled.get("position_ttl_minutes"),
            sampled.get("trail_distance_atr", 0.0),
            sampled.get("tp_move_pct"),
        )

    @staticmethod
    def _fast_metric_key(evaluation: FastExitEvaluation) -> tuple[object, ...]:
        metrics = evaluation.metrics
        attrs = evaluation.mandate_attrs
        return (
            round(float(attrs.get("mandate_score", -float("inf"))), 6),
            metrics.get("total_return_pct"),
            metrics.get("max_drawdown"),
            attrs.get("monthly_shortfall_pct"),
            attrs.get("mandate_months_passing_floor"),
            attrs.get("mandate_months_below_floor"),
            attrs.get("mandate_dd_breach_months"),
            attrs.get("mandate_worst_monthly_drawdown_pct"),
        )

    @staticmethod
    def _fast_trial_metric_key(trial: FastSearchTrial) -> tuple[object, ...]:
        attrs = trial.user_attrs
        return (
            round(float(attrs.get("mandate_score", trial.value)), 6),
            attrs.get("total_return_pct"),
            attrs.get("max_drawdown"),
            attrs.get("monthly_shortfall_pct"),
            attrs.get("mandate_months_passing_floor"),
            attrs.get("mandate_months_below_floor"),
            attrs.get("mandate_dd_breach_months"),
            attrs.get("mandate_worst_monthly_drawdown_pct"),
        )

    def _sample_fast_native_params(self, rng: np.random.Generator) -> dict[str, Any]:
        risk_percent = self._sample_float_range(rng, self.risk_percent_range, self.risk_percent)
        rrr = self._sample_float_range(rng, self.rrr_range, 2.0)
        exit_family = self._sample_exit_family(rng)
        position_ttl_minutes = self._sample_int_range(
            rng,
            self.position_ttl_minutes_range,
            self.position_ttl_minutes,
        )
        position_ttl_bars = ttl_minutes_to_bars(position_ttl_minutes, self.candle_timeframe)
        sampled: dict[str, Any] = {
            "risk_percent": risk_percent,
            "rrr": rrr,
            "exit_family": exit_family,
            "position_ttl_minutes": position_ttl_minutes,
            "position_ttl_bars": position_ttl_bars,
            "exit_geometry": "tp_pct" if exit_family == "tp_pct" else "sl_rrr",
        }
        if exit_family == "sl_rrr_trailing" or not self.exit_family_search:
            trail_distance_atr = self._sample_float_range(
                rng,
                self.trail_distance_atr_range,
                self.trail_distance_atr,
            )
            sampled["trail_distance_atr"] = trail_distance_atr
            sampled["trail_activation_rrr"] = rrr if trail_distance_atr > 0 else 0.0
        else:
            sampled["trail_distance_atr"] = 0.0
            sampled["trail_activation_rrr"] = 0.0
        if exit_family == "tp_pct":
            fixed_tp = self.tp_move_pct if self.tp_move_pct is not None else 0.015
            sampled["tp_move_pct"] = self._sample_float_range(
                rng,
                self.tp_move_pct_range,
                fixed_tp,
            )
        return sampled

    def _sample_exit_family(self, rng: np.random.Generator) -> ExitFamily:
        if self.exit_family_search:
            return str(rng.choice(self.exit_families))  # type: ignore[return-value]
        if self.exit_geometry == "tp_pct" or self.tp_move_pct_range is not None:
            return "tp_pct"
        if self.trail_distance_atr_range is not None or self.trail_distance_atr > 0:
            return "sl_rrr_trailing"
        return "sl_rrr"

    @staticmethod
    def _sample_float_range(
        rng: np.random.Generator,
        value_range: FloatRange | None,
        fixed: float,
    ) -> float:
        if value_range is None:
            return float(fixed)
        low, high, step = value_range
        count = round((high - low) / step)
        return round(float(low + int(rng.integers(0, count + 1)) * step), 10)

    @staticmethod
    def _mutate_float_value(
        rng: np.random.Generator,
        value_range: FloatRange | None,
        current: float,
        *,
        radius: int,
    ) -> float:
        if value_range is None:
            return float(current)
        low, high, step = value_range
        count = round((high - low) / step)
        current_index = round((current - low) / step)
        current_index = max(0, min(count, current_index))
        if rng.random() < 0.15:
            index = int(rng.integers(0, count + 1))
        else:
            offset = int(rng.integers(-radius, radius + 1))
            index = max(0, min(count, current_index + offset))
        return round(float(low + index * step), 10)

    @staticmethod
    def _sample_int_range(
        rng: np.random.Generator,
        value_range: IntRange | None,
        fixed: int,
    ) -> int:
        if value_range is None:
            return int(fixed)
        low, high, step = value_range
        count = int((high - low) // step)
        return int(low + int(rng.integers(0, count + 1)) * step)

    @staticmethod
    def _mutate_int_value(
        rng: np.random.Generator,
        value_range: IntRange | None,
        current: int,
        *,
        radius: int,
    ) -> int:
        if value_range is None:
            return int(current)
        low, high, step = value_range
        count = int((high - low) // step)
        current_index = round((current - low) / step)
        current_index = max(0, min(count, current_index))
        if rng.random() < 0.15:
            index = int(rng.integers(0, count + 1))
        else:
            offset = int(rng.integers(-radius, radius + 1))
            index = max(0, min(count, current_index + offset))
        return int(low + index * step)
