# ADR-0049: Liquidation-safe leverage parity

- **Status**: accepted
- **Date**: 2026-06-29
- **Supersedes**: ADR-0029's unconditional maximum-leverage selection

## Context

The first live `causal_v3_core4` entry exposed a hidden execution mismatch.
OKX opened an isolated SOL long at 25x with:

- actual entry `73.91`;
- structural stop `70.9484`;
- estimated liquidation price `71.2843`.

Liquidation would therefore occur before the structural stop. The canonical
backtester did not model liquidation and always selected the configured maximum
leverage, so it scored risk and take-profit geometry against a stop the live
position could not reach.

## Decision

Backtester and live execution use the same liquidation-aware leverage policy
for USDT-margined linear swaps:

1. Resolve structural SL and TP before leverage selection.
2. Estimate isolated liquidation from entry, side, leverage, maintenance margin
   rate, and liquidation taker fee using the published OKX formula.
3. Reserve an additional price buffer of `0.5%` of entry between structural SL
   and estimated liquidation.
4. Select the highest whole-number leverage at or below the configured maximum
   that keeps liquidation beyond the buffered structural stop.
5. When an existing common leverage is already active, reuse it only if it is
   safe for the new trade.
6. Reject the entry when no liquidation-safe leverage fits the available-margin
   cap.
7. Record a liquidation exit when a candle reaches the estimated liquidation
   level under the default `worst_case` intrabar policy. Under `best_case`, the
   safer structural stop retains precedence.
8. Mirror OKX side aggregation: overlapping entries of the same instrument and
   side use a size-weighted common entry and one liquidation price, which must
   remain safe relative to every constituent stop.

Initial reproducible assumptions:

- base maintenance margin rate: `0.004`;
- SOL live/backtest tier schedule:
  `okx_sol_usdt_swap_2026_06_29`, derived from OKX public isolated SWAP
  position tiers on 2026-06-29 and used to resolve both maintenance margin
  rate and maximum leverage from aggregate same-side size;
- liquidation fee rate: `0.0005`;
- liquidation price buffer: `0.005` of entry;
- maximum leverage: `25x`.

Live execution must compare the post-entry OKX `liqPx` with the local structural
stop and block further entries if the exchange reports an unsafe relationship.

## Consequences

- Every historical candidate using the old unconditional 25x policy must be
  rerun before its return and drawdown numbers are reused.
- Lower leverage locks more margin and may reject overlapping entries that the
  old backtest accepted.
- Backtester trade exports include estimated liquidation price, selected
  maintenance margin rate, and the tier schedule used to derive it.
- Backtests no longer silently score a structural-stop exit on a worst-case bar
  that also crossed liquidation.
- Actual OKX liquidation remains mark-price based and can move with funding,
  future tier schedule changes, and margin adjustments. The 0.5% buffer covers
  ordinary model error but does not make liquidation harmless.

## References

- ADR-0024 — required explicit liquidation modeling
- ADR-0029 — previous unconditional maximum-leverage policy
- `docs/execution/liquidation_safe_leverage.md`
- `src/backtester/margin_policy.py`
- `src/backtester/risk_model.py`
