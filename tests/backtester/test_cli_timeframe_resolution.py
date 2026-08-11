from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.cli_runner import (
    StrategyConfig,
    dss_candidate_candle_timeframe,
    strategy_config_candle_timeframe,
)
from backtester.router_runtime import ArchivedStrategySpec
from backtester.strategies.filtered_donor_portfolio import _event_from_signal_row


def test_backtester_cli_exposes_only_current_product_commands() -> None:
    assert set(cli.commands) == {
        "run",
        "optimize",
        "search-signals",
        "search-signals-matrix",
    }


def test_run_and_optimize_hide_candle_timeframe_option() -> None:
    runner = CliRunner()

    run_result = runner.invoke(cli, ["run", "--help"])
    optimize_result = runner.invoke(cli, ["optimize", "--help"])

    assert run_result.exit_code == 0
    assert optimize_result.exit_code == 0
    assert "--candle-timeframe" not in run_result.output
    assert "--candle-timeframe" not in optimize_result.output


def test_run_and_optimize_expose_compact_owner_defaults() -> None:
    runner = CliRunner()

    run_result = runner.invoke(cli, ["run", "--help"])
    optimize_result = runner.invoke(cli, ["optimize", "--help"])

    assert run_result.exit_code == 0
    assert optimize_result.exit_code == 0
    assert "--data-source" not in run_result.output
    assert "--data-source" not in optimize_result.output
    assert "--data-dir TEXT" in run_result.output
    assert "[default: data]" in run_result.output
    assert "--symbol TEXT" in run_result.output
    assert "[default: SOL-USDT-SWAP]" in run_result.output
    assert "--trials INTEGER" in optimize_result.output
    assert "[default: 50000]" in optimize_result.output


def test_strategy_config_candle_timeframe_uses_dss_trigger_instance() -> None:
    cfg = StrategyConfig(
        name="dss_strategy",
        version="test",
        params={"trigger_instance": {"name": "pt_ema_cross", "timeframe": "H4"}},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "4h"


def test_strategy_config_candle_timeframe_uses_legacy_trigger_timeframe() -> None:
    cfg = StrategyConfig(
        name="dss_strategy",
        version="test",
        params={"trigger_timeframe": "15m"},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "15m"


def test_strategy_config_candle_timeframe_defaults_legacy_configs_to_h1() -> None:
    cfg = StrategyConfig(
        name="dss_strategy",
        version="test",
        params={"trigger_name": "pt_double_bottom_sweep"},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "1h"


def test_strategy_config_candle_timeframe_uses_fastest_portfolio_donor(
    tmp_path: Path,
) -> None:
    h1 = tmp_path / "h1.json"
    h1.write_text(
        json.dumps(
            {
                "name": "dss_strategy",
                "version": "test",
                "params": {"trigger_instance": {"name": "pt_ema_cross", "timeframe": "H1"}},
            }
        ),
        encoding="utf-8",
    )
    m15 = tmp_path / "m15.json"
    m15.write_text(
        json.dumps(
            {
                "name": "dss_strategy",
                "version": "test",
                "params": {"trigger_instance": {"name": "pt_ema_cross", "timeframe": "15m"}},
            }
        ),
        encoding="utf-8",
    )
    cfg = StrategyConfig(
        name="filtered_donor_portfolio",
        version="test",
        params={"strategy_paths": {"h1": str(h1), "m15": str(m15)}},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "15m"


def test_strategy_config_candle_timeframe_prefers_explicit_portfolio_timeframe(
    tmp_path: Path,
) -> None:
    h4 = tmp_path / "h4.json"
    h4.write_text(
        json.dumps(
            {
                "name": "dss_strategy",
                "version": "test",
                "params": {"trigger_instance": {"name": "pt_ema_cross", "timeframe": "H4"}},
            }
        ),
        encoding="utf-8",
    )
    cfg = StrategyConfig(
        name="filtered_donor_portfolio",
        version="test",
        params={"candle_timeframe": "H1", "strategy_paths": {"h4": str(h4)}},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "1h"


def test_strategy_config_candle_timeframe_uses_only_portfolio_donors(
    tmp_path: Path,
) -> None:
    h4 = tmp_path / "h4.json"
    h4.write_text(
        json.dumps(
            {
                "name": "dss_strategy",
                "version": "test",
                "params": {"trigger_instance": {"name": "pt_ema_cross", "timeframe": "H4"}},
            }
        ),
        encoding="utf-8",
    )
    cfg = StrategyConfig(
        name="filtered_donor_portfolio",
        version="test",
        params={"strategy_paths": {"h4": str(h4)}},
        backtest_args={},
    )

    assert strategy_config_candle_timeframe(cfg) == "4h"


def test_filtered_donor_event_preserves_ttl_minutes() -> None:
    spec = ArchivedStrategySpec(
        strategy_id="h4_candidate",
        name="dss_strategy",
        params={},
        execution=SimpleNamespace(
            risk_percent=0.25,
            rrr=8.5,
            ttl=32,
            ttl_minutes=7_560,
            trail_activation_rrr=0.0,
            trail_distance_atr=0.0,
            exit_geometry="sl_rrr",
            tp_move_pct=None,
            structural_sl_mode="cap",
            min_tp_move_pct=0.004,
        ),
    )
    row = pd.Series({"signal": -1, "sl_price": 120.0})

    event = _event_from_signal_row(row, spec)

    assert event["position_ttl_bars"] == 32
    assert event["position_ttl_minutes"] == 7_560


def test_dss_candidate_candle_timeframe_rejects_missing_timeframe(tmp_path: Path) -> None:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps({"name": "dss_strategy", "params": {"trigger_name": "pt_ema_cross"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="has no trigger timeframe"):
        dss_candidate_candle_timeframe(path)


def test_dss_candidate_candle_timeframe_reads_trigger_name_suffix(tmp_path: Path) -> None:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps({"name": "dss_strategy", "params": {"trigger_name": "pt_ema_cross@H1"}}),
        encoding="utf-8",
    )

    assert dss_candidate_candle_timeframe(path) == "1h"
