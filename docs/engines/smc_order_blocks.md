# Engine: smc_order_blocks

## Purpose

Models the order-block retest view. It does not signal when an order block is
created; it signals when price returns into an active zone that aligns with
the current SMC structure bias.

## Inputs

- `ctx.candles[H4]` — closed H4 candles (required, ≥ 260 preferred).

## Output (`Signal`)

- `engine`: `"smc_order_blocks"`
- `direction`:
  - `bullish` when price retests an active bullish order block while current
    structure bias is bullish or neutral.
  - `bearish` when price retests an active bearish order block while current
    structure bias is bearish or neutral.
  - `neutral` otherwise.
- `strength`:
  - `0.65` base for a valid retest;
  - +0.15 if swing and internal bias agree with the block;
  - +0.10 if the close rejects out of the zone in the signal direction;
  - sign by direction, clipped to `[-1, 1]`.
- `confidence`: `0.50 + confluence bonuses`, clipped to `[0, 0.85]`.
- `meta`: `zone_low`, `zone_high`, `origin_time`, `distance_to_zone_atr`,
  `structure_event_type`, `bias`.

## Logic

```text
state = analyse_smc(h4, tick_time)
active_blocks = unmitigated order blocks with known_at <= tick_time
candidate = nearest active block touched by current closed candle

if candidate bias conflicts with both swing and internal bias:
    neutral

if bullish block and low <= zone_high and close >= zone_low:
    bullish
if bearish block and high >= zone_low and close <= zone_high:
    bearish
```

## Edge cases

- Mitigated blocks are ignored.
- If bullish and bearish zones are both touched on the same candle, choose the
  one whose bias matches the latest structure event. If still tied, neutral.
- Very wide zones (`zone_width > 3 * ATR14`) are ignored.

## Tests

- Bullish BOS creates bullish OB; later retest emits bullish signal.
- Bearish BOS creates bearish OB; later retest emits bearish signal.
- Mitigated block does not emit.
- Conflicting structure bias suppresses signal.

## Known weaknesses

- H4 order blocks are coarse. Entry price may be much worse than the visual
  zone suggests; M3 entry/SL logic must account for this.
