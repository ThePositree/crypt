from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import ClassVar

from crypt.models import Direction, EvaluationContext, Signal


class BaseEngine(ABC):
    """Abstract base for all signal engines."""

    # Inputs whose absence should trigger the critical-inputs guard in
    # DecisionFilter. Subclasses declare their own list; empty by default
    # (engines that degrade gracefully without any single critical input).
    critical_inputs: ClassVar[list[str]] = []

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
        missing = inputs_missing or []
        critical_missing = [k for k in missing if k in self.critical_inputs]
        return Signal(
            engine=self.name,
            symbol=ctx.symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            rationale=rationale,
            inputs_missing=missing,
            critical_missing=critical_missing,
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
