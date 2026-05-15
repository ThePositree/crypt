# ADR-0012: Liquidation engine roadmap (complements ADR-0006)

- **Status**: accepted
- **Date**: 2026-05-15
- **Owner**: agent

## Context

ADR-0006 deferred the liquidation engine on the grounds that:

1. OKX exposes liquidation orders only via WebSocket (`liquidation-orders`
   channel), and ADR-0004 committed the MVP to REST-only polling.
2. Paid aggregators (Coinglass, Laevitas) were excluded by the 0$ budget.
3. Free WS feeds from other venues were either rate-capped (Binance
   forceOrder post-2021) or out-of-venue for our trading decisions.

Since ADR-0006, two things have changed in the project's posture:

- The MVP is **deployed and validated**. The original concern of "don't
  add a WS lifecycle to an unproven REST pipeline" no longer applies the
  same way; we can sensibly add a secondary collector with its own
  failure modes.
- The owner has indicated intent to expand the ensemble after M2
  (`docs/tasks/ROADMAP.md` M5+ candidates). Liquidations are a well-known
  source of contrarian edge that the current engine set (trend, meanrev,
  derivatives, vol, regime) cannot capture.

This ADR does **not** supersede ADR-0006. ADR-0006's analysis was
correct for the MVP phase. This ADR adds the next-step plan and is the
file future agents should read when "should we implement liquidations?"
comes up.

## Decision

The liquidation engine is moved from BACKLOG **P2 (post-MVP)** to
BACKLOG **P1, post-M2**. Three implementation paths are listed in
priority order; the path is to be chosen by the agent who implements,
guided by what is true at that time (Coinglass freemium tier, OKX WS
stability, Path-C tooling).

### Path B (default recommendation) — Coinglass freemium REST API

- Pulls aggregated liquidation volumes (long vs short, USD-equivalent,
  per 1h bucket) across all major venues.
- Polled by a separate background task (every 5 min), persisted to
  `data/<symbol>/liquidations.parquet`.
- Engine reads parquet via `ContextBuilder`, never directly via the
  vendor.
- **Rate limit confirmation is required via Context7 before
  implementation** — the freemium tier has been quietly tightened
  multiple times.

### Path A (revisit if Path B becomes too restrictive) — OKX WS

- Long-running WS process appends raw liquidation events to the same
  parquet store.
- Requires reconnect-with-backoff that preserves the "no events lost"
  guarantee (use OKX's `seq_id` field).
- Requires updating ADR-0004 to admit a WS subscriber for one data
  source — write a new ADR superseding ADR-0004 only for the
  liquidation channel scope.

### Path C — ccxt-mediated cross-venue REST polling

- For venues that expose REST liquidation endpoints, fetch each
  individually and aggregate.
- Maintainability concern: we duplicate Coinglass's work poorly.
- Considered only if both Path A and Path B become unavailable.

Engine logic (independent of the path) lives in `docs/engines/liquidations.md`.

## Alternatives considered

### Stay at ADR-0006 (deferred indefinitely)

Pro: smallest scope.
Con: liquidation cascades are an actual edge in volatile regimes; M2
backtest will be missing an engine that any human discretionary trader
*does* look at. **Rejected** — we are past MVP.

### Build a custom WS aggregator across OKX + Bybit + Binance ourselves

Pro: pure free-tier, fully in our control.
Con: substantial multi-venue WS reconnect code, schema normalisation,
clock skew, deduplication. Two weeks of work to replace what Coinglass
provides for free. **Rejected** until vendor risk forces it.

## Consequences

### Positive
- The roadmap now has a concrete next-step plan for liquidations rather
  than "deferred". Future agents have specs (`docs/engines/liquidations.md`)
  to implement against.
- Path B keeps us REST-only on the critical path; the new vendor
  exposure is in a background task, isolated.
- M3 paper trading evaluates the new engine before any contemplation of
  M4 execution.

### Negative
- Adds an external vendor (Coinglass) with its own pricing/rate-limit
  drift risk. Mitigation: caching + graceful degradation; the engine
  spec (`docs/engines/liquidations.md`) handles all-missing data.
- The decision to switch from Path B to Path A would itself need an
  ADR (specifically, scoping ADR-0004 to "REST except liquidations").

### To revisit later
- Confirm Coinglass freemium tier at implementation time (Context7).
- If Coinglass becomes paid or unstable, evaluate Path A.
- After 30 days of liquidation data, run an ablation: ensemble with vs
  without the liquidation engine, on the M2 backtest harness. If
  ablation shows < 5% improvement in expectancy, consider deprecating
  the engine.

## References

- `ADR-0004` — REST-only choice (still in force for everything except
  liquidations).
- `ADR-0006` — original liquidation deferral; analysis remains valid
  for the MVP phase.
- `docs/engines/liquidations.md` — engine spec.
- `docs/backtest.md` — where the ablation will be measured.
