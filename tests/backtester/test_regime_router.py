from __future__ import annotations

import pandas as pd
from click.testing import CliRunner

from backtester.__main__ import cli
from backtester.regime_router import (
    RouterConfig,
    RouterSearchConfig,
    evaluate_rolling_router_baselines,
    evaluate_single_strategy_router_search,
)


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


def test_single_strategy_router_search_selects_one_strategy() -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0, ps=1.0),
            _row("2024-02-01", "2024-03-02", a=4.0, b=-2.0, ps=1.0),
            _row("2024-03-05", "2024-04-04", a=3.0, b=-1.0, ps=1.0),
            _row("2024-04-10", "2024-05-10", a=1.0, b=6.0, ps=-1.0),
        ]
    )

    predictions, dense, offsets, utility = evaluate_single_strategy_router_search(
        labels,
        config=RouterSearchConfig(
            validation_start="2024-04-10",
            min_available_strategies=2,
            lookback_days=(120,),
            scoring_methods=("rolling_mean", "feature_knn_mean"),
            feature_sets=("pinescript",),
            knn_k=(3,),
            min_hold_days=(0,),
            switch_margin_thresholds=(0.0,),
            min_samples=1,
            max_configs=10,
        ),
    )

    assert not predictions.empty
    assert set(predictions["selected_strategy"]).issubset({"a", "b"})
    assert predictions["selected_strategy"].str.contains(";").sum() == 0
    assert not dense.empty
    assert not offsets.empty
    assert not utility.empty


def test_router_search_help() -> None:
    result = CliRunner().invoke(cli, ["router-search", "--help"])

    assert result.exit_code == 0
    assert "--labels" in result.output
    assert "--catalog-version" in result.output
    assert "--algorithm" in result.output
    assert "--config-offset" in result.output
    assert "--max-configs" in result.output
    assert "--summary-only" in result.output


def test_router_search_matrix_help() -> None:
    result = CliRunner().invoke(cli, ["router-search-matrix", "--help"])

    assert result.exit_code == 0
    assert "--algorithms" in result.output
    assert "--proposal-multiplier" in result.output
    assert "--max-configs" in result.output
    assert "--output-root" in result.output


def test_v2_summary_only_keeps_predictions_for_top_shortlist() -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0, ps=1.0),
            _row("2024-02-01", "2024-03-02", a=4.0, b=-2.0, ps=1.0),
            _row("2024-03-05", "2024-04-04", a=3.0, b=-1.0, ps=1.0),
            _row("2024-04-10", "2024-05-10", a=1.0, b=6.0, ps=-1.0),
        ]
    )

    predictions, dense, offsets, utility = evaluate_single_strategy_router_search(
        labels,
        config=RouterSearchConfig(
            validation_start="2024-04-10",
            min_available_strategies=2,
            catalog_version="v2",
            summary_only=True,
            top_predictions=2,
            max_configs=4,
        ),
    )

    assert len(dense) == 4
    assert len(utility) == 4
    assert predictions["router"].nunique() == 2
    assert offsets["router"].nunique() == 2


def test_v2_search_algorithms_share_result_contract() -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0, ps=1.0),
            _row("2024-02-01", "2024-03-02", a=4.0, b=-2.0, ps=1.0),
            _row("2024-03-05", "2024-04-04", a=3.0, b=-1.0, ps=1.0),
            _row("2024-04-10", "2024-05-10", a=1.0, b=6.0, ps=-1.0),
            _row("2024-05-15", "2024-06-14", a=-1.0, b=5.0, ps=-1.0),
        ]
    )

    for algorithm in ("random", "island_qd", "hyperband_qd", "smac_qd"):
        predictions, dense, offsets, utility = evaluate_single_strategy_router_search(
            labels,
            config=RouterSearchConfig(
                validation_start="2024-04-10",
                min_available_strategies=2,
                catalog_version="v2",
                algorithm=algorithm,
                seed=17,
                proposal_multiplier=2,
                summary_only=True,
                top_predictions=1,
                max_configs=2,
            ),
        )

        assert len(dense) == 2
        assert len(utility) == 2
        assert predictions["router"].nunique() == 1
        assert offsets["router"].nunique() == 1


def _row(
    asof: str, label_end: str, *, a: float, b: float, ps: float = 0.0
) -> dict[str, object]:
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
        "router_ps_supertrend_dir": ps,
        "router_ps_adx": 25.0,
        "router_ps_di_side": ps,
    }
