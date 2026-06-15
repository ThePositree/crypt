# ADR-0039: Hyperband-QD budgeted DSS backend

- **Status**: accepted
- **Date**: 2026-06-12
- **Owner**: agent
- **Related**: ADR-0025, ADR-0036, ADR-0037, ADR-0038

## Context

The owner is running several DSS searches in parallel. Existing backends cover
three different pressures:

- `staged`: deterministic staged quality-diversity search;
- `catcma_qd`: adaptive mixed-variable sampling;
- `island_qd`: per-window specialist search.

If another machine is available, running another CatCMA or Island variant would
mostly duplicate an existing pressure. The next distinct experiment should
allocate expensive evaluation budgets more formally: score many candidates
cheaply, then promote only a capped, behavior-diverse fraction to progressively
more expensive backtests.

## Decision

Add an experimental `hyperband_qd` backend to `backtester search-signals`.

The backend uses successive-halving rungs:

1. Stage 1 signal viability for every generated candidate.
2. Rung 1 promotes a capped, behavior-diverse slice to one-window proxy scoring.
3. Rung 2 promotes a smaller slice to multi-window proxy scoring.
4. Rung 3 promotes the final slice to full all-window Stage 3 scoring.

It reuses the DSS v2 candidate model, mandate score, quality-diversity archive,
candidate export format, and downstream `compare-fixed` / `walk-forward`
validation path.

Owner-facing command:

```bash
uv run backtester search-signals \
  --algorithm hyperband_qd \
  --seed 4242 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_hyperband_seed4242
```

## Consequences

- Positive: fewer weak candidates should pay full proxy/full backtest cost.
- Positive: behavior-diverse promotion keeps the search from becoming only a
  top-score filter at each rung.
- Positive: artifacts remain compatible with existing DSS reports and replay
  candidate JSONs.
- Negative: this is a pragmatic Hyperband-style implementation, not BOHB/DEHB;
  it does not add a surrogate model.
- Negative: a candidate can be dropped early if its cheap-window score is poor
  even when another regime would have worked. Island-QD remains the better tool
  for explicit window-specialist discovery.

## References

- ADR-0036 — staged quality-diversity DSS
- ADR-0038 — Island-QD window-specialist backend
- `docs/discovery/direct_signal_search_v2.md`
