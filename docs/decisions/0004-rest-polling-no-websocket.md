# ADR-0004: REST polling, no WebSocket in MVP

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent

## Context

OKX exposes both REST and WS for market data. WS adds substantial code
complexity (connection lifecycle, reconnection, heartbeat, sequence
ordering), benefits a sub-minute decision horizon, and is unnecessary at
the 4h horizon (ADR-0003).

## Decision

MVP uses **synchronous REST polling** through `ccxt`'s OKX adapter,
scheduled at a coarse cadence:

- OHLCV (`H4`, `H1`, `D1`): once every 5 minutes (cheap; gives near-instant
  detection of candle close).
- Funding rate: once every 15 minutes.
- Open Interest history: once every 5 minutes.
- Long/short ratio, taker volume: once every 15 minutes.

OKX rate limits (10 req / 2 s per IP+instId for most public endpoints) are
comfortably honoured with 3 symbols.

The decision tick (engines + aggregator + sinks) runs only on `H4` close.

## Consequences

- Positive: dramatically simpler runtime; no WS state machine.
- Positive: trivially reproducible in backtest (pure pull model).
- Negative: cannot collect liquidation events (WS-only on OKX). Covered by
  ADR-0006 (deferred).
- Negative: small latency between true candle close and our verdict (≤ 5
  min). Acceptable at the 4h horizon.

## References

- OKX rate limits, Context7 `/websites/okx_docs-v5_en`.
- ADR-0003.
