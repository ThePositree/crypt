# ADR-0016: Drop funding sub-signal; fix OI history endpoint; retire Coinglass backfill

- **Status**: accepted
- **Date**: 2026-06-01
- **Owner**: agent (confirmed by owner in chat)
- **Supersedes**: ADR-0015 (Coinglass as backfill source) — retired in full.

## Context

Three issues identified during the M2 backfill investigation:

### 1. Funding interval instability

OKX perpetual swaps do **not** all settle funding every 8 h. As of April 2025,
OKX runs contracts on 1 h, 2 h, 4 h, and 8 h cycles — and changed several
contracts to shorter cycles without advance notice (e.g. TON-USDT-SWAP moved
to 4 h in the April 17 batch). The `DerivativesEngine` was written assuming
a fixed 8 h cycle (`_FUNDING_LIMIT = 200` rows ≈ "7–8 days"). With a 4 h
contract, 200 rows = only ~33 days; the z-score window is cut in half, making
the signal structurally different from the 8 h case. If OKX silently moves a
contract to 1 h, the calibrated weights break immediately with no error.

### 2. OKX funding history depth

`/api/v5/public/funding-rate-history` returns at most ~3 months of history.
This is insufficient for meaningful M2 calibration over 18+ months, and adding
a paid third-party source (Coinglass) to work around it was the plan under
ADR-0015.

### 3. Wrong OI endpoint in ccxt wrapper

`ccxt`'s `fetch_open_interest_history` calls
`/rubik/stat/contracts/open-interest-volume`, which has only ~9 days of
history. The correct deep-history endpoint is
`/rubik/stat/contracts/open-interest-history`, which OKX retains to
**early February 2024** (1 440 entries at 1 H). ccxt registers this endpoint
in its rate-limit table but never calls it from any public method; it must be
invoked directly as `publicGetRubikStatContractsOpenInterestHistory`.

The same deep-history situation applies to LS ratio:
`/rubik/stat/contracts/long-short-account-ratio-contract` (ccxt
`fetch_long_short_ratio_history`) already uses the correct endpoint and
provides data to February 2024.

## Decision

### 1. Drop funding from `DerivativesEngine`

Remove `_funding_signal` and all funding data paths. Rebalance internal
weights: **OI momentum 0.67, L/S ratio 0.33**. The engine now exits neutral
only when both OI and LS ratio are missing.

Rationale: the funding signal was worth 0.4 weight — meaningful but not
dominant. OI + LS ratio together remain a coherent "derivatives positioning"
view. Funding was the only data source that:
- Had interval instability across contracts,
- Had only 3 months of OKX-native history,
- Needed a paid third-party to bridge.

### 2. Fix the OI endpoint

Replace the ccxt high-level call in `OKXClient.fetch_oi_history_page` with a
direct `publicGetRubikStatContractsOpenInterestHistory` call. Parameters:
`ccy=<base>`, `period=1H`, `begin=<ms>`, `end=<ms>`. Parse `response["data"]`
as `[ts_ms, oi_usd, vol_usd]` arrays. This gives OI history to Feb 2024.

### 3. Remove `funding` from the backfill CLI

Delete the `_backfill_funding` function and the `funding` data-type option
from `python -m crypt.backfill`. Drop `funding.parquet` from storage layout.
Remove `EvaluationContext.funding` field and `FundingSnapshot` from the
context builder. (The `FundingSnapshot` Pydantic model may be left in
`models.py` as a tombstone to avoid a breaking import for any downstream
notebook, but it is no longer populated.)

### 4. Retire Coinglass backfill (ADR-0015 superseded)

With funding dropped and OI/LS ratio obtainable from OKX native endpoints
back to February 2024, there is no remaining data gap that requires Coinglass.
`CoinglassClient` is **not implemented**. ADR-0015 is superseded entirely.

Coinglass remains a valid future option for the liquidations engine
(ADR-0012); that engine will require its own ADR when implemented.

## Affected files (code — implementation deferred to next agent)

| File | Change |
|------|--------|
| `src/crypt/exchange/okx.py` | `fetch_oi_history_page`: replace `fetch_open_interest_history` with direct `publicGetRubikStatContractsOpenInterestHistory` call |
| `src/crypt/engines/derivatives.py` | Remove `_funding_signal`, `FundingSnapshot` import; rebalance weights to 0.67/0.33 |
| `src/crypt/models.py` | `EvaluationContext.funding` field removed (or set to `None` permanently) |
| `src/crypt/data/context.py` | Remove `_FUNDING_LIMIT`, `_df_to_funding`, funding loading |
| `src/crypt/data/store.py` | Remove `save_funding`, `load_funding` |
| `src/crypt/backfill/__main__.py` | Remove `_backfill_funding`, `funding` data-type, `--source` flag |
| `tests/engines/test_derivatives.py` | Remove funding-specific test cases; add OI+LS-only tests |
| `.env.example` | Remove `COINGLASS_API_KEY` / `COINGLASS_BASE_URL` placeholders |
| `docs/backfill.md` | Remove §4 (Coinglass), remove funding row from §2 table |
| `docs/engines/derivatives.md` | Update spec to reflect new weights and no-funding design |

## Consequences

### Positive

- No Coinglass subscription cost.
- No funding interval instability — removing a known source of train/live
  skew that could silently break calibration when OKX changes a contract's
  cycle.
- OI history to Feb 2024 from OKX native — sufficient for 18-month M2
  backtest window.
- `DerivativesEngine` simpler and more auditable.

### Negative

- Funding extremity signal (0.4 weight) is lost. Funding rate is a genuine
  market sentiment signal; this is a real reduction in engine expressiveness.
  Mitigation: M2 calibration will confirm whether OI + LS ratio alone carry
  enough information.
- If M2 shows derivatives weight collapsed to near-zero, revisit funding via
  a more stable source (e.g. on-chain perpetual premium index, or re-introduce
  with per-contract interval awareness as a future improvement).

### To revisit after M2

- If the `derivatives` engine weight in calibration is < 0.05, consider
  disabling it entirely until a more robust funding source is available.
- If M3 paper trading shows the engine adds value, evaluate adding funding
  back with explicit per-symbol interval metadata to avoid the z-score window
  mismatch.

## References

- `docs/decisions/0015-coinglass-historical-backfill.md` (superseded)
- `docs/decisions/0002-okx-only-with-future-fallback.md`
- `docs/decisions/0012-liquidations-roadmap.md` (Coinglass still relevant here)
- OKX API: `/api/v5/rubik/stat/contracts/open-interest-history`
- OKX announcement: funding rate formula update April 2025 (1/2/4/8 h cycles)
