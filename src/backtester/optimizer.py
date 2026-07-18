import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import optuna
import pandas as pd
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.execution_context import (
    StrategyExecutionContext,
    attach_execution_context,
    execution_context_from_run_kwargs,
)
from backtester.mandate_report import MONTHLY_DD_LIMIT_PCT, RETURN_FLOOR_PCT, build_mandate_report
from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategy import BaseStrategy
from backtester.tester import Backtester

FloatRange = tuple[float, float, float]
IntRange = tuple[int, int, int]


def _mandate_score(
    *,
    sum_capped_monthly_return_pct: float,
    monthly_shortfall_pct: float,
    dd_excess_pct: float,
    months_below_floor: int,
    dd_breach_months: int,
    worst_consecutive_losing_months: int,
) -> float:
    excess_failed_months = max(months_below_floor - 3, 0)
    excess_losing_streak = max(worst_consecutive_losing_months - 2, 0)
    return (
        sum_capped_monthly_return_pct
        - monthly_shortfall_pct * 10.0
        - dd_excess_pct * 25.0
        - dd_breach_months * 200.0
        - excess_failed_months * 500.0
        - excess_losing_streak * 500.0
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


class ParameterOptimizer:
    """
    Оптимизатор параметров стратегии.
    """

    def __init__(
        self,
        df: StrategyInput,
        strategy_class: type[BaseStrategy],
        target: TargetFunction,
        initial_capital: float = 1000.0,
        taker_fee: float = 0.001,
        maker_fee: float = 0.0002,
        position_ttl_bars: int = 20,
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
        tp_move_pct_range: FloatRange | None = None,
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
        optimize_daily_limits: bool = True,
        optimize_trading_window: bool = True,
    ):
        self.df = df
        self.strategy_class = strategy_class
        self.target = target
        self.initial_capital = initial_capital
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.position_ttl_bars = position_ttl_bars
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
        self.tp_move_pct_range = tp_move_pct_range
        self.exit_geometry = exit_geometry
        self.tp_move_pct = tp_move_pct
        self.structural_sl_mode = structural_sl_mode
        self.min_tp_move_pct = min_tp_move_pct
        self.optimize_daily_limits = optimize_daily_limits
        self.optimize_trading_window = optimize_trading_window
        self._signal_cache: dict[str, pd.DataFrame] = {}
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
            trail_distance_atr = self._suggest_float_or_fixed(
                trial,
                "trail_distance_atr",
                self.trail_distance_atr_range,
                self.trail_distance_atr,
            )
            trail_activation_rrr = rrr if trail_distance_atr > 0 else 0.0
            max_positions = 0
            position_ttl_bars = self._suggest_int_or_fixed(
                trial,
                "position_ttl_bars",
                self.position_ttl_bars_range,
                self.position_ttl_bars,
            )
            tp_move_pct: float | None = None
            exit_geometry = self.exit_geometry
            if self.tp_move_pct_range is not None or self.exit_geometry == "tp_pct":
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
            strategy_cache_key = self._strategy_cache_key(
                strategy_params,
                execution_context,
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

            # 4. Запускаем бэктест
            bt = Backtester(self.df, strategy)
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
            )

            m = results.metrics
            mandate_attrs = self._mandate_trial_attrs(results)
            trial.set_user_attr("total_return_pct", m.get("total_return_pct", -100))
            trial.set_user_attr("trail_activation_rrr", trail_activation_rrr)
            trial.set_user_attr("trail_distance_atr", trail_distance_atr)
            trial.set_user_attr("max_positions", 0)
            trial.set_user_attr("position_ttl_bars", position_ttl_bars)
            if tp_move_pct is not None:
                trial.set_user_attr("tp_move_pct", tp_move_pct)
            trial.set_user_attr("exit_geometry", exit_geometry)
            trial.set_user_attr("signal_cache_size", len(self._signal_cache))
            for name, value in mandate_attrs.items():
                trial.set_user_attr(name, value)
            trial.set_user_attr("max_drawdown", m.get("max_drawdown", -100))
            trial.set_user_attr("total_trades", m.get("total_trades", 0))
            trial.set_user_attr("sharpe_ratio", m.get("sharpe_ratio", -999.0))
            if self.target.name == "mandate_score":
                return float(mandate_attrs["mandate_score"])
            return self.target.fn(results)

        except Exception as e:
            self._logger.debug(f"Ошибка в итерации: {e}")
            return -float("inf")

    def _mandate_trial_attrs(self, results: ResultsAnalyzer) -> dict[str, Any]:
        primary = self._primary_frame()
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

    def _primary_frame(self) -> pd.DataFrame:
        if isinstance(self.df, StrategyData):
            return self.df.primary
        return self.df

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
    ) -> tuple[dict[str, Any], optuna.Study]:
        study_kwargs: dict[str, Any] = {}
        if isinstance(d := self.target.direction, list):
            study_kwargs["sampler"] = optuna.samplers.NSGAIIISampler()
            study_kwargs["directions"] = d
        else:
            study_kwargs["sampler"] = optuna.samplers.TPESampler()
            study_kwargs["pruner"] = optuna.pruners.HyperbandPruner()
            study_kwargs["direction"] = d

        journal_path = Path(f"{name}.log")
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        storage = JournalStorage(JournalFileBackend(str(journal_path)))
        study = optuna.create_study(
            study_name=name,
            storage=storage,
            load_if_exists=True,
            **study_kwargs,
        )
        study.optimize(
            self._objective,
            n_trials=n_trials,
            show_progress_bar=show_progress,
            n_jobs=1,
        )
        return study.best_params, study
