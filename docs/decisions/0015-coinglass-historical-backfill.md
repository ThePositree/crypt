# ADR-0015: Coinglass as read-only backfill source for derivatives history

- **Status**: accepted
- **Date**: 2026-05-29
- **Owner**: agent (confirmed by owner in chat)

## Context

M2 backtest requires multi-year history for `DerivativesEngine` inputs:
funding, open interest, long/short account ratio (and optionally taker
volume). OKX REST / Rubik endpoints only retain shallow windows (~9–90
days depending on metric). Running a 2-year backtest with OKX-only
backfill leaves `derivatives` neutral for ~95% of ticks, which makes
weight optimisation meaningless and risks miscalibrated ensemble weights.

The owner asked to evaluate third-party data providers. Coinglass API v4
covers all required metrics **per exchange and pair** (`exchange=OKX`,
`symbol=SOLUSDT`, etc.), with up to ~720 days of `1h` history on the
Professional plan. Alternatives considered:

- **CryptoQuant** — strong for BTC/ETH; weak altcoin derivatives coverage;
  no OKX-style account LS ratio endpoint.
- **Laevitas** — good aggregated OI/funding by currency; not OKX instId
  granularity; institutional pricing.
- **Kaiko / Tardis / Amberdata / CoinAPI** — institutional cost; overkill
  for MVP backfill.
- **Paper-trading accumulation only** — correct long-term, but blocks M2
  calibration for months.

ADR-0002 allows read-only data fallback when OKX cannot serve an endpoint,
with a follow-up ADR documenting contamination risk. ADR-0012 already
names Coinglass as the default path for a future liquidations engine.

## Decision

Use **Coinglass API v4** as a **backfill-only** read source for
`funding`, `oi`, `ls_ratio`, and `taker_vol`. OHLCV remains OKX-only.

- New `CoinglassClient` under `src/crypt/exchange/coinglass.py`.
- Extend `python -m crypt.backfill` with `--source okx|coinglass|auto`.
- Mapped rows are written to the **same Parquet files** via existing
  `ParquetStore` models and upsert semantics.
- **Live runtime continues OKX-only** — no Coinglass calls in engines,
  orchestrator, or tick loop.
- Operator workflow: Coinglass historical pass → OKX pass for recent
  overlap (last write wins on duplicate `ts`) → live OKX append.

Full endpoint mapping, CLI contract, and tier limits: **`docs/backfill.md`**.

## Alternatives considered

- **Optimise trend/meanrev only; fix derivatives weight manually** —
  avoids vendor cost but leaves the ensemble deliberately half-blind;
  rejected as primary strategy now that Coinglass is approved.
- **Use Binance/Bybit fallback (ADR-0002)** — cross-venue contamination
  for an OKX-only trader; worse than Coinglass OKX-specific endpoints.
- **Coinglass aggregated-coin endpoints** — simpler API but blends
  venues; rejected for backtest fidelity.

## Consequences

### Positive

- Enables meaningful M2 calibration of `derivatives` weight over 1–2
  years instead of ~30 days.
- Reuses the same Parquet schema — no backtest/replay code changes beyond
  provenance metadata in reports.
- Establishes `CoinglassClient` for ADR-0012 liquidations later.

### Negative

- **Cost:** Professional tier ~$699/mo if full 720-day `1h` history is
  needed; mitigated by one-month bulk download then cancel.
- **Train/live drift:** backtest history from Coinglass, live from OKX
  Rubik — values may differ slightly at the same timestamp. Mitigation:
  re-run calibration after 90 days of OKX-native paper trading; document
  in backtest report (`data_provenance`).
- **Vendor lock-in / rate-limit drift:** same risk as ADR-0012; cache in
  Parquet; graceful degradation if key missing (`--source auto` falls
  back to OKX).
- **Symbol coverage:** TON/XPL must be verified on Coinglass before
  backfill; XPL may be unavailable.

### To revisit later

- After M2 calibration: compare Coinglass vs OKX overlapping window;
  quantify LS ratio / OI correlation; supersede if drift is material.
- If Coinglass pricing or terms change, evaluate CoinAPI metrics or
  one-time Enterprise CSV export.
- Merge with ADR-0012 implementation — single API key, shared rate-limit
  budget across backfill + liquidation poller.

## References

- `docs/backfill.md` — implementation contract.
- `docs/decisions/0002-okx-only-with-future-fallback.md`
- `docs/decisions/0012-liquidations-roadmap.md`
- `docs/backtest.md` §4 (preconditions), §14 (backfill), §16 (limitations)
- Coinglass API v4: https://docs.coinglass.com/reference/endpoint-overview
- Coinglass pricing: https://www.coinglass.com/pricing
