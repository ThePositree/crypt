# Engine: derivatives

## Purpose

Models the derivatives positioning view: open interest momentum and
top-trader long/short account ratio. Captures *how much conviction the
market has* in the current direction and whether large traders are
positioned at an extreme.

> **Note (ADR-0016, 2026-06-01):** Funding rate sub-signal removed.
> OKX settlement intervals vary per contract (1 h / 2 h / 4 h / 8 h) and
> changed without notice in April 2025. The z-score window was
> interval-dependent, creating silent train/live skew. OKX native funding
> history depth is also only ~3 months — insufficient for M2 calibration.
> See `docs/decisions/0016-drop-funding-fix-oi-endpoint.md`.

## Inputs

- `ctx.oi[symbol][1h]` — last ~200 hourly OI snapshots (required; data
  available to Feb 2024 via OKX `/rubik/stat/contracts/open-interest-history`
  after ADR-0016 endpoint fix).
- `ctx.ls_ratio[symbol]` — last 100 hourly top-trader account L/S ratio
  snapshots (optional; degrades gracefully if missing; data available to
  Feb 2024 via OKX `/rubik/stat/contracts/long-short-account-ratio-contract`).
- `ctx.candles[H4]` — price direction for OI momentum sign (required by
  `_oi_signal`; falls back to 0 if missing).

## Output (`Signal`)

- `engine`: `"derivatives"`
- `direction`: composite — see logic below.
- `strength`: weighted sum of two sub-components, clipped to `[-1, +1]`.
- `confidence`:
  - base 0.5;
  - +0.2 if both sub-components agree on direction;
  - −0.3 if `inputs_missing` contains `oi` (OI is the primary input);
  - −0.2 if `inputs_missing` contains `ls_ratio`.

## Logic

Two sub-signals, each in `[-1, +1]`, combined with fixed weights:

### a) Open Interest momentum (trend confirmation) — weight 0.67

- Δ%OI(4h) = (OI_now / OI_4h_ago − 1).
- `oi_signal = sign(close_change_4h) × clip(|ΔOI%| / 0.05, 0, 1)`
  (rising OI aligned with price ⇒ trend-confirming; rising OI against price
  ⇒ weak counter-signal).
- *Important:* OI alone is direction-less; the sign comes from the
  simultaneous H4 price move.

### b) Top-trader L/S ratio extremity (contrarian) — weight 0.33

- `ls_z = (ls_now − mean_48h) / std_48h`.
- `ls_signal = −clip(ls_z / 3, −1, +1)`.
  (extreme long positioning ⇒ contrarian bearish; extreme short ⇒ contrarian bullish).

### Combination

```text
strength = clip(0.67 × oi_signal + 0.33 × ls_signal, −1, +1)

if   strength >=  0.25: direction = bullish
elif strength <= −0.25: direction = bearish
else:                   direction = neutral
```

If `oi` is missing, the engine returns `neutral` immediately (OI is
the primary input; LS alone does not justify a signal).

If `ls_ratio` is missing, the engine runs on OI only (weight 1.0),
confidence reduced by 0.2.

### Weight rebalancing

```text
Both present:     oi=0.67, ls=0.33   (nominal)
ls_ratio missing: oi=1.00, ls=0.00   (OI only)
oi missing:       neutral immediately (cannot run)
```

## Edge cases

- OI history < 5 points ⇒ `oi` added to `inputs_missing`; engine returns
  neutral.
- LS ratio history < 2 points ⇒ `ls_ratio` added to `inputs_missing`;
  engine runs on OI only.
- H4 candles missing ⇒ `price_sign = 0`; OI magnitude still contributes
  to confidence, but strength stays near 0.

## Tests

`tests/engines/test_derivatives.py`:

- OI rising sharply with price rising ⇒ `bullish`.
- OI falling with price falling ⇒ `bearish`.
- Top-trader L/S ratio extreme long ⇒ contributes a `bearish` push.
- OI and LS agreeing ⇒ `confidence >= 0.7`.
- Missing OI ⇒ `neutral`, `inputs_missing=["oi"]`.
- Missing LS ratio ⇒ engine runs on OI alone, `confidence -= 0.2`.

## Known weaknesses

- OI as "trend confirmation × price" cannot distinguish opening longs from
  closing shorts. Both scenarios produce the same delta-OI signal.
- L/S ratio from OKX is a *sample* (top traders only), not the full market.
  Its predictive value is limited; weight is intentionally low.
- Without funding extremity, the engine loses the "market is overleveraged"
  contrarian signal. This is a known gap accepted in ADR-0016; revisit after
  M2 calibration.
- OI data has a hard floor at early February 2024 from OKX. Backtest
  windows starting before that date will have missing OI for the pre-Feb-2024
  segment.
