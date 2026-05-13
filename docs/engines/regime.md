# Engine: regime

## Purpose

Classifies the current state of the symbol so the aggregator can pick the
right weight set. Outputs **one of**:

- `TRENDING` — sustained directional movement.
- `RANGING` — bounded oscillation.
- `HIGH_VOL` — large two-sided moves dominate; both trend and meanrev are
  unreliable.

Unlike trend / meanrev / derivatives, this engine does not contribute to
the weighted-sum score. Its sole output is the `Regime` used to look up
weights and per-regime thresholds.

## Inputs

- `ctx.candles[H4]` — last ≥ 60 closed H4 candles (required).
- `ctx.candles[D1]` — last ≥ 30 closed D1 candles (recommended).
- The `vol_regime` payload from the volatility engine (passed in via
  context, computed earlier in the same tick).

## Output

- A `Regime` enum value, returned alongside the Signal stream from the
  orchestrator. For uniformity, the engine *also* emits a `Signal` with:
  - `engine`: `"regime"`,
  - `direction`: `neutral`,
  - `strength`: 0,
  - `confidence`: 0,
  - `rationale`: includes the chosen regime and the values used.
  - extra `meta`: `{"regime": "TRENDING" | "RANGING" | "HIGH_VOL"}`.

## Logic

```text
adx_h4 = adx(closed_h4, 14)
adx_d1 = adx(closed_d1, 14) if closed_d1 else None
vol_regime = ctx.vol_regime    # produced by the volatility engine

# 1) HIGH_VOL has priority: very volatile chop is its own thing.
if vol_regime == "high" and (adx_h4 is None or adx_h4 < 25):
    return HIGH_VOL

# 2) Otherwise trend vs range from ADX.
if adx_h4 is not None and adx_h4 >= 22:
    if adx_d1 is None or adx_d1 >= 18:
        return TRENDING
    return RANGING

return RANGING
```

`HIGH_VOL` takes priority over `TRENDING` only when ADX itself is not
clearly trending — otherwise a strong trend with high realised volatility
is still a trend.

## Edge cases

- Missing H4 ADX (insufficient history) ⇒ default to `RANGING`. Reflected
  in `inputs_missing`.
- Conflict between H4 and D1 ADX (H4 strong, D1 weak) ⇒ `RANGING`. This is
  intentionally cautious: in micro-trends, mean-reversion still works
  better than trend.

## Tests

`tests/engines/test_regime.py`:

- Pure synthetic uptrend with ADX_h4 = 30, ADX_d1 = 25 ⇒ `TRENDING`.
- Sine-wave OHLC ⇒ `RANGING`.
- Spiky chop with vol_regime = "high" and ADX < 20 ⇒ `HIGH_VOL`.
- < 60 H4 candles ⇒ `RANGING` with `inputs_missing` populated.

## Known weaknesses

- ADX is a lagging indicator. Regime switches lag behind reality by several
  bars. Acceptable at 4h; would be unacceptable on 1m.
- Three regimes is a coarse abstraction. We accept this for explainability;
  a richer hidden-state model would be M5+ territory.
- The thresholds (18, 22, 25) are *placeholders*. They must be calibrated
  in M2 against historical OKX H4 data for the three target symbols.
