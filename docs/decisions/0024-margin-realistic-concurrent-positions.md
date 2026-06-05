# ADR-0024: Margin-realistic concurrent positions before H1 promotion

- **Status**: accepted
- **Date**: 2026-06-05
- **Owner**: owner (direction in chat); agent documented

## Context

The H1 short-only diagnostic artifacts showed that candidate evaluation is
now sensitive to concurrent-position semantics, not only signal quality.

The owner questioned two related issues:

1. How many positions can be open at the same time when real isolated-margin
   futures require margin for every position.
2. Why early rows in
   `results/crypt_ensemble_h1_signal_quality_filter_short_only/20260604_143218/runs/sol_2025_01/trades.csv`
   show the same `capital_before = 10000` even though multiple trades were
   open.

The current donor simulator treats `capital_before` / `capital_after` as
realized equity before entry and after exit. It does not mean free margin.
Open-position margin is tracked separately in current code via
`locked_margin`, but the older referenced artifact did not export that column.
Reconstructing it as `size * entry_price / leverage` for SOL January showed a
peak of 16 simultaneous positions and about 100% of initial capital locked as
margin under the old artifact's leverage choices.

That is a serious calibration risk. A strategy that looks acceptable only
because the simulator allows repeated H1 entries inside the same setup, while
the real account would be margin-constrained, is not a tradable candidate.

## Decision

Do not promote H1 short-only or any future H1 candidate until concurrent
position and margin realism are audited.

`max_positions` becomes an explicit optimization/search dimension for donor
H1 calibration. It must be searched with bounded values such as `1`, `2`, `3`,
`5`, and possibly `0` only as an unconstrained diagnostic baseline. The search
belongs beside execution parameters such as `rrr`, `position_ttl_bars`, and
`risk_percent`, not inside the `crypt_ensemble` signal-generation logic.

Before `max_positions` search is trusted, reports and exported trades must
make margin state auditable:

- keep `capital_before` / `capital_after` as realized equity fields;
- export per-entry `locked_margin`;
- export per-entry `available_balance_before`;
- export per-entry `open_positions_before`;
- export a report-level peak open-position count;
- export a report-level peak locked margin and peak locked-margin percentage
  of equity or initial capital.

The project assumes isolated futures for this line of work. Liquidation is
not treated as catastrophic account loss when isolation is enabled, but it
must be modeled explicitly if used as the effective stop:

- leverage is capped by the exchange maximum, currently `25x` for the owner's
  OKX assumption;
- using a liquidation price as the stop is allowed only if the simulator can
  compute and export that liquidation price;
- if liquidation is closer than the structural stop, the effective stop is the
  liquidation price and the trade's risk/TP geometry must be computed from
  that effective stop, not from the farther structural stop;
- silently using `25x` while still scoring risk against a farther structural
  stop is invalid.

## Consequences

- Current H1 short-only evidence remains useful for signal diagnosis, but it
  is not sufficient for promotion.
- Optimizer work must add `max_positions` search after the margin report
  surface is clear enough to audit.
- Candidate comparisons should include the unconstrained baseline only as a
  reference. Tradable candidates must pass with finite `max_positions` and
  realistic margin usage.
- Future leverage/liquidation modeling may require a follow-up ADR if it
  changes the risk model beyond reporting and `max_positions` search.

## References

- ADR-0018: Donor backtester becomes the canonical M2 backtest architecture
- ADR-0019: Monthly risk base for donor M2 sizing
- ADR-0023: Root-integrated backtester package
- `src/backtester/execution_sim.py`
- `src/backtester/risk_model.py`
- `docs/crypt_ensemble_mtf.md`
- `docs/tasks/BACKLOG.md`
