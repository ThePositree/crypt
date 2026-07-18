# Engine: sentiment

Status: **deferred** (BACKLOG P2 → implement after M2 weight calibration).

This is a spec for a future engine. The agent who implements it should
read this end-to-end, then `docs/engines/trend.md` for the existing
engine pattern, then `docs/architecture.md` §3 for data contracts.

---

## Purpose

Captures the "news / social mood" trader view. Crypto reacts strongly to
narratives, especially around regulatory events, large hacks, exchange
listings, and macro Fed days. A textbook EMA crossover engine has no way
to see "the SEC just rejected a 19b-4 filing" before the price moves; a
sentiment engine does.

The expected edge is **small but real at extremes**. We do not chase
day-to-day Twitter noise; we look for sustained skew (z-score across a
rolling baseline).

---

## Data source

**Primary candidate**: CryptoPanic freemium API
(<https://cryptopanic.com/developers/api/>).

- Free tier: 200 requests/day, 50 requests/min, all posts JSON.
- Endpoints used:
  - `GET /api/v1/posts/?auth_token=...&currencies=BTC,SOL,TON&kind=news&public=true`
- Returns a list of news posts with fields: `title`, `published_at`,
  `votes` (positive/negative/important/liked/disliked/lol/toxic/saved),
  `domain`, `currencies` (tickers tagged).

Alternative sources (lower priority, listed in case CryptoPanic
free-tier becomes insufficient):
- LunarCrush v4 free tier (sentiment time-series; throttled).
- Twitter API v2 (paid since 2023 — out of 0$ budget).
- Reddit API (free; but signal-to-noise is much worse and it has its
  own rate limits).

**Use Context7 (`/cryptopanic/api/docs` if available, otherwise generic
crypto-news APIs) before writing the fetcher**, because the API surface
and rate limits may have changed.

---

## Inputs

- `ctx.sentiment[symbol]` — last 7 days of hourly sentiment buckets
  (≥ 168 points required for z-score stability).
- The mapping from OKX `instId` to CryptoPanic currency tag must be
  explicit in a config map:
  ```python
  _SYMBOL_TO_TAG = {
      "SOL-USDT-SWAP": "SOL",
      "TON-USDT-SWAP": "TON",
      "XPL-USDT-SWAP": None,        # not on CryptoPanic, will degrade
      "BTC-USDT-SWAP": "BTC",       # for BTC context engine (separate spec)
  }
  ```

A new data type and ingestor method are required (see §8).

---

## Output (`Signal`)

- `engine`: `"sentiment"`
- `direction`:
  - `bullish` when 24h sentiment z-score `≥ +1.0` AND non-trivial volume
    (`n_posts_24h ≥ 20`).
  - `bearish` when 24h sentiment z-score `≤ -1.0` AND `n_posts_24h ≥ 20`.
  - `neutral` otherwise.
- `strength`:
  ```
  raw      = sign(z_24h) * clip(|z_24h| / 3, 0, 1)
  vol_mult = clip(n_posts_24h / 50, 0, 1)
  strength = raw * vol_mult
  ```
  Low news volume should not produce a strong signal even if z is large
  (a single salacious tweet should not steer a swing trade).
- `confidence`:
  - base `0.4`;
  - `+0.2` if `|z_72h| ≥ 1.0` and `sign(z_72h) == sign(z_24h)` (sustained
    skew);
  - `-0.2` if the symbol's currency tag is `None` (we fell back to BTC
    sentiment as a proxy);
  - `-0.3` if `inputs_missing` contains `sentiment` (engine ran on cached
    stale data > 6h old).

---

## Logic

```text
posts_24h = ctx.sentiment[symbol].window("24h")
posts_7d  = ctx.sentiment[symbol].window("7d")

score_per_post = +1 * vote.positive + 1.5 * vote.important
                 - 1 * vote.negative - 2 * vote.toxic
score_24h = sum(score_per_post for posts_24h)
mean_7d   = mean over rolling 24h windows of score_24h, last 7 days
std_7d    = stdev over the same windows

z_24h = (score_24h - mean_7d) / std_7d
z_72h = ... same computation over 72h window
n_posts_24h = len(posts_24h)
```

