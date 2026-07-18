# ADR-0057: Distinguish below-start and peak-to-trough drawdown

- **Status**: accepted
- **Date**: 2026-07-02
- **Complements**: ADR-0030

## Context

ADR-0030 intentionally defines mandate drawdown as realized equity below a
window's starting capital. `ResultsAnalyzer` exposed that value under the
standard-looking label `Max Drawdown`.

The minute Core4 artifact printed `-9.20%` while its realized equity fell
`-42.54%` from a prior peak. Both values are mathematically valid, but they
answer different questions. Calling the below-start metric maximum drawdown
hides the investor's actual peak-to-trough loss.

## Decision

- Retain `max_drawdown` as the ADR-0030 below-window-start compatibility
  metric used by existing mandate and optimizer contracts.
- Add `peak_to_trough_drawdown` as the standard realized-equity decline from
  each running peak.
- Print both values with explicit labels:
  - `Drawdown Below Start`;
  - `Peak-to-Trough Drawdown`.
- Monthly mandate gates remain unchanged and continue to reset their
  below-start capital at each evaluation window.
- Owner-facing artifact reviews must quote both values. The standard
  peak-to-trough value is required when describing account risk.

## Consequences

- Existing candidate gates and optimizer objectives do not change.
- Existing `max_drawdown` consumers remain compatible.
- Reports can no longer present a small below-start value as the account's
  total peak-to-trough risk.
- Realized-only limitations remain: open-position unrealized drawdown is not
  included.

## References

- ADR-0030
- `docs/investment_mandate.md`
- `docs/mandate_reporting.md`
- `src/backtester/results_analyzer.py`
