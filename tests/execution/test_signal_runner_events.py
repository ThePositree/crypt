from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from crypt.execution.signal_runner import LiveSignalRunner, _events_from_row, _signal_event_from_raw
from crypt.models import Timeframe


class _FakeStore:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load_candles(self, symbol: str, timeframe: Timeframe, limit: int | None = None) -> pd.DataFrame:
        assert symbol == "SOL-USDT-SWAP"
        assert timeframe == Timeframe.H1
        return self._frame.tail(limit) if limit is not None else self._frame


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
    runner._store = _FakeStore(
        pd.DataFrame({"open_time": [pd.Timestamp(datetime.now(tz=UTC))]})
    )

    assert runner._check_data_freshness("SOL-USDT-SWAP")
