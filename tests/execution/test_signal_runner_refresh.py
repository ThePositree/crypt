from __future__ import annotations

from datetime import UTC

import pandas as pd

from crypt.execution.signal_runner import _refresh_since_ms
from crypt.models import Timeframe


def test_refresh_starts_at_first_internal_gap() -> None:
    stored = pd.DataFrame(
        {
            "open_time": pd.to_datetime(
                [
                    "2026-06-10T10:00:00Z",
                    "2026-06-10T11:00:00Z",
                    "2026-06-25T09:00:00Z",
                ],
                utc=True,
            )
        }
    )

    since_ms = _refresh_since_ms(stored, Timeframe.H1)

    expected = pd.Timestamp("2026-06-10T12:00:00Z").to_pydatetime().astimezone(UTC)
    assert since_ms == int(expected.timestamp() * 1000)


def test_refresh_starts_after_latest_when_history_is_continuous() -> None:
    stored = pd.DataFrame(
        {
            "open_time": pd.to_datetime(
                [
                    "2026-06-10T10:00:00Z",
                    "2026-06-10T11:00:00Z",
                ],
                utc=True,
            )
        }
    )

    since_ms = _refresh_since_ms(stored, Timeframe.H1)

    expected = pd.Timestamp("2026-06-10T12:00:00Z").to_pydatetime().astimezone(UTC)
    assert since_ms == int(expected.timestamp() * 1000)
