# Archived router: PineScript q25 trend-momentum-structure 90d

**Router id:** `pinescript_q25_trend_momentum_structure_90d_similarity80_hold45`  
**Search row:** `router_v2_4252951`  
**Archived:** 2026-06-24  
**Reason:** research_seed  
**Config:** `routers/archive/pinescript_q25_trend_momentum_structure_90d_similarity80_hold45.json`

## Logic

At each daily decision point:

1. use only rolling labels whose `label_end <= asof`;
2. inspect prior 90-day labels with at least 80% weighted state similarity
   across trend, momentum, and market-structure PineScript states;
3. weight Supertrend, DI side, and ADX state three times more heavily;
4. require at least 20 matching samples;
5. rank every archived strategy by its 25th-percentile forward return;
6. select exactly one strategy and hold it for at least 45 days.

The full archived strategy set is always available. The router never splits
capital and never selects cash.

## Matrix result

Validation range: 2024-01-01 through 2025-12-01, using daily 30-day rolling
labels and all 30 non-overlap start offsets.

| Metric | Value |
| --- | ---: |
| Utility score | **375.29** |
| Median offset return | **+425.17%** |
| Minimum offset return | **+202.21%** |
| Maximum offset return | **+571.40%** |
| Worst max drawdown | **-6.11%** |
| Median max drawdown | **-3.37%** |
| Median negative periods | **3** |
| Median switches | **14** |

Dense selection counts:

| Strategy | Rows |
| --- | ---: |
| `crypt_ensemble_h1_discovery_nr4_vwap_robust` | 340 |
| `island_2023_021396_engulfing_bb_trend` | 181 |
| `crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4` | 90 |
| `smac_003335_double_bottom_body_to_range` | 45 |
| `crypt_ensemble_h1_discovery_vwap_reclaim_robust` | 45 |

## Verdict

This is the highest-utility router from 100,000 matrix evaluations and a new
high-return frontier point. It remains a research seed: rolling-label offset
drawdown is not the mandate's continuous routed-execution monthly drawdown.

## Local artifacts

- Search:
  `results/router_search_matrix_v2_25k/hyperband_qd_seed3303/`
- Utility:
  `results/router_search_matrix_v2_25k/hyperband_qd_seed3303/router_utility_scores.csv`
- Offset sensitivity:
  `results/router_search_matrix_v2_25k/hyperband_qd_seed3303/router_offset_sensitivity.csv`
- Predictions:
  `results/router_search_matrix_v2_25k/hyperband_qd_seed3303/router_search_predictions.csv`
