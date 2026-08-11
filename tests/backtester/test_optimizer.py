from __future__ import annotations

import json
from typing import Any, ClassVar

import optuna
import pandas as pd
import pytest

from backtester import cli_runner
from backtester import optimizer as optimizer_mod
from backtester.cli_runner import (
    BacktestArgs,
    OptimizerSearchArgs,
    StrategyConfig,
    backtest_run_kwargs,
    build_backtest_args,
    run_parameter_optimization,
)
from backtester.fast_exit_optimizer import FastExitGeometryEvaluator
from backtester.optimizer import ParameterOptimizer, TargetFunction, _mandate_score
from backtester.strategy import BaseStrategy


class _DummyStrategy(BaseStrategy):
    seen_params: ClassVar[dict[str, Any]] = {}
    generate_calls = 0

    def __init__(self, params: dict[str, Any]):
        super().__init__(params)
        type(self).seen_params = params

    def generate(self, data):
        type(self).generate_calls += 1
        return data

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:
        return {"suggested": trial.suggest_int("suggested", 1, 3)}


class _DummyResults:
    metrics: ClassVar[dict[str, Any]] = {
        "total_return_pct": 1.5,
        "monthly_returns_pct": {"2025-01": {"ret": 1.5}},
        "max_drawdown": -2.0,
        "total_trades": 3,
        "sharpe_ratio": 0.1,
    }


def test_fast_exit_evaluator_honors_monthly_risk_base_period() -> None:
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0, 101.0, 101.0],
            "low": [89.0, 89.0, 89.0, 89.0, 89.0],
            "close": [100.0, 100.0, 100.0, 100.0, 100.0],
            "signal": [1, 0, 1, 0, 0],
            "sl_price": [90.0, None, 90.0, None, None],
        },
        index=pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC"),
    )
    common_kwargs = {
        "signal_df": df,
        "initial_capital": 1000.0,
        "taker_fee": 0.0,
        "candle_timeframe": "1h",
        "risk_free_rate_annual": 0.0,
    }

    monthly = FastExitGeometryEvaluator(
        **common_kwargs,
        risk_base_period="monthly",
    ).evaluate(
        risk_percent=10.0,
        rrr=1.0,
        exit_family="sl_rrr",
        position_ttl_bars=1,
        trail_distance_atr=0.0,
        tp_move_pct=None,
    )
    trade = FastExitGeometryEvaluator(
        **common_kwargs,
        risk_base_period="trade",
    ).evaluate(
        risk_percent=10.0,
        rrr=1.0,
        exit_family="sl_rrr",
        position_ttl_bars=1,
        trail_distance_atr=0.0,
        tp_move_pct=None,
    )

    assert monthly.metrics["final_capital"] == pytest.approx(800.0)
    assert trade.metrics["final_capital"] == pytest.approx(810.0)


def test_fast_exit_evaluator_trailing_activation_is_not_take_profit() -> None:
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 110.0, 110.0],
            "high": [100.0, 110.0, 112.0, 110.0],
            "low": [100.0, 109.0, 106.0, 110.0],
            "close": [100.0, 110.0, 107.0, 110.0],
            "signal": [1, 0, 0, 0],
            "sl_price": [90.0, None, None, None],
            "trail_atr": [5.0, 5.0, 5.0, 5.0],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC"),
    )

    result = FastExitGeometryEvaluator(
        signal_df=df,
        initial_capital=1000.0,
        taker_fee=0.0,
        candle_timeframe="1h",
        risk_base_period="trade",
        risk_free_rate_annual=0.0,
    ).evaluate(
        risk_percent=10.0,
        rrr=1.0,
        exit_family="sl_rrr_trailing",
        position_ttl_bars=3,
        trail_distance_atr=1.0,
        tp_move_pct=None,
    )

    assert result.metrics["final_capital"] == pytest.approx(1070.0)


