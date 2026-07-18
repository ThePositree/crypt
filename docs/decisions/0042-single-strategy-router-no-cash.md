# ADR-0042: Single-strategy router without cash state

- **Status**: accepted
- **Date**: 2026-06-24
- **Owner**: owner direction in chat, agent documented
- **Supersedes in part**: ADR-0041
- **Related**: ADR-0025, ADR-0032, ADR-0041

## Context

ADR-0041 described a future router that could allocate capital among several
strategy portfolios or reduce exposure in an unknown regime.

The owner rejected that shape:

- strategy research and margin assumptions were built around one active
  strategy;
- simultaneous strategies create ambiguous capital and margin allocation;
- every archived strategy is always eligible for selection;
- the router must always choose a strategy and may not choose cash.

## Decision

The regime router is a single-strategy selector:

1. every decision selects exactly one archived strategy;
2. all archived strategies remain in the available universe;
3. the router never splits capital;
4. the router has no cash or unknown-exposure state;
5. a strategy may emit no trade while selected, but that is not a router cash
   decision;
6. routed execution uses one shared portfolio and one shared margin limit;
7. strategy handoff uses drain semantics: existing positions close naturally,
   and the newly selected strategy cannot enter until positions from the
   previous strategy are closed.

## Consequences

- Router search evaluates selection quality rather than portfolio weights.
- Capital and margin accounting are unambiguous.
- A delayed handoff can skip entries from the newly selected strategy.
- The router cannot suppress trading during uncertain regimes; it must choose
  the best available archived strategy.
- ADR-0041 remains accepted for strategy-behavior regime discovery, labeler,
  and detector separation. Its capital-allocation and unknown-exposure router
  shape is superseded by this ADR.

## References

- `docs/regime_router_search.md`
- `docs/routed_execution_validation.md`
- `docs/backtester/router_archive.md`
