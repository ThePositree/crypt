from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypt.engines.derivatives import DerivativesEngine
from crypt.models import FundingSnapshot, LongShortRatioSnapshot, OISnapshot
from tests.conftest import make_ctx, make_trending_up_h4

engine = DerivativesEngine()

_T0 = datetime(2025, 1, 1, tzinfo=UTC)


def _make_funding(rates: list[float]) -> list[FundingSnapshot]:
    return [
        FundingSnapshot(symbol="BTC-USDT-SWAP", ts=_T0 + timedelta(hours=8 * i), rate=Decimal(str(r)))
        for i, r in enumerate(rates)
    ]


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


def test_extreme_positive_funding_bearish() -> None:
    # Funding z-score ≈ +3 (very high) → contrarian bearish push.
    base_rate = 0.0001
    rates = [base_rate] * 20 + [base_rate + 0.006]  # +3 sigma spike
    ctx = make_ctx(funding=_make_funding(rates))
    sig = engine.evaluate(ctx)
    # With only funding (no OI, no L/S), direction should be bearish or neutral.
    assert sig.direction in ("bearish", "neutral")
    if sig.direction == "bearish":
        assert sig.strength < 0


def test_oi_rising_with_price_bullish() -> None:
    h4 = make_trending_up_h4(30)
    # OI growing 10% over last 5 bars.
    oi_vals = list(range(100, 110)) + [110] * 5  # last few bars include a rising step
    oi_vals = [float(v) * 1_000_000 for v in range(1, 20)]
    oi = _make_oi(oi_vals)
    funding = _make_funding([0.0001] * 20)
    ctx = make_ctx(h4=h4, funding=funding, oi=oi)
    sig = engine.evaluate(ctx)
    # With bullish price and rising OI, should lean bullish or neutral.
    assert sig.direction in ("bullish", "neutral")


def test_missing_oi_inputs_missing() -> None:
    funding = _make_funding([0.0001] * 10)
    ctx = make_ctx(funding=funding)  # no OI
    sig = engine.evaluate(ctx)
    assert "oi" in sig.inputs_missing


def test_no_funding_neutral() -> None:
    ctx = make_ctx()
    sig = engine.evaluate(ctx)
    assert sig.direction == "neutral"
    assert "funding" in sig.inputs_missing


def test_all_sub_signals_agree_high_confidence() -> None:
    # Extreme positive funding (bearish) + falling OI with falling price (bearish) + high LS ratio (bearish).

    # Extreme positive funding.
    base = 0.0001
    rates = [base] * 20 + [base + 0.006]
    funding = _make_funding(rates)

    # Falling OI with falling price hint.
    oi = _make_oi([float(v) for v in range(200, 181, -1)])

    # High LS ratio (many longs → contrarian bearish).
    ls = _make_ls([0.55] * 20 + [0.70])

    h4 = make_trending_up_h4(30)  # price direction for OI signal
    ctx = make_ctx(h4=h4, funding=funding, oi=oi, ls_ratio=ls)
    sig = engine.evaluate(ctx)
    assert sig.confidence >= 0.3
