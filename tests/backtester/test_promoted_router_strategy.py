from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

import backtester.cli_runner as cli_runner
import backtester.strategies.promoted_router as promoted_router_module
from backtester.registry import STRATEGIES
from backtester.strategies.promoted_router import PromotedRouterStrategy


def test_promoted_router_is_registered() -> None:
    assert STRATEGIES["promoted_router"] is PromotedRouterStrategy


def test_router_2687609_config_contains_full_six_strategy_universe() -> None:
    payload = json.loads(
        Path("strategies/archive/router_v2_2687609.json").read_text()
    )

    assert payload["name"] == "promoted_router"
    assert len(payload["params"]["strategy_paths"]) == 6
    assert payload["params"]["router"]["scoring_method"] == (
        "same_state_median_minus_dd"
    )
    assert payload["params"]["router"]["state_subset"] == "trend_structure"


def test_promoted_router_emits_selected_nested_strategy_params(monkeypatch) -> None:
    index = pd.date_range("2025-01-01", periods=3, freq="D", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.0, 101.0, 102.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=index,
    )

    def fake_load(path, _logger):
        strategy_id = str(path).split("/")[-1].removesuffix(".json")
        return SimpleNamespace(name="fake", params={"strategy_id": strategy_id})

    def fake_build(_name, params, *, logger):  # noqa: ARG001
        return SimpleNamespace(strategy_id=params["strategy_id"])

    def fake_args(cfg, **_kwargs):
        strategy_id = cfg.params["strategy_id"]
        if strategy_id == "a":
            return SimpleNamespace(
                risk_percent=0.5,
                rrr=1.5,
                ttl=10,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
            )
        return SimpleNamespace(
            risk_percent=1.25,
            rrr=2.0,
            ttl=20,
            trail_activation_rrr=2.0,
            trail_distance_atr=0.25,
            exit_geometry="tp_pct",
            tp_move_pct=0.02,
            structural_sl_mode="ignore",
            min_tp_move_pct=0.004,
        )

    def fake_run(*, df, strategy, args):  # noqa: ARG001
        signal = 1 if strategy.strategy_id == "a" else -1
        signals = primary.copy()
        signals["signal"] = signal
        signals["sl_price"] = 99.0 if signal == 1 else 103.0
        return SimpleNamespace(trades=pd.DataFrame(), signals=signals)

    monkeypatch.setattr(cli_runner, "load_strategy_config", fake_load)
    monkeypatch.setattr(cli_runner, "build_strategy_instance", fake_build)
    monkeypatch.setattr(cli_runner, "build_backtest_args", fake_args)
    monkeypatch.setattr(cli_runner, "run_backtest", fake_run)
    monkeypatch.setattr(
        promoted_router_module,
        "build_rolling_label_dataset_from_trades",
        lambda **_kwargs: pd.DataFrame({"asof": [index[1].isoformat()]}),
    )
    monkeypatch.setattr(
        promoted_router_module,
        "evaluate_frozen_router_candidate",
        lambda *_args, **_kwargs: pd.DataFrame(
            {
                "asof": [index[1].isoformat()],
                "selected_strategy": ["b"],
            }
        ),
    )

    strategy = PromotedRouterStrategy(
        {
            "router_id": "router_test",
            "fallback_strategy": "a",
            "min_available_strategies": 2,
            "router": {
                "scoring_method": "same_state_median_minus_dd",
                "lookback_days": 180,
                "state_subset": "trend_structure",
                "state_match_mode": "exact",
                "min_samples": 10,
                "min_hold_days": 60,
                "switch_margin_threshold": 0.5,
            },
            "strategy_paths": {"a": "nested/a.json", "b": "nested/b.json"},
        }
    )

    result = strategy.generate(primary)

    assert result["selected_strategy"].tolist() == ["a", "b", "b"]
    assert result["signal"].tolist() == [1, -1, -1]
    assert result["risk_percent"].tolist() == [0.5, 1.25, 1.25]
    assert result["position_ttl_bars"].tolist() == [10, 20, 20]
    assert result["exit_geometry"].tolist() == ["sl_rrr", "tp_pct", "tp_pct"]
    assert result["position_group"].tolist() == ["a", "b", "b"]
    assert result["drain_on_group_change"].all()
