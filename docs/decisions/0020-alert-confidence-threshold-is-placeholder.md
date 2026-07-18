# ADR-0020: Alert confidence threshold is a placeholder

- **Status**: accepted
- **Date**: 2026-06-02
- **Owner**: agent (owner corrected in chat)
- **Supersedes**: ADR-0011 Part A for the rationale of
  `ALERT_CONFIDENCE_THRESHOLD = 75`

## Context

ADR-0011 documented `ALERT_CONFIDENCE_THRESHOLD = 75` as a plausible default
and included a post-hoc rationale for alert frequency. The owner corrected this:
the number `75` was chosen arbitrarily and future agents should not try to
explain it as a calibrated or empirically motivated threshold.

The threshold-correct donor smoke at `/tmp/crypt_donor_smoke/20260602_122510`
made the problem concrete. Applying `min_confidence = 75` as a donor entry
gate produced zero trades even though the ensemble emitted 1798 directional
BUY/SELL verdicts. The current confidence scale had p99 around 38 and max 52
on that SOL sample, so `75` is not semantically compatible with using donor
smokes to evaluate the directional setup surface.

## Decision

Treat the live alert threshold of `75` as an arbitrary placeholder until a
future calibration ADR replaces it.

For donor M2 work:

- `crypt_ensemble` must not default to filtering entries by `confidence >= 75`.
- Directional BUY/SELL verdicts are tradeable by default in donor smokes.
- `min_confidence` remains an optional explicit strategy parameter for
  diagnostics or Optuna experiments.
- Signal diagnostics should summarize the confidence distribution rather than
  hard-coding one placeholder cutoff as the main metric.

The live Telegram decision filter may keep the default value `75` for now
because changing live alert volume is an operator-visible policy change. That
value must not be interpreted as calibrated probability, model quality, or a
required M2 tradeability gate.

## Consequences

- Donor smoke tests again evaluate the existing ensemble's directional setup
  surface instead of only the arbitrary live-alert surface.
- Future calibration can search or replace confidence thresholds from data.
- Documentation must avoid post-hoc explanations for the number `75`.
- The `[UNCALIBRATED]` marker policy from ADR-0011 remains valid.

## References

- ADR-0011: Thresholds rationale and `[UNCALIBRATED]` marker policy
- `src/backtester/strategies/crypt_ensemble.py`
- `strategies/backtester/crypt_ensemble.json`
- `src/backtester/results_analyzer.py`
