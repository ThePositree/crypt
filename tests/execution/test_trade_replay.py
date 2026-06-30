from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from crypt.execution.position_state import LivePosition
from crypt.execution.trade_replay import replay_position


def test_replay_uses_actual_legacy_fixed_protection() -> None:
    pos = LivePosition.create(
        symbol="SOL-USDT-SWAP",
        signal_time=datetime(2026, 6, 29, 11, tzinfo=UTC),
        entry_time=datetime(2026, 6, 29, 12, tzinfo=UTC),
        entry_price=100.0,
        sl_price=98.0,
        tp_price=102.0,
        size=1.0,
        contracts=1.0,
        leverage=20.0,
        locked_margin=5.0,
        risk_base_capital=100.0,
        is_long=True,
        ttl_bars=16,
        entry_order_id="entry-1",
        trail_activation_rrr=1.0,
        trail_distance_atr=0.25,
    )
    pos.status = "closed"
    pos.exit_time = datetime(2026, 6, 29, 13, tzinfo=UTC).isoformat()
    pos.exit_price = 102.0
    pos.exit_reason = "take_profit"
    candles = pd.DataFrame(
        {
            "open_time": pd.to_datetime(
                ["2026-06-29T12:00:00Z", "2026-06-29T13:00:00Z"],
                utc=True,
            ),
            "o": [100.0, 102.0],
            "h": [102.1, 102.2],
            "l": [99.5, 101.5],
            "c": [102.0, 102.0],
            "volume": [1.0, 1.0],
        }
    )

    report = replay_position(pos=pos, candles=candles)

    assert report.matched
    assert report.expected_exit_reason == "take_profit"
    assert report.expected_trigger_price == 102.0
