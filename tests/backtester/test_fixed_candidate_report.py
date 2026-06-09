from __future__ import annotations

from dataclasses import replace
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
    _trades_touching_window,
    parse_float_values,
    parse_int_values,
    parse_signal_quality_window_specs,
    parse_window_spec,
    run_execution_grid_comparison,
    run_fixed_candidate_comparison,
    summarize_fixed_candidate_run,
    summarize_signal_quality_groups,
    summarize_signal_quality_setup_attribution,
    summarize_signal_quality_window,
)


def _candidate_params() -> FixedCandidateParams:
    return FixedCandidateParams(
        capital=10000.0,
        risk_percent=1.0,
        rrr=1.25,
        trail_activation_rrr=0.0,
        trail_distance_atr=0.0,
        ttl=36,
        maker_fee=0.0002,
        taker_fee=0.0005,
        max_positions=0,
        max_allowed_leverage=25.0,
        max_allowed_margin=1.0,
        risk_base_period="monthly",
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


def test_signal_quality_default_windows_include_sol_and_ton_q1_q2_slice():
    windows = parse_signal_quality_window_specs(())

    assert [window.label for window in windows] == [
        "sol_2025_01",
        "sol_2025_02",
        "sol_2025_03",
        "ton_2025_01",
        "ton_2025_02",
        "ton_2025_03",
        "ton_2025_04",
    ]


def test_summarize_fixed_candidate_run_counts_sides_signals_and_exits():
    trades = pd.DataFrame(
        {
            "is_long": [True, False, False],
            "pnl_abs": [120.25, -50.0, 30.0],
            "exit_reason": ["take_profit", "stop_loss", "ttl_expired"],
            "locked_margin": [100.0, 200.0, 150.0],
            "available_balance_before": [10000.0, 9900.0, 9700.0],
            "open_positions_before": [0, 1, 2],
            "total_locked_margin_before": [0.0, 100.0, 300.0],
            "total_locked_margin_after_entry": [100.0, 300.0, 450.0],
            "capital_before": [10000.0, 10000.0, 9900.0],
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
    assert summary["max_positions"] == 0
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
    assert summary["peak_open_positions"] == 3
    assert summary["peak_locked_margin"] == 450.0
    assert summary["peak_locked_margin_pct_initial"] == 4.5
    assert summary["peak_locked_margin_pct_capital"] == pytest.approx(4.55)
    assert summary["min_available_balance_before"] == 9700.0


def test_signal_quality_summaries_attribute_trades_by_diagnostic_groups(tmp_path):
    window = WindowSpec(
        label="sol_mar",
        symbol="SOL-USDT-SWAP",
        start="2025-03-01",
        end="2025-04-01",
    )
    signals = pd.DataFrame(
        {
            "signal": [1, -1, 0],
            "setup_direction": ["BUY", "SELL", "HOLD"],
            "context_bias": ["bullish", "bearish", "neutral"],
            "trigger_type": ["1h_candle_confirm", "1h_candle_confirm", "setup_neutral"],
            "sl_anchor_type": ["pivot", "order_block", "none"],
            "sl_source_tf": ["1h", "4h", "4h"],
            "signal_filter_reason": [None, "anchor_too_old:80.00h", None],
            "confidence": [45, 65, 0],
        }
    )
    trades = pd.DataFrame(
        {
            "is_long": [True, False],
            "pnl_abs": [120.0, -80.0],
            "exit_reason": ["take_profit", "stop_loss"],
            "signal_time": [
                "2025-03-10T10:00:00+00:00",
                "2025-03-11T10:00:00+00:00",
            ],
            "entry_time": [
                "2025-03-10T11:00:00+00:00",
                "2025-03-11T11:00:00+00:00",
            ],
            "sl_anchor_known_at": [
                "2025-03-10T08:00:00+00:00",
                "2025-03-07T00:00:00+00:00",
            ],
            "confidence": [45, 65],
            "sl_anchor_type": ["pivot", "order_block"],
            "sl_source_tf": ["1h", "4h"],
            "context_bias": ["bearish", "bullish"],
            "setup_direction": ["BUY", "SELL"],
            "trigger_type": ["1h_candle_confirm", "1h_candle_confirm"],
            "signal_filter_reason": [None, "anchor_too_old:106.00h"],
        }
    )

    summary = summarize_signal_quality_window(
        index=0,
        window=window,
        params=_candidate_params(),
        metrics={
            "total_return_pct": 0.4,
            "profit_factor": 1.2,
            "max_drawdown": -1.0,
            "total_trades": 2,
        },
        signals=signals,
        trades=trades,
        run_dir=tmp_path,
    )
    groups = summarize_signal_quality_groups(
        window=window,
        params=_candidate_params(),
        trades=trades,
        run_dir=tmp_path,
    )

    assert summary["signal_long"] == 1
    assert summary["signal_short"] == 1
    assert summary["signal_neutral"] == 1
    assert summary["stale_anchor_trades"] == 1
    assert summary["reversal_marker_trades"] == 2
    assert summary["anchor_pivot"] == 1
    assert summary["filter_anchor_too_old_80.00h"] == 1

    by_anchor_age = groups[
        (groups["dimension"] == "anchor_age_bucket") & (groups["group"] == "old_72h_plus")
    ].iloc[0]
    assert by_anchor_age["trades"] == 1
    assert by_anchor_age["pnl_sum"] == -80.0

    by_reversal = groups[
        (groups["dimension"] == "reversal_marker") & (groups["group"] == "True")
    ].iloc[0]
    assert by_reversal["trades"] == 2
    assert by_reversal["pnl_sum"] == 40.0


def test_signal_quality_setup_attribution_groups_rejected_and_executed_rows(tmp_path):
    window = WindowSpec(
        label="sol_mar",
        symbol="SOL-USDT-SWAP",
        start="2025-03-01",
        end="2025-04-01",
    )
    signals = pd.DataFrame(
        {
            "tick_time": [
                "2025-03-10T11:00:00+00:00",
                "2025-03-10T12:00:00+00:00",
                "2025-03-10T13:00:00+00:00",
            ],
            "signal": [-1, 0, 0],
            "setup_snapshot_time": [
                "2025-03-10T08:00:00+00:00",
                "2025-03-10T08:00:00+00:00",
                "2025-03-10T12:00:00+00:00",
            ],
            "setup_direction": ["SELL", "SELL", "HOLD"],
            "context_bias": ["bearish", "bearish", "neutral"],
            "trigger_type": [
                "1h_candle_confirm",
                "trigger_rejected",
                "setup_neutral",
            ],
            "sl_anchor_type": ["pivot", "none", "none"],
            "sl_source_tf": ["1h", "4h", "4h"],
            "sl_distance_atr": [1.5, 0.0, 0.0],
            "sl_anchor_known_at": [
                "2025-03-10T10:00:00+00:00",
                None,
                None,
            ],
            "signal_filter_reason": [None, None, None],
        }
    )
    trades = pd.DataFrame(
        {
            "signal_time": ["2025-03-10T11:00:00+00:00"],
            "pnl_abs": [75.0],
        }
    )

    attribution = summarize_signal_quality_setup_attribution(
        window=window,
        params=_candidate_params(),
        signals=signals,
        trades=trades,
        run_dir=tmp_path,
    )

    setup_snapshot = attribution[
        (attribution["dimension"] == "setup_snapshot_group")
        & (attribution["group"] == "2025-03-10T08:00:00Z")
    ].iloc[0]
    assert setup_snapshot["setup_rows"] == 2
    assert setup_snapshot["tradeable_signals"] == 1
    assert setup_snapshot["rejected_setup_rows"] == 1
    assert setup_snapshot["sell_setup_rows"] == 2
    assert setup_snapshot["short_signals"] == 1
    assert setup_snapshot["trigger_rejected_rows"] == 1
    assert setup_snapshot["executed_trades"] == 1
    assert setup_snapshot["pnl_sum"] == 75.0

    rejected = attribution[
        (attribution["dimension"] == "trigger_type") & (attribution["group"] == "trigger_rejected")
    ].iloc[0]
    assert rejected["setup_rows"] == 1
    assert rejected["rejected_setup_rows"] == 1
    assert rejected["executed_trades"] == 0

    outcome = attribution[
        (attribution["dimension"] == "realized_outcome") & (attribution["group"] == "win")
    ].iloc[0]
    assert outcome["executed_trades"] == 1
    assert outcome["win_rate"] == 1.0


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
        (
            0,
            window,
            _params_with_execution_values(base_params, rrr=1.0, ttl=3, max_positions=1),
        ),
        (
            1,
            window,
            _params_with_execution_values(
                base_params,
                rrr=1.25,
                ttl=6,
                max_positions=3,
            ),
        ),
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
    assert [row["max_positions"] for _, row in rows] == [1, 3]
    assert [row["signal_long"] for _, row in rows] == [1, 1]


def test_execution_grid_writes_partial_summary_when_window_fails(
    monkeypatch,
    tmp_path,
):
    windows = [
        WindowSpec(
            label="ok_window",
            symbol="SOL-USDT-SWAP",
            start="2025-01-01",
            end="2025-02-01",
        ),
        WindowSpec(
            label="missing_window",
            symbol="SOL-USDT-SWAP",
            start="2025-05-01",
            end="2025-06-01",
        ),
    ]

    def fake_run_window(*, tasks, **_kwargs):
        _, window, _params = tasks[0]
        if window.label == "missing_window":
            raise ValueError("Failed to load data for missing_window")
        return [
            (
                index,
                {
                    "label": window.label,
                    "symbol": window.symbol,
                    "from": window.start,
                    "to": window.end,
                    "rrr": params.rrr,
                    "ttl": params.ttl,
                    "max_positions": params.max_positions,
                    "risk_percent": params.risk_percent,
                    "total_return_pct": 1.23,
                    "profit_factor": 1.1,
                    "max_drawdown": -2.0,
                    "total_trades": 3,
                    "long_trades": 1,
                    "short_trades": 2,
                    "long_pnl": 10.0,
                    "short_pnl": 113.0,
                    "signal_long": 1,
                    "signal_short": 2,
                    "signal_neutral": 0,
                    "setup_buy": 1,
                    "setup_sell": 2,
                    "setup_neutral": 0,
                    "exit_take_profit": 2,
                    "exit_stop_loss": 1,
                    "exit_ttl_expired": 0,
                    "run_dir": str(tmp_path / "runs" / window.label),
                },
            )
            for index, window, params in tasks
        ]

    monkeypatch.setattr(
        "backtester.fixed_candidate_report._run_execution_grid_window_precomputed",
        fake_run_window,
    )

    summary = run_execution_grid_comparison(
        windows=windows,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        base_params=_candidate_params(),
        rrr_values=[1.0],
        ttl_values=[30],
        trail_activation_rrr_values=[0.0],
        trail_distance_atr_values=[0.0],
        max_positions_values=[1, 3],
        data_dir="/unused",
        primary_timeframe="1h",
        output_folder=str(tmp_path),
        jobs=1,
        logger=__import__("logging").getLogger("test"),
    )

    assert summary["label"].tolist() == ["ok_window", "ok_window"]
    assert summary["max_positions"].tolist() == [1, 3]
    assert (tmp_path / "grid.csv").exists()
    assert (tmp_path / "grid.md").exists()

    errors = pd.read_csv(tmp_path / "grid_errors.csv")
    assert errors["label"].tolist() == ["missing_window"]
    assert errors["error_type"].tolist() == ["ValueError"]
    assert "Failed to load data" in errors["error"].iloc[0]
    assert (tmp_path / "grid_errors.md").exists()


def test_fixed_candidate_comparison_exports_mandate_report(monkeypatch, tmp_path):
    windows = [
        WindowSpec(
            label="jan",
            symbol="SOL-USDT-SWAP",
            start="2025-01-01",
            end="2025-02-01",
        ),
        WindowSpec(
            label="feb",
            symbol="SOL-USDT-SWAP",
            start="2025-02-01",
            end="2025-03-01",
        ),
    ]

    def fake_run_window(*, index, window, run_dir, **_kwargs):
        run_dir.mkdir(parents=True, exist_ok=True)
        pnl = 1600.0 if window.label == "jan" else -500.0
        pd.DataFrame(
            {
                "exit_time": [f"{window.start}T12:00:00+00:00"],
                "pnl_abs": [pnl],
                "exit_reason": ["take_profit" if pnl > 0 else "stop_loss"],
            }
        ).to_csv(run_dir / "trades.csv", index=False)
        return (
            index,
            {
                "label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "rrr": 1.25,
                "trail_activation_rrr": 0.0,
                "trail_distance_atr": 0.0,
                "ttl": 36,
                "max_positions": 1,
                "risk_percent": 1.0,
                "total_return_pct": pnl / 100.0,
                "profit_factor": 1.0,
                "max_drawdown": 0.0,
                "total_trades": 1,
                "run_dir": str(run_dir),
            },
        )

    monkeypatch.setattr(
        "backtester.fixed_candidate_report._run_fixed_candidate_window",
        fake_run_window,
    )

    run_fixed_candidate_comparison(
        windows=windows,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        params=_candidate_params(),
        data_dir="/unused",
        primary_timeframe="1h",
        output_folder=str(tmp_path),
        jobs=1,
        logger=__import__("logging").getLogger("test"),
    )

    monthly = pd.read_csv(tmp_path / "monthly_mandate.csv")
    summary = pd.read_csv(tmp_path / "mandate_summary.csv")

    assert monthly["month"].tolist() == ["2025-01", "2025-02"]
    assert monthly["symbol"].tolist() == ["SOL-USDT-SWAP", "SOL-USDT-SWAP"]
    assert monthly["raw_monthly_return_pct"].tolist() == [16.0, -5.0]
    assert monthly["stop_loss_count"].tolist() == [0, 1]
    assert summary["symbol"].tolist() == ["SOL-USDT-SWAP"]
    assert summary.loc[0, "verdict"] == "full_optuna"
    assert (tmp_path / "mandate_summary.md").exists()


def test_fixed_candidate_mandate_report_evaluates_symbols_separately(
    monkeypatch,
    tmp_path,
):
    windows = [
        WindowSpec(
            label="sol_jan",
            symbol="SOL-USDT-SWAP",
            start="2025-01-01",
            end="2025-02-01",
        ),
        WindowSpec(
            label="ton_jan",
            symbol="TON-USDT-SWAP",
            start="2025-01-01",
            end="2025-02-01",
        ),
    ]

    def fake_run_window(*, index, window, run_dir, **_kwargs):
        run_dir.mkdir(parents=True, exist_ok=True)
        pnl = 1600.0 if window.symbol == "SOL-USDT-SWAP" else -500.0
        pd.DataFrame(
            {
                "exit_time": [f"{window.start}T12:00:00+00:00"],
                "pnl_abs": [pnl],
                "exit_reason": ["take_profit" if pnl > 0 else "stop_loss"],
            }
        ).to_csv(run_dir / "trades.csv", index=False)
        return (
            index,
            {
                "label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "rrr": 1.25,
                "ttl": 36,
                "max_positions": 1,
                "risk_percent": 1.0,
                "total_return_pct": pnl / 100.0,
                "profit_factor": 1.0,
                "max_drawdown": 0.0,
                "total_trades": 1,
                "run_dir": str(run_dir),
            },
        )

    monkeypatch.setattr(
        "backtester.fixed_candidate_report._run_fixed_candidate_window",
        fake_run_window,
    )

    run_fixed_candidate_comparison(
        windows=windows,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        params=_candidate_params(),
        data_dir="/unused",
        primary_timeframe="1h",
        output_folder=str(tmp_path),
        jobs=1,
        logger=__import__("logging").getLogger("test"),
    )

    monthly = pd.read_csv(tmp_path / "monthly_mandate.csv")
    summary = pd.read_csv(tmp_path / "mandate_summary.csv")

    assert monthly["symbol"].tolist() == ["SOL-USDT-SWAP", "TON-USDT-SWAP"]
    assert monthly["raw_monthly_return_pct"].tolist() == [16.0, -5.0]
    assert summary["symbol"].tolist() == ["SOL-USDT-SWAP", "TON-USDT-SWAP"]
    assert summary["months_passing_floor"].tolist() == [1, 0]


def test_fixed_candidate_mandate_report_handles_empty_trades_csv(
    monkeypatch,
    tmp_path,
):
    window = WindowSpec(
        label="empty_jan",
        symbol="SOL-USDT-SWAP",
        start="2025-01-01",
        end="2025-02-01",
    )

    def fake_run_window(*, index, run_dir, **_kwargs):
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "trades.csv").write_text("")
        return (
            index,
            {
                "label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "rrr": 1.25,
                "ttl": 36,
                "max_positions": 1,
                "risk_percent": 1.0,
                "total_return_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "run_dir": str(run_dir),
            },
        )

    monkeypatch.setattr(
        "backtester.fixed_candidate_report._run_fixed_candidate_window",
        fake_run_window,
    )

    run_fixed_candidate_comparison(
        windows=[window],
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        params=_candidate_params(),
        data_dir="/unused",
        primary_timeframe="1h",
        output_folder=str(tmp_path),
        jobs=1,
        logger=__import__("logging").getLogger("test"),
    )

    monthly = pd.read_csv(tmp_path / "monthly_mandate.csv")

    assert monthly.loc[0, "symbol"] == "SOL-USDT-SWAP"
    assert monthly.loc[0, "trade_count"] == 0
    assert monthly.loc[0, "raw_monthly_return_pct"] == 0.0


def test_trades_touching_window_includes_cross_month_entries_and_exits():
    trades = pd.DataFrame(
        {
            "entry_time": [
                "2025-01-15T00:00:00+00:00",
                "2025-02-20T00:00:00+00:00",
            ],
            "exit_time": [
                "2025-02-05T00:00:00+00:00",
                pd.NA,
            ],
            "exit_reason": ["take_profit", "open"],
            "pnl_abs": [100.0, pd.NA],
        }
    )

    jan = _trades_touching_window(trades, start="2025-01-01", end="2025-02-01")
    feb = _trades_touching_window(trades, start="2025-02-01", end="2025-03-01")

    assert len(jan) == 1
    assert jan.iloc[0]["exit_reason"] == "take_profit"
    assert len(feb) == 2
    assert set(feb["exit_reason"]) == {"take_profit", "open"}


def test_continuous_fixed_candidate_derives_monthly_rows_from_single_run(
    monkeypatch,
    tmp_path,
):
    windows = [
        WindowSpec(
            label="jan",
            symbol="SOL-USDT-SWAP",
            start="2025-01-01",
            end="2025-02-01",
        ),
        WindowSpec(
            label="feb",
            symbol="SOL-USDT-SWAP",
            start="2025-02-01",
            end="2025-03-01",
        ),
        WindowSpec(
            label="mar",
            symbol="SOL-USDT-SWAP",
            start="2025-03-01",
            end="2025-04-01",
        ),
    ]
    run_calls: list[str] = []

    def fake_run_window(*, index, window, run_dir, **_kwargs):
        run_calls.append(window.label)
        run_dir.mkdir(parents=True, exist_ok=True)
        if not window.label.endswith("_continuous"):
            raise AssertionError(f"continuous mode must not run isolated window {window.label}")

        trades = pd.DataFrame(
            {
                "entry_time": [
                    "2025-01-15T00:00:00+00:00",
                    "2025-02-20T00:00:00+00:00",
                ],
                "exit_time": [
                    "2025-02-05T00:00:00+00:00",
                    pd.NA,
                ],
                "exit_reason": ["take_profit", "open"],
                "pnl_abs": [1600.0, pd.NA],
                "is_long": [True, True],
                "locked_margin": [100.0, 120.0],
                "available_balance_before": [10000.0, 11600.0],
                "open_positions_before": [0, 0],
                "total_locked_margin_before": [0.0, 0.0],
                "total_locked_margin_after_entry": [100.0, 120.0],
                "capital_before": [10000.0, 11600.0],
                "capital_after": [11600.0, pd.NA],
                "holding_bars": [21, pd.NA],
            }
        )
        trades.to_csv(run_dir / "trades.csv", index=False)
        pd.DataFrame({"signal": [1, -1]}).to_csv(run_dir / "signals.csv")

        return (
            index,
            {
                "label": window.label,
                "symbol": window.symbol,
                "from": window.start,
                "to": window.end,
                "rrr": 1.25,
                "ttl": 0,
                "max_positions": 1,
                "risk_percent": 1.0,
                "total_return_pct": 16.0,
                "profit_factor": 1.0,
                "max_drawdown": 0.0,
                "total_trades": 2,
                "run_dir": str(run_dir),
            },
        )

    monkeypatch.setattr(
        "backtester.fixed_candidate_report._run_fixed_candidate_window",
        fake_run_window,
    )

    summary = run_fixed_candidate_comparison(
        windows=windows,
        cfg=StrategyConfig(
            name="dummy",
            version="test",
            params={},
            backtest_args={},
        ),
        params=replace(_candidate_params(), ttl=0),
        data_dir="/unused",
        primary_timeframe="1h",
        output_folder=str(tmp_path),
        jobs=1,
        logger=__import__("logging").getLogger("test"),
        continuous=True,
    )

    assert run_calls == ["sol_continuous"]
    assert summary["label"].tolist() == ["jan", "feb", "mar"]
    assert (summary["execution_mode"] == "continuous_derived").all()
    continuous_dir = str(tmp_path / "runs" / "sol_continuous")
    assert (summary["continuous_run_dir"] == continuous_dir).all()
    assert (tmp_path / "runs" / "sol_continuous" / "continuous_summary.json").exists()

    monthly = pd.read_csv(tmp_path / "monthly_mandate.csv")
    assert monthly["month"].tolist() == ["2025-01", "2025-02", "2025-03"]
    assert monthly["trade_count"].tolist() == [1, 1, 0]
    assert monthly.loc[monthly["month"] == "2025-02", "raw_monthly_return_pct"].iloc[0] == 16.0
    assert monthly.loc[monthly["month"] == "2025-01", "raw_monthly_return_pct"].iloc[0] == 0.0
    assert monthly.loc[monthly["month"] == "2025-03", "raw_monthly_return_pct"].iloc[0] == 0.0
