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
    critical_missing: list[str] | None = None,
) -> Verdict:
    sig = Signal(
        engine="trend",
        symbol=_SYM,
        direction="bullish" if decision == "BUY" else "bearish",
        strength=0.5,
        confidence=0.8,
        inputs_missing=inputs_missing or [],
        critical_missing=critical_missing or [],
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
    v = _verdict(inputs_missing=["candles[H4]"], critical_missing=["candles[H4]"])
    guarded = f.apply_guard(v)
    assert guarded.decision == "HOLD"
    assert f.should_alert(guarded) is False


def test_no_missing_input_not_downgraded() -> None:
    f = DecisionFilter()
    v = _verdict()
    guarded = f.apply_guard(v)
    assert guarded.decision == "BUY"


def test_non_critical_missing_does_not_downgrade() -> None:
    """
    An engine that loses a non-critical input (e.g. oi) should NOT trigger
    the guard. Only critical_missing matters.
    """
    f = DecisionFilter()
    v = _verdict(inputs_missing=["oi"], critical_missing=[])
    guarded = f.apply_guard(v)
    assert guarded.decision == "BUY"


def test_critical_missing_via_engine_classvar() -> None:
    """
    Verify that BaseEngine._signal populates critical_missing automatically
    from the engine's critical_inputs ClassVar.
    """
    from crypt.engines.trend import TrendEngine
    from crypt.models import EvaluationContext

    engine = TrendEngine()
    ctx = EvaluationContext(
        symbol="TEST",
        tick_time=_NOW,
        candles={},  # no H4 — should trigger critical_missing
        funding=None,
        oi=None,
        ls_ratio=None,
        taker_volume=None,
    )
    sig = engine.evaluate(ctx)
    assert "candles[H4]" in sig.inputs_missing
    assert "candles[H4]" in sig.critical_missing


def test_non_critical_engine_has_empty_critical_missing() -> None:
    """
    DerivativesEngine has no critical_inputs → critical_missing stays empty
    even when derivative data is absent.
    """
    from crypt.engines.derivatives import DerivativesEngine
    from crypt.models import EvaluationContext

    engine = DerivativesEngine()
    ctx = EvaluationContext(
        symbol="TEST",
        tick_time=_NOW,
        candles={},
        funding=None,
        oi=None,
        ls_ratio=None,
        taker_volume=None,
    )
    sig = engine.evaluate(ctx)
    assert sig.critical_missing == []
