# ADR-0030: Drawdown measured from window-start capital

- **Status**: accepted
- **Date**: 2026-06-09
- **Owner**: owner direction in chat

## Context

Mandate and backtest reports previously computed max drawdown as the worst
drop from a **rolling peak** on the realized equity curve. That produced
counter-intuitive gates (e.g. a month finishing +15% could still breach DD
after recovering from an earlier dip) and inconsistent numbers between
`windows.csv` and `monthly_mandate.csv` on multi-month aggregates.

The owner requires a single rule everywhere:

- DD = how far **realized equity** fell **below window-start capital**.
- Example: start $10 000, lowest post-exit equity $9 900 → **−1%** DD.
- **Open positions do not count** until closed (same realized-only equity).

## Decision

1. **`mandate_report._max_drawdown_pct`**: for each month/window, track
   `initial_capital + cumsum(pnl_abs)` at closed exits; DD =
   `(min_equity - initial_capital) / initial_capital × 100`, floored at 0
   if equity never drops below start.
2. **`ResultsAnalyzer._compute_drawdown_metrics`**: same rule on
   `capital_after` at exit times vs run `initial_capital`.
3. Remove rolling-peak DD and remove mandate `running_equity` carry-over
   for DD (each month uses its own $10k start for compare-fixed windows).

## Consequences

- Historical mandate verdicts and `max_drawdown` columns are **not**
  comparable before this change; re-baseline active candidates (NR4).
- Months with only gains show **0%** DD even if equity dipped from an
  intra-month peak above start (peak-after-gain drops are ignored).

## References

- ADR-0025 — mandate gates
- `docs/mandate_reporting.md`
- `src/backtester/mandate_report.py`, `src/backtester/results_analyzer.py`
