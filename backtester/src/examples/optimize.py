from multiprocessing import Pool

import numpy as np
import pandas as pd
from backtester.optimizer import ParameterOptimizer, TargetFunction
from backtester.results_analyzer import ResultsAnalyzer
from backtester.strategies.fractal_rb import FractalRbStrategy
from backtester.strategies.phase_routed import PhaseRoutedStrategy

# 1. Данные
data = {
    "SOL/USDT": pd.read_pickle(f".bingx-cache/6bbc897ffb61d40f4874a8922086ec501c6fee81669997bb002a8a230bf81ece.pkl"),
    # "SOL/USDT": pd.read_csv("data/validation/all_sol.csv"),
}


def target_total_return(analyzer: ResultsAnalyzer) -> float:
    """Цель: только полная доходность (%). Maximize."""
    m = analyzer.metrics
    return m.get("total_return_pct", -100)


def target_min_monthly_return(analyzer: ResultsAnalyzer) -> float:
    """Цель: худший месячный return (%). Maximize = стабильность по месяцам."""
    return min(
        map(
            lambda x: x["ret"],
            analyzer.metrics.get("monthly_returns_pct", {"ret": -100}).values(),
        )
    )


def target_max_drawdown(analyzer: ResultsAnalyzer) -> float:
    """Цель: максимальная просадка (%, отрицательное). Minimize |drawdown|."""
    return analyzer.metrics.get("max_drawdown", -100)


def target_total_trades(analyzer: ResultsAnalyzer) -> int:
    """Число сделок. Для штрафа за слишком мало сделок."""
    return analyzer.metrics.get("total_trades", 0)


def multi_obj(analyzer: ResultsAnalyzer) -> float:
    """
    Композитная цель: 0.5*return + 0.3*min_monthly + 0.2*drawdown. Maximize.

    Учитывает доходность, стабильность по месяцам и штраф за просадку (drawdown < 0).
    """
    ret = target_total_return(analyzer) / 100
    min_month = target_min_monthly_return(analyzer) / 100
    dd = target_max_drawdown(analyzer) / 100  # negative, e.g. -20
    return 0.5 * ret + 0.3 * min_month + 0.2 * dd


def target_calmar_ratio(analyzer: ResultsAnalyzer) -> float:
    """
    Цель: Calmar-подобный ratio — доходность / |просадка|. Maximize.

    Returns
    -------
    float
        total_return_pct / abs(max_drawdown); при отсутствии просадки — return / 1.
    """
    m = analyzer.metrics
    ret = m.get("total_return_pct", -100)
    dd = m.get("max_drawdown", -100)
    if dd >= 0:
        return ret / 1.0  # нет просадки — делим на 1
    return ret / abs(dd)


def target_return_over_drawdown_with_trades(analyzer: ResultsAnalyzer) -> float:
    """
    Цель: Calmar ratio минус штраф за мало сделок (< 20). Maximize.

    Даёт более устойчивые параметры за счёт отсечения стратегий с малым числом сделок.
    """
    calmar = target_calmar_ratio(analyzer)
    n = analyzer.metrics.get("total_trades", 0)
    if n < 20:
        penalty = (20 - n) * 0.1  # штраф за мало сделок
        return calmar - penalty
    return calmar


def target_sharpe_ratio(analyzer: ResultsAnalyzer) -> float:
    """
    Цель: годовой Sharpe ratio (доходность за единицу риска). Maximize.

    Использует sharpe_ratio из ResultsAnalyzer (месячные returns, annualized).
    """
    return analyzer.metrics.get("sharpe_ratio", -999.0)


def target_sharpe_with_trades_penalty(analyzer: ResultsAnalyzer) -> float:
    """
    Цель: Sharpe ratio минус штраф за мало сделок (< 30). Maximize.

    Предпочитает стратегии с гладкой кривой капитала и достаточной выборкой сделок.
    """
    sharpe = target_sharpe_ratio(analyzer)
    n = analyzer.metrics.get("total_trades", 0)
    if n < 30:
        penalty = (30 - n) * 0.05
        return sharpe - penalty
    return sharpe


# 3. Оптимизация
best_by_strategies = {}

for s in [
    # Example: optimize a single strategy class
    # FractalRbStrategy,
    PhaseRoutedStrategy,
    # Or iterate all registered strategies:
    # *STRATEGIES.values(),
]:
    # Рекомендуемые цели: target_calmar_ratio (риск/доходность),
    # target_return_over_drawdown_with_trades (+ штраф за мало сделок),
    # target_sharpe_ratio или target_sharpe_with_trades_penalty (гладкая кривая)
    optimizer = ParameterOptimizer(
        df=data["SOL/USDT"],
        strategy_class=s,
        target=TargetFunction(
            fn=target_sharpe_with_trades_penalty,  # или target_sharpe_ratio, target_sharpe_with_trades_penalty
            direction="maximize",
        ),
        initial_capital=10000,
        max_positions=1,
        position_ttl_bars=30,
        is_isolated_futures=True,
    )

    # optimizer.optimize(n_trials=200, name="som_2")

    def run_optimization(_):
        optimizer.optimize(n_trials=200, name="phase_routed")

    with Pool(processes=12) as pool:
        pool.map(
            run_optimization,
            range(12),
        )
    # best_by_strategies[s.__name__] = {
    #     "params": best_params,
    #     "study": study.best_value,
    # }

# print("Лучшие параметры:\n", pprint(best_by_strategies))
