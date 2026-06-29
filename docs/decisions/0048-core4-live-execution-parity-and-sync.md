# ADR-0048: Core4 live execution parity and exchange sync

- **Status**: accepted
- **Date**: 2026-06-27
- **Supersedes**: parts of ADR-0033 that hardcoded `crypt_ensemble` scalar live signals

## Context

ADR-0033 introduced the first M4 live execution module around a single
`crypt_ensemble.generate()` signal row. The selected deploy candidate has since
changed to Core v4:

`strategies/archive/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85.json`

Core v4 is a backtester-registry `filtered_donor_portfolio` strategy. It emits
multiple same-bar `signal_events`, each carrying donor metadata and possible
execution overrides. Trading one scalar row would no longer be the backtested
strategy.

The owner also requires live execution to survive redeploys and always know the
actual OKX account state: balance, positions, regular orders, algo SL/TP orders,
and mismatches between exchange state and local JSON state.

## Decision

Live execution now loads strategy JSON through the same backtester registry used
by `backtester run`. It processes the latest closed H1 bar's complete event
batch in order, using the current forming H1 candle open as the live equivalent
of the backtester's next-bar open.

Live sizing, SL/TP, margin, fees, TTL, and event-level overrides continue to use
the same backtester primitives as `ExecutionSim`.

Before startup reconciliation, before every H1 entry decision, and after order
placement, live execution fetches a normalized OKX snapshot and reconciles it
with the persisted state file. Blocking mismatches stop new entries:

- exchange position without local state;
- local open position missing from exchange state until classified/closed;
- regular or algo order without a tracked live position;
- non-positive balance.

If a local open position is absent from OKX, live execution marks it closed and
recomputes sync status before deciding whether new entries are allowed in that
same H1 tick.

## Consequences

- Core v4 live trading uses the same strategy config and same event list as the
  exact backtest path.
- `EXECUTION_MAX_POSITIONS=0` is the default and remains the project rule for
  Core v4; shared margin/capital guards remain active.
- The state file schema is v2 and stores donor id, position group, raw signal
  event metadata, trailing state, and last exchange sync status.
- Live money must still start with `EXECUTION_DRY_RUN=true` until operator logs
  show clean sync and sane orders over real H1 ticks.

## References

- `docs/execution/live_execution.md`
- ADR-0047
- `src/crypt/execution/`
