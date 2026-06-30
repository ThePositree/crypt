from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from backtester.data_contracts import StrategyData
from backtester.execution_context import attach_execution_context, execution_context_from_run_kwargs
from backtester.execution_sim import ExecutionSim
from backtester.registry import STRATEGIES
from backtester.strategies import crypt_ensemble as crypt_ensemble_mod
from backtester.strategies.crypt_ensemble import (
    CryptEnsembleStrategy,
    _apply_signal_filters,
    _DiscoveryBarFeatures,
    _SignalFilterConfig,
    _StopPlan,
)
from crypt.models import Regime, Signal, Timeframe, Verdict
from crypt.structure.smc import (
    BEARISH,
    BULLISH,
    SMCLiquiditySweep,
    SMCOrderBlock,
    SMCPivot,
    SMCState,
    SMCStructureEvent,
)

_PARITY_COLUMNS = [
    "signal",
    "sl_price",
    "entry_price",
    "confidence",
    "score",
    "regime",
    "decision",
    "rationale",
    "sl_anchor_type",
    "sl_anchor_level",
    "sl_anchor_known_at",
    "sl_distance_atr",
    "context_tf",
    "setup_tf",
    "trigger_tf",
    "context_bias",
    "setup_direction",
    "trigger_type",
    "trigger_known_at",
    "setup_snapshot_time",
    "sl_source_tf",
    "signal_filter_reason",
    "strength_derivatives",
    "strength_meanrev",
    "strength_smc_liquidity",
    "strength_smc_order_blocks",
    "strength_smc_structure",
    "strength_trend",
]


def _filter_stop(
    *,
    signal: int = 1,
    anchor_type: str = "pivot",
    anchor_known_at: datetime | None = None,
) -> _StopPlan:
    return _StopPlan(
        signal=signal,
        sl_price=99.0,
        anchor_type=anchor_type,  # type: ignore[arg-type]
        anchor_level=98.0,
        anchor_known_at=anchor_known_at,
        distance_atr=2.0,
    )


def _ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "volume": [10.0, 20.0, 30.0],
        },
        index=pd.to_datetime(
            [
                "2024-01-01 00:00:00",
                "2024-01-01 04:00:00",
                "2024-01-01 08:00:00",
            ],
            utc=True,
        ),
    )


def test_signal_filter_blocks_disallowed_side():
    stop = _filter_stop(signal=1)

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=frozenset({"short"}),
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="BUY",
    )

    assert filtered.signal == 0
    assert reason == "side_not_allowed:long"
    assert filtered.anchor_type == "pivot"


def test_signal_filter_blocks_configured_anchor_type():
    stop = _filter_stop(signal=-1, anchor_type="liquidity_sweep")

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset({"liquidity_sweep"}),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="SELL",
    )

    assert filtered.signal == 0
    assert reason == "sl_anchor_type_blocked:liquidity_sweep"


def test_signal_filter_blocks_unlisted_anchor_type():
    stop = _filter_stop(signal=-1, anchor_type="order_block")

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=frozenset({"pivot"}),
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="SELL",
    )

    assert filtered.signal == 0
    assert reason == "sl_anchor_type_not_allowed:order_block"


def test_signal_filter_blocks_stop_distance_outside_diagnostic_range():
    tight = _StopPlan(
        signal=-1,
        sl_price=101.0,
        anchor_type="pivot",
        anchor_level=100.5,
        anchor_known_at=None,
        distance_atr=1.5,
    )
    wide = _StopPlan(
        signal=-1,
        sl_price=105.0,
        anchor_type="pivot",
        anchor_level=104.0,
        anchor_known_at=None,
        distance_atr=3.25,
    )
    filters = _SignalFilterConfig(
        allowed_sides=None,
        allowed_sl_anchor_types=None,
        blocked_sl_anchor_types=frozenset(),
        max_anchor_age_hours=None,
        min_signal_sl_distance_atr=2.0,
        max_signal_sl_distance_atr=3.0,
        block_context_reversal=False,
    )

    filtered_tight, tight_reason = _apply_signal_filters(
        stop=tight,
        filters=filters,
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="SELL",
    )
    filtered_wide, wide_reason = _apply_signal_filters(
        stop=wide,
        filters=filters,
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="SELL",
    )

    assert filtered_tight.signal == 0
    assert tight_reason == "sl_distance_too_tight:1.5000"
    assert filtered_wide.signal == 0
    assert wide_reason == "sl_distance_too_wide:3.2500"


def test_signal_filter_blocks_stale_anchor():
    stop = _filter_stop(
        signal=-1,
        anchor_known_at=datetime(2025, 3, 6, tzinfo=UTC),
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=72.0,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="neutral",
        setup_direction="SELL",
    )

    assert filtered.signal == 0
    assert reason == "anchor_too_old:96.00h"


def test_signal_filter_blocks_context_reversal():
    stop = _filter_stop(signal=1)

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=True,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bearish",
        setup_direction="BUY",
    )

    assert filtered.signal == 0
    assert reason == "context_reversal:bearish:BUY"


