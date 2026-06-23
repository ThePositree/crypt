from __future__ import annotations

import pandas as pd
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.regime_router import RouterConfig, evaluate_rolling_router_baselines


def test_rolling_router_uses_only_completed_prior_labels() -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=10.0, b=0.0),
            _row("2024-01-15", "2024-02-14", a=0.0, b=100.0),
            _row("2024-02-01", "2024-03-02", a=1.0, b=3.0),
        ]
    )

    dense, _, _ = evaluate_rolling_router_baselines(
        labels,
        config=RouterConfig(
            validation_start="2024-02-01",
            min_available_strategies=2,
            lookback_days=365,
        ),
    )

    top2 = dense[dense["router"] == "rolling_top2_mean_60_40"].iloc[0]
    assert top2["weights"].startswith("a:")
    assert "dispersion_pct" not in top2["weights"]


def test_rolling_router_baseline_help() -> None:
    result = CliRunner().invoke(cli, ["rolling-router-baseline", "--help"])

    assert result.exit_code == 0
    assert "--labels" in result.output
    assert "--min-available-strategies" in result.output


def _row(asof: str, label_end: str, *, a: float, b: float) -> dict[str, object]:
    best = "a" if a >= b else "b"
    second = "b" if best == "a" else "a"
    best_return = max(a, b)
    second_return = min(a, b)
    return {
        "asof": f"{asof}T00:00:00+00:00",
        "label_end": f"{label_end}T00:00:00+00:00",
        "available_strategy_count": 2,
        "best_strategy": best,
        "best_return_pct": best_return,
        "second_strategy": second,
        "second_return_pct": second_return,
        "return_a": a,
        "return_b": b,
        "ret_30d_pct": 0.0,
        "ret_90d_pct": 0.0,
    }
