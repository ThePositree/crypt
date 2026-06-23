# Regime label analysis

Status: **MVP analysis**.

Source artifact:
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/oracle_labels.csv`

This document summarizes the first monthly oracle-label analysis over the
archive-only SOL 2022-2025 strategy matrix.

## Dataset

- Buckets: 48 monthly rows.
- Strategy columns: 6 archived strategy variants.
- Labels: `best_strategy` by same-month strategy return.
- Features: OHLCV-only, computed strictly before the bucket start.

Selection counts:

| Strategy | Buckets |
| --- | ---: |
| `dssv2_013321_ps_macd_squeeze_recent` | 14 |
| `crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4` | 10 |
| `island_2023_021396_engulfing_bb_trend` | 9 |
| `crypt_ensemble_h1_discovery_vwap_reclaim_robust` | 6 |
| `smac_003335_double_bottom_body_to_range` | 5 |
| `crypt_ensemble_h1_discovery_nr4_vwap_robust` | 4 |

## Label Stability

- Average margin to second-best strategy: **6.7430%**.
- Ambiguous buckets with `margin_to_second_pct < 2%`: **12 / 48**.
- Strong buckets with `margin_to_second_pct >= 5%`: **26 / 48**.
- Losing oracle buckets: **0 / 48**.

The 12 low-margin buckets should not be treated as clean hard labels. They are
better used as low-confidence or multi-label training rows.

## Feature Separation

The first one-way separation scan is weak but not empty. Top features:

| Feature | F score | Eta squared |
| --- | ---: | ---: |
| `sma50_slope_30d_pct` | 1.4023 | 0.1460 |
| `trend_efficiency_30d` | 1.3689 | 0.1431 |
| `ret_30d_pct` | 1.2988 | 0.1367 |
| `ret_90d_pct` | 1.0778 | 0.1214 |
| `choppiness_30d` | 0.9992 | 0.1086 |
| `atr14_pct` | 0.9606 | 0.1026 |
| `realized_vol_90d_pct` | 0.8791 | 0.0947 |
| `close_vs_sma200_pct` | 0.7316 | 0.0801 |

Interpretation: trend direction/slope and trend efficiency separate labels
better than raw volatility or volume in this first small sample.

## Walk-Forward Baseline

Validation shape:

- train on all prior months;
- test month-by-month from 2024-01 through 2025-12;
- exact target is monthly `best_strategy`.

| Model | Exact accuracy | Top-2 accuracy |
| --- | ---: | ---: |
| `random_forest_small` | 0.1667 | 0.2500 |
| `rolling_majority` | 0.1667 | n/a |
| `decision_tree_depth2` | 0.1250 | 0.2083 |
| `decision_tree_depth3` | 0.1250 | 0.2083 |
| `logreg_l2` | 0.0417 | 0.2083 |

Result: exact single-strategy selection is not reliable yet. The best ML model
only ties rolling majority on exact accuracy and top-2 accuracy is weak.

## Interpretive Rule Hypothesis

The all-data shallow tree is not validated, but it gives a useful hypothesis
for the first rule router:

```text
sma50_slope_30d_pct <= 35.70
  choppiness_30d <= 43.41 -> island_2023_021396_engulfing_bb_trend
  choppiness_30d > 43.41
    trend_efficiency_30d <= 0.01 -> crypt_ensemble_h1_discovery_vwap_reclaim_robust
    trend_efficiency_30d > 0.01 -> dssv2_013321_ps_macd_squeeze_recent
sma50_slope_30d_pct > 35.70
  realized_vol_90d_pct <= 29.09 -> smac_003335_double_bottom_body_to_range
  realized_vol_90d_pct > 29.09 -> crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4
```

This should be treated as a candidate router scaffold, not as evidence that the
detector is solved.

## Decision

Do not build the first detector as a hard exact-strategy classifier.

Build the next MVP as a **confidence-gated top-2 portfolio router**:

1. Treat `margin_to_second_pct < 2%` rows as ambiguous.
2. Use the strongest OHLCV features first:
   `sma50_slope_30d_pct`, `ret_30d_pct`, `trend_efficiency_30d`,
   `choppiness_30d`, and `realized_vol_90d_pct`.
3. Output strategy weights over one or two strategies, not a single forced
   winner.
4. Score by portfolio return, drawdown, switching cost, and unknown/ambiguous
   exposure rather than classifier accuracy alone.

## Plan B: Rolling Labels

The monthly label dataset is the active MVP because it already exists and is
cheap to analyze. It is not the final target shape.

If monthly labels remain too coarse, move to rolling labels:

```text
as of time T:
  features = OHLCV information available before T
  label = best archived strategy over future window T -> T + horizon
```

Recommended first shape:

- feature step: 1 day;
- label horizon: 30 days;
- optional later step: 1h;
- labels: best strategy, top-2 strategies, margin to second, and ambiguity flag.

This requires the matrix command to preserve per-strategy raw trades, not only
bucket aggregates:

```text
results/<matrix>/strategy_trades/<strategy_id>.csv
```

With raw trades saved, future labelers can build daily, weekly, rolling 7d,
rolling 30d, and rolling 90d labels without rerunning heavy strategy backtests.

Trade inclusion rule for the first rolling-label MVP:

- features at `T` use only OHLCV candles strictly before `T`;
- label window is `[T, T + horizon)`;
- a trade contributes to the forward return if its `exit_time` falls inside the
  label window;
- trades still open at the end of the label window are ignored until a later
  window that contains their exit.
- if a partial `strategy_coverage.csv` manifest exists, a strategy only
  participates when its coverage fully contains `[T, T + horizon)`.

First partial artifact from existing exact-parameter runs:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/`.

Daily 30-day rolling labels:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/rolling_labels_day_30d/rolling_labels.csv`.

This artifact has 1341 rows. It is useful for testing the Plan B pipeline, but
it is not equivalent to a fresh full archive-only matrix because NR4/island/smac
cover 2022-2024, NR7/VWAP cover 2025, and only the DSS MACD strategy covers
2022-2025. Router training should filter low-availability rows, especially
`available_strategy_count == 1` around the 2024/2025 boundary.

The full rolling router baseline is documented in
`docs/regime_rolling_router_baseline.md`. The full matrix artifact supersedes
the earlier partial artifact:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/`.

Every rolling-label row now has all six archived strategies available. Oracle
non-overlap return over 2024-2025 is +1812.32%, but simple live-safe routers
capture far less. The next step is utility-scored and offset-robust router
evaluation before building a trainable detector.