def _ohlcv_at(times: list[str], closes: list[float] | None = None) -> pd.DataFrame:
    closes = closes or [12.5 for _ in times]
    opens = [close - 0.5 for close in closes]
    return pd.DataFrame(
        {
            "open": opens,
            "high": [close + 0.5 for close in closes],
            "low": [open_price - 0.5 for open_price in opens],
            "close": closes,
            "volume": [10.0 for _ in times],
        },
        index=pd.to_datetime(times, utc=True),
    )


def _verdict(decision: str, score: float, confidence: int | None = None) -> Verdict:
    direction = "bullish" if decision == "BUY" else "bearish" if decision == "SELL" else "neutral"
    return Verdict(
        symbol="SOL-USDT-SWAP",
        decision=decision,
        confidence=(confidence if confidence is not None else 80 if decision != "HOLD" else 0),
        score=score,
        regime=Regime.TRENDING,
        breakdown=[
            Signal(
                engine="trend",
                symbol="SOL-USDT-SWAP",
                direction=direction,
                strength=score,
                confidence=0.8,
                rationale=["test"],
                produced_at=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
            )
        ],
        rationale=f"test {decision}",
        produced_at=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
    )


def _ts(value: str = "2024-01-01 00:00:00"):
    return pd.Timestamp(value, tz="UTC").to_pydatetime()


def _pivot(side: str, level: float, known_at=None, kind: str = "internal") -> SMCPivot:
    return SMCPivot(
        kind=kind,  # type: ignore[arg-type]
        side=side,  # type: ignore[arg-type]
        level=level,
        pivot_time=_ts(),
        known_at=known_at or _ts(),
        index=1,
    )


def _event(direction: int, known_at=None) -> SMCStructureEvent:
    pivot_side = "high" if direction == BULLISH else "low"
    pivot = _pivot(pivot_side, 10.0, known_at=known_at)
    return SMCStructureEvent(
        kind="internal",
        event_type="BOS",
        direction=direction,
        level=pivot.level,
        event_time=_ts(),
        known_at=known_at or _ts(),
        pivot=pivot,
    )


def _order_block(direction: int, low: float, high: float, known_at=None) -> SMCOrderBlock:
    known = known_at or _ts()
    return SMCOrderBlock(
        kind="internal",
        direction=direction,
        low=low,
        high=high,
        origin_time=_ts(),
        known_at=known,
        source_event=_event(direction, known),
    )


def _sweep(side: str, level: float, known_at=None) -> SMCLiquiditySweep:
    known = known_at or _ts()
    return SMCLiquiditySweep(
        side=side,  # type: ignore[arg-type]
        level_type="swing",
        level=level,
        event_time=known,
        known_at=known,
        wick_distance_atr=1.0,
        level_known_at=known,
    )


def _state_with_protective_pivots() -> SMCState:
    return SMCState(
        pivots=[
            _pivot("low", 9.0),
            _pivot("high", 14.0),
        ]
    )


def _assert_strategy_parity(reference: pd.DataFrame, optimized: pd.DataFrame) -> None:
    assert list(reference.index) == list(optimized.index)
    missing = [
        col
        for col in _PARITY_COLUMNS
        if col not in reference.columns or col not in optimized.columns
    ]
    assert missing == []
    assert_frame_equal(
        reference.loc[:, _PARITY_COLUMNS],
        optimized.loc[:, _PARITY_COLUMNS],
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


@pytest.fixture(autouse=True)
def _structural_stop_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state",
        lambda _ctx: _state_with_protective_pivots(),
    )


def test_crypt_ensemble_registered():
    assert STRATEGIES["crypt_ensemble"] is CryptEnsembleStrategy


