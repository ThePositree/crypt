# Engine: smc_liquidity

## Purpose

Models liquidity grabs around equal highs/lows and recent swing levels. It is
candle-only and acts mainly as a reversal/confluence engine.

## Inputs

- `ctx.candles[H4]` — closed H4 candles (required, ≥ 260 preferred).

## Output (`Signal`)

- `engine`: `"smc_liquidity"`
- `direction`:
  - `bearish` when price sweeps an equal/swing high and closes back below it.
  - `bullish` when price sweeps an equal/swing low and closes back above it.
  - `neutral` otherwise.
- `strength`:
  - `0.55` for equal high/low sweep;
  - `0.70` for swing high/low sweep;
  - +0.10 if sweep rejects with candle body in the signal direction;
  - sign by direction.
- `confidence`: `0.45 + abs(strength) * 0.35`, clipped to `[0, 0.80]`.
- `meta`: `swept_level`, `level_type`, `event_time`, `wick_distance_atr`.

## Logic

```text
state = analyse_smc(h4, tick_time)
event = latest sweep with known_at <= tick_time and age <= 3 H4 bars

if no sweep:
    neutral
else:
    direction = bearish for high sweep, bullish for low sweep
```

## Edge cases

- Sweeps older than 3 H4 bars do not emit a fresh signal.
- If both high and low are swept on the same candle, neutral unless candle
  close is clearly in one rejection direction (`body > 0.5 * range`).
- Equal highs/lows require ATR-scaled tolerance so low-volatility symbols do
  not overproduce levels.

## Tests

- Sweep high with close back below emits bearish.
- Sweep low with close back above emits bullish.
- Equal high detection respects ATR tolerance.
- Same-candle ambiguous double sweep is neutral.

## Known weaknesses

- Sweep signals are reversal-biased and can fight strong trends. Aggregator
  weights should normally be lower in TRENDING regimes unless backtest proves
  otherwise.
