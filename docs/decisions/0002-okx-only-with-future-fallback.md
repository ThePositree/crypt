# ADR-0002: OKX as the sole exchange, Bybit/Binance reserved as data-only fallback

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent (confirmed by owner)

## Context

Owner trades only on OKX. Some data may still be missing or rate-limited
there. Owner stated: "Data missing on OKX — take from Bybit or Binance."

## Decision

- All execution (when later wired up) is OKX-only.
- Primary market data source is OKX via `ccxt`.
- Bybit / Binance are allowed **only as read-only data fallbacks** for
  specific endpoints OKX cannot serve, and only when justified by a follow-up
  ADR specifying the endpoint, reason, and contamination risk.

## Alternatives considered

- **Multi-venue from day one**: rejected. Adds significant cross-venue
  normalisation cost for no business value at MVP stage.
- **Strict OKX-only including data**: rejected. Some derivatives data
  (notably liquidations) is limited on OKX REST (ADR-0006). A predefined
  fallback path avoids dead-ends later.

## Consequences

- Positive: simple data layer, single exchange model in `crypt.exchange`.
- Positive: clear procedure when something is missing — new ADR + new client.
- Negative: cross-venue inconsistency risk if/when fallbacks are added.
  Mitigation: every fallback must document its delta vs OKX (e.g. Binance
  funding is settled every 8h aligned to UTC; OKX every 8h aligned to UTC
  too — usually compatible, but each pair must be confirmed).

## References

- Owner chat, 2026-05-13.
- OKX docs verified via Context7 `/websites/okx_docs-v5_en`.
