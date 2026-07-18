# ADR-0037: CatCMA-QD experimental DSS backend

- **Status**: accepted
- **Date**: 2026-06-11
- **Related**: ADR-0025, ADR-0036

## Context

The owner started a long DSS v2 run on a work machine. Running the same staged
search at home with the same deterministic candidate generator would mostly
duplicate the same candidate sequence and waste the next multi-day budget.

The project needs a second search pressure that is meaningfully different from
the staged coverage generator while preserving the same downstream artifacts:
candidate JSONs, `compare-fixed` replay, and mandate-aware reports.

Recent mixed-variable black-box optimization research is relevant because DSS
candidate search mixes:

- categorical variables: trigger and filter choices;
- integer variables: TTL and lookback periods;
- continuous variables: thresholds, RRR, risk percent, ATR stop multipliers;
- expensive objective evaluations: full backtests and mandate reports.

The selected inspiration is **CatCMA with Margin** (2025), a stochastic
optimizer for continuous, integer, and categorical black-box problems. The
implementation here is a pragmatic in-repository adaptation, not a full paper
reproduction.

## Decision

Add an experimental `catcma_qd` backend to `backtester search-signals`.

The backend combines:

1. A lightweight mixed-variable distribution model inspired by CatCMA:
   categorical probabilities for trigger/filter choices and discrete grids for
   integer/float dimensions.
2. Evolutionary population updates from Stage 2/3 survivors.
3. Existing DSS v2 staged evaluation and quality-diversity archive semantics.

The default backend remains the accepted DSS v2 staged generator from
ADR-0036. Operators opt into the experiment explicitly:

```bash
uv run backtester search-signals \
  --algorithm catcma_qd \
  --seed 777 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_catcma_seed777
```

## Consequences

- Positive: the home run can explore a different candidate distribution from
  the work-machine staged run.
- Positive: candidate exports remain replayable through the existing
  `DSSStrategy` path.
- Positive: the experiment can learn from intermediate proxy/full scores
  without adding a heavy dependency.
- Negative: this is not a production-grade CatCMA implementation and should be
  reported as experimental.
- Negative: the update rule is intentionally simple; if it works, a later ADR
  can justify a fuller optimizer or external library.

## Guardrails

- `catcma_qd` must write artifacts compatible with the existing DSS v2 report
  shape.
- It must not replace `compare-fixed` or `walk-forward` as final validation.
- It must be seedable and resumable from generated stage artifacts.
- It must not hide poor results behind novelty or diversity bonuses.
