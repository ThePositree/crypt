# Backfill — historical data into Parquet

Contract for `python -m crypt.backfill`. Read this before touching backfill
code or adding a new data vendor.

Related ADRs:

- `docs/decisions/0002-okx-only-with-future-fallback.md` — OKX primary;
  read-only third-party fallback allowed with ADR.
- `docs/decisions/0015-coinglass-historical-backfill.md` — Coinglass for
  deep derivatives history (this doc implements that ADR).

---

## 1. Purpose

Populate `data/<SYMBOL>/` Parquet files so the M2 backtest harness and
paper-trading replay have enough history for all engines — especially
`DerivativesEngine`, which needs funding, OI, and long/short ratio.

**Live runtime is unchanged:** the orchestrator keeps fetching from OKX
via `OKXClient`. Coinglass is **backfill-only** (plus a future shared
client for the liquidations engine per ADR-0012).

---

## 2. Storage layout

Default root: `Settings.data_dir` → `data/` (override with `DATA_DIR` env
or `--data-dir`).

| File | Columns | Used by |
|------|---------|---------|
| `ohlcv_4h.parquet` | `open_time, o, h, l, c, volume, closed` | Trend, MeanRev, Regime, Volatility |
| `ohlcv_1h.parquet` | same | Context / warm-up |
| `ohlcv_1d.parquet` | same | Trend, Regime |
| `funding.parquet` | `ts, rate` | DerivativesEngine, ExecutionSim funding model |
| `oi_1h.parquet` | `ts, oi` | DerivativesEngine |
| `ls_ratio_1h.parquet` | `ts, long_ratio, short_ratio` | DerivativesEngine |
| `taker_vol_1h.parquet` | `ts, buy_vol, sell_vol` | Optional; not in MVP engines |

All cross-module payloads are typed models (`FundingSnapshot`, etc.) before
`ParquetStore.save_*`. Never write naked dicts across module boundaries.

**Upsert semantics:** `ParquetStore._upsert` deduplicates on timestamp,
`keep="last"`. Re-running backfill is idempotent. When Coinglass and OKX
both write the same `ts`, **whichever run happened last wins**. Recommended
operator order:

1. Coinglass backfill for the full `[from, to)` window (historical gap).
2. OKX backfill for the same window (overwrites overlapping recent rows
   with exchange-native values).
3. Live bot appends OKX-native rows going forward.

---

## 3. CLI

```bash
PYTHONPATH=src uv run python -m crypt.backfill \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 \
    --to   2026-05-01 \
    [--source okx|coinglass|auto] \
    [--data-types ohlcv,funding,oi,ls_ratio,taker_vol] \
    [--page-size 100] \
    [--max-rps 5] \
    [--data-dir data/]
```

### 3.1 Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--symbol` | required | OKX `instId`, e.g. `SOL-USDT-SWAP` |
| `--from` / `--to` | required | UTC dates `YYYY-MM-DD`; `--to` exclusive |
| `--source` | `auto` | Data vendor selection (see §4) |
| `--data-types` | see §5 | Comma-separated subset |
| `--page-size` | `100` | Records per API page (max 100 OKX; max 1000 Coinglass) |
| `--max-rps` | `5.0` | Client-side rate limit |
| `--data-dir` | `Settings.data_dir` | Parquet root |

Exit `0` on success; `1` on bad args or precondition failure (unknown
symbol on vendor, empty required range).

### 3.2 `--source` behaviour

| Value | OHLCV | funding / oi / ls_ratio / taker_vol |
|-------|-------|-------------------------------------|
| `okx` | OKX | OKX (shallow history — see §6) |
| `coinglass` | OKX | Coinglass API v4 |
| `auto` | OKX | Coinglass when `COINGLASS_API_KEY` set; else OKX |

`auto` is the recommended default for M2 backtest prep: free OHLCV from
OKX, paid deep derivatives from Coinglass when the key is present.

---

## 4. Coinglass integration (ADR-0015)

