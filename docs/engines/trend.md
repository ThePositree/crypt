# Engine: trend

## Purpose

Models the trend-follower view. Trades the direction of the prevailing
medium-term move. Loses systematically in ranges — that is why we have a
regime detector.

## Inputs

- `ctx.candles[H4]` — last ≥ 200 closed H4 candles (required).
- `ctx.candles[D1]` — last ≥ 60 closed D1 candles (optional; only used for
  higher-timeframe alignment bonus).

## Output (`Signal`)

- `engine`: `"trend"`
- `direction`:
  - `bullish` when `EMA50_H4 > EMA200_H4` and ADX(14) on H4 ≥ 18.
  - `bearish` when `EMA50_H4 < EMA200_H4` and ADX(14) on H4 ≥ 18.
  - `neutral` otherwise.
- `strength`: signed; magnitude grows with the EMA gap normalised by ATR(14)
  and with ADX. Capped at ±1:
  - `raw = sign(EMA50 - EMA200) * min(1.0, |EMA50 - EMA200| / (3 * ATR14))`
  - `strength = raw * clip(ADX14 / 30, 0, 1)`
- `confidence`:
  - base 0.5;
  - +0.2 if direction agrees with EMA50_D1 vs EMA200_D1 (higher-timeframe
    confluence);
  - +0.1 if `ADX14 ≥ 25`;
  - −0.2 if regime detector says `RANGING` (the aggregator already
    down-weights us; this is a secondary penalty kept inside the engine for
    sanity).

## Logic

```text
closed_h4 = ctx.candles[H4][:-1]      # drop the forming candle
ema50  = ema(closed_h4.close, 50)
ema200 = ema(closed_h4.close, 200)
adx14  = adx(closed_h4, 14)
atr14  = atr(closed_h4, 14)

if len(closed_h4) < 200 or adx14 is None:
    return neutral(rationale="not enough H4 history", missing=["candles[H4]"])

if ema50 > ema200 and adx14 >= 18:
    direction = bullish
elif ema50 < ema200 and adx14 >= 18:
    direction = bearish
else:
    direction = neutral

strength   = ... (see formula above)
confidence = ... (see formula above)
```

## Edge cases

- Insufficient history → `neutral`, `confidence=0`,
  `inputs_missing=["candles[H4]"]`.
- ADX `None` (extremely low movement) → `neutral`.
- D1 missing → skip the higher-timeframe bonus; do not fail.

## Tests

`tests/engines/test_trend.py`:

- Pure uptrend OHLC ⇒ `bullish`, `strength > 0.5`, `confidence ≥ 0.6`.
- Pure downtrend ⇒ `bearish`.
- Sideways OHLC with low ADX ⇒ `neutral`.
- < 200 candles ⇒ `neutral` with `inputs_missing`.
- Sharp reversal candle does not flip direction if EMA50/EMA200 still agree.

## Known weaknesses

- ADX-gated EMA crossover is a textbook signal, fully priced in by HFT
  market makers. The edge — if any — comes from the ensemble vote, not from
  this engine alone.
- Whip-saws on consolidations near `EMA50 ≈ EMA200`. Mitigated only
  partially by ADX gate. Regime layer is the real fix.
- EMA200 on H4 requires ~33 days of warm-up. First runs must bootstrap
  history; see BACKLOG P1 item.
