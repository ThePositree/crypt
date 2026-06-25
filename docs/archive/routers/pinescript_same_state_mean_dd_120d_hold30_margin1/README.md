# Archived router: PineScript same-state mean-DD 120d, hold 30, margin 1

**Router id:** `pinescript_same_state_mean_dd_120d_hold30_margin1`  
**Search row:** `router_005807`  
**Archived:** 2026-06-23  
**Reason:** superseded  
**Config:** `routers/archive/pinescript_same_state_mean_dd_120d_hold30_margin1.json`

## Logic

At each daily decision point:

1. use only rolling labels whose `label_end <= asof`;
2. match prior rows with the same PineScript-derived market state;
3. score every archived strategy by mean forward return minus realized
   drawdown over the prior 120 days;
4. select the highest-scoring strategy;
5. hold the selected strategy for at least 30 days;
6. after the hold period, switch only when the new leader improves the score by
   at least 1 percentage point.

The full archived strategy set is always available. The router always selects
exactly one strategy; it never splits capital and never selects cash.

## Full-catalog result

Validation range: 2024-01-01 through 2025-12-01, using daily 30-day rolling
labels and all 30 non-overlap start offsets.

| Metric | Value |
| --- | ---: |
| Utility score | **162.90** |
| Median offset return | **+192.80%** |
| Minimum offset return | **+141.63%** |
| Maximum offset return | **+265.92%** |
| Worst max drawdown | **-6.52%** |
| Median max drawdown | **-2.60%** |
| Median negative periods | **3** |
| Median switches | **12** |

Dense selection counts:

| Strategy | Rows |
| --- | ---: |
| `crypt_ensemble_h1_discovery_nr4_vwap_robust` | 433 |
| `island_2023_021396_engulfing_bb_trend` | 238 |
| `crypt_ensemble_h1_discovery_vwap_reclaim_robust` | 30 |

## Why kept / why not accepted

This was the best utility result in the complete 7040-config catalog among
routers whose worst offset drawdown stayed within 10%. It is a distinct
PineScript-state family and materially reduces drawdown relative to the first
rolling-median archive seed.

It was superseded on 2026-06-24 by
`pinescript_median_dd_momentum_structure_180d_similarity65_hold60_margin1p5`,
which improved median return, minimum return, drawdown, negative periods, and
switch count. Neither router is accepted for production because these figures
come from rolling oracle-label evaluation rather than a routed execution
backtest.

## Local artifacts

- Chunk:
  `results/router_search_offset_4000/`
- Utility:
  `results/router_search_offset_4000/router_utility_scores.csv`
- Offset sensitivity:
  `results/router_search_offset_4000/router_offset_sensitivity.csv`
- Predictions:
  `results/router_search_offset_4000/router_search_predictions.csv`
