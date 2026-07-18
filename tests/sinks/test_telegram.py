"""Unit tests for TelegramSink message formatting and uncalibrated flag."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crypt.models import Regime, Signal, Verdict
from crypt.sinks.telegram import _format_message


def _make_verdict(decision: str = "BUY", confidence: int = 78) -> Verdict:
    now = datetime.now(tz=UTC)
    signal = Signal(
        engine="trend",
        symbol="SOL-USDT-SWAP",
        direction="bullish",
        strength=0.7,
        confidence=0.78,
        rationale=["test rationale"],
        inputs_missing=[],
        meta={},
        produced_at=now,
    )
    return Verdict(
        symbol="SOL-USDT-SWAP",
        decision=decision,  # type: ignore[arg-type]
        confidence=confidence,
        score=0.412,
        regime=Regime.TRENDING,
        breakdown=[signal],
        rationale="Regime: TRENDING | decision: BUY (78%)",
        produced_at=now,
    )


class TestFormatMessage:
    def test_uncalibrated_flag_present_by_default(self) -> None:
        msg = _format_message(_make_verdict())
        assert "[UNCALIBRATED]" in msg

    def test_uncalibrated_flag_present_when_true(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=True)
        assert "[UNCALIBRATED]" in msg

    def test_uncalibrated_flag_absent_when_false(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=False)
        assert "[UNCALIBRATED]" not in msg

    def test_uncalibrated_marker_on_first_line(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=True)
        first_line = msg.splitlines()[0]
        assert "[UNCALIBRATED]" in first_line
        assert "SOL-USDT-SWAP" in first_line
        assert "BUY" in first_line

    def test_confidence_and_score_in_message(self) -> None:
        msg = _format_message(_make_verdict(confidence=78))
        assert "78%" in msg
        assert "+0.412" in msg

    def test_regime_in_message(self) -> None:
        msg = _format_message(_make_verdict())
        assert "TRENDING" in msg

    @pytest.mark.parametrize("decision,emoji", [("BUY", "🟢"), ("SELL", "🔴")])
    def test_decision_emoji(self, decision: str, emoji: str) -> None:
        msg = _format_message(_make_verdict(decision=decision))
        assert emoji in msg
