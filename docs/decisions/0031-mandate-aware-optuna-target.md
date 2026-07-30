# ADR-0031: Mandate-aware Optuna target

- **Status**: accepted
- **Date**: 2026-06-09
- **Owner**: owner direction in chat

## Context

The donor optimizer previously defaulted to `--target total_return_pct`. That
target maximizes one continuous backtest's aggregate return over the selected
window. It can select a trial with excellent full-year return while failing the
owner mandate because several months miss the 15% floor or breach the monthly
DD limit.

NR4 exposed this mismatch: legacy Optuna selected a +461% full-year profile,
but the ADR-0030 re-baseline still discarded it with 4 months below the floor
and 2 DD breach months.

## Decision

Add `--target mandate_score` to `backtester optimize`.

Each trial now records mandate-oriented user attrs:

- `mandate_score`
- `min_monthly_return`
- `monthly_shortfall_pct`
- `mandate_months_passing_floor`
- `mandate_months_below_floor`
- `mandate_dd_breach_months`
- `mandate_worst_consecutive_losing_months`
- `mandate_worst_monthly_drawdown_pct`
- `mandate_avg_capped_monthly_return_pct`
- `mandate_sum_capped_monthly_return_pct`
- `mandate_verdict`

The score is:

```text
sum_capped_monthly_return_pct
- 10  * monthly_shortfall_pct
- 25  * dd_excess_pct
- 200 * dd_breach_months
- 500 * max(months_below_floor - 3, 0)
- 500 * max(worst_consecutive_losing_months - 2, 0)
```

Where:

- `monthly_shortfall_pct` is the sum of `max(15 - raw_monthly_return_pct, 0)`;
- `dd_excess_pct` is the sum of drawdown beyond the accepted -10% monthly DD
  limit under ADR-0030;
- capped monthly return follows ADR-0025 (`min(raw, 20%)`).

## Consequences

- Candidate tuning should prefer `--target mandate_score` over
  `--target total_return_pct`.
- Legacy targets remain available for diagnostics: `total_return_pct`,
  `profit_factor`, `sharpe_ratio`, and `max_drawdown`.
- `mandate_score` is a continuous-run optimizer objective aligned with the
  canonical mandate path (ADR-0032). Final promotion still requires owner-run
  `compare-fixed` (default continuous) for exported artifacts.
- The penalty weights are deliberately conservative: mandate gate failures
  should dominate high aggregate return when ranking trials.

## References

- ADR-0025 — investment mandate candidate gates
- ADR-0030 — drawdown from window-start capital
- `src/backtester/optimizer.py`
- `docs/strategy_benchmark.md`
