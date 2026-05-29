"""
Look-ahead guard regression test.

Contract (docs/backtest.md §5.1):
    At tick_time = T, no engine may access any datum with
    open_time >= T (candles) or ts >= T (funding/OI/LS-ratio/taker-vol).

This test deliberately injects a future candle and verifies:
1. ReplayParquetStore filters it out (guard works).
2. The naive ContextBuilder (no guard) would return it (proof that without
   the guard there IS a leak — so the test would catch a real regression).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from crypt.backtest.replay import ReplayContextBuilder, ReplayParquetStore
from crypt.data.context import ContextBuilder
from crypt.data.store import ParquetStore
from crypt.models import Candle, FundingSnapshot, OISnapshot, Timeframe

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_candle(symbol: str, open_time: datetime, close: float = 100.0) -> Candle:
    return Candle(
        symbol=symbol,
        timeframe=Timeframe.H4,
        open_time=open_time,
        o=Decimal(str(close)),
        h=Decimal(str(close + 1)),
        low=Decimal(str(close - 1)),
        c=Decimal(str(close)),
        volume=Decimal("1000"),
        closed=True,
    )


def _make_funding(symbol: str, ts: datetime, rate: float = 0.0001) -> FundingSnapshot:
    return FundingSnapshot(symbol=symbol, ts=ts, rate=Decimal(str(rate)))


def _make_oi(symbol: str, ts: datetime, oi: float = 1_000_000.0) -> OISnapshot:
    return OISnapshot(symbol=symbol, ts=ts, oi=Decimal(str(oi)))


# ─── Fixtures ───────────────────────────────────────────────────────────────

SYMBOL = "SOL-USDT-SWAP"
TICK_TIME = datetime(2025, 6, 1, 8, 0, 0, tzinfo=UTC)
PAST_TIME = TICK_TIME - timedelta(hours=4)
FUTURE_TIME = TICK_TIME  # open_time == tick_time is the boundary; must be excluded


@pytest.fixture
def store_with_future_bar(tmp_path: Path) -> ParquetStore:
    """Store containing both a past candle and a candle exactly at tick_time."""
    store = ParquetStore(tmp_path)
    # Past candle — should be visible.
    store.save_candles([_make_candle(SYMBOL, PAST_TIME, close=100.0)])
    # Future candle — open_time == TICK_TIME, must NOT be visible at tick_time.
    store.save_candles([_make_candle(SYMBOL, FUTURE_TIME, close=999.0)])
    # Funding: one past, one at boundary.
    store.save_funding([
        _make_funding(SYMBOL, PAST_TIME - timedelta(hours=8), 0.0001),
        _make_funding(SYMBOL, TICK_TIME, 0.9999),  # must be filtered
    ])
    # OI: one past, one at boundary.
    store.save_oi([
        _make_oi(SYMBOL, PAST_TIME - timedelta(hours=1), 1_000_000),
        _make_oi(SYMBOL, TICK_TIME, 9_999_999),  # must be filtered
    ])
    return store


# ─── Tests ──────────────────────────────────────────────────────────────────


class TestReplayParquetStoreGuard:
    """ReplayParquetStore must never expose data at or after tick_time."""

    def test_candles_future_bar_excluded(self, store_with_future_bar: ParquetStore) -> None:
        rs = ReplayParquetStore(store_with_future_bar)
        df = rs.load_candles(SYMBOL, Timeframe.H4, TICK_TIME)
        assert not df.empty, "past candle must be present"
        close_values = set(df["c"].tolist())
        assert 999.0 not in close_values, "future candle (close=999) leaked through guard"
        assert 100.0 in close_values, "past candle (close=100) must be present"

    def test_candles_past_bar_included(self, store_with_future_bar: ParquetStore) -> None:
        rs = ReplayParquetStore(store_with_future_bar)
        df = rs.load_candles(SYMBOL, Timeframe.H4, TICK_TIME)
        # All returned rows must have open_time < TICK_TIME.
        assert (df["open_time"] < pd.Timestamp(TICK_TIME)).all()

    def test_funding_boundary_excluded(self, store_with_future_bar: ParquetStore) -> None:
        rs = ReplayParquetStore(store_with_future_bar)
        df = rs.load_funding(SYMBOL, TICK_TIME)
        assert not df.empty
        funding_rates = set(df["rate"].tolist())
        assert 0.9999 not in funding_rates, "boundary funding rate must be filtered"
        assert 0.0001 in funding_rates, "past funding rate must be present"

    def test_oi_boundary_excluded(self, store_with_future_bar: ParquetStore) -> None:
        rs = ReplayParquetStore(store_with_future_bar)
        df = rs.load_oi(SYMBOL, TICK_TIME)
        assert not df.empty
        oi_values = set(df["oi"].tolist())
        assert 9_999_999 not in oi_values, "boundary OI must be filtered"
        assert 1_000_000 in oi_values, "past OI must be present"

    def test_empty_store_returns_empty(self, tmp_path: Path) -> None:
        store = ParquetStore(tmp_path)
        rs = ReplayParquetStore(store)
        df = rs.load_candles(SYMBOL, Timeframe.H4, TICK_TIME)
        assert df.empty

    def test_all_future_returns_empty(self, tmp_path: Path) -> None:
        """If the only data is at or after tick_time, result must be empty."""
        store = ParquetStore(tmp_path)
        store.save_candles([_make_candle(SYMBOL, TICK_TIME, close=500.0)])
        rs = ReplayParquetStore(store)
        df = rs.load_candles(SYMBOL, Timeframe.H4, TICK_TIME)
        assert df.empty


class TestLeakProof:
    """
    Without the guard, the naive ContextBuilder would return future data.

    This test proves the guard is non-trivial: if we bypass it, the future
    candle IS visible.  If this test starts failing, it means the test is no
    longer a valid sentinel (data is no longer leaking even without the guard,
    which would itself be a bug in how the test is set up).
    """

    def test_naive_builder_sees_future_candle(
        self, store_with_future_bar: ParquetStore
    ) -> None:
        """ContextBuilder (no guard) must return the future candle."""
        # Use the live ContextBuilder which has NO time-fence.
        builder = ContextBuilder(store_with_future_bar)
        ctx = builder.build(SYMBOL, TICK_TIME)
        df_h4 = ctx.candles.get(Timeframe.H4)
        assert df_h4 is not None, "H4 candles must not be None without guard"
        close_values = set(df_h4["c"].tolist())
        # Without the guard the future candle (close=999) IS present.
        assert 999.0 in close_values, (
            "Naive ContextBuilder should see the future candle — "
            "if it does not, the test setup is wrong"
        )

    def test_replay_builder_hides_future_candle(
        self, store_with_future_bar: ParquetStore
    ) -> None:
        """ReplayContextBuilder must hide the future candle."""
        rs = ReplayParquetStore(store_with_future_bar)
        builder = ReplayContextBuilder(rs)
        ctx = builder.build(SYMBOL, TICK_TIME)
        df_h4 = ctx.candles.get(Timeframe.H4)
        assert df_h4 is not None, "H4 candles must not be None with guard"
        close_values = set(df_h4["c"].tolist())
        assert 999.0 not in close_values, "ReplayContextBuilder must not expose future candle"
        assert 100.0 in close_values, "Past candle must still be visible"
