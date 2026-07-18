from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtester.trade_filter_research import (
    FilterSearchConfig,
    SplitConfig,
    attach_catalog_features,
    generate_candidate_rules,
    generate_pair_candidate_rules,
    prepare_trade_features,
    run_trade_filter_research,
)


def test_generate_candidate_rules_blocks_outcome_leakage() -> None:
    trades = prepare_trade_features(
        pd.DataFrame(
            {
                "entry_time": pd.date_range("2022-01-01", periods=12, freq="D", tz="UTC"),
                "exit_time": pd.date_range("2022-01-02", periods=12, freq="D", tz="UTC"),
                "pnl_abs": [100, -100] * 6,
                "exit_reason": ["take_profit", "stop_loss"] * 6,
                "holding_bars": list(range(12)),
                "selected_strategy": ["a"] * 6 + ["b"] * 6,
                "is_long": [True, False] * 6,
                "size": [100.0, 200.0] * 6,
            }
        )
    )

    rules = generate_candidate_rules(trades, min_train_trades=2, max_categories=10)
    features = {rule.feature for rule in rules}

    assert "selected_strategy" in features
    assert "is_long" in features
    assert "exit_reason" not in features
    assert "holding_bars" not in features
    assert "pnl_abs" not in features
    assert "size" not in features

    portfolio_rules = generate_candidate_rules(
        trades,
        min_train_trades=2,
        max_categories=10,
        include_portfolio_state_features=True,
    )
    assert "size" in {rule.feature for rule in portfolio_rules}


def test_run_trade_filter_research_writes_split_outputs(tmp_path: Path) -> None:
    trades_path = tmp_path / "trades.csv"
    trades = pd.DataFrame(
        {
            "entry_time": [
                "2022-01-05T00:00:00Z",
                "2022-02-05T00:00:00Z",
                "2024-01-05T00:00:00Z",
                "2024-02-05T00:00:00Z",
                "2025-01-05T00:00:00Z",
                "2025-02-05T00:00:00Z",
            ],
            "exit_time": [
                "2022-01-05T01:00:00Z",
                "2022-02-05T01:00:00Z",
                "2024-01-05T01:00:00Z",
                "2024-02-05T01:00:00Z",
                "2025-01-05T01:00:00Z",
                "2025-02-05T01:00:00Z",
            ],
            "pnl_abs": [2000.0, -500.0, 1500.0, -250.0, -100.0, 500.0],
            "selected_strategy": ["good", "bad", "good", "bad", "good", "bad"],
            "is_long": [True, False, True, False, True, False],
        }
    )
    trades.to_csv(trades_path, index=False)

    result = run_trade_filter_research(
        FilterSearchConfig(
            trades_paths=(trades_path,),
            output_dir=tmp_path / "out",
            splits=SplitConfig(
                train_start="2022-01-01",
                validation_start="2024-01-01",
                stress_start="2025-01-01",
                stress_end="2025-03-01",
            ),
            min_train_trades=1,
            progress=False,
        )
    )

    assert (tmp_path / "out" / "baseline_by_split.csv").exists()
    assert (tmp_path / "out" / "filter_candidates.csv").exists()
    assert (tmp_path / "out" / "top_filters.csv").exists()
    assert (tmp_path / "out" / "report.md").exists()
    assert result.baseline_by_split["split"].tolist() == ["train", "validation", "stress"]
    assert not result.filter_candidates.empty
    assert "robust_forward_pass" in result.filter_candidates.columns
    assert "robust_forward_score" in result.filter_candidates.columns
    assert "validation_return_delta_pct" in result.filter_candidates.columns
    assert "stress_return_delta_pct" in result.filter_candidates.columns
    assert "pair" in set(result.filter_candidates["rule_kind"])
    selected_strategy_rows = result.filter_candidates[
        result.filter_candidates["feature"] == "selected_strategy"
    ]
    assert not selected_strategy_rows.empty


