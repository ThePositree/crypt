"""Quality-diversity archive for DSS."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, pstdev
from typing import Literal

from backtester.strategy_discovery.dss_config import DSSBehavior, DSSCandidate

ArchiveRole = Literal["robust", "average", "low_drawdown"]


@dataclass(frozen=True, slots=True)
class DSSScore:
    """Score summary used by archive and reports."""

    candidate_id: str
    window_scores: dict[str, float]
    trades_by_window: dict[str, int]
    robust_score: float
    score_min: float
    score_median: float
    score_mean: float
    score_stdev: float
    worst_drawdown_pct: float | None = None

    @classmethod
    def from_window_scores(
        cls,
        *,
        candidate: DSSCandidate,
        window_scores: dict[str, float],
        trades_by_window: dict[str, int],
        novelty_bonus: float = 0.0,
        worst_drawdown_pct: float | None = None,
    ) -> DSSScore:
        values = list(window_scores.values())
        if not values:
            values = [-10_000.0]
        score_min = min(values)
        score_median = float(median(values))
        score_mean = float(mean(values))
        score_stdev = float(pstdev(values)) if len(values) > 1 else 0.0
        duplicate_penalty = len(candidate.filter_names) - len(set(candidate.filter_names))
        complexity_penalty = 5.0 * len(candidate.filter_names) + 10.0 * duplicate_penalty
        robust = score_min + 0.25 * score_median - 0.10 * score_stdev + novelty_bonus - complexity_penalty
        return cls(
            candidate_id=candidate.candidate_id,
            window_scores=window_scores,
            trades_by_window=trades_by_window,
            robust_score=float(robust),
            score_min=float(score_min),
            score_median=score_median,
            score_mean=score_mean,
            score_stdev=score_stdev,
            worst_drawdown_pct=worst_drawdown_pct,
        )


@dataclass(frozen=True, slots=True)
class DSSArchiveElite:
    candidate: DSSCandidate
    behavior: DSSBehavior
    score: DSSScore
    role: ArchiveRole

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "behavior_cell": self.behavior.to_label(),
            "candidate": self.candidate.to_dict(),
            "score": {
                "window_scores": self.score.window_scores,
                "trades_by_window": self.score.trades_by_window,
                "robust_score": self.score.robust_score,
                "score_min": self.score.score_min,
                "score_median": self.score.score_median,
                "score_mean": self.score.score_mean,
                "score_stdev": self.score.score_stdev,
                "worst_drawdown_pct": self.score.worst_drawdown_pct,
            },
        }


class DSSArchive:
    """MAP-Elites style archive with one elite per role in each cell."""

    def __init__(self) -> None:
        self._cells: dict[tuple[str, str, str, str, str], dict[ArchiveRole, DSSArchiveElite]] = {}

    @property
    def occupied_cells(self) -> int:
        return len(self._cells)

    def consider(
        self,
        candidate: DSSCandidate,
        behavior: DSSBehavior,
        score: DSSScore,
    ) -> bool:
        cell = self._cells.setdefault(behavior.cell_key, {})
        changed = False
        for role in ("robust", "average", "low_drawdown"):
            current = cell.get(role)
            elite = DSSArchiveElite(candidate=candidate, behavior=behavior, score=score, role=role)
            if current is None or _role_value(elite, role) > _role_value(current, role):
                cell[role] = elite
                changed = True
        return changed

    def elites(self) -> list[DSSArchiveElite]:
        seen: set[tuple[str, ArchiveRole]] = set()
        out: list[DSSArchiveElite] = []
        for cell in self._cells.values():
            for role, elite in cell.items():
                key = (elite.candidate.candidate_id, role)
                if key in seen:
                    continue
                seen.add(key)
                out.append(elite)
        return sorted(out, key=lambda e: e.score.robust_score, reverse=True)

    def best_per_cell(self) -> list[DSSArchiveElite]:
        out: list[DSSArchiveElite] = []
        for cell in self._cells.values():
            out.append(max(cell.values(), key=lambda e: e.score.robust_score))
        return sorted(out, key=lambda e: e.score.robust_score, reverse=True)

    def to_dict(self) -> dict[str, object]:
        cells: list[dict[str, object]] = []
        for key, role_map in sorted(self._cells.items()):
            cells.append(
                {
                    "cell": list(key),
                    "elites": [elite.to_dict() for elite in role_map.values()],
                }
            )
        return {"occupied_cells": self.occupied_cells, "cells": cells}


def _role_value(elite: DSSArchiveElite, role: ArchiveRole) -> float:
    if role == "average":
        return elite.score.score_mean
    if role == "low_drawdown":
        dd = elite.score.worst_drawdown_pct
        dd_bonus = 0.0 if dd is None else -abs(dd)
        return elite.score.robust_score + dd_bonus
    return elite.score.robust_score
