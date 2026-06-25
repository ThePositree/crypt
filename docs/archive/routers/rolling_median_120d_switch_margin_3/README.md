# Archived router: rolling median 120d, switch margin 3

**Router id:** `rolling_median_120d_switch_margin_3`  
**Search row:** `router_001190`  
**Archived:** 2026-06-23  
**Reason:** research_seed  
**Config:** `routers/archive/rolling_median_120d_switch_margin_3.json`

## Logic

At each daily decision point:

1. use only rolling labels whose `label_end <= asof`;
2. compute each archived strategy's median forward return over the prior 120
   days;
3. select the highest-scoring strategy;
4. keep the current strategy unless the new leader improves the score by at
   least 3 percentage points.

The full archived strategy set is always available. The router always selects
exactly one strategy; it never splits capital and never selects cash.

## Best search result

Validation range: 2024-01-01 through 2025-12-01, using daily 30-day rolling
labels and all 30 non-overlap start offsets.

| Metric | Value |
| --- | ---: |
| Utility score | **202.12** |
| Median offset return | **+258.13%** |
| Minimum offset return | **+186.37%** |
| Maximum offset return | **+365.24%** |
| Worst max drawdown | **-17.34%** |
| Median max drawdown | **-10.02%** |
| Median negative periods | **5** |
| Median switches | **2** |

Dense selection counts:

| Strategy | Rows |
| --- | ---: |
| `island_2023_021396_engulfing_bb_trend` | 480 |
| `crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4` | 182 |
| `crypt_ensemble_h1_discovery_vwap_reclaim_robust` | 39 |

## Why kept / why not accepted

This is the first strong offset-robust single-strategy selector and a useful
benchmark for future router families. It is not accepted for production:
worst drawdown is -17.34%, above the current 10% mandate limit. The owner chose
to archive it instead of tuning this one candidate further.

## Local artifacts

- Full search:
  `results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/`
- Utility:
  `results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/router_utility_scores.csv`
- Offset sensitivity:
  `results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/router_offset_sensitivity.csv`
- Predictions:
  `results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/router_search_predictions.csv`

