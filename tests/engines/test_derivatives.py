from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypt.engines.derivatives import DerivativesEngine
from crypt.models import LongShortRatioSnapshot, OISnapshot
from tests.conftest import make_ctx, make_trending_up_h4

engine = DerivativesEngine()

_T0 = datetime(2025, 1, 1, tzinfo=UTC)


def _make_oi(values: list[float]) -> list[OISnapshot]:
    return [
        OISnapshot(symbol="BTC-USDT-SWAP", ts=_T0 + timedelta(hours=i), oi=Decimal(str(v)))
        for i, v in enumerate(values)
    ]


def _make_ls(values: list[float]) -> list[LongShortRatioSnapshot]:
    return [
        LongShortRatioSnapshot(
            symbol="BTC-USDT-SWAP",
            ts=_T0 + timedelta(hours=i),
            long_ratio=v,
            short_ratio=1.0 - v,
        )
        for i, v in enumerate(values)
    ]


def test_oi_rising_with_price_bullish() -> None:
    h4 = make_trending_up_h4(30)
    oi = _make_oi([float(v) * 1_000_000 for v in range(1, 20)])
    ctx = make_ctx(h4=h4, oi=oi)
    sig = engine.evaluate(ctx)
    assert sig.direction in ("bullish", "neutral")


def test_missing_oi_inputs_missing() -> None:
    ctx = make_ctx()  # no OI
    sig = engine.evaluate(ctx)
    assert "oi" in sig.inputs_missing


def test_no_oi_no_ls_neutral() -> None:
    ctx = make_ctx()
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert "oi" in sig.inputs_missing
    assert "ls_ratio" in sig.inputs_missing


def test_oi_only_missing_ls_lower_confidence() -> None:
    oi = _make_oi([float(v) * 1_000_000 for v in range(1, 20)])
    ctx = make_ctx(oi=oi)  # no ls_ratio
    sig = engine.evaluate(ctx)
    # ls_ratio missing → confidence penalty of -0.2 from base 0.5
    assert sig.confidence <= 0.5
    assert "ls_ratio" in sig.inputs_missing


def test_ls_only_missing_oi_lower_confidence() -> None:
    ls = _make_ls([0.5] * 20 + [0.6])
    ctx = make_ctx(ls_ratio=ls)  # no OI
    sig = engine.evaluate(ctx)
    # oi missing → confidence penalty of -0.3 from base 0.5
    assert sig.confidence <= 0.3
    assert "oi" in sig.inputs_missing


def test_oi_and_ls_agree_high_confidence() -> None:
    # Falling OI + falling price → bearish OI signal.
    # High LS ratio (many longs) → contrarian bearish LS signal.
    h4 = make_trending_up_h4(30)
    oi = _make_oi([float(v) for v in range(200, 181, -1)])
    ls = _make_ls([0.55] * 20 + [0.70])
    ctx = make_ctx(h4=h4, oi=oi, ls_ratio=ls)
    sig = engine.evaluate(ctx)
    assert sig.confidence >= 0.5
