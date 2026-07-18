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

import backtester.strategy_discovery.catcma_qd as catcma_qd_module
import backtester.strategy_discovery.dss_stage1 as dss_stage1_module
import backtester.strategy_discovery.dss_v2 as dss_v2_module
import backtester.strategy_discovery.hyperband_qd as hyperband_qd_module
import backtester.strategy_discovery.island_qd as island_qd_module
import backtester.strategy_discovery.smac_qd as smac_qd_module
from backtester.__main__ import cli
from backtester.data_contracts import StrategyData
from backtester.strategies.dss_strategy import DSSStrategy
from backtester.strategy_discovery.catcma_qd import (
    _EvaluatedCandidate,
    _select_stage2_candidates,
    _Stage1Candidate,
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
from backtester.strategy_discovery.dss_objective import (
    DSSObjective,
    compute_mandate_score,
    run_dss_backtest,
)
from backtester.strategy_discovery.dss_report import _extract_pareto_front, _is_dominated
from backtester.strategy_discovery.dss_v2 import (
    BarrierMetrics,
    DSSV2Result,
    Stage1Result,
    _append_stage1,
    _guard_output_dir,
    _write_state,
    evaluate_stage1,
    export_stage4_candidates,
    run_dss_v2_search,
)
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import build_discovery_dataset
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


def _make_stage1_pass(candidate: DSSCandidate) -> Stage1Result:
    return Stage1Result(
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
        return lambda data: self._signals_by_primary_id[id(data.primary)]


class _CountingWindowAwareFakeComposer:
    def __init__(self, signals_by_primary_id: dict[int, pd.DataFrame]) -> None:
        self._signals_by_primary_id = signals_by_primary_id
        self.calls = 0

    def build(self, _config: TrialConfig) -> Callable[[StrategyData], pd.DataFrame]:
        def _generate(data: StrategyData) -> pd.DataFrame:
            self.calls += 1
            return self._signals_by_primary_id[id(data.primary)]

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
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
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
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=3)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 2)),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_stage1_uses_weekly_signal_frequency_gate(tmp_path: Path) -> None:
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
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 4)),
    )
    assert result.passed is False
    assert result.rejection_reason == "too_few_signals:w1"


def test_stage1_accepts_tp_first_barrier_signal(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=6,
        atr_sl_mult=1.0,
        generation=0,
    )
    result = evaluate_stage1(
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


def test_stage1_reject_does_not_promote(tmp_path: Path) -> None:
    primary = _make_primary(200)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=3)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 2)),
    )
    assert result.passed is False
    assert result.should_promote is False