def test_build_backtest_args_accepts_position_ttl_bars_alias() -> None:
    args = build_backtest_args(
        StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={
                "position_ttl_bars": 56,
                "rrr": 2.0,
                "trail_distance_atr": 0.25,
            },
        ),
        capital=10000.0,
        risk_percent=1.0,
        rrr=1.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=0,
        ttl_minutes=0,
        max_positions=3,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
    )

    assert args.ttl == 56
    assert args.ttl_minutes == 56 * 60
    assert args.rrr == 2.0
    assert args.trail_distance_atr == 0.25
    assert args.trail_activation_rrr == 2.0
    assert args.max_positions == 0


def test_backtest_run_kwargs_preserve_ttl_minutes() -> None:
    args = build_backtest_args(
        None,
        candle_timeframe="4h",
        capital=10_000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=32,
        ttl_minutes=7_560,
        max_positions=0,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
    )

    kwargs = backtest_run_kwargs(args)

    assert kwargs["position_ttl_bars"] == 32
    assert kwargs["position_ttl_minutes"] == 7_560


def test_build_backtest_args_ignores_null_strategy_file_window_over_cli_window() -> None:
    args = build_backtest_args(
        StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={
                "execution_start": None,
                "execution_end": None,
            },
        ),
        capital=10_000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=0,
        ttl_minutes=0,
        max_positions=0,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
        execution_start="2021-12-18T00:00:00Z",
        execution_end="2026-06-29T14:00:00Z",
    )

    assert args.execution_start == "2021-12-18T00:00:00Z"
    assert args.execution_end == "2026-06-29T14:00:00Z"


def test_build_backtest_args_uses_flat_dss_params_as_execution_defaults() -> None:
    args = build_backtest_args(
        StrategyConfig(
            name="dss_strategy",
            version="test",
            params={
                "risk_percent": 0.5,
                "rrr": 6.0,
                "trail_distance_atr": 0.25,
                "position_ttl_bars": 92,
                "trigger_name": "pt_ps_macd_signal_cross",
            },
            backtest_args={},
        ),
        capital=10000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=0,
        ttl_minutes=0,
        max_positions=3,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
    )

    assert args.risk_percent == 0.5
    assert args.rrr == 6.0
    assert args.trail_distance_atr == 0.25
    assert args.trail_activation_rrr == 6.0
    assert args.ttl == 92
    assert args.ttl_minutes == 92 * 60
    assert args.max_positions == 0


def test_build_backtest_args_backtest_args_override_flat_dss_params() -> None:
    args = build_backtest_args(
        StrategyConfig(
            name="dss_strategy",
            version="test",
            params={
                "risk_percent": 0.5,
                "rrr": 6.0,
                "trail_distance_atr": 0.25,
                "position_ttl_bars": 92,
            },
            backtest_args={
                "risk_percent": 0.75,
                "rrr": 3.0,
                "trail_distance_atr": 0.5,
                "position_ttl_bars": 44,
            },
        ),
        capital=10000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=0,
        ttl_minutes=0,
        max_positions=3,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
    )

    assert args.risk_percent == 0.75
    assert args.rrr == 3.0
    assert args.trail_distance_atr == 0.5
    assert args.trail_activation_rrr == 3.0
    assert args.ttl == 44
    assert args.ttl_minutes == 44 * 60


def test_parameter_optimizer_can_suggest_ttl_and_merge_base_strategy_params(
    monkeypatch,
):
    captured: dict[str, Any] = {}

    class Backtester:
        def __init__(self, df, strategy, **_kwargs):
            captured["df"] = df
            captured["strategy"] = strategy

        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs
            captured["strategy"](captured["df"])
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        strategy_params={"baseline": True},
        optimize_strategy_params=True,
        risk_percent_range=None,
        rrr_range=(1.0, 1.5, 0.25),
        position_ttl_minutes_range=(24 * 60, 48 * 60, 12 * 60),
        optimize_daily_limits=False,
        optimize_trading_window=False,
        risk_base_period="monthly",
    )

    _DummyStrategy.generate_calls = 0
    value = optimizer._objective(
        optuna.trial.FixedTrial(
            {
                "suggested": 2,
                "rrr": 1.25,
                "max_positions": 2,
                "position_ttl_minutes": 36 * 60,
            }
        )
    )

    assert value == 1.5
    assert _DummyStrategy.seen_params == {"baseline": True, "suggested": 2}
    assert _DummyStrategy.generate_calls == 1
    assert captured["run_kwargs"]["risk_percent"] == 1.0
    assert captured["run_kwargs"]["rrr"] == 1.25
    assert captured["run_kwargs"]["max_positions"] == 0
    assert captured["run_kwargs"]["position_ttl_bars"] == 36
    assert captured["run_kwargs"]["risk_base_period"] == "monthly"
    assert captured["run_kwargs"]["max_daily_profit"] is None
    assert captured["run_kwargs"]["max_daily_loss"] is None
    assert captured["run_kwargs"]["trading_begin"] is None
    assert captured["run_kwargs"]["trading_end"] is None


