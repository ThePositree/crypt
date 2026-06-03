from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backtester.fixed_candidate_report import (
    FixedCandidateParams,
    WindowSpec,
    parse_window_spec,
    summarize_fixed_candidate_run,
)


def _candidate_params() -> FixedCandidateParams:
    return FixedCandidateParams(
        capital=10000.0,
        risk_percent=1.0,
        rrr=1.25,
        ttl=36,
        maker_fee=0.0002,
        taker_fee=0.0005,
        max_positions=0,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
        is_isolated_futures=False,
    )


def test_parse_window_spec_requires_label_symbol_start_end():
    assert parse_window_spec("sol_mar:SOL-USDT-SWAP:2025-03-01:2025-04-01") == (
        WindowSpec(
            label="sol_mar",
            symbol="SOL-USDT-SWAP",
            start="2025-03-01",
            end="2025-04-01",
        )
    )

    with pytest.raises(ValueError, match="label:SYMBOL"):
        parse_window_spec("SOL-USDT-SWAP:2025-03-01:2025-04-01")


def test_summarize_fixed_candidate_run_counts_sides_signals_and_exits():
    trades = pd.DataFrame(
        {
            "is_long": [True, False, False],
            "pnl_abs": [120.25, -50.0, 30.0],
            "exit_reason": ["take_profit", "stop_loss", "ttl_expired"],
        }
    )
    signals = pd.DataFrame(
        {
            "signal": [1, -1, 0, -1, 0],
            "setup_direction": ["BUY", "SELL", "HOLD", "SELL", "HOLD"],
        }
    )

    summary = summarize_fixed_candidate_run(
        window=WindowSpec(
            label="sol_mar",
            symbol="SOL-USDT-SWAP",
            start="2025-03-01",
            end="2025-04-01",
        ),
        params=_candidate_params(),
        metrics={
            "total_return_pct": 1.23,
            "profit_factor": 1.1,
            "max_drawdown": -2.5,
            "total_trades": 3,
        },
        signals=signals,
        trades=trades,
        run_dir=Path("/tmp/run"),
    )

    assert summary["total_return_pct"] == 1.23
    assert summary["long_trades"] == 1
    assert summary["short_trades"] == 2
    assert summary["long_pnl"] == 120.25
    assert summary["short_pnl"] == -20.0
    assert summary["signal_long"] == 1
    assert summary["signal_short"] == 2
    assert summary["signal_neutral"] == 2
    assert summary["setup_buy"] == 1
    assert summary["setup_sell"] == 2
    assert summary["setup_neutral"] == 2
    assert summary["exit_take_profit"] == 1
    assert summary["exit_stop_loss"] == 1
    assert summary["exit_ttl_expired"] == 1
