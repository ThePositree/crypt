# Archived: VWAP reclaim + low volume + BB width rank + session off-hours

**Candidate id:** `h1_vwap_reclaim__avoid_low_volume__bb_width_rank_min_low__session_off_hours`  
**Archived:** 2026-06-09  
**Reason:** superseded (weaker than NR7 and NR4 on SOL 2025 execution)  
**Strategy:** `strategies/archive/crypt_ensemble_h1_discovery_vwap_reclaim_robust.json`

## Discovery labels

- Trigger: `h1_vwap_reclaim`
- Filters: `avoid_low_volume`, `bb_width_rank_min_low`, `session_off_hours`
- 238 passed events, 57.1% label WR — robust shortlist rank #1 (PC2 `20260608_193549`)

## Best mandate run (SOL 2025, tp_pct Optuna best)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Sum capped monthly | **+50.26%** |
| Months ≥ 15% | 1 / 12 (Jan +17.55%) |
| Worst consecutive losing | 1 |
| DD breach months | 1 (Jun −16.26%) |
| Window | 12 × monthly `compare-fixed` |

**Execution (frozen):** `exit_geometry=tp_pct`, `tp=0.016`, `rrr=2.0`, `ttl=24`,
`risk=2.0%`, `structural_sl_mode=ignore`, monthly risk base.

## Why not promoted

Only one month cleared the 15% floor after full-year tp_pct Optuna. Discovery
rank #1 on robustness did not transfer to donor execution at mandate level.
NR4 on the same pipeline dominates (+164.75% capped, 8/12 months ≥15%).

## Local artifacts

- Overnight: `results/v3_robust_overnight_20260609/vwap_reclaim/`
- Optuna: `.../02_optuna_full_year/20260609_083127/`
- Mandate: `.../03_optuna_best_compare/20260609_092232/`
