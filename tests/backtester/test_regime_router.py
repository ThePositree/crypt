from __future__ import annotations

from pathlib import Path

import pandas as pd
from click.testing import CliRunner

import backtester.regime_router as regime_router_module
from backtester.__main__ import cli
from backtester.regime_router import (
    RouterConfig,
    RouterSearchConfig,
    _router_utility_summary,
    evaluate_rolling_router_baselines,
    evaluate_single_strategy_router_search,
    write_single_strategy_router_search_report,
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
    assert {
        "oracle_total_return_pct",
        "oracle_gap_pct",
        "oracle_capture_ratio",
        "mean_regret_pct",
        "p90_regret_pct",
        "worst_regret_pct",
        "oracle_hit_rate",
    }.issubset(offsets.columns)
    assert utility["scoring_objective"].eq("oracle_regret_v1").all()


def test_router_search_help() -> None:
    result = CliRunner().invoke(cli, ["router-search", "--help"])

    assert result.exit_code == 0
    assert "--labels" in result.output
    assert "--validation-end" in result.output
    assert "--catalog-version" in result.output
    assert "--algorithm" in result.output
    assert "--config-offset" in result.output
    assert "--max-configs" in result.output
    assert "--summary-only" in result.output
    assert "--progress" in result.output


def test_router_search_matrix_help() -> None:
    result = CliRunner().invoke(cli, ["router-search-matrix", "--help"])

    assert result.exit_code == 0
    assert "--algorithms" in result.output
    assert "--validation-end" in result.output
    assert "--proposal-multiplier" in result.output
    assert "--max-configs" in result.output
    assert "--output-root" in result.output


def test_router_search_matrix_keeps_child_progress_on_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    labels = tmp_path / "labels.csv"
    labels.write_text("asof\n", encoding="utf-8")
    popen_calls: list[tuple[list[str], dict[str, object]]] = []

    class FakeProcess:
        pid = 123

        def wait(self) -> int:
            return 0

        def poll(self) -> int:
            return 0

        def terminate(self) -> None:
            return None

    def fake_popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return FakeProcess()

    monkeypatch.setattr("backtester.__main__.subprocess.Popen", fake_popen)

    result = CliRunner().invoke(
        cli,
        [
            "router-search-matrix",
            "--labels",
            str(labels),
            "--algorithms",
            "random,island_qd",
            "--output-root",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert [call[0][call[0].index("--progress-position") + 1] for call in popen_calls] == [
        "0",
        "1",
    ]
    assert all("stderr" not in kwargs for _command, kwargs in popen_calls)


def test_router_validate_shortlist_help() -> None:
    result = CliRunner().invoke(cli, ["router-validate-shortlist", "--help"])

    assert result.exit_code == 0
    assert "--predictions" in result.output
    assert "--shortlist" in result.output
    assert "--matrix-dir" in result.output


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


def test_router_search_preserves_exclusive_holdout_end() -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0),
            _row("2024-06-01", "2024-07-01", a=4.0, b=-2.0),
            _row("2025-01-01", "2025-01-31", a=-5.0, b=10.0),
        ]
    )

    predictions, _, _, _ = evaluate_single_strategy_router_search(
        labels,
        config=RouterSearchConfig(
            validation_start="2024-01-01",
            validation_end="2025-01-01",
            min_available_strategies=2,
            min_samples=1,
            max_configs=1,
        ),
    )

    assert pd.to_datetime(predictions["asof"], utc=True).max() < pd.Timestamp(
        "2025-01-01",
        tz="UTC",
    )


def test_router_search_progress_reports_known_candidate_total(monkeypatch) -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0),
            _row("2024-02-01", "2024-03-02", a=4.0, b=-2.0),
            _row("2024-03-05", "2024-04-04", a=3.0, b=-1.0),
            _row("2024-04-10", "2024-05-10", a=1.0, b=6.0),
        ]
    )
    calls: list[dict[str, object]] = []

    def fake_tqdm(iterable, **kwargs):
        calls.append(kwargs)
        return iterable

    monkeypatch.setattr(regime_router_module, "tqdm", fake_tqdm)

    evaluate_single_strategy_router_search(
        labels,
        config=RouterSearchConfig(
            validation_start="2024-04-10",
            min_available_strategies=2,
            max_configs=2,
            progress=True,
        ),
    )

    evaluation = next(call for call in calls if call.get("unit") == "router")
    assert evaluation["total"] == 2
    assert evaluation["disable"] is False
    assert evaluation["position"] == 0


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


def test_router_utility_prefers_lower_oracle_regret() -> None:
    offsets = pd.DataFrame(
        [
            _offset_row("close", mean_regret=1.0, p90_regret=2.0, worst_regret=3.0),
            _offset_row("close", mean_regret=2.0, p90_regret=3.0, worst_regret=4.0),
            _offset_row("far", mean_regret=5.0, p90_regret=7.0, worst_regret=9.0),
            _offset_row("far", mean_regret=6.0, p90_regret=8.0, worst_regret=10.0),
        ]
    )

    utility = _router_utility_summary(offsets)

    assert utility.iloc[0]["router"] == "close"
    assert utility.iloc[0]["utility_score"] > utility.iloc[1]["utility_score"]


def test_router_search_report_writes_parameterized_shortlist(tmp_path: Path) -> None:
    labels = pd.DataFrame(
        [
            _row("2024-01-01", "2024-01-31", a=5.0, b=-1.0),
            _row("2024-02-01", "2024-03-02", a=4.0, b=-2.0),
            _row("2024-03-05", "2024-04-04", a=3.0, b=-1.0),
            _row("2024-04-10", "2024-05-10", a=1.0, b=6.0),
        ]
    )
    config = RouterSearchConfig(
        validation_start="2024-04-10",
        min_available_strategies=2,
        max_configs=2,
        top_predictions=1,
    )
    predictions, dense, offsets, utility = evaluate_single_strategy_router_search(
        labels,
        config=config,
    )

    write_single_strategy_router_search_report(
        output=tmp_path,
        predictions=predictions,
        dense_summary=dense,
        offset_sensitivity=offsets,
        utility=utility,
        config=config,
    )

    shortlist = pd.read_csv(tmp_path / "router_shortlist.csv")
    assert len(shortlist) == 1
    assert shortlist.loc[0, "router"] == utility.iloc[0]["router"]
    assert pd.notna(shortlist.loc[0, "scoring_method"])


def _row(asof: str, label_end: str, *, a: float, b: float, ps: float = 0.0) -> dict[str, object]:
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


def _offset_row(
    router: str,
    *,
    mean_regret: float,
    p90_regret: float,
    worst_regret: float,
) -> dict[str, object]:
    return {
        "router": router,
        "offset_days": 0,
        "periods": 10,
        "total_return_pct": 100.0,
        "oracle_total_return_pct": 120.0,
        "oracle_gap_pct": 20.0,
        "oracle_capture_ratio": 0.9,
        "mean_regret_pct": mean_regret,
        "p90_regret_pct": p90_regret,
        "worst_regret_pct": worst_regret,
        "oracle_hit_rate": 0.5,
        "max_drawdown_pct": -5.0,
        "negative_periods": 1,
        "switches": 2,
    }
