# In progress

## Status as of 2026-05-29 (session 4)

**Active work:** Coinglass backfill integration (ADR-0015).

Spec and ADR are written. Code is **not** implemented yet.

---

## Next steps for the implementing agent

### 1. Coinglass backfill (P0 for M2 calibration)

Read first:

- `docs/backfill.md` (full contract)
- `docs/decisions/0015-coinglass-historical-backfill.md`
- Resolve Coinglass API v4 via **Context7 MCP** before writing HTTP code.

Implementation order:

1. `Settings.coinglass_api_key` + `.env.example` (already has placeholder).
2. `src/crypt/exchange/coinglass.py` — `CoinglassClient` with paginated
   fetch methods matching §4.3 in `docs/backfill.md`.
3. Extend `src/crypt/backfill/__main__.py`:
   - `--source okx|coinglass|auto`
   - Coinglass paths for `funding`, `oi`, `ls_ratio`, `taker_vol`
   - OHLCV always via OKX regardless of `--source`
4. `tests/backfill/test_symbol_mapping.py`, `test_coinglass_parsers.py`,
   `test_source_routing.py` (synthetic fixtures).
5. Owner provides `COINGLASS_API_KEY` (Professional tier for 2y @ 1h).

Smoke command after implementation:

```bash
PYTHONPATH=src uv run python -m crypt.backfill \
    --source coinglass \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 --to 2026-05-01 \
    --data-types funding,oi,ls_ratio
```

Then OKX overlay for recent window (see `docs/backfill.md` §7).

### 2. Run full backfill + backtest (after step 1)

```bash
# All three symbols — verify XPL on Coinglass supported-exchange-pairs first
PYTHONPATH=src uv run python -m crypt.backfill --source coinglass \
    --symbol SOL-USDT-SWAP --from 2024-01-01 --to 2026-05-01
PYTHONPATH=src uv run python -m crypt.backfill --source coinglass \
    --symbol TON-USDT-SWAP --from 2024-01-01 --to 2026-05-01
# XPL only if supported:
PYTHONPATH=src uv run python -m crypt.backfill --source coinglass \
    --symbol XPL-USDT-SWAP --from 2024-01-01 --to 2026-05-01

PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-05-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-05/
```

### 3. After backtest report reviewed

- **ADR-0014** — calibration result: weights, expectancy CI, dataset window.
- Flip `Settings.uncalibrated = False`.
- Copy `weights.recommended.yaml` → `config/weights.yaml` if sanity guards pass.

---

## Completed earlier (M2 harness steps 4–11)

All backtest pipeline modules implemented and tested (2026-05-29 session 3).
See `docs/tasks/DONE.md`.

OKX backfill history-wall performance fix shipped same day (`CHANGELOG.md`).

---

## Known limitations / caveats

- **Coinglass cost:** ~$699/mo Professional for 720 days @ `1h`; one-month
  bulk download is the expected operator pattern.
- **Train/live drift:** backtest uses Coinglass history; live uses OKX —
  document `data_provenance` in report (see `docs/backfill.md` §4.4).
- **XPL** may lack Coinglass coverage — check API before backfill.
- **Optimizer is slow** on large datasets; use `--no-optimize` for smoke runs.

---

## Hard blockers

- **Coinglass API key** — owner must subscribe and set `COINGLASS_API_KEY`
  before historical backfill can run at full depth.

---

## Reading list

- `AGENTS.md`
- `docs/backfill.md` ← **start here for current task**
- `docs/decisions/0015-coinglass-historical-backfill.md`
- `docs/backtest.md` (M2 contract)
- `docs/decisions/0012-liquidations-roadmap.md` (future shared Coinglass client)