def test_parameter_optimizer_can_skip_strategy_param_search_and_reuse_signals(
    monkeypatch,
):
    class Backtester:
        def __init__(self, df, strategy, **_kwargs):
            self.df = df
            self.strategy = strategy

        def run(self, **_kwargs):
            self.strategy(self.df)
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        strategy_params={"baseline": True},
        optimize_strategy_params=False,
        risk_percent_range=None,
        rrr_range=(1.0, 1.5, 0.25),
        position_ttl_minutes_range=(24 * 60, 48 * 60, 12 * 60),
        optimize_daily_limits=False,
        optimize_trading_window=False,
    )

    _DummyStrategy.generate_calls = 0
    optimizer._objective(
        optuna.trial.FixedTrial({"rrr": 1.25, "position_ttl_minutes": 36 * 60})
    )
    optimizer._objective(
        optuna.trial.FixedTrial({"rrr": 1.5, "position_ttl_minutes": 48 * 60})
    )

    assert _DummyStrategy.seen_params == {"baseline": True}
    assert _DummyStrategy.generate_calls == 1


def test_parameter_optimizer_activates_trailing_at_selected_rrr(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    class Backtester:
        def __init__(self, df, strategy, **_kwargs):
            captured["df"] = df
            captured["strategy"] = strategy

        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs
            captured["strategy"](captured["df"])
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        strategy_params={"baseline": True},
        optimize_strategy_params=False,
        risk_percent_range=None,
        rrr_range=(2.0, 4.0, 0.25),
        trail_distance_atr_range=(0.5, 1.0, 0.25),
        optimize_daily_limits=False,
        optimize_trading_window=False,
        exit_geometry="sl_rrr",
    )

    value = optimizer._objective(
        optuna.trial.FixedTrial({"rrr": 2.75, "trail_distance_atr": 0.5})
    )

    assert value == 1.5
    assert captured["run_kwargs"]["rrr"] == 2.75
    assert captured["run_kwargs"]["trail_activation_rrr"] == 2.75
    assert captured["run_kwargs"]["trail_distance_atr"] == 0.5


def test_parameter_optimizer_disables_trailing_when_atr_distance_is_zero(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    class Backtester:
        def __init__(self, df, strategy, **_kwargs):
            captured["df"] = df
            captured["strategy"] = strategy

        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs
            captured["strategy"](captured["df"])
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        strategy_params={"baseline": True},
        optimize_strategy_params=False,
        risk_percent_range=None,
        rrr_range=(3.0, 4.0, 0.25),
        trail_distance_atr=0.0,
        trail_distance_atr_range=None,
        optimize_daily_limits=False,
        optimize_trading_window=False,
        exit_geometry="sl_rrr",
    )

    value = optimizer._objective(
        optuna.trial.FixedTrial(
            {
                "rrr": 3.5,
            }
        )
    )

    assert value == 1.5
    assert captured["run_kwargs"]["trail_activation_rrr"] == 0.0
    assert captured["run_kwargs"]["trail_distance_atr"] == 0.0


