"""Tests for SignalComposer (Phase P2 acceptance criteria from spec).

Covers all 9 test cases listed in docs/discovery/signal_composer.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.dss_config import TrialConfig
from backtester.strategy_discovery.signal_composer import SignalComposer, signal_df_to_ohlcv_aligned

# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def _make_primary(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data with a DatetimeIndex."""
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


def _make_strategy_data(primary: pd.DataFrame, symbol: str = "SOL-USDT-SWAP") -> StrategyData:
    return StrategyData(primary=primary, candles={}, extras={}, metadata={"symbol": symbol})


def _minimal_config(
    trigger_name: str = "pt_nr4_breakout",
    filter_names: tuple[str, ...] = (),
) -> TrialConfig:
    return TrialConfig(
        trigger_name=trigger_name,
        trigger_params={"lookback": 4},
        filter_names=filter_names,
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
        atr_sl_mult=1.0,
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_build_returns_callable() -> None:
    """build(config) returns a callable."""
    composer = SignalComposer()
    config = _minimal_config()
    fn = composer.build(config)
    assert callable(fn)


def test_generate_empty_when_no_events() -> None:
    """Flat-price data should never fire NR4; result is an empty DataFrame."""
    primary = pd.DataFrame(
        {
            "open": [100.0] * 50,
            "high": [100.1] * 50,
            "low": [99.9] * 50,
            "close": [100.0] * 50,
            "volume": [1_000.0] * 50,
        },
        index=pd.date_range("2024-01-01", periods=50, freq="1h", tz="UTC"),
    )
    data = _make_strategy_data(primary)
    composer = SignalComposer()
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
    fn = composer.build(config)
    result = fn(data)
    assert result.empty


def test_generate_schema_matches() -> None:
    """Output columns match the SignalRow spec."""
    required = {"bar_time", "symbol", "side", "confidence", "rationale", "entry_price", "stop_price", "tp_price"}
    primary = _make_primary(300)
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config = _minimal_config("pt_candle_confirm")
    fn = composer.build(config)
    result = fn(data)
    if not result.empty:
        assert required.issubset(set(result.columns)), f"Missing columns: {required - set(result.columns)}"


def test_stop_tp_long_consistency() -> None:
    """All long signals: stop < entry < tp."""
    primary = _make_primary(500)
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config = _minimal_config("pt_candle_confirm")
    fn = composer.build(config)
    result = fn(data)
    longs = result[result["side"] == "long"]
    if not longs.empty:
        assert (longs["stop_price"] < longs["entry_price"]).all(), "stop >= entry for some longs"
        assert (longs["entry_price"] < longs["tp_price"]).all(), "entry >= tp for some longs"


def test_stop_tp_short_consistency() -> None:
    """All short signals: tp < entry < stop."""
    primary = _make_primary(500, seed=99)
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config = _minimal_config("pt_candle_confirm")
    fn = composer.build(config)
    result = fn(data)
    shorts = result[result["side"] == "short"]
    if not shorts.empty:
        assert (shorts["tp_price"] < shorts["entry_price"]).all(), "tp >= entry for some shorts"
        assert (shorts["entry_price"] < shorts["stop_price"]).all(), "entry >= stop for some shorts"


def test_unknown_trigger_raises() -> None:
    """ValueError raised immediately for bad trigger_name."""
    composer = SignalComposer()
    config = TrialConfig(
        trigger_name="nonexistent_trigger",
        trigger_params={},
        filter_names=(),
        filter_params={},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    with pytest.raises(ValueError, match="Unknown trigger_name"):
        composer.build(config)


def test_filter_drops_events() -> None:
    """A restrictive filter (short_only) drops longs, reducing output rows."""
    primary = _make_primary(400)
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config_no_filter = _minimal_config("pt_candle_confirm")
    config_short_only = TrialConfig(
        trigger_name="pt_candle_confirm",
        trigger_params={"body_ratio": 0.3},
        filter_names=("pf_side_short_only",),
        filter_params={"pf_side_short_only": {}},
        rrr=2.0,
        risk_percent=1.0,
        position_ttl_bars=36,
    )
    fn_full = composer.build(config_no_filter)
    fn_filtered = composer.build(config_short_only)
    result_full = fn_full(data)
    result_filtered = fn_filtered(data)
    assert len(result_filtered) <= len(result_full)
    if not result_filtered.empty:
        assert (result_filtered["side"] == "short").all()


def test_filter_ordering_deterministic() -> None:
    """Same config → same output on every call."""
    primary = _make_primary(300)
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config = _minimal_config("pt_candle_confirm")
    fn = composer.build(config)
    r1 = fn(data)
    r2 = fn(data)
    pd.testing.assert_frame_equal(r1.reset_index(drop=True), r2.reset_index(drop=True))


def test_atr_zero_discards_event() -> None:
    """Constant-close data (ATR→0) must produce no signals."""
    primary = pd.DataFrame(
        {
            "open": [100.0] * 100,
            "high": [100.0] * 100,
            "low": [100.0] * 100,
            "close": [100.0] * 100,
            "volume": [1_000.0] * 100,
        },
        index=pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC"),
    )
    data = _make_strategy_data(primary)
    composer = SignalComposer()
    config = _minimal_config("pt_candle_confirm")
    fn = composer.build(config)
    result = fn(data)
    assert result.empty


# ---------------------------------------------------------------------------
# signal_df_to_ohlcv_aligned helpers
# ---------------------------------------------------------------------------


def test_signal_df_to_ohlcv_aligned_long() -> None:
    """Long signal maps to signal=1 and correct sl_price."""
    primary = _make_primary(50)
    bar_time = primary.index[20]
    entry = float(primary.loc[bar_time, "close"])
    stop = entry - 1.0

    signal_df = pd.DataFrame(
        [{
            "bar_time": bar_time,
            "symbol": "SOL",
            "side": "long",
            "confidence": 75.0,
            "rationale": "test",
            "entry_price": entry,
            "stop_price": stop,
            "tp_price": entry + 2.0,
        }]
    )
    aligned = signal_df_to_ohlcv_aligned(signal_df, primary)
    assert list(aligned.columns[:4]) == ["open", "high", "low", "close"]
    assert aligned.loc[bar_time, "signal"] == 1
    assert abs(aligned.loc[bar_time, "sl_price"] - stop) < 1e-9


def test_signal_df_to_ohlcv_aligned_short() -> None:
    """Short signal maps to signal=-1."""
    primary = _make_primary(50)
    bar_time = primary.index[30]
    entry = float(primary.loc[bar_time, "close"])
    stop = entry + 1.0

    signal_df = pd.DataFrame(
        [{
            "bar_time": bar_time,
            "symbol": "SOL",
            "side": "short",
            "confidence": 75.0,
            "rationale": "test",
            "entry_price": entry,
            "stop_price": stop,
            "tp_price": entry - 2.0,
        }]
    )
    aligned = signal_df_to_ohlcv_aligned(signal_df, primary)
    assert aligned.loc[bar_time, "signal"] == -1


def test_signal_df_to_ohlcv_aligned_empty_returns_zeros() -> None:
    """Empty signal DataFrame → all-zero aligned frame."""
    primary = _make_primary(30)
    aligned = signal_df_to_ohlcv_aligned(pd.DataFrame(columns=["bar_time", "symbol", "side", "confidence", "rationale", "entry_price", "stop_price", "tp_price"]), primary)
    assert (aligned["signal"] == 0).all()
