# Aggregator

## Purpose

Combines per-engine `Signal`s into a single `Verdict` per symbol. Uses
regime-conditional weights (ADR-0007). Aggregator is **deterministic**:
given the same Signals and weights, the same Verdict comes out.

## Inputs

- `signals`: a list of `Signal` objects produced by all engines that ran on
  this tick.
- `regime`: a `Regime` enum from the regime engine.
- `weights`: a dict-like loaded from `config/weights.yaml`:

  ```yaml
  TRENDING:
    trend:       0.55
    meanrev:     0.05
    derivatives: 0.30
    volatility:  0.10
  RANGING:
    trend:       0.15
    meanrev:     0.50
    derivatives: 0.25
    volatility:  0.10
  HIGH_VOL:
    trend:       0.20
    meanrev:     0.20
    derivatives: 0.30
    volatility:  0.30

  # Per-regime decision thresholds on |score|.
  thresholds:
    TRENDING:  0.25
    RANGING:   0.30
    HIGH_VOL:  0.45

  # Confidence multiplier from vol_regime payload.
  vol_confidence_multiplier:
    low:    0.95
    normal: 1.0
    high:   0.85
  ```

  Initial values are placeholders. M2 calibrates them on history.

## Output

A `Verdict`:

- `decision`: `BUY` if `score >= +T[regime]`, `SELL` if `score <= -T[regime]`,
  else `HOLD`.
- `score`: weighted sum of `signal.strength * weight[regime, signal.engine]`,
  for engines that contribute (i.e. excluding `volatility`/`regime`).
- `confidence`: integer in `[0, 100]`. Computed as:

  ```text
  base_conf = sum_i (weight_i * signal_i.confidence * (1 if signal_i.strength != 0 else 0.5))
  alignment = fraction of contributing signals whose sign matches sign(score)
  raw       = base_conf * (0.5 + 0.5 * alignment) * vol_multiplier
  conf      = round(clip(raw * 100, 0, 100))
  ```

- `breakdown`: the original signals (sorted by `|contribution|` descending).
- `rationale`: a human-readable string composed from:
  - regime,
  - decision + confidence,
  - per-engine: `engine_name: direction (strength=±0.xx, weight=0.xx)`,
  - any `inputs_missing` flags raised by engines.

## Logic notes

- Engines whose `direction == neutral` contribute 0 to `score`. Their
  `confidence` *does* still contribute to `base_conf` (penalising "everyone
  shrugs" cases by being small).
- An engine that reported missing data → its weight is renormalised across
  the remaining engines so the score is still in `[-1, +1]`.
- The aggregator never raises. Any unexpected condition → `HOLD` with a
  `rationale` describing what was wrong.

## Edge cases

- All engines `neutral` ⇒ `decision = HOLD`, `score ≈ 0`, `confidence < 50`.
- One engine far stronger than all others (e.g. extreme funding) ⇒ score
  reflects that, but `alignment` is low ⇒ `confidence` is capped.
- Regime is `HIGH_VOL` ⇒ threshold is high (0.45). The system intentionally
  emits fewer non-HOLD verdicts in crisis.

## Tests

`tests/aggregator/test_ensemble.py`:

- All-bullish signals with normal regime ⇒ `BUY`, high `confidence`.
- Trend bullish + meanrev bearish in `TRENDING` regime ⇒ `BUY`
  (trend weight dominates), moderate confidence.
- Same signals in `RANGING` regime ⇒ likely `SELL` (meanrev weight
  dominates) or `HOLD` if score < threshold.
- Missing derivatives signal ⇒ weights renormalised, decision still
  reasonable.
- All neutral ⇒ `HOLD`, `confidence < 50`.

## Known weaknesses

- Weighted-sum is transparent but cannot capture non-linear interactions
  (e.g. "trend + funding extreme" should boost more than the linear sum
  suggests). ML meta-aggregator (BACKLOG P2) addresses this later.
- Confidence calibration is heuristic. M3's paper-trading phase should
  establish whether the `≥ 75` alert threshold actually correlates with
  positive expectancy.
- Static per-regime weights still embed an assumption that the regime
  detector is correct. Whenever the detector is wrong, the wrong weight
  set applies. Mitigation: keep the detector simple (ADX-based) so its
  errors are at least predictable.
