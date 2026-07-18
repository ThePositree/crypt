# ADR-0058: OKX aggregate average-entry accounting

- **Status**: accepted
- **Date**: 2026-07-03
- **Supersedes**: the constituent-entry accounting in ADR-0049 and ADR-0055

## Context

OKX exposes one position per instrument and position side in long/short mode.
Adding exposure recalculates that position's volume-weighted average entry
price. Partially closing exposure reduces its size but leaves the average entry
price unchanged.

The Core4 backtester represented every donor event as a logical constituent.
It correctly aggregated same-side size before entry, but it then:

- calculated each constituent's realized PnL from that constituent's own entry;
- rebuilt the remaining average entry from the entries of logical constituents
  that had not closed yet; and
- rebuilt liquidation and allocated margin from that reconstructed average.

That is lot accounting, not OKX position accounting. It changes realized cash
timing, monthly risk bases, later position sizes, margin availability, and
liquidation after partial closes.

## Decision

Backtester and live execution maintain one exchange-side accounting state for
each `(symbol, side)` while retaining logical constituents for independent
SL/TP/trailing/TTL orders.

1. A fresh side starts with the first fill as its aggregate average entry.
2. Adding exposure updates the average entry by size-weighted fill price.
3. A partial close realizes price PnL from the current aggregate average entry.
4. A partial close does not change the remaining aggregate average entry.
5. When side size reaches zero, the aggregate average state is cleared.
6. Aggregate liquidation uses the preserved average entry, current remaining
   size, common leverage, and the current size tier.
7. Aggregate locked margin is allocated pro rata across logical constituents
   so their sum equals `aggregate_size * aggregate_average / leverage`.
8. Live synchronization adopts OKX `avgPx` and `liqPx` as authoritative for all
   local constituents on that side.
9. Trade exports include `aggregate_entry_price` so realized PnL can be
   independently reconciled.

Logical entry price remains the source for that constituent's structural stop,
take-profit, native trailing geometry, and signal audit metadata.

## Consequences

- Artifact `results/core4_v3_minute_last_mark_20260702/20260702_102019/`
  is no longer canonical and must be rerun.
- Historical entry events and signal artifacts should remain unchanged, but
  cash, risk bases, sizes, entry eligibility, liquidation, and final account
  value can change.
- Existing persisted live positions without `aggregate_entry_price` migrate to
  their own entry price and adopt the exchange average on the next successful
  synchronization.
- A synthetic regression must cover entries at different prices followed by a
  partial close at the aggregate average.

## References

- OKX, "How do I calculate the average fill price?"
- `docs/execution/liquidation_safe_leverage.md`
- `src/backtester/execution_sim.py`
- `src/crypt/execution/exchange_sync.py`
