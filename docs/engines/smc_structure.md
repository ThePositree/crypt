# Engine: smc_structure

## Purpose

Models the market-structure trader view: bullish when price breaks structure
up, bearish when it breaks down, cautious when the latest event is only an
internal change of character. It is candle-only and intended for M2
OHLCV-only calibration (ADR-0017).

## Inputs

- `ctx.candles[H4]` — last closed H4 candles (required, ≥ 260 preferred).

## Output (`Signal`)

- `engine`: `"smc_structure"`
- `direction`:
  - `bullish` after recent bullish swing/internal BOS or bullish CHoCH.
  - `bearish` after recent bearish swing/internal BOS or bearish CHoCH.
  - `neutral` when no recent confirmed structure event exists.
- `strength`:
  - sign from event direction;
  - base magnitude `0.45` for internal CHoCH, `0.60` for internal BOS,
    `0.75` for swing CHoCH, `0.90` for swing BOS;
  - decays by `0.10` per H4 bar after the event, floor `0.20` while the event
    is still within the lookback window.
- `confidence`:
  - base equals `abs(strength)`;
  - +0.10 when swing and internal bias agree;
  - -0.15 when the latest event is CHoCH against the higher-level swing bias;
  - clipped to `[0, 1]`.
- `meta`:
  - `event_type`, `structure_kind`, `event_time`, `broken_level`,
    `swing_bias`, `internal_bias`.

## Logic

```text
state = analyse_smc(h4, tick_time)
event = latest BOS/CHoCH with known_at <= tick_time and age <= 12 H4 bars

if no event:
    neutral

direction = bullish if event.direction == +1 else bearish
strength = signed(event_weight[event.kind, event.type] - age_decay)
confidence = abs(strength) +/- confluence penalties
```

## Edge cases

- Missing or short H4 data → neutral with `inputs_missing=["candles[H4]"]`.
- Equal but opposite swing/internal events on the same candle → prefer swing.
- Events older than 12 H4 bars → neutral; they are structure context, not a
  fresh directional signal.

## Tests

- Bullish swing BOS produces bullish signal.
- Bearish CHoCH after bullish bias produces bearish signal.
- Old event decays to neutral.
- Missing H4 data emits neutral and marks critical input missing.
- No-lookahead: event is absent before pivot confirmation and present after.

## Known weaknesses

- BOS often appears after a move has already travelled; the engine may buy late.
- CHoCH is noisy in ranges. The aggregator/regime layer must decide whether
  to trust it.
