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
import sys
import types
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

import backtester.strategy_discovery.catcma_qd as catcma_qd_module
import backtester.strategy_discovery.dss_directional as dss_directional_module
import backtester.strategy_discovery.dss_directional_search as dss_directional_search_module
import backtester.strategy_discovery.hyperband_qd as hyperband_qd_module
import backtester.strategy_discovery.island_qd as island_qd_module
import backtester.strategy_discovery.smac_qd as smac_qd_module
from backtester.__main__ import cli
from backtester.data_contracts import StrategyData
from backtester.data_loader import CryptParquetDataLoader
from backtester.strategies.dss_strategy import DSSStrategy
from backtester.strategy_discovery.catalog_timeframes import dss_instance_labels
from backtester.strategy_discovery.catcma_qd import (
    _DirectionalCandidate,
    _EvaluatedCandidate,
    _select_directional_feedback_candidates,
    _WeightedModel,
    run_catcma_qd_search,
)
from backtester.strategy_discovery.dss_archive import DSSArchive, DSSScore
from backtester.strategy_discovery.dss_cache import DSSSignalCache
from backtester.strategy_discovery.dss_config import (
    CategoricalParam,
    DSSBehavior,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    FloatParam,
    IntParam,
    TrialConfig,
)
from backtester.strategy_discovery.dss_directional_search import (
    BarrierMetrics,
    DirectionalResult,
    DSSDirectionalResult,
    DSSSignalNoveltyTracker,
    _append_directional_result,
    _directional_with_novelty,
    _guard_output_dir,
    _select_directional_export_rows,
    _write_state,
    directional_rank_score,
    evaluate_directional_viability,
    export_directional_candidates,
    run_dss_directional_search,
    sample_random_directional_candidate,
    write_directional_ranked,
)
from backtester.strategy_discovery.dss_objective import compute_mandate_score
from backtester.strategy_discovery.dss_report import _extract_pareto_front, _is_dominated
from backtester.strategy_discovery.dss_runtime import DSSSearchRuntime
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import (
    align_discovery_dataset_asof,
    build_discovery_dataset,
    build_timeframe_discovery_dataset,
)
from backtester.strategy_discovery.hyperband_qd import (
    _RungCandidate,
    _select_rung_promotions,
    run_hyperband_qd_search,
)
from backtester.strategy_discovery.island_qd import run_island_qd_search
from backtester.strategy_discovery.parameterized_filters import parameterized_filter_catalog
from backtester.strategy_discovery.parameterized_triggers import parameterized_trigger_catalog
from backtester.strategy_discovery.pinescript_catalog import (
    pinescript_filter_catalog,
    pinescript_trigger_catalog,
)
from backtester.strategy_discovery.signal_composer import SignalComposer
from backtester.strategy_discovery.smac_qd import (
    _CandidateEncoder,
    _RandomForestSurrogate,
    run_smac_qd_search,
)

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
    return StrategyData(
        candles_by_timeframe={"H1": primary},
        extras={},
        metadata={"symbol": symbol},
    )


def _make_multiframe_strategy_data(
    primary: pd.DataFrame,
    symbol: str = "TEST-USDT-SWAP",
) -> StrategyData:
    return StrategyData(
        candles_by_timeframe={
            "M15": primary.copy(),
            "H1": primary.copy(),
            "H4": primary.copy(),
            "D1": primary.copy(),
        },
        extras={},
        metadata={"symbol": symbol},
    )


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
        generation=0,
    )


def _make_behavior(trigger_name: str = "pt_nr4_breakout") -> DSSBehavior:
    return DSSBehavior(
        trigger_family=trigger_name,
        side_profile="balanced",
        frequency_class="medium",
        regime_strength="balanced",
        filter_depth="0",
    )


def _make_directional_pass(candidate: DSSCandidate) -> DirectionalResult:
    return DirectionalResult(
        candidate_id=candidate.candidate_id,
        passed=True,
        rejection_reason="",
        signal_counts={"w1": 12},
        long_ratios={"w1": 0.5},
        median_stop_atr={"w1": 1.0},
        barrier_metrics={
            "w1": BarrierMetrics(
                total=12,
                tp_first=8,
                sl_first=4,
                unresolved_tail=0,
                tp_first_rate=8 / 12,
                sl_first_rate=4 / 12,
                unresolved_tail_rate=0.0,
                win_rate=8 / 12,
                median_mae_pct=0.8,
                median_mfe_pct=1.4,
                median_bars_to_tp=3.0,
            )
        },
        behavior=_make_behavior(candidate.trigger_name),
        candidate_class="balanced",
        advisory_score=150.0,
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


def _make_barrier_primary(*, same_bar_stop: bool = False) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=40, freq="1h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [100.35] * len(index),
            "low": [99.65] * len(index),
            "close": [100.0] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    if same_bar_stop:
        frame.iloc[11, frame.columns.get_loc("high")] = 100.8
        frame.iloc[11, frame.columns.get_loc("low")] = 99.5
    else:
        frame.iloc[11, frame.columns.get_loc("high")] = 100.5
        frame.iloc[11, frame.columns.get_loc("low")] = 99.7
        frame.iloc[12, frame.columns.get_loc("high")] = 100.8
        frame.iloc[12, frame.columns.get_loc("low")] = 100.0
    return frame


def _make_one_signal(primary: pd.DataFrame, side: str = "long") -> pd.DataFrame:
    time = primary.index[10]
    return pd.DataFrame(
        {
            "bar_time": [time],
            "symbol": ["TEST-USDT-SWAP"],
            "side": [side],
            "confidence": [80.0],
            "rationale": ["test"],
            "entry_price": [100.0],
            "stop_price": [98.0 if side == "long" else 102.0],
            "tp_price": [102.0 if side == "long" else 98.0],
        }
    )


def _make_multi_signal(
    primary: pd.DataFrame, offsets: list[int], side: str = "long"
) -> pd.DataFrame:
    rows = []
    for offset in offsets:
        time = primary.index[offset]
        rows.append(
            {
                "bar_time": time,
                "symbol": "TEST-USDT-SWAP",
                "side": side,
                "confidence": 80.0,
                "rationale": "test",
                "entry_price": 100.0,
                "stop_price": 98.0 if side == "long" else 102.0,
                "tp_price": 102.0 if side == "long" else 98.0,
            }
        )
    return pd.DataFrame(rows)


class _FakeComposer:
    def __init__(self, signals: pd.DataFrame) -> None:
        self._signals = signals

    def build(self, _config: TrialConfig) -> Callable[[StrategyData], pd.DataFrame]:
        return lambda _data: self._signals


class _WindowAwareFakeComposer:
    def __init__(self, signals_by_primary_id: dict[int, pd.DataFrame]) -> None:
        self._signals_by_primary_id = signals_by_primary_id

    def build(self, _config: TrialConfig) -> Callable[[StrategyData], pd.DataFrame]:
        return lambda data: self._signals_by_primary_id[id(data.require_timeframe("H1"))]


class _CountingWindowAwareFakeComposer:
    def __init__(self, signals_by_primary_id: dict[int, pd.DataFrame]) -> None:
        self._signals_by_primary_id = signals_by_primary_id
        self.calls = 0

    def build(self, _config: TrialConfig) -> Callable[[StrategyData], pd.DataFrame]:
        def _generate(data: StrategyData) -> pd.DataFrame:
            self.calls += 1
            return self._signals_by_primary_id[id(data.require_timeframe("H1"))]

        return _generate


# ---------------------------------------------------------------------------
# TrialConfig serialisation
# ---------------------------------------------------------------------------


def test_trial_config_round_trip() -> None:
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 5},
        filter_names=("pf_body_to_range_min", "pf_side_short_only"),
        filter_params={"pf_body_to_range_min": {"ratio": 0.35}},
    )
    d = config.to_dict()
    restored = TrialConfig.from_dict(d)
    assert restored.trigger_name == config.trigger_name
    assert restored.filter_names == config.filter_names
    assert "rrr" not in d


def test_trial_config_signal_cache_key_is_deterministic() -> None:
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=("pf_body_to_range_min",),
        filter_params={"pf_body_to_range_min": {"ratio": 0.3}},
    )
    assert config.signal_cache_key == config.signal_cache_key


def test_trial_config_hash_includes_timeframe_instances() -> None:
    h1 = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_timeframe="H1",
        trigger_params={"lookback": 4},
        filter_names=("pf_body_to_range_min@H1", "pf_body_to_range_min@H4"),
        filter_params={
            "pf_body_to_range_min@H1": {"ratio": 0.3},
            "pf_body_to_range_min@H4": {"ratio": 0.3},
        },
    )
    h4 = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_timeframe="H4",
        trigger_params={"lookback": 4},
        filter_names=("pf_body_to_range_min@H1", "pf_body_to_range_min@H4"),
        filter_params={
            "pf_body_to_range_min@H1": {"ratio": 0.3},
            "pf_body_to_range_min@H4": {"ratio": 0.3},
        },
    )

    assert h1.signal_cache_key != h4.signal_cache_key
    assert [instance.label for instance in h1.filter_instances] == [
        "pf_body_to_range_min@H1",
        "pf_body_to_range_min@H4",
    ]


def test_directional_generation_samples_timeframe_instances() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout@15m", "pt_nr4_breakout@H4"),
        filter_names=("pf_body_to_range_min@H1", "pf_body_to_range_min@H4"),
        trigger_param_bounds={"pt_nr4_breakout": {"lookback": IntParam(3, 4)}},
        filter_param_bounds={"pf_body_to_range_min": {"ratio": FloatParam(0.2, 0.4)}},
        max_filters=1,
        trigger_timeframes=("15m", "H4"),
        filter_timeframes=("H1", "H4"),
    )

    candidates = dss_directional_search_module._generate_directional_candidates(
        search_space=search_space,
        start=0,
        limit=8,
        max_filters=1,
    )

    assert {candidate.trigger_timeframe for candidate in candidates} == {"15m", "H4"}
    assert any(
        "pf_body_to_range_min@H4" in candidate.filter_names
        and candidate.filter_timeframes["pf_body_to_range_min@H4"] == "H4"
        for candidate in candidates
    )


