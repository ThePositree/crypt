from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.cli_runner import BacktestArgs, StrategyConfig, build_backtest_args
from backtester.regime_matrix import (
    MatrixBacktestCliParams,
    MatrixStrategy,
    MatrixStrategyResult,
    aggregate_strategy_buckets,
    build_strategy_manifest,
    pivot_metric,
    results_in_strategy_order,
    run_archived_performance_matrix,
    strategy_id_from_path,
    write_strategy_trades,
)

MATRIX_CLI_DEFAULTS = {
    "capital": 10_000.0,
    "risk_percent": 1.0,
    "rrr": 2.0,
    "trail_activation_rrr": 0.0,
    "trail_distance_atr": 0.0,
    "maker_fee": 0.0002,
    "taker_fee": 0.0005,
    "ttl": 0,
    "max_positions": 0,
    "max_allowed_leverage": 25.0,
    "max_allowed_margin": 1.0,
    "risk_base_period": "monthly",
    "max_daily_profit": None,
    "max_daily_loss": None,
    "trading_begin": None,
    "trading_end": None,
    "exit_geometry": "sl_rrr",
    "tp_move_pct": None,
    "structural_sl_mode": "cap",
    "min_tp_move_pct": 0.004,
}

EXPECTED_ARCHIVE_ARGS = {
    "crypt_ensemble_h1_discovery_nr4_vwap_robust.json": {
        "risk_percent": 0.5,
        "rrr": 1.75,
        "ttl": 52,
        "trail_activation_rrr": 1.75,
        "trail_distance_atr": 0.25,
        "exit_geometry": "tp_pct",
        "tp_move_pct": 0.026,
        "structural_sl_mode": "cap",
    },
    "crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json": {
        "risk_percent": 2.0,
        "rrr": 2.25,
        "ttl": 24,
        "trail_activation_rrr": 0.0,
        "trail_distance_atr": 0.0,
        "exit_geometry": "tp_pct",
        "tp_move_pct": 0.014,
        "structural_sl_mode": "ignore",
    },
    "crypt_ensemble_h1_discovery_vwap_reclaim_robust.json": {
        "risk_percent": 2.0,
        "rrr": 2.0,
        "ttl": 24,
        "trail_activation_rrr": 0.0,
        "trail_distance_atr": 0.0,
        "exit_geometry": "tp_pct",
        "tp_move_pct": 0.016,
        "structural_sl_mode": "ignore",
    },
    "dssv2_013321_ps_macd_squeeze_recent.json": {
        "risk_percent": 1.25,
        "rrr": 2.0,
        "ttl": 56,
        "trail_activation_rrr": 2.0,
        "trail_distance_atr": 0.25,
        "exit_geometry": "sl_rrr",
        "tp_move_pct": None,
        "structural_sl_mode": "ignore",
    },
    "island_2023_021396_engulfing_bb_trend.json": {
        "risk_percent": 1.0,
        "rrr": 1.0,
        "ttl": 16,
        "trail_activation_rrr": 1.0,
        "trail_distance_atr": 0.25,
        "exit_geometry": "sl_rrr",
        "tp_move_pct": None,
        "structural_sl_mode": "cap",
    },
    "smac_003335_double_bottom_body_to_range.json": {
        "risk_percent": 0.75,
        "rrr": 1.5,
        "ttl": 116,
        "trail_activation_rrr": 1.5,
        "trail_distance_atr": 0.25,
        "exit_geometry": "sl_rrr",
        "tp_move_pct": None,
        "structural_sl_mode": "cap",
    },
}


def _args() -> BacktestArgs:
    return BacktestArgs(
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
    )


def test_archive_strategy_backtest_args_override_matrix_defaults() -> None:
    cfg = StrategyConfig(
        name="dss_strategy",
        version="archive",
        params={
            "position_ttl_bars": 24,
            "risk_percent": 1.0,
            "rrr": 1.5,
            "trail_distance_atr": 0.0,
        },
        backtest_args={
            "position_ttl_bars": 56,
            "risk_percent": 1.25,
            "rrr": 2.0,
            "trail_activation_rrr": 2.0,
            "trail_distance_atr": 0.25,
            "exit_geometry": "sl_rrr",
            "structural_sl_mode": "ignore",
        },
    )

    args = build_backtest_args(cfg, **MATRIX_CLI_DEFAULTS)

    assert args.ttl == 56
    assert args.risk_percent == 1.25
    assert args.rrr == 2.0
    assert args.trail_activation_rrr == 2.0
    assert args.trail_distance_atr == 0.25
    assert args.structural_sl_mode == "ignore"


@pytest.mark.parametrize("filename,expected", EXPECTED_ARCHIVE_ARGS.items())
def test_archive_strategy_files_resolve_expected_matrix_args(
    filename: str, expected: dict[str, object]
) -> None:
    raw = json.loads((Path("strategies/archive") / filename).read_text())
    cfg = StrategyConfig(
        name=raw["name"],
        version=raw.get("version", ""),
        params=raw.get("params", {}),
        backtest_args=raw.get("backtest_args", {}),
    )

    args = build_backtest_args(cfg, **MATRIX_CLI_DEFAULTS)

    for key, value in expected.items():
        assert getattr(args, key) == value
    assert args.risk_base_period == "monthly"
    assert args.max_positions == 0


