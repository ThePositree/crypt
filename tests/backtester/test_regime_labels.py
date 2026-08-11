from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtester.regime_labels import build_oracle_label_dataset, build_rolling_label_dataset


def test_build_oracle_label_dataset_selects_best_and_top2() -> None:
    matrix = pd.DataFrame(
        [
            {"bucket": "2024-01", "a": 1.0, "b": 3.0, "c": -2.0},
            {"bucket": "2024-02", "a": 5.0, "b": 4.0, "c": 6.0},
        ]
    )
    ohlcv = _hourly_ohlcv("2023-01-01", periods=24 * 450)

    labels = build_oracle_label_dataset(
        return_matrix=matrix,
        ohlcv=ohlcv,
        bucket="month",
    )

    jan = labels[labels["bucket"] == "2024-01"].iloc[0]
    feb = labels[labels["bucket"] == "2024-02"].iloc[0]
    assert jan["best_strategy"] == "b"
    assert jan["best_return_pct"] == 3.0
    assert jan["second_strategy"] == "a"
    assert jan["margin_to_second_pct"] == 2.0
    assert jan["positive_strategy_count"] == 2
    assert jan["negative_strategy_count"] == 1
    assert feb["best_strategy"] == "c"
    assert feb["second_strategy"] == "a"


def test_oracle_label_features_use_only_bars_before_bucket_start() -> None:
    matrix = pd.DataFrame([{"bucket": "2024-02", "a": 1.0, "b": 2.0}])
    before = _hourly_ohlcv("2023-01-01", periods=24 * 396)
    after = before.copy()
    # This bar is inside the labeled month and must not affect feature_close.
    after.loc[len(after)] = {
        "open_time": pd.Timestamp("2024-02-01 00:00:00", tz="UTC"),
        "o": 999.0,
        "h": 999.0,
        "l": 999.0,
        "c": 999.0,
        "volume": 999.0,
        "closed": True,
    }

    labels = build_oracle_label_dataset(
        return_matrix=matrix,
        ohlcv=after,
        bucket="month",
    )

    assert labels.iloc[0]["feature_close"] == before.iloc[-1]["c"]


def test_oracle_label_dataset_accepts_datetime_index_ohlcv() -> None:
    matrix = pd.DataFrame([{"bucket": "2024-02", "a": 1.0, "b": 2.0}])
    ohlcv = _hourly_ohlcv("2023-01-01", periods=24 * 396)
    indexed = ohlcv.rename(
        columns={"o": "open", "h": "high", "l": "low", "c": "close"}
    ).set_index("open_time")

    labels = build_oracle_label_dataset(
        return_matrix=matrix,
        ohlcv=indexed,
        bucket="month",
    )

    assert labels.iloc[0]["feature_bar_count"] == len(indexed)


def test_build_rolling_label_dataset_uses_future_exit_window(tmp_path: Path) -> None:
    trades_dir = tmp_path / "strategy_trades"
    trades_dir.mkdir()
    pd.DataFrame(
        [
            {
                "exit_time": "2024-02-05T00:00:00+00:00",
                "pnl_abs": 100.0,
                "capital_before": 10_000.0,
            }
        ]
    ).to_csv(trades_dir / "a.csv", index=False)
    pd.DataFrame(
        [
            {
                "exit_time": "2024-02-10T00:00:00+00:00",
                "pnl_abs": 50.0,
                "capital_before": 10_000.0,
            },
            {
                "exit_time": "2024-03-15T00:00:00+00:00",
                "pnl_abs": 1_000.0,
                "capital_before": 10_000.0,
            },
        ]
    ).to_csv(trades_dir / "b.csv", index=False)
    ohlcv = _hourly_ohlcv("2023-10-01", periods=24 * 160)

    labels = build_rolling_label_dataset(
        trades_dir=trades_dir,
        ohlcv=ohlcv,
        step="day",
        horizon_days=30,
        min_history_days=90,
        start="2024-02-01",
        end="2024-02-01",
    )

    row = labels.iloc[0]
    assert row["best_strategy"] == "a"
    assert row["return_a"] == 1.0
    assert row["return_b"] == 0.5
    assert "router_ps_supertrend_dir" in labels.columns
    assert "router_ps_adx" in labels.columns


def test_build_rolling_label_dataset_respects_partial_strategy_coverage(tmp_path: Path) -> None:
    trades_dir = tmp_path / "strategy_trades"
    trades_dir.mkdir()
    pd.DataFrame(
        [
            {
                "exit_time": "2024-02-05T00:00:00+00:00",
                "pnl_abs": 100.0,
                "capital_before": 10_000.0,
            }
        ]
    ).to_csv(trades_dir / "past_only.csv", index=False)
    pd.DataFrame(
        [
            {
                "exit_time": "2025-02-05T00:00:00+00:00",
                "pnl_abs": -50.0,
                "capital_before": 10_000.0,
            }
        ]
    ).to_csv(trades_dir / "covered.csv", index=False)
    pd.DataFrame(
        [
            {
                "strategy_id": "past_only",
                "coverage_start": "2024-01-01T00:00:00+00:00",
                "coverage_end": "2024-12-31T00:00:00+00:00",
            },
            {
                "strategy_id": "covered",
                "coverage_start": "2025-01-01T00:00:00+00:00",
                "coverage_end": "2026-01-01T00:00:00+00:00",
            },
        ]
    ).to_csv(tmp_path / "strategy_coverage.csv", index=False)
    ohlcv = _hourly_ohlcv("2024-01-01", periods=24 * 430)

    labels = build_rolling_label_dataset(
        trades_dir=trades_dir,
        ohlcv=ohlcv,
        step="day",
        horizon_days=30,
        min_history_days=90,
        start="2025-02-01",
        end="2025-02-01",
    )

    row = labels.iloc[0]
    assert row["available_strategy_count"] == 1
    assert row["best_strategy"] == "covered"
    assert pd.isna(row["return_past_only"])
    assert row["return_covered"] == -0.5


def _hourly_ohlcv(start: str, *, periods: int) -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=periods, freq="h", tz="UTC")
    base = pd.Series(range(periods), dtype="float64") + 100.0
    return pd.DataFrame(
        {
            "open_time": timestamps,
            "o": base,
            "h": base + 1.0,
            "l": base - 1.0,
            "c": base + 0.5,
            "volume": base * 10.0,
            "closed": True,
        }
    )
