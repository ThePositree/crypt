# Engine: btc_context

Status: **proposed, post-M2** (BACKLOG P1 — high value, low cost).

This engine is a **filter / context source**, not a strong standalone
directional signal. It models the well-documented fact that, on a 4h
horizon, mid-cap altcoins (SOL, TON, ETH-ratio assets) follow BTC with
correlation in the 0.5–0.9 range; XPL and other small caps have lower
but still meaningful correlation. Trading against BTC is a low-edge
strategy; agreeing with BTC adds a confidence floor.

---

## Purpose

Two functions:

1. **Confidence multiplier**: when the engine's BTC direction agrees
   with a directional engine's symbol direction, multiply confidence by
   `1.10`; when it disagrees, multiply by `0.85`. This is implemented
   inside the engine via `meta.btc_alignment` and consumed by the
   aggregator.
2. **Crisis filter**: when BTC is in a "drawdown regime"
   (defined below), every long alert is suppressed to HOLD by the
   decision layer (similar to the existing critical-inputs guard).

The engine itself emits a `Signal` with `direction = neutral`,
`strength = 0`, `confidence = 0` so that the weighted-sum aggregator
ignores it; the `meta` payload is the entire output.

This pattern matches the existing `volatility` engine — it does not
contribute to the score, it feeds aggregator/regime decisions.

---

## Inputs

- `ctx.btc_candles[H4]` — last ≥ 200 closed H4 BTC candles. Even though
  the orchestrator iterates per-symbol, the BTC candles are loaded once
  per tick and cached in `EvaluationContext` (see §6 implementation).
- `ctx.btc_candles[D1]` — last ≥ 60 closed D1 BTC candles. Optional;
  used for the drawdown-regime check.

---

## Output (`Signal`)

- `engine`: `"btc_context"`
- `direction`: always `neutral`.
- `strength`: always `0`.
- `confidence`: always `0`.
- `rationale`: explicit lines for `btc_direction`, `btc_drawdown_pct`,
  `btc_regime`.
- `meta`:
  ```python
  {
      "btc_direction": "bullish" | "bearish" | "neutral",
      "btc_drawdown_pct": float,            # negative, e.g. -0.07 for -7%
      "btc_regime": "trending_up" | "trending_down" | "ranging" | "crisis",
      "btc_alignment": "agree" | "disagree" | "neutral",
                                            # filled by the aggregator
                                            # for the *current* symbol
  }
  ```

---

## Logic

```text
btc_h4_close = ctx.btc_candles[H4].close
ema20  = ema(btc_h4_close, 20)
ema50  = ema(btc_h4_close, 50)
ema200 = ema(btc_h4_close, 200)
adx14  = adx(ctx.btc_candles[H4], 14)

# 1) Direction
if   ema20 > ema50 > ema200 and adx14 >= 20: btc_direction = bullish
elif ema20 < ema50 < ema200 and adx14 >= 20: btc_direction = bearish
else:                                        btc_direction = neutral

# 2) Drawdown from 30d high (close-to-close).
high_30d = max(btc_h4_close[-180:])  # 30 days * 6 H4 bars
btc_drawdown_pct = (btc_h4_close[-1] - high_30d) / high_30d

# 3) Regime
if btc_drawdown_pct <= -0.15:                btc_regime = "crisis"
elif btc_direction == bullish:               btc_regime = "trending_up"
elif btc_direction == bearish:               btc_regime = "trending_down"
else:                                        btc_regime = "ranging"
```

Thresholds (`15%` drawdown, `ADX 20`) are placeholders; calibrate in M2.

---

## Aggregator integration

This engine **modifies** how the aggregator computes `confidence` for
*other* engines. Two specific rules:

1. **Alignment bonus/penalty**: After computing the per-symbol score
   `S`, the aggregator looks at `btc_direction`:
   - If `sign(S) == direction_to_signed(btc_direction)`:
     `confidence *= 1.10` (capped at 100).
   - If `sign(S) != direction_to_signed(btc_direction)` and
     `btc_direction != neutral`: `confidence *= 0.85`.
   - If `btc_direction == neutral`: no change.

   Record the multiplier applied in `verdict.rationale`.

