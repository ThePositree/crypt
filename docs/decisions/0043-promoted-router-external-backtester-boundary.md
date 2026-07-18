# ADR-0043: Promoted router preserves the external backtester boundary

- **Status**: accepted
- **Date**: 2026-06-25
- **Owner**: owner direction in chat, agent documented
- **Supersedes**: the nested-backtest implementation recorded on 2026-06-24
- **Related**: ADR-0032, ADR-0041, ADR-0042

## Context

The first `promoted_router` implementation reconstructed rolling strategy
performance by launching one complete backtest per nested strategy from inside
`BaseStrategy.generate()`, then returned a routed signal frame to another outer
backtest.

That shape violated the required integration contract. The backtester must be
treated as an external library: it accepts one strategy, performs one portfolio
simulation, and returns one result. A strategy may compose signal generators,
but it may not instantiate or recursively invoke the backtester.

## Decision

1. `promoted_router` is one normal `BaseStrategy`.
2. `generate()` never instantiates `Backtester` or `ExecutionSim` and never
   calls `run_backtest`.
3. Completed rolling-label history is persisted router state and is supplied
   to the router through an explicit `labels_path`. The external backtester
   does not know that this dependency exists.
4. Router decisions remain causal: only rows with
   `label_end <= decision_timestamp` may affect a decision.
5. The strategy computes the selection timeline, generates only nested signal
   streams selected during the input period, and multiplexes them into one
   output frame.
6. The external backtester is the only owner of real capital, margin,
   positions, fees, entries, and exits.
7. Missing router state is a hard error. Historical nested backtests are not an
   allowed fallback.

## Consequences

- Full-period validation uses one external portfolio simulation.
- Research or paper infrastructure must persist and update rolling-label state
  for production use.
- Component signal generation remains internal strategy computation; it does
  not create independent portfolios.
- Historical validation cannot start until the exact promoted-router label
  artifact is restored locally.
- Future optimization may share feature computation among nested strategies,
  but it must not weaken this boundary.

## References

- `docs/strategies/promoted_router.md`
- `strategies/archive/router_v2_2687609.json`
- `docs/tasks/IN_PROGRESS.md`