### 4.1 Configuration

```bash
# .env
COINGLASS_API_KEY=          # required when --source coinglass or auto
COINGLASS_BASE_URL=https://open-api-v4.coinglass.com  # optional override
```

Header on every request: `CG-API-KEY: <key>`.

Resolve API details via Context7 / official docs before implementation:
https://docs.coinglass.com/reference/endpoint-overview

### 4.2 Symbol mapping

Internal symbol stays OKX `instId` in Parquet paths and model payloads
(e.g. `SOL-USDT-SWAP`). Map to Coinglass query params:

| OKX instId | Coinglass `exchange` | Coinglass `symbol` |
|------------|----------------------|--------------------|
| `SOL-USDT-SWAP` | `OKX` | `SOLUSDT` |
| `TON-USDT-SWAP` | `OKX` | `TONUSDT` |
| `XPL-USDT-SWAP` | `OKX` | verify via API* |

\*Before backfilling a symbol, call
`/api/futures/supported-exchange-pairs` (or equivalent) and fail fast with
a clear log if the pair is missing. XPL may not exist on Coinglass at
implementation time — record in backtest report, do not silently skip.

Implementation lives in `src/crypt/exchange/coinglass.py` as
`CoinglassClient` (async HTTP, same retry/backoff patterns as OKX).

### 4.3 Endpoint mapping

All use `interval=1h` unless noted. Paginate with `start_time` /
`end_time` (ms) and `limit` (max 1000). Respect plan rate limits
(see §4.5).

| Parquet | Coinglass endpoint | Field mapping |
|---------|-------------------|---------------|
| `funding.parquet` | `GET /api/futures/funding-rate/history` | `ts` ← `time`; `rate` ← funding rate field (verify OHLC → use `close` if OHLC) |
| `oi_1h.parquet` | `GET /api/futures/open-interest/history` | `ts` ← `time`; `oi` ← `close` (USD, `unit=usd`) |
| `ls_ratio_1h.parquet` | `GET /api/futures/global-long-short-account-ratio/history` | `long_ratio` ← `global_account_long_percent / 100`; `short_ratio` ← `global_account_short_percent / 100` |
| `taker_vol_1h.parquet` | `GET /api/futures/v2/taker-buy-sell-volume/history` | `buy_vol`, `sell_vol` ← vendor fields (USD or coin — pick USD, document choice) |

Required query params on all four: `exchange=OKX`, `symbol=<mapped>`,
`interval=1h`.

### 4.4 Semantic drift (OKX live vs Coinglass history)

| Risk | Mitigation |
|------|------------|
| LS ratio definition differs slightly from OKX Rubik | Accept for backtest calibration; re-calibrate after 90d paper trading on OKX-native data |
| OI units (USD vs contracts) | Coinglass `unit=usd`; OKX stores `openInterestValue` — both USD-notional; document in report |
| Funding timestamp alignment (8h boundaries) | Normalize to UTC; upsert dedupes |
| Aggregated vs single-exchange | Always pass `exchange=OKX`; never use aggregated-coin endpoints for backtest |

Backtest HTML report must include `data_provenance: coinglass+okx` when
Coinglass rows were used (see `docs/backtest.md` §16).

### 4.5 Subscription tiers and history depth

Per [Coinglass pricing](https://www.coinglass.com/pricing) (verify at
implementation time):

| Plan | ~cost | Max `1h` history |
|------|-------|------------------|
| Hobbyist | $29/mo | 180 days |
| Standard | $299/mo | 360 days |
| Professional | $699/mo | 720 days (~2 years) |
| Daily interval | any paid plan | all-time |

For `--from 2024-01-01 --to 2026-05-01` at `1h`, **Professional** (or
Enterprise bulk export) is required. Operator may subscribe for one month,
bulk backfill, then cancel.

Rate limits (approximate): Hobbyist 30 req/min, Startup 80, Standard 300,
Professional 1200. Implement client-side pacing below the plan limit.

