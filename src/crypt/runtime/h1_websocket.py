from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from crypt.models import Candle, Timeframe

_OKX_BUSINESS_WS_URL = "wss://ws.okx.com:8443/ws/v5/business"
_EXECUTION_CALLBACK_TIMEOUT_S = 90.0
_CHANNEL_TO_TIMEFRAME = {
    "candle1H": Timeframe.H1,
    "candle4H": Timeframe.H4,
    "candle1Dutc": Timeframe.D1,
}
_TIMEFRAME_DELTA = {
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}


@dataclass(frozen=True)
class H1Boundary:
    symbol: str
    boundary_time: datetime
    closed_candles: tuple[Candle, ...]
    next_open: float


BoundaryCallback = Callable[[str, H1Boundary | None, str], Awaitable[None]]
ErrorCallback = Callable[[str, BaseException | str], Awaitable[None]]
BoundaryReceiver = Callable[[datetime], Awaitable[dict[str, H1Boundary]]]


class H1WebSocketScheduler:
    """Trigger H1 execution from confirmed OKX candles with a REST fallback."""

    def __init__(
        self,
        callback: BoundaryCallback,
        symbols: list[str],
        *,
        error_callback: ErrorCallback | None = None,
        websocket_url: str = _OKX_BUSINESS_WS_URL,
        boundary_receiver: BoundaryReceiver | None = None,
    ) -> None:
        self._callback = callback
        self._symbols = tuple(symbols)
        self._error_callback = error_callback
        self._websocket_url = websocket_url
        self._boundary_receiver = boundary_receiver or self._receive_boundaries
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._listener_tasks: set[asyncio.Task[None]] = set()
        self._in_flight: set[tuple[str, datetime]] = set()
        self._completed: set[tuple[str, datetime]] = set()

    def start(self) -> None:
        self._scheduler.add_job(
            self._start_listener,
            trigger=CronTrigger(minute=59, second=30, timezone="UTC"),
            id="h1_websocket_prepare",
            max_instances=1,
            misfire_grace_time=20,
        )
        self._scheduler.add_job(
            self._run_rest_fallback,
            trigger=CronTrigger(minute=2, second=0, timezone="UTC"),
            id="h1_rest_fallback",
            max_instances=1,
            misfire_grace_time=120,
        )
        self._scheduler.start()
        logger.info(
            "H1 WebSocket scheduler started — prepares at *:59:30 UTC; "
            "REST fallback at *:02:00 UTC"
        )

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        for task in tuple(self._listener_tasks):
            task.cancel()
        logger.info("H1 WebSocket scheduler stopped")

    async def run_now(self) -> None:
        """Run a startup reconciliation tick through the duplicate guard."""
        boundary = _floor_hour(datetime.now(UTC))
        for symbol in self._symbols:
            await self._dispatch(symbol, boundary, None, "startup")

    async def _start_listener(self) -> None:
        now = datetime.now(UTC)
        boundary = _floor_hour(now) + timedelta(hours=1)
        task = asyncio.create_task(
            self._listen_and_dispatch(boundary),
            name=f"okx-h1-boundary-{boundary.isoformat()}",
        )
        self._listener_tasks.add(task)
        task.add_done_callback(self._listener_tasks.discard)

    async def _listen_and_dispatch(self, boundary: datetime) -> None:
        try:
            boundaries = await self._boundary_receiver(boundary)
            await asyncio.gather(
                *(
                    self._dispatch(symbol, boundary, boundaries[symbol], "websocket")
                    for symbol in self._symbols
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "OKX H1 WebSocket trigger failed for boundary {}",
                boundary.isoformat(),
            )
            await self._report_error(
                f"OKX H1 WebSocket boundary {boundary.isoformat()}",
                exc,
            )

    async def _run_rest_fallback(self) -> None:
        boundary = _floor_hour(datetime.now(UTC))
        for symbol in self._symbols:
            key = (symbol, boundary)
            if key in self._completed or key in self._in_flight:
                logger.info(
                    "REST fallback skipped for {} boundary={} — already handled by WebSocket",
                    symbol,
                    boundary.isoformat(),
                )
                continue
            logger.warning(
                "Using REST H1 fallback for {} boundary={}",
                symbol,
                boundary.isoformat(),
            )
            await self._dispatch(symbol, boundary, None, "rest_fallback")

    async def _dispatch(
        self,
        symbol: str,
        boundary: datetime,
        payload: H1Boundary | None,
        source: str,
    ) -> None:
        key = (symbol, boundary)
        if key in self._completed or key in self._in_flight:
            logger.info(
                "Duplicate H1 trigger ignored for {} boundary={} source={}",
                symbol,
                boundary.isoformat(),
                source,
            )
            return

        self._in_flight.add(key)
        logger.info(
            "H1 execution trigger accepted for {} boundary={} source={}",
            symbol,
            boundary.isoformat(),
            source,
        )
        try:
            async with asyncio.timeout(_EXECUTION_CALLBACK_TIMEOUT_S):
                await self._callback(symbol, payload, source)
        except Exception as exc:
            logger.exception(
                "H1 execution callback failed for {} boundary={} source={}",
                symbol,
                boundary.isoformat(),
                source,
            )
            await self._report_error(
                f"H1 execution callback for {symbol} via {source}",
                exc,
            )
        else:
            self._completed.add(key)
            cutoff = boundary - timedelta(hours=2)
            self._completed = {item for item in self._completed if item[1] >= cutoff}
        finally:
            self._in_flight.discard(key)

    async def _report_error(self, context: str, error: BaseException | str) -> None:
        if self._error_callback is not None:
            await self._error_callback(context, error)

    async def _receive_boundaries(self, boundary: datetime) -> dict[str, H1Boundary]:
        expected = {
            symbol: _expected_closed_opens(boundary)
            for symbol in self._symbols
        }
        closed: dict[str, dict[Timeframe, Candle]] = {
            symbol: {} for symbol in self._symbols
        }
        next_opens: dict[str, float] = {}
        deadline = boundary + timedelta(seconds=90)
        subscribe_args = [
            {"channel": channel, "instId": symbol}
            for symbol in self._symbols
            for channel in _CHANNEL_TO_TIMEFRAME
        ]

        logger.info(
            "Connecting to OKX candle WebSocket for boundary={} symbols={}",
            boundary.isoformat(),
            list(self._symbols),
        )
        async with aiohttp.ClientSession() as session:
            while datetime.now(UTC) < deadline:
                try:
                    async with session.ws_connect(
                        self._websocket_url,
                        autoping=True,
                    ) as websocket:
                        await websocket.send_json(
                            {
                                "id": f"h1-{int(boundary.timestamp())}",
                                "op": "subscribe",
                                "args": subscribe_args,
                            }
                        )
                        logger.info(
                            "OKX candle WebSocket subscription sent for boundary={}",
                            boundary.isoformat(),
                        )
                        result = await self._read_connection_until_ready(
                            websocket=websocket,
                            boundary=boundary,
                            deadline=deadline,
                            expected=expected,
                            closed=closed,
                            next_opens=next_opens,
                        )
                        if result is not None:
                            return result
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if datetime.now(UTC) >= deadline:
                        break
                    logger.warning(
                        "OKX candle WebSocket disconnected before boundary confirmation; "
                        "reconnecting: {}",
                        exc,
                    )
                    await asyncio.sleep(1.0)

        raise TimeoutError(
            f"OKX did not confirm all required candles before {deadline.isoformat()}"
        )

    async def _read_connection_until_ready(
        self,
        *,
        websocket: aiohttp.ClientWebSocketResponse,
        boundary: datetime,
        deadline: datetime,
        expected: dict[str, dict[Timeframe, datetime]],
        closed: dict[str, dict[Timeframe, Candle]],
        next_opens: dict[str, float],
    ) -> dict[str, H1Boundary] | None:
        while datetime.now(UTC) < deadline:
            remaining = max((deadline - datetime.now(UTC)).total_seconds(), 0.1)
            try:
                message = await websocket.receive(timeout=min(25.0, remaining))
            except TimeoutError:
                # OKX documents an application-level text ping when no message
                # arrives for less than 30 seconds. goex uses the same 25s cadence.
                await websocket.send_str("ping")
                continue

            if message.type == aiohttp.WSMsgType.ERROR:
                raise RuntimeError(f"OKX candle WebSocket error: {websocket.exception()}")
            if message.type in {
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSED,
            }:
                raise RuntimeError("OKX candle WebSocket closed before confirmation")
            if message.type != aiohttp.WSMsgType.TEXT or message.data == "pong":
                continue

            payload = json.loads(message.data)
            if payload.get("event") == "error":
                raise RuntimeError(
                    f"OKX candle subscription rejected: "
                    f"{payload.get('code')} {payload.get('msg')}"
                )
            if payload.get("event") == "subscribe":
                logger.debug("OKX candle WebSocket subscribed: {}", payload.get("arg"))
                continue

            arg = payload.get("arg")
            data = payload.get("data")
            if not isinstance(arg, dict) or not isinstance(data, list):
                continue
            symbol = arg.get("instId")
            channel = arg.get("channel")
            if symbol not in expected or channel not in _CHANNEL_TO_TIMEFRAME:
                continue

            timeframe = _CHANNEL_TO_TIMEFRAME[channel]
            for raw_row in data:
                candle = _parse_candle_row(symbol, timeframe, raw_row)
                if candle.open_time == expected[symbol].get(timeframe) and candle.closed:
                    closed[symbol][timeframe] = candle
                if (
                    timeframe == Timeframe.H1
                    and candle.open_time == boundary
                    and not candle.closed
                ):
                    next_opens[symbol] = float(candle.o)

            ready = {
                symbol
                for symbol in self._symbols
                if set(closed[symbol]) == set(expected[symbol]) and symbol in next_opens
            }
            if len(ready) == len(self._symbols):
                result = {
                    symbol: H1Boundary(
                        symbol=symbol,
                        boundary_time=boundary,
                        closed_candles=tuple(
                            closed[symbol][timeframe]
                            for timeframe in sorted(
                                closed[symbol],
                                key=lambda item: item.value,
                            )
                        ),
                        next_open=next_opens[symbol],
                    )
                    for symbol in self._symbols
                }
                logger.info(
                    "OKX WebSocket confirmed H1 boundary={} next_opens={}",
                    boundary.isoformat(),
                    next_opens,
                )
                return result
        return None


def _floor_hour(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _expected_closed_opens(boundary: datetime) -> dict[Timeframe, datetime]:
    boundary = boundary.astimezone(UTC)
    expected = {Timeframe.H1: boundary - _TIMEFRAME_DELTA[Timeframe.H1]}
    if boundary.hour % 4 == 0:
        expected[Timeframe.H4] = boundary - _TIMEFRAME_DELTA[Timeframe.H4]
    if boundary.hour == 0:
        expected[Timeframe.D1] = boundary - _TIMEFRAME_DELTA[Timeframe.D1]
    return expected


def _parse_candle_row(
    symbol: str,
    timeframe: Timeframe,
    raw_row: Any,
) -> Candle:
    if not isinstance(raw_row, list) or len(raw_row) < 9:
        raise ValueError(f"invalid OKX {timeframe.value} candle payload: {raw_row!r}")
    try:
        open_time = datetime.fromtimestamp(int(raw_row[0]) / 1000, tz=UTC)
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            o=Decimal(str(raw_row[1])),
            h=Decimal(str(raw_row[2])),
            low=Decimal(str(raw_row[3])),
            c=Decimal(str(raw_row[4])),
            volume=Decimal(str(raw_row[5])),
            closed=str(raw_row[8]) == "1",
        )
    except (IndexError, TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid OKX {timeframe.value} candle payload: {raw_row!r}"
        ) from exc
