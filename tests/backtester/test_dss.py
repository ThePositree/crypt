"""Integration and unit tests for DSS components.

Covers:
- TrialConfig serialisation round-trip
- DSSWindowSpec.parse
- DSSSignalCache hit/miss/eviction
- parameterized_trigger_catalog / parameterized_filter_catalog
- DSSObjective end-to-end with 5 synthetic trials (smoke test)
- dss_report Pareto front extraction
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.data_contracts import StrategyData
from backtester.strategies.dss_strategy import DSSStrategy
from backtester.strategy_discovery.dss_archive import DSSArchive, DSSScore
from backtester.strategy_discovery.dss_cache import DSSSignalCache
from backtester.strategy_discovery.dss_config import (
    DSSBehavior,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    TrialConfig,
)
from backtester.strategy_discovery.dss_objective import (
    DSSObjective,
    compute_mandate_score,
    run_dss_backtest,
)
from backtester.strategy_discovery.dss_report import _extract_pareto_front, _is_dominated
from backtester.strategy_discovery.dss_v2 import (
    _guard_output_dir,
    _write_state,
    evaluate_stage1,
    export_stage4_candidates,
    run_dss_v2_search,
)
from backtester.strategy_discovery.parameterized_filters import parameterized_filter_catalog
from backtester.strategy_discovery.parameterized_triggers import parameterized_trigger_catalog
from backtester.strategy_discovery.signal_composer import SignalComposer

# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def _make_primary(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n))
    open_ = close + rng.normal(0, 0.3, n)
    high = np.maximum(open_, close) + rng.uniform(0.1, 1.0, n)
    low = np.minimum(open_, close) - rng.uniform(0.1, 1.0, n)
    volume = rng.uniform(1_000, 10_000, n)
    index = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )


def _make_strategy_data(primary: pd.DataFrame, symbol: str = "TEST-USDT-SWAP") -> StrategyData:
    return StrategyData(primary=primary, candles={}, extras={}, metadata={"symbol": symbol})


def _make_candidate(
    candidate_id: str = "c1",
    trigger_name: str = "pt_nr4_breakout",
    filters: tuple[str, ...] = (),
) -> DSSCandidate:
    return DSSCandidate(
        candidate_id=candidate_id,
        trigger_name=trigger_name,
        trigger_params={"lookback": 4},
        filter_names=filters,
        filter_params={name: {} for name in filters},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
        generation=0,
    )


def _make_behavior(trigger_name: str = "pt_nr4_breakout") -> DSSBehavior:
    return DSSBehavior(
        trigger_family=trigger_name,
        side_profile="balanced",
        trade_count_bucket="medium",
        hold_time_bucket="medium",
        risk_geometry="medium_sl",
        regime_strength="balanced",
        filter_depth="0",
    )


def _make_signal_df(primary: pd.DataFrame, n: int, side: str = "long") -> pd.DataFrame:
    times = primary.index[20 : 20 + n]
    return pd.DataFrame(
        {
            "bar_time": times,
            "symbol": "TEST-USDT-SWAP",
            "side": [side] * len(times),
            "confidence": [80.0] * len(times),
            "rationale": ["test"] * len(times),
            "entry_price": primary.loc[times, "close"].to_numpy(),
            "stop_price": primary.loc[times, "close"].to_numpy() * 0.99,
            "tp_price": primary.loc[times, "close"].to_numpy() * 1.02,
        }
    )


class _FakeComposer:
    def __init__(self, signals: pd.DataFrame) -> None:
        self._signals = signals

    def build(self, _config: TrialConfig) -> Callable[[StrategyData], pd.DataFrame]:
        return lambda _data: self._signals


# ---------------------------------------------------------------------------
# TrialConfig serialisation
# ---------------------------------------------------------------------------


def test_trial_config_round_trip() -> None:
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 5},
        filter_names=("pf_body_to_range_min", "pf_side_short_only"),
        filter_params={"pf_body_to_range_min": {"ratio": 0.35}},
        rrr=2.5,
        risk_percent=1.5,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
    )
    d = config.to_dict()
    restored = TrialConfig.from_dict(d)
    assert restored.trigger_name == config.trigger_name
    assert restored.filter_names == config.filter_names
    assert abs(restored.rrr - config.rrr) < 1e-9


def test_trial_config_signal_cache_key_is_deterministic() -> None:
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=("pf_body_to_range_min",),
        filter_params={"pf_body_to_range_min": {"ratio": 0.3}},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    assert config.signal_cache_key == config.signal_cache_key


def test_dss_candidate_round_trip() -> None:
    candidate = _make_candidate(filters=("pf_body_to_range_min",))
    restored = DSSCandidate.from_dict(candidate.to_dict())
    assert restored == candidate
    assert restored.signal_cache_key == candidate.signal_cache_key


def test_trial_config_exec_params_do_not_affect_signal_cache_key() -> None:
    """Different rrr/risk_percent/ttl → same cache key (signal shape unchanged)."""
    base = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    different_exec = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=3.0,
        risk_percent=2.0,
        position_ttl_bars=48,
    )
    assert base.signal_cache_key == different_exec.signal_cache_key


def test_archive_keeps_separate_trigger_family_elites() -> None:
    archive = DSSArchive()
    c1 = _make_candidate("c1", "pt_nr4_breakout")
    c2 = _make_candidate("c2", "pt_ema_cross")
    archive.consider(
        c1,
        _make_behavior("pt_nr4_breakout"),
        DSSScore.from_window_scores(
            candidate=c1,
            window_scores={"w1": 10.0, "w2": 8.0},
            trades_by_window={"w1": 5, "w2": 5},
        ),
    )
    archive.consider(
        c2,
        _make_behavior("pt_ema_cross"),
        DSSScore.from_window_scores(
            candidate=c2,
            window_scores={"w1": 9.0, "w2": 7.0},
            trades_by_window={"w1": 5, "w2": 5},
        ),
    )
    assert archive.occupied_cells == 2


def test_archive_replacement_preserves_best_robust_candidate() -> None:
    archive = DSSArchive()
    weak = _make_candidate("weak")
    strong = _make_candidate("strong")
    behavior = _make_behavior()
    archive.consider(
        weak,
        behavior,
        DSSScore.from_window_scores(
            candidate=weak,
            window_scores={"w1": -100.0, "w2": -80.0},
            trades_by_window={"w1": 3, "w2": 3},
        ),
    )
    archive.consider(
        strong,
        behavior,
        DSSScore.from_window_scores(
            candidate=strong,
            window_scores={"w1": 20.0, "w2": 15.0},
            trades_by_window={"w1": 3, "w2": 3},
        ),
    )
    assert archive.best_per_cell()[0].candidate.candidate_id == "strong"


def test_robust_score_penalizes_cross_window_dispersion() -> None:
    stable = _make_candidate("stable")
    volatile = _make_candidate("volatile")
    stable_score = DSSScore.from_window_scores(
        candidate=stable,
        window_scores={"w1": 20.0, "w2": 20.0},
        trades_by_window={"w1": 3, "w2": 3},
    )
    volatile_score = DSSScore.from_window_scores(
        candidate=volatile,
        window_scores={"w1": 0.0, "w2": 40.0},
        trades_by_window={"w1": 3, "w2": 3},
    )
    assert stable_score.robust_score > volatile_score.robust_score


# ---------------------------------------------------------------------------
# DSSWindowSpec parsing
# ---------------------------------------------------------------------------


def test_window_spec_parse_year() -> None:
    spec = DSSWindowSpec.parse("2024", "SOL-USDT-SWAP")
    assert spec.label == "2024"
    assert spec.start == "2024-01-01"
    assert spec.end == "2024-12-31"


def test_window_spec_parse_half_year() -> None:
    spec = DSSWindowSpec.parse("2024H1", "SOL-USDT-SWAP")
    assert spec.start == "2024-01-01"
    assert spec.end == "2024-06-30"


def test_window_spec_parse_explicit() -> None:
    spec = DSSWindowSpec.parse("q1:2024-01-01:2024-03-31", "SOL-USDT-SWAP")
    assert spec.label == "q1"
    assert spec.start == "2024-01-01"
    assert spec.end == "2024-03-31"


def test_window_spec_parse_invalid_raises() -> None:
    with pytest.raises((ValueError, TypeError)):
        DSSWindowSpec.parse("bad:spec:with:too:many:colons", "SOL-USDT-SWAP")


def test_stage1_rejects_empty_signals(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(pd.DataFrame()),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_stage1_rejects_too_few_signals_in_one_window(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=3)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 2)),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_stage1_rejects_overtrading(tmp_path: Path) -> None:
    primary = _make_primary(2000)
    windows = [DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-03-01")]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 500)),
    )
    assert result.passed is False
    assert result.rejection_reason == "overtrading:w1"


def test_stage4_exported_json_replays_through_dss_strategy(tmp_path: Path) -> None:
    candidate = _make_candidate()
    behavior = _make_behavior()
    archive = DSSArchive()
    archive.consider(
        candidate,
        behavior,
        DSSScore.from_window_scores(
            candidate=candidate,
            window_scores={"w1": 10.0},
            trades_by_window={"w1": 5},
        ),
    )
    config = DSSConfig(
        output=tmp_path,
        windows=[DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")],
        top_n_candidates=1,
    )
    paths = export_stage4_candidates(archive, config)
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    strategy = DSSStrategy(payload["params"])
    generated = strategy.generate(_make_strategy_data(_make_primary(300)))
    assert {"signal", "sl_price"}.issubset(generated.columns)


def test_dss_v1_output_dir_fails_resume(tmp_path: Path) -> None:
    (tmp_path / "study.journal").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="DSS v1 artifacts"):
        _guard_output_dir(tmp_path)


def test_dss_v2_state_serializes_slots_window_specs(tmp_path: Path) -> None:
    config = DSSConfig(
        output=tmp_path,
        windows=[
            DSSWindowSpec(
                label="2025H1",
                symbol="SOL-USDT-SWAP",
                start="2025-01-01",
                end="2025-06-30",
            )
        ],
        n_trials=10,
    )
    _write_state(tmp_path, config)
    payload = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert payload["windows"] == [
        {
            "label": "2025H1",
            "symbol": "SOL-USDT-SWAP",
            "start": "2025-01-01",
            "end": "2025-06-30",
        }
    ]


def test_dss_v2_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(
            label="w1",
            symbol="TEST-USDT-SWAP",
            start="2024-01-01",
            end="2024-01-10",
        )
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        n_trials=3,
        min_trades_per_window=10_000,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    run_dss_v2_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    assert ticks == [1, 1, 1]


def test_search_signals_help_no_longer_exposes_sampler() -> None:
    result = CliRunner().invoke(cli, ["search-signals", "--help"])
    assert result.exit_code == 0
    assert "--sampler" not in result.output


def test_search_signals_rejects_removed_sampler_option() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "search-signals",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--sampler",
            "random",
        ],
    )
    assert result.exit_code != 0
    assert "DSS v2 replaced the old Optuna sampler path" in result.output


# ---------------------------------------------------------------------------
# DSSSignalCache
# ---------------------------------------------------------------------------


def test_cache_basic_hit_miss() -> None:
    cache = DSSSignalCache(max_entries=10)
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    calls = [0]

    def compute() -> pd.DataFrame:
        calls[0] += 1
        return pd.DataFrame({"x": [1, 2, 3]})

    r1 = cache.get_or_compute(config, "2024", compute)
    r2 = cache.get_or_compute(config, "2024", compute)
    assert calls[0] == 1
    assert len(r1) == len(r2)
    assert cache.hits == 1
    assert cache.misses == 1


def test_cache_evicts_oldest_when_full() -> None:
    max_entries = 3
    cache = DSSSignalCache(max_entries=max_entries)

    def make_config(n: int) -> TrialConfig:
        return TrialConfig(
            trigger_name="pt_candle_confirm",
            trigger_params={"body_ratio": float(n) / 10},
            filter_names=(),
            filter_params={},
            rrr=2.0,
            risk_percent=1.0,
            position_ttl_bars=36,
        )

    empty_df = pd.DataFrame()
    for i in range(max_entries + 2):
        cache.get_or_compute(make_config(i), "2024", lambda: empty_df)

    assert cache.size == max_entries


def test_cache_different_windows_cached_separately() -> None:
    cache = DSSSignalCache(max_entries=10)
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    calls: dict[str, int] = {"2022": 0, "2023": 0}

    def make_compute(label: str) -> Callable[[], pd.DataFrame]:
        def _compute() -> pd.DataFrame:
            calls[label] += 1
            return pd.DataFrame({"label": [label]})
        return _compute

    cache.get_or_compute(config, "2022", make_compute("2022"))
    cache.get_or_compute(config, "2023", make_compute("2023"))
    cache.get_or_compute(config, "2022", make_compute("2022"))  # should hit
    assert calls["2022"] == 1
    assert calls["2023"] == 1


# ---------------------------------------------------------------------------
# Parameterized catalogs
# ---------------------------------------------------------------------------


def test_parameterized_trigger_catalog_nonempty() -> None:
    cat = parameterized_trigger_catalog()
    assert len(cat) >= 10


def test_parameterized_filter_catalog_nonempty() -> None:
    cat = parameterized_filter_catalog()
    assert len(cat) >= 8


def test_all_triggers_callable() -> None:
    cat = parameterized_trigger_catalog()
    for name, factory in cat.items():
        fn = factory({})
        assert callable(fn), f"Factory {name!r} did not return a callable"


def test_all_filters_callable() -> None:
    cat = parameterized_filter_catalog()
    for name, factory in cat.items():
        fn = factory({})
        assert callable(fn), f"Factory {name!r} did not return a callable"


def test_trigger_produces_events_on_synthetic_data() -> None:
    """At least one trigger fires on synthetic noisy data."""
    from backtester.strategy_discovery.features import build_discovery_dataset

    primary = _make_primary(400)
    data = _make_strategy_data(primary)
    dataset = build_discovery_dataset(data=data, window_label="test", symbol="TEST")
    cat = parameterized_trigger_catalog()
    any_fired = False
    for _name, factory in cat.items():
        try:
            fn = factory({})
            events = fn(dataset)
            if events:
                any_fired = True
                break
        except Exception:
            continue
    assert any_fired, "No trigger fired on 400-bar synthetic data"


# ---------------------------------------------------------------------------
# compute_mandate_score
# ---------------------------------------------------------------------------


def test_compute_mandate_score_empty_trades() -> None:
    score = compute_mandate_score(
        pd.DataFrame(),
        initial_capital=10_000.0,
        start="2024-01-01",
        end="2024-12-31",
    )
    assert score < 0


def test_compute_mandate_score_profitable_trades() -> None:
    """Trades with consistent >15%/month profit should yield a positive mandate_score."""
    n = 12
    # Use same-day entry/exit so mandate_month aligns with each calendar month.
    months = pd.date_range("2024-01-15", periods=n, freq="MS")
    trades = pd.DataFrame(
        {
            "entry_time": months,
            "exit_time": months + pd.Timedelta(hours=4),
            # 1600/10000 = 16% > RETURN_FLOOR_PCT (15%) — clears the floor every month.
            "pnl_abs": [1600.0] * n,
            "is_long": [True] * n,
            "exit_reason": ["take_profit"] * n,
        }
    )
    score = compute_mandate_score(
        trades,
        initial_capital=10_000.0,
        start="2024-01-01",
        end="2024-12-31",
    )
    assert score > 0


# ---------------------------------------------------------------------------
# Pareto front helpers (dss_report)
# ---------------------------------------------------------------------------


def test_is_dominated_basic() -> None:
    # [1,2] is fully dominated by [2,3]
    assert _is_dominated([1.0, 2.0], [2.0, 3.0]) is True
    # [2,3] is NOT dominated by [1,2]
    assert _is_dominated([2.0, 3.0], [1.0, 2.0]) is False
    # [2,2] is dominated by [2,3] (second objective is strictly better)
    assert _is_dominated([2.0, 2.0], [2.0, 3.0]) is True
    # Neither dominates the other when each is better in a different objective
    assert _is_dominated([3.0, 1.0], [1.0, 3.0]) is False
    assert _is_dominated([1.0, 3.0], [3.0, 1.0]) is False


def test_extract_pareto_front_empty() -> None:
    front = _extract_pareto_front([], n_objectives=2)
    assert front == []


# ---------------------------------------------------------------------------
# run_dss_backtest
# ---------------------------------------------------------------------------


def test_run_dss_backtest_completes_with_ignore_structural_sl_mode() -> None:
    """DSS signals embed sl_price; backtest must not use invalid structural_sl_mode."""
    primary = _make_primary(500, seed=42)
    data = _make_strategy_data(primary)
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
    )
    signal_df = SignalComposer().build(config)(data)
    assert not signal_df.empty

    trades = run_dss_backtest(signal_df, config, data)
    assert not trades.empty
    score = compute_mandate_score(
        trades,
        initial_capital=10_000.0,
        start="2024-01-01",
        end="2024-12-31",
    )
    assert score not in (-5_000.0, -10_000.0)


# ---------------------------------------------------------------------------
# DSSObjective smoke test (5 trials on synthetic data)
# ---------------------------------------------------------------------------


def test_dss_objective_smoke(tmp_path: Path) -> None:
    """DSSObjective must complete 5 trials without crashing."""
    import optuna

    primary = _make_primary(500, seed=7)

    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-06-30"),
        DSSWindowSpec(label="w2", symbol="TEST-USDT-SWAP", start="2024-07-01", end="2024-12-31"),
    ]
    primary_w1 = primary.loc["2024-01-01":"2024-06-30"]
    primary_w2 = primary.loc["2024-07-01":"2024-12-31"]

    window_data = {
        "w1": StrategyData(primary=primary_w1, candles={}, extras={}, metadata={"symbol": "TEST-USDT-SWAP"}),
        "w2": StrategyData(primary=primary_w2, candles={}, extras={}, metadata={"symbol": "TEST-USDT-SWAP"}),
    }

    t_catalog = parameterized_trigger_catalog()
    f_catalog = parameterized_filter_catalog()

    search_space = DSSSearchSpace(
        trigger_names=tuple(sorted(t_catalog.keys())),
        filter_names=tuple(sorted(f_catalog.keys())),
        trigger_param_bounds={},
        filter_param_bounds={},
        max_filters=1,
        rrr_range=(2.0, 2.0, 0.5),
        risk_percent_range=(1.0, 1.0, 0.5),
        position_ttl_bars_range=(36, 36, 4),
        atr_sl_mult_range=(1.0, 1.0, 0.5),
    )

    dss_config = DSSConfig(
        output=tmp_path,
        windows=windows,
        n_trials=5,
        n_jobs=1,
        max_filters=1,
        min_trades_per_window=1,
    )

    signal_cache = DSSSignalCache(max_entries=100)
    objective = DSSObjective(
        windows=windows,
        window_data=window_data,
        search_space=search_space,
        signal_cache=signal_cache,
        config=dss_config,
    )

    optuna.logging.set_verbosity(optuna.logging.ERROR)
    study = optuna.create_study(
        directions=["maximize", "maximize"],
        sampler=optuna.samplers.RandomSampler(seed=42),
    )
    study.optimize(objective, n_trials=5)
    complete = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    assert len(complete) == 5
    for trial in complete:
        assert trial.values is not None
        assert len(trial.values) == 2
