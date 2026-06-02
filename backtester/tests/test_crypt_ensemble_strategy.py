from crypt.models import Regime, Signal, Verdict
from crypt.structure.smc import (
    BEARISH,
    BULLISH,
    SMCLiquiditySweep,
    SMCOrderBlock,
    SMCPivot,
    SMCState,
    SMCStructureEvent,
)
from datetime import timedelta

import pandas as pd
import pytest

from backtester.data_contracts import StrategyData
from backtester.registry import STRATEGIES
from backtester.strategies import crypt_ensemble as crypt_ensemble_mod
from backtester.strategies.crypt_ensemble import CryptEnsembleStrategy


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
    direction = (
        "bullish"
        if decision == "BUY"
        else "bearish"
        if decision == "SELL"
        else "neutral"
    )
    return Verdict(
        symbol="SOL-USDT-SWAP",
        decision=decision,
        confidence=(
            confidence if confidence is not None else 80 if decision != "HOLD" else 0
        ),
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
    verdicts = iter(
        [_verdict("BUY", 0.5), _verdict("SELL", -0.5), _verdict("HOLD", 0.0)]
    )
    strategy._evaluate_context = lambda _ctx: next(verdicts)  # type: ignore[method-assign]

    result = strategy.generate(data)

    expected_index = primary.index + pd.Timedelta(hours=4)
    assert list(result.index) == list(expected_index)
    assert list(result["signal"]) == [1, -1, 0]
    assert list(result["entry_price"]) == [10.5, 11.5, 12.5]
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
    strategy = CryptEnsembleStrategy(
        {"sl_atr_mult": 2.0, "min_confidence": 75, "progress": False}
    )
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
            assert name == "sl_atr_buffer_mult"
            assert low == 0.05
            assert high == 0.30
            return 0.15

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
        allow_atr_sl_fallback=False,
        state=state,
        tick_time=_ts(),
    )

    assert stop.signal == 0
    assert stop.anchor_type == "none"
    assert stop.sl_price == 100.0


def test_structural_sl_no_anchor_without_fallback_neutralizes_signal():
    stop = crypt_ensemble_mod._plan_structural_stop(
        signal=1,
        entry=100.0,
        atr=10.0,
        sl_atr_mult=2.0,
        sl_atr_buffer_mult=0.10,
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
        }
    )
    strategy._evaluate_context = lambda _ctx: _verdict("BUY", 0.5)  # type: ignore[method-assign]

    result = strategy.generate(data)

    assert list(result["signal"]) == [0]
    assert list(result["context_bias"]) == ["bearish"]
    assert list(result["trigger_type"]) == ["context_opposite"]