def test_directional_generation_does_not_repeat_adjacent_batches() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout@15m", "pt_nr4_breakout@H4"),
        filter_names=("pf_body_to_range_min@H1", "pf_body_to_range_min@H4"),
        trigger_param_bounds={"pt_nr4_breakout": {"lookback": IntParam(3, 8)}},
        filter_param_bounds={"pf_body_to_range_min": {"ratio": FloatParam(0.2, 0.7)}},
        max_filters=2,
        trigger_timeframes=("15m", "H4"),
        filter_timeframes=("H1", "H4"),
    )

    first = dss_directional_search_module._generate_directional_candidates(
        search_space=search_space,
        start=0,
        limit=64,
        max_filters=2,
    )
    second = dss_directional_search_module._generate_directional_candidates(
        search_space=search_space,
        start=64,
        limit=128,
        max_filters=2,
    )

    first_keys = {candidate.candidate_key for candidate in first}
    second_keys = {candidate.candidate_key for candidate in second}
    assert len(second_keys - first_keys) >= 20


def test_trial_config_rejects_exact_duplicate_filter_instances() -> None:
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=("pf_body_to_range_min@H1", "pf_body_to_range_min@H1"),
        filter_params={"pf_body_to_range_min@H1": {"ratio": 0.3}},
    )

    with pytest.raises(ValueError, match="Duplicate DSS filter instance"):
        _ = config.filter_instances


def test_timeframe_dataset_selects_requested_candles_and_asof_aligns() -> None:
    primary = _make_primary(48)
    h4 = primary.resample("4h").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    data = StrategyData(
        candles_by_timeframe={"H4": h4},
        extras={},
        metadata={"symbol": "TEST-USDT-SWAP"},
    )

    h4_dataset = build_timeframe_discovery_dataset(
        data=data,
        timeframe="H4",
        window_label="w1",
        symbol="TEST-USDT-SWAP",
    )
    aligned = align_discovery_dataset_asof(h4_dataset, pd.DatetimeIndex(primary.index))

    assert h4_dataset.ohlcv.index.equals(h4.index)
    assert aligned.ohlcv.index.equals(primary.index)
    assert aligned.ohlcv.loc[primary.index[5], "open"] == h4.iloc[0]["open"]
    assert aligned.ohlcv.loc[primary.index[8], "open"] == h4.iloc[1]["open"]


def test_dss_candidate_round_trip() -> None:
    candidate = _make_candidate(filters=("pf_body_to_range_min",))
    restored = DSSCandidate.from_dict(candidate.to_dict())
    assert restored == candidate
    assert restored.signal_cache_key == candidate.signal_cache_key


def test_trial_config_rejects_geometry_fields_from_signal_cache_key() -> None:
    """DSS v3 ignores legacy geometry fields during deserialization."""
    base = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
    )
    legacy = TrialConfig.from_dict({**base.to_dict(), "rrr": 3.0, "risk_percent": 2.0})
    assert base.signal_cache_key == legacy.signal_cache_key


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


def test_runtime_progress_preserves_last_exported_count(tmp_path: Path) -> None:
    config = DSSConfig(output=tmp_path, windows=[])

    runtime = DSSSearchRuntime(config=config)
    runtime.write_progress(generated=10, evaluated=10, exported=3)
    runtime.write_progress(generated=11, evaluated=11)

    payload = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert payload["exported"] == 3


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


def test_crypt_parquet_loader_filters_every_timeframe_to_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Timeframe:
        M15 = "M15"
        H1 = "H1"
        H4 = "H4"
        D1 = "D1"

    def _frame(freq: str, periods: int) -> pd.DataFrame:
        index = pd.date_range("2023-12-31", periods=periods, freq=freq, tz="UTC")
        values = np.arange(periods, dtype=float) + 100.0
        return pd.DataFrame(
            {
                "open": values,
                "high": values + 1.0,
                "low": values - 1.0,
                "close": values,
                "volume": values * 10.0,
            },
            index=index,
        )

    class _ParquetStore:
        def __init__(self, _path: Path) -> None:
            self.frames = {
                _Timeframe.M15: _frame("15min", 400),
                _Timeframe.H1: _frame("1h", 140),
                _Timeframe.H4: _frame("4h", 60),
                _Timeframe.D1: _frame("1d", 12),
            }

        def load_candles(self, _symbol: str, timeframe: str, **_kwargs: object) -> pd.DataFrame:
            return self.frames[timeframe]

        def load_oi(self, _symbol: str) -> pd.DataFrame:
            return pd.DataFrame()

        def load_ls_ratio(self, _symbol: str) -> pd.DataFrame:
            return pd.DataFrame()

        def load_taker_volume(self, _symbol: str) -> pd.DataFrame:
            return pd.DataFrame()

    crypt_module = types.ModuleType("crypt")
    crypt_data_module = types.ModuleType("crypt.data")
    crypt_store_module = types.ModuleType("crypt.data.store")
    crypt_models_module = types.ModuleType("crypt.models")
    crypt_store_module.ParquetStore = _ParquetStore
    crypt_models_module.Timeframe = _Timeframe
    monkeypatch.setitem(sys.modules, "crypt", crypt_module)
    monkeypatch.setitem(sys.modules, "crypt.data", crypt_data_module)
    monkeypatch.setitem(sys.modules, "crypt.data.store", crypt_store_module)
    monkeypatch.setitem(sys.modules, "crypt.models", crypt_models_module)

    data = CryptParquetDataLoader(
        str(tmp_path),
        "TEST-USDT-SWAP",
        candle_timeframe="4h",
        start="2024-01-02",
        end="2024-01-03",
    ).load()

    lower = pd.Timestamp("2024-01-02", tz="UTC")
    upper = pd.Timestamp("2024-01-03", tz="UTC")
    for frame in (data.require_timeframe("H1"), *data.candles_by_timeframe.values()):
        assert frame.index.min() >= lower
        assert frame.index.max() <= upper


def test_cli_dss_catalog_timeframe_labels_are_role_eligible() -> None:
    trigger_labels = dss_instance_labels(
        ("pt_vwap_reclaim", "pt_structure_break"),
        ("15m", "H1", "H4", "D1"),
        role="trigger",
    )
    filter_labels = dss_instance_labels(
        ("pf_session", "pf_context_aligned"),
        ("15m", "H1", "H4", "D1"),
        role="filter",
    )

    assert "pt_vwap_reclaim@D1" not in trigger_labels
    assert "pt_structure_break@H4" in trigger_labels
    assert "pf_session@D1" not in filter_labels
    assert "pf_context_aligned@D1" in filter_labels


def test_directional_rejects_empty_signals(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(pd.DataFrame()),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_directional_rejects_too_few_signals_in_one_window(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=3)
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 2)),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_directional_uses_weekly_signal_frequency_gate(tmp_path: Path) -> None:
    primary = _make_primary(24 * 14)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-14")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_signals_per_week=4.0,
    )
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 4)),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_directional_accepts_tp_first_barrier_signal(tmp_path: Path) -> None:
    primary = _make_barrier_primary()
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.5,
    )
    candidate = DSSCandidate(
        candidate_id="barrier_pass",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    result = evaluate_directional_viability(
        candidate,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_one_signal(primary)),
    )
    metrics = result.barrier_metrics["w1"]
    assert result.passed is True
    assert metrics.tp_first_rate == 1.0
    assert metrics.sl_first_rate == 0.0
    assert metrics.median_bars_to_tp == 2.0
    assert result.should_promote is True
    assert result.advisory_score is not None


def test_directional_labels_barriers_on_trigger_timeframe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h1_primary = _make_primary(120)
    m15_primary = _make_primary(480)
    m15_primary.index = pd.date_range("2024-01-01", periods=480, freq="15min", tz="UTC")
    data = StrategyData(
        candles_by_timeframe={"H1": h1_primary, "M15": m15_primary},
        extras={},
        metadata={"symbol": "TEST-USDT-SWAP"},
    )
    candidate = DSSCandidate(
        candidate_id="m15_trigger",
        trigger_name="pt_nr4_breakout@15m",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    signals = _make_signal_df(m15_primary, 3)
    config = DSSConfig(
        output=tmp_path,
        windows=[
            DSSWindowSpec(
                label="w1",
                symbol="TEST-USDT-SWAP",
                start="2024-01-01",
                end="2024-01-05",
            )
        ],
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.5,
    )

    def _fake_barrier_metrics(
        primary: pd.DataFrame,
        signals: pd.DataFrame,
        *,
        tp_move_pct: float,
        sl_move_pct: float,
        reference_atr_pct: float,
    ) -> BarrierMetrics:
        _ = (signals, tp_move_pct, sl_move_pct, reference_atr_pct)
        assert primary.index.equals(m15_primary.index)
        return BarrierMetrics(
            total=3,
            tp_first=2,
            sl_first=1,
            unresolved_tail=0,
            tp_first_rate=2 / 3,
            sl_first_rate=1 / 3,
            unresolved_tail_rate=0.0,
            win_rate=2 / 3,
            median_mae_pct=0.2,
            median_mfe_pct=0.8,
            median_bars_to_tp=2.0,
        )

    monkeypatch.setattr(dss_directional_module, "_barrier_metrics", _fake_barrier_metrics)

    result = evaluate_directional_viability(candidate, {"w1": data}, config, _FakeComposer(signals))

    assert result.passed is True
    assert result.barrier_metrics["w1"].total == 3


def test_directional_reject_does_not_promote(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=3)
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 2)),
    )
    assert result.passed is False
    assert result.should_promote is False


def test_directional_result_records_signal_fingerprint(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.0,
        min_barrier_win_rate=0.0,
    )

    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_one_signal(primary)),
    )

    assert result.metadata["signal_set_size"] == 1
    assert result.metadata["signal_fingerprint"]


