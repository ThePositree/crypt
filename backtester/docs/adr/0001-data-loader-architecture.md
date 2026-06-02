# ADR 0001: Data Loader Architecture

## Status

Accepted

## Date

2026-04-25

## Context

The backtester uses historical OHLCV data as a primary input for simulation,
strategy optimization, and result analysis.

The project needs a data loading design that:

- supports multiple data sources over time (CSV now, other providers later);
- keeps strategy and simulation code independent from storage details;
- provides predictable, validated data shape for all execution paths;
- remains simple enough for local experimentation workflows.

Without a clear architecture, loading logic can spread across scripts and core
modules, causing inconsistent preprocessing and duplicated validation.

## Decision

We standardize data ingestion behind a dedicated loader layer with a clear
interface:

- a loader accepts source configuration and returns a canonical tabular dataset;
- data is normalized to a shared schema before reaching backtester internals;
- validation (required columns, dtypes, ordering, missing critical fields) is
  performed at load boundaries;
- source-specific parsing logic is isolated from strategy, optimizer, and
  analyzer modules.

For the current stage, CSV is the primary concrete source, but the architecture
is intentionally extensible to additional adapters without changing consumers.

## Consequences

### Positive

- Backtester core remains focused on trading logic, not I/O details.
- New data sources can be added with minimal changes to existing components.
- Validation behavior is centralized and consistent across workflows.
- Integration points for caching and preprocessing are explicit.

### Negative

- One more abstraction layer increases initial implementation overhead.
- Adapters require maintenance as external source formats evolve.

## Alternatives Considered

1. **Inline loading in each script/module**
   - Rejected due to duplication and inconsistent preprocessing.
2. **Single monolithic loader without adapters**
   - Rejected because source-specific logic would become tightly coupled.
3. **Immediate full plugin system**
   - Rejected as premature complexity for current project scope.

## Notes

This ADR records architectural intent. Concrete loader APIs and adapter details
should evolve incrementally and remain backward-compatible where practical.
