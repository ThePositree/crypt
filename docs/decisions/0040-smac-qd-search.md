# ADR-0040: SMAC-QD random-forest surrogate DSS backend

- **Status**: accepted
- **Date**: 2026-06-12
- **Owner**: agent
- **Related**: ADR-0025, ADR-0036, ADR-0039

## Context

The owner wants five materially different DSS search algorithms to run before
the next result-inspection session. After staged DSS v2, CatCMA-QD, Island-QD,
and Hyperband-QD, the next distinct pressure is conditional surrogate
optimization.

DSS is a conditional algorithm-configuration problem:

- trigger parameters depend on trigger choice;
- filter parameters depend on selected filters;
- execution parameters interact with signal shape;
- full objective evaluations are expensive backtests.

This is the problem shape SMAC-style random-forest surrogate optimization was
designed for. The repository already depends on `scikit-learn`, so the backend
can use `RandomForestRegressor` without adding another dependency.

## Decision

Add `backtester search-signals --algorithm smac_qd`.

SMAC-QD uses:

1. random-design bootstrap evaluations;
2. a fixed conditional numeric encoding of DSS candidates;
3. `sklearn.ensemble.RandomForestRegressor` as the surrogate model;
4. per-tree prediction dispersion as an uncertainty estimate;
5. acquisition score `predicted_mean + 0.75 * predicted_std`;
6. normal DSS Stage 1/2/3 evaluation and quality-diversity archive updates for
   selected infill candidates.

Owner-facing command:

```bash
uv run backtester search-signals \
  --algorithm smac_qd \
  --seed 5151 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_smac_seed5151
```

## Consequences

- Positive: the fifth search backend is genuinely different from random staged
  coverage, CatCMA-style adaptive probabilities, Island specialists, and
  Hyperband budget allocation.
- Positive: RF handles categorical/conditional spaces better than a vanilla
  Gaussian-process surrogate.
- Positive: artifacts remain compatible with existing DSS candidate replay.
- Negative: RF fit cost grows with observations; it is acceptable for this DSS
  scale but should be monitored on long runs.
- Negative: uncertainty from tree dispersion is approximate. It is sufficient
  for exploratory infill, not a substitute for mandate validation.

## References

- ADR-0036 — staged quality-diversity DSS
- ADR-0039 — Hyperband-QD backend
- `docs/discovery/direct_signal_search_v2.md`
