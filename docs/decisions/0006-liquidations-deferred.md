# ADR-0006: Liquidation analytics deferred (OKX exposes WS only)

- **Status**: accepted — complemented by [ADR-0012](0012-liquidations-roadmap.md) (post-M2 roadmap)
- **Date**: 2026-05-13
- **Owner**: agent

> **Note (2026-05-15)**: ADR-0012 records the post-M2 plan for this
> engine without superseding the analysis below. The MVP-phase
> reasoning here is still valid.

## Context

OKX exposes liquidation orders only through the public WebSocket channel
`liquidation-orders` on `/ws/v5/public`. There is no REST endpoint for
historical liquidations on OKX. ADR-0004 commits the MVP to REST-only.

Free liquidation feeds across venues are increasingly throttled
(Binance forceOrder stream is rate-capped post-2021; Bybit is more open but
out-of-venue for our trading decisions). Paid aggregators (Coinglass,
Laevitas) are excluded by the 0$ budget.

## Decision

- No liquidation engine in MVP.
- Architecturally reserve `engines/liquidations.py` and a future background
  process `data/collectors/liquidations_ws.py` so a future ADR can add this
  without restructuring.
- When (and if) we add it, the design will be:
  - separate long-running WS listener appends raw liquidation events to
    `data/<symbol>/liquidations.parquet`;
  - the engine reads aggregate buckets (e.g. liquidation volume in
    last 4h, last 24h, z-score against rolling baseline) from that store.

## Consequences

- Positive: no WS lifecycle code in MVP.
- Negative: lose a known-useful contrarian signal (liquidation cascades).
  Mitigation: regime-detector + funding-rate extremes cover part of the
  same edge.

## References

- OKX docs (Context7 `/websites/okx_docs-v5_en`), `liquidation-orders` WS
  channel.
- ADR-0003, ADR-0004.
