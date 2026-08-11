# Archived strategy performance matrix

Status: **MVP implementation**.

This document defines the first artifact needed by
`docs/regime_detection.md`: a comparable performance matrix built from frozen
strategy variants.

## Goal

The matrix answers:

```text
How did each frozen strategy behave in the same market period?
```

It is not a promotion gate and does not replace mandate reporting. Its purpose
is to create input data for future regime discovery, labeler, detector, and
portfolio router work.

## Inputs

- One symbol.
- One shared historical window.
- One shared execution candle stream per strategy run; each strategy still
  requests any additional context timeframes it owns.
- A list of strategy JSON files from `strategies/archive/`.
- Optional explicit strategy JSON files from `strategies/backtester/` for
  exploratory runs only.
- Frozen execution params from each strategy JSON `backtest_args`.
- A bucket size: `day`, `week`, or `month`.

All strategies in one matrix run must use the same data source and date range.

Use `--jobs N` to run independent strategy backtests in parallel. Default is
`--jobs 1` (serial). Parallel workers each receive a copy of the shared OHLCV
dataframe, so large windows and high `N` can increase RAM use. Completed
strategy outputs are still checkpointed after each worker finishes.

## Archive Contract

A matrix used for regime discovery, retrospective labeling, detector training,
or portfolio-router evaluation should be built from `strategies/archive/` only.
Each strategy column must have matching documentation under
`docs/archive/candidates/<candidate_id>/` with:

- frozen execution params;
- provenance pointing to the discovery/Optuna/backtest artifacts;
- mandate or research verdict;
- monthly diagnostics when available.

Passing an active strategy with `--strategy` is allowed only for experiments and
sanity checks. Those runs should be treated as draft artifacts until the active
strategy is re-optimized if needed and archived under the same contract as the
other columns.

Current operator note: NR4 VWAP robust is archived as `nr4_vwap_robust` after
the 2022-2024 execution-only Optuna run, so the next label-grade matrix should
be archive-only and should not pass NR4 via `--strategy`.

## Backtest Semantics

Each strategy is run independently over the full shared window. The matrix
builder uses the same strategy config loader, data loader, strategy registry,
and donor `Backtester` path as `backtester run`.

The MVP does not write charts, candles, or per-strategy full OHLCV exports.
It writes lightweight matrix CSVs and optional raw per-strategy trade CSVs for
future rolling-label generation.

Trades are assigned to buckets by `entry_time`. Open trades are excluded from
bucket metrics unless they have realized `pnl_abs`.

## Outputs

Output directory:

```text
results/regime_matrix_<timestamp>/
```

Files:

- `strategy_manifest.csv`: one row per strategy config.
- `bucket_metrics.csv`: long-format matrix, one row per strategy per bucket.
- `matrix_return_pct.csv`: wide pivot, bucket rows and strategy columns.
- `matrix_trade_count.csv`: wide pivot of bucket trade counts.
- `strategy_trades/<strategy_id>.csv`: raw trade export for each completed
  strategy run.
- `strategy_coverage.csv`: optional coverage manifest for manually assembled
  or partial raw-trade datasets.
- `summary.md`: owner-facing summary.

### `strategy_manifest.csv`

Columns:

- `strategy_id`
- `strategy_path`
- `strategy_name`
- `version`
- `trigger_name`
- `filter_names`
- `risk_percent`
- `rrr`
- `ttl`
- `trail_distance_atr`
- `risk_base_period`

### `bucket_metrics.csv`

Columns:

- `bucket`
- `strategy_id`
- `strategy_path`
- `return_pct`
- `pnl_abs`
- `trade_count`
- `win_rate`
- `profit_factor`
- `avg_trade`
- `avg_win`
- `avg_loss`
- `max_drawdown_pct`
- `long_trades`
- `short_trades`
- `long_pnl_abs`
- `short_pnl_abs`
- `avg_holding_bars`
- `exposure_bars`
- `exit_stop_loss`
- `exit_take_profit`
- `exit_trailing_stop`
- `exit_ttl_expired`
- `exit_open`
- `exit_other`

`return_pct` is bucket PnL divided by the bucket start capital inferred from
trade `capital_before`. `max_drawdown_pct` is realized from trade-level
`capital_after` inside the bucket.

## MVP Limitations

- Only OHLCV-backed strategy configs are supported.
- The matrix is descriptive; it does not label regimes yet.
- Raw `strategy_trades/*.csv` files are written for rolling-label generation,
  but no charts or full per-strategy OHLCV files are exported.
- Buckets with no trades are emitted with zero trades and zero PnL so wide
  pivots remain aligned.
- Strategy families with multiple execution variants should appear as separate
  `strategy_id` columns, while their JSON metadata preserves family identity.

## Next Use

The future Regime Discovery step consumes `bucket_metrics.csv` and pivots
selected metrics into `time x strategy metrics` tensors. Initial clustering
should start with returns, trade count, drawdown, and win rate before adding
more features.

Plan B for denser detector training uses `strategy_trades/<strategy_id>.csv`
exports to build rolling labels from raw trades, e.g. daily rows with 30-day
forward strategy returns.

When `strategy_trades/` is assembled from existing artifacts instead of a fresh
single matrix run, add `strategy_coverage.csv` next to it:

```csv
strategy_id,coverage_start,coverage_end
dssv2_013321_ps_macd_squeeze_recent,2022-01-01T00:00:00+00:00,2026-01-01T00:00:00+00:00
```

Rolling labels use this manifest to exclude strategies whose coverage does not
fully contain the label window `[T, T + horizon)`. This prevents missing years
from being treated as 0% strategy return.
