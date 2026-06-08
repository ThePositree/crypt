from __future__ import annotations

import pandas as pd

from backtester.data_contracts import StrategyData
from backtester.execution_context import (
    EXECUTION_CONTEXT_METADATA_KEY,
    attach_execution_context,
    execution_context_from_run_kwargs,
    read_execution_context,
)


def test_execution_context_from_run_kwargs_defaults_to_sl_rrr():
    ctx = execution_context_from_run_kwargs()
    assert ctx.exit_geometry == "sl_rrr"
    assert ctx.skips_structural_entry_gate is False


def test_tp_pct_context_skips_structural_entry_gate():
    ctx = execution_context_from_run_kwargs(
        exit_geometry="tp_pct",
        tp_move_pct=0.008,
        structural_sl_mode="ignore",
    )
    assert ctx.skips_structural_entry_gate is True


def test_attach_execution_context_round_trips_on_strategy_data():
    primary = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        }
    )
    data = StrategyData(
        primary=primary,
        candles={},
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )
    ctx = execution_context_from_run_kwargs(exit_geometry="tp_pct", tp_move_pct=0.01)
    attached = attach_execution_context(data, ctx)
    loaded = read_execution_context(attached)
    assert loaded is not None
    assert loaded.exit_geometry == "tp_pct"
    assert loaded.tp_move_pct == 0.01


def test_attach_execution_context_on_dataframe_uses_attrs():
    frame = pd.DataFrame({"close": [1.0]})
    ctx = execution_context_from_run_kwargs(exit_geometry="tp_pct")
    attached = attach_execution_context(frame, ctx)
    assert attached.attrs[EXECUTION_CONTEXT_METADATA_KEY].exit_geometry == "tp_pct"
