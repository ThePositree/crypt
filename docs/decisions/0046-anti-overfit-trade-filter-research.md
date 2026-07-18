# ADR-0046: Anti-overfit validation and trade filter research

- **Status**: accepted
- **Date**: 2026-06-26

## Context

Router searches over the current six archived SOL strategies failed the owner
mandate when validated through exact OHLCV composite backtests. The best exact
2025 finalist returned roughly +158% but passed only 4/12 monthly floor gates.
Continuing to search more routers over the same weak donor universe is likely
to optimize a proxy rather than produce a production candidate.

The owner redirected research toward two constraints:

1. every trainable entity must use a fixed anti-overfit chronology;
2. before searching new strategies or routers, inspect current trades and find
   entry-known filters that remove bad trades while preserving good trades.

## Decision

Adopt the following default validation chronology for **all trainable research
entities** unless a later ADR explicitly supersedes it:

- Train: `2022-01-01` inclusive → `2024-01-01` exclusive.
- Validation: `2024-01-01` inclusive → `2025-01-01` exclusive.
- Stress: `2025-01-01` inclusive → latest available closed trade/bar.

Add a trade-filter research surface that consumes existing `trades.csv`
artifacts and searches `take` / `skip` rules using only fields known at entry
time. Post-entry fields such as PnL, exit reason, exit price, and holding
duration are blocked from feature generation.

The first implementation searches single-feature threshold/equality rules and
reports train, validation, and stress performance side by side.

## Consequences

- Search reports must separate fit, selection, and stress evidence instead of
  reporting one in-sample score.
- Trade filtering can be explored quickly from existing artifacts without
  launching owner-scale backtests.
- A profitable research filter is not automatically production-ready because
  skipping trades changes capital, overlap, and margin state. Promising filters
  must be implemented inside the strategy/router and validated through the
  unchanged external backtester.
- Composite-oracle work is no longer the active next step; it remains a
  secondary diagnostic if the project later needs a theoretical upper bound.

## References

- `docs/trade_filter_research.md`
- `docs/investment_mandate.md`
- ADR-0025
- ADR-0043
- ADR-0045
