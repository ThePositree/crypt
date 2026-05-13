# ADR-0003: 4-hour intraday horizon as the only timeframe at MVP

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent (confirmed by owner)

## Context

Owner picked "4h intraday only". The horizon dictates which engines are
worth building and what infrastructure is required.

## Decision

The decision tick is aligned to **4-hour closed candle**. Engines may read
auxiliary lower timeframes (e.g. `1h` for ADX smoothing, `1d` for regime
context) but the verdict is emitted once per closed `H4` candle.

## Consequences

- Order book / tape / order-flow engines are **out of scope** (ADR-0008).
- WebSocket streaming is **not required for MVP** (ADR-0004).
- Funding-rate cadence (OKX: 8h) is well-aligned with two H4 candles —
  every other tick coincides with a fresh funding rate.
- Slower iteration than scalping setups, but far less sensitive to slippage
  and latency. Better fit for a 0-budget local deployment (ADR-0005).

## Alternatives considered

- 1h / 15m intraday — more signal but funding cadence (8h) becomes lumpy
  and signal-to-noise on derivatives drops.
- Daily swing — too few decision points per month for a paper-trading
  validation phase of reasonable length.

## References

- Owner chat, 2026-05-13.
