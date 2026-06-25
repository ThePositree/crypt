from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import backtester.cli_runner as cli_runner
import backtester.strategies.promoted_router as promoted_router_module
from backtester.registry import STRATEGIES
from backtester.strategies.promoted_router import PromotedRouterStrategy


def _execution(**overrides):
    values = {
        "capital": 10_000.0,
        "risk_percent": 1.0,
        "rrr": 2.0,
        "trail_activation_rrr": 0.0,
        "trail_distance_atr": 0.0,
        "maker_fee": 0.0002,
        "taker_fee": 0.0005,
        "ttl": 0,
        "max_positions": 0,
        "max_allowed_leverage": 25.0,
        "max_allowed_margin": 1.0,
        "risk_base_period": "monthly",
        "max_daily_profit": None,
        "max_daily_loss": None,
        "trading_begin": None,
        "trading_end": None,
        "exit_geometry": "sl_rrr",
        "tp_move_pct": None,
        "structural_sl_mode": "cap",
        "min_tp_move_pct": 0.004,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_promoted_router_is_registered() -> None:
    assert STRATEGIES["promoted_router"] is PromotedRouterStrategy


def test_promoted_router_requires_frozen_validation_start() -> None:
    with pytest.raises(ValueError, match=r"router\.validation_start is required"):
        PromotedRouterStrategy(
            {
                "router_id": "router_test",
                "labels_path": "labels.csv",
                "fallback_strategy": "selected",
                "router": {
                    "scoring_method": "rolling_median",
                    "lookback_days": 180,
                },
                "strategy_paths": {"selected": "nested/selected.json"},
            }
        )


def test_router_2687609_config_contains_full_six_strategy_universe() -> None:
    payload = json.loads(Path("strategies/archive/router_v2_2687609.json").read_text())

    assert payload["name"] == "promoted_router"
    assert len(payload["params"]["strategy_paths"]) == 6
    assert payload["params"]["router"]["scoring_method"] == ("same_state_median_minus_dd")
    assert payload["params"]["router"]["validation_start"] == "2024-01-01"
    assert payload["params"]["router"]["state_subset"] == "trend_structure"
    assert payload["params"]["progress"] is True
    assert payload["params"]["labels_path"].endswith("rolling_labels.csv")


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

    def fake_args(cfg, **_kwargs):
        strategy_id = cfg.params["strategy_id"]
        if strategy_id == "a":
            return _execution(
                risk_percent=0.5,
                rrr=1.5,
                ttl=10,
            )
        return _execution(
            risk_percent=1.25,
            rrr=2.0,
            ttl=20,
            trail_activation_rrr=2.0,
            trail_distance_atr=0.25,
            exit_geometry="tp_pct",
            tp_move_pct=0.02,
            structural_sl_mode="ignore",
        )

    monkeypatch.setattr(cli_runner, "load_strategy_config", fake_load)
    monkeypatch.setattr(cli_runner, "build_backtest_args", fake_args)
    monkeypatch.setattr(
        promoted_router_module,
        "build_archived_signal_frames",
        lambda **_kwargs: {
            "a": primary.assign(signal=1, sl_price=99.0),
            "b": primary.assign(signal=-1, sl_price=103.0),
        },
    )
    monkeypatch.setattr(
        PromotedRouterStrategy,
        "_load_labels",
        lambda _self: pd.DataFrame({"asof": [index[1].isoformat()]}),
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
            "labels_path": "labels.csv",
            "fallback_strategy": "a",
            "min_available_strategies": 2,
            "router": {
                "validation_start": "2024-01-01",
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


def test_promoted_router_never_runs_nested_backtests(monkeypatch) -> None:
    index = pd.date_range("2025-01-01", periods=2, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.0, 101.0],
            "volume": [1.0, 1.0],
        },
        index=index,
    )
    prepared_specs: list[str] = []

    def fake_load(path, _logger):
        strategy_id = str(path).split("/")[-1].removesuffix(".json")
        return SimpleNamespace(name="fake", params={"strategy_id": strategy_id})

    monkeypatch.setattr(cli_runner, "load_strategy_config", fake_load)
    monkeypatch.setattr(
        cli_runner,
        "build_strategy_instance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("nested strategy generate must not run")
        ),
    )
    monkeypatch.setattr(
        cli_runner,
        "build_backtest_args",
        lambda *_args, **_kwargs: _execution(),
    )
    monkeypatch.setattr(
        cli_runner,
        "run_backtest",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("nested backtest must not run")),
    )

    def fake_prepare(*, data, specs):  # noqa: ARG001
        prepared_specs.extend(spec.strategy_id for spec in specs)
        return {
            strategy_id: primary.assign(signal=1, sl_price=99.0) for strategy_id in prepared_specs
        }

    monkeypatch.setattr(
        promoted_router_module,
        "build_archived_signal_frames",
        fake_prepare,
    )
    monkeypatch.setattr(
        PromotedRouterStrategy,
        "_load_labels",
        lambda _self: pd.DataFrame({"asof": [index[0].isoformat()]}),
    )
    monkeypatch.setattr(
        promoted_router_module,
        "evaluate_frozen_router_candidate",
        lambda *_args, **_kwargs: pd.DataFrame(
            {
                "asof": [index[0].isoformat()],
                "selected_strategy": ["selected"],
            }
        ),
    )

    strategy = PromotedRouterStrategy(
        {
            "router_id": "router_test",
            "labels_path": "labels.csv",
            "fallback_strategy": "selected",
            "router": {
                "validation_start": "2024-01-01",
                "scoring_method": "same_state_median_minus_dd",
                "lookback_days": 180,
            },
            "strategy_paths": {
                "selected": "nested/selected.json",
                "unused": "nested/unused.json",
            },
        }
    )

    result = strategy.generate(primary)

    assert prepared_specs == ["selected", "unused"]
    assert result["selected_strategy"].tolist() == ["selected", "selected"]


