# Rolling regime router baseline

Status: **partial artifact analysis**.

Source labels:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/rolling_labels_day_30d/rolling_labels.csv`

Router artifact:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/rolling_labels_day_30d/router_baseline_min3/`

## Dataset

The labels were assembled from existing exact-parameter raw trade artifacts.
They are useful for testing the Plan B pipeline, but they are not a complete
six-strategy matrix:

| Coverage | Strategies |
| --- | --- |
| 2022-2024 | NR4 VWAP, DSS MACD, island engulfing, smac double-bottom |
| 2025 | DSS MACD, NR7 BB squeeze, VWAP reclaim |
| 2022-2025 | DSS MACD only |

The label builder uses `strategy_coverage.csv`, so a strategy is excluded when
its source artifact does not fully cover `[T, T + horizon)`.

Rows:

- 1341 daily rows total.
- 977 rows with 4 available strategies.
- 335 rows with 3 available strategies.
- 29 rows with 1 available strategy around the 2024/2025 boundary; these are
  excluded from router scoring with `--min-available-strategies 3`.

## Validation Contract

Routers are live-safe:

- score starts at `2024-01-01`;
- a router may train only on prior rows with `label_end <= asof`;
- dense scores evaluate every eligible daily 30-day forward label;
- non-overlap scores sample every 30 days before compounding, so overlapping
  future windows are not double-counted.

## Overall Partial Result

Artifact:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/rolling_labels_day_30d/router_baseline_min3/`

Dense rows, 2024-2025, `available_strategy_count >= 3`:

| Router | Avg 30d forward | Worst 30d | Negative rows | Avg regret |
| --- | ---: | ---: | ---: | ---: |
| `oracle` | +11.78% | -6.18% | 8 | 0.00% |
| `equal_weight_available` | +3.89% | -8.35% | 145 | 7.88% |
| `feature_knn_top2_60_40` | +3.49% | -14.98% | 171 | 8.29% |
| `rolling_top2_mean_60_40` | +3.40% | -14.98% | 179 | 8.38% |
| `rolling_best_mean` | +3.21% | -25.35% | 255 | 8.57% |

Non-overlap 30-day score, 24 periods:

| Router | Return | Max DD | Negative periods |
| --- | ---: | ---: | ---: |
| `oracle` | +1128.30% | -6.18% | 2 |
| `equal_weight_available` | +145.84% | -8.35% | 6 |
| `feature_knn_top2_60_40` | +131.65% | -12.85% | 6 |
| `rolling_best_mean` | +116.83% | -25.35% | 8 |
| `rolling_top2_mean_60_40` | +109.79% | -14.57% | 7 |

## Coverage Split

The overall score hides a coverage issue.

2024-only, 4 available strategies:

| Router | Non-overlap return | Max DD |
| --- | ---: | ---: |
| `oracle` | +167.20% | -0.38% |
| `feature_knn_top2_60_40` | +60.60% | -4.49% |
| `equal_weight_available` | +32.96% | -4.91% |
| `rolling_top2_mean_60_40` | +28.72% | -14.57% |

2025-only, 3 available strategies:

| Router | Non-overlap return | Max DD |
| --- | ---: | ---: |
| `oracle` | +359.69% | -6.18% |
| `rolling_best_mean` | +88.58% | -8.21% |
| `equal_weight_available` | +84.91% | -8.35% |
| `rolling_top2_mean_60_40` | +62.98% | -7.93% |
| `feature_knn_top2_60_40` | +44.24% | -11.12% |

## Decision

The rolling-label pipeline is worth continuing, but the partial dataset is not
enough to choose a production router:

- the 2024 subset suggests OHLCV KNN has some signal;
- the 2025 subset prefers much simpler allocation;
- the strategy universe changes between the two periods, so a router can learn
  coverage artifacts instead of market regimes.

Next step: run a full archive-only matrix with raw `strategy_trades/` on the
current code, then rebuild rolling labels and rerun `rolling-router-baseline`.
Only after that should we tune risk gates or train a detector.