2. **Crisis mute** (decision-layer): If `btc_regime == "crisis"` AND
   the symbol verdict is `BUY`, the decision layer must downgrade the
   verdict to `HOLD` and tag rationale with `[BTC crisis: long alerts
   muted]`. Short alerts pass through unchanged.

The aggregator implementation needs a small addition; the decision
filter needs one new guard. Neither change is destructive for existing
engines — both are no-ops when this engine is absent.

---

## Per-symbol special case

`BTC-USDT-SWAP` itself never gets this engine applied (it would compare
BTC's direction to its own direction, trivially). Hard-coded skip in the
orchestrator: if `ctx.symbol == "BTC-USDT-SWAP"`, the engine emits an
empty signal with `meta = {}` and the aggregator skips alignment logic.

---

## Edge cases

- < 200 H4 BTC candles → `btc_direction = neutral`, `btc_regime =
  "ranging"`. Log `inputs_missing=["btc_candles[H4]"]`.
- BTC fetch failed for the current tick → if cached BTC candles exist
  and are < 8h stale, use them and log WARNING. Otherwise neutral.
- Whipsaw at ema20≈ema50≈ema200 → `btc_direction = neutral` (single
  guard already, no extra logic).

---

## Data ingestion

The orchestrator must ingest BTC OHLCV alongside the configured symbols,
even if BTC is not in `SYMBOLS`. Add a constant `_BTC_SYMBOL =
"BTC-USDT-SWAP"` in `crypt/data/ingestor.py` and include it in
`ingest_all` unconditionally.

Storage path: `data/BTC-USDT-SWAP/ohlcv_4h.parquet` etc. — same schema
as the user-facing symbols.

---

## Tests

`tests/engines/test_btc_context.py`:

- Pure uptrend BTC → `btc_direction = bullish`, `btc_regime =
  "trending_up"`.
- BTC at -20% from 30d high, ADX low → `btc_regime = "crisis"`.
- BTC ranging, ADX < 20 → `btc_regime = "ranging"`.
- Symbol BUY + BTC bullish → aggregator applies `*1.10`; verdict
  rationale records "BTC alignment: agree".
- Symbol BUY + BTC bearish → `*0.85`.
- Symbol BUY + BTC `crisis` → decision layer downgrades to HOLD.
- `ctx.symbol == "BTC-USDT-SWAP"` → engine returns trivially, no
  alignment logic.

---

## Known weaknesses

- "BTC leads alts" is a folk wisdom that breaks during alt-specific
  events (e.g. a TON-specific announcement). The 0.10/0.15 multipliers
  are conservative on purpose to limit damage when this assumption is
  wrong.
- The drawdown definition uses a 30-day window. Over a long bear
  market the 30-day high erodes, so "crisis" eventually flips off; this
  is intentional — we do not want to be permanently bearish in a slow
  bear.
- ADX 20 is a low threshold; the engine may flicker between
  `trending_*` and `ranging` near the boundary. This is acceptable
  because the alignment multiplier is small.
- If we later add more engines (sentiment, calendar), the alignment
  multiplier compounds — three different "filters" each multiplying by
  0.85 can collapse confidence below threshold even when the signal is
  strong. Place an explicit cap in the aggregator: the **total**
  filter-multiplier is clamped to `[0.5, 1.5]`.

---

## Implementation order

1. Add `BTC-USDT-SWAP` to the unconditional ingestion list.
2. Extend `EvaluationContext` with `btc_candles: dict[Timeframe,
   pd.DataFrame]`.
3. Write `crypt/engines/btc_context.py` (this spec).
4. Modify `aggregator/ensemble.py` to read `meta.btc_direction` and
   apply the multiplier.
5. Modify `decision/filters.py` to suppress BUY in `crisis` regime.
6. Add tests as above.
7. Re-run M2 backtest harness to confirm the multiplier improves
   expectancy; if not, lower its magnitude or disable.
