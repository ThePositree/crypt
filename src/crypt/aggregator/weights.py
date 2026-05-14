from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crypt.models import Regime, VolRegime

# Engines whose strength contributes to the weighted-sum score.
SCORING_ENGINES = frozenset({"trend", "meanrev", "derivatives"})

# Default weights (used when config file is missing or malformed).
_DEFAULTS: dict[str, Any] = {
    "TRENDING": {"trend": 0.55, "meanrev": 0.05, "derivatives": 0.40},
    "RANGING": {"trend": 0.15, "meanrev": 0.60, "derivatives": 0.25},
    "HIGH_VOL": {"trend": 0.20, "meanrev": 0.20, "derivatives": 0.60},
    "thresholds": {"TRENDING": 0.25, "RANGING": 0.30, "HIGH_VOL": 0.45},
    "vol_confidence_multiplier": {"low": 0.95, "normal": 1.00, "high": 0.85},
}


class WeightsConfig:
    """
    Holds per-regime engine weights and decision thresholds loaded from YAML.
    Falls back to hard-coded defaults so the system can start without a file.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def load(cls, path: Path) -> WeightsConfig:
        if path.exists():
            with path.open("r") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return cls(data)
        return cls(_DEFAULTS)

    def engine_weights(self, regime: Regime) -> dict[str, float]:
        """
        Return normalised weights for the scoring engines under `regime`.

        Engines not present in the config receive weight 0. Weights are
        renormalised so they always sum to 1 over SCORING_ENGINES.
        """
        raw: dict[str, float] = self._data.get(regime.value, {})
        weights = {eng: float(raw.get(eng, 0.0)) for eng in SCORING_ENGINES}
        total = sum(weights.values())
        if total <= 0:
            equal = 1.0 / len(SCORING_ENGINES)
            return dict.fromkeys(SCORING_ENGINES, equal)
        return {eng: w / total for eng, w in weights.items()}

    def threshold(self, regime: Regime) -> float:
        thresholds: dict[str, float] = self._data.get("thresholds", {})
        return float(thresholds.get(regime.value, 0.30))

    def vol_multiplier(self, vol_regime: VolRegime) -> float:
        mult: dict[str, float] = self._data.get("vol_confidence_multiplier", {})
        return float(mult.get(vol_regime, 1.0))
