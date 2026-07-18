# Engine: liquidations

Status: **deferred, reconsidered**. Original ADR-0006 deferred this
engine because OKX's `liquidation-orders` is WebSocket-only and our MVP
is REST-only (ADR-0004). ADR-0012 records the reconsideration and lists
three viable implementation paths. Pick one when implementing.

This file is the engine spec; ADR-0012 is the *which path* decision.

---

## Purpose

Models the "stop-cascade trader" view. Forced liquidations on perpetual
swaps are involuntary order flow: longs being liquidated must sell,
shorts being liquidated must buy. Concentrated liquidation events
produce two effects:

1. **Reflexive price move** in the direction of the liquidations
   (cascade).
2. **Mean-reversion candidate** *after* the cascade exhausts (the move
   was caused by liquidations, not new information).

The edge is contrarian *after* a cascade, but only when the cascade is
big enough to be exhausting (not a small bleed). The threshold is the
hard part.

---

## Data source — three paths

ADR-0012 picks one of these; this file specifies the engine independent
of the choice.

### Path A — OKX WebSocket `liquidation-orders` channel

- Pro: free, primary venue (matches everything else in the system).
- Pro: real-time stream, no polling waste.
- Con: introduces a long-running WS process. ADR-0004 explicitly chose
  REST-only for the MVP. This is a 14-day-run-stability question.
- Con: WS sessions drop. We'd need reconnect-with-backoff that does not
  lose events during reconnects.

### Path B — Coinglass freemium API

- Pro: REST only, fits ADR-0004.
- Pro: aggregated across venues (BTC long liquidations on Bybit + OKX +
  Binance combined → bigger sample, less venue-specific noise).
- Con: rate-limited (latest freemium tier ≈ 30 req/min); we have to ask
  Context7 for the current limit and endpoints at implementation time.
- Con: external vendor in critical path. Mitigate with caching.

### Path C — `ccxt`-mediated polling against multiple venues' liquidation
endpoints

- Pro: free.
- Con: some venues are WS-only (OKX), some are REST (Bybit), and `ccxt`
  abstracts the difference imperfectly.
- Con: maintaining the multi-venue fetch logic ourselves duplicates
  Coinglass's work poorly.

Default recommendation (ADR-0012): **Path B**, until rate limit becomes
binding, then revisit Path A.

---

## Inputs

- `ctx.liquidations[symbol]` — last 7 days of 1h liquidation buckets
  with two fields per bucket:
  - `long_usd`: USD-equivalent volume of long liquidations.
  - `short_usd`: USD-equivalent volume of short liquidations.

Required: at least 168 hourly points (7 days) for the z-score baseline.

---

## Output (`Signal`)

- `engine`: `"liquidations"`
- `direction`: contrarian to the dominant side of the last 4h cascade.
  - `bullish` if `long_usd_4h` is mean + 2σ AND `short_usd_4h < long_usd_4h / 2`.
    Reading: longs got blown up disproportionately → forced sells exhausted →
    reversal candidate.
  - `bearish` if mirrored.
  - `neutral` otherwise.
- `strength`:
  ```
  side_dominant_usd = max(long_usd_4h, short_usd_4h)
  z = (side_dominant_usd - mean_7d) / std_7d
  imbalance = (long_usd_4h - short_usd_4h) / (long_usd_4h + short_usd_4h)
  raw = clip(z / 5, 0, 1)          # 5σ event saturates strength
  strength = -sign(imbalance) * raw  # contrarian to side that got blown up
  ```
- `confidence`:
  - base `0.5`;
  - `+0.2` if z `≥ 3` (rare event, more reliable contrarian);
  - `+0.1` if regime detector says `HIGH_VOL` (cascades are most
    informative in high vol);
  - `-0.3` if `inputs_missing` contains `liquidations`.

---

## Logic

