"""
Walk-forward cross-validation — docs/backtest.md §8.

Expanding-window scheme:
    fold k uses:
        train = [from_dt, from_dt + (T/N) * (k+1)]
        test  =           [from_dt + (T/N) * (k+1), from_dt + (T/N) * (k+2)]

where T = to_dt - from_dt and N = n_folds.

Hard guarantee: no test slice timestamp ever appears in the corresponding
train slice (tests/backtest/test_walk_forward_split.py verifies this).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class FoldSpec:
    """
    A single expanding-window fold.

    Attributes
    ----------
    fold_index : int
        0-based fold index.
    train_from : datetime
        Start of train slice (inclusive).
    train_to : datetime
        End of train slice (exclusive).
    test_from : datetime
        Start of test slice (inclusive, == train_to).
    test_to : datetime
        End of test slice (exclusive).
    """

    fold_index: int
    train_from: datetime
    train_to: datetime
    test_from: datetime
    test_to: datetime

    def __post_init__(self) -> None:
        if self.train_to != self.test_from:
            raise ValueError("train_to must equal test_from (no gap / overlap)")
        if self.test_to <= self.test_from:
            raise ValueError("test_to must be after test_from")
        if self.train_to <= self.train_from:
            raise ValueError("train_to must be after train_from")


def generate_folds(
    from_dt: datetime,
    to_dt: datetime,
    n_folds: int,
) -> list[FoldSpec]:
    """
    Generate expanding-window folds covering [from_dt, to_dt).

    Parameters
    ----------
    from_dt, to_dt : datetime
        Date range to split. Both are normalised to UTC if naive.
    n_folds : int
        Number of folds.  Must be >= 2 (at least one train + one test slice).

    Returns
    -------
    list[FoldSpec]
        Length n_folds - 1 (each fold produces one train + one test slice).
        Fold 0: train = [from, from + T/N], test = [from + T/N, from + 2*T/N].
        Fold k: train = [from, from + T/N*(k+1)], test expands by one step.
    """
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2 for at least one train+test split")

    from_ts = _ensure_utc(from_dt)
    to_ts = _ensure_utc(to_dt)

    if to_ts <= from_ts:
        raise ValueError("to_dt must be after from_dt")

    total_seconds = (to_ts - from_ts).total_seconds()
    step_seconds = total_seconds / n_folds

    folds: list[FoldSpec] = []
    for k in range(n_folds - 1):
        train_from = from_ts
        train_to = from_ts + pd.Timedelta(seconds=step_seconds * (k + 1))
        test_from = train_to
        test_to = from_ts + pd.Timedelta(seconds=step_seconds * (k + 2))
        # Clamp last test slice to to_ts.
        if k == n_folds - 2:
            test_to = to_ts
        folds.append(
            FoldSpec(
                fold_index=k,
                train_from=train_from.to_pydatetime(),
                train_to=train_to.to_pydatetime(),
                test_from=test_from.to_pydatetime(),
                test_to=test_to.to_pydatetime(),
            )
        )
    return folds


def slice_verdicts(
    verdicts_df: pd.DataFrame,
    from_dt: datetime,
    to_dt: datetime,
    time_col: str = "tick_time",
) -> pd.DataFrame:
    """
    Return verdicts where from_dt <= time_col < to_dt.

    Parameters
    ----------
    verdicts_df : pd.DataFrame
        Must have column ``time_col`` (timezone-aware datetime).
    from_dt, to_dt : datetime
        Slice boundaries.
    time_col : str
        Name of the timestamp column (default ``tick_time``).
    """
    df = verdicts_df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    lo = pd.Timestamp(_ensure_utc(from_dt))
    hi = pd.Timestamp(_ensure_utc(to_dt))
    mask = (df[time_col] >= lo) & (df[time_col] < hi)
    return df[mask].reset_index(drop=True)


def slice_trades(
    trades_df: pd.DataFrame,
    from_dt: datetime,
    to_dt: datetime,
    time_col: str = "exit_time",
) -> pd.DataFrame:
    """
    Return trades where from_dt <= time_col < to_dt.

    Trades are keyed by exit_time for metric computation.
    """
    df = trades_df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    lo = pd.Timestamp(_ensure_utc(from_dt))
    hi = pd.Timestamp(_ensure_utc(to_dt))
    mask = (df[time_col] >= lo) & (df[time_col] < hi)
    return df[mask].reset_index(drop=True)


def _ensure_utc(dt: datetime) -> pd.Timestamp:
    if dt.tzinfo is None:
        return pd.Timestamp(dt, tz="UTC")
    return pd.Timestamp(dt).tz_convert("UTC")