def test_promoted_router_enables_chronological_replay_progress(monkeypatch) -> None:
    index = pd.date_range("2025-01-01", periods=2, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.0, 101.0],
            "volume": [1.0, 1.0],
        },
        index=index,
    )
    replay_progress: list[bool] = []

    monkeypatch.setattr(
        cli_runner,
        "load_strategy_config",
        lambda *_args: SimpleNamespace(
            name="crypt_ensemble",
            params={"progress": False},
        ),
    )

    monkeypatch.setattr(
        cli_runner,
        "build_backtest_args",
        lambda *_args, **_kwargs: _execution(),
    )
    monkeypatch.setattr(
        PromotedRouterStrategy,
        "_load_labels",
        lambda _self: pd.DataFrame({"asof": [index[0].isoformat()]}),
    )
    monkeypatch.setattr(
        promoted_router_module,
        "evaluate_frozen_router_candidate",
        lambda *_args, **_kwargs: pd.DataFrame(
            {
                "asof": [index[0].isoformat()],
                "selected_strategy": ["selected"],
            }
        ),
    )
    monkeypatch.setattr(
        promoted_router_module,
        "build_archived_signal_frames",
        lambda **_kwargs: {"selected": primary.assign(signal=0, sl_price=0.0)},
    )

    def fake_replay(**kwargs):
        replay_progress.append(bool(kwargs["progress"]))
        return primary.assign(signal=0, sl_price=0.0)

    monkeypatch.setattr(
        promoted_router_module,
        "replay_selected_signals",
        fake_replay,
    )

    strategy = PromotedRouterStrategy(
        {
            "router_id": "router_test",
            "progress": True,
            "labels_path": "labels.csv",
            "fallback_strategy": "selected",
            "router": {
                "validation_start": "2024-01-01",
                "scoring_method": "rolling_median",
                "lookback_days": 180,
            },
            "strategy_paths": {"selected": "nested/selected.json"},
        }
    )

    strategy.generate(primary)

    assert replay_progress == [True]


def test_promoted_router_requires_persisted_labels() -> None:
    strategy = PromotedRouterStrategy(
        {
            "router_id": "router_test",
            "labels_path": "missing/rolling_labels.csv",
            "fallback_strategy": "selected",
            "router": {
                "validation_start": "2024-01-01",
                "scoring_method": "rolling_median",
                "lookback_days": 180,
            },
            "strategy_paths": {"selected": "nested/selected.json"},
        }
    )

    try:
        strategy._load_labels()
    except FileNotFoundError as exc:
        assert "nested backtests are forbidden" in str(exc)
    else:
        raise AssertionError("missing labels must fail")
