# H1 WebSocket execution trigger

## Purpose

Start Core4 processing as soon as OKX confirms the candle required by the
strategy, while retaining a safe REST fallback.

## Inputs

- OKX public business WebSocket:
  `wss://ws.okx.com:8443/ws/v5/business`
- Channels per execution symbol:
  - `candle1H`
  - `candle4H`
  - `candle1Dutc`
- Subscription begins at `HH:59:30 UTC`.

No authentication is required.

## Boundary contract

For an hourly boundary `B`, the primary callback may run only after:

1. `candle1H` supplies the candle opened at `B - 1h` with `confirm=1`;
2. when `B` is a four-hour boundary, `candle4H` supplies the candle opened at
   `B - 4h` with `confirm=1`;
3. when `B` is `00:00 UTC`, `candle1Dutc` supplies the candle opened at
   `B - 1d` with `confirm=1`;
4. `candle1H` supplies the forming candle opened at `B` with `confirm=0`; its
   open is the live equivalent of the backtester's `next_open`.

The callback payload contains the confirmed candles, boundary time, and H1
open. The signal runner saves the confirmed candles and validates local
continuity before generating signals.

## Duplicate prevention

The trigger tracks each `(symbol, boundary)` in memory:

- an in-flight WebSocket callback blocks the REST fallback for that boundary;
- a successful callback marks the boundary complete;
- a failed callback removes the in-flight marker so the fallback can retry;
- repeated WebSocket updates for a completed candle are ignored.

Order-level event IDs remain the durable restart protection.

## Failure behavior

- Subscription errors, malformed payloads, disconnects, or a missing confirmed
  boundary are logged.
- If the WebSocket path does not complete, the existing REST cycle runs at
  `*:02 UTC`.
- The failure is sent through the execution error notifier.
- Shutdown cancels the listener and closes the WebSocket cleanly.

## Observability

Normal logs must show:

- WebSocket connection/subscription readiness;
- the confirmed boundary and new H1 open;
- whether execution was started by `websocket`, `rest_fallback`, or `startup`;
- every `ENTRY ATTEMPT`;
- every `ENTRY REJECTED` with the complete reason also sent to Telegram.

## Known latency

After the boundary arrives, `filtered_donor_portfolio.generate()` currently
recomputes the full history and takes roughly 30 seconds. Removing that cost
requires an incremental strategy runtime and is separate from this trigger.