def test_run_trade_filter_research_can_search_per_strategy(tmp_path: Path) -> None:
    trades_path = tmp_path / "trades.csv"
    trades = pd.DataFrame(
        {
            "entry_time": [
                "2022-01-05T00:00:00Z",
                "2022-01-06T12:00:00Z",
                "2024-01-05T00:00:00Z",
                "2024-01-06T12:00:00Z",
                "2025-01-05T00:00:00Z",
                "2025-01-06T12:00:00Z",
                "2022-02-05T00:00:00Z",
                "2022-02-06T12:00:00Z",
                "2024-02-05T00:00:00Z",
                "2024-02-06T12:00:00Z",
                "2025-02-05T00:00:00Z",
                "2025-02-06T12:00:00Z",
            ],
            "exit_time": [
                "2022-01-05T01:00:00Z",
                "2022-01-06T13:00:00Z",
                "2024-01-05T01:00:00Z",
                "2024-01-06T13:00:00Z",
                "2025-01-05T01:00:00Z",
                "2025-01-06T13:00:00Z",
                "2022-02-05T01:00:00Z",
                "2022-02-06T13:00:00Z",
                "2024-02-05T01:00:00Z",
                "2024-02-06T13:00:00Z",
                "2025-02-05T01:00:00Z",
                "2025-02-06T13:00:00Z",
            ],
            "pnl_abs": [
                200.0,
                -100.0,
                300.0,
                -50.0,
                250.0,
                -75.0,
                -50.0,
                120.0,
                -40.0,
                220.0,
                -60.0,
                180.0,
            ],
            "selected_strategy": ["alpha"] * 6 + ["beta"] * 6,
            "is_long": [True, False] * 6,
        }
    )
    trades.to_csv(trades_path, index=False)

    result = run_trade_filter_research(
        FilterSearchConfig(
            trades_paths=(trades_path,),
            output_dir=tmp_path / "out_grouped",
            group_by="selected_strategy",
            splits=SplitConfig(
                train_start="2022-01-01",
                validation_start="2024-01-01",
                stress_start="2025-01-01",
                stress_end="2025-03-01",
            ),
            min_train_trades=1,
            progress=False,
        )
    )

    assert set(result.baseline_by_split["group_value"]) == {"alpha", "beta"}
    assert set(result.filter_candidates["group_value"]) == {"alpha", "beta"}
    assert "selected_strategy" not in set(result.filter_candidates["feature"])


def test_generate_pair_candidate_rules_uses_top_single_rules() -> None:
    singles = pd.DataFrame(
        {
            "rule_kind": ["single", "single", "single"],
            "feature": ["is_long", "entry_hour", "entry_dayofweek"],
            "op": ["==", "<=", ">="],
            "value": ["True", 12.0, 2.0],
            "train_trade_count": [10, 10, 10],
        }
    )

    pairs = generate_pair_candidate_rules(
        single_candidates=singles,
        max_components=3,
        max_pair_rules=10,
    )

    assert pairs
    assert all("AND" in pair.expression for pair in pairs)


def test_attach_catalog_features_adds_closed_candle_features(tmp_path: Path) -> None:
    ohlcv_path = tmp_path / "ohlcv.csv"
    times = pd.date_range("2022-01-01", periods=80, freq="h", tz="UTC")
    ohlcv = pd.DataFrame(
        {
            "timestamp": times,
            "open": [100.0 + index for index in range(len(times))],
            "high": [101.0 + index for index in range(len(times))],
            "low": [99.0 + index for index in range(len(times))],
            "close": [100.5 + index for index in range(len(times))],
            "volume": [1000.0 + index for index in range(len(times))],
        }
    )
    ohlcv.to_csv(ohlcv_path, index=False)
    trades = prepare_trade_features(
        pd.DataFrame(
            {
                "entry_time": ["2022-01-03T12:30:00Z"],
                "exit_time": ["2022-01-03T13:00:00Z"],
                "pnl_abs": [100.0],
            }
        )
    )

    enriched = attach_catalog_features(trades, ohlcv_path)

    assert "catalog_atr_pct" in enriched.columns
    assert "catalog_ema_stack_long" in enriched.columns
    assert not pd.isna(enriched.loc[0, "catalog_atr_pct"])


def test_attach_catalog_features_uses_previous_candle_on_exact_open_time(
    tmp_path: Path,
) -> None:
    ohlcv_path = tmp_path / "ohlcv.csv"
    times = pd.date_range("2022-01-01", periods=80, freq="h", tz="UTC")
    ohlcv = pd.DataFrame(
        {
            "open_time": times,
            "open": [100.0 + index for index in range(len(times))],
            "high": [101.0 + index for index in range(len(times))],
            "low": [99.0 + index for index in range(len(times))],
            "close": [100.5 + index for index in range(len(times))],
            "volume": [1000.0 + index for index in range(len(times))],
        }
    )
    ohlcv.to_csv(ohlcv_path, index=False)
    trades = prepare_trade_features(
        pd.DataFrame(
            {
                "entry_time": ["2022-01-03T12:00:00Z"],
                "exit_time": ["2022-01-03T13:00:00Z"],
                "pnl_abs": [100.0],
            }
        )
    )

    enriched = attach_catalog_features(trades, ohlcv_path)
    previous = attach_catalog_features(
        prepare_trade_features(
            pd.DataFrame(
                {
                    "entry_time": ["2022-01-03T11:59:59Z"],
                    "exit_time": ["2022-01-03T13:00:00Z"],
                    "pnl_abs": [100.0],
                }
            )
        ),
        ohlcv_path,
    )

    assert enriched.loc[0, "catalog_bar_range_atr"] == previous.loc[
        0,
        "catalog_bar_range_atr",
    ]
