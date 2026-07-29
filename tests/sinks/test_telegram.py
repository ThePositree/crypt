"""Unit tests for Russian Telegram decision-alert formatting."""

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
        decision=decision,
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
        assert "модель ещё не откалибрована" in msg
        assert "[UNCALIBRATED]" in msg

    def test_uncalibrated_flag_present_when_true(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=True)
        assert "модель ещё не откалибрована" in msg

    def test_uncalibrated_flag_absent_when_false(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=False)
        assert "модель ещё не откалибрована" not in msg

    def test_uncalibrated_marker_on_first_line(self) -> None:
        msg = _format_message(_make_verdict(), uncalibrated=True)
        first_line = msg.splitlines()[0]
        assert "модель ещё не откалибрована" in first_line
        assert "SOL-USDT-SWAP" in first_line
        assert "рост (покупка)" in first_line

    def test_confidence_and_score_in_message(self) -> None:
        msg = _format_message(_make_verdict(confidence=78))
        assert "78%" in msg
        assert "+0.412" in msg
        assert "Уверенность модели" in msg

    def test_regime_in_message(self) -> None:
        msg = _format_message(_make_verdict())
        assert "выраженное движение" in msg

    @pytest.mark.parametrize("decision,emoji", [("BUY", "🟢"), ("SELL", "🔴")])
    def test_decision_emoji(self, decision: str, emoji: str) -> None:
        msg = _format_message(_make_verdict(decision=decision))
        assert emoji in msg

    def test_legacy_rationale_is_html_escaped(self) -> None:
        verdict = _make_verdict().model_copy(update={"rationale": "<b>untrusted</b>"})

        msg = _format_message(verdict)

        assert "&lt;b&gt;untrusted&lt;/b&gt;" in msg

    def test_legacy_rationale_is_bounded_after_html_escaping(self) -> None:
        verdict = _make_verdict().model_copy(update={"rationale": "&<>" * 2_000})

        msg = _format_message(verdict)

        assert len(msg) <= 4_000
        assert "&amp;&lt;&gt;" in msg
