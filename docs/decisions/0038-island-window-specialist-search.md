# ADR-0038: Islanded window-specialist DSS backend

- **Status**: accepted
- **Date**: 2026-06-12
- **Related**: ADR-0025, ADR-0036, ADR-0037

## Context

The first CatCMA-QD run improved cost control after Stage 2 capping, but the
search still failed to produce any proxy candidate with `robust_score > -5000`
or `score_min > -5000` after about 23.7k generated candidates. The best rows
were often acceptable only on `2025H1` and were killed by `2022`.

This suggests the immediate search problem is not only optimizer mechanics. It
is a regime/window conflict: robust all-window pressure can reject every
candidate before the project learns which strategy families can work in each
individual window.

## Decision

Add an experimental `island_qd` backend for `backtester search-signals`.

Island-QD keeps separate window-specialist islands:

- each population batch targets one window, e.g. `2022`, `2023`, `2024`,
  `2025H1`;
- Stage 1 still checks viability across all configured windows so candidates
  are not empty/noisy globally;
- Stage 2 scores only the island's target window, making specialist discovery
  cheaper and less hostile than all-window robust scoring;
- occasional full-window Stage 3 checks still run so robust candidates are not
  missed;
- output remains compatible with DSS artifacts and replay candidate JSONs.

Owner-facing command:

```bash
uv run backtester search-signals \
  --algorithm island_qd \
  --seed 2026 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output data/results/dss_sol_island_qd_railway_seed2026
```

## Consequences

- Positive: Railway can run a materially different search from both default
  DSS v2 and local CatCMA-QD.
- Positive: the run can reveal whether each window has any viable specialist
  families before searching for robust intersections.
- Negative: exported candidates are not automatically robust; `compare-fixed`
  and `walk-forward` remain mandatory.
- Negative: this is still a Python/pandas backtester path and can be slow on
  large budgets.
