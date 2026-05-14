from __future__ import annotations

from datetime import UTC, datetime, timedelta

from crypt.decision.filters import DecisionFilter
from crypt.models import Regime, Signal, Verdict

_NOW = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
_SYM = "SOL-USDT-SWAP"


def _verdict(
    decision: str = "BUY",
    confidence: int = 80,
    produced_at: datetime | None = None,
    inputs_missing: list[str] | None = None,
) -> Verdict:
    sig = Signal(
        engine="trend",
        symbol=_SYM,
        direction="bullish" if decision == "BUY" else "bearish",
        strength=0.5,
        confidence=0.8,
        inputs_missing=inputs_missing or [],
        produced_at=produced_at or _NOW,
    )
    return Verdict(
        symbol=_SYM,
        decision=decision,  # type: ignore[arg-type]
        confidence=confidence,
        score=0.5,
        regime=Regime.TRENDING,
        breakdown=[sig],
        rationale="test",
        produced_at=produced_at or _NOW,
    )


def test_confidence_above_threshold_alerts() -> None:
    f = DecisionFilter(confidence_threshold=75)
    v = _verdict(confidence=75)
    assert f.should_alert(v) is True


def test_confidence_below_threshold_suppressed() -> None:
    f = DecisionFilter(confidence_threshold=75)
    v = _verdict(confidence=74)
    assert f.should_alert(v) is False


def test_hold_never_alerts() -> None:
    f = DecisionFilter()
    v = _verdict(decision="HOLD", confidence=99)
    assert f.should_alert(v) is False


def test_cooldown_suppresses_same_direction() -> None:
    f = DecisionFilter(cooldown_hours=4)
    v1 = _verdict(decision="BUY", produced_at=_NOW)
    f.record_alert(v1)
    # Same direction within cooldown.
    v2 = _verdict(decision="BUY", produced_at=_NOW + timedelta(hours=2))
    assert f.should_alert(v2) is False


def test_direction_flip_breaks_cooldown() -> None:
    f = DecisionFilter(cooldown_hours=4)
    v1 = _verdict(decision="BUY", produced_at=_NOW)
    f.record_alert(v1)
    # Direction flip within cooldown — should be alerted.
    v2 = _verdict(decision="SELL", produced_at=_NOW + timedelta(hours=1))
    assert f.should_alert(v2) is True


def test_after_cooldown_passes() -> None:
    f = DecisionFilter(cooldown_hours=4)
    v1 = _verdict(decision="BUY", produced_at=_NOW)
    f.record_alert(v1)
    v2 = _verdict(decision="BUY", produced_at=_NOW + timedelta(hours=5))
    assert f.should_alert(v2) is True


def test_critical_missing_input_downgrade() -> None:
    f = DecisionFilter()
    v = _verdict(inputs_missing=["candles[H4]"])
    guarded = f.apply_guard(v)
    assert guarded.decision == "HOLD"
    assert f.should_alert(guarded) is False


def test_no_missing_input_not_downgraded() -> None:
    f = DecisionFilter()
    v = _verdict()
    guarded = f.apply_guard(v)
    assert guarded.decision == "BUY"