def test_directional_records_window_specialist_without_survivor_export(tmp_path: Path) -> None:
    w1_primary = _make_barrier_primary()
    w2_primary = _make_barrier_primary()
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10"),
        DSSWindowSpec(label="w2", symbol="TEST-USDT-SWAP", start="2024-02-01", end="2024-02-10"),
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.5,
        specialist_windows=("w1",),
    )
    candidate = DSSCandidate(
        candidate_id="specialist",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    result = evaluate_directional_viability(
        candidate,
        {
            "w1": _make_strategy_data(w1_primary),
            "w2": _make_strategy_data(w2_primary),
        },
        config,
        _WindowAwareFakeComposer(
            {
                id(w1_primary): _make_one_signal(w1_primary),
                id(w2_primary): pd.DataFrame(),
            }
        ),
    )

    assert result.passed is False
    assert result.candidate_class == "specialist:w1"
    assert result.target_window == "w1"
    assert result.rejection_reason == "specialist:w1"
    assert result.behavior is not None
    assert result.behavior.regime_strength == "w1"

    _append_directional_result(tmp_path, candidate, result, windows)

    assert not (tmp_path / "directional_survivors.jsonl").exists()
    assert not (tmp_path / "directional_rejections.csv").exists()
    specialist_csv = (tmp_path / "directional_specialists.csv").read_text(encoding="utf-8")
    assert "candidate_class" in specialist_csv.splitlines()[0]
    assert "specialist:w1" in specialist_csv


def test_directional_default_path_still_rejects_early(tmp_path: Path) -> None:
    w1_primary = _make_barrier_primary()
    w2_primary = _make_barrier_primary()
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10"),
        DSSWindowSpec(label="w2", symbol="TEST-USDT-SWAP", start="2024-02-01", end="2024-02-10"),
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    composer = _CountingWindowAwareFakeComposer(
        {
            id(w1_primary): pd.DataFrame(),
            id(w2_primary): _make_one_signal(w2_primary),
        }
    )

    result = evaluate_directional_viability(
        _make_candidate(),
        {
            "w1": _make_strategy_data(w1_primary),
            "w2": _make_strategy_data(w2_primary),
        },
        config,
        composer,
    )

    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"
    assert result.candidate_class == "rejected"
    assert composer.calls == 1


def test_directional_counts_same_bar_tp_and_sl_as_sl_first(tmp_path: Path) -> None:
    primary = _make_barrier_primary(same_bar_stop=True)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.1,
    )
    candidate = DSSCandidate(
        candidate_id="barrier_reject",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    result = evaluate_directional_viability(
        candidate,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_one_signal(primary)),
    )
    metrics = result.barrier_metrics["w1"]
    assert result.passed is False
    assert result.rejection_reason == "weak_barrier_edge:w1"
    assert metrics.tp_first_rate == 0.0
    assert metrics.sl_first_rate == 1.0


def test_directional_barrier_uses_next_open_entry(tmp_path: Path) -> None:
    primary = _make_barrier_primary()
    primary.iloc[11, primary.columns.get_loc("open")] = 110.0
    primary.iloc[12, primary.columns.get_loc("high")] = 100.8
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.1,
    )
    candidate = DSSCandidate(
        candidate_id="gap_reject",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    result = evaluate_directional_viability(
        candidate,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_one_signal(primary)),
    )
    metrics = result.barrier_metrics["w1"]
    assert result.passed is False
    assert result.rejection_reason == "weak_barrier_edge:w1"
    assert metrics.tp_first == 0
    assert metrics.sl_first == 1


def test_directional_atr_scaled_label_ignores_rrr_ttl_and_signal_stop(tmp_path: Path) -> None:
    primary = _make_barrier_primary()
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.5,
    )
    base = DSSCandidate(
        candidate_id="base",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    variant = DSSCandidate(
        candidate_id="variant",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    signals = _make_one_signal(primary)
    signals["stop_price"] = 1.0

    base_metrics = evaluate_directional_viability(
        base,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(signals),
    ).barrier_metrics["w1"]
    variant_metrics = evaluate_directional_viability(
        variant,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(signals),
    ).barrier_metrics["w1"]

    assert base_metrics == variant_metrics
    assert base_metrics.tp_first == 1
    assert base_metrics.median_bars_to_tp == 2.0


def test_directional_atr_scaled_label_expands_for_more_volatile_symbol(tmp_path: Path) -> None:
    index = pd.date_range("2024-01-01", periods=40, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [100.6] * len(index),
            "low": [99.4] * len(index),
            "close": [100.0] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    primary.iloc[12, primary.columns.get_loc("high")] = 100.8
    primary.iloc[12, primary.columns.get_loc("low")] = 99.6
    primary.iloc[13, primary.columns.get_loc("high")] = 101.25
    primary.iloc[13, primary.columns.get_loc("low")] = 100.0
    windows = [
        DSSWindowSpec(label="w1", symbol="TON-USDT-SWAP", start="2024-01-01", end="2024-01-03")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.5,
    )
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_one_signal(primary)),
    )

    metrics = result.barrier_metrics["w1"]
    assert result.passed is True
    assert metrics.tp_first == 1
    assert metrics.sl_first == 0
    assert metrics.median_bars_to_tp == 3.0


def test_directional_unresolved_tail_excluded_from_win_rate(tmp_path: Path) -> None:
    index = pd.date_range("2024-01-01", periods=30, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [100.2] * len(index),
            "low": [99.8] * len(index),
            "close": [100.0] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    primary.iloc[12, primary.columns.get_loc("high")] = 100.8
    primary.iloc[22, primary.columns.get_loc("low")] = 99.5
    signal_offsets = [10, 20, 28]
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-02")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.0,
        min_barrier_win_rate=0.4,
    )
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_multi_signal(primary, signal_offsets)),
    )

    metrics = result.barrier_metrics["w1"]
    assert metrics.tp_first == 1
    assert metrics.sl_first == 1
    assert metrics.unresolved_tail == 1
    assert metrics.win_rate == 0.5
    assert metrics.unresolved_tail_rate == pytest.approx(1 / 3)


def test_directional_rejects_barrier_win_rate_below_floor(tmp_path: Path) -> None:
    index = pd.date_range("2024-01-01", periods=80, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [100.2] * len(index),
            "low": [99.8] * len(index),
            "close": [100.0] * len(index),
            "volume": [1_000.0] * len(index),
        },
        index=index,
    )
    signal_offsets = [10, 20, 30, 40, 50, 60]
    for offset in signal_offsets[:3]:
        primary.iloc[offset + 2, primary.columns.get_loc("high")] = 103.0
        primary.iloc[offset + 2, primary.columns.get_loc("low")] = 100.0
    for offset in signal_offsets[3:]:
        primary.iloc[offset + 2, primary.columns.get_loc("high")] = 101.0
        primary.iloc[offset + 2, primary.columns.get_loc("low")] = 97.0

    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.0,
        min_barrier_win_rate=0.55,
    )
    candidate = DSSCandidate(
        candidate_id="low_win_rate",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        generation=0,
    )
    result = evaluate_directional_viability(
        candidate,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_multi_signal(primary, signal_offsets)),
    )
    metrics = result.barrier_metrics["w1"]
    assert result.passed is False
    assert result.rejection_reason == "weak_barrier_win_rate:w1"
    assert metrics.tp_first == 3
    assert metrics.sl_first == 3
    assert metrics.win_rate == 0.5


def test_directional_min_wr_is_only_win_rate_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = _make_primary(80)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.0,
        min_barrier_win_rate=0.45,
    )

    def fake_barrier_metrics(**_kwargs: object) -> BarrierMetrics:
        return BarrierMetrics(
            total=19,
            tp_first=9,
            sl_first=10,
            unresolved_tail=0,
            tp_first_rate=9 / 19,
            sl_first_rate=10 / 19,
            unresolved_tail_rate=0.0,
            win_rate=9 / 19,
            median_mae_pct=0.4,
            median_mfe_pct=0.7,
            median_bars_to_tp=3.0,
        )

    monkeypatch.setattr(dss_directional_module, "_barrier_metrics", fake_barrier_metrics)
    result = evaluate_directional_viability(
        _make_candidate("wr45_only"),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 19)),
    )

    metrics = result.barrier_metrics["w1"]
    assert metrics.tp_first < metrics.sl_first
    assert metrics.win_rate == pytest.approx(9 / 19)
    assert result.passed is True
    assert result.rejection_reason == ""


def test_directional_csv_header_includes_barrier_columns_after_early_reject(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10"),
        DSSWindowSpec(label="w2", symbol="TEST-USDT-SWAP", start="2024-02-01", end="2024-02-10"),
    ]
    candidate = _make_candidate("early_reject")
    result = DirectionalResult(
        candidate_id=candidate.candidate_id,
        passed=False,
        rejection_reason="too_few_signals:w1",
        signal_counts={"w1": 0},
        long_ratios={},
        median_stop_atr={},
        barrier_metrics={},
        behavior=None,
    )
    _append_directional_result(tmp_path, candidate, result, windows)
    header = (tmp_path / "directional_viability.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "trigger_timeframe" in header
    assert "filter_timeframes" in header
    assert "barrier_tp_first_rate_w1" in header
    assert "barrier_tp_first_rate_w2" in header
    assert len(header.split(",")) == len(
        (tmp_path / "directional_viability.csv").read_text().splitlines()[1].split(",")
    )


def test_directional_ranked_preserves_near_miss_rejections(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    candidate = _make_candidate("near_miss")
    result = DirectionalResult(
        candidate_id=candidate.candidate_id,
        passed=False,
        rejection_reason="weak_barrier_win_rate:w1",
        signal_counts={"w1": 30},
        long_ratios={"w1": 0.5},
        median_stop_atr={"w1": 1.0},
        barrier_metrics={
            "w1": BarrierMetrics(
                total=30,
                tp_first=16,
                sl_first=14,
                unresolved_tail=0,
                tp_first_rate=16 / 30,
                sl_first_rate=14 / 30,
                unresolved_tail_rate=0.0,
                win_rate=16 / 30,
                median_mae_pct=1.0,
                median_mfe_pct=1.5,
                median_bars_to_tp=4.0,
            )
        },
        behavior=None,
    )
    _append_directional_result(tmp_path, candidate, result, windows)

    ranked = dss_directional_search_module.write_directional_ranked(
        tmp_path, DSSConfig(output=tmp_path, windows=windows)
    )

    assert ranked == []
    near_misses = (tmp_path / "directional_near_misses.csv").read_text(encoding="utf-8")
    assert "near_miss" in near_misses
    assert "weak_barrier_win_rate:w1" in near_misses


def test_directional_rejects_overtrading(tmp_path: Path) -> None:
    primary = _make_primary(120)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-06")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 51)),
    )
    assert result.passed is False
    assert result.rejection_reason == "overtrading:w1"


def test_directional_allows_up_to_ten_signals_per_day(tmp_path: Path) -> None:
    primary = _make_barrier_primary()
    primary = pd.concat([primary] * 4, ignore_index=True)
    primary.index = pd.date_range("2024-01-01", periods=len(primary), freq="1h", tz="UTC")
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-07")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        min_trades_per_window=1,
        min_barrier_tp_first_rate=0.0,
        min_barrier_win_rate=0.0,
    )
    result = evaluate_directional_viability(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 49)),
    )
    assert result.rejection_reason != "overtrading:w1"


