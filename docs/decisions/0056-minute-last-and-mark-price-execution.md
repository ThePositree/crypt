# ADR-0056: Minute last- and mark-price execution replay

- **Status**: accepted
- **Date**: 2026-07-02
- **Supersedes**: the H1-only historical execution approximation in ADR-0055
  when complete one-minute data is configured

## Context

The conservative H1 model removed favorable within-hour assumptions, reducing
the Core4 v3 result from an invalid `$588,744` account value to a reconciled
`$32,956`. It still cannot determine the order of multiple exits inside one
hour. It also compares liquidation with last-trade candles even though OKX
liquidates derivatives using mark price.

OKX exposes historical one-minute last-trade candles and separate historical
one-minute mark-price candles. Live protection already runs continuously on
OKX, so historical replay needs finer data while live must not wait for closed
minute polling.

## Decision

- Keep H1/H4/D1 as the strategy signal inputs.
- Add an explicit `execution_1m` backfill dataset containing last-trade and
  mark-price one-minute candles.
- Allow the disjoint `last_1m` and `mark_1m` series to backfill in parallel.
- Partition both minute series by UTC month so backfill is resumable without
  repeatedly rewriting the complete multi-year file.
- Pass minute frames to the simulator through a typed execution-only contract,
  outside strategy inputs.
- Process open-position exits minute by minute while preserving H1 entry, TTL,
  drain, risk-base, and synchronization boundaries.
- Use last-trade candles for stops, TP, and native trailing; use mark-price
  candles for liquidation.
- Require complete aligned minute coverage when a strategy opts in. Never mix
  minute replay and H1 fallback in one result.
- Keep the conservative configured bar policy for ambiguity that remains
  inside one minute.
- Accept OKX's rare H1-open/first-1m-open aggregation difference only when the
  H1 high, low, and close still match exactly and the minute open remains
  inside the H1 range. H1 open remains the modeled entry price.
- Keep live native protection and real-time exchange liquidation as the source
  of truth; do not add a delayed closed-minute live control loop.

## Consequences

- Core4 must be backfilled and rerun before its next live acceptance.
- Signal artifacts should remain unchanged; trade ordering, exits, dollars,
  and drawdown may change.
- Historical liquidation is materially closer to OKX because it uses mark
  price, but one-minute OHLC still cannot reconstruct tick order inside a
  minute or exact market slippage.
- The minute dataset is much larger and backfill takes materially longer than
  H1/H4/D1 history. Progress and resumable atomic upserts are mandatory.

## References

- `docs/execution/minute_intrabar_execution.md`
- `docs/backfill.md`
- `docs/execution/live_backtest_parity_audit_2026-06-30.md`
- ADR-0049
- ADR-0050
- ADR-0055
