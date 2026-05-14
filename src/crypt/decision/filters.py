from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from crypt.models import Verdict


class DecisionFilter:
    """
    Applies coarse suppression rules between the aggregator and sinks.

    Three active filters for MVP:
      1. Confidence threshold — suppress Telegram if confidence < threshold.
      2. Per-symbol cooldown — suppress Telegram if previous alert < cooldown_hours ago,
         unless direction has flipped.
      3. Inputs-missing guard — downgrade to HOLD if critical candle data missing.

    Verdicts are always passed to non-Telegram sinks regardless of filters.
    """

    def __init__(
        self,
        confidence_threshold: int = 75,
        cooldown_hours: int = 4,
    ) -> None:
        self._threshold = confidence_threshold
        self._cooldown = timedelta(hours=cooldown_hours)
        # symbol → (last_alert_time, last_direction)
        self._last_alert: dict[str, tuple[datetime, str]] = {}

    def should_alert(self, verdict: Verdict) -> bool:
        """
        Return True if a Telegram alert should fire for this verdict.

        Reasons to suppress:
        - decision is HOLD
        - confidence below threshold
        - symbol in cooldown AND direction has not flipped
        - critical inputs missing (candles[H4])
        """
        if verdict.decision == "HOLD":
            return False

        # Filter 3: critical missing inputs → downgrade verdict direction internally.
        if self._has_critical_missing(verdict):
            logger.warning(
                "{} verdict downgraded to HOLD (critical inputs missing)", verdict.symbol
            )
            return False

        # Filter 1: confidence threshold.
        if verdict.confidence < self._threshold:
            logger.debug(
                "{} suppressed — confidence {} < threshold {}",
                verdict.symbol,
                verdict.confidence,
                self._threshold,
            )
            return False

        # Filter 2: cooldown.
        now = verdict.produced_at
        if verdict.symbol in self._last_alert:
            last_time, last_direction = self._last_alert[verdict.symbol]
            if now - last_time < self._cooldown and last_direction == verdict.decision:
                    logger.debug(
                        "{} suppressed — cooldown ({} remaining)",
                        verdict.symbol,
                        self._cooldown - (now - last_time),
                    )
                    return False
                # Direction flip breaks the cooldown.

        return True

    def record_alert(self, verdict: Verdict) -> None:
        """Must be called after each successful Telegram alert."""
        self._last_alert[verdict.symbol] = (verdict.produced_at, verdict.decision)

    def apply_guard(self, verdict: Verdict) -> Verdict:
        """
        Returns a (possibly modified) Verdict after applying the inputs-missing
        guard. Mutates the decision to HOLD if critical data is absent.
        All sinks receive the guarded verdict.
        """
        if self._has_critical_missing(verdict) and verdict.decision != "HOLD":
            return Verdict(
                symbol=verdict.symbol,
                decision="HOLD",
                confidence=verdict.confidence,
                score=verdict.score,
                regime=verdict.regime,
                breakdown=verdict.breakdown,
                rationale=verdict.rationale + "\n[GUARD: critical inputs missing → HOLD]",
                produced_at=verdict.produced_at,
            )
        return verdict

    # ------------------------------------------------------------------

    @staticmethod
    def _has_critical_missing(verdict: Verdict) -> bool:
        """Critical = H4 candle data absent on any contributing engine."""
        return any("candles[H4]" in sig.inputs_missing for sig in verdict.breakdown)
