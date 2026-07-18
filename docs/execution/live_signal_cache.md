# Live Core4 latest-bar signal cache

## Purpose

Reduce the delay between an OKX-confirmed H1 boundary and an entry decision
without changing Core4 signals or the external backtester.

## Inputs

- complete `StrategyData` loaded by `LiveSignalRunner`;
- owner-selected filtered donor portfolio configuration;
- cached primary OHLCV prefix and donor frames held by the strategy instance.

## Cold path

1. Build the exact complete discovery feature dataset.
2. Build complete frames for every donor.
3. Apply nested donor replay controls.
4. Save the primary OHLCV prefix and controlled donor frames in memory.
5. Assemble only the latest portfolio event row.

## Fast append path

1. Require current OHLCV to begin with the exact cached primary frame.
2. Rebuild discovery features from the complete current history.
3. Slice the last 512 primary bars and their exact full-history feature rows.
4. Recompute each donor on that slice.
5. Compare the last 128 cached/recomputed rows exactly across all donor-frame
   columns.
6. Append only genuinely new donor rows to the cache.
7. Build catalog features from complete current history and assemble the latest
   event row.

## Invalidation and failure behavior

The cache is discarded and rebuilt cold when:

- history was revised, removed, or reordered;
- more new bars arrived than leave a validation overlap;
- donor columns or values differ in the validation overlap;
- strategy configuration creates a new strategy instance;
- a calculation raises.

An invalid cache is an optimization miss, not a trading error. If the cold
rebuild also fails, normal execution error handling blocks the entry and alerts
the operator.

## Backtester contract

`backtester run` continues to use `FilteredDonorPortfolioStrategy.generate()`
over the complete input. `generate_latest()` is a live-only optimization.

Acceptance requires:

1. local full-vs-latest signal equality tests;
2. cache append and invalidation tests;
3. owner-run full v3 backtest;
4. exact comparison of trade count, timestamps, side, strategy, prices, size,
   exit reason, fees, and PnL against the pre-cache canonical artifact.
