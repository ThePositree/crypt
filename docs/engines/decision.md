# Decision layer

Sits between the aggregator and the sinks. Applies coarse filters that
should *suppress* a verdict (turn it into `HOLD` for output purposes, or
withhold the alert) rather than override its direction.

## Filters

### 1. Confidence threshold

If `verdict.confidence < ALERT_CONFIDENCE_THRESHOLD` (default 75), the
verdict is still recorded by `JsonLogSink` and `ConsoleSink`, but
`TelegramSink` does not fire.

### 2. Per-symbol cooldown

If the previous alert for the same symbol was emitted within the last
`COOLDOWN_HOURS` (default 4, i.e. one H4 candle), no Telegram alert fires.
Verdict is still logged. Direction-flips break the cooldown (BUY → SELL is
always alerted).

### 3. Inputs-missing guard

If the verdict was produced with critical inputs missing (currently:
`candles[H4]` missing on the symbol), the verdict is downgraded to `HOLD`
and a warning is logged. This is a safety net: an engine should already
have emitted `neutral`, but the guard ensures we never alert on a partial
context.

### 4. Spread / staleness guard (placeholder)

Reserved. When execution is wired up (M4), this will check the live ticker
bid/ask spread and last-trade timestamp before letting a verdict through.
In MVP this is a no-op.

## Configuration

Loaded from `.env` via pydantic-settings; can be overridden per symbol in
`config/runtime.yaml` (M1+).

## Tests

`tests/decision/test_filters.py`:

- Verdict with `confidence = 74` ⇒ Telegram not called.
- Verdict with `confidence = 75` ⇒ Telegram called.
- Two consecutive `BUY` within < 4h ⇒ second is suppressed.
- `BUY` then `SELL` within < 4h ⇒ both are alerted.
- Verdict with `inputs_missing=["candles[H4]"]` ⇒ decision rewritten to
  `HOLD`.
