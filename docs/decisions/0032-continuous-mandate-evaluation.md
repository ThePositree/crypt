# ADR-0032: Mandate evaluation uses continuous backtests

- **Status**: accepted
- **Date**: 2026-06-09
- **Owner**: owner direction in chat

## Context

`docs/investment_mandate.md` already required a **full-year continuous backtest**,
but `compare-fixed` defaulted to **12 isolated monthly runs** — each window
reset capital to $10k and dropped open positions at month boundaries.

That isolated mode is unrealistic for live trading (positions are not panic-closed
at 00:00 UTC on the 1st) and caused a systematic mismatch:

- Optuna and `mandate_score` evaluate one continuous year.
- Isolated `compare-fixed` produced different monthly economics for the same params
  (NR4 mandate-score best: 9/12 on continuous proxy vs 3/12 isolated).

Continuous slicing was already implemented as `compare-fixed --continuous` but
was opt-in and undocumented as the canonical promotion path.

## Decision

1. **Canonical mandate evaluation** = one continuous backtest per symbol across
   the evaluation window; calendar-month gates (≥15% return, ≤10% DD) are computed
   from **closed-trade PnL in that month** on that single run.
2. `compare-fixed` defaults to **`--continuous`** (new flag pair:
   `--continuous` / `--isolated-windows`).
3. **`--isolated-windows`** remains for diagnostics (attrition studies, legacy
   comparisons) but must **not** be used for promote/archive/discard decisions.
4. Monthly return floor still uses **`raw_monthly_return_pct = month_pnl / $10k`**
   (ADR-0025 portfolio size), not reset-to-$10k simulation each month.
5. Monthly DD still uses **window-start capital = $10k** per calendar month
   (ADR-0030) on the continuous run's realized equity curve.

## Consequences

- Optuna `mandate_score` and `compare-fixed` mandate reports are aligned when
  both use the same continuous year (modulo independent-window noise removed).
- Prior isolated-window NR4 verdicts remain historical artifacts; re-baseline
  active candidates with default `compare-fixed` before promote/archive decisions.
- `--jobs` parallelizes only in isolated mode; continuous mode runs one backtest
  per symbol (inherent serial dependency).

## References

- ADR-0025 — investment mandate
- ADR-0030 — drawdown from window-start capital
- ADR-0031 — mandate-aware Optuna target
- `src/backtester/fixed_candidate_report.py` — `_run_fixed_candidate_comparison_continuous`
