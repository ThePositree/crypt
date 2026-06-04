from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backtester.cli_runner import StrategyConfig
from backtester.fixed_candidate_report import (
    FixedCandidateParams,
    WindowSpec,
    _params_with_execution_values,
    _rows_in_window_order,
    _run_execution_grid_window_precomputed,
    parse_float_values,
    parse_int_values,
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


def test_parse_execution_grid_values():
    assert parse_float_values("1.0, 1.25,1.5") == [1.0, 1.25, 1.5]
    assert parse_int_values("30, 36,42") == [30, 36, 42]

    with pytest.raises(ValueError, match="float values"):
        parse_float_values("1.0,,1.5")
    with pytest.raises(ValueError, match="integer values"):
        parse_int_values("30,soon")


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


def test_rows_in_window_order_is_deterministic_for_out_of_order_workers():
    rows = _rows_in_window_order(
        [
            (2, {"label": "third"}),
            (0, {"label": "first"}),
            (1, {"label": "second"}),
        ]
    )

    assert [row["label"] for row in rows] == ["first", "second", "third"]


def test_execution_grid_window_reuses_one_signal_build(monkeypatch, tmp_path):
    index = pd.date_range("2025-03-01", periods=4, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 101.0, 101.0],
            "high": [100.0, 101.5, 102.0, 102.0],
            "low": [100.0, 99.8, 100.5, 100.5],
            "close": [100.0, 101.0, 101.0, 101.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        },
        index=index,
    )

    class DummyStrategy:
        def __init__(self):
            self.calls = 0

        def generate(self, source):
            self.calls += 1
            signals = source.copy()
            signals["signal"] = [1, 0, 0, 0]
            signals["sl_price"] = [99.0, 0.0, 0.0, 0.0]
            signals["setup_direction"] = ["BUY", "HOLD", "HOLD", "HOLD"]
            return signals

    strategy = DummyStrategy()
    monkeypatch.setattr(
        "backtester.fixed_candidate_report._load_window_data",
        lambda **_: df,
    )
    monkeypatch.setattr(
        "backtester.fixed_candidate_report.build_strategy_instance",
        lambda *_args, **_kwargs: strategy,
    )
    monkeypatch.setattr(
        "backtester.fixed_candidate_report.export_and_optional_analysis",
        lambda **_kwargs: None,
    )

    window = WindowSpec(
        label="sol_mar",
        symbol="SOL-USDT-SWAP",
        start="2025-03-01",
        end="2025-04-01",
    )
    base_params = _candidate_params()
    tasks = [
        (0, window, _params_with_execution_values(base_params, rrr=1.0, ttl=3)),
        (1, window, _params_with_execution_values(base_params, rrr=1.25, ttl=6)),
    ]

    rows = _run_execution_grid_window_precomputed(
        tasks=tasks,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        data_dir="/unused",
        primary_timeframe="1h",
        window_run_dir=tmp_path,
    )

    assert strategy.calls == 1
    assert [index for index, _ in rows] == [0, 1]
    assert [row["rrr"] for _, row in rows] == [1.0, 1.25]
    assert [row["ttl"] for _, row in rows] == [3, 6]
    assert [row["signal_long"] for _, row in rows] == [1, 1]