def test_dss_strategy_allowed_signal_filters_direction() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1.0, 1.0, 1.0],
        },
        index=index,
    )
    strategy = DSSStrategy(
        {
            "trigger_name": "pt_engulfing",
            "trigger_params": {"body_ratio": 0.7},
            "filter_names": [],
            "filter_params": {},
            "rrr": 1.0,
            "risk_percent": 1.0,
            "position_ttl_bars": 16,
            "allowed_signal": -1,
        }
    )
    strategy._generate_fn = lambda data: pd.DataFrame(  # noqa: ARG005
        {
            "bar_time": [index[0], index[1]],
            "symbol": ["SOL-USDT-SWAP", "SOL-USDT-SWAP"],
            "side": ["long", "short"],
            "confidence": [80.0, 80.0],
            "rationale": ["long", "short"],
            "entry_price": [100.5, 101.5],
            "stop_price": [99.0, 103.0],
            "tp_price": [102.0, 99.0],
        }
    )

    signals = strategy.generate(primary)

    assert signals["signal"].tolist() == [0, -1, 0]


def test_dss_strategy_adds_default_stop_for_directional_only_signals() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1.0, 1.0, 1.0],
        },
        index=index,
    )
    strategy = DSSStrategy(
        {
            "trigger_name": "pt_engulfing",
            "trigger_params": {"body_ratio": 0.7},
            "filter_names": [],
            "filter_params": {},
            "directional_sl_move_pct": 0.004,
        }
    )
    strategy._generate_fn = lambda data: pd.DataFrame(  # noqa: ARG005
        {
            "bar_time": [index[0], index[1]],
            "symbol": ["SOL-USDT-SWAP", "SOL-USDT-SWAP"],
            "side": ["long", "short"],
            "confidence": [80.0, 80.0],
            "rationale": ["directional long", "directional short"],
            "entry_price": [0.0, 0.0],
            "stop_price": [0.0, 0.0],
            "tp_price": [0.0, 0.0],
        }
    )

    signals = strategy.generate(primary)

    assert signals.loc[index[0], "sl_price"] == pytest.approx(101.0 * 0.996)
    assert signals.loc[index[1], "sl_price"] == pytest.approx(102.0 * 1.004)


def test_dss_strategy_atr_default_stop_uses_previous_closed_tr() -> None:
    index = pd.date_range("2026-01-01", periods=16, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0] * 15 + [107.0],
            "high": [101.0] * 15 + [120.0],
            "low": [99.0] * 15 + [80.0],
            "close": [100.0] * len(index),
            "volume": [1.0] * len(index),
        },
        index=index,
    )
    strategy = DSSStrategy(
        {
            "trigger_name": "pt_engulfing",
            "trigger_params": {"body_ratio": 0.7},
            "filter_names": [],
            "filter_params": {},
            "directional_sl_move_pct": 0.004,
            "atr_sl_mult": 1.5,
        }
    )
    strategy._generate_fn = lambda data: pd.DataFrame(  # noqa: ARG005
        {
            "bar_time": [index[-2]],
            "symbol": ["SOL-USDT-SWAP"],
            "side": ["long"],
            "confidence": [80.0],
            "rationale": ["directional long"],
            "entry_price": [0.0],
            "stop_price": [0.0],
            "tp_price": [0.0],
        }
    )

    signals = strategy.generate(primary)

    assert signals.loc[index[-2], "sl_price"] == pytest.approx(100.0 - 2.0 * 1.5)


def test_dss_strategy_entry_skip_rules_filter_next_bar_entry_features() -> None:
    index = pd.date_range("2026-01-02 23:00", periods=4, freq="h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        },
        index=index,
    )
    strategy = DSSStrategy(
        {
            "trigger_name": "pt_engulfing",
            "trigger_params": {"body_ratio": 0.7},
            "filter_names": [],
            "filter_params": {},
            "rrr": 1.0,
            "risk_percent": 1.0,
            "position_ttl_bars": 16,
            "allowed_signal": -1,
            "entry_skip_rules": [
                {
                    "conditions": [
                        {"feature": "stop_distance_pct", "op": ">=", "value": 0.02},
                        {"feature": "entry_dayofweek", "op": ">=", "value": 5.0},
                    ]
                }
            ],
        }
    )
    strategy._generate_fn = lambda data: pd.DataFrame(  # noqa: ARG005
        {
            "bar_time": [index[0], index[1]],
            "symbol": ["SOL-USDT-SWAP", "SOL-USDT-SWAP"],
            "side": ["short", "short"],
            "confidence": [80.0, 80.0],
            "rationale": ["wide weekend short", "normal short"],
            "entry_price": [100.0, 100.0],
            "stop_price": [103.0, 101.0],
            "tp_price": [97.0, 99.0],
        }
    )

    signals = strategy.generate(primary)

    assert signals["signal"].tolist() == [0, -1, 0, 0]


def test_dss_v1_output_dir_fails_resume(tmp_path: Path) -> None:
    (tmp_path / "study.journal").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="legacy DSS artifacts"):
        _guard_output_dir(tmp_path)


def test_dss_directional_state_serializes_slots_window_specs(tmp_path: Path) -> None:
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


def test_dss_directional_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
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
    result = run_dss_directional_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    assert ticks == [1] * result.generated
    assert (tmp_path / "candidate_journal.jsonl").exists()
    assert (tmp_path / "seen_candidates.jsonl").exists()
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["generated"] == result.generated
    assert progress["status"] == "stopped"
    assert json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))[
        "status"
    ] == "stopped"
    assert not (tmp_path / "search.lock").exists()


def test_dss_directional_resume_ticks_existing_evaluations(tmp_path: Path) -> None:
    candidate = _make_candidate("dssv3_000001")
    windows = [
        DSSWindowSpec(
            label="w1",
            symbol="TEST-USDT-SWAP",
            start="2024-01-01",
            end="2024-01-10",
        )
    ]
    (tmp_path / "candidates.jsonl").write_text(
        json.dumps(candidate.to_dict()) + "\n",
        encoding="utf-8",
    )
    _append_directional_result(tmp_path, candidate, _make_directional_pass(candidate), windows)
    ticks: list[int] = []

    result = run_dss_directional_search(
        config=DSSConfig(
            output=tmp_path,
            windows=windows,
            n_trials=1,
            min_trades_per_window=1,
        ),
        search_space=DSSSearchSpace(
            trigger_names=("pt_nr4_breakout",),
            filter_names=(),
            trigger_param_bounds={"pt_nr4_breakout": {}},
            filter_param_bounds={},
            max_filters=0,
        ),
        window_data={"w1": _make_strategy_data(_make_primary(80))},
        progress_callback=ticks.append,
    )

    assert result.generated == 1
    assert ticks == [1]


def test_catcma_model_updates_full_catcmawm_generation() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_a", "pt_b"),
        filter_names=("pf_a", "pf_b"),
        trigger_param_bounds={"pt_a": {}, "pt_b": {}},
        filter_param_bounds={"pf_a": {}, "pf_b": {}},
        max_filters=2,
    )
    model = _WeightedModel(search_space, seed=123)
    candidates = [
        model.sample(f"c{i}", generation=0) for i in range(model._optimizer.population_size)
    ]
    model.update(
        [
            _EvaluatedCandidate(
                candidate,
                robust_score=10.0 if candidate.trigger_name == "pt_b" else 0.0,
            )
            for candidate in candidates
        ]
    )
    assert model.backend_name == "cmaes.CatCMAwM"
    assert model._tell_count == 1
    assert not model._feedback


def test_catcma_qd_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
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
        n_trials=4,
        min_trades_per_window=10_000,
        algorithm="catcma_qd",
        seed=777,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    result = run_catcma_qd_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    assert ticks == [1] * result.generated
    assert result.generated == 1
    assert (tmp_path / "backend_state" / "catcma_qd_state.csv").exists()


def test_catcma_qd_directional_feedback_selection_caps_batch_cost() -> None:
    candidates = [
        _DirectionalCandidate(
            candidate=(candidate := _make_candidate(f"c{i}", trigger_name=f"pt_{i % 12}")),
            result=DirectionalResult(
                candidate_id=candidate.candidate_id,
                passed=True,
                rejection_reason="",
                signal_counts={"w1": 20},
                long_ratios={"w1": 1.0},
                median_stop_atr={"w1": 0.01},
                barrier_metrics={
                    "w1": BarrierMetrics(
                        total=20,
                        tp_first=12,
                        sl_first=8,
                        unresolved_tail=0,
                        tp_first_rate=0.6,
                        sl_first_rate=0.4,
                        unresolved_tail_rate=0.0,
                        win_rate=0.6,
                        median_mae_pct=0.5,
                        median_mfe_pct=1.5,
                        median_bars_to_tp=4.0,
                    )
                },
                behavior=_make_behavior(candidate.trigger_name),
            ),
            cheap_score=float(i),
        )
        for i in range(40)
    ]
    selected = _select_directional_feedback_candidates(candidates, batch_size=48)
    assert len(selected) == 5
    assert len({item.result.behavior.cell_key for item in selected if item.result.behavior}) > 1


