"""Tests for src/crypt/backtest/labels.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from crypt.backtest.labels import DROP_TAIL_TICKS, compute_labels

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_h4_ohlcv(n_bars: int, base_price: float = 100.0, step: float = 1.0) -> pd.DataFrame:
    """Build a synthetic H4 OHLCV DataFrame with n_bars rows.

    Each bar: open_time = 2025-01-01 00:00 + i * 4h.
    Close price increments by `step` each bar (monotone for easy hit-rate checks).
    """
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(n_bars):
        c = base_price + i * step
        rows.append(
            {
                "open_time": start + timedelta(hours=4 * i),
                "o": c - 0.1,
                "h": c + 0.5,
                "l": c - 0.5,
                "c": c,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def _make_verdicts(tick_times: list[datetime], decision: str = "BUY") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "TEST-USDT-SWAP",
                "tick_time": t,
                "decision": decision,
                "confidence": 80,
                "score": 0.5,
                "regime": "TRENDING",
                "rationale": "test",
            }
            for t in tick_times
        ]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compute_labels_basic() -> None:
    """Forward returns are computed correctly for simple monotone prices."""
    n = 50
    ohlcv = _make_h4_ohlcv(n, base_price=100.0, step=1.0)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    # tick_time corresponds to bar close time = open_time + 4h
    tick_times = [start + timedelta(hours=4 * (i + 1)) for i in range(10)]
    verdicts = _make_verdicts(tick_times)

    result = compute_labels(verdicts, ohlcv)
    assert not result.empty
    # Prices are monotone, so all forward returns should be positive (BUY → hits).
    assert (result["return_h4"] > 0).all()
    assert (result["return_h24"] > 0).all()
    assert (result["return_h96"] > 0).all()


def test_hit_rate_columns_buy() -> None:
    """hit_h* should be 1 for BUY when price goes up."""
    n = 50
    ohlcv = _make_h4_ohlcv(n, base_price=100.0, step=1.0)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    tick_times = [start + timedelta(hours=4 * (i + 1)) for i in range(5)]
    verdicts = _make_verdicts(tick_times, decision="BUY")

    result = compute_labels(verdicts, ohlcv)
    assert not result.empty
    assert all(float(h) == 1.0 for h in result["hit_h4"].dropna())
    assert all(float(h) == 1.0 for h in result["hit_h24"].dropna())


def test_hit_rate_columns_sell() -> None:
    """hit_h* should be 1 for SELL when price goes down."""
    n = 50
    ohlcv = _make_h4_ohlcv(n, base_price=200.0, step=-1.0)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    tick_times = [start + timedelta(hours=4 * (i + 1)) for i in range(5)]
    verdicts = _make_verdicts(tick_times, decision="SELL")

    result = compute_labels(verdicts, ohlcv)
    assert not result.empty
    assert all(float(h) == 1.0 for h in result["hit_h24"].dropna())


def test_hold_verdicts_get_nan_hit() -> None:
    """HOLD verdicts receive NaN for hit_* columns."""
    n = 50
    ohlcv = _make_h4_ohlcv(n)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    tick_times = [start + timedelta(hours=4 * (i + 1)) for i in range(5)]
    verdicts = _make_verdicts(tick_times, decision="HOLD")

    result = compute_labels(verdicts, ohlcv)
    assert not result.empty
    assert result["hit_h4"].isna().all()


def test_drop_tail_ticks() -> None:
    """When dataset > DROP_TAIL_TICKS, the last DROP_TAIL_TICKS rows are removed."""
    # Need enough OHLCV to cover all forward windows.
    # We use 100 bars; verdicts span ticks 1..50 (well inside the window).
    n_ohlcv = 150
    n_verdicts = DROP_TAIL_TICKS + 10  # more than the drop threshold
    ohlcv = _make_h4_ohlcv(n_ohlcv)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    tick_times = [start + timedelta(hours=4 * (i + 1)) for i in range(n_verdicts)]
    verdicts = _make_verdicts(tick_times)

    result = compute_labels(verdicts, ohlcv)
    # Should have at most n_verdicts - DROP_TAIL_TICKS valid labelled rows.
    assert len(result) <= n_verdicts - DROP_TAIL_TICKS


def test_incomplete_forward_window_dropped() -> None:
    """Verdicts near the end of the OHLCV window are dropped (no 96h data)."""
    n = 30
    ohlcv = _make_h4_ohlcv(n)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    # Last tick: bar close_time = open_time[29] + 4h — only 0 bars ahead.
    last_close_time = start + timedelta(hours=4 * 30)
    verdicts = _make_verdicts([last_close_time])

    result = compute_labels(verdicts, ohlcv)
    assert result.empty


def test_mae_mfe_direction() -> None:
    """For monotone-up prices, MAE <= 0 and MFE > 0."""
    n = 50
    ohlcv = _make_h4_ohlcv(n, step=1.0)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    tick_times = [start + timedelta(hours=4 * 5)]  # tick 5
    verdicts = _make_verdicts(tick_times)

    result = compute_labels(verdicts, ohlcv)
    assert not result.empty
    assert float(result["mfe"].iloc[0]) > 0
    # MAE = (min_low - entry) / entry — since prices go up, min_low = first bar low ≈ entry
    # so mae should be close to 0 or slightly negative.
    assert float(result["mae"].iloc[0]) <= 0.01


def test_empty_inputs() -> None:
    """Empty inputs return empty output without raising."""
    assert compute_labels(pd.DataFrame(), pd.DataFrame()).empty
    ohlcv = _make_h4_ohlcv(30)
    assert compute_labels(pd.DataFrame(), ohlcv).empty
