import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import optuna
import pandas as pd
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend

from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategy import BaseStrategy
from backtester.tester import Backtester

FloatRange = tuple[float, float, float]
IntRange = tuple[int, int, int]


@dataclass
class TargetFunction:
    fn: Callable[[ResultsAnalyzer], float]
    direction: Literal["maximize", "minimize"]


class ParameterOptimizer:
    """
    Оптимизатор параметров стратегии.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        strategy_class: type[BaseStrategy],
        target: TargetFunction,
        initial_capital: float = 1000.0,
        taker_fee: float = 0.001,
        maker_fee: float = 0.0002,
        max_positions: int = 5,
        position_ttl_bars: int = 20,
        min_net_exposure: float = 0.01,
        is_isolated_futures: bool = False,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        risk_free_rate_annual: float = 0.02,
        strategy_params: dict[str, Any] | None = None,
        optimize_strategy_params: bool = True,
        risk_percent: float = 1.0,
        risk_percent_range: FloatRange | None = (0.1, 0.5, 0.1),
        rrr_range: FloatRange | None = (1.0, 5.0, 1.0),
        position_ttl_bars_range: IntRange | None = None,
        optimize_daily_limits: bool = True,
        optimize_trading_window: bool = True,
    ):
        self.df = df
        self.strategy_class = strategy_class
        self.target = target
        self.initial_capital = initial_capital
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.max_positions = max_positions
        self.position_ttl_bars = position_ttl_bars
        self.min_net_exposure = min_net_exposure
        self.is_isolated_futures = is_isolated_futures
        self.max_allowed_margin = max_allowed_margin
        self.risk_base_period = risk_base_period
        self.risk_free_rate_annual = risk_free_rate_annual
        self.strategy_params = dict(strategy_params or {})
        self.optimize_strategy_params = optimize_strategy_params
        self.risk_percent = risk_percent
        self.risk_percent_range = risk_percent_range
        self.rrr_range = rrr_range
        self.position_ttl_bars_range = position_ttl_bars_range
        self.optimize_daily_limits = optimize_daily_limits
        self.optimize_trading_window = optimize_trading_window
        self._signal_cache: dict[str, pd.DataFrame] = {}
        self._logger = logging.getLogger(__name__)

    def _objective(self, trial: optuna.Trial) -> float:
        try:
            # 1. Подбираем ПАРАМЕТРЫ СТРАТЕГИИ
            strategy_params = {
                **self.strategy_params,
                **(
                    self.strategy_class.suggest_params(None, trial)
                    if self.optimize_strategy_params
                    else {}
                ),
            }
            strategy_instance = self.strategy_class(strategy_params)
            strategy_cache_key = self._strategy_cache_key(strategy_params)

            def strategy(df):
                cached = self._signal_cache.get(strategy_cache_key)
                if cached is not None:
                    return cached.copy()
                generated = strategy_instance.generate(df)
                self._signal_cache[strategy_cache_key] = generated.copy()
                return generated

            # 2. Подбираем ПАРАМЕТРЫ РИСКА (относятся к тестеру)
            risk_percent = self._suggest_float_or_fixed(
                trial,
                "risk_percent",
                self.risk_percent_range,
                self.risk_percent,
            )
            rrr = self._suggest_float_or_fixed(trial, "rrr", self.rrr_range, 2.0)
            position_ttl_bars = self._suggest_int_or_fixed(
                trial,
                "position_ttl_bars",
                self.position_ttl_bars_range,
                self.position_ttl_bars,
            )

            # 3. Подбираем лимиты по дню и окно торговли (ExecutionSim)
            max_daily_profit = None
            max_daily_loss = None
            if self.optimize_daily_limits:
                max_daily_profit = trial.suggest_float(
                    "max_daily_profit", rrr, 15.0, step=1
                )
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
                max_positions=self.max_positions,
                position_ttl_bars=position_ttl_bars,
                min_net_exposure=self.min_net_exposure,
                is_isolated_futures=self.is_isolated_futures,
                max_allowed_margin=self.max_allowed_margin,
                risk_base_period=self.risk_base_period,
                max_daily_profit=max_daily_profit,
                max_daily_loss=max_daily_loss,
                trading_begin=trading_begin,
                trading_end=trading_end,
                risk_free_rate_annual=self.risk_free_rate_annual,
            )

            m = results.metrics
            trial.set_user_attr("total_return_pct", m.get("total_return_pct", -100))
            trial.set_user_attr("position_ttl_bars", position_ttl_bars)
            trial.set_user_attr("signal_cache_size", len(self._signal_cache))
            trial.set_user_attr(
                "min_monthly_return",
                min(
                    map(
                        lambda x: x["ret"],
                        m.get("monthly_returns_pct", {"ret": -100}).values(),
                    )
                ),
            )
            trial.set_user_attr("max_drawdown", m.get("max_drawdown", -100))
            trial.set_user_attr("total_trades", m.get("total_trades", 0))
            trial.set_user_attr("sharpe_ratio", m.get("sharpe_ratio", -999.0))
            return self.target.fn(results)

        except Exception as e:
            self._logger.debug(f"Ошибка в итерации: {e}")
            return -float("inf")

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
    def _strategy_cache_key(params: dict[str, Any]) -> str:
        return json.dumps(params, sort_keys=True, default=str)

    def cached_signals_for_params(self, params: dict[str, Any]) -> pd.DataFrame | None:
        cached = self._signal_cache.get(self._strategy_cache_key(params))
        if cached is None:
            return None
        return cached.copy()

    def optimize(
        self,
        n_trials: int = 50,
        show_progress: bool = True,
        name: str = "no_name",
    ) -> tuple[dict, optuna.Study]:
        study_kwargs = {}
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
