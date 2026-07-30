# ADR-0041: Regime discovery from archived strategy behavior

- **Status**: accepted; router allocation shape superseded by ADR-0042
- **Date**: 2026-06-19
- **Owner**: owner direction in chat, agent documented
- **Related**: ADR-0025, ADR-0036, ADR-0040

## Context

Current strategy search is optimized around finding candidates that score well
against the strategy benchmark. This remains the main quality target, but
recent DSS results show that useful signal families may be temporary or
regime-specific rather than universally robust.

The owner clarified a broader direction:

- keep running strategy searches in parallel with feature work;
- archive strategies that are economically or diagnostically useful even if
  they do not pass the full benchmark;
- later use the archived strategy set to discover market regimes and train a
  detector/router layer.

This changes the role of the archive. It is not only a shelf for near-miss
production candidates. It is also a dataset of strategy behavior that can
reveal when different alpha families work.

## Decision

Build the future regime layer around strategy behavior.

Regimes are not predefined calendar labels. They are inferred from a strategy
performance matrix built from archived and active strategy variants:

```text
time x strategy metrics
```

The project will separate three components:

1. **Regime Discovery**: offline analysis that clusters or models historical
   strategy-performance changes.
2. **Regime Labeler**: offline historical labeler that may use future data to
   create retrospective training labels.
3. **Regime Detector**: online/backtest-time detector that may use only past
   and current data.

The original Portfolio Router allocation shape is superseded by ADR-0042. The
router now selects exactly one archived strategy, never splits capital, and
never selects cash. The discovery, labeler, and detector separation in this
ADR remains accepted.

## Consequences

- Positive: strategy searches can produce value even when no candidate passes
  the benchmark.
- Positive: the archive becomes training material for regime detection and
  portfolio routing.
- Positive: the system can aim for fast adaptation instead of searching only
  for permanent alpha.
- Negative: archive quality now matters. Strategy configs, execution params,
  artifact paths, and performance windows must be reproducible.
- Negative: detector accuracy is not enough. Detector candidates must be scored
  by portfolio utility after routing costs, drawdown, switching, uncertainty,
  and detection delay penalties.
- Negative: this adds a second research loop after strategy search. It should
  not block continued DSS/catalog runs.

## Implementation Notes

Start with OHLCV-only regime features and rule-based detectors.

Future detector models may include Random Forest, gradient boosting, HMMs,
clustering assignment, or neural networks, but only after the MVP labeler and
portfolio-utility scoring loop exists.

Archived strategies can be stored even if they are below the production
benchmark, provided the archive entry states why the strategy is useful for
research: positive return, regime-specific behavior, diversified signal
family, high signal quality, or useful failure mode.

## References

- `docs/regime_detection.md`
- `docs/backtester/candidate_archive.md`
- `docs/archive/candidates/README.md`
