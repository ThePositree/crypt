from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from crypt.models import Direction, EvaluationContext, Signal


class BaseEngine(ABC):
    """Abstract base for all signal engines."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, ctx: EvaluationContext) -> Signal: ...

    # ------------------------------------------------------------------
    # Helpers for constructing Signal objects
    # ------------------------------------------------------------------

    def _signal(
        self,
        ctx: EvaluationContext,
        direction: Direction,
        strength: float,
        confidence: float,
        rationale: list[str],
        inputs_missing: list[str] | None = None,
        meta: dict[str, object] | None = None,
    ) -> Signal:
        return Signal(
            engine=self.name,
            symbol=ctx.symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
            inputs_missing=inputs_missing or [],
            meta=meta or {},
            produced_at=datetime.now(tz=UTC),
        )

    def _neutral(
        self,
        ctx: EvaluationContext,
        rationale: list[str],
        inputs_missing: list[str] | None = None,
        meta: dict[str, object] | None = None,
    ) -> Signal:
        return self._signal(
            ctx,
            direction="neutral",
            strength=0.0,
            confidence=0.0,
            rationale=rationale,
            inputs_missing=inputs_missing,
            meta=meta,
        )
