# ADR-0019: Monthly risk base for donor M2 sizing

- **Status**: accepted
- **Date**: 2026-06-02
- **Owner**: agent (owner directed in chat)

## Context

The donor `ExecutionSim` originally sized every new position from current
capital minus locked margin. This is standard fixed-fractional compounding, but
it makes M2 signal evaluation path-dependent: an early loss immediately
shrinks later position size, and an early win immediately increases it.

For the donor `crypt_ensemble` migration, the owner wants risk sizing to be
anchored to the capital available at the beginning of a time window. Example:
with 100 initial capital and 2% risk, a first losing trade leaves 98 capital;
the next trade in the same window should still size from 100, not from 98.

## Decision

The donor simulator now supports `risk_base_period`:

- `trade` — old behaviour; size from current capital on every entry.
- `weekly` — size from capital at the first entry of the ISO week.
- `monthly` — size from capital at the first entry of the calendar month.
- `backtest` — size from initial backtest capital for the whole run.

The donor `crypt_ensemble` strategy config uses `risk_base_period: "monthly"`.

The simulator still uses current available capital for margin/exposure checks.
Only risk sizing is anchored to the window base. This avoids pretending that
cash exists when drawdown or locked margin makes a position impossible.

## Alternatives considered

- `trade` current-capital sizing — preserved as the default for donor
  compatibility, but not used for `crypt_ensemble` M2 because it compounds
  path dependency into signal-quality evaluation.
- `weekly` windows — rejected as the default for now. H4 swing signals can be
  sparse or clustered; weekly resets are likely too noisy for first M2 smoke
  reports.
- `backtest` window — useful as a diagnostic, but too static as a default
  because it ignores capital regime changes over long samples.

## Consequences

- `crypt_ensemble` smoke runs become easier to interpret: trades in the same
  month use the same risk base even after wins/losses.
- Exported trades include `risk_base_capital`, so position size can be audited.
- Comparing old and new reports requires checking `risk_base_period`; metrics
  are not directly comparable when the sizing mode differs.
- Future Optuna/walk-forward work can test `weekly`, `monthly`, and
  `backtest`, but acceptance must be out-of-sample.

## References

- ADR-0018: Donor backtester becomes the canonical M2 backtest architecture
- `src/backtester/execution_sim.py`
- `src/backtester/risk_model.py`
- `strategies/backtester/crypt_ensemble.json`