def test_catcma_qd_resume_continues_after_existing_candidates(tmp_path: Path) -> None:
    existing = _make_candidate("catcma_000001").to_dict()
    (tmp_path / "candidates.jsonl").write_text(
        json.dumps(existing) + "\n",
        encoding="utf-8",
    )
    primary = _make_primary(200)
    config = DSSConfig(
        output=tmp_path,
        windows=[
            DSSWindowSpec(
                label="w1",
                symbol="TEST-USDT-SWAP",
                start="2024-01-01",
                end="2024-01-10",
            )
        ],
        n_trials=3,
        min_trades_per_window=10_000,
        algorithm="catcma_qd",
        seed=777,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    result = run_catcma_qd_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    lines = (tmp_path / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(line)["candidate_id"] for line in lines]
    assert ticks == [1] * result.generated
    assert ids == ["catcma_000001", "catcma_000002"]
    journal = (tmp_path / "candidate_journal.jsonl").read_text(encoding="utf-8")
    assert "duplicate_skipped" in journal


def test_catcma_qd_resume_reports_existing_candidates_above_budget(tmp_path: Path) -> None:
    candidates = [_make_candidate("catcma_000001"), _make_candidate("catcma_000002")]
    (tmp_path / "candidates.jsonl").write_text(
        "".join(json.dumps(candidate.to_dict()) + "\n" for candidate in candidates),
        encoding="utf-8",
    )
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    _append_directional_result(tmp_path, candidates[0], _make_directional_pass(candidates[0]), windows)

    result = run_catcma_qd_search(
        config=DSSConfig(
            output=tmp_path,
            windows=windows,
            n_trials=1,
            min_trades_per_window=1,
            algorithm="catcma_qd",
            seed=777,
        ),
        search_space=DSSSearchSpace(
            trigger_names=("pt_nr4_breakout",),
            filter_names=(),
            trigger_param_bounds={"pt_nr4_breakout": {}},
            filter_param_bounds={},
            max_filters=0,
        ),
        window_data={"w1": _make_strategy_data(_make_primary(80))},
    )

    assert result.generated == 2
    assert "Generated candidates: **2**" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_island_qd_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(
            label="w1",
            symbol="TEST-USDT-SWAP",
            start="2024-01-01",
            end="2024-01-10",
        ),
        DSSWindowSpec(
            label="w2",
            symbol="TEST-USDT-SWAP",
            start="2024-02-01",
            end="2024-02-10",
        ),
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        n_trials=4,
        min_trades_per_window=10_000,
        algorithm="island_qd",
        seed=888,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    result = run_island_qd_search(
        config=config,
        search_space=search_space,
        window_data={
            "w1": _make_strategy_data(primary),
            "w2": _make_strategy_data(primary),
        },
        progress_callback=ticks.append,
    )
    assert ticks == [1] * result.generated
    assert result.generated == 1
    assert (tmp_path / "candidates.jsonl").exists()


def test_hyperband_qd_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
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
        n_trials=4,
        min_trades_per_window=10_000,
        algorithm="hyperband_qd",
        seed=999,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    result = run_hyperband_qd_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    assert ticks == [1] * result.generated
    assert result.generated == 1
    assert (tmp_path / "backend_state" / "hyperband_qd_state.csv").exists()


def test_hyperband_qd_rung_selection_caps_expensive_evaluations() -> None:
    items: list[_RungCandidate] = []
    for i in range(40):
        candidate = _make_candidate(f"c{i}", trigger_name=f"pt_{i % 16}")
        behavior = _make_behavior(candidate.trigger_name)
        directional = _DirectionalCandidate(
            candidate=candidate,
            result=DirectionalResult(
                candidate_id=candidate.candidate_id,
                passed=True,
                rejection_reason="",
                signal_counts={"w1": 20},
                long_ratios={"w1": 0.5},
                median_stop_atr={"w1": 0.01},
                barrier_metrics={
                    "w1": BarrierMetrics(
                        total=20,
                        tp_first=10,
                        sl_first=5,
                        unresolved_tail=5,
                        tp_first_rate=0.5,
                        sl_first_rate=0.25,
                        unresolved_tail_rate=0.25,
                        win_rate=2 / 3,
                        median_mae_pct=0.5,
                        median_mfe_pct=1.5,
                        median_bars_to_tp=4.0,
                    )
                },
                behavior=behavior,
            ),
            cheap_score=float(i),
        )
        items.append(_RungCandidate(directional))

    selected = _select_rung_promotions(
        items,
        fraction=0.30,
        minimum=3,
        score_getter=lambda item: item.directional.cheap_score,
    )
    assert len(selected) == 12
    selected_cells = {
        item.directional.result.behavior.cell_key
        for item in selected
        if item.directional.result.behavior is not None
    }
    assert len(selected_cells) > 1


def test_smac_qd_encoder_is_fixed_width_for_conditional_candidates() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_a", "pt_b"),
        filter_names=("pf_a", "pf_b"),
        trigger_param_bounds={
            "pt_a": {"lookback": IntParam(2, 6, 1)},
            "pt_b": {"threshold": FloatParam(0.1, 0.5, 0.1)},
        },
        filter_param_bounds={
            "pf_a": {"mode": CategoricalParam(("x", "y"))},
            "pf_b": {},
        },
        max_filters=2,
    )
    encoder = _CandidateEncoder(search_space)
    c1 = DSSCandidate(
        candidate_id="c1",
        trigger_name="pt_a",
        trigger_params={"lookback": 4},
        filter_names=("pf_a",),
        filter_params={"pf_a": {"mode": "y"}},
        generation=0,
    )
    c2 = DSSCandidate(
        candidate_id="c2",
        trigger_name="pt_b",
        trigger_params={"threshold": 0.3},
        filter_names=("pf_b",),
        filter_params={"pf_b": {}},
        generation=0,
    )
    assert len(encoder.encode(c1)) == len(encoder.feature_names)
    assert len(encoder.encode(c2)) == len(encoder.feature_names)
    assert encoder.encode(c1) != encoder.encode(c2)


def test_smac_qd_random_forest_surrogate_predicts_elite_region() -> None:
    surrogate = _RandomForestSurrogate(seed=123)
    x_rows = [[0.0], [0.1], [0.9], [1.0]]
    y = [-100.0, -80.0, 50.0, 60.0]
    surrogate.fit(x_rows, y)
    means, stds = surrogate.predict([[0.05], [0.95]])
    assert surrogate.fitted
    assert means[1] > means[0]
    assert len(stds) == 2


def test_smac_qd_surrogate_fit_uses_capped_recent_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    encoder = _CandidateEncoder(search_space)
    surrogate = _RandomForestSurrogate(seed=1)
    observations = [
        smac_qd_module._SMACObservation(
            candidate=_make_candidate(f"c{i}"),
            target_score=float(i),
            fidelity="directional_reject",
        )
        for i in range(5_100)
    ]
    fit_sizes: list[int] = []

    def _fake_fit(x_rows: list[list[float]], y: list[float]) -> None:
        fit_sizes.append(len(x_rows))
        assert y[0] == 100.0

    monkeypatch.setattr(surrogate, "fit", _fake_fit)

    smac_qd_module._fit_surrogate(surrogate, encoder, observations)

    assert fit_sizes == [5_000]


def test_smac_qd_progress_callback_ticks_per_candidate(tmp_path: Path) -> None:
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
        n_trials=4,
        min_trades_per_window=10_000,
        algorithm="smac_qd",
        seed=1001,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    ticks: list[int] = []
    result = run_smac_qd_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    assert ticks == [1] * result.generated
    assert result.generated == 1
    assert (tmp_path / "backend_state" / "smac_qd_state.csv").exists()
    assert (tmp_path / "smac_qd_observations.csv").exists()
    observations = (tmp_path / "smac_qd_observations.csv").read_text(encoding="utf-8")
    assert "directional_reject" in observations


def test_dss_directional_search_exports_shortlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = _make_primary(80)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        n_trials=1,
        min_trades_per_window=1,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )
    behavior = DSSBehavior(
        trigger_family="pt_nr4_breakout",
        side_profile="balanced",
        frequency_class="medium",
        regime_strength="balanced",
        filter_depth="0",
    )

    def _fake_directional(
        candidate: DSSCandidate,
        _window_data: dict[str, StrategyData],
        _config: DSSConfig,
        _composer: object | None = None,
    ) -> DirectionalResult:
        return DirectionalResult(
            candidate_id=candidate.candidate_id,
            passed=True,
            rejection_reason="",
            signal_counts={"w1": 12},
            long_ratios={"w1": 0.5},
            median_stop_atr={"w1": 1.0},
            barrier_metrics={
                "w1": BarrierMetrics(
                    total=12,
                    tp_first=8,
                    sl_first=4,
                    unresolved_tail=0,
                    tp_first_rate=8 / 12,
                    sl_first_rate=4 / 12,
                    unresolved_tail_rate=0.0,
                    win_rate=8 / 12,
                    median_mae_pct=0.8,
                    median_mfe_pct=1.4,
                    median_bars_to_tp=3.0,
                )
            },
            behavior=behavior,
            candidate_class="balanced",
        )

    monkeypatch.setattr(dss_directional_search_module, "evaluate_directional_viability", _fake_directional)

    result = dss_directional_search_module.run_dss_directional_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
    )

    assert result.directional_survivors == 1
    assert (tmp_path / "directional_ranked.csv").exists()
    assert (tmp_path / "directional_candidates").exists()
    assert not (tmp_path / "replay_proxy.csv").exists()
    assert not (tmp_path / "replay_full_scores.csv").exists()
    assert "Evaluator: **directional_labeling_only**" in (
        tmp_path / "summary.md"
    ).read_text(encoding="utf-8")


