# ADR-0053: Versioned instrument precision and entry-fee timing

- **Status**: accepted
- **Date**: 2026-07-01

## Context

OKX live execution rounds order quantity and protection prices to instrument
metadata before submission. The backtester previously kept continuous sizes
and prices. It also included the entry fee in closed-trade PnL but left that
cash available until the position closed. Both differences can change later
entry eligibility and size, especially for overlapping positions and small
accounts.

The public OKX instrument metadata captured for `SOL-USDT-SWAP` on 2026-07-01
is:

- contract size: `1 SOL`;
- amount step: `0.01 contracts`;
- minimum amount: `0.01 contracts`;
- price tick: `0.01 USDT`.

## Decision

- Backtest execution accepts an optional named, dated instrument-precision
  policy.
- The active Core4 v3 config uses
  `okx_sol_usdt_swap_2026_07_01`.
- Quantity is converted to contracts, rounded down to the amount step, checked
  against the minimum, and converted back to asset units before all aggregate
  tier, liquidation, margin, fee, and PnL calculations.
- Structural SL, fixed TP, trailing activation, and trailing callback spread
  are rounded to the exchange price tick using decimal half-up rounding, which
  matches the live CCXT precision contract for this market.
- The backtester debits the entry fee immediately. On close it credits only
  gross price PnL minus the exit fee; the trade's reported net PnL continues to
  include both entry and exit fees.
- Funding remains excluded by explicit owner decision.

## Consequences

- Existing strategies without a precision policy retain legacy continuous
  behavior.
- Core4 v3 results will change and require a new owner-run canonical backtest.
- The dated policy must be refreshed when OKX changes SOL instrument metadata.
- Closed-trade PnL remains directly comparable, while capital available to
  overlapping entries now follows exchange cash timing.

## References

- `docs/execution/live_backtest_parity_audit_2026-06-30.md`
- `docs/execution/live_execution.md`
- ADR-0048
- ADR-0049
- ADR-0050