def test_strategy_id_from_path_is_stable() -> None:
    assert strategy_id_from_path(Path("strategies/archive/Foo Bar-v1.json")) == "foo_bar_v1"


def test_build_strategy_manifest_serializes_execution_defaults() -> None:
    cfg = StrategyConfig(
        name="dss_strategy",
        version="v1",
        params={
            "trigger_name": "pt_double_bottom_sweep",
            "filter_names": ["pf_body_to_range_min"],
        },
        backtest_args={},
    )

    manifest = build_strategy_manifest(
        [
            MatrixStrategy(
                strategy_id="double_bottom",
                strategy_path=Path("strategies/archive/double_bottom.json"),
                config=cfg,
                args=_args(),
            )
        ]
    )

    row = manifest.iloc[0].to_dict()
    assert row["strategy_id"] == "double_bottom"
    assert row["trigger_name"] == "pt_double_bottom_sweep"
    assert row["filter_names"] == "pf_body_to_range_min"
    assert row["risk_percent"] == 1.0
    assert row["ttl"] == 24


def test_aggregate_strategy_buckets_outputs_monthly_metrics() -> None:
    trades = pd.DataFrame(
        [
            {
                "entry_time": pd.Timestamp("2024-01-03", tz="UTC"),
                "pnl_abs": 100.0,
                "capital_before": 10_000.0,
                "capital_after": 10_100.0,
                "is_long": True,
                "holding_bars": 3,
                "exit_reason": "take_profit",
            },
            {
                "entry_time": pd.Timestamp("2024-01-20", tz="UTC"),
                "pnl_abs": -50.0,
                "capital_before": 10_100.0,
                "capital_after": 10_050.0,
                "is_long": False,
                "holding_bars": 2,
                "exit_reason": "stop_loss",
            },
            {
                "entry_time": pd.Timestamp("2024-02-05", tz="UTC"),
                "pnl_abs": 25.0,
                "capital_before": 10_050.0,
                "capital_after": 10_075.0,
                "is_long": False,
                "holding_bars": 4,
                "exit_reason": "trailing_stop",
            },
        ]
    )

    metrics = aggregate_strategy_buckets(
        trades,
        strategy_id="s1",
        strategy_path=Path("s1.json"),
        bucket="month",
        start="2024-01-01",
        end="2024-02-29",
    )

    jan = metrics[metrics["bucket"] == "2024-01"].iloc[0]
    feb = metrics[metrics["bucket"] == "2024-02"].iloc[0]
    assert jan["trade_count"] == 2
    assert jan["pnl_abs"] == pytest.approx(50.0)
    assert jan["return_pct"] == pytest.approx(0.5)
    assert jan["win_rate"] == pytest.approx(50.0)
    assert jan["profit_factor"] == pytest.approx(2.0)
    assert jan["long_trades"] == 1
    assert jan["short_trades"] == 1
    assert jan["exit_take_profit"] == 1
    assert jan["exit_stop_loss"] == 1
    assert feb["trade_count"] == 1
    assert feb["exit_trailing_stop"] == 1


def test_pivot_metric_returns_bucket_x_strategy() -> None:
    metrics = pd.DataFrame(
        [
            {"bucket": "2024-01", "strategy_id": "a", "return_pct": 1.0},
            {"bucket": "2024-01", "strategy_id": "b", "return_pct": -2.0},
            {"bucket": "2024-02", "strategy_id": "a", "return_pct": 3.0},
            {"bucket": "2024-02", "strategy_id": "b", "return_pct": 4.0},
        ]
    )

    pivot = pivot_metric(metrics, "return_pct")

    assert pivot.to_dict("records") == [
        {"bucket": "2024-01", "a": 1.0, "b": -2.0},
        {"bucket": "2024-02", "a": 3.0, "b": 4.0},
    ]


def test_archived_performance_matrix_help() -> None:
    result = CliRunner().invoke(cli, ["archived-performance-matrix", "--help"])

    assert result.exit_code == 0
    assert "--include-archive" in result.output
    assert "--bucket" in result.output
    assert "--jobs" in result.output


def test_results_in_strategy_order_sorts_by_index() -> None:
    cfg = StrategyConfig(name="x", version="v1", params={}, backtest_args={})
    args = _args()
    ordered = results_in_strategy_order(
        [
            MatrixStrategyResult(
                index=2,
                strategy=MatrixStrategy("c", Path("c.json"), cfg, args),
                trades=pd.DataFrame(),
                bucket_metrics=pd.DataFrame(),
            ),
            MatrixStrategyResult(
                index=0,
                strategy=MatrixStrategy("a", Path("a.json"), cfg, args),
                trades=pd.DataFrame(),
                bucket_metrics=pd.DataFrame(),
            ),
            MatrixStrategyResult(
                index=1,
                strategy=MatrixStrategy("b", Path("b.json"), cfg, args),
                trades=pd.DataFrame(),
                bucket_metrics=pd.DataFrame(),
            ),
        ]
    )

    assert [item.strategy.strategy_id for item in ordered] == ["a", "b", "c"]


