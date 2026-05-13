# Engine: derivatives

## Purpose

Models the derivatives positioning trader: funding rate, open interest,
and top-trader long/short ratio. Captures *who is paying for the
positioning* and how much.

## Inputs

- `ctx.funding[symbol]` — current funding rate + last 7 days of history
  (required).
- `ctx.oi[symbol][1h]` — last 168 hourly OI points (≥ 7 days; required).
- `ctx.ls_ratio[symbol]` — last 48 hourly top-trader account L/S ratio
  points (optional; degrade if missing).

## Output (`Signal`)

- `engine`: `"derivatives"`
- `direction`: composite, see logic below.
- `strength`: weighted sum of three sub-components, clipped to `[-1, +1]`.
- `confidence`:
  - base 0.5;
  - +0.2 if all three sub-components agree on direction;
  - −0.2 if `inputs_missing` contains `ls_ratio`;
  - −0.3 if `inputs_missing` contains `oi` (funding alone is too weak).

## Logic

Three sub-signals are computed, each in `[-1, +1]`, then combined:

### a) Funding extremity (contrarian)

- Normalise funding against its own 7-day standard deviation:
  `f_z = (current_funding - mean_7d) / std_7d`.
- `funding_signal = -clip(f_z / 3, -1, +1)`
  (positive funding extreme ⇒ longs paying ⇒ contrarian *bearish* push;
   sign inverted).
- A *small* funding skew is informational at best; only ±2σ moves register
  meaningfully.

### b) Open Interest momentum (trend confirmation)

- Δ%OI(4h) = (OI_now / OI_4h_ago - 1).
- `oi_signal = sign(close_change_4h) * clip(|ΔOI%| / 0.05, 0, 1)`
  (rising OI in the direction of price ⇒ trend-confirming; rising OI
  against price ⇒ contrarian, magnitude same).
- *Important*: OI alone is direction-less. It only earns a sign by being
  combined with the recent price move.

### c) Top-trader L/S ratio (mild contrarian)

- `ls_z = (ls_now - mean_48h) / std_48h`.
- `ls_signal = -clip(ls_z / 3, -1, +1)`.

### Combination

```text
strength = clip(0.4 * funding_signal +
                0.4 * oi_signal +
                0.2 * ls_signal, -1, +1)

if   strength >=  0.25: direction = bullish
elif strength <= -0.25: direction = bearish
else:                   direction = neutral
```

Rationale strings always include all three sub-values for explainability.

## Edge cases

- Missing OI ⇒ rebalance weights to funding 0.7, ls 0.3, halve confidence,
  put `oi` in `inputs_missing`.
- Missing L/S ratio ⇒ rebalance weights to funding 0.5, OI 0.5.
- Missing funding (should not happen on OKX, but...) ⇒ `neutral`.
- Less than 48h of history for any series ⇒ that sub-signal contributes 0
  but the engine still runs on the others.

## Tests

`tests/engines/test_derivatives.py`:

- Extreme positive funding (z = +3) with no other inputs ⇒ `bearish`,
  reduced confidence.
- OI rising sharply with price rising ⇒ `bullish`.
- Top-trader L/S ratio extreme high ⇒ contributes a `bearish` push.
- Two sub-signals agreeing, third disagreeing ⇒ direction follows the
  weighted majority.
- Missing OI ⇒ `inputs_missing=["oi"]`, halved confidence.

## Known weaknesses

- Treating funding as contrarian *on the sign* is folk wisdom; the real
  effect lives at the tails, hence the z-score gate and small unit weight.
- OI as "trend confirmation × price" is a coarse proxy for "increasing
  conviction in the direction" — it cannot distinguish opening longs from
  closing shorts.
- L/S ratio from OKX is a *sample* (top traders), not the market. Its
  predictive value is small and often inverted; we keep its weight low.
- All three series are sensitive to large-fee exchange events
  (funding-rate caps, OI snapshot timing). Z-score normalisation absorbs
  some of this; not all.
