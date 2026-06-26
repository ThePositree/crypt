# ADR-0047: Multi-signal shared-capital execution

- **Status**: accepted
- **Date**: 2026-06-26

## Context

Donor-level trade-filter research found robust-forward CSV filters for all six
current SOL donor strategies. After filtering, the next owner-approved
experiment is to release every passing donor signal into one shared portfolio,
without assigning fixed capital slices per strategy.

The existing backtester strategy contract represents one OHLCV bar as one
dataframe row with one scalar `signal`. That is not enough for exact portfolio
simulation because standalone donor artifacts show material same-candle
overlap: 1,320 of 6,210 donor trades share an entry timestamp with at least one
other strategy. Selecting one row or duplicating OHLCV bars would distort the
portfolio.

## Decision

Add a backward-compatible multi-signal input contract to the execution layer:

- legacy scalar `signal` / `sl_price` rows continue to work unchanged;
- strategies may optionally emit `signal_events`, a list of event dictionaries
  for each OHLCV bar;
- `ExecutionSim` processes existing-position exits once per OHLCV bar, then
  processes all same-bar entry events in list order through the same risk,
  margin, fee, TTL, trailing, and exit-geometry code.

Capital is shared. There is no per-strategy capital allocation layer in this
ADR.

## Consequences

- Filtered donor portfolios can be exact-tested through normal backtester
  artifacts instead of CSV-deletion approximations.
- Event order can matter when margin is scarce. Portfolio strategies must make
  their event ordering explicit and auditable.
- Existing single-signal strategy tests and behavior must remain valid.
- The owner can compare money outcomes directly: final capital, weekly trade
  count, drawdown, and monthly returns on the same $10k base.

## References

- `docs/multi_signal_execution.md`
- `docs/trade_filter_research.md`
- ADR-0046