def test_crypt_ensemble_maps_verdicts_to_donor_signal_and_sl():
    primary = _ohlcv()
    data = StrategyData(
        primary=primary,
        candles={"H4": primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy({"sl_atr_mult": 2.0, "progress": False})
    verdicts = iter([_verdict("BUY", 0.5), _verdict("SELL", -0.5), _verdict("HOLD", 0.0)])
    strategy._evaluate_context = lambda _ctx: next(verdicts)  # type: ignore[method-assign]

    result = strategy.generate(data)

    expected_index = primary.index + pd.Timedelta(hours=4)
    assert list(result.index) == list(expected_index)
    assert list(result["signal"]) == [1, -1, 0]
    assert result["entry_price"].isna().all()
    assert list(result["sl_anchor_type"]) == ["pivot", "pivot", "none"]
    assert list(result["sl_price"]) == [8.8, 14.2, 12.5]
    assert list(result["confidence"]) == [80, 80, 0]
    assert list(result["decision"]) == ["BUY", "SELL", "HOLD"]


def test_crypt_ensemble_default_does_not_gate_entries_by_confidence():
    primary = _ohlcv()
    data = StrategyData(
        primary=primary,
        candles={"H4": primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy({"sl_atr_mult": 2.0, "progress": False})
    verdicts = iter(
        [
            _verdict("BUY", 0.5, confidence=10),
            _verdict("SELL", -0.5, confidence=20),
            _verdict("BUY", 0.5, confidence=30),
        ]
    )
    strategy._evaluate_context = lambda _ctx: next(verdicts)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1, -1, 1]
    assert list(result["confidence"]) == [10, 20, 30]


def test_crypt_ensemble_explicit_min_confidence_suppresses_entries():
    primary = _ohlcv()
    data = StrategyData(
        primary=primary,
        candles={"H4": primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy({"sl_atr_mult": 2.0, "min_confidence": 75, "progress": False})
    verdicts = iter(
        [
            _verdict("BUY", 0.5, confidence=74),
            _verdict("SELL", -0.5, confidence=75),
            _verdict("BUY", 0.5, confidence=80),
        ]
    )
    strategy._evaluate_context = lambda _ctx: next(verdicts)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [0, -1, 1]
    assert list(result["decision"]) == ["BUY", "SELL", "BUY"]
    assert list(result["confidence"]) == [74, 75, 80]


def test_crypt_ensemble_suggests_strategy_params_for_optuna():
    class Trial:
        def suggest_float(self, name: str, low: float, high: float) -> float:
            if name == "sl_atr_mult":
                assert low == 1.0
                assert high == 3.5
                return 2.5
            if name == "sl_atr_buffer_mult":
                assert low == 0.05
                assert high == 0.30
                return 0.15
            assert name == "max_sl_distance_atr"
            assert low == 2.0
            assert high == 8.0
            return 4.0

        def suggest_int(self, name: str, low: int, high: int, *, step: int) -> int:
            assert name == "min_confidence"
            assert low == 0
            assert high == 75
            assert step == 5
            return 35

    params = CryptEnsembleStrategy.suggest_params(None, Trial())  # type: ignore[arg-type]

    assert params == {
        "sl_atr_mult": 2.5,
        "sl_atr_buffer_mult": 0.15,
        "max_sl_distance_atr": 4.0,
        "min_confidence": 35,
    }


def test_structural_sl_uses_bullish_order_block_low_with_atr_buffer():
    state = SMCState(
        internal_bias=BULLISH,
        order_blocks=[_order_block(BULLISH, low=95.0, high=98.0)],
        liquidity_sweeps=[_sweep("low", 90.0)],
        pivots=[_pivot("low", 85.0)],
    )

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == 1
    assert stop.anchor_type == "order_block"
    assert stop.anchor_level == 95.0
    assert stop.sl_price == 94.0


def test_structural_sl_uses_bearish_order_block_high_with_atr_buffer():
    state = SMCState(
        internal_bias=BEARISH,
        order_blocks=[_order_block(BEARISH, low=102.0, high=105.0)],
        pivots=[_pivot("high", 115.0)],
    )

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=-1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == -1
    assert stop.anchor_type == "order_block"
    assert stop.anchor_level == 105.0
    assert stop.sl_price == 106.0


def test_structural_sl_uses_fresh_sweep_when_no_order_block_exists():
    state = SMCState(liquidity_sweeps=[_sweep("low", 96.0)], pivots=[_pivot("low", 90.0)])

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=5.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.20,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == 1
    assert stop.anchor_type == "liquidity_sweep"
    assert stop.sl_price == 95.0


def test_structural_sl_uses_pivot_fallback_for_short():
    state = SMCState(pivots=[_pivot("high", 103.0), _pivot("high", 112.0, kind="swing")])

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=-1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == -1
    assert stop.anchor_type == "pivot"
    assert stop.anchor_level == 112.0
    assert stop.sl_price == 113.0


def test_structural_sl_excessive_distance_neutralizes_signal():
    state = SMCState(order_blocks=[_order_block(BULLISH, low=90.0, high=91.0)])

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=1.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == 0
    assert stop.anchor_type == "none"
    assert stop.sl_price == 100.0


def test_structural_sl_respects_explicit_max_distance_cap():
    state = SMCState(order_blocks=[_order_block(BULLISH, low=96.0, high=97.0)])

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=1.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=4.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == 0
    assert stop.anchor_type == "none"
    assert "ATR guard" in str(stop.rationale_suffix)


def test_structural_sl_no_anchor_without_fallback_neutralizes_signal():
    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=SMCState(),
        tick_time=_ts(),
    )

    assert stop.signal == 0
    assert stop.anchor_type == "none"
    assert "no structural stop anchor" in str(stop.rationale_suffix)


def test_structural_sl_ignores_anchor_known_after_tick_time():
    tick_time = _ts()
    state = SMCState(
        order_blocks=[
            _order_block(BULLISH, low=95.0, high=98.0, known_at=tick_time + timedelta(hours=4))
        ],
        pivots=[_pivot("low", 90.0, known_at=tick_time)],
    )

    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
        max_sl_distance_atr=8.0,
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=tick_time,
    )

    assert stop.signal == 1
    assert stop.anchor_type == "pivot"
    assert stop.anchor_level == 90.0


def test_crypt_ensemble_missing_optional_frames_does_not_raise():
    primary = _ohlcv()
    data = StrategyData(
        primary=primary,
        candles={"H4": primary, "H1": pd.DataFrame(), "D1": pd.DataFrame()},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy({"sl_atr_mult": 2.0, "progress": False})

    result = strategy.generate(data)

    assert len(result) == len(primary)
    assert set(result["signal"]) == {0}
    assert "missing inputs: candles[H4]" in str(result["rationale"].iloc[-1])


def test_crypt_ensemble_accepts_open_time_named_index():
    primary = _ohlcv()
    primary.index.name = "open_time"
    data = StrategyData(
        primary=primary,
        candles={"H4": primary},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy({"sl_atr_mult": 2.0, "progress": False})

    result = strategy.generate(data)

    assert len(result) == len(primary)
    assert result.index.name == "tick_time"


def test_crypt_ensemble_h1_mode_uses_h1_execution_index_and_diagnostics():
    primary = _ohlcv_at(
        [
            "2024-01-02 01:00:00",
            "2024-01-02 02:00:00",
            "2024-01-02 03:00:00",
        ],
        closes=[10.5, 11.5, 12.5],
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00", "2024-01-02 00:00:00"])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[12.0])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result.index) == list(primary.index + pd.Timedelta(hours=1))
    assert list(result["signal"]) == [1, 1, 1]
    assert set(result["context_tf"]) == {"1d"}
    assert set(result["setup_tf"]) == {"4h"}
    assert set(result["trigger_tf"]) == {"1h"}
    assert set(result["trigger_type"]) == {"1h_candle_confirm"}
    assert set(result["sl_source_tf"]) == {"4h"}


def test_crypt_ensemble_h1_default_requires_structural_trigger(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[12.0])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, timeframe: (
            SMCState() if timeframe == Timeframe.H1 else _state_with_protective_pivots()
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [0]
    assert list(result["trigger_type"]) == ["trigger_rejected"]


def test_crypt_ensemble_h1_raw_candle_mode_uses_h1_candle_direction(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = pd.DataFrame(
        {
            "open": [10.0, 10.0],
            "high": [11.0, 11.0],
            "low": [9.0, 9.0],
            "close": [10.5, 9.5],
            "volume": [10.0, 10.0],
        },
        index=pd.to_datetime(
            ["2024-01-02 01:00:00", "2024-01-02 02:00:00"],
            utc=True,
        ),
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = pd.DataFrame(
        {
            "open": [10.0],
            "high": [10.5],
            "low": [8.5],
            "close": [9.0],
            "volume": [10.0],
        },
        index=pd.to_datetime(["2024-01-01 00:00:00"], utc=True),
    )
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, _timeframe: SMCState(
            pivots=[
                _pivot("low", 8.0),
                _pivot("high", 12.0),
            ]
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "setup_source": "h1_raw",
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("HOLD", 0.0)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1, -1]
    assert list(result["setup_direction"]) == ["BUY", "SELL"]
    assert list(result["trigger_type"]) == [
        "raw_1h_candle_confirm",
        "raw_1h_candle_confirm",
    ]
    assert list(result["context_bias"]) == ["bearish", "bearish"]


def test_discovery_filter_blocks_d1_h4_context_reversal() -> None:
    stop = _filter_stop(signal=-1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=None,
        volume_median20=None,
        d1_context="long",
        h4_context="short",
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            block_d1_h4_context_reversal=True,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bullish",
        setup_direction="SELL",
        discovery=discovery,
    )

    assert filtered.signal == 0
    assert reason == "d1_h4_context_reversal:long:short"


def test_discovery_filter_allows_incomplete_d1_h4_context() -> None:
    stop = _filter_stop(signal=-1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=None,
        volume_median20=None,
        d1_context="missing",
        h4_context="short",
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            block_d1_h4_context_reversal=True,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bullish",
        setup_direction="SELL",
        discovery=discovery,
    )

    assert filtered.signal == -1
    assert reason is None


def test_discovery_filter_blocks_low_trend_strength() -> None:
    stop = _filter_stop(signal=-1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=0.2,
        volume=None,
        volume_median20=None,
        d1_context="short",
        h4_context="short",
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            min_trend_strength_atr=0.5,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bearish",
        setup_direction="SELL",
        discovery=discovery,
    )

    assert filtered.signal == 0
    assert reason == "trend_strength_low:0.2000"


def test_discovery_filter_blocks_low_volume() -> None:
    stop = _filter_stop(signal=-1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=10.0,
        volume_median20=100.0,
        d1_context="short",
        h4_context="short",
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            min_volume_median_ratio=0.5,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bearish",
        setup_direction="SELL",
        discovery=discovery,
    )

    assert filtered.signal == 0
    assert reason == "low_volume"


def test_crypt_ensemble_h1_raw_momentum_burst_fires_on_short_burst(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closes = [100.0 + index * 0.05 for index in range(24)]
    closes.append(99.0)
    opens = closes[:-1] + [100.2]
    highs = [max(open_, close) + 0.1 for open_, close in zip(opens, closes, strict=True)]
    lows = [min(open_, close) - 0.1 for open_, close in zip(opens, closes, strict=True)]
    index = pd.date_range("2024-01-02 00:00:00", periods=25, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * 25,
        },
        index=index,
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[100.0])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[100.0])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "setup_source": "h1_raw",
            "allow_atr_sl_fallback": True,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_momentum_burst"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("HOLD", 0.0)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert result["trigger_type"].iloc[-1] == "raw_h1_momentum_burst"
    assert result["signal"].iloc[-1] == -1
    assert result["setup_direction"].iloc[-1] == "SELL"


def test_crypt_ensemble_h1_raw_nr7_breakout_fires_on_bullish_nr7(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warmup_opens = [100.0 + index * 0.05 for index in range(18)]
    warmup_closes = [open_ + 0.05 for open_ in warmup_opens]
    warmup_highs = [close + 1.0 for close in warmup_closes]
    warmup_lows = [open_ - 1.0 for open_ in warmup_opens]
    tail_opens = [106.0, 106.0, 106.0, 106.0, 106.0, 106.0, 105.2]
    tail_closes = [106.5, 106.5, 106.5, 106.5, 106.5, 106.5, 105.7]
    tail_highs = [107.0, 107.0, 107.0, 107.0, 107.0, 107.0, 105.8]
    tail_lows = [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0]
    opens = warmup_opens + tail_opens
    closes = warmup_closes + tail_closes
    highs = warmup_highs + tail_highs
    lows = warmup_lows + tail_lows
    index = pd.date_range("2024-01-02 00:00:00", periods=25, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * 25,
        },
        index=index,
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[100.0])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[100.0])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "setup_source": "h1_raw",
            "allow_atr_sl_fallback": True,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_nr7_breakout"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("HOLD", 0.0)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert result["trigger_type"].iloc[-1] == "raw_h1_nr7_breakout"
    assert result["setup_direction"].iloc[-1] == "BUY"


def test_crypt_ensemble_tp_pct_execution_context_skips_structural_entry_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warmup_opens = [100.0 + index * 0.05 for index in range(18)]
    warmup_closes = [open_ + 0.05 for open_ in warmup_opens]
    warmup_highs = [close + 1.0 for close in warmup_closes]
    warmup_lows = [open_ - 1.0 for open_ in warmup_opens]
    tail_opens = [106.0, 106.0, 106.0, 106.0, 106.0, 106.0, 105.2]
    tail_closes = [106.5, 106.5, 106.5, 106.5, 106.5, 106.5, 105.7]
    tail_highs = [107.0, 107.0, 107.0, 107.0, 107.0, 107.0, 105.8]
    tail_lows = [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0]
    opens = warmup_opens + tail_opens
    closes = warmup_closes + tail_closes
    highs = warmup_highs + tail_highs
    lows = warmup_lows + tail_lows
    index = pd.date_range("2024-01-02 00:00:00", periods=25, freq="1h", tz="UTC")
    primary = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * 25,
        },
        index=index,
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[100.0])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[100.0])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "setup_source": "h1_raw",
            "allow_atr_sl_fallback": False,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_nr7_breakout"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("HOLD", 0.0)  # type: ignore[method-assign]
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state",
        lambda _ctx: SMCState(),
    )

    sl_rrr_result = strategy.generate(data)
    tp_pct_data = attach_execution_context(
        data,
        execution_context_from_run_kwargs(exit_geometry="tp_pct", tp_move_pct=0.008),
    )
    tp_pct_result = strategy.generate(tp_pct_data)

    assert sl_rrr_result["signal"].iloc[-1] == 0
    assert tp_pct_result["signal"].iloc[-1] == 1
    assert tp_pct_result["sl_anchor_type"].iloc[-1] == "none"
    assert "structural entry gate skipped" in str(tp_pct_result["rationale"].iloc[-1])


def test_discovery_filter_blocks_h4_context_misaligned() -> None:
    stop = _filter_stop(signal=-1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=None,
        volume_median20=None,
        d1_context="short",
        h4_context="long",
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            require_h4_context_aligned=True,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bearish",
        setup_direction="SELL",
        discovery=discovery,
    )

    assert filtered.signal == 0
    assert reason == "h4_context_misaligned:long"


def test_discovery_filter_blocks_bb_not_squeezed() -> None:
    stop = _filter_stop(signal=1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=None,
        volume_median20=None,
        d1_context="long",
        h4_context="long",
        bb_width_pct=0.06,
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            max_bb_width_pct=0.04,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bullish",
        setup_direction="BUY",
        discovery=discovery,
    )

    assert filtered.signal == 0
    assert reason == "bb_not_squeezed:0.0600"


def test_discovery_filter_session_off_hours_accepts_numpy_hour_utc() -> None:
    stop = _filter_stop(signal=1)
    discovery = _DiscoveryBarFeatures(
        trend_strength_atr=None,
        volume=200.0,
        volume_median20=100.0,
        d1_context="long",
        h4_context="long",
        hour_utc=np.int64(3),
        bb_width_rank_20=0.5,
    )

    filtered, reason = _apply_signal_filters(
        stop=stop,
        filters=_SignalFilterConfig(
            allowed_sides=None,
            allowed_sl_anchor_types=None,
            blocked_sl_anchor_types=frozenset(),
            max_anchor_age_hours=None,
            min_signal_sl_distance_atr=None,
            max_signal_sl_distance_atr=None,
            block_context_reversal=False,
            require_session_off_hours=True,
            min_volume_median_ratio=0.5,
            min_bb_width_rank_20=0.2,
        ),
        trigger_known_at=datetime(2025, 3, 10, tzinfo=UTC),
        context_bias="bullish",
        setup_direction="BUY",
        discovery=discovery,
    )

    assert filtered.signal == 1
    assert reason is None


def test_crypt_ensemble_h1_raw_mode_rejects_doji_without_setup_gate(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = pd.DataFrame(
        {
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.0],
            "volume": [10.0],
        },
        index=pd.to_datetime(["2024-01-02 01:00:00"], utc=True),
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, _timeframe: _state_with_protective_pivots(),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": pd.DataFrame()},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "setup_source": "h1_raw",
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [0]
    assert list(result["trigger_type"]) == ["raw_h1_trigger_rejected"]


@pytest.mark.parametrize(
    ("rule", "state", "expected_trigger_type"),
    [
        (
            "h1_structure_break",
            SMCState(structure_events=[_event(BULLISH, known_at=_ts("2024-01-02 02:00:00"))]),
            "h1_structure_break",
        ),
        (
            "h1_sweep_reversal",
            SMCState(liquidity_sweeps=[_sweep("low", 9.5, known_at=_ts("2024-01-02 02:00:00"))]),
            "h1_sweep_reversal",
        ),
        (
            "h1_order_block_retest",
            SMCState(
                order_blocks=[
                    _order_block(
                        BULLISH,
                        low=9.0,
                        high=10.25,
                        known_at=_ts("2024-01-02 02:00:00"),
                    )
                ]
            ),
            "h1_order_block_retest",
        ),
    ],
)
def test_crypt_ensemble_h1_structural_trigger_rules_emit_auditable_type(
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
    state: SMCState,
    expected_trigger_type: str,
):
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[12.0])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, timeframe: (
            state if timeframe == Timeframe.H1 else _state_with_protective_pivots()
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": [rule],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1]
    assert list(result["trigger_type"]) == [expected_trigger_type]


def test_context_window_cache_matches_reference_builder():
    primary = _ohlcv_at(
        [
            "2024-01-02 01:00:00",
            "2024-01-02 02:00:00",
            "2024-01-02 03:00:00",
        ]
    )
    h4 = _ohlcv_at(
        [
            "2024-01-01 20:00:00",
            "2024-01-02 00:00:00",
            "2024-01-02 04:00:00",
        ]
    )
    d1 = _ohlcv_at(["2024-01-01 00:00:00", "2024-01-02 00:00:00"])
    extras = {
        "oi": pd.DataFrame(
            {
                "ts": pd.to_datetime(
                    [
                        "2024-01-02 01:00:00",
                        "2024-01-02 02:00:00",
                        "2024-01-02 03:00:00",
                    ],
                    utc=True,
                ),
                "oi": [100.0, 101.0, 102.0],
            }
        ),
        "ls_ratio": pd.DataFrame(
            {
                "ts": pd.to_datetime(["2024-01-02 01:00:00", "2024-01-02 03:00:00"], utc=True),
                "long_ratio": [0.51, 0.52],
                "short_ratio": [0.49, 0.48],
            }
        ),
        "taker_volume": pd.DataFrame(
            {
                "ts": pd.to_datetime(["2024-01-02 02:00:00"], utc=True),
                "buy_vol": [10.0],
                "sell_vol": [8.0],
            }
        ),
    }
    candles = {
        Timeframe.H1: crypt_ensemble_mod._to_crypt_candles(primary),
        Timeframe.H4: crypt_ensemble_mod._to_crypt_candles(h4),
        Timeframe.D1: crypt_ensemble_mod._to_crypt_candles(d1),
    }
    tick_time = pd.Timestamp("2024-01-02 05:00:00", tz="UTC").to_pydatetime()

    reference = crypt_ensemble_mod._build_context(
        symbol="SOL-USDT-SWAP",
        tick_time=tick_time,
        candles=candles,
        extras=extras,
    )
    optimized = crypt_ensemble_mod._ContextWindowCache(
        candles=candles, extras=extras
    ).build_context(symbol="SOL-USDT-SWAP", tick_time=tick_time)

    assert {timeframe: len(frame) for timeframe, frame in reference.candles.items()} == {
        timeframe: len(frame) for timeframe, frame in optimized.candles.items()
    }
    assert len(reference.candles[Timeframe.H1]) == 3
    assert len(reference.candles[Timeframe.H4]) == 2
    assert len(reference.candles[Timeframe.D1]) == 1
    assert [item.oi for item in reference.oi or []] == [item.oi for item in optimized.oi or []]
    assert [item.long_ratio for item in reference.ls_ratio or []] == [
        item.long_ratio for item in optimized.ls_ratio or []
    ]
    assert [item.buy_vol for item in reference.taker_volume or []] == [
        item.buy_vol for item in optimized.taker_volume or []
    ]


def test_crypt_ensemble_optimized_windows_match_reference_h1_output(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0, 13.0],
            "high": [11.0, 11.5, 12.5, 14.0],
            "low": [9.5, 10.0, 11.0, 12.0],
            "close": [10.5, 10.5, 12.0, 13.5],
            "volume": [10.0, 20.0, 30.0, 40.0],
        },
        index=pd.to_datetime(
            [
                "2024-01-02 01:00:00",
                "2024-01-02 02:00:00",
                "2024-01-02 03:00:00",
                "2024-01-02 04:00:00",
            ],
            utc=True,
        ),
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00", "2024-01-02 00:00:00"])
    d1 = pd.DataFrame(
        {
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.0],
            "volume": [10.0],
        },
        index=pd.to_datetime(["2024-01-01 00:00:00"], utc=True),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    params = {
        "sl_atr_mult": 2.0,
        "progress": False,
        "optimized_setup_snapshots": False,
        "timeframes": {
            "context": ["1d"],
            "setup": ["4h"],
            "trigger": "1h",
            "execution": "1h",
        },
        "trigger_rules": ["h1_candle_confirm"],
    }

    def evaluate(ctx):
        hour = pd.Timestamp(ctx.tick_time).hour
        if hour == 2:
            return _verdict("BUY", 0.5)
        if hour == 3:
            return _verdict("SELL", -0.5)
        if hour == 4:
            return _verdict("HOLD", 0.0)
        return _verdict("BUY", 0.4)

    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, _timeframe: SMCState(),
    )
    reference_strategy = CryptEnsembleStrategy({**params, "optimized_windows": False})
    optimized_strategy = CryptEnsembleStrategy({**params, "optimized_windows": True})
    reference_strategy._evaluate_context = evaluate  # type: ignore[method-assign]
    optimized_strategy._evaluate_context = evaluate  # type: ignore[method-assign]

    reference = reference_strategy.generate(data)
    optimized = optimized_strategy.generate(data)

    _assert_strategy_parity(reference, optimized)


def test_crypt_ensemble_h1_setup_snapshot_reuses_h4_verdict_until_next_h4_close(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0, 9.0, 9.0],
            "close": [10.5, 9.5, 10.5, 10.5, 9.5],
            "volume": [10.0, 10.0, 10.0, 10.0, 10.0],
        },
        index=pd.to_datetime(
            [
                "2024-01-02 04:00:00",
                "2024-01-02 05:00:00",
                "2024-01-02 06:00:00",
                "2024-01-02 07:00:00",
                "2024-01-02 08:00:00",
            ],
            utc=True,
        ),
    )
    h4 = _ohlcv_at(
        [
            "2024-01-01 20:00:00",
            "2024-01-02 00:00:00",
            "2024-01-02 04:00:00",
        ]
    )
    d1 = _ohlcv_at(["2024-01-01 00:00:00"])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, _timeframe: SMCState(pivots=[_pivot("low", 9.0)]),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    setup_times: list[pd.Timestamp] = []

    def evaluate(ctx):
        setup_times.append(pd.Timestamp(ctx.tick_time))
        return _verdict("BUY", 0.5)

    strategy._evaluate_context = evaluate  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert setup_times == [
        pd.Timestamp("2024-01-02 04:00:00", tz="UTC"),
        pd.Timestamp("2024-01-02 08:00:00", tz="UTC"),
    ]
    assert list(result["trigger_type"]) == [
        "1h_candle_confirm",
        "trigger_rejected",
        "1h_candle_confirm",
        "1h_candle_confirm",
        "trigger_rejected",
    ]
    assert list(result["setup_snapshot_time"]) == [
        "2024-01-02T04:00:00+00:00",
        "2024-01-02T04:00:00+00:00",
        "2024-01-02T04:00:00+00:00",
        "2024-01-02T08:00:00+00:00",
        "2024-01-02T08:00:00+00:00",
    ]


