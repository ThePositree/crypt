import logging
from dataclasses import dataclass
from typing import Callable, Literal

import optuna
import pandas as pd
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend

from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategy import BaseStrategy
from backtester.tester import Backtester


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
        risk_free_rate_annual: float = 0.02,
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
        self.risk_free_rate_annual = risk_free_rate_annual
        self._logger = logging.getLogger(__name__)

    def _objective(self, trial: optuna.Trial) -> float:
        try:
            # 1. Подбираем ПАРАМЕТРЫ СТРАТЕГИИ
            strategy_params = self.strategy_class.suggest_params(None, trial)
            strategy_instance = self.strategy_class(strategy_params)

            def strategy(df):
                return strategy_instance.generate(df)

            # 2. Подбираем ПАРАМЕТРЫ РИСКА (относятся к тестеру)
            risk_percent = trial.suggest_float("risk_percent", 0.1, 0.5, step=0.1)
            rrr = trial.suggest_float("rrr", 1.0, 5.0, step=1)

            # 3. Подбираем лимиты по дню и окно торговли (ExecutionSim)
            max_daily_profit = trial.suggest_float(
                "max_daily_profit", rrr, 15.0, step=1
            )
            max_daily_loss = trial.suggest_float(
                "max_daily_loss", max(1, rrr//2), min(5.0, max_daily_profit), step=1
            )
            trading_begin = trial.suggest_int("trading_begin", 0, 20)
            trading_end = trial.suggest_int("trading_end", trading_begin+3, 24)

            # 4. Запускаем бэктест
            bt = Backtester(self.df, strategy)
            results = bt.run(
                initial_capital=self.initial_capital,
                taker_fee=self.taker_fee,
                maker_fee=self.maker_fee,
                risk_percent=risk_percent,
                rrr=rrr,
                max_positions=self.max_positions,
                position_ttl_bars=self.position_ttl_bars,
                min_net_exposure=self.min_net_exposure,
                is_isolated_futures=self.is_isolated_futures,
                max_allowed_margin=self.max_allowed_margin,
                max_daily_profit=max_daily_profit,
                max_daily_loss=max_daily_loss,
                trading_begin=trading_begin,
                trading_end=trading_end,
                risk_free_rate_annual=self.risk_free_rate_annual,
            )

            m = results.metrics
            trial.set_user_attr("total_return_pct", m.get("total_return_pct", -100))
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

        storage = JournalStorage(JournalFileBackend(f"{name}.log"))
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