The vote weights (`+1`, `+1.5`, ...) are placeholder, calibrated in M2.

---

## Edge cases

- API returns empty list (no news in window) → `neutral`,
  `inputs_missing=["sentiment"]`, conf `= 0`. Do NOT raise.
- API rate-limited (HTTP 429) → use cached data, log WARNING, mark
  `inputs_missing=["sentiment_fresh"]`.
- Symbol has no currency tag → degrade to BTC sentiment as a coarse
  proxy. Document this in `rationale`.
- Sudden burst of 200+ posts in 1h (e.g. major news event) → cap
  `n_posts_24h` at `200` to avoid one event dominating multiple ticks.

---

## Tests

`tests/engines/test_sentiment.py`:

- Synthetic posts with mean = 0, last 24h burst of positive votes
  (z = +3) and 50 posts → `bullish`, `strength > 0.5`, `conf ≥ 0.6`.
- Same z but only 5 posts → low `strength` (volume gate).
- All zero votes 7 days → `neutral`, low confidence.
- Empty API response → `neutral` with `inputs_missing=["sentiment"]`.
- 429 simulation → engine uses cached data, marks stale.
- XPL (no tag) → falls back to BTC, `inputs_missing=["sentiment"]` not
  set (we have data), but rationale notes "BTC proxy".

---

## Aggregator integration

A new `sentiment` row must be added to `config/weights.yaml`:

```yaml
TRENDING:   { trend: 0.45, meanrev: 0.05, derivatives: 0.30, sentiment: 0.10, volatility: 0.10 }
RANGING:    { trend: 0.10, meanrev: 0.45, derivatives: 0.25, sentiment: 0.10, volatility: 0.10 }
HIGH_VOL:   { trend: 0.15, meanrev: 0.15, derivatives: 0.30, sentiment: 0.10, volatility: 0.30 }
```

Initial values placeholder; **M2 backtest must re-calibrate before this
engine is enabled in live**.

The aggregator does not need code changes — it walks the weight dict.

---

## Decision-layer integration

No new filters. The existing critical-inputs guard
(`docs/engines/decision.md` §3) does NOT promote `sentiment` to critical:
sentiment alone is too noisy to mandate.

---

## Background polling

Sentiment polling is **NOT** tied to the 4h tick. It must run as a
separate background task in `__main__.py`:

- Every 30 min: fetch new posts, append to
  `data/<symbol>/sentiment.parquet`.
- Each tick: read the cached file via `ContextBuilder` (no network call
  inside `evaluate`).

Justification: CryptoPanic rate limit is 50 req/min; we have time. Keeping
sentiment ingestion off the critical tick path means a CryptoPanic
outage cannot delay or fail a tick.

---

## Known weaknesses

- Sentiment APIs go down or get re-priced often. The architectural risk
  is that this engine has an external vendor in its critical path.
  Mitigation: cached data is reused for up to 6h; after that the engine
  emits `neutral` with reduced confidence.
- News volume is heavily skewed by listing announcements, ETF cycles,
  and hack post-mortems. A simple z-score normalisation will mark large
  events as `bullish` or `bearish` based on subjective vote tallies,
  which are themselves gamed.
- Vote weights are placeholders. There is no ground truth; M2 must run
  ablations: `(vote_pos - vote_neg)` vs `(vote_pos - 2*vote_toxic)` etc,
  pick the variant with the best test-slice expectancy.
- This engine cannot run for XPL until either a tag is added on
  CryptoPanic or we accept BTC-as-proxy. Be explicit in the report.

---

## Implementation order

1. Verify CryptoPanic free-tier still exists and has the documented
   surface (Context7).
2. Add `SentimentPost` and `SentimentSnapshot` to `crypt/models.py`.
3. Add `fetch_sentiment(symbol, since)` to `ExchangeClient`-like
   interface, but in a separate `crypt/external/cryptopanic.py` module
   (it is NOT an exchange).
4. Add `SentimentStore.save/load` to `crypt/data/store.py`.
5. Add the background polling task in `__main__.py`.
6. Write `crypt/engines/sentiment.py`.
7. Add config keys to `Settings` (API token, refresh interval).
8. Re-run M2 backtest harness to recalibrate weights with the new engine.
