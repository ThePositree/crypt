"""
BacktestRecorder — in-memory verdict sink for the replay loop.

Replaces JsonLogSink during backtesting (docs/backtest.md §5.2).
Stores all Verdict objects in memory, then writes a single Parquet file
at the end of the replay so the metrics layer can query them efficiently.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from crypt.aggregator.weights import SCORING_ENGINES
from crypt.models import Verdict

_STRENGTH_COLUMNS = [f"strength_{engine}" for engine in sorted(SCORING_ENGINES)]


class BacktestRecorder:
    """
    Collects Verdict objects emitted by the replay loop.

    Usage:
        recorder = BacktestRecorder()
        # inside replay loop:
        recorder.record(verdict)
        # after loop:
        df = recorder.to_dataframe()
        recorder.save(path)
    """

    def __init__(self) -> None:
        self._rows: list[dict[str, object]] = []

    def record(self, verdict: Verdict) -> None:
        """Append one verdict to the in-memory buffer."""
        row: dict[str, object] = {
            "symbol": verdict.symbol,
            "tick_time": verdict.produced_at,
            "decision": verdict.decision,
            "confidence": verdict.confidence,
            "score": verdict.score,
            "regime": verdict.regime,
            "rationale": verdict.rationale,
        }
        strengths = {
            signal.engine: signal.strength
            for signal in verdict.breakdown
            if signal.engine in SCORING_ENGINES
        }
        for engine in sorted(SCORING_ENGINES):
            row[f"strength_{engine}"] = strengths.get(engine)
        self._rows.append(row)

    def to_dataframe(self) -> pd.DataFrame:
        """Return all recorded verdicts as a DataFrame."""
        if not self._rows:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "tick_time",
                    "decision",
                    "confidence",
                    "score",
                    "regime",
                    "rationale",
                    *_STRENGTH_COLUMNS,
                ]
            )
        df = pd.DataFrame(self._rows)
        df["tick_time"] = pd.to_datetime(df["tick_time"], utc=True)
        return df.sort_values("tick_time").reset_index(drop=True)

    def save(self, path: Path) -> None:
        """Write verdicts to a Parquet file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        df.to_parquet(path, index=False)

    def __len__(self) -> int:
        return len(self._rows)

    def filter_alerts(self) -> pd.DataFrame:
        """Return only BUY/SELL verdicts (HOLD verdicts have no fee impact)."""
        df = self.to_dataframe()
        if df.empty:
            return df
        return df[df["decision"].isin(("BUY", "SELL"))].reset_index(drop=True)