```text
liqs_4h = ctx.liquidations[symbol].window("4h")
liqs_7d = ctx.liquidations[symbol].window("7d")

long_usd_4h  = sum(b.long_usd  for b in liqs_4h)
short_usd_4h = sum(b.short_usd for b in liqs_4h)

# Rolling mean/std over 4h windows in the last 7 days, excluding the
# current 4h bucket.
mean_7d, std_7d = rolling_4h_stats(liqs_7d[:-1])

side_dominant_usd = max(long_usd_4h, short_usd_4h)
z = (side_dominant_usd - mean_7d) / std_7d

if   long_usd_4h > 2 * short_usd_4h and z >= 2.0:  direction = bullish
elif short_usd_4h > 2 * long_usd_4h and z >= 2.0:  direction = bearish
else:                                              direction = neutral

# strength as above
```

---

## Edge cases

- Less than 7 days of history → `neutral`,
  `inputs_missing=["liquidations"]`. Do NOT raise.
- All-zero history (low-volume symbol) → `neutral`. Don't divide by zero
  std; treat 0 std as "missing".
- One-sided extreme (`long_usd_4h = 1e9, short_usd_4h = 0`): clip the
  imbalance ratio numerator/denominator to avoid divide-by-zero when
  summing.
- A single venue outage in the multi-venue source (Path B) → labelled in
  `rationale`, otherwise tolerated.

---

## Aggregator integration

Sketched weights (placeholder; M2 calibrates):

```yaml
TRENDING:    { trend: 0.50, meanrev: 0.05, derivatives: 0.25, liquidations: 0.10, volatility: 0.10 }
RANGING:     { trend: 0.15, meanrev: 0.40, derivatives: 0.20, liquidations: 0.15, volatility: 0.10 }
HIGH_VOL:    { trend: 0.15, meanrev: 0.10, derivatives: 0.25, liquidations: 0.20, volatility: 0.30 }
```

Liquidations are weighted heaviest in `HIGH_VOL` regime — that is where
cascades happen and where contrarian timing is most rewarded.

---

## Decision-layer integration

This engine is **not** critical for the inputs-missing guard. A failure
of the liquidation feed should reduce the verdict's confidence but
never block alerts entirely.

---

## Tests

`tests/engines/test_liquidations.md`:

- Synthetic: stable baseline, then a 4h bucket with `long_usd = 10x
  baseline` → `bullish` with `strength ≈ +0.8`.
- Mirrored: stable baseline, then a 4h bucket with `short_usd = 10x
  baseline` → `bearish`.
- Symmetric cascade (`long ≈ short`, both elevated) → `neutral`
  (imbalance gate not met).
- Zero history → `neutral`, `inputs_missing` populated.
- Vendor outage simulation → `neutral` with marked rationale.

---

## Background polling (Path B)

Like sentiment, liquidation polling is NOT on the tick critical path:

- Every 5 min: fetch latest 1h bucket from Coinglass, append to
  `data/<symbol>/liquidations.parquet`.
- Each tick: read parquet via `ContextBuilder`.

If Path A (OKX WS) is chosen instead, the long-running WS listener
appends events to the same parquet file in real time.

---

## Known weaknesses

- Liquidations data quality varies wildly between aggregators. Two
  vendors can report different aggregate volumes for the same hour by
  factors of 2 or more. M2 must include a sanity check (e.g. compare
  Coinglass vs CCXT-derived volumes for the same window).
- "Cascade exhaustion → reversal" is a folk model. In strong trends,
  liquidation cascades **continue** the move rather than reversing it.
  The regime-weight should heavily under-weight this engine in
  `TRENDING` regime — which the placeholder weights do.
- Path B introduces an external vendor with its own rate limits and
  outages. If Coinglass changes pricing, we lose the engine. Architect
  for swapability: the engine reads from `data/<symbol>/liquidations.parquet`,
  it does not care who put the data there.
- Z-score normalisation against a 7-day rolling baseline means the
  engine is **always** finding "extreme" events because the baseline
  drifts with each cascade. Watch for this in the M2 hit-rate analysis;
  consider a longer or fixed-window baseline if the issue is real.