def test_directional_export_replaces_stale_candidate_files(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, top_n_candidates=1)
    candidates = [_make_candidate("c1"), _make_candidate("c2", trigger_name="pt_ema_cross")]
    (tmp_path / "candidates.jsonl").write_text(
        "".join(json.dumps(candidate.to_dict()) + "\n" for candidate in candidates),
        encoding="utf-8",
    )
    for candidate in candidates:
        _append_directional_result(tmp_path, candidate, _make_directional_pass(candidate), windows)
    stale_dir = tmp_path / "directional_candidates"
    stale_dir.mkdir()
    (stale_dir / "directional_999_stale.json").write_text("{}", encoding="utf-8")

    ranked = write_directional_ranked(tmp_path, config)
    exported = export_directional_candidates(ranked, tmp_path, config)

    assert len(exported) == 1
    assert not (stale_dir / "directional_999_stale.json").exists()
    assert len(list(stale_dir.glob("directional_*.json"))) == 1


def test_directional_export_includes_default_execution_geometry(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        top_n_candidates=1,
        directional_sl_move_pct=0.004,
    )
    candidate = _make_candidate("c1")
    (tmp_path / "candidates.jsonl").write_text(
        json.dumps(candidate.to_dict()) + "\n",
        encoding="utf-8",
    )
    _append_directional_result(tmp_path, candidate, _make_directional_pass(candidate), windows)

    ranked = write_directional_ranked(tmp_path, config)
    exported = export_directional_candidates(ranked, tmp_path, config)
    payload = json.loads(exported[0].read_text(encoding="utf-8"))

    assert payload["params"]["rrr"] == 2.0
    assert payload["params"]["risk_percent"] == 1.0
    assert payload["params"]["position_ttl_minutes"] == 720
    assert payload["params"]["position_ttl_bars"] == 12
    assert payload["params"]["directional_sl_move_pct"] == 0.004


def test_directional_export_deduplicates_signal_fingerprints(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, top_n_candidates=2)
    candidates = [_make_candidate("c1"), _make_candidate("c2", trigger_name="pt_ema_cross")]
    (tmp_path / "candidates.jsonl").write_text(
        "".join(json.dumps(candidate.to_dict()) + "\n" for candidate in candidates),
        encoding="utf-8",
    )
    for candidate in candidates:
        result = _make_directional_pass(candidate)
        result = DirectionalResult(
            candidate_id=result.candidate_id,
            passed=result.passed,
            rejection_reason=result.rejection_reason,
            signal_counts=result.signal_counts,
            long_ratios=result.long_ratios,
            median_stop_atr=result.median_stop_atr,
            barrier_metrics=result.barrier_metrics,
            behavior=result.behavior,
            candidate_class=result.candidate_class,
            target_window=result.target_window,
            advisory_score=result.advisory_score,
            metadata={"signal_fingerprint": "same-signal-set", "signal_set_size": 12},
        )
        _append_directional_result(tmp_path, candidate, result, windows)

    ranked = write_directional_ranked(tmp_path, config)
    exported = export_directional_candidates(ranked, tmp_path, config)

    assert len(exported) == 1


def test_directional_export_prefers_active_frequency_buckets() -> None:
    rows = [
        {"candidate_id": "sparse_1", "frequency_class": "sparse", "signal_fingerprint": "s1"},
        {"candidate_id": "medium_1", "frequency_class": "medium", "signal_fingerprint": "m1"},
        {"candidate_id": "frequent_1", "frequency_class": "frequent", "signal_fingerprint": "f1"},
        {"candidate_id": "sparse_2", "frequency_class": "sparse", "signal_fingerprint": "s2"},
    ]

    selected = _select_directional_export_rows(rows, top_n=3)

    assert [row["candidate_id"] for row in selected] == [
        "frequent_1",
        "medium_1",
        "sparse_1",
    ]


def test_directional_rank_score_rewards_more_active_viable_candidates() -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    base = {
        "barrier_win_rate_w1": 0.52,
        "barrier_tp_first_rate_w1": 0.52,
        "barrier_sl_first_rate_w1": 0.48,
        "barrier_unresolved_tail_rate_w1": 0.0,
    }

    sparse = {**base, "signals_w1": 35}
    frequent = {**base, "signals_w1": 220}

    assert directional_rank_score(frequent, windows) > directional_rank_score(sparse, windows)