def test_crypt_ensemble_h1_mode_uses_closer_h1_structural_stop(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[12.0])
    h1_state = SMCState(pivots=[_pivot("low", 10.0)])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, timeframe: (
            h1_state if timeframe == crypt_ensemble_mod.Timeframe.H1 else SMCState()
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1]
    assert list(result["sl_source_tf"]) == ["1h"]
    assert list(result["sl_anchor_type"]) == ["pivot"]
    assert list(result["sl_anchor_level"]) == [10.0]


def test_crypt_ensemble_h1_mode_keeps_h4_stop_when_h1_is_wider(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[12.0])
    h1_state = SMCState(pivots=[_pivot("low", 8.5)])
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state_for_timeframe",
        lambda _ctx, timeframe: (
            h1_state if timeframe == crypt_ensemble_mod.Timeframe.H1 else SMCState()
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1]
    assert list(result["sl_source_tf"]) == ["4h"]
    assert list(result["sl_anchor_type"]) == ["pivot"]
    assert list(result["sl_anchor_level"]) == [9.0]


def test_crypt_ensemble_h1_mode_excludes_forming_h4_candle():
    primary = _ohlcv_at(["2024-01-02 05:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-02 00:00:00", "2024-01-02 04:00:00"])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": pd.DataFrame()},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    h4_lengths: list[int] = []

    def evaluate(ctx):
        h4_frame = ctx.candles.get(crypt_ensemble_mod.Timeframe.H4)
        h4_lengths.append(0 if h4_frame is None else len(h4_frame))
        return _verdict("BUY", 0.5)

    strategy._evaluate_context = evaluate  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert h4_lengths == [1]
    assert list(result["signal"]) == [1]


