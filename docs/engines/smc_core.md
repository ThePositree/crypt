# SMC core

## Purpose

Shared deterministic candle-structure analyser used by SMC engines. It is not
an engine by itself. It converts closed OHLCV candles into timestamped
structure events that can be replayed without lookahead bias.

`pinescript/smc.pine` is the behavioural reference for the first version:
pivot legs, BOS/CHoCH, order-block extraction, equal highs/lows, and
mitigation rules. TradingView drawing code and any `lookahead_on` MTF logic
are not ported.

## Inputs

- H4 closed candles with `open_time, o, h, l, c, volume` (required).
- Optional D1 closed candles for future higher-timeframe levels. Not used by
  the first implementation slice.

## Outputs

Python dataclasses under `crypt.structure.smc`:

- `SMCPivot` — confirmed high/low pivot, level, pivot time, confirmation time,
  kind (`swing` or `internal`).
- `SMCStructureEvent` — bullish/bearish BOS or CHoCH, broken level, event time,
  source pivot, structure kind.
- `SMCOrderBlock` — bullish/bearish zone (`low`, `high`), origin time,
  source event, active/mitigated state.
- `SMCLiquidityEvent` — equal high/low or sweep event with level and time.
- `SMCState` — current swing/internal bias, latest events, active order blocks.

Every event has both the source candle time and the `known_at` time. Engines
must use only events where `known_at <= ctx.tick_time`.

## Logic

### Pivot confirmation

Use the same leg idea as the Pine reference:

- `swing_length = 50` by default.
- `internal_length = 5` by default.
- a pivot high at index `i - length` is confirmed only after the current bar
  at index `i` closes and the candidate high is higher than the previous
  `length` highs in the rolling comparison;
- a pivot low is symmetrical.

The exact Python implementation may use explicit loops instead of vectorised
Pine semantics, but tests must prove that a pivot is not visible before its
confirmation bar.

### BOS / CHoCH

- Bullish break: close crosses above the latest uncrossed pivot high.
- Bearish break: close crosses below the latest uncrossed pivot low.
- If the previous bias was opposite, tag the break as `CHOCH`; otherwise tag
  it as `BOS`.
- Mark the pivot crossed after the first valid break.

### Order blocks

On a bullish structure break, create a bullish order block from the lowest
parsed candle between the broken pivot and the break candle. On a bearish
break, create a bearish order block from the highest parsed candle in that
window.

High-volatility candle parsing follows the Pine reference:

- compute ATR(200) or cumulative mean true range;
- if `high - low >= 2 * volatility_measure`, swap parsed high/low so the
  extreme wick is not selected as the order-block body.

First implementation may use ATR(200) only.

Mitigation:

- bullish OB is invalidated when low trades below `barLow` (or close below,
  if configured later);
- bearish OB is invalidated when high trades above `barHigh`.

### Equal highs/lows and sweeps

- Equal high/low threshold: `0.1 * ATR(200)` by default, matching Pine input.
- Sweep high: current high exceeds an existing equal/swing high and the candle
  closes back below that level.
- Sweep low: current low exceeds an existing equal/swing low and the candle
  closes back above that level.

## Edge cases

- Fewer than `max(swing_length, internal_length, 200)` candles: return an empty
  state; engines emit neutral.
- NaN prices or non-monotonic `open_time`: caller should fail schema
  validation; analyser skips invalid rows defensively.
- Multiple events on one candle are allowed and returned in deterministic
  order: pivots, structure breaks, order blocks, liquidity events.

## Tests

- Pivot high/low is emitted only after the right-side confirmation delay.
- Bullish BOS after crossing pivot high updates bias bullish.
- Bearish CHoCH after bullish bias flips bias bearish.
- Bullish/bearish order block zone is selected from the pivot-to-break window.
- Mitigated order block is removed/marked inactive.
- Equal high/low threshold uses ATR-scaled tolerance.
- No event has `known_at` later than the context tick used by an engine.

## Known weaknesses

- SMC patterns are easy to overfit. The analyser must expose raw events; the
  optimiser decides whether they deserve weight.
- LuxAlgo's indicator is visual and stateful. Python replay must preserve the
  known-at timing, not the chart placement.
