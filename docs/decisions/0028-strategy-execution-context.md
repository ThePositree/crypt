# ADR-0028: Propagate execution context into strategy.generate

- **Status**: accepted
- **Date**: 2026-06-08
- **Owner**: agent
- **Supersedes**: partial clarification of ADR-0027 entry vs exit semantics

## Context

TP-first mode (`exit_geometry=tp_pct`) was implemented in ExecutionSim only.
`crypt_ensemble` still required a valid structural stop before emitting
`signal != 0`, cutting ~70% of discovery-filtered events (Jan NR7: 23 → 7).
Owner intent: with `tp_pct`, entry must not be gated by order blocks / SMC
anchors; all discovery-filtered events should reach execution, where TP/SL are
set mechanically from `tp_move_pct` and `rrr`.

## Decision

1. Add `StrategyExecutionContext` and attach it from `Backtester.run` /
   `ParameterOptimizer` into `StrategyData.metadata` (or `DataFrame.attrs`).
2. `crypt_ensemble` reads the context; when `exit_geometry=tp_pct`, skip
   structural SL entry validation and emit a placeholder `sl_price` for the
   signal row (execution derives real exits via `resolve_exit_levels`).
3. Optuna signal cache keys include execution-context dimensions that affect
   signal generation (`exit_geometry`, `structural_sl_mode`).

## Alternatives considered

- **Strategy JSON flag only** — duplicates CLI; easy to drift from run flags.
- **Post-process in ExecutionSim** — cannot recover signals already zeroed in
  strategy layer.
- **Remove structural SL entirely** — breaks default `sl_rrr` path.

## Consequences

- Positive: discovery-filter parity for tp_pct runs; flexible hook for future
  strategy behaviour keyed off execution flags.
- Negative: two entry paths in `crypt_ensemble`; strategies must document which
  context fields they honour.
- Follow-up: discovery donor-eligibility gate (BACKLOG) should reuse the same
  context or shared stop-planning helper.

## References

- `src/backtester/execution_context.py`
- `docs/backtester/exit_geometry.md`
- ADR-0027
