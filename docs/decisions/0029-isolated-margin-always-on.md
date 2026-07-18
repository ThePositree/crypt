# ADR-0029: Isolated-margin mode is always on

- **Status**: accepted; unconditional maximum-leverage selection superseded by ADR-0049
- **Date**: 2026-06-09
- **Owner**: agent (owner direction in chat)

## Context

OKX perpetual execution for this project assumes **isolated margin**: each
position locks its own collateral, and **all open positions must share the same
leverage** on the account/instrument side the owner trades.

Until 2026-06-09, `ExecutionSim` exposed `is_isolated_futures` (default
**False**) and the CLI required `--is-isolated-futures` to enable leverage
consistency checks. NR4 overnight Optuna and mandate runs ran **without** the
flag, so concurrent positions could open with inconsistent leverage semantics
and optimistic margin behaviour.

ADR-0026 defined leverage selection under isolated assumptions but left the
simulator toggle optional.

## Decision

1. **`ISOLATED_FUTURES_ALWAYS = True`** in `margin_policy.py` — single source
   of truth.
2. **`ExecutionSim` always enforces isolated semantics**: open positions must
   share one leverage; per-entry margin caps from `margin_policy.py` apply.
3. **Remove the CLI flag** `--is-isolated-futures` and the `is_isolated_futures`
   field from `BacktestArgs` / `FixedCandidateParams`. Strategy JSON
   `backtest_args.is_isolated_futures` is **ignored** (not a valid override key).
4. **`max_positions=0` remains valid** — no artificial cap on concurrent
   positions; only margin and leverage consistency limit entries (matches owner:
   OKX allows many positions when margin permits).

## Consequences

- All `backtester run`, `optimize`, `compare-fixed`, `compare-grid`, and
  `signal-quality` commands use isolated margin without operator action.
- Historical results produced **without** `--is-isolated-futures` (e.g. NR4
  v3 overnight) are **not directly comparable** to new runs; re-baseline NR4
  after this change.
- Docs and scripts must not mention `--is-isolated-futures`.

## References

- ADR-0024 — margin realism
- ADR-0026 — leverage selection
- `src/backtester/execution_sim.py` — `_can_open_position`
