# ADR-0051: WebSocket-confirmed H1 execution trigger

- **Status**: accepted
- **Date**: 2026-06-30
- **Supersedes**: the fixed `*:02 UTC` primary H1 execution schedule

## Context

The first post-audit Core4 signal exposed an avoidable live/backtest mismatch.
The backtester entered at the next H1 open (`72.84`), while live execution
started two minutes later and rejected the entry at `73.52` because the price
had moved `0.934%`.

A fixed delay protects against reading an unconfirmed exchange candle, but it
also guarantees unnecessary entry latency. OKX's business WebSocket publishes
candle updates with a `confirm` field, so the exchange can explicitly tell the
executor when H1/H4/D1 candles are complete.

## Decision

- At `HH:59:30 UTC`, execution connects to the OKX public business WebSocket
  and subscribes to H1, H4, and UTC-day candles for every execution symbol.
- A live H1 cycle starts when:
  - the ending H1 candle is received with `confirm=1`;
  - any H4/D1 candle ending at the same boundary is also confirmed; and
  - the first forming H1 update supplies the new hour's actual open.
- Confirmed WebSocket candles are persisted before strategy generation and
  become the source of truth for that boundary.
- The existing REST refresh at `*:02 UTC` remains as a fallback when the
  WebSocket path fails or does not confirm the boundary.
- A boundary coordinator prevents the WebSocket and fallback paths from
  processing the same symbol/hour concurrently or twice.
- Every entry attempt and deterministic rejection is written to the normal log
  as well as Telegram.

## Consequences

- Normal live signal generation begins seconds after the exchange confirms the
  candle instead of two minutes after the hour.
- The roughly 30-second full-history strategy calculation remains the next
  major latency source.
- WebSocket disconnects do not stop trading permanently; the REST fallback
  still runs at `*:02`.
- Backtester/live fill parity is improved but cannot be exact during fast moves:
  live still uses the executable market price and retains the entry-drift guard.

## References

- `docs/execution/h1_websocket_trigger.md`
- `docs/execution/live_execution.md`
- OKX API v5 business WebSocket candlesticks channel
