# Archived: island_2023_021396 engulfing + BB width + EMA stack

**Candidate id:** `island_2023_021396_engulfing_bb_trend`  
**Archived:** 2026-06-22  
**Reason:** research_seed  
**Strategy:** `strategies/archive/island_2023_021396_engulfing_bb_trend.json`

## Discovery labels

- Trigger: `pt_engulfing` with `body_ratio=0.7`
- Filters: `pf_bb_width` with `max_width_pct=0.0625`,
  `pf_trend_ema_stack` with `fast=16`, `mid=50`, `slow=50`
- Stage 1 WR45 threshold-only search:
  - 2022: 290 signals, 45.52% barrier win rate
  - 2023: 335 signals, 40.12% barrier win rate
  - rejection: `weak_barrier_win_rate:2023`

## Best run (SOL 2022-2024, Optuna best-run)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Total return | **+375.80%** |
| Final capital | **$47,579.68** |
| Total trades | **968** |
| Win rate | **51.03%** |
| Profit factor | **1.40** |
| Sharpe | **2.1858** |
| Mandate score | **-15,622.90** |
| Sum capped monthly | **+276.10%** |
| Months >= 15% | **12 / 36** |
| DD breach months | **6** |
| Worst monthly DD | **-36.12%** |

**Execution (frozen):** `exit_geometry=sl_rrr`, `rrr=1.0`, `ttl=16`,
`risk=1.0%`, `trail_distance_atr=0.25`, trailing activates at `rrr`,
`structural_sl_mode=cap`, monthly risk base.

## Why kept / why not promoted

The tuned run has the strongest total return of this pair and a balanced
long/short trade count, but the mandate verdict is `discard`: 24 months remain
below the 15% floor and six months breach the monthly drawdown gate. It is kept
as a `research_seed` because it is a distinct engulfing/BB/EMA-stack family
with strong 2023 pockets and useful regime-separation evidence.

## Local artifacts

- Discovery: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/island_qd_seed2026/`
- Manual candidate: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/manual_candidates/island_2023_021396_engulfing_bb_trend_wr45_research.json`
- Optuna: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/`
- Best run: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/best_run/`
- Best trial: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/best_trial.json`
