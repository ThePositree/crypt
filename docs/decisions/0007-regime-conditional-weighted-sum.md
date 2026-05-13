# ADR-0007: Regime-conditional weighted-sum aggregator

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent (confirmed by owner: "do as you see fit")

## Context

Owner picked weighted-sum over ML. Static weights are known to fail across
regimes (trend engine in a range, mean-reversion engine in a strong trend).
A regime detector + three weight sets is the cheapest mitigation that
preserves the transparency of weighted-sum.

## Decision

The aggregator computes:

```
score(symbol) = sum_i weight[regime, engine_i] * signal_i.strength
```

where `signal_i.strength ∈ [-1, +1]` and weights per `(regime, engine)` are
loaded from a YAML config. Three regimes:

- `TRENDING`
- `RANGING`
- `HIGH_VOL`

The `RegimeEngine` is a dedicated, deterministic module (not a weighted
component); it labels the current state of the symbol and selects the
weight set. Detector inputs: ADX(14) on `H4`, ATR%-rank on `D1` over the
last 60 days.

Verdict decision rule:

- `score >= +T` ⇒ `BUY`
- `score <= -T` ⇒ `SELL`
- otherwise ⇒ `HOLD`

with `T` per regime (lower for `TRENDING`, higher for `HIGH_VOL`).
`confidence` is a function of `|score|` calibrated so that values around
`T` give ≈ 60 and stronger consensus pushes towards 100.

## Alternatives considered

- **Static (non-regime) weighted sum**: chosen by the owner initially.
  Rejected because it is provably wrong across regimes; the regime layer is
  worth its ~150 LOC.
- **ML meta-aggregator** (logistic / LightGBM): out of scope until we have
  a backtested baseline. Tracked as BACKLOG P2.

## Consequences

- Positive: explainable verdicts (we can show each engine's contribution).
- Positive: tunable per symbol without retraining anything.
- Negative: weights must be calibrated on real history — that is what the
  backtest harness exists for (ADR-0008-ish; see BACKLOG).
- Negative: regime detection is itself a model with its own failure modes.
  Mitigated by keeping it simple and falling back to `RANGING` on missing
  inputs.

## References

- Owner chat, 2026-05-13.
- `docs/engines/regime.md`, `docs/engines/aggregator.md`.
