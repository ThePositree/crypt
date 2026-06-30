from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

import backtester.strategies.filtered_donor_portfolio as filtered_portfolio_module
from backtester import cli_runner
from backtester.cli_runner import BacktestArgs, StrategyConfig
from backtester.data_contracts import StrategyData
from backtester.router_runtime import ArchivedStrategySpec
from backtester.strategies.filtered_donor_portfolio import (
    FilteredDonorPortfolioStrategy,
    PortfolioFilterRule,
    _catalog_features,
    _validate_filter_features_available,
)
from backtester.tester import Backtester


def test_backtester_accepts_signal_events_without_scalar_signal_columns() -> None:
    data = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    def strategy(frame: pd.DataFrame) -> pd.DataFrame:
        output = frame.copy()
        output["signal_events"] = [
            [
                {"signal": 1, "sl_price": 99.0, "selected_strategy": "alpha"},
                {"signal": 1, "sl_price": 98.0, "selected_strategy": "beta"},
            ],
            [],
            [],
        ]
        return output

    result = Backtester(data, strategy).run(
        initial_capital=10_000.0,
        max_positions=0,
    )

    trades = result.get_trades()
    assert len(trades) == 2
    assert trades["selected_strategy"].tolist() == ["alpha", "beta"]


def test_filtered_portfolio_catalog_features_use_previous_closed_bar() -> None:
    index = pd.date_range("2026-01-01 00:00", periods=40, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(len(index))],
            "high": [101.0 + i for i in range(len(index))],
            "low": [99.0 + i for i in range(len(index))],
            "close": [100.5 + i for i in range(len(index))],
            "volume": [1_000.0 + i for i in range(len(index))],
        },
        index=index,
    )

    catalog = _catalog_features(primary)

    assert pd.isna(catalog.iloc[0]["catalog_bb_width_pct"])
    assert catalog.iloc[1]["entry_hour"] == 1
    assert catalog.iloc[1]["entry_dayofweek"] == index[1].dayofweek


def test_filtered_portfolio_rejects_unavailable_filter_features() -> None:
    frames = {"alpha": pd.DataFrame({"signal": [1], "catalog_bb_width_pct": [0.02]})}
    filters = {
        "alpha": [
            PortfolioFilterRule("catalog_bb_width_pct", ">=", 0.01),
            PortfolioFilterRule("confidence", "<=", 7.0),
        ]
    }

    with pytest.raises(ValueError, match="alpha: confidence"):
        _validate_filter_features_available(frames, filters)


def test_filtered_portfolio_passes_nested_backtest_defaults_to_donor_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.date_range("2026-01-01 00:00", periods=20, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.0] * len(index),
            "volume": [1.0] * len(index),
        },
        index=index,
    )
    captured_kwargs: dict[str, object] = {}
    original_build_backtest_args = cli_runner.build_backtest_args

    def fake_load_strategy_config(_path: str, _logger: object) -> StrategyConfig:
        return StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={"risk_percent": 0.5},
        )

    def fake_build_backtest_args(
        cfg: StrategyConfig | None,
        **kwargs: object,
    ) -> BacktestArgs:
        captured_kwargs.update(kwargs)
        return original_build_backtest_args(cfg, **kwargs)

    monkeypatch.setattr(cli_runner, "load_strategy_config", fake_load_strategy_config)
    monkeypatch.setattr(cli_runner, "build_backtest_args", fake_build_backtest_args)
    monkeypatch.setattr(
        filtered_portfolio_module,
        "build_archived_signal_frames",
        lambda **_kwargs: {"alpha": primary.assign(signal=0, sl_price=0.0)},
    )

    strategy = FilteredDonorPortfolioStrategy(
        {
            "progress": False,
            "strategy_paths": {"alpha": "nested/alpha.json"},
            "nested_backtest_args": {
                "maintenance_margin_rate": 0.004,
                "liquidation_fee_rate": 0.0005,
                "liquidation_buffer_pct": 0.005,
                "maintenance_margin_tier_schedule": "okx_sol_usdt_swap_2026_06_29",
            },
        }
    )

    strategy.generate(primary)

    assert captured_kwargs["maintenance_margin_tier_schedule"] == (
        "okx_sol_usdt_swap_2026_06_29"
    )
    assert captured_kwargs["maintenance_margin_rate"] == 0.004


def test_filtered_portfolio_latest_cache_appends_only_validated_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.date_range("2026-01-01", periods=601, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.5] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    calls: list[int] = []

    def fake_frames(
        *,
        data: pd.DataFrame | StrategyData,
        specs: list[ArchivedStrategySpec],
        dataset: object = None,  # noqa: ARG001
    ) -> dict[str, pd.DataFrame]:
        frame = data.primary if isinstance(data, StrategyData) else data
        calls.append(len(frame))
        output = frame.copy()
        output["signal"] = 1
        output["sl_price"] = output["low"]
        return {specs[0].strategy_id: output}

    monkeypatch.setattr(
        filtered_portfolio_module,
        "build_archived_signal_frames",
        fake_frames,
    )
    strategy = FilteredDonorPortfolioStrategy(
        {
            "progress": False,
            "strategy_paths": {"alpha": "unused.json"},
        }
    )
    spec = ArchivedStrategySpec(
        strategy_id="alpha",
        name="dummy",
        params={},
        execution=SimpleNamespace(),
    )
    monkeypatch.setattr(strategy, "_get_specs", lambda: (spec,))

    first_data = StrategyData(
        primary=primary.iloc[:600],
        candles={"H1": primary.iloc[:600]},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    appended_data = StrategyData(
        primary=primary,
        candles={"H1": primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )

    first = strategy.generate_latest(first_data)
    appended = strategy.generate_latest(appended_data)

    assert calls == [600, 513]
    assert first.iloc[-1]["signal_events"][0]["selected_strategy"] == "alpha"
    assert appended.iloc[-1]["signal_events"][0]["selected_strategy"] == "alpha"
    assert appended.iloc[-1]["signal_events"][0]["sl_price"] == 99.0


def test_filtered_portfolio_latest_cache_rebuilds_after_history_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.date_range("2026-01-01", periods=601, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.5] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    calls: list[int] = []

    def fake_frames(
        *,
        data: pd.DataFrame | StrategyData,
        specs: list[ArchivedStrategySpec],
        dataset: object = None,  # noqa: ARG001
    ) -> dict[str, pd.DataFrame]:
        frame = data.primary if isinstance(data, StrategyData) else data
        calls.append(len(frame))
        output = frame.assign(signal=0, sl_price=0.0)
        return {specs[0].strategy_id: output}

    monkeypatch.setattr(
        filtered_portfolio_module,
        "build_archived_signal_frames",
        fake_frames,
    )
    strategy = FilteredDonorPortfolioStrategy(
        {
            "progress": False,
            "strategy_paths": {"alpha": "unused.json"},
        }
    )
    spec = ArchivedStrategySpec(
        strategy_id="alpha",
        name="dummy",
        params={},
        execution=SimpleNamespace(),
    )
    monkeypatch.setattr(strategy, "_get_specs", lambda: (spec,))

    initial = StrategyData(
        primary=primary.iloc[:600],
        candles={"H1": primary.iloc[:600]},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    revised_primary = primary.copy()
    revised_primary.iloc[100, revised_primary.columns.get_loc("close")] = 101.0
    revised = StrategyData(
        primary=revised_primary,
        candles={"H1": revised_primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )

    strategy.generate_latest(initial)
    strategy.generate_latest(revised)

    assert calls == [600, 601]
