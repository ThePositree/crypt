from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.cli_runner import (
    StrategyConfig,
    dss_candidate_candle_timeframe,
    strategy_config_candle_timeframe,
)


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
