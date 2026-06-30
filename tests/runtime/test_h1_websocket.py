from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from crypt.models import Candle, Timeframe
from crypt.runtime.h1_websocket import (
    H1Boundary,
    H1WebSocketScheduler,
    _expected_closed_opens,
    _parse_candle_row,
)


def test_expected_boundary_requires_higher_timeframes_only_when_they_close() -> None:
    ordinary = _expected_closed_opens(datetime(2026, 6, 30, 13, tzinfo=UTC))
    four_hour = _expected_closed_opens(datetime(2026, 6, 30, 16, tzinfo=UTC))
    midnight = _expected_closed_opens(datetime(2026, 7, 1, 0, tzinfo=UTC))

    assert set(ordinary) == {Timeframe.H1}
    assert set(four_hour) == {Timeframe.H1, Timeframe.H4}
    assert set(midnight) == {Timeframe.H1, Timeframe.H4, Timeframe.D1}


def test_parse_okx_candle_uses_confirm_as_closed_flag() -> None:
    candle = _parse_candle_row(
        "SOL-USDT-SWAP",
        Timeframe.H1,
        [
            "1782824400000",
            "72.05",
            "72.90",
            "71.86",
            "72.84",
            "1294726.9",
            "1294726.9",
            "93600000",
            "1",
        ],
    )

    assert candle.open_time == datetime(2026, 6, 30, 13, tzinfo=UTC)
    assert candle.o == Decimal("72.05")
    assert candle.c == Decimal("72.84")
    assert candle.closed is True


@pytest.mark.asyncio
async def test_websocket_and_fallback_cannot_dispatch_same_boundary_twice() -> None:
    calls: list[tuple[str, str]] = []
    boundary_time = datetime(2026, 6, 30, 14, tzinfo=UTC)
    closed = Candle(
        symbol="SOL-USDT-SWAP",
        timeframe=Timeframe.H1,
        open_time=datetime(2026, 6, 30, 13, tzinfo=UTC),
        o=Decimal("72.05"),
        h=Decimal("72.90"),
        low=Decimal("71.86"),
        c=Decimal("72.84"),
        volume=Decimal("1294726.9"),
        closed=True,
    )
    payload = H1Boundary(
        symbol="SOL-USDT-SWAP",
        boundary_time=boundary_time,
        closed_candles=(closed,),
        next_open=72.84,
    )

    async def callback(
        symbol: str,
        websocket_boundary: H1Boundary | None,
        source: str,
    ) -> None:
        assert websocket_boundary is payload
        calls.append((symbol, source))

    scheduler = H1WebSocketScheduler(callback, ["SOL-USDT-SWAP"])
    await scheduler._dispatch(
        "SOL-USDT-SWAP",
        boundary_time,
        payload,
        "websocket",
    )
    await scheduler._dispatch(
        "SOL-USDT-SWAP",
        boundary_time,
        None,
        "rest_fallback",
    )

    assert calls == [("SOL-USDT-SWAP", "websocket")]


@pytest.mark.asyncio
async def test_failed_websocket_callback_can_be_retried_by_rest_fallback() -> None:
    calls: list[str] = []
    errors: list[str] = []
    boundary_time = datetime(2026, 6, 30, 14, tzinfo=UTC)

    async def callback(
        _symbol: str,
        _websocket_boundary: H1Boundary | None,
        source: str,
    ) -> None:
        calls.append(source)
        if source == "websocket":
            raise RuntimeError("strategy refresh failed")

    async def report_error(context: str, _error: BaseException | str) -> None:
        errors.append(context)

    scheduler = H1WebSocketScheduler(
        callback,
        ["SOL-USDT-SWAP"],
        error_callback=report_error,
    )
    await scheduler._dispatch(
        "SOL-USDT-SWAP",
        boundary_time,
        None,
        "websocket",
    )
    await scheduler._dispatch(
        "SOL-USDT-SWAP",
        boundary_time,
        None,
        "rest_fallback",
    )

    assert calls == ["websocket", "rest_fallback"]
    assert errors == ["H1 execution callback for SOL-USDT-SWAP via websocket"]
