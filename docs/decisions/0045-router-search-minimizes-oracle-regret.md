# ADR-0045: Router search minimizes regret to a single-strategy oracle

- **Status**: accepted
- **Date**: 2026-06-25
- **Owner**: owner direction in chat, agent documented
- **Related**: ADR-0042, ADR-0043, ADR-0044

## Context

The first Router Catalog searches ranked millions of candidates primarily by
their own offset-compounded return, drawdown, losing periods, switches, and
offset instability. The owner wants the search objective to express the
router's actual learning target directly: choose as closely as possible to the
best available strategy known by the offline oracle.

The oracle selects exactly one strategy per forward label window. It does not
split capital and is not executable because it uses future returns.

## Decision

1. The mass-search objective is oracle regret:

   ```text
   regret = best_return_pct - selected_return_pct
   ```

2. Every non-overlap offset reports mean, p90, and worst regret, oracle hit
   rate, oracle compounded return, router compounded return, and oracle capture
   ratio.
3. Candidate utility is ranked primarily by robust regret:

   ```text
   utility =
       - median(offset mean regret)
       - p90(offset mean regret)
       - 0.25 * median(offset worst regret)
       - 0.10 * abs(worst offset drawdown)
       - 0.10 * median(offset switches)
   ```

4. Strategy-id hit rate is diagnostic only. Choosing a strategy returning 19%
   instead of the oracle's 20% is better than matching more IDs with larger
   return loss.
5. Mass search writes a deterministic shortlist artifact. Archived-trade
   replay and exact composite OHLCV backtests remain later validation stages.
6. Oracle information may rank candidates on train data. Holdout oracle values
   may evaluate a frozen router but may not tune it.
7. Router search therefore accepts an exclusive `validation_end`; the current
   train/holdout boundary is `2025-01-01`.

## Consequences

- Search ranking directly measures distance from the desired oracle behavior.
- Return, drawdown, capture ratio, and switches remain visible diagnostics.
- A high proxy rank is not a production result; exact shared-capital execution
  remains mandatory for the shortlist.
