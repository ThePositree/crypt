# Rolling regime router baseline

Status: **full archive matrix analysis**.

Source labels:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/rolling_labels.csv`

Router artifact:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/router_baseline_min6/`

## Dataset

The labels come from a fresh archive-only matrix over SOL 2022-2025 with raw
`strategy_trades/` for all six archived strategies.

Rows:

- 1341 daily rows total.
- every row has all 6 strategies available.
- horizon: 30 calendar days.
- validation starts at 2024-01-01.

## Validation Contract

Routers are live-safe:

- score starts at `2024-01-01`;
- a router may train only on prior rows with `label_end <= asof`;
- dense scores evaluate every eligible daily 30-day forward label;
- non-overlap scores sample every 30 days before compounding, so overlapping
  future windows are not double-counted.

## Full Matrix Result

Artifact:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/router_baseline_min6/`

Dense rows, 2024-2025, `available_strategy_count == 6`:

| Router | Avg 30d forward | Worst 30d | Negative rows | Avg regret |
| --- | ---: | ---: | ---: | ---: |
| `oracle` | +13.85% | -0.39% | 2 | 0.00% |
| `rolling_best_mean` | +2.83% | -25.35% | 244 | 11.01% |
| `rolling_top2_mean_60_40` | +2.81% | -14.57% | 202 | 11.04% |
| `feature_knn_top2_60_40` | +2.14% | -23.99% | 237 | 11.70% |
| `equal_weight_available` | +1.75% | -11.06% | 208 | 12.10% |

Non-overlap 30-day score, 24 periods:

| Router | Return | Max DD | Negative periods |
| --- | ---: | ---: | ---: |
| `oracle` | +1812.32% | 0.00% | 0 |
| `rolling_top2_mean_60_40` | +92.91% | -14.57% | 7 |
| `rolling_best_mean` | +91.62% | -25.35% | 6 |
| `feature_knn_top2_60_40` | +85.19% | -14.18% | 9 |
| `equal_weight_available` | +49.95% | -18.99% | 8 |

## Parameter Sensitivity

The default router baseline used `lookback=365d` and `knn_k=7`. A small
sensitivity pass over lookback and KNN neighbors found a better single-start
KNN configuration:

Artifact:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/router_baseline_min6_lb180_k3/`

| Router | Non-overlap return | Max DD | Negative periods |
| --- | ---: | ---: | ---: |
| `oracle` | +1812.32% | 0.00% | 0 |
| `feature_knn_top2_60_40` | +142.75% | -6.84% | 8 |
| `rolling_best_mean` | +118.76% | -8.50% | 7 |
| `rolling_top2_mean_60_40` | +86.78% | -5.62% | 11 |
| `equal_weight_available` | +49.95% | -18.99% | 8 |

However this KNN result is not stable enough to treat as solved. Across all 30
possible non-overlap start offsets, the same `lookback=180d, k=3` configuration
has this range:

| Router | Min return | Median return | Max return | Worst DD | Median DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| `oracle` | +1433.29% | +1921.78% | +2265.14% | -0.39% | 0.00% |
| `rolling_top2_mean_60_40` | +29.84% | +84.11% | +101.95% | -12.26% | -8.32% |
| `rolling_best_mean` | +37.20% | +83.26% | +149.84% | -27.72% | -12.40% |
| `feature_knn_top2_60_40` | +20.98% | +74.42% | +183.51% | -26.66% | -12.22% |
| `equal_weight_available` | +43.58% | +46.72% | +49.95% | -19.43% | -17.24% |

## Feature Separation

Single OHLCV features weakly separate the best strategy labels. Top eta-squared
values:

| Feature | Eta squared |
| --- | ---: |
| `realized_vol_90d_pct` | 0.0687 |
| `volume_percentile_90d` | 0.0619 |
| `ret_90d_pct` | 0.0550 |
| `realized_vol_30d_pct` | 0.0505 |
| `choppiness_30d` | 0.0408 |

This is enough to justify feature-aware routing experiments, but not enough to
trust the current KNN router as production logic.

## Decision

The full rolling-label pipeline is now label-grade. The router is not solved:

- oracle performance shows large theoretical value in regime routing;
- simple rolling mean routers capture only a small part of that value;
- KNN can beat the rolling router on one start offset, but is unstable across
  offsets;
- the next useful work is a utility-scored router with risk gates and offset
  robustness, not a heavier detector yet.

Implemented next step: `backtester router-search` now evaluates single-strategy
router candidates by median non-overlap return, max drawdown, negative periods,
switching cost, and offset robustness. Routers always select exactly one
archived strategy; no capital split and no cash state are allowed.

The first full PineScript-aware 2000-config run is documented in
`docs/regime_router_search.md`. Its best router is a `rolling_median` 120-day
selector with a 3-point switch margin: median offset return +258.13%, minimum
offset return +186.37%, worst max drawdown -17.34%. This is a strong research
shortlist but not production-ready because DD remains above the mandate limit.

## Appendix: Partial Artifact

The earlier partial artifact remains useful only as a pipeline smoke test:
`results/regime_matrix_archive_partial_existing_trades_2022_2025/`.

It mixed 2022-2024 and 2025 strategy coverage and is superseded by the full
matrix artifact above.