def test_run_parameter_optimization_exports_trials_and_best_run(
    monkeypatch,
    tmp_path,
):
    captured: dict[str, Any] = {}

    class _FakeTrial:
        number = 7
        value = 1.25
        user_attrs: ClassVar[dict[str, Any]] = {"total_trades": 4}

    class _FakeStudy:
        best_trial = _FakeTrial()

        def trials_dataframe(self):
            return pd.DataFrame([{"number": 7, "value": 1.25}])

    class _FakeOptimizer:
        def __init__(self, **kwargs):
            captured["optimizer_kwargs"] = kwargs

        def optimize(self, **kwargs):
            captured["optimize_kwargs"] = kwargs
            return {
                "rrr": 1.5,
                "trail_distance_atr": 1.5,
                "max_positions": 3,
                "position_ttl_minutes": 30 * 60,
                "tp_move_pct": 0.012,
            }, _FakeStudy()

        def cached_signals_for_params(self, params, *, execution_context=None):
            captured["cached_params"] = params
            captured["cached_execution_context"] = execution_context
            return df.assign(signal=0, sl_price=0.0)

    class _FakeResults:
        def export_results(self, folder, ohlcv_df):
            captured["best_run_folder"] = folder
            captured["best_run_rows"] = len(ohlcv_df)
            path = tmp_path / "export_marker.txt"
            path.write_text(folder)

    def fake_run_backtest(**_kwargs):
        raise AssertionError("cached best-run export should not regenerate signals")

    class _FakeBacktester:
        def __init__(self, df, strategy, **_kwargs):
            captured["best_df"] = df
            captured["best_strategy_fn"] = strategy

        def run(self, **kwargs):
            captured["best_run_kwargs"] = kwargs
            generated = captured["best_strategy_fn"](captured["best_df"])
            captured["best_signal_columns"] = generated.columns.tolist()
            return _FakeResults()

    monkeypatch.setitem(cli_runner.STRATEGIES, "dummy", _DummyStrategy)
    monkeypatch.setattr(cli_runner, "ParameterOptimizer", _FakeOptimizer)
    monkeypatch.setattr(cli_runner, "run_backtest", fake_run_backtest)
    monkeypatch.setattr(cli_runner, "Backtester", _FakeBacktester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    run_parameter_optimization(
        df=df,
        ohlcv=df,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={"baseline": True},
            backtest_args={},
        ),
        backtest_args=BacktestArgs(
            capital=10000.0,
            risk_percent=0.75,
            rrr=1.0,
            trail_activation_rrr=0.0,
            trail_distance_atr=0.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            ttl=24,
            ttl_minutes=24 * 60,
            max_positions=0,
            max_allowed_leverage=25.0,
            max_allowed_margin=1.0,
            risk_base_period="monthly",
            exit_geometry="tp_pct",
            structural_sl_mode="ignore",
        ),
        optimizer_args=OptimizerSearchArgs(
            trials=3,
            study_name="study",
            target="mandate_score",
            show_progress=False,
            optimize_strategy_params=False,
            risk_percent_range=None,
            rrr_range=(1.0, 2.0, 0.25),
            trail_distance_atr_range=(1.0, 2.0, 0.5),
            position_ttl_minutes_range=(24 * 60, 48 * 60, 6 * 60),
            tp_move_pct_range=None,
            exit_family_search=False,
            exit_families=("sl_rrr", "sl_rrr_trailing", "tp_pct"),
            optimize_daily_limits=False,
            optimize_trading_window=False,
            export_best_run=True,
        ),
        output_folder=str(tmp_path),
        logger=optimizer_mod.logging.getLogger(__name__),
    )

    assert (tmp_path / "trials.csv").exists()
    assert (tmp_path / "best_trial.json").exists()
    assert (tmp_path / "best_geometry_summary.txt").exists()
    optimized_strategy = json.loads((tmp_path / "optimized_strategy.json").read_text())
    assert optimized_strategy["name"] == "dummy"
    assert optimized_strategy["params"] == {"baseline": True}
    assert optimized_strategy["backtest_args"]["risk_percent"] == pytest.approx(0.75)
    assert optimized_strategy["backtest_args"]["rrr"] == pytest.approx(1.5)
    assert optimized_strategy["backtest_args"]["ttl_minutes"] == 30 * 60
    assert optimized_strategy["backtest_args"]["position_ttl_bars"] == 30
    assert optimized_strategy["backtest_args"]["exit_geometry"] == "tp_pct"
    assert optimized_strategy["backtest_args"]["tp_move_pct"] == pytest.approx(0.012)
    assert optimized_strategy["optuna_source"]["best_trial"] == str(tmp_path / "best_trial.json")
    assert captured["optimizer_kwargs"]["strategy_params"] == {"baseline": True}
    assert captured["optimizer_kwargs"]["risk_percent"] == 0.75
    assert captured["optimizer_kwargs"]["trail_distance_atr_range"] == (1.0, 2.0, 0.5)
    assert captured["optimize_kwargs"]["n_trials"] == 3
    assert captured["cached_params"] == {"baseline": True}
    assert captured["best_run_kwargs"]["rrr"] == 1.5
    assert captured["best_run_kwargs"]["trail_activation_rrr"] == 0.0
    assert captured["best_run_kwargs"]["trail_distance_atr"] == 0.0
    assert captured["best_run_kwargs"]["max_positions"] == 0
    assert captured["best_run_kwargs"]["position_ttl_bars"] == 30
    assert captured["best_run_kwargs"]["exit_geometry"] == "tp_pct"
    assert captured["best_run_kwargs"]["tp_move_pct"] == pytest.approx(0.012)
    assert captured["best_run_kwargs"]["structural_sl_mode"] == "ignore"
    assert captured["cached_execution_context"] is not None
    assert captured["cached_execution_context"].exit_geometry == "tp_pct"
    assert "signal" in captured["best_signal_columns"]
    assert captured["best_run_folder"] == str(tmp_path / "best_run")
    assert captured["best_run_rows"] == 1


