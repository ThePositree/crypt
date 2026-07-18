# ADR-0055: Durable order recovery and conservative H1 path

- **Status**: accepted
- **Date**: 2026-07-01
- **Supersedes**: the incomplete crash-safety claim in ADR-0053 and the
  liquidation-first H1 rule in `liquidation_safe_leverage.md`

## Context

The 2026-07-01 full-code audit found that a persisted entry intent was not
adopted after restart and `status="closing"` was excluded from reconciliation.
It also found that the H1 simulator selected a deeper liquidation before a
nearer last-price stop and tightened native trailing from the favorable
extreme before checking the adverse extreme of the same candle.

Those behaviors can leave real money unmanaged and can make historical results
depend on an unobserved favorable within-hour price order.

## Decision

- Persist explicit entry lifecycle states from intent through protected.
- Recover regular entry/close orders by deterministic client ID.
- Adopt actual entry price, contracts, fee, liquidation, and protection after
  restart.
- Keep closing positions active in risk/sync state; adopt confirmed close
  fills or retry only the remaining reduce-only contracts.
- Set isolated leverage only for the position side being opened.
- Deduplicate fills by trade identity and match stored exchange order IDs as
  well as client IDs.
- In last-trade H1 simulation, a nearer protective stop precedes a deeper
  liquidation.
- Under `worst_case`, an active trailing stop is checked before the bar's
  favorable extreme tightens it. A newly activated/tightened stop cannot use
  the earlier adverse extreme of the same H1 candle.
- Market-triggered gap exits fill at the adverse bar open.
- Triggered TP limits use taker fees in historical results; live keeps actual
  exchange fees.
- If a constituent close causes the remaining aggregate side to lose its
  required liquidation buffer, both paths fail-safe close at the next H1
  synchronization/open.

## Consequences

- Restart recovery converges without duplicate entries and retains control of
  partially closed positions.
- The next canonical Core4 v3 result will differ from artifact
  `20260701_091336`; that artifact is no longer an execution baseline.
- Last-trade H1 simulation will likely report fewer or zero liquidations.
  Exact OKX liquidation still requires historical mark-price candles.
- Conservative trailing/gap/TP fees can reduce reported profit.

## References

- `docs/execution/live_execution.md`
- `docs/execution/liquidation_safe_leverage.md`
- `docs/execution/native_okx_trailing.md`
- `docs/execution/live_backtest_parity_audit_2026-06-30.md`
