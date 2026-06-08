from __future__ import annotations

import math


def wilson_lower_bound(wins: int, trials: int, confidence_z: float = 1.96) -> float:
    if trials <= 0:
        return 0.0
    p = wins / trials
    z2 = confidence_z * confidence_z
    denominator = 1 + z2 / trials
    centre = p + z2 / (2 * trials)
    margin = confidence_z * math.sqrt((p * (1 - p) + z2 / (4 * trials)) / trials)
    return max((centre - margin) / denominator, 0.0)


def discovery_score(
    *,
    wins: int,
    losses: int,
    neutral: int,
    passed_events: int,
    windows_passing_min_trades: int,
    window_count: int,
) -> float:
    decisive = wins + losses
    if passed_events <= 0 or decisive <= 0:
        return 0.0
    neutral_rate = neutral / passed_events
    concentration_penalty = 0.0
    if window_count > 0:
        concentration_penalty = max(0.0, 1.0 - windows_passing_min_trades / window_count) * 0.25
    return (
        wilson_lower_bound(wins, decisive) * math.log1p(passed_events)
        - neutral_rate * 0.15
        - concentration_penalty
    )