def test_parameter_optimizer_suggests_tp_move_pct_when_range_enabled(monkeypatch):
    captured: dict[str, Any] = {}

    class Backtester:
        def __init__(self, _df, strategy, **_kwargs):
            captured["strategy"] = strategy

        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        optimize_strategy_params=False,
        risk_percent_range=None,
        rrr_range=(1.0, 1.5, 0.25),
        position_ttl_minutes_range=None,
        tp_move_pct_range=(0.008, 0.016, 0.004),
        exit_geometry="sl_rrr",
        optimize_daily_limits=False,
        optimize_trading_window=False,
    )

    value = optimizer._objective(
        optuna.trial.FixedTrial({"rrr": 1.25, "tp_move_pct": 0.012})
    )

    assert value == 1.5
    assert captured["run_kwargs"]["exit_geometry"] == "tp_pct"
    assert captured["run_kwargs"]["tp_move_pct"] == pytest.approx(0.012)


def test_parameter_optimizer_default_geometry_family_search(monkeypatch):
    captured: dict[str, Any] = {}

    class Backtester:
        def __init__(self, _df, strategy, **_kwargs):
            captured.setdefault("strategies", []).append(strategy)

        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs
            return _DummyResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=pd.to_datetime(["2025-01-01"], utc=True),
    )
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda results: float(results.metrics["total_return_pct"]),
            direction="maximize",
        ),
        optimize_strategy_params=False,
        risk_percent_range=(0.25, 3.0, 0.25),
        rrr_range=(1.0, 10.0, 0.25),
        trail_distance_atr_range=(0.5, 10.0, 0.5),
        position_ttl_minutes_range=(60, 10_080, 60),
        tp_move_pct_range=(0.004, 0.14, 0.002),
        exit_family_search=True,
        optimize_daily_limits=False,
        optimize_trading_window=False,
    )

    trial = optuna.trial.FixedTrial(
        {
            "exit_family": "tp_pct",
            "risk_percent": 1.25,
            "rrr": 4.5,
            "position_ttl_minutes": 720,
            "tp_move_pct": 0.028,
        }
    )

    value = optimizer._objective(trial)

    assert value == 1.5
    assert captured["run_kwargs"]["exit_geometry"] == "tp_pct"
    assert captured["run_kwargs"]["tp_move_pct"] == pytest.approx(0.028)
    assert captured["run_kwargs"]["trail_distance_atr"] == 0.0
    assert captured["run_kwargs"]["risk_percent"] == pytest.approx(1.25)
    assert captured["run_kwargs"]["rrr"] == pytest.approx(4.5)
    assert captured["run_kwargs"]["position_ttl_bars"] == 12
    assert trial.user_attrs["exit_family"] == "tp_pct"
    assert trial.user_attrs["position_ttl_minutes"] == 720


