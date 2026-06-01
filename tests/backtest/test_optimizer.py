from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import yaml
from numpy import float64

from crypt.aggregator.weights import WeightsConfig
from crypt.backtest.optimizer import _apply_weights, _objective, run_optimizer, weights_to_yaml
from crypt.backtest.recorder import BacktestRecorder
from crypt.models import Regime, Signal, Verdict


def _weights(*, trend: float, meanrev: float, threshold: float = 0.15) -> dict[str, object]:
    regime_weights = {
        "trend": trend,
        "meanrev": meanrev,
        "derivatives": 0.0,
        "smc_structure": 0.0,
        "smc_order_blocks": 0.0,
        "smc_liquidity": 0.0,
    }
    return {
        "TRENDING": regime_weights,
        "RANGING": regime_weights,
        "HIGH_VOL": regime_weights,
        "thresholds": {"TRENDING": threshold, "RANGING": threshold, "HIGH_VOL": threshold},
        "vol_confidence_multiplier": {"low": 1.0, "normal": 1.0, "high": 1.0},
    }


def _verdicts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "SOL-USDT-SWAP",
                "tick_time": datetime(2025, 1, 1, tzinfo=UTC),
                "decision": "HOLD",
                "confidence": 80,
                "score": 0.0,
                "regime": "TRENDING",
                "rationale": "test",
                "strength_trend": 0.40,
                "strength_meanrev": -0.90,
                "strength_derivatives": None,
                "strength_smc_structure": None,
                "strength_smc_order_blocks": None,
                "strength_smc_liquidity": None,
                "return_h24": 0.02,
            }
        ]
    )


def _multi_regime_verdicts() -> pd.DataFrame:
    rows = []
    for i, regime in enumerate(["TRENDING", "RANGING", "HIGH_VOL"]):
        for j in range(2):
            rows.append(
                {
                    "symbol": "SOL-USDT-SWAP",
                    "tick_time": datetime(2025, 1, 1 + i, 4 * j, tzinfo=UTC),
                    "decision": "HOLD",
                    "confidence": 80,
                    "score": 0.0,
                    "regime": regime,
                    "rationale": "test",
                    "strength_trend": 0.60,
                    "strength_meanrev": -0.20,
                    "strength_derivatives": None,
                    "strength_smc_structure": None,
                    "strength_smc_order_blocks": None,
                    "strength_smc_liquidity": None,
                    "return_h24": 0.02,
                }
            )
    return pd.DataFrame(rows)


def test_apply_weights_recomputes_score_from_engine_strengths() -> None:
    trend_weighted = _apply_weights(_verdicts(), _weights(trend=1.0, meanrev=0.0))
    meanrev_weighted = _apply_weights(_verdicts(), _weights(trend=0.0, meanrev=1.0))

    assert float(trend_weighted["score"].iloc[0]) == 0.40
    assert trend_weighted["decision"].iloc[0] == "BUY"
    assert float(meanrev_weighted["score"].iloc[0]) == -0.90
    assert meanrev_weighted["decision"].iloc[0] == "SELL"


def test_objective_changes_when_candidate_weights_change_decision() -> None:
    trend_weighted = _apply_weights(_verdicts(), _weights(trend=1.0, meanrev=0.0))
    meanrev_weighted = _apply_weights(_verdicts(), _weights(trend=0.0, meanrev=1.0))

    trend_obj = _objective(trend_weighted, WeightsConfig(_weights(trend=1.0, meanrev=0.0)))
    meanrev_obj = _objective(meanrev_weighted, WeightsConfig(_weights(trend=0.0, meanrev=1.0)))

    assert trend_obj > meanrev_obj


def test_backtest_recorder_persists_scoring_engine_strengths() -> None:
    now = datetime(2025, 1, 1, tzinfo=UTC)
    signal = Signal(
        engine="trend",
        symbol="SOL-USDT-SWAP",
        direction="bullish",
        strength=0.4,
        confidence=0.8,
        produced_at=now,
    )
    recorder = BacktestRecorder()
    recorder.record(
        Verdict(
            symbol="SOL-USDT-SWAP",
            decision="BUY",
            confidence=80,
            score=0.4,
            regime=Regime.TRENDING,
            breakdown=[signal],
            rationale="test",
            produced_at=now,
        )
    )

    df = recorder.to_dataframe()

    assert float(df["strength_trend"].iloc[0]) == 0.4
    assert pd.isna(df["strength_meanrev"].iloc[0])


def test_run_optimizer_returns_weights_for_all_regimes() -> None:
    verdicts = _multi_regime_verdicts()

    result = run_optimizer(verdicts, verdicts)

    assert set(result.weights["thresholds"]) == {"TRENDING", "RANGING", "HIGH_VOL"}
    for regime in ("TRENDING", "RANGING", "HIGH_VOL"):
        assert "trend" in result.weights[regime]
        assert result.weights[regime]["derivatives"] == 0.0


def test_weights_to_yaml_writes_safe_yaml_for_numpy_scalars(tmp_path) -> None:
    path = tmp_path / "weights.candidate.yaml"
    weights = {
        "TRENDING": {
            "trend": float64(0.25),
            "meanrev": float64(0.75),
            "derivatives": 0.0,
        },
        "thresholds": {"TRENDING": float64(0.55)},
    }

    weights_to_yaml(weights, str(path))

    text = path.read_text()
    assert "!!python/object" not in text
    assert yaml.safe_load(text) == {
        "TRENDING": {
            "trend": 0.25,
            "meanrev": 0.75,
            "derivatives": 0.0,
        },
        "thresholds": {"TRENDING": 0.55},
    }
