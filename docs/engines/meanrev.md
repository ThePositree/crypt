# Engine: meanrev

## Purpose

Models the mean-reversion / contrarian trader. Fades local extremes in
ranges. Systematically loses in trends — regime detector and the
aggregator's regime-conditional weights are responsible for muzzling it
when trend conditions dominate.

## Inputs

- `ctx.candles[H4]` — last ≥ 50 closed H4 candles (required).

## Output (`Signal`)

- `engine`: `"meanrev"`
- `direction`:
  - `bullish` when `RSI14_H4 ≤ 30` **and** `close ≤ lower Bollinger Band(20, 2)`.
  - `bearish` when `RSI14_H4 ≥ 70` **and** `close ≥ upper Bollinger Band(20, 2)`.
  - `neutral` otherwise.
- `strength`: signed; magnitude grows with both:
  - RSI extremity beyond 30/70;
  - %B distance from the BB (how far outside the band).

  ```text
  rsi_extreme = max(0, 30 - rsi14) + max(0, rsi14 - 70)   # 0..30
  bb_extreme  = max(0, (lowerBB - close) / (mid - lowerBB)) +
                max(0, (close - upperBB) / (upperBB - mid))
  raw         = clip((rsi_extreme / 30 + bb_extreme) / 2, 0, 1)
  strength    = -raw if rsi14 >= 70 else raw if rsi14 <= 30 else 0
  ```
- `confidence`:
  - base 0.4;
  - +0.2 if regime detector says `RANGING`;
  - −0.3 if regime detector says `TRENDING`;
  - −0.2 if regime detector says `HIGH_VOL`;
  - +0.1 if RSI has been in extreme territory for ≤ 2 consecutive candles
    (early fade is better than late).

## Logic

```text
closed_h4 = ctx.candles[H4][:-1]
if len(closed_h4) < 50:
    return neutral(missing=["candles[H4]"])

rsi14   = rsi(closed_h4.close, 14)
bb_mid, bb_up, bb_low = bollinger(closed_h4.close, 20, 2)
close   = closed_h4.close[-1]

oversold   = rsi14 <= 30 and close <= bb_low
overbought = rsi14 >= 70 and close >= bb_up
...
```

## Edge cases

- Strong trend with RSI > 70 for many candles in a row ⇒ this engine will
  still emit `bearish`. That is fine: the aggregator down-weights it in
  `TRENDING` regime. We do not introduce ad-hoc trend filters here —
  separation of concerns.
- `bb_up == bb_mid` (zero volatility window, e.g. exchange outage) ⇒
  `neutral` with `inputs_missing=["bollinger"]`.

## Tests

`tests/engines/test_meanrev.py`:

- Constructed oversold series (RSI < 30, close below lower BB) ⇒ `bullish`.
- Constructed overbought series ⇒ `bearish`.
- Pure trend with RSI rising from 50→80 across 10 candles ⇒ direction is
  `bearish` but `confidence < 0.4` if we inject `Regime.TRENDING`.
- Zero-variance series ⇒ `neutral`.

## Known weaknesses

- "Buying oversold" in crypto is a famously expensive habit. The 4h
  timeframe is the friendliest — sub-1h mean-reversion in crypto is mostly
  noise — but expect this engine to underperform in any extended trend.
- RSI(14) and BB(20, 2) are deliberately textbook so the system is
  interpretable. We are not trying to be original at the indicator level.
