# Engine: volatility

## Purpose

This engine is **not directional**. It outputs a regime hint and a
risk-side adjustment. Its `direction` is always `neutral`. Its purpose in
the ensemble is to (a) feed the regime detector, (b) act as a confidence
multiplier — high volatility reduces confidence in any directional signal,
because expected slippage and noise rise.

## Inputs

- `ctx.candles[H4]` — last ≥ 60 closed H4 candles (required).
- `ctx.candles[D1]` — last ≥ 60 closed D1 candles (optional).

## Output (`Signal`)

- `engine`: `"volatility"`
- `direction`: always `neutral`.
- `strength`: always 0.
- `confidence`: always 0 — this engine does not contribute to the
  weighted-sum score directly.
- `rationale`: includes the computed values so the verdict-explanation
  can show them.
- **Extra payload on the Signal** (kept in `rationale` lines or in a
  dedicated `meta` dict): `atr_pct`, `atr_pct_rank_60d`, `vol_regime` ∈
  {`"low"`, `"normal"`, `"high"`}.

The aggregator reads `meta.vol_regime` to:

- multiply `confidence` of trend / meanrev / derivatives signals by a
  factor (e.g. 1.0 in `normal`, 0.85 in `high`, 0.95 in `low`),
- and (alongside the regime detector) influence the `Regime` choice.

## Logic

```text
closed_h4 = ctx.candles[H4][:-1]
atr14_h4    = atr(closed_h4, 14)
atr_pct     = atr14_h4 / closed_h4.close[-1]

# Rank over last 60 days of H4 candles (60 * 6 = 360 samples).
atr_pct_rank_60d = rank_pct(atr_pct, recent=360)

if atr_pct_rank_60d > 0.85:
    vol_regime = "high"
elif atr_pct_rank_60d < 0.15:
    vol_regime = "low"
else:
    vol_regime = "normal"
```

## Edge cases

- < 60 H4 candles (i.e. cannot rank reliably) ⇒ `vol_regime = "normal"` and
  `inputs_missing=["candles[H4]"]`. We still emit a Signal so the
  aggregator does not crash.
- All ATR values identical (flat-line) ⇒ `vol_regime = "low"`.

## Tests

`tests/engines/test_volatility.py`:

- Synthetic series with stable 1% ATR ⇒ `vol_regime ∈ {"low", "normal"}`
  depending on history.
- Synthetic spike at the end of the series ⇒ `vol_regime = "high"`.
- < 60 candles ⇒ `vol_regime = "normal"` and `inputs_missing` populated.

## Known weaknesses

- ATR percent-rank is a coarse summary. It does not distinguish a slow
  grind-up from a violent two-sided chop with the same realised volatility.
- Volatility regimes regime-shift in crypto rapidly (e.g. ETF news,
  exchange outages). The 60-day window is a compromise; calibrated in M2.
