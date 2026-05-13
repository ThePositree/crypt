# ADR-0008: No order-flow / tape-reading engines

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent

## Context

The original brief mentioned an order-flow / tape-reading layer
(delta, buyer/seller pressure, book imbalance). These signals decay on a
seconds-to-minutes horizon. At a 4h horizon (ADR-0003) they are essentially
noise from a decision standpoint.

Building them anyway would require WebSocket streaming (rejected for MVP by
ADR-0004) and L2 order book history (which is not realistically free).

## Decision

Order-flow / tape engines are **not** part of the roadmap of this project.
If the owner later wants sub-minute decision-making, that becomes a separate
project (or a separate subsystem with its own scheduler and runtime), not an
addition to this one.

## Consequences

- Positive: tightly scoped MVP focused on what actually matters at 4h —
  trend, mean-reversion, derivatives positioning, volatility regime.
- Negative: known short-horizon edges (book imbalance, OFI) are unavailable.
  Acceptable trade-off.

## References

- ADR-0003, ADR-0004.
- Owner chat, 2026-05-13 (4h horizon confirmed).
