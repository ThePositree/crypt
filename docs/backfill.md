# Backfill — historical data into Parquet

Contract for `python -m crypt.backfill`. Read this before touching backfill
code or adding a new data vendor.

Related ADRs:

- `docs/decisions/0002-okx-only-with-future-fallback.md` — OKX primary.
- `docs/decisions/0016-drop-funding-fix-oi-endpoint.md` — funding dropped;
  OI/LS ratio from OKX native deep endpoints (data to Feb 2024).

> **ADR-0015 retired (2026-06-01).** Coinglass backfill is no longer planned.
> Funding sub-signal is removed from `DerivativesEngine`. OI and LS ratio
> are fetched from OKX's own deep-history endpoints.

---

## 1. Purpose

Populate `data/<SYMBOL>/` Parquet files so the donor backtester and future
paper-trading replay have enough history for all engines — especially
`DerivativesEngine`, which needs OI and long/short ratio back to Feb 2024.

**Live runtime is unchanged:** the orchestrator keeps fetching from OKX via
`OKXClient`. Backfill is a one-time (or periodic catch-up) offline operation.

---

## 2. Storage layout

Default root: `Settings.data_dir` → `data/` (override with `DATA_DIR` env
or `--data-dir`).

| File | Columns | Used by |
|------|---------|---------|
| `ohlcv_4h.parquet` | `open_time, o, h, l, c, volume, closed` | Trend, MeanRev, Regime, Volatility |
| `ohlcv_1h.parquet` | same | Context / warm-up |
| `ohlcv_1d.parquet` | same | Trend, Regime |
| `oi_1h.parquet` | `ts, oi` | DerivativesEngine |
| `ls_ratio_1h.parquet` | `ts, long_ratio, short_ratio` | DerivativesEngine |
| `taker_vol_1h.parquet` | `ts, buy_vol, sell_vol` | Optional; not in MVP engines |

`funding.parquet` is removed (ADR-0016). Do not create it.

All cross-module payloads are typed models (`OISnapshot`, etc.) before
`ParquetStore.save_*`. Never write naked dicts across module boundaries.

**Upsert semantics:** `ParquetStore._upsert` deduplicates on timestamp,
`keep="last"`. Re-running backfill is idempotent.

---

## 3. CLI

```bash
PYTHONPATH=src uv run python -m crypt.backfill \
    --symbol SOL-USDT-SWAP \
    --from 2024-02-01 \
    --to   2026-06-01 \
    [--data-types ohlcv,oi,ls_ratio,taker_vol] \
    [--page-size 100] \
    [--max-rps 5] \
    [--data-dir data/]
```

### 3.1 Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--symbol` | required | OKX `instId`, e.g. `SOL-USDT-SWAP` |
| `--from` / `--to` | required | UTC dates `YYYY-MM-DD`; `--to` exclusive |
| `--data-types` | `ohlcv,oi,ls_ratio` | Comma-separated subset |
| `--page-size` | `100` | Records per API page (max 100 OKX) |
| `--max-rps` | `5.0` | Client-side rate limit |
| `--data-dir` | `Settings.data_dir` | Parquet root |

Exit `0` on success; `1` on bad args or precondition failure.

---

## 4. OKX endpoints used

| Data type | OKX endpoint | Depth (2026-06) | Notes |
|-----------|-------------|-----------------|-------|
| OHLCV | `/market/history-candles` (ccxt auto-selects) | 2+ years | ccxt switches to HistoryCandles automatically |
| OI (1H) | `/rubik/stat/contracts/open-interest-history` | to Feb 2024 | Direct call via `publicGetRubikStatContractsOpenInterestHistory`; NOT the `open-interest-volume` endpoint |
| LS ratio (1H) | `/rubik/stat/contracts/long-short-account-ratio-contract` | to Feb 2024 | ccxt `fetch_long_short_ratio_history` uses the correct endpoint |
| taker_vol | `/rubik/stat/taker-volume` | ~31 days | Optional only |

### OKX history-wall handling

Rubik endpoints return error `50030` ("Illegal time range") for timestamps
older than their history window. The backfill loop skips ahead after
consecutive failures (`_MAX_CONSECUTIVE_EMPTY=3`, `_HISTORY_SKIP_MS=90 days`).
Retries on `50030` abort immediately (`no_retry_on` in `retry_with_backoff`).

---

## 5. Data types

| `--data-types` value | Source | Approximate depth |
|----------------------|--------|-------------------|
| `ohlcv` | OKX | 2+ years |
| `oi` | OKX | to Feb 2024 (after endpoint fix) |
| `ls_ratio` | OKX | to Feb 2024 |
| `taker_vol` | OKX | ~31 days |

Default `--data-types`: `ohlcv,oi,ls_ratio`.

`funding` is no longer a valid data type (ADR-0016).

---

## 6. Recommended M2 workflow

```bash
# All three symbols — adjust --from to the OKX deep history boundary
for SYMBOL in SOL-USDT-SWAP TON-USDT-SWAP XPL-USDT-SWAP; do
    PYTHONPATH=src uv run python -m crypt.backfill \
        --symbol "$SYMBOL" \
        --from 2024-02-01 --to 2026-06-01 \
    --data-types ohlcv
done

# Run one donor-backed symbol smoke from the repository root
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/backtester/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

ADR-0017 makes the first M2 calibration OHLCV-only, so derivatives history is
not required for the primary report. `--from 2024-02-01` still gives enough
candle warm-up before the `2024-06-01` backtest start.

---

## 7. Tests

`tests/backfill/`:

- `test_okx_oi_endpoint.py` — verify `fetch_oi_history_page` calls
  `publicGetRubikStatContractsOpenInterestHistory` (not `…Volume`).
- Existing `test_symbol_mapping.py`, history-wall skip tests remain valid.

---

## 8. Future: Coinglass for liquidations (ADR-0012)

If the liquidations engine is implemented, it will require a Coinglass
integration. At that point, create `src/crypt/exchange/coinglass.py` as a
standalone async client. Do not repurpose the retired ADR-0015 design —
write a fresh ADR superseding ADR-0012 for the liquidations-specific scope.
