from __future__ import annotations

import pandas as pd
import pytest

from backtester.routed_execution import (
    RoutedExecutionConfig,
    evaluate_routed_execution,
    write_routed_execution_report,
)


def test_routed_execution_drains_previous_strategy_and_scales_shared_capital() -> None:
    predictions = pd.DataFrame(
        [
            _prediction("2025-01-01", "a"),
            _prediction("2025-01-02", "b"),
        ]
    )
    trades = {
        "a": pd.DataFrame(
            [
                _trade(
                    signal="2025-01-01 01:00",
                    entry="2025-01-01 02:00",
                    exit="2025-01-02 12:00",
                    pnl=100.0,
                    margin=500.0,
                )
            ]
        ),
        "b": pd.DataFrame(
            [
                _trade(
                    signal="2025-01-02 03:00",
                    entry="2025-01-02 04:00",
                    exit="2025-01-02 08:00",
                    pnl=500.0,
                    margin=500.0,
                ),
                _trade(
                    signal="2025-01-03 03:00",
                    entry="2025-01-03 04:00",
                    exit="2025-01-03 08:00",
                    pnl=200.0,
                    margin=500.0,
                ),
            ]
        ),
    }

    result = evaluate_routed_execution(
        predictions=predictions,
        router="router_test",
        trades_by_strategy=trades,
        config=RoutedExecutionConfig(start="2025-01-01", end="2025-02-01"),
    )

    assert result.routed_trades["source_strategy"].tolist() == ["a", "b"]
    assert result.routed_trades["pnl_abs"].tolist() == [100.0, 200.0]
    assert result.execution_summary.loc[0, "final_capital"] == 10_300.0
    assert result.execution_summary.loc[0, "drain_rejections"] == 1
    assert result.execution_summary.loc[0, "max_concurrent_positions"] == 1
    assert result.mandate.monthly.loc[0, "raw_monthly_return_pct"] == 3.0


def test_routed_execution_rejects_entry_over_shared_margin_limit() -> None:
    predictions = pd.DataFrame([_prediction("2025-01-01", "a")])
    trades = {
        "a": pd.DataFrame(
            [
                _trade(
                    signal="2025-01-01 01:00",
                    entry="2025-01-01 02:00",
                    exit="2025-01-01 03:00",
                    pnl=100.0,
                    margin=6_000.0,
                )
            ]
        )
    }

    result = evaluate_routed_execution(
        predictions=predictions,
        router="router_test",
        trades_by_strategy=trades,
        config=RoutedExecutionConfig(
            start="2025-01-01",
            end="2025-02-01",
            max_allowed_margin=0.5,
        ),
    )

    assert result.routed_trades.empty
    assert result.rejected_entries.loc[0, "reason"] == "margin_limit"
    assert result.execution_summary.loc[0, "final_capital"] == 10_000.0


def test_routed_execution_rejects_cash_selection() -> None:
    predictions = pd.DataFrame([_prediction("2025-01-01", "cash")])

    with pytest.raises(ValueError, match="cash or empty"):
        evaluate_routed_execution(
            predictions=predictions,
            router="router_test",
            trades_by_strategy={"a": pd.DataFrame()},
            config=RoutedExecutionConfig(start="2025-01-01", end="2025-02-01"),
        )


def test_routed_execution_report_writes_contract(tmp_path) -> None:
    predictions = pd.DataFrame([_prediction("2025-01-01", "a")])
    trades = {
        "a": pd.DataFrame(
            [
                _trade(
                    signal="2025-01-01 01:00",
                    entry="2025-01-01 02:00",
                    exit="2025-01-01 03:00",
                    pnl=100.0,
                    margin=500.0,
                )
            ]
        )
    }
    result = evaluate_routed_execution(
        predictions=predictions,
        router="router_test",
        trades_by_strategy=trades,
        config=RoutedExecutionConfig(start="2025-01-01", end="2025-02-01"),
    )

    write_routed_execution_report(output=tmp_path, result=result)

    assert (tmp_path / "routed_trades.csv").exists()
    assert (tmp_path / "monthly_mandate.csv").exists()
    assert (tmp_path / "mandate_summary.csv").exists()
    assert "# Routed Execution Validation" in (tmp_path / "report.md").read_text()


def _prediction(asof: str, strategy: str) -> dict[str, object]:
    return {
        "router": "router_test",
        "asof": f"{asof}T00:00:00+00:00",
        "selected_strategy": strategy,
    }


def _trade(
    *,
    signal: str,
    entry: str,
    exit: str,
    pnl: float,
    margin: float,
) -> dict[str, object]:
    return {
        "signal_time": f"{signal}:00+00:00",
        "entry_time": f"{entry}:00+00:00",
        "exit_time": f"{exit}:00+00:00",
        "pnl_abs": pnl,
        "risk_base_capital": 10_000.0,
        "locked_margin": margin,
        "exit_reason": "take_profit" if pnl > 0 else "stop_loss",
    }
