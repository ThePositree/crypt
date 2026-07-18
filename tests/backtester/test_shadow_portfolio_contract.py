from __future__ import annotations

import pandas as pd
import pytest

from backtester.cli_runner import BacktestArgs
from backtester.execution_sim import ExecutionSim
from backtester.shadow_portfolio import ShadowPortfolio


@pytest.mark.parametrize(
    ("exit_geometry", "tp_move_pct"),
    [("sl_rrr", None), ("tp_pct", 0.02)],
)
def test_incremental_shadow_execution_matches_external_simulator(
    exit_geometry: str,
    tp_move_pct: float | None,
) -> None:
    index = pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 104.0, 104.0],
            "high": [101.0, 101.0, 104.0, 105.0, 105.0],
            "low": [99.0, 99.0, 99.5, 103.0, 103.0],
            "close": [100.0, 100.0, 103.0, 104.0, 104.0],
            "volume": [1.0] * 5,
            "signal": [0, 1, 0, 0, 0],
            "sl_price": [0.0, 98.0, 0.0, 0.0, 0.0],
        },
        index=index,
    )
    args = BacktestArgs(
        capital=10_000.0,
        risk_percent=1.0,
        rrr=2.0,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        ttl=24,
        max_positions=0,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
        exit_geometry=exit_geometry,
        tp_move_pct=tp_move_pct,
        structural_sl_mode="cap",
    )
    expected = ExecutionSim(
        initial_capital=args.capital,
        taker_fee=args.taker_fee,
        maker_fee=args.maker_fee,
        risk_percent=args.risk_percent,
        rrr=args.rrr,
        max_positions=args.max_positions,
        position_ttl_bars=args.ttl,
        max_allowed_leverage=args.max_allowed_leverage,
        max_allowed_margin=args.max_allowed_margin,
        risk_base_period=args.risk_base_period,
        exit_geometry=args.exit_geometry,
        tp_move_pct=args.tp_move_pct,
        structural_sl_mode=args.structural_sl_mode,
    ).run(frame)

    shadow = ShadowPortfolio(args)
    for bar_index, (timestamp, row) in enumerate(frame.iterrows()):
        shadow.on_closed_bar(
            bar_index=bar_index,
            timestamp=timestamp,
            open_price=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            trail_atr=None,
            signal_row=row,
        )
    actual = pd.DataFrame(shadow.state.trades)

    columns = [
        "signal_time",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "pnl_abs",
        "exit_reason",
        "capital_after",
    ]
    pd.testing.assert_frame_equal(
        actual.loc[:, columns].reset_index(drop=True),
        expected.loc[expected["exit_reason"].ne("open"), columns].reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
