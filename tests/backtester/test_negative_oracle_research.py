from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtester.negative_oracle_research import (
    NegativeOracleConfig,
    run_negative_oracle_research,
)


def test_negative_oracle_research_finds_repeatable_skip_rule(tmp_path: Path) -> None:
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
            "pnl_abs": [200.0, -500.0, 150.0, -300.0, 100.0, -250.0],
            "selected_strategy": ["good", "bad", "good", "bad", "good", "bad"],
            "is_long": [True, False, True, False, True, False],
        }
    )
    trades.to_csv(trades_path, index=False)

    result = run_negative_oracle_research(
        NegativeOracleConfig(
            trades_path=trades_path,
            output_dir=tmp_path / "out",
            train_start="2022-01-01",
            validation_start="2024-01-01",
            stress_start="2025-01-01",
            min_train_trades=1,
            progress=False,
        )
    )

    assert (tmp_path / "out" / "negative_rules.csv").exists()
    assert (tmp_path / "out" / "top_negative_rules.csv").exists()
    assert (tmp_path / "out" / "report.md").exists()
    assert not result.rules.empty

    best = result.rules.iloc[0]
    assert "selected_strategy == 'bad'" in str(best["expression"])
    assert best["validation_delta_abs"] == 300.0
    assert best["stress_delta_abs"] == 250.0
    assert bool(best["robust_negative_pass"])
