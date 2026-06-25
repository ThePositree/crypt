# Archived router: PineScript median-DD momentum-structure 180d

**Router id:** `pinescript_median_dd_momentum_structure_180d_similarity65_hold60_margin1p5`  
**Search row:** `router_v2_3216811`  
**Archived:** 2026-06-24  
**Reason:** research_seed  
**Config:** `routers/archive/pinescript_median_dd_momentum_structure_180d_similarity65_hold60_margin1p5.json`

## Logic

At each daily decision point:

1. use only rolling labels whose `label_end <= asof`;
2. inspect prior 180-day labels with at least 65% weighted state similarity
   across momentum and market-structure PineScript states;
3. weight SMC state columns three times more heavily;
4. require at least 10 matching samples;
5. rank every archived strategy by median return minus drawdown;
6. hold the selected strategy for at least 60 days;
7. switch only when the new leader improves the score by at least 1.5 points.

The full archived strategy set is always available. The router never splits
capital and never selects cash.

## Matrix result

Validation range: 2024-01-01 through 2025-12-01, using daily 30-day rolling
labels and all 30 non-overlap start offsets.

| Metric | Value |
| --- | ---: |
| Utility score | **292.87** |
| Median offset return | **+310.56%** |
| Minimum offset return | **+281.26%** |
| Maximum offset return | **+369.97%** |
| Worst max drawdown | **-3.80%** |
| Median max drawdown | **-0.98%** |
| Median negative periods | **1** |
| Median switches | **5** |

Dense selection counts:

| Strategy | Rows |
| --- | ---: |
| `island_2023_021396_engulfing_bb_trend` | 361 |
| `crypt_ensemble_h1_discovery_nr4_vwap_robust` | 278 |
| `dssv2_013321_ps_macd_squeeze_recent` | 62 |

## Verdict

This is the strongest robustness frontier point: every offset exceeded
+281%, worst offset drawdown was -3.80%, and only one negative period remained
at the median. Its daily selections agree with the high-return archive seed on
45.2% of rows, confirming that the two routers are behaviorally distinct.

It supersedes the earlier full-state mean-DD router as a research baseline, but
is not production-approved until continuous routed-execution validation.

## Local artifacts

- Search:
  `results/router_search_matrix_v2_25k/random_seed1101/`
- Utility:
  `results/router_search_matrix_v2_25k/random_seed1101/router_utility_scores.csv`
- Offset sensitivity:
  `results/router_search_matrix_v2_25k/random_seed1101/router_offset_sensitivity.csv`
- Predictions:
  `results/router_search_matrix_v2_25k/random_seed1101/router_search_predictions.csv`