### 4.6 Error handling

- HTTP 401 → log "invalid COINGLASS_API_KEY", exit 1.
- HTTP 429 → exponential backoff (reuse `retry_with_backoff`).
- Empty page in range → advance cursor; do not retry forever (same pattern
  as OKX history-wall skip, but Coinglass should return data for valid
  historical windows).
- Vendor 4xx for unknown pair → exit 1 with symbol name.

---

## 5. Data types and source matrix

| `--data-types` | OKX `--source okx` | Coinglass |
|----------------|-------------------|-----------|
| `ohlcv` | ✅ always OKX | ✅ always OKX (Coinglass not used for OHLCV) |
| `funding` | ✅ ~90 days | ✅ up to plan limit |
| `oi` | ✅ ~9 days | ✅ up to plan limit |
| `ls_ratio` | ✅ ~31 days | ✅ up to plan limit |
| `taker_vol` | ✅ ~31 days | ✅ up to plan limit |

Default `--data-types`: `ohlcv,funding,oi,ls_ratio`.

---

## 6. OKX source (existing)

Implemented in `src/crypt/backfill/__main__.py` + `src/crypt/exchange/okx.py`.

OKX Rubik / OI endpoints return error `50030` ("Illegal time range") for
timestamps older than the exchange history window. The backfill loop skips
ahead after consecutive failures (`_MAX_CONSECUTIVE_EMPTY`, `_HISTORY_SKIP_MS`).
Retries on `50030` abort immediately (`no_retry_on` in `retry_with_backoff`).

Approximate OKX-native depth (2026-05-29):

| Type | Depth |
|------|-------|
| OHLCV | 2+ years |
| funding | ~90 days |
| ls_ratio / taker_vol | ~31 days |
| oi | ~9 days |

Use OKX alone for incremental / live-gap fills after a Coinglass historical
pass.

---

## 7. Recommended M2 workflow

```bash
# 1. OHLCV + deep derivatives (requires COINGLASS_API_KEY + Professional tier for 2y)
PYTHONPATH=src uv run python -m crypt.backfill \
    --source coinglass \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 --to 2026-05-01

# Repeat for TON, XPL (verify XPL on Coinglass first)

# 2. Overwrite recent derivatives with OKX-native values
PYTHONPATH=src uv run python -m crypt.backfill \
    --source okx \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 --to 2026-05-01 \
    --data-types funding,oi,ls_ratio

# 3. Backtest
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-05-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-05/
```

---

## 8. Implementation checklist (for the implementing agent)

1. Read this doc and ADR-0015 fully.
2. Resolve Coinglass API v4 docs via Context7 MCP.
3. Add `CoinglassClient` in `src/crypt/exchange/coinglass.py`.
4. Add `Settings.coinglass_api_key` (optional str).
5. Extend `crypt.backfill` CLI with `--source` and Coinglass code paths.
6. Unit tests: symbol mapping, response → model mapping (synthetic JSON fixtures).
7. Integration smoke test (optional, `@pytest.mark.network`): one page fetch
   if owner provides key in CI secret — otherwise skip.
8. Update `.env.example`, `README.md`, `CHANGELOG.md`.
9. Do **not** call Coinglass from engines or live orchestrator.

---

## 9. Tests

`tests/backfill/` (create if missing):

- `test_symbol_mapping.py` — OKX instId → Coinglass exchange/symbol.
- `test_coinglass_parsers.py` — fixture JSON → typed snapshots.
- `test_source_routing.py` — `--source auto` picks Coinglass iff key set.

---

## 10. Future: shared client with liquidations (ADR-0012)

The liquidations engine (post-M2) will also use Coinglass. Design
`CoinglassClient` as a reusable module under `src/crypt/exchange/`, not
backfill-only helpers. Backfill and a future liquidation poller both write
to Parquet via `ParquetStore`; engines never import the vendor directly
except through pre-fetched context (live) or replay store (backtest).
