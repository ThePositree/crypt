# `crypt_ensemble` structural stop-loss

## Purpose

Replace the previous mechanical ATR-only stop in the donor `crypt_ensemble`
strategy with a stop anchored to SMC market structure.

This was implemented on 2026-06-02 and must be smoke-tested before another
optimizer or backtest interpretation pass. The previous stop was convenient
for smoke tests, but it was not a trade setup: it ignored where the idea is
structurally invalidated.

## Safety rule

`backtester/` is a high-risk donor/source-of-truth package. Do not rewrite its
execution simulator or optimizer to solve this. Keep the donor contract the
same: `crypt_ensemble.generate(...)` emits `signal` and `sl_price`, and donor
`ExecutionSim` consumes them unchanged.

The change belongs in the `crypt_ensemble` adapter and, if useful, small
project-side helpers that reuse existing SMC analysis.

## References

- `pinescript/smc.pine` — behavioural reference for pivots, structure, order
  blocks, equal highs/lows, and sweeps.
- `docs/engines/smc_core.md` — Python SMC analyser contract.
- `src/crypt/structure/smc.py` — existing deterministic SMC outputs:
  `SMCOrderBlock`, `SMCLiquiditySweep`, `SMCPivot`, `SMCState`.
- `src/backtester/strategies/crypt_ensemble.py` — current donor
  strategy adapter.

## Previous behaviour

For every BUY/SELL verdict, `crypt_ensemble` computes:

- BUY: `sl_price = close - sl_atr_mult * ATR14`.
- SELL: `sl_price = close + sl_atr_mult * ATR14`.
- HOLD: `sl_price = close`.

This is mechanical volatility sizing, not structural invalidation.

## Current stop hierarchy

Use the first valid structural anchor in this order.

1. **Active order-block boundary**
   - Long: bullish OB low below entry.
   - Short: bearish OB high above entry.
   - Prefer a recent active order block aligned with current SMC bias and the
     trade direction.

2. **Fresh liquidity sweep level**
   - Long: swept low level below entry.
   - Short: swept high level above entry.
   - Use only sweeps known at or before the signal tick and still fresh under
     the same freshness rule as `SMCLiquidityEngine`.

3. **Confirmed pivot fallback**
   - Long: most recent confirmed swing/internal low below entry.
   - Short: most recent confirmed swing/internal high above entry.
   - Prefer swing pivots over internal pivots when both are valid and similarly
     close.

4. **ATR guard fallback**
   - The default is conservative: no structural anchor means `signal = 0` and
     `sl_price = entry_price`.
   - The previous ATR-only stop remains available only when
     `allow_atr_sl_fallback = true`, for diagnostics.

## Buffer and validation

After selecting a structural level, place the stop outside that level with an
ATR buffer:

- Long: `sl_price = structural_level - buffer_atr_mult * ATR14`.
- Short: `sl_price = structural_level + buffer_atr_mult * ATR14`.

Initial buffer can be small, for example `0.10 * ATR14`, but it should be a
strategy parameter (`sl_atr_buffer_mult`) rather than a hidden constant.

Validation:

- Long stop must be strictly below entry.
- Short stop must be strictly above entry.
- Reject or neutralize the signal if the stop is on the wrong side.
- Reject or neutralize the signal if stop distance is zero, NaN, or more than
  `8 * ATR14`.
- All anchors must satisfy `known_at <= tick_time`; no look-ahead.

## Output contract

Keep donor output unchanged:

- `signal`: `1`, `-1`, or `0`;
- `entry_price`: close of the signal H4 candle;
- `sl_price`: structural stop;
- existing verdict metadata columns remain preserved.

Optional diagnostic columns are allowed if they do not break donor execution:

- `sl_anchor_type`: `order_block`, `liquidity_sweep`, `pivot`, or `atr_fallback`;
- `sl_anchor_level`;
- `sl_anchor_known_at`;
- `sl_distance_atr`.

## Implementation notes

- Implemented in `src/backtester/strategies/crypt_ensemble.py`.
- Donor `ExecutionSim` is unchanged.
- `sl_atr_buffer_mult` defaults to `0.10`.
- `allow_atr_sl_fallback` defaults to `false` in
  `strategies/backtester/crypt_ensemble.json`.
- `sl_atr_mult` remains in the parameter surface for the explicit diagnostic
  ATR fallback path and for backward-compatible Optuna suggestions, but it is
  not used for default structural stops.
- BUY/SELL verdict metadata remains auditable even when structural SL
  neutralizes the donor `signal`.
- Structural-stop diagnostics are emitted as strategy columns and preserved in
  donor trade exports when trades exist.

## Tests

Add focused synthetic tests before running optimizer/backtest:

- Long signal uses bullish order-block low plus ATR buffer.
- Short signal uses bearish order-block high plus ATR buffer.
- Fresh sweep low/high is used when no order block is available.
- Pivot fallback works for long and short.
- Wrong-side structural stop neutralizes the donor signal.
- No anchor with conservative fallback disabled neutralizes the donor signal.
- Anchor with `known_at > tick_time` is ignored.
- Existing BUY/SELL/HOLD mapping and metadata export still work.

Implemented verification:

- `uv run ruff check src/backtester/strategies/crypt_ensemble.py tests/backtester/test_crypt_ensemble_strategy.py`
  -> clean.
- `uv run pytest tests/backtester/test_crypt_ensemble_strategy.py -q`
  -> 14 passed, 1 existing pandas warning.
- `uv run pytest tests/backtester -q`
  -> 82 passed, 3 existing pandas warnings.

## Future optimizer note

After structural SL lands, optimizer work can register `sl_atr_buffer_mult`,
`min_confidence`, thresholds, and regime weights. Do not add `folds` or broad
donor optimizer changes as part of that first pass.
