# ADR-0017: M2 uses OHLCV-only calibration with SMC structure engines

- **Status**: accepted
- **Date**: 2026-06-01
- **Owner**: agent (owner directed in chat)
- **Supersedes**: the M2 primary-calibration part of ADR-0016 where
  derivatives history was still expected to drive the next backtest.

## Context

M2 needs a credible backtest before the project should spend money on paid
data. The previous plan depended on deep OKX derivatives history:

- funding was already removed by ADR-0016 because OKX history is shallow and
  funding intervals vary by contract;
- OI and long/short ratio may be available from OKX deep Rubik endpoints, but
  the local store still has only short windows and the data depth must be
  verified per symbol;
- liquidations, sentiment, and richer order-flow feeds either require paid
  vendors or have unknown free-tier limits.

The owner also supplied `pinescript/smc.pine`, the LuxAlgo Smart Money
Concepts indicator, as a behavioural reference for candle-only structure:
BOS/CHoCH, order blocks, equal highs/lows, fair value gaps, premium/discount
zones, and higher-timeframe levels.

## Decision

M2 primary calibration is **OHLCV-only**. The backtest must be able to run and
produce recommended weights using only free OKX candle history:

- H4 candles for all engines and labels;
- H1 candles only when a candle-only engine explicitly needs lower-timeframe
  confirmation;
- D1 candles for higher-timeframe context.

`DerivativesEngine` remains in the codebase and live pipeline, but it is not
part of the M2 primary calibration until deep OI/LS history is proven stable
for the full backtest window. In the M2 weights file its weight should be `0`
unless a separate backtest proves otherwise.

Implement a deterministic SMC core in Python, using `pinescript/smc.pine` as a
reference for behaviour rather than copying TradingView drawing code. First
engines:

1. `smc_structure` — swing/internal BOS and CHoCH trend bias.
2. `smc_order_blocks` — active order-block zones and retests in the direction
   of structure.
3. `smc_liquidity` — equal highs/lows and liquidity sweeps.

Fair value gaps, Fibonacci, and full premium/discount zone engines are deferred
until the core structure implementation has passed no-lookahead tests and the
first M2 report shows whether SMC signals carry weight.

## Lookahead rules

The Python implementation must model **when a structure becomes known**:

- a pivot confirmed with `N` bars to the right may only be emitted after those
  `N` bars have closed;
- no engine may use a candle with `open_time >= tick_time`;
- current higher-timeframe candles are not final values; only completed D1/W1
  levels may be used;
- PineScript `request.security(..., lookahead = barmerge.lookahead_on)` logic
  must not be ported directly.

## Consequences

### Positive

- M2 becomes reproducible on free data.
- Calibration can start before the project proves value.
- Structural engines can provide future entry/SL/TP zones, not only direction.

### Negative

- The ensemble temporarily loses derivatives-positioning information.
- SMC patterns are easier to overfit than simple indicators; implementation
  must stay deterministic and heavily tested.
- LuxAlgo's source is licensed CC BY-NC-SA 4.0. Direct commercial reuse is not
  acceptable without review. Treat it as a research reference and keep our
  Python code independently written.

## Follow-up

- Update `docs/backtest.md` so M2 data preconditions are OHLCV-only.
- Add specs for the SMC core and first SMC engines before implementation.
- Update `config/weights.yaml` to include SMC engines and set derivatives to
  `0` for M2 primary calibration.
- After the first report, write ADR-0014 with accepted weights or a critique
  of why the candle-only model is not yet tradeable.
