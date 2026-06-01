"""Tests for src/crypt/backtest/walkforward.py.

Key property: no test slice timestamp ever appears in the corresponding
train slice (docs/backtest.md §15: test_walk_forward_split.py).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from crypt.backtest.walkforward import generate_folds, slice_verdicts

# ---------------------------------------------------------------------------
# generate_folds tests
# ---------------------------------------------------------------------------


def test_generate_folds_count() -> None:
    """n_folds=5 produces n_folds-1=4 FoldSpec objects."""
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    folds = generate_folds(from_dt, to_dt, 5)
    assert len(folds) == 4


def test_generate_folds_no_overlap() -> None:
    """No test slice timestamp ever appears in the train slice of the same fold."""
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    folds = generate_folds(from_dt, to_dt, 4)

    for fold in folds:
        # Test slice starts exactly where train slice ends.
        assert fold.test_from == fold.train_to
        # Test slice ends after test starts.
        assert fold.test_to > fold.test_from
        # Train slice starts at from_dt.
        assert fold.train_from == from_dt


def test_generate_folds_expanding_train() -> None:
    """Each successive fold has a strictly longer train slice."""
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    folds = generate_folds(from_dt, to_dt, 5)

    for i in range(1, len(folds)):
        prev_train_end = folds[i - 1].train_to
        curr_train_end = folds[i].train_to
        assert curr_train_end > prev_train_end, f"fold {i} train end not later than fold {i - 1}"


def test_generate_folds_last_test_to_equals_to_dt() -> None:
    """Last fold's test_to equals the original to_dt."""
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    folds = generate_folds(from_dt, to_dt, 4)
    assert folds[-1].test_to == to_dt


def test_generate_folds_invalid_n_folds() -> None:
    """n_folds < 2 raises ValueError."""
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="n_folds must be >= 2"):
        generate_folds(from_dt, to_dt, 1)


def test_generate_folds_synthetic_1_year_4_folds() -> None:
    """
    Regression: 1 year of data with 4 folds, no test slice appears in train.

    Creates a synthetic tick dataset covering [from_dt, to_dt) and verifies
    the no-overlap property on actual timestamps.
    """
    from_dt = datetime(2025, 1, 1, tzinfo=UTC)
    to_dt = datetime(2026, 1, 1, tzinfo=UTC)
    folds = generate_folds(from_dt, to_dt, 4)

    # Build a dense H4 tick series.
    ticks = pd.date_range(from_dt, to_dt, freq="4h", inclusive="left", tz="UTC")
    tick_series = pd.Series(ticks, name="tick_time")

    for fold in folds:
        train_ticks = tick_series[(tick_series >= fold.train_from) & (tick_series < fold.train_to)]
        test_ticks = tick_series[(tick_series >= fold.test_from) & (tick_series < fold.test_to)]
        overlap = set(train_ticks.values) & set(test_ticks.values)
        assert len(overlap) == 0, (
            f"Fold {fold.fold_index}: {len(overlap)} timestamps appear in both train and test"
        )


# ---------------------------------------------------------------------------
# slice_verdicts tests
# ---------------------------------------------------------------------------


def _make_verdicts(n: int, start: datetime) -> pd.DataFrame:
    return pd.DataFrame(
        [{"tick_time": start + timedelta(hours=4 * i), "decision": "BUY"} for i in range(n)]
    )


def test_slice_verdicts_basic() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _make_verdicts(20, start)
    from_dt = start + timedelta(days=1)
    to_dt = start + timedelta(days=3)
    sliced = slice_verdicts(df, from_dt, to_dt)
    for _, row in sliced.iterrows():
        assert row["tick_time"] >= pd.Timestamp(from_dt)
        assert row["tick_time"] < pd.Timestamp(to_dt)


def test_slice_verdicts_empty_result() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _make_verdicts(5, start)
    # Slice after all ticks.
    from_dt = start + timedelta(days=100)
    to_dt = start + timedelta(days=200)
    sliced = slice_verdicts(df, from_dt, to_dt)
    assert sliced.empty