def test_stage1_records_window_specialist_without_survivor_export(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=6,
        atr_sl_mult=1.0,
        generation=0,
    )
    result = evaluate_stage1(
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

    _append_stage1(tmp_path, candidate, result, windows)

    assert not (tmp_path / "stage1_survivors.jsonl").exists()
    assert not (tmp_path / "stage1_rejections.csv").exists()
    specialist_csv = (tmp_path / "stage1_specialists.csv").read_text(encoding="utf-8")
    assert "candidate_class" in specialist_csv.splitlines()[0]
    assert "specialist:w1" in specialist_csv


def test_stage1_default_path_still_rejects_early(tmp_path: Path) -> None:
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

    result = evaluate_stage1(
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


def test_stage1_counts_same_bar_tp_and_sl_as_sl_first(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=6,
        atr_sl_mult=1.0,
        generation=0,
    )
    result = evaluate_stage1(
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


def test_stage1_barrier_uses_next_open_entry_like_stage2(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=6,
        atr_sl_mult=1.0,
        generation=0,
    )
    result = evaluate_stage1(
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


def test_stage1_atr_scaled_label_ignores_rrr_ttl_and_signal_stop(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=1,
        atr_sl_mult=0.5,
        generation=0,
    )
    variant = DSSCandidate(
        candidate_id="variant",
        trigger_name="pt_nr4_breakout",
        trigger_params={"lookback": 4},
        filter_names=(),
        filter_params={},
        rrr=10.0,
        risk_percent=3.0,
        position_ttl_bars=100,
        atr_sl_mult=5.0,
        generation=0,
    )
    signals = _make_one_signal(primary)
    signals["stop_price"] = 1.0

    base_metrics = evaluate_stage1(
        base,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(signals),
    ).barrier_metrics["w1"]
    variant_metrics = evaluate_stage1(
        variant,
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(signals),
    ).barrier_metrics["w1"]

    assert base_metrics == variant_metrics
    assert base_metrics.tp_first == 1
    assert base_metrics.median_bars_to_tp == 2.0


def test_stage1_atr_scaled_label_expands_for_more_volatile_symbol(tmp_path: Path) -> None:
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
    result = evaluate_stage1(
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


def test_stage1_unresolved_tail_excluded_from_win_rate(tmp_path: Path) -> None:
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
    result = evaluate_stage1(
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


def test_stage1_rejects_barrier_win_rate_below_floor(tmp_path: Path) -> None:
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
        rrr=1.0,
        risk_percent=1.0,
        position_ttl_bars=6,
        atr_sl_mult=1.0,
        generation=0,
    )
    result = evaluate_stage1(
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


def test_stage1_min_wr_is_only_win_rate_gate(
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

    monkeypatch.setattr(dss_stage1_module, "_barrier_metrics", fake_barrier_metrics)
    result = evaluate_stage1(
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


def test_stage1_csv_header_includes_barrier_columns_after_early_reject(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10"),
        DSSWindowSpec(label="w2", symbol="TEST-USDT-SWAP", start="2024-02-01", end="2024-02-10"),
    ]
    candidate = _make_candidate("early_reject")
    result = Stage1Result(
        candidate_id=candidate.candidate_id,
        passed=False,
        rejection_reason="too_few_signals:w1",
        signal_counts={"w1": 0},
        long_ratios={},
        median_stop_atr={},
        barrier_metrics={},
        behavior=None,
    )
    _append_stage1(tmp_path, candidate, result, windows)
    header = (tmp_path / "stage1_viability.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "barrier_tp_first_rate_w1" in header
    assert "barrier_tp_first_rate_w2" in header
    assert len(header.split(",")) == len(
        (tmp_path / "stage1_viability.csv").read_text().splitlines()[1].split(",")
    )


def test_stage1_ranked_preserves_near_miss_rejections(tmp_path: Path) -> None:
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
    ]
    candidate = _make_candidate("near_miss")
    result = Stage1Result(
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
    _append_stage1(tmp_path, candidate, result, windows)

    ranked = dss_v2_module.write_stage1_ranked(
        tmp_path, DSSConfig(output=tmp_path, windows=windows)
    )

    assert ranked == []
    near_misses = (tmp_path / "stage1_near_misses.csv").read_text(encoding="utf-8")
    assert "near_miss" in near_misses
    assert "weak_barrier_win_rate:w1" in near_misses


def test_stage1_rejects_overtrading(tmp_path: Path) -> None:
    primary = _make_primary(120)
    windows = [
        DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-06")
    ]
    config = DSSConfig(output=tmp_path, windows=windows, min_trades_per_window=1)
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 51)),
    )
    assert result.passed is False
    assert result.rejection_reason == "overtrading:w1"


def test_stage1_allows_up_to_ten_signals_per_day(tmp_path: Path) -> None:
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
    result = evaluate_stage1(
        _make_candidate(),
        {"w1": _make_strategy_data(primary)},
        config,
        _FakeComposer(_make_signal_df(primary, 49)),
    )
    assert result.rejection_reason != "overtrading:w1"


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
        windows=[
            DSSWindowSpec(label="w1", symbol="TEST-USDT-SWAP", start="2024-01-01", end="2024-01-10")
        ],
        top_n_candidates=1,
    )
    paths = export_stage4_candidates(archive, config)
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    strategy = DSSStrategy(payload["params"])
    generated = strategy.generate(_make_strategy_data(_make_primary(300)))
    assert {"signal", "sl_price"}.issubset(generated.columns)


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


def test_catcma_weighted_model_updates_toward_elites() -> None:
    search_space = DSSSearchSpace(
        trigger_names=("pt_a", "pt_b"),
        filter_names=("pf_a", "pf_b"),
        trigger_param_bounds={"pt_a": {}, "pt_b": {}},
        filter_param_bounds={"pf_a": {}, "pf_b": {}},
        max_filters=2,
    )
    model = _WeightedModel(search_space, seed=123)
    elite = DSSCandidate(
        candidate_id="elite",
        trigger_name="pt_b",
        trigger_params={},
        filter_names=("pf_b",),
        filter_params={"pf_b": {}},
        rrr=2.0,
        risk_percent=1.5,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
        generation=0,
    )
    model.update([_EvaluatedCandidate(elite, robust_score=10.0, promoted_to_stage3=False)])
    sampled = [model.sample(f"c{i}", generation=1).trigger_name for i in range(100)]
    assert sampled.count("pt_b") > sampled.count("pt_a")


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
    assert ticks == [1, 1, 1, 1]
    assert result.generated == 4
    assert (tmp_path / "catcma_qd_state.csv").exists()


def test_catcma_qd_stage2_selection_caps_batch_cost() -> None:
    candidates = [
        _Stage1Candidate(
            candidate=(candidate := _make_candidate(f"c{i}", trigger_name=f"pt_{i % 12}")),
            result=Stage1Result(
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
    selected = _select_stage2_candidates(candidates, batch_size=48)
    assert len(selected) == 5
    assert len({item.result.behavior.cell_key for item in selected if item.result.behavior}) > 1


def test_catcma_qd_resume_continues_after_existing_stage0(tmp_path: Path) -> None:
    existing = _make_candidate("catcma_000001").to_dict()
    (tmp_path / "stage0_candidates.jsonl").write_text(
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
    run_catcma_qd_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
        progress_callback=ticks.append,
    )
    lines = (tmp_path / "stage0_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(line)["candidate_id"] for line in lines]
    assert ticks == [1, 1, 1]
    assert ids == ["catcma_000001", "catcma_000002", "catcma_000003"]


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
    assert ticks == [1, 1, 1, 1]
    assert result.generated == 4
    assert (tmp_path / "stage0_candidates.jsonl").exists()


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
    assert ticks == [1, 1, 1, 1]
    assert result.generated == 4
    assert (tmp_path / "hyperband_qd_state.csv").exists()


def test_hyperband_qd_rung_selection_caps_expensive_evaluations() -> None:
    items: list[_RungCandidate] = []
    for i in range(40):
        candidate = _make_candidate(f"c{i}", trigger_name=f"pt_{i % 16}")
        behavior = _make_behavior(candidate.trigger_name)
        stage1 = _Stage1Candidate(
            candidate=candidate,
            result=Stage1Result(
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
        items.append(_RungCandidate(stage1))

    selected = _select_rung_promotions(
        items,
        fraction=0.30,
        minimum=3,
        score_getter=lambda item: item.stage1.cheap_score,
    )
    assert len(selected) == 12
    selected_cells = {
        item.stage1.result.behavior.cell_key
        for item in selected
        if item.stage1.result.behavior is not None
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
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
        generation=0,
    )
    c2 = DSSCandidate(
        candidate_id="c2",
        trigger_name="pt_b",
        trigger_params={"threshold": 0.3},
        filter_names=("pf_b",),
        filter_params={"pf_b": {}},
        rrr=2.5,
        risk_percent=1.5,
        position_ttl_bars=48,
        atr_sl_mult=1.5,
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
    assert ticks == [1, 1, 1, 1]
    assert result.generated == 4
    assert (tmp_path / "smac_qd_state.csv").exists()
    assert (tmp_path / "smac_qd_observations.csv").exists()


def test_dss_stage1_mode_stops_before_backtest_and_exports_shortlist(
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
        stage_mode="stage1",
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
        trade_count_bucket="medium",
        hold_time_bucket="medium",
        risk_geometry="medium_sl",
        regime_strength="balanced",
        filter_depth="0",
    )

    def _fake_stage1(
        candidate: DSSCandidate,
        _window_data: dict[str, StrategyData],
        _config: DSSConfig,
        _composer: object | None = None,
    ) -> Stage1Result:
        return Stage1Result(
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

    def _stage2_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Stage 2 should not run in stage1 mode")

    monkeypatch.setattr(dss_v2_module, "evaluate_stage1", _fake_stage1)
    monkeypatch.setattr(dss_v2_module, "evaluate_stage_scores", _stage2_must_not_run)

    result = dss_v2_module.run_dss_v2_search(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
    )

    assert result.stage1_survivors == 1
    assert result.stage2_survivors == 0
    assert (tmp_path / "stage1_ranked.csv").exists()
    assert (tmp_path / "stage1_candidates").exists()
    assert not (tmp_path / "stage2_proxy.csv").exists()
    assert "Stage mode: **stage1**" in (tmp_path / "summary.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("module", "runner"),
    [
        (catcma_qd_module, run_catcma_qd_search),
        (island_qd_module, run_island_qd_search),
        (hyperband_qd_module, run_hyperband_qd_search),
        (smac_qd_module, run_smac_qd_search),
    ],
)
def test_stage1_mode_stops_all_backends_before_backtest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    runner: Callable[..., DSSV2Result],
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
        stage_mode="stage1",
    )
    search_space = DSSSearchSpace(
        trigger_names=("pt_nr4_breakout",),
        filter_names=(),
        trigger_param_bounds={"pt_nr4_breakout": {}},
        filter_param_bounds={},
        max_filters=0,
    )

    def _fake_stage1(
        candidate: DSSCandidate,
        _window_data: dict[str, StrategyData],
        _config: DSSConfig,
        _composer: object | None = None,
    ) -> Stage1Result:
        return _make_stage1_pass(candidate)

    def _stage2_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Stage 2 should not run in stage1 mode")

    monkeypatch.setattr(module, "evaluate_stage1", _fake_stage1)
    monkeypatch.setattr(module, "evaluate_stage_scores", _stage2_must_not_run)

    result = runner(
        config=config,
        search_space=search_space,
        window_data={"w1": _make_strategy_data(primary)},
    )

    assert result.stage1_survivors == 1
    assert result.stage2_survivors == 0
    assert (tmp_path / "stage1_ranked.csv").exists()
    assert (tmp_path / "stage1_candidates").exists()
    assert not (tmp_path / "stage2_proxy.csv").exists()
    assert "Stage mode: **stage1**" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_search_signals_help_no_longer_exposes_sampler() -> None:
    result = CliRunner().invoke(cli, ["search-signals", "--help"])
    assert result.exit_code == 0
    assert "--sampler" not in result.output
    assert "--algorithm" in result.output
    assert "island_qd" in result.output
    assert "hyperband_qd" in result.output
    assert "smac_qd" in result.output


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


def test_search_signals_matrix_help() -> None:
    result = CliRunner().invoke(cli, ["search-signals-matrix", "--help"])
    assert result.exit_code == 0
    assert "--n-jobs-per-algorithm" in result.output
    assert "--algorithms" in result.output


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
            "staged,nope",
        ],
    )
    assert result.exit_code != 0
    assert "unknown value" in result.output
    assert "nope" in result.output


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
        data=_make_strategy_data(primary),
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
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=24,
        atr_sl_mult=1.0,
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
        data=_make_strategy_data(primary),
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
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=24,
        atr_sl_mult=1.0,
    )

    composer = SignalComposer()
    assert composer.validate_config(config) == []
    signals = composer.build(config)(_make_strategy_data(primary))

    assert not signals.empty
    assert set(signals["side"]) <= {"long", "short"}


def test_pinescript_adx_di_filter_uses_side_alignment() -> None:
    primary = _make_primary(80)
    dataset = build_discovery_dataset(
        data=_make_strategy_data(primary),
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
        "w1": StrategyData(
            primary=primary_w1, candles={}, extras={}, metadata={"symbol": "TEST-USDT-SWAP"}
        ),
        "w2": StrategyData(
            primary=primary_w2, candles={}, extras={}, metadata={"symbol": "TEST-USDT-SWAP"}
        ),
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
