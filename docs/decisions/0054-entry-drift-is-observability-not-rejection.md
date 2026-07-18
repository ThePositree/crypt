# ADR-0054: Entry drift is observability, not rejection

- **Status**: accepted
- **Date**: 2026-07-01
- **Supersedes**: the entry-drift rejection in ADR-0051

## Context

The H1 backtester enters every actionable event at the next candle open. Live
execution cannot fill retroactively at that price: it submits at market after
the candle boundary is confirmed and the cached strategy result is available.

Rejecting live entries when the executable quote moves more than `0.1%` skips
trades that the backtester always takes. The 2026-06-30 SMAC event demonstrated
this directly: backtest entry `72.84`, live quote `73.52`, drift `0.934%`, and
the live trade was rejected. A hard gate therefore creates a larger structural
parity error than accepting measurable market slippage.

## Decision

- `EXECUTION_MAX_ENTRY_DRIFT_PCT` remains an observability threshold.
- Quote drift beyond the threshold is logged but never blocks an otherwise
  valid entry.
- The order is submitted without waiting for Telegram delivery.
- After fill confirmation, live compares the actual fill with both the H1 open
  and the pre-submit quote.
- A threshold breach sends `ENTRY DRIFT [OK]` containing H1 open, quote, fill,
  H1-to-fill drift, quote-to-fill drift, and an explicit confirmation that the
  entry executed.
- Post-fill liquidation and leverage-tier safety checks remain blocking and
  trigger a reduce-only fail-safe close when violated.

## Consequences

- Live no longer drops a backtester trade solely because the market moved after
  the H1 boundary.
- Fill price and therefore realized PnL can still differ from the H1 model.
- Collected H1-to-fill drift becomes the input for a later measured slippage
  stress model.

## References

- ADR-0051
- `docs/execution/live_execution.md`
- `docs/execution/live_backtest_parity_audit_2026-06-30.md`