def test_parameter_optimizer_mandate_score_uses_monthly_floor_and_dd(monkeypatch):
    class _MandateResults:
        metrics: ClassVar[dict[str, Any]] = {
            "total_return_pct": 80.0,
            "monthly_returns_pct": {"2025-01": {"ret": 80.0}},
            "max_drawdown": -12.0,
            "total_trades": 2,
            "sharpe_ratio": 0.5,
        }
        trades = pd.DataFrame(
            [
                {
                    "entry_time": "2025-01-10T00:00:00Z",
                    "exit_time": "2025-01-10T04:00:00Z",
                    "pnl_abs": 2000.0,
                    "exit_reason": "take_profit",
                },
                {
                    "entry_time": "2025-02-10T00:00:00Z",
                    "exit_time": "2025-02-10T04:00:00Z",
                    "pnl_abs": -1200.0,
                    "exit_reason": "stop_loss",
                },
            ]
        )

    class Backtester:
        def __init__(self, df, strategy, **_kwargs):
            self.df = df
            self.strategy = strategy

        def run(self, **_kwargs):
            self.strategy(self.df)
            return _MandateResults()

    monkeypatch.setattr(optimizer_mod, "Backtester", Backtester)

    df = pd.DataFrame(
        {
            "open": [1.0, 1.0],
            "high": [1.0, 1.0],
            "low": [1.0, 1.0],
            "close": [1.0, 1.0],
            "volume": [1.0, 1.0],
        },
        index=pd.to_datetime(["2025-01-01", "2025-02-28"], utc=True),
    )
    trial = optuna.trial.FixedTrial({"rrr": 1.25})
    optimizer = ParameterOptimizer(
        df=df,
        ohlcv=df,
        strategy_class=_DummyStrategy,
        target=TargetFunction(
            fn=lambda _results: -999.0,
            direction="maximize",
            name="mandate_score",
        ),
        initial_capital=10000.0,
        optimize_strategy_params=False,
        risk_percent_range=None,
        rrr_range=(1.0, 1.5, 0.25),
        position_ttl_minutes_range=None,
        optimize_daily_limits=False,
        optimize_trading_window=False,
    )

    value = optimizer._objective(trial)

    assert value == pytest.approx(-4420.5)
    assert trial.user_attrs["mandate_score"] == pytest.approx(-4420.5)
    assert trial.user_attrs["mandate_months_passing_floor"] == 1
    assert trial.user_attrs["mandate_months_below_floor"] == 1
    assert trial.user_attrs["mandate_dd_breach_months"] == 1
    assert trial.user_attrs["mandate_sum_capped_monthly_return_pct"] == pytest.approx(8.0)
    assert trial.user_attrs["min_monthly_return"] == pytest.approx(-12.0)


def test_mandate_score_prefers_lower_drawdown_when_money_is_still_good() -> None:
    higher_return_higher_dd = _mandate_score(
        total_return_pct=67.16,
        max_drawdown_pct=-6.45,
        peak_to_trough_drawdown_pct=-24.55,
        sum_capped_monthly_return_pct=51.79,
        monthly_shortfall_pct=807.55,
        dd_excess_pct=0.0,
        months_below_floor=48,
        dd_breach_months=4,
        worst_consecutive_losing_months=3,
    )
    lower_return_lower_dd = _mandate_score(
        total_return_pct=55.0,
        max_drawdown_pct=-3.5,
        peak_to_trough_drawdown_pct=-14.0,
        sum_capped_monthly_return_pct=45.0,
        monthly_shortfall_pct=850.0,
        dd_excess_pct=0.0,
        months_below_floor=48,
        dd_breach_months=2,
        worst_consecutive_losing_months=3,
    )

    assert lower_return_lower_dd > higher_return_higher_dd
