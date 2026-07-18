from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from crypt.execution.signal_runner import (
    LiveSignalRunner,
    _events_from_row,
    _signal_event_from_raw,
    _timestamp_to_utc,
)
from crypt.models import Candle, Timeframe
from crypt.runtime.h1_websocket import H1Boundary


class _FakeStore:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load_candles(
        self, symbol: str, timeframe: Timeframe, limit: int | None = None
    ) -> pd.DataFrame:
        assert symbol == "SOL-USDT-SWAP"
        assert timeframe == Timeframe.H1
        return self._frame.tail(limit) if limit is not None else self._frame


class _MutableFakeStore:
    def __init__(self, frames: dict[Timeframe, pd.DataFrame]) -> None:
        self._frames = frames

    def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int | None = None,
    ) -> pd.DataFrame:
        assert symbol == "SOL-USDT-SWAP"
        frame = self._frames.get(timeframe, pd.DataFrame({"open_time": []}))
        return frame.tail(limit) if limit is not None else frame

    def save_candles(self, candles: list[Candle]) -> None:
        rows_by_tf: dict[Timeframe, list[dict[str, object]]] = {}
        for candle in candles:
            rows_by_tf.setdefault(candle.timeframe, []).append({"open_time": candle.open_time})
        for timeframe, rows in rows_by_tf.items():
            existing = self._frames.get(timeframe, pd.DataFrame({"open_time": []}))
            new = pd.DataFrame(rows)
            merged = (
                pd.concat([existing, new], ignore_index=True)
                .drop_duplicates(subset=["open_time"], keep="last")
                .sort_values("open_time")
                .reset_index(drop=True)
            )
            self._frames[timeframe] = merged


class _EmptyOkx:
    async def fetch_ohlcv(
        self,
        _symbol: str,
        _tf: Timeframe,
        *,
        limit: int,
        since_ms: int | None,
    ) -> list[Candle]:
        del limit, since_ms
        return []


def test_events_from_signal_events_row_preserves_all_events() -> None:
    row = pd.Series(
        {
            "signal_events": [
                {
                    "signal": 1,
                    "sl_price": 98.0,
                    "selected_strategy": "donor_a",
                    "risk_percent": 0.85,
                },
                {
                    "signal": -1,
                    "sl_price": 102.0,
                    "selected_strategy": "donor_b",
                    "rrr": 1.5,
                },
            ],
            "signal": 0,
            "sl_price": 0.0,
        }
    )

    events = _events_from_row(row)

    assert len(events) == 2
    assert events[0]["selected_strategy"] == "donor_a"
    assert events[1]["selected_strategy"] == "donor_b"


def test_events_from_legacy_scalar_signal_builds_one_event() -> None:
    row = pd.Series(
        {
            "signal": -1,
            "sl_price": 105.0,
            "rrr": 2.0,
            "risk_percent": 1.0,
        }
    )

    assert _events_from_row(row) == [
        {"signal": -1, "sl_price": 105.0, "rrr": 2.0, "risk_percent": 1.0}
    ]


def test_signal_event_from_raw_carries_execution_overrides() -> None:
    event = _signal_event_from_raw(
        datetime(2026, 6, 27, 10, tzinfo=UTC),
        100.0,
        {
            "signal": -1,
            "sl_price": 105.0,
            "selected_strategy": "donor_short",
            "position_group": "donor_short",
            "risk_percent": 0.85,
            "rrr": 1.75,
            "position_ttl_bars": 32,
            "trail_activation_rrr": 1.0,
            "trail_distance_atr": 2.0,
            "exit_geometry": "sl_rrr",
            "min_tp_move_pct": 0.004,
        },
    )

    assert event is not None
    assert event.signal == -1
    assert event.next_open == 100.0
    assert event.selected_strategy == "donor_short"
    assert event.risk_percent == 0.85
    assert event.position_ttl_bars == 32
    assert event.trail_activation_rrr == 1.0


def test_check_data_freshness_accepts_timezone_aware_open_time() -> None:
    runner = LiveSignalRunner.__new__(LiveSignalRunner)
    runner._store = _FakeStore(pd.DataFrame({"open_time": [pd.Timestamp(datetime.now(tz=UTC))]}))

    assert runner._check_data_freshness("SOL-USDT-SWAP")


def test_timestamp_to_utc_parses_string_timestamp() -> None:
    assert _timestamp_to_utc("2026-06-27T10:00:00Z") == datetime(
        2026,
        6,
        27,
        10,
        tzinfo=UTC,
    )


