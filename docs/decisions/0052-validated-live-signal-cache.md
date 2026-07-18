# ADR-0052: Validated latest-bar cache for live Core4 signals

- **Status**: accepted
- **Date**: 2026-06-30

## Context

ADR-0051 removed the fixed two-minute scheduler delay, but the live
`filtered_donor_portfolio.generate()` call still rebuilt four complete donor
frames and assembled events for roughly 40,000 historical H1 bars. The observed
runtime was about 32 seconds:

- exact discovery feature dataset: about 7 seconds;
- four full donor frames: about 7 seconds;
- portfolio joins and all-history event assembly: the remaining time.

Simply truncating history is not safe. Tests with 1,000-20,000 H1 bars changed
EMA-derived diagnostic values and can change a threshold decision near a
boundary.

## Decision

- The normal backtester continues to call the unchanged full-history
  `generate()` contract.
- Live execution may call a dedicated `generate_latest()` contract.
- Exact discovery features are still rebuilt from the complete history on every
  new closed bar.
- Full donor frames are cached after a cold calculation.
- On an appended bar, donor adapters run on a bounded primary tail using the
  exact full-history feature rows.
- Before accepting the update, an overlap of cached and recomputed donor frames
  must match exactly for all event-producing columns.
- A changed historical prefix, missing overlap, schema mismatch, or any
  comparison failure invalidates the cache and forces a cold full donor rebuild.
- The latest portfolio event is assembled from exact full-history catalog
  features. Cached output never changes backtester results.

## Consequences

- Cold startup remains slower than an hourly update but avoids the all-history
  portfolio event loop.
- Normal hourly calculation should fall from roughly 32 seconds toward the
  full-feature build time, approximately 7-10 seconds on the current machine.
- Historical backtest semantics remain unchanged and must be verified by an
  owner-run full v3 rerun plus exact trade comparison.

## References

- `docs/execution/live_signal_cache.md`
- ADR-0051
- `src/backtester/strategies/filtered_donor_portfolio.py`
- `src/crypt/execution/signal_runner.py`
