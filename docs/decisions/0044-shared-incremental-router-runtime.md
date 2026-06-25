# ADR-0044: Shared incremental router runtime for backtest and live

- **Status**: accepted
- **Date**: 2026-06-25
- **Owner**: owner direction in chat, agent documented
- **Supersedes in part**: ADR-0043
- **Related**: ADR-0032, ADR-0041, ADR-0042, ADR-0043

## Context

ADR-0043 removed recursive portfolio backtests from `promoted_router`, but the
replacement still generated complete nested signal frames before routing.
That retained multiple full-history strategy passes and did not match how a
long-running production process should consume newly closed candles.

The owner requires the backtest to be production logic executed against past
time, with only the clock, market-data source, and broker adapter changing.

## Decision

1. Introduce one stateful `RouterRuntime.on_closed_bar` core shared by
   historical replay and live execution.
2. Every H1 step updates all archived strategies in shadow mode because router
   performance comparisons require counterfactual results.
3. Exactly one selected strategy may emit into the real composite stream.
4. Rolling labels mature causally after their complete forward horizon.
5. Runtime state is serializable and restart-safe.
6. `promoted_router.generate()` is only a historical clock adapter over
   `on_closed_bar`.
7. The live scheduler is only a real-time clock/data adapter over the same
   method.
8. The external backtester and its execution simulator remain unchanged.
9. Router code dispatches through a strategy-class adapter registry. It may not
   branch on portfolio member ids or enumerate archived strategy rules.

## Consequences

- Full-history nested signal generation is removed from the final architecture.
- Backtest and live decisions can be compared bar-for-bar.
- All strategy indicator and shadow-execution logic needs incremental state.
- Existing vectorized implementations remain parity oracles during migration,
  not the promoted runtime.
- Portfolio membership remains data. Contract tests enumerate `strategy_paths`
  automatically instead of adding one test per transient strategy.
- Redis, SQLite, or files may later persist production state without changing
  runtime behavior.

## References

- `docs/strategies/incremental_router_runtime.md`
- `docs/strategies/promoted_router.md`
- `src/backtester/strategies/promoted_router.py`
- `src/crypt/execution/signal_runner.py`
