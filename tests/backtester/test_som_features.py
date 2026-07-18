from __future__ import annotations

import pandas as pd
import pytest

from backtester.strategies.som import SOMStrategy


def _order_block_fixture(rows: int = 24) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0] * rows,
            "high": [105.0] * rows,
            "low": [95.0] * rows,
            "close": [100.0] * rows,
            "volume": [1_000.0] * rows,
        },
        index=index,
    )

    # Candidate bullish order-block candle.
    df.iloc[15, df.columns.get_loc("open")] = 100.0
    df.iloc[15, df.columns.get_loc("high")] = 102.0
    df.iloc[15, df.columns.get_loc("low")] = 99.0
    df.iloc[15, df.columns.get_loc("close")] = 101.0

    # Confirming impulse three closed bars later.
    if rows > 18:
        df.iloc[18, df.columns.get_loc("low")] = 80.0
        df.iloc[18, df.columns.get_loc("close")] = 82.0
    return df


def test_detect_order_blocks_confirms_without_backfilling_future_label() -> None:
    df = _order_block_fixture()

    ob, zone_high, zone_low = SOMStrategy.detect_order_blocks(df, lookback=3)

    assert ob.iloc[15] == 0
    assert pd.isna(zone_high.iloc[15])
    assert pd.isna(zone_low.iloc[15])
    assert ob.iloc[18] == 1
    assert zone_high.iloc[18] == pytest.approx(102.0)
    assert zone_low.iloc[18] == pytest.approx(99.0)


def test_detect_order_blocks_prefix_is_stable_when_future_rows_are_added() -> None:
    prefix = _order_block_fixture(rows=18)
    full = _order_block_fixture(rows=24)

    prefix_ob, _, _ = SOMStrategy.detect_order_blocks(prefix, lookback=3)
    full_ob, _, _ = SOMStrategy.detect_order_blocks(full, lookback=3)

    pd.testing.assert_series_equal(full_ob.iloc[: len(prefix_ob)], prefix_ob)


def test_order_block_size_uses_confirmed_zone_not_confirmation_bar_range() -> None:
    df = _order_block_fixture()
    ob, zone_high, zone_low = SOMStrategy.detect_order_blocks(df, lookback=3)

    ratio = SOMStrategy.calculate_ob_size_ratio_to_atr(
        df,
        ob,
        ob_zone_high=zone_high,
        ob_zone_low=zone_low,
    )

    atr_at_confirmation = SOMStrategy.calculate_atr(df, period=14).iloc[18]
    assert ratio.iloc[18] == pytest.approx((102.0 - 99.0) / atr_at_confirmation)