def test_timestamp_to_utc_rejects_unparseable_timestamp() -> None:
    with pytest.raises(ValueError, match="cannot parse timestamp"):
        _timestamp_to_utc(object())


@pytest.mark.asyncio
async def test_websocket_continuity_gap_is_repaired_before_signal_generation() -> None:
    runner = LiveSignalRunner.__new__(LiveSignalRunner)
    store = _MutableFakeStore(
        {
            Timeframe.H1: pd.DataFrame(
                {
                    "open_time": pd.to_datetime(
                        [
                            "2026-07-13T22:00:00Z",
                            "2026-07-14T00:00:00Z",
                        ],
                        utc=True,
                    )
                }
            )
        }
    )
    runner._store = store
    repaired: list[Timeframe] = []

    async def repair(_symbol: str, timeframe: Timeframe) -> None:
        repaired.append(timeframe)
        store.save_candles(
            [
                Candle(
                    symbol="SOL-USDT-SWAP",
                    timeframe=Timeframe.H1,
                    open_time=datetime(2026, 7, 13, 23, tzinfo=UTC),
                    o=Decimal("74.48"),
                    h=Decimal("75.00"),
                    low=Decimal("74.20"),
                    c=Decimal("74.95"),
                    volume=Decimal("1"),
                    closed=True,
                )
            ]
        )

    runner._refresh_timeframe = repair

    await runner._validate_or_repair_continuity("SOL-USDT-SWAP", Timeframe.H1)

    assert repaired == [Timeframe.H1]


@pytest.mark.asyncio
async def test_websocket_boundary_next_open_survives_rest_repair() -> None:
    runner = LiveSignalRunner.__new__(LiveSignalRunner)
    store = _MutableFakeStore(
        {
            Timeframe.H1: pd.DataFrame(
                {"open_time": pd.to_datetime(["2026-07-15T04:00:00Z"], utc=True)}
            ),
            Timeframe.H4: pd.DataFrame(
                {"open_time": pd.to_datetime(["2026-07-15T04:00:00Z"], utc=True)}
            ),
            Timeframe.D1: pd.DataFrame(
                {"open_time": pd.to_datetime(["2026-07-15T00:00:00Z"], utc=True)}
            ),
        }
    )
    runner._store = store
    runner._next_open_by_symbol = {}

    async def repair(_symbol: str, timeframe: Timeframe) -> None:
        if timeframe is not Timeframe.H1:
            return
        store.save_candles(
            [
                Candle(
                    symbol="SOL-USDT-SWAP",
                    timeframe=Timeframe.H1,
                    open_time=datetime(2026, 7, 15, hour, tzinfo=UTC),
                    o=Decimal("77.00"),
                    h=Decimal("77.50"),
                    low=Decimal("76.80"),
                    c=Decimal("77.10"),
                    volume=Decimal("1"),
                    closed=True,
                )
                for hour in range(5, 10)
            ]
        )
        runner._next_open_by_symbol["SOL-USDT-SWAP"] = (
            datetime(2026, 7, 15, 10, tzinfo=UTC),
            77.10,
        )

    runner._refresh_timeframe = repair
    boundary = H1Boundary(
        symbol="SOL-USDT-SWAP",
        boundary_time=datetime(2026, 7, 15, 11, tzinfo=UTC),
        closed_candles=[
            Candle(
                symbol="SOL-USDT-SWAP",
                timeframe=Timeframe.H1,
                open_time=datetime(2026, 7, 15, 10, tzinfo=UTC),
                o=Decimal("77.10"),
                h=Decimal("77.40"),
                low=Decimal("76.90"),
                c=Decimal("77.33"),
                volume=Decimal("1"),
                closed=True,
            )
        ],
        next_open=77.33,
    )

    await runner.refresh_candles("SOL-USDT-SWAP", boundary)

    assert runner._next_open_by_symbol["SOL-USDT-SWAP"] == (
        datetime(2026, 7, 15, 11, tzinfo=UTC),
        77.33,
    )


@pytest.mark.asyncio
async def test_empty_higher_timeframe_refresh_keeps_existing_history() -> None:
    runner = LiveSignalRunner.__new__(LiveSignalRunner)
    runner._store = _MutableFakeStore(
        {
            Timeframe.D1: pd.DataFrame(
                {"open_time": pd.to_datetime(["2026-07-13T00:00:00Z"], utc=True)}
            )
        }
    )
    runner._okx = _EmptyOkx()

    await runner._refresh_timeframe("SOL-USDT-SWAP", Timeframe.D1)
