# ADR-0026: Isolated-margin leverage selection and per-slot caps

- **Status**: accepted
- **Date**: 2026-06-05
- **Owner**: agent (margin audit P0 from `BACKLOG.md`)

## Context

The 2026-06-05 H1 short-only `max_positions = 1` grid showed a bounded
aggregate return of `+10.12%`, but peak locked margin stayed at `96.62%` of
initial capital even when `risk_percent` was lowered to `0.5` and `0.25`.
That blocked promotion under ADR-0024/ADR-0025 because margin diagnostics
looked stuck at near-total collateral usage.

Root cause in `BasicRiskModel`:

1. Leverage was chosen as the **minimum integer leverage** that fit the
   per-entry margin budget (`ceil(position_value / cap)`). That maximizes
   locked margin instead of minimizing it.
2. With tight structural stops, lowering `risk_percent` could still leave
   `locked_margin` pinned at the per-entry cap until notional dropped below
   the cap at `1x` leverage.
3. `max_positions` and `max_allowed_margin` were only combined when
   `max_allowed_margin == 0`, while `ExecutionSim._can_open_position` ignored
   per-slot sharing entirely.

ADR-0024 already stated that using maximum OKX leverage minimizes locked
margin in isolated futures. The old donor path contradicted that assumption.

## Decision

Introduce `src/backtester/margin_policy.py` as the single source of truth for:

- `effective_margin_fraction(max_allowed_margin, max_positions)`
- `per_entry_margin_cap(available_balance, max_allowed_margin, max_positions,
  open_positions)`
- `select_leverage_and_locked_margin(position_value, per_entry_cap,
  max_allowed_leverage)`

Rules:

1. When `max_positions > 0`, each slot receives
   `min(max_allowed_margin, 1 / max_positions)` of available balance, split
   across **remaining** slots.
2. When the position fits under the per-entry cap at
   `max_allowed_leverage`, use **maximum allowed leverage** and set
   `locked_margin = position_value / max_allowed_leverage`.
3. Reject the entry when `ceil(position_value / per_entry_cap)` exceeds
   `max_allowed_leverage`.
4. `EntryContext` now carries `open_positions` so sizing and
   `ExecutionSim._can_open_position` share the same cap.

## Alternatives considered

- **Keep minimum-leverage path** — preserves old donor numbers but leaves
  peak margin pinned high on tight-stop H1 profiles; rejected.
- **Cap position size to margin budget** — under-risks relative to
  `risk_percent` without an owner-approved sizing policy; rejected for this
  slice.
- **Change default `max_allowed_margin` only** — does not fix the leverage
  selection bias; rejected as insufficient.

## Consequences

- Peak locked margin now scales down with `risk_percent` on tight-stop
  profiles when `max_allowed_leverage` is finite (e.g. `25x`).
- Existing trade counts and PnL paths change wherever the old minimum-leverage
  geometry inflated margin; bounded H1 grids must be re-run before promotion
  decisions.
- `locked_margin` values become materially smaller under high
  `max_allowed_leverage`, which is closer to isolated OKX behaviour.
- Liquidation-aware effective-stop modeling remains a separate follow-up
  (BACKLOG P1).

## References

- ADR-0024 — margin-realistic concurrent positions
- ADR-0025 — investment mandate §7
- `src/backtester/margin_policy.py`
- `src/backtester/risk_model.py`
- `src/backtester/execution_sim.py`
- `tests/backtester/test_margin_policy.py`
