from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from crypt.structure.smc import BEARISH, BULLISH, analyse_smc


def _candles(
    closes: list[float], highs: list[float] | None = None, lows: list[float] | None = None
) -> pd.DataFrame:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for i, close in enumerate(closes):
        high = highs[i] if highs is not None else close + 1.0
        low = lows[i] if lows is not None else close - 1.0
        rows.append(
            {
                "open_time": t0 + timedelta(hours=4 * i),
                "o": close,
                "h": high,
                "l": low,
                "c": close,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def test_pivot_is_not_known_before_confirmation() -> None:
    closes = [100, 101, 100, 99, 98, 97]
    highs = [101, 102, 110, 104, 103, 102]
    lows = [99, 100, 98, 97, 96, 95]
    df = _candles(closes, highs, lows)

    before_confirmation = df["open_time"].iloc[3] + timedelta(hours=4)
    after_confirmation = df["open_time"].iloc[4] + timedelta(hours=4)

    early = analyse_smc(df, tick_time=before_confirmation, internal_length=2, swing_length=50)
    late = analyse_smc(df, tick_time=after_confirmation, internal_length=2, swing_length=50)

    assert not [p for p in early.pivots if p.side == "high" and p.level == 110]
    assert [p for p in late.pivots if p.side == "high" and p.level == 110]


def test_bullish_bos_after_confirmed_pivot_break() -> None:
    closes = [100, 101, 100, 99, 100, 111]
    highs = [101, 102, 110, 104, 103, 112]
    lows = [99, 100, 98, 97, 98, 100]
    df = _candles(closes, highs, lows)

    state = analyse_smc(df, internal_length=2, swing_length=50)

    event = state.structure_events[-1]
    assert event.direction == BULLISH
    assert event.event_type == "BOS"
    assert event.level == 110
    assert state.internal_bias == BULLISH


def test_bearish_choch_after_bullish_bias() -> None:
    closes = [100, 101, 100, 99, 100, 111, 105, 104, 103, 94]
    highs = [101, 102, 110, 104, 103, 112, 106, 105, 104, 100]
    lows = [99, 100, 98, 97, 98, 100, 95, 99, 100, 90]
    df = _candles(closes, highs, lows)

    state = analyse_smc(df, internal_length=2, swing_length=50)

    bearish_events = [e for e in state.structure_events if e.direction == BEARISH]
    assert bearish_events
    assert bearish_events[-1].event_type == "CHOCH"
    assert state.internal_bias == BEARISH


def test_bullish_bos_creates_order_block_from_pivot_to_break_window() -> None:
    closes = [100, 101, 100, 99, 100, 106, 102]
    highs = [101, 102, 105, 101, 102, 107, 103]
    lows = [99, 100, 99, 98, 99, 103, 100]
    df = _candles(closes, highs, lows)

    state = analyse_smc(df, internal_length=2, swing_length=50)

    blocks = [ob for ob in state.order_blocks if ob.direction == BULLISH]
    assert blocks
    block = blocks[-1]
    assert block.low == 98
    assert block.high == 101
    assert block.active
    assert block.source_event.direction == BULLISH


def test_order_block_mitigation_marks_block_inactive() -> None:
    closes = [100, 101, 100, 99, 100, 106, 102, 101]
    highs = [101, 102, 105, 101, 102, 107, 103, 102]
    lows = [99, 100, 99, 98, 99, 103, 97, 100]
    df = _candles(closes, highs, lows)

    state = analyse_smc(df, internal_length=2, swing_length=50)

    block = [ob for ob in state.order_blocks if ob.direction == BULLISH][-1]
    assert not block.active
    assert block.mitigated_at == df["open_time"].iloc[6] + timedelta(hours=4)


def test_equal_high_detected_after_second_pivot_confirmation() -> None:
    closes = [100, 101, 104, 100, 99, 100, 104, 100, 99]
    highs = [101, 102, 110.0, 104, 103, 104, 110.1, 104, 103]
    lows = [99, 100, 98, 97, 96, 97, 98, 97, 96]
    df = _candles(closes, highs, lows)

    before_confirmation = df["open_time"].iloc[7] + timedelta(hours=4)
    after_confirmation = df["open_time"].iloc[8] + timedelta(hours=4)

    early = analyse_smc(df, tick_time=before_confirmation, internal_length=2, swing_length=50)
    late = analyse_smc(df, tick_time=after_confirmation, internal_length=2, swing_length=50)

    assert not early.liquidity_levels
    equal_highs = [level for level in late.liquidity_levels if level.level_type == "equal"]
    assert equal_highs
    assert equal_highs[-1].side == "high"
    assert equal_highs[-1].known_at == after_confirmation


def test_equal_high_sweep_known_after_sweep_candle_close() -> None:
    closes = [100, 101, 104, 100, 99, 100, 104, 100, 99, 108]
    highs = [101, 102, 110.0, 104, 103, 104, 110.1, 104, 103, 112]
    lows = [99, 100, 98, 97, 96, 97, 98, 97, 96, 106]
    df = _candles(closes, highs, lows)

    before_sweep_close = df["open_time"].iloc[9]
    after_sweep_close = df["open_time"].iloc[9] + timedelta(hours=4)

    early = analyse_smc(df, tick_time=before_sweep_close, internal_length=2, swing_length=50)
    late = analyse_smc(df, tick_time=after_sweep_close, internal_length=2, swing_length=50)

    assert not early.liquidity_sweeps
    sweep = late.liquidity_sweeps[-1]
    assert sweep.side == "high"
    assert sweep.level_type == "equal"
    assert sweep.known_at == after_sweep_close


def test_same_candle_high_low_sweep_is_marked_ambiguous() -> None:
    closes = [100, 101, 104, 100, 99, 100, 104, 100, 99, 100, 96, 100, 99, 100, 100]
    highs = [101, 102, 110.0, 104, 103, 104, 110.1, 104, 103, 104, 103, 104, 103, 104, 112]
    lows = [99, 100, 98, 97, 96.0, 97, 98, 97, 96.1, 97, 97, 97, 97, 97, 93]
    df = _candles(closes, highs, lows)

    state = analyse_smc(df, internal_length=2, swing_length=50)

    ambiguous = [sweep for sweep in state.liquidity_sweeps if sweep.ambiguous]
    assert ambiguous
    assert {sweep.side for sweep in ambiguous} == {"high", "low"}