def test_signal_novelty_tracker_rejects_duplicate_promoted_fingerprint(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    first = _make_candidate("c1")
    second = _make_candidate("c2", trigger_name="pt_ema_cross")
    first_result = _make_directional_pass(first)
    first_result = DirectionalResult(
        candidate_id=first_result.candidate_id,
        passed=first_result.passed,
        rejection_reason=first_result.rejection_reason,
        signal_counts=first_result.signal_counts,
        long_ratios=first_result.long_ratios,
        median_stop_atr=first_result.median_stop_atr,
        barrier_metrics=first_result.barrier_metrics,
        behavior=first_result.behavior,
        candidate_class=first_result.candidate_class,
        target_window=first_result.target_window,
        advisory_score=first_result.advisory_score,
        metadata={"signal_fingerprint": "fp1", "signal_set_size": 12},
    )
    second_result = DirectionalResult(
        candidate_id=second.candidate_id,
        passed=first_result.passed,
        rejection_reason=first_result.rejection_reason,
        signal_counts=first_result.signal_counts,
        long_ratios=first_result.long_ratios,
        median_stop_atr=first_result.median_stop_atr,
        barrier_metrics=first_result.barrier_metrics,
        behavior=first_result.behavior,
        candidate_class=first_result.candidate_class,
        target_window=first_result.target_window,
        advisory_score=first_result.advisory_score,
        metadata={"signal_fingerprint": "fp1", "signal_set_size": 12},
    )

    tracker = DSSSignalNoveltyTracker(tmp_path / "directional_viability.csv")

    assert tracker.register(first_result) is True
    _append_directional_result(tmp_path, first, first_result, windows)
    assert tracker.register(second_result) is False


def test_signal_novelty_tracker_rejects_high_overlap_promoted_signal(tmp_path: Path) -> None:
    candidate = _make_candidate("c1")
    first_result = replace(
        _make_directional_pass(candidate),
        metadata={
            "signal_fingerprint": "fp1",
            "signal_identity_keys": [f"w1|2024-01-{day:02d}T00:00:00+00:00|long" for day in range(1, 11)],
            "signal_set_size": 10,
        },
    )
    second_result = replace(
        _make_directional_pass(_make_candidate("c2", trigger_name="pt_ema_cross")),
        metadata={
            "signal_fingerprint": "fp2",
            "signal_identity_keys": [
                *[f"w1|2024-01-{day:02d}T00:00:00+00:00|long" for day in range(1, 9)],
                "w1|2024-02-01T00:00:00+00:00|long",
                "w1|2024-02-02T00:00:00+00:00|long",
            ],
            "signal_set_size": 10,
        },
    )

    tracker = DSSSignalNoveltyTracker(tmp_path / "directional_viability.csv")

    assert tracker.register(first_result) is True
    assert tracker.register(second_result) is False


def test_signal_novelty_tracker_restores_overlap_from_viability_csv(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    first = _make_candidate("c1")
    first_result = replace(
        _make_directional_pass(first),
        metadata={
            "signal_fingerprint": "fp1",
            "signal_identity_keys": [
                f"w1|2024-01-{day:02d}T00:00:00+00:00|long" for day in range(1, 11)
            ],
            "signal_set_size": 10,
        },
    )
    _append_directional_result(tmp_path, first, first_result, windows)

    resumed_tracker = DSSSignalNoveltyTracker(tmp_path / "directional_viability.csv")
    overlapping_result = replace(
        _make_directional_pass(_make_candidate("c2", trigger_name="pt_ema_cross")),
        metadata={
            "signal_fingerprint": "fp2",
            "signal_identity_keys": [
                *[f"w1|2024-01-{day:02d}T00:00:00+00:00|long" for day in range(1, 9)],
                "w1|2024-02-01T00:00:00+00:00|long",
                "w1|2024-02-02T00:00:00+00:00|long",
            ],
            "signal_set_size": 10,
        },
    )

    assert resumed_tracker.register(overlapping_result) is False


def test_random_directional_candidate_uses_independent_sampler() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_a@15m", "pt_b@H4"),
        filter_names=("pf_a@15m", "pf_b@H4", "pf_c@D1"),
        trigger_param_bounds={"pt_a": {}, "pt_b": {}},
        filter_param_bounds={"pf_a": {}, "pf_b": {}, "pf_c": {}},
        max_filters=3,
    )

    candidate = sample_random_directional_candidate(
        search_space=search_space,
        candidate_id="random_000005",
        generation=7,
        max_filters=3,
        seed=123,
    )

    assert candidate.candidate_id == "random_000005"
    assert candidate.generation == 7
    assert candidate.trigger_name in {"pt_a", "pt_b"}
    assert candidate.trigger_timeframe in {"15m", "H4"}
    assert set(candidate.filter_names).issubset(set(search_space.filter_names))


def test_directional_duplicate_signal_demotes_exportable_result() -> None:
    result = _make_directional_pass(_make_candidate())

    demoted = _directional_with_novelty(result, is_novel_signal=False)

    assert demoted.passed is False
    assert demoted.should_promote is False
    assert demoted.rejection_reason == "duplicate_signal_set"
    assert demoted.advisory_score is not None
    assert demoted.advisory_score < 0


def test_smac_observation_penalizes_duplicate_promoted_signal() -> None:
    candidate = _make_candidate()
    result = _make_directional_pass(candidate)

    observation = smac_qd_module._directional_observation(
        candidate, result, is_novel_signal=False
    )

    assert observation.fidelity == "duplicate_signal"
    assert observation.target_score < 0


@pytest.mark.parametrize(
    ("runner", "algorithm"),
    [
        (run_dss_directional_search, "directional"),
        (run_catcma_qd_search, "catcma_qd"),
        (run_island_qd_search, "island_qd"),
        (run_hyperband_qd_search, "hyperband_qd"),
        (run_smac_qd_search, "smac_qd"),
    ],
)
def test_dss_resume_evaluates_candidate_without_directional_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[..., DSSDirectionalResult],
    algorithm: str,
) -> None:
    candidate = _make_candidate("pending_000001")
    (tmp_path / "candidates.jsonl").write_text(
        json.dumps(candidate.to_dict()) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "seen_candidates.jsonl").write_text(
        json.dumps(
            {
                "candidate_hash": candidate.candidate_key,
                "candidate_id": candidate.candidate_id,
                "ts": "2026-07-31T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]

    def _fake_directional(
        candidate: DSSCandidate,
        _window_data: dict[str, StrategyData],
        _config: DSSConfig,
        _composer: object | None = None,
    ) -> DirectionalResult:
        return _make_directional_pass(candidate)

    monkeypatch.setattr(dss_directional_search_module, "evaluate_directional_viability", _fake_directional)

    result = runner(
        config=DSSConfig(
            output=tmp_path,
            windows=windows,
            n_trials=1,
            min_trades_per_window=1,
            algorithm=algorithm,  # type: ignore[arg-type]
        ),
        search_space=DSSSearchSpace(
            trigger_names=("pt_nr4_breakout",),
            filter_names=(),
            trigger_param_bounds={"pt_nr4_breakout": {}},
            filter_param_bounds={},
            max_filters=0,
        ),
        window_data={"w1": _make_strategy_data(_make_primary(80))},
    )

    assert result.generated == 1
    assert result.directional_survivors == 1
    viability = (tmp_path / "directional_viability.csv").read_text(encoding="utf-8")
    assert "pending_000001" in viability
    journal = (tmp_path / "candidate_journal.jsonl").read_text(encoding="utf-8")
    assert "candidate_evaluated" in journal


@pytest.mark.parametrize(
    ("module", "runner"),
    [
        (catcma_qd_module, run_catcma_qd_search),
        (island_qd_module, run_island_qd_search),
        (hyperband_qd_module, run_hyperband_qd_search),
        (smac_qd_module, run_smac_qd_search),
    ],
)
def test_directional_search_all_backends_skip_replay_backtests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    runner: Callable[..., DSSDirectionalResult],
) -> None:
    primary = _make_primary(80)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(
        output=tmp_path,
        windows=windows,
        n_trials=1,
        min_trades_per_window=1,
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )

    def _fake_directional(
        candidate: DSSCandidate,
        _window_data: dict[str, StrategyData],
        _config: DSSConfig,
        _composer: object | None = None,
    ) -> DirectionalResult:
        return _make_directional_pass(candidate)

    _ = module
    monkeypatch.setattr(dss_directional_search_module, "evaluate_directional_viability", _fake_directional)

    result = runner(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
    )

    assert result.directional_survivors == 1
    assert (tmp_path / "directional_ranked.csv").exists()
    assert (tmp_path / "directional_candidates").exists()
    assert not (tmp_path / "replay_proxy.csv").exists()
    assert not (tmp_path / "replay_full_scores.csv").exists()
    assert "Evaluator: **directional_labeling_only**" in (
        tmp_path / "summary.md"
    ).read_text(encoding="utf-8")


def test_search_signals_help_no_longer_exposes_sampler() -> None:
    result = CliRunner().invoke(cli, ["search-signals", "--help"])
    assert result.exit_code == 0
    assert "--sampler" not in result.output
    assert "--algorithm" in result.output
    assert "island_qd" in result.output
    assert "hyperband_qd" in result.output
    assert "smac_qd" in result.output


def test_search_signals_without_n_trials_runs_endless_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_load_discovery_window(**_kwargs: object) -> StrategyData:
        return _make_multiframe_strategy_data(_make_primary(80))

    def _fake_runner(
        *,
        config: DSSConfig,
        search_space: DSSSearchSpace,
        window_data: dict[str, StrategyData],
        progress_callback: Callable[[int], None] | None = None,
    ) -> DSSDirectionalResult:
        captured["n_trials"] = config.n_trials
        captured["progress_callback"] = progress_callback
        captured["trigger_count"] = len(search_space.trigger_names)
        captured["window_count"] = len(window_data)
        return DSSDirectionalResult(
            output=config.output,
            generated=0,
            directional_survivors=0,
            exported_candidates=0,
            archive=DSSArchive(),
        )

    monkeypatch.setattr("backtester.__main__._load_discovery_window", _fake_load_discovery_window)
    monkeypatch.setattr("backtester.__main__.run_dss_directional_search", _fake_runner)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "endless mode" in result.output
    assert captured["n_trials"] is None
    assert captured["progress_callback"] is None
    assert captured["window_count"] == 1
    assert captured["trigger_count"] > 0


def test_search_signals_multi_symbol_keeps_distinct_window_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_load_discovery_window(**kwargs: object) -> StrategyData:
        return _make_multiframe_strategy_data(
            _make_primary(80),
            symbol=str(kwargs["symbol"]),
        )

    def _fake_runner(
        *,
        config: DSSConfig,
        search_space: DSSSearchSpace,
        window_data: dict[str, StrategyData],
        progress_callback: Callable[[int], None] | None = None,
    ) -> DSSDirectionalResult:
        _ = search_space, progress_callback
        captured["window_labels"] = [window.label for window in config.windows]
        captured["window_symbols"] = [window.symbol for window in config.windows]
        captured["window_data_keys"] = sorted(window_data)
        captured["metadata"] = {
            key: dict(data.metadata) for key, data in sorted(window_data.items())
        }
        return DSSDirectionalResult(
            output=config.output,
            generated=0,
            directional_survivors=0,
            exported_candidates=[],
            archive=DSSArchive(),
        )

    monkeypatch.setattr("backtester.__main__._load_discovery_window", _fake_load_discovery_window)
    monkeypatch.setattr("backtester.__main__.run_dss_directional_search", _fake_runner)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--symbol",
            "BTC-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert captured["window_labels"] == [
        "SOL-USDT-SWAP:smoke",
        "BTC-USDT-SWAP:smoke",
    ]
    assert captured["window_symbols"] == ["SOL-USDT-SWAP", "BTC-USDT-SWAP"]
    assert captured["window_data_keys"] == [
        "BTC-USDT-SWAP:smoke",
        "SOL-USDT-SWAP:smoke",
    ]
    assert captured["metadata"] == {
        "BTC-USDT-SWAP:smoke": {
            "symbol": "BTC-USDT-SWAP",
            "window_label": "BTC-USDT-SWAP:smoke",
        },
        "SOL-USDT-SWAP:smoke": {
            "symbol": "SOL-USDT-SWAP",
            "window_label": "SOL-USDT-SWAP:smoke",
        },
    }


def test_search_signals_preflight_rejects_missing_required_timeframes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_load_discovery_window(**_kwargs: object) -> StrategyData:
        return _make_strategy_data(_make_primary(80))

    def _fail_runner(**_kwargs: object) -> DSSDirectionalResult:
        raise AssertionError("DSS runner must not start when required candles are missing")

    monkeypatch.setattr("backtester.__main__._load_discovery_window", _fake_load_discovery_window)
    monkeypatch.setattr("backtester.__main__.run_dss_directional_search", _fail_runner)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "DSS search space requires candle timeframes" in result.output
    assert "smoke:15m" in result.output
    assert "python -m crypt.backfill" in result.output
    assert "MPLCONFIGDIR" not in result.output
    assert "UV_CACHE_DIR" not in result.output
    assert "--from 2024-01-01" in result.output
    assert "--to 2024-01-06" in result.output
    assert "--data-types ohlcv" in result.output


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
    assert "DSS directional search removed the old Optuna sampler path" in result.output


def test_search_signals_matrix_help() -> None:
    result = CliRunner().invoke(cli, ["search-signals-matrix", "--help"])
    assert result.exit_code == 0
    assert "--n-jobs-per-algorithm" not in result.output
    assert "--algorithms" in result.output
    assert "--min-signals-per-week FLOAT" not in result.output
    assert "[default: data]" in result.output
    assert "[default: SOL-USDT-SWAP]" in result.output


def test_search_signals_matrix_rejects_unknown_algorithm() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "search-signals-matrix",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--algorithms",
            "generated,nope",
        ],
    )
    assert result.exit_code != 0
    assert "unknown value" in result.output
    assert "nope" in result.output