def test_crypt_ensemble_h1_mode_excludes_forming_d1_candle():
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = pd.DataFrame(
        {
            "open": [10.0, 10.0],
            "high": [10.5, 13.0],
            "low": [8.5, 9.5],
            "close": [9.0, 12.5],
            "volume": [10.0, 10.0],
        },
        index=pd.to_datetime(
            ["2024-01-01 00:00:00", "2024-01-02 00:00:00"],
            utc=True,
        ),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    d1_lengths: list[int] = []

    def evaluate(ctx):
        d1_frame = ctx.candles.get(crypt_ensemble_mod.Timeframe.D1)
        d1_lengths.append(0 if d1_frame is None else len(d1_frame))
        return _verdict("BUY", 0.5)

    strategy._evaluate_context = evaluate  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert d1_lengths == [1]
    assert list(result["signal"]) == [0]
    assert list(result["context_bias"]) == ["bearish"]
    assert list(result["trigger_type"]) == ["context_opposite"]


def test_crypt_ensemble_h1_mode_blocks_opposite_d1_context():
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[10.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[10.5])
    d1 = pd.DataFrame(
        {
            "open": [10.0],
            "high": [10.5],
            "low": [8.5],
            "close": [9.0],
            "volume": [10.0],
        },
        index=pd.to_datetime(["2024-01-01 00:00:00"], utc=True),
    )
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [0]
    assert list(result["context_bias"]) == ["bearish"]
    assert list(result["trigger_type"]) == ["context_opposite"]


def test_crypt_ensemble_h1_mode_ignores_future_known_h4_stop_anchor(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = _ohlcv_at(["2024-01-02 01:00:00"], closes=[100.5])
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[100.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[101.0])
    tick_time = pd.Timestamp("2024-01-02 02:00:00", tz="UTC").to_pydatetime()
    state = SMCState(
        order_blocks=[
            _order_block(
                BULLISH,
                low=95.0,
                high=98.0,
                known_at=tick_time + timedelta(hours=1),
            )
        ],
        pivots=[_pivot("low", 90.0, known_at=tick_time)],
    )
    monkeypatch.setattr(crypt_ensemble_mod, "_structural_stop_state", lambda _ctx: state)
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [1]
    assert list(result["sl_anchor_type"]) == ["pivot"]
    assert list(result["sl_anchor_level"]) == [90.0]
    assert result["sl_anchor_known_at"].iloc[0] == tick_time.isoformat()


def test_crypt_ensemble_h1_signal_enters_next_h1_open_through_execution_sim(
    monkeypatch: pytest.MonkeyPatch,
):
    primary = _ohlcv_at(
        [
            "2024-01-02 01:00:00",
            "2024-01-02 02:00:00",
            "2024-01-02 03:00:00",
        ],
        closes=[100.5, 102.5, 103.5],
    )
    h4 = _ohlcv_at(["2024-01-01 20:00:00"], closes=[100.5])
    d1 = _ohlcv_at(["2024-01-01 00:00:00"], closes=[101.0])
    data = StrategyData(
        primary=primary,
        candles={"H1": primary, "H4": h4, "D1": d1},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    tick_time = pd.Timestamp("2024-01-02 02:00:00", tz="UTC").to_pydatetime()
    monkeypatch.setattr(
        crypt_ensemble_mod,
        "_structural_stop_state",
        lambda _ctx: SMCState(pivots=[_pivot("low", 99.0, known_at=tick_time)]),
    )
    strategy = CryptEnsembleStrategy(
        {
            "sl_atr_mult": 2.0,
            "progress": False,
            "timeframes": {
                "context": ["1d"],
                "setup": ["4h"],
                "trigger": "1h",
                "execution": "1h",
            },
            "trigger_rules": ["h1_candle_confirm"],
        }
    )
    verdicts = iter([_verdict("BUY", 0.5), _verdict("HOLD", 0.0), _verdict("HOLD", 0.0)])
    strategy._evaluate_context = lambda _ctx: next(verdicts)  # type: ignore[method-assign]

    signals = strategy.generate(data)
    trades = ExecutionSim(
        initial_capital=1000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
        min_net_exposure=0.0,
        position_ttl_bars=1,
    ).run(signals)

    assert list(signals.index) == list(primary.index + pd.Timedelta(hours=1))
    assert signals["entry_price"].isna().all()
    # The mocked BUY context remains actionable on later H1 rows. This test
    # verifies the first signal's next-open timing, not total re-entry count.
    assert not trades.empty
    assert trades.iloc[0]["signal_time"] == signals.index[0]
    assert trades.iloc[0]["entry_time"] == signals.index[1]
    assert trades.iloc[0]["entry_price"] == primary["open"].iloc[1]