def test_run_archived_performance_matrix_parallel_writes_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    for path in paths:
        path.write_text("{}")

    def _fake_prepare(
        strategy_paths: list[Path],
        *,
        cli_params: MatrixBacktestCliParams,
        strategy_progress: bool,
        logger: object,
    ) -> list[object]:
        from backtester.regime_matrix import MatrixStrategyWorkItem

        _ = cli_params, strategy_progress, logger
        cfg = StrategyConfig(name="x", version="v1", params={}, backtest_args={})
        args = _args()
        return [
            MatrixStrategyWorkItem(
                index=index,
                strategy_id=strategy_id_from_path(strategy_path),
                strategy_path=strategy_path,
                config=cfg,
                args=args,
            )
            for index, strategy_path in enumerate(strategy_paths)
        ]

    def _fake_worker(
        *,
        data: object,  # noqa: ARG001
        work: object,
        bucket: str,
        start: str | None,
        end: str | None,
    ) -> MatrixStrategyResult:
        from backtester.regime_matrix import MatrixStrategyWorkItem

        assert isinstance(work, MatrixStrategyWorkItem)
        cfg = StrategyConfig(name="dss_strategy", version="v1", params={}, backtest_args={})
        args = _args()
        trades = pd.DataFrame(
            [
                {
                    "entry_time": pd.Timestamp("2024-01-03", tz="UTC"),
                    "pnl_abs": float(work.index + 1),
                    "capital_before": 10_000.0,
                    "capital_after": 10_000.0 + float(work.index + 1),
                    "is_long": True,
                    "holding_bars": 1,
                    "exit_reason": "take_profit",
                }
            ]
        )
        return MatrixStrategyResult(
            index=work.index,
            strategy=MatrixStrategy(work.strategy_id, work.strategy_path, cfg, args),
            trades=trades,
            bucket_metrics=aggregate_strategy_buckets(
                trades,
                strategy_id=work.strategy_id,
                strategy_path=work.strategy_path,
                bucket=bucket,
                start=start,
                end=end,
            ),
        )

    class _InlineFuture:
        def __init__(self, value: MatrixStrategyResult) -> None:
            self._value = value

        def result(self) -> MatrixStrategyResult:
            return self._value

    class _InlineExecutor:
        def __init__(self, max_workers: int) -> None:
            self._max_workers = max_workers

        def __enter__(self) -> _InlineExecutor:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit(self, fn: object, /, **kwargs: object) -> _InlineFuture:
            assert callable(fn)
            return _InlineFuture(fn(**kwargs))

    monkeypatch.setattr(
        "backtester.regime_matrix.prepare_matrix_work_items",
        _fake_prepare,
    )
    monkeypatch.setattr(
        "backtester.regime_matrix._run_matrix_strategy_worker",
        _fake_worker,
    )
    monkeypatch.setattr("backtester.regime_matrix.ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(
        "backtester.regime_matrix.as_completed",
        lambda futures: iter(futures),
    )
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC"),
            "open": [1.0, 1.0, 1.0],
            "high": [1.0, 1.0, 1.0],
            "low": [1.0, 1.0, 1.0],
            "close": [1.0, 1.0, 1.0],
            "volume": [1.0, 1.0, 1.0],
        }
    )
    output = tmp_path / "matrix"

    run_archived_performance_matrix(
        paths=paths,
        data=data,
        output=output,
        bucket="month",
        from_date="2024-01-01",
        to_date="2024-01-31",
        jobs=2,
        cli_params=MatrixBacktestCliParams(
            capital=10_000.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            max_allowed_leverage=25.0,
            max_allowed_margin=1.0,
        ),
        strategy_progress=False,
        logger=__import__("logging").getLogger("test"),
    )

    manifest = pd.read_csv(output / "strategy_manifest.csv")
    metrics = pd.read_csv(output / "bucket_metrics.csv")
    assert len(manifest) == 2
    assert set(manifest["strategy_id"]) == {"a", "b"}
    assert len(metrics) == 2
    assert (output / "strategy_trades" / "a.csv").exists()
    assert (output / "strategy_trades" / "b.csv").exists()


def test_write_strategy_trades_exports_csv(tmp_path: Path) -> None:
    trades = pd.DataFrame([{"pnl_abs": 10.0, "exit_time": "2024-01-01"}])

    path = write_strategy_trades(output=tmp_path, strategy_id="s1", trades=trades)

    assert path == tmp_path / "strategy_trades" / "s1.csv"
    saved = pd.read_csv(path)
    assert saved.to_dict("records") == [{"pnl_abs": 10.0, "exit_time": "2024-01-01"}]