def test_search_signals_matrix_preflight_rejects_before_spawning_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_load_discovery_window(**_kwargs: object) -> StrategyData:
        return _make_strategy_data(_make_primary(80))

    def _fail_popen(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("matrix must not spawn children before candle preflight passes")

    monkeypatch.setattr("backtester.__main__._load_discovery_window", _fake_load_discovery_window)
    monkeypatch.setattr("backtester.__main__.subprocess.Popen", _fail_popen)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals-matrix",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "DSS search space requires candle timeframes" in result.output
    assert "python -m crypt.backfill" in result.output
    assert "MPLCONFIGDIR" not in result.output
    assert "UV_CACHE_DIR" not in result.output


def _capture_search_signals_matrix_children(
    monkeypatch: pytest.MonkeyPatch,
) -> list[list[str]]:
    launched: list[list[str]] = []

    def _fake_load_discovery_window(**_kwargs: object) -> StrategyData:
        return _make_multiframe_strategy_data(_make_primary(80))

    class _FakeProcess:
        pid = 12345

        def __init__(self, cmd: list[str], stdout: object, stderr: object) -> None:
            _ = stdout, stderr
            launched.append(cmd)

        def wait(self) -> int:
            return 0

        def poll(self) -> int:
            return 0

        def terminate(self) -> None:
            raise AssertionError("terminate should not be called on successful children")

    monkeypatch.setattr("backtester.__main__._load_discovery_window", _fake_load_discovery_window)
    monkeypatch.setattr("backtester.__main__.subprocess.Popen", _FakeProcess)
    return launched


def test_search_signals_matrix_defaults_to_endless_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched = _capture_search_signals_matrix_children(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals-matrix",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--algorithms",
            "directional,catcma_qd",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "mode=endless" in result.output
    assert [cmd[cmd.index("--algorithm") + 1] for cmd in launched] == [
        "directional",
        "catcma_qd",
    ]
    assert all("--n-trials" not in cmd for cmd in launched)
    assert all(cmd[cmd.index("--directional-min-wr") + 1] == "0.45" for cmd in launched)


def test_search_signals_matrix_all_alias_launches_every_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched = _capture_search_signals_matrix_children(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals-matrix",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--algorithms",
            "all",
            "--n-trials",
            "1",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert [cmd[cmd.index("--algorithm") + 1] for cmd in launched] == [
        "directional",
        "catcma_qd",
        "island_qd",
        "hyperband_qd",
        "smac_qd",
    ]


def test_search_signals_matrix_launches_bounded_current_dss_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched = _capture_search_signals_matrix_children(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "search-signals-matrix",
            "--data-dir",
            "data",
            "--symbol",
            "SOL-USDT-SWAP",
            "--windows",
            "smoke:2024-01-01:2024-01-05",
            "--candle-timeframe",
            "1h",
            "--n-trials",
            "7",
            "--n-jobs-per-algorithm",
            "2",
            "--algorithms",
            "directional,catcma_qd",
            "--catalog",
            "all",
            "--output-root",
            str(tmp_path),
            "--directional-min-wr",
            "0.42",
        ],
    )

    assert result.exit_code == 0
    assert [cmd[cmd.index("--algorithm") + 1] for cmd in launched] == [
        "directional",
        "catcma_qd",
    ]
    for cmd in launched:
        assert cmd[1:3] == ["-m", "backtester"]
        assert cmd[cmd.index("search-signals")] == "search-signals"
        assert cmd[cmd.index("--n-trials") + 1] == "7"
        assert cmd[cmd.index("--n-jobs") + 1] == "2"
        assert cmd[cmd.index("--catalog") + 1] == "all"
        assert cmd[cmd.index("--directional-min-wr") + 1] == "0.42"
        assert "--sampler" not in cmd
        assert "--resume" not in cmd
        assert "--accept-min-score" not in cmd


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


def test_pinescript_catalog_is_separate_from_legacy_catalog() -> None:
    legacy_triggers = set(parameterized_trigger_catalog())
    legacy_filters = set(parameterized_filter_catalog())
    ps_triggers = set(pinescript_trigger_catalog())
    ps_filters = set(pinescript_filter_catalog())

    assert "pt_ps_supertrend_flip" in ps_triggers
    assert "pt_ps_macd_signal_cross" in ps_triggers
    assert "pt_ps_smc_structure_break" in ps_triggers
    assert "pt_ps_smc_fvg" in ps_triggers
    assert "pt_ps_smc_order_block_retest" in ps_triggers
    assert "pf_ps_adx_di_aligned" in ps_filters
    assert "pf_ps_killzone_session" in ps_filters
    assert "pf_ps_smc_bias" in ps_filters
    assert "pf_ps_smc_premium_discount" in ps_filters
    assert legacy_triggers.isdisjoint(ps_triggers)
    assert legacy_filters.isdisjoint(ps_filters)


def test_pinescript_macd_cross_trigger_emits_events() -> None:
    primary = _make_primary(140)
    primary["close"] = list(np.linspace(120, 90, 70)) + list(np.linspace(90, 130, 70))
    primary["open"] = primary["close"].shift(1).fillna(primary["close"])
    primary["high"] = primary[["open", "close"]].max(axis=1) + 1.0
    primary["low"] = primary[["open", "close"]].min(axis=1) - 1.0
    dataset = build_discovery_dataset(
        data=primary,
        window_label="w1",
        symbol="TEST-USDT-SWAP",
    )

    trigger = pinescript_trigger_catalog()["pt_ps_macd_signal_cross"]({"zero_filter": "off"})
    events = trigger(dataset)

    assert events
    assert {event.trigger_name for event in events} == {"pt_ps_macd_signal_cross_off"}
    assert {event.side for event in events} <= {"long", "short"}
    assert "ps_macd_hist" in events[0].metadata


def test_signal_composer_replays_pinescript_catalog_config() -> None:
    primary = _make_primary(140)
    primary["close"] = list(np.linspace(120, 90, 70)) + list(np.linspace(90, 130, 70))
    primary["open"] = primary["close"].shift(1).fillna(primary["close"])
    primary["high"] = primary[["open", "close"]].max(axis=1) + 1.0
    primary["low"] = primary[["open", "close"]].min(axis=1) - 1.0
    config = TrialConfig(
        trigger_name="pt_ps_macd_signal_cross",
        trigger_params={"zero_filter": "off"},
        filter_names=(),
        filter_params={},
    )

    composer = SignalComposer()
    assert composer.validate_config(config) == []
    signals = composer.build(config)(_make_strategy_data(primary))

    assert not signals.empty
    assert set(signals["side"]) <= {"long", "short"}


def _make_smc_primary() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=90, freq="1h", tz="UTC")
    close = np.array([100.0 + np.sin(i / 3) * 2 + i * 0.08 for i in range(90)])
    close[30:36] = [101, 100, 99, 98, 99, 100]
    close[50:56] = [103, 104, 106, 109, 111, 114]
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 1.0
    low = np.minimum(open_, close) - 1.0
    high[40] = 104.0
    low[42] = 106.0
    high[60] = 112.0
    low[62] = 108.0
    volume = np.full(90, 1_000.0)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )


def test_pinescript_smc_features_and_triggers_emit_events() -> None:
    primary = _make_smc_primary()
    dataset = build_discovery_dataset(
        data=primary,
        window_label="w1",
        symbol="TEST-USDT-SWAP",
    )

    assert "ps_smc_internal_bias" in dataset.features
    assert "ps_smc_bullish_fvg" in dataset.features
    assert dataset.features["ps_smc_bullish_fvg"].fillna(False).any()

    structure_trigger = pinescript_trigger_catalog()["pt_ps_smc_structure_break"](
        {"structure": "internal", "event": "all"}
    )
    fvg_trigger = pinescript_trigger_catalog()["pt_ps_smc_fvg"]({"min_gap_atr": 0.0})

    assert structure_trigger(dataset)
    fvg_events = fvg_trigger(dataset)
    assert fvg_events
    assert {event.side for event in fvg_events} <= {"long", "short"}
    assert "ps_smc_zone" in fvg_events[0].metadata


def test_signal_composer_replays_pinescript_smc_config() -> None:
    primary = _make_smc_primary()
    config = TrialConfig(
        trigger_name="pt_ps_smc_fvg",
        trigger_params={"min_gap_atr": 0.0},
        filter_names=("pf_ps_smc_fvg_recent",),
        filter_params={"pf_ps_smc_fvg_recent": {"lookback": 12}},
    )

    composer = SignalComposer()
    assert composer.validate_config(config) == []
    signals = composer.build(config)(_make_strategy_data(primary))

    assert not signals.empty
    assert set(signals["side"]) <= {"long", "short"}


def test_pinescript_adx_di_filter_uses_side_alignment() -> None:
    primary = _make_primary(80)
    dataset = build_discovery_dataset(
        data=primary,
        window_label="w1",
        symbol="TEST-USDT-SWAP",
    )
    event_time = primary.index[-1]
    event = DiscoveryEvent(
        event_time=event_time,
        side="long",
        trigger_name="test",
        entry_reference_price=100.0,
        window_label="w1",
        symbol="TEST-USDT-SWAP",
        metadata={"ps_adx": 25.0, "ps_di_plus": 30.0, "ps_di_minus": 10.0},
    )
    filter_fn = pinescript_filter_catalog()["pf_ps_adx_di_aligned"]({"min_adx": 20.0})

    assert filter_fn(event, dataset).passed is True
    assert (
        filter_fn(
            DiscoveryEvent(
                event_time=event_time,
                side="short",
                trigger_name="test",
                entry_reference_price=100.0,
                window_label="w1",
                symbol="TEST-USDT-SWAP",
                metadata={"ps_adx": 25.0, "ps_di_plus": 30.0, "ps_di_minus": 10.0},
            ),
            dataset,
        ).passed
        is False
    )


def test_trigger_produces_events_on_synthetic_data() -> None:
    """At least one trigger fires on synthetic noisy data."""
    primary = _make_primary(400)
    dataset = build_discovery_dataset(data=primary, window_label="test", symbol="TEST")
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


def test_dss_v3_signal_composer_does_not_export_trade_geometry() -> None:
    """DSS v3 signals are directional research rows, not trade geometry."""
    primary = _make_primary(500, seed=42)
    data = _make_strategy_data(primary)
    config = TrialConfig(
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
    )
    signal_df = SignalComposer().build(config)(data)
    assert not signal_df.empty
    assert set(signal_df["stop_price"]) == {0.0}
    assert set(signal_df["tp_price"]) == {0.0}


def test_dss_v3_search_space_has_no_geometry_ranges() -> None:
    t_catalog = parameterized_trigger_catalog()
    f_catalog = parameterized_filter_catalog()

    search_space = DSSSearchSpace(
        trigger_names=tuple(sorted(t_catalog.keys())),
        filter_names=tuple(sorted(f_catalog.keys())),
        trigger_param_bounds={},
        filter_param_bounds={},
        max_filters=1,
    )
    assert not hasattr(search_space, "rrr_range")
    assert not hasattr(search_space, "risk_percent_range")
    assert not hasattr(search_space, "position_ttl_bars_range")
    assert not hasattr(search_space, "atr_sl_mult_range")
