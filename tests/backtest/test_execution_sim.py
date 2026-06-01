"""Tests for src/crypt/backtest/execution_sim.py."""

from __future__ import annotations

import pandas as pd

from crypt.backtest.execution_sim import ExecutionSim


def test_multi_symbol_next_open_is_symbol_local() -> None:
    """Same-timestamp rows must not use another symbol's price as next_open."""
    idx = pd.to_datetime(
        [
            "2025-01-01 00:00Z",
            "2025-01-01 00:00Z",
            "2025-01-01 04:00Z",
            "2025-01-01 04:00Z",
            "2025-01-01 08:00Z",
            "2025-01-01 08:00Z",
        ],
        utc=True,
    )
    df = pd.DataFrame(
        [
            {
                "symbol": "SOL-USDT-SWAP",
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.0,
                "signal": 1,
                "sl_price": 95.0,
            },
            {
                "symbol": "TON-USDT-SWAP",
                "open": 5.0,
                "high": 5.1,
                "low": 4.9,
                "close": 5.0,
                "signal": 0,
                "sl_price": 5.0,
            },
            {
                "symbol": "SOL-USDT-SWAP",
                "open": 102.0,
                "high": 103.0,
                "low": 101.0,
                "close": 102.0,
                "signal": 0,
                "sl_price": 102.0,
            },
            {
                "symbol": "TON-USDT-SWAP",
                "open": 5.2,
                "high": 5.3,
                "low": 5.1,
                "close": 5.2,
                "signal": 0,
                "sl_price": 5.2,
            },
            {
                "symbol": "SOL-USDT-SWAP",
                "open": 104.0,
                "high": 105.0,
                "low": 103.0,
                "close": 104.0,
                "signal": 0,
                "sl_price": 104.0,
            },
            {
                "symbol": "TON-USDT-SWAP",
                "open": 5.4,
                "high": 5.5,
                "low": 5.3,
                "close": 5.4,
                "signal": 0,
                "sl_price": 5.4,
            },
        ],
        index=idx,
    )

    sim = ExecutionSim(
        initial_capital=10_000.0,
        taker_fee=0.0,
        maker_fee=0.0,
        risk_percent=1.0,
        rrr=2.0,
        max_allowed_leverage=100.0,
        position_ttl_bars=1,
    )

    trades = sim.run(df)

    assert not trades.empty
    assert trades.iloc[0]["symbol"] == "SOL-USDT-SWAP"
    assert float(trades.iloc[0]["entry_price"]) == 102.0
    assert float(trades.iloc[0]["sl_price"]) == 95.0
