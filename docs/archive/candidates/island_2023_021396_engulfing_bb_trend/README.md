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

## 2026-06-26 follow-up: short-only Island branch

The full-period donor run showed that the original Island family is mostly a
short-side edge. The original 2022-12-18 → 2026-06-10 exact run turned
$10,000 into $60,599 (+$50,599) with 1,326 trades, about 7.32 trades/week, and
a recalculated equity drawdown of -23.91%.

**Current selected branch:** keep
`island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1` as the best Island
research branch unless a later exact run supersedes it. It keeps trade
frequency above the owner's minimum and improves return/drawdown versus the
original:

| Variant | Result on $10k | Trades/week | Recalculated DD | Notes |
| ------- | -------------- | ----------- | --------------- | ----- |
| `island_short_r1p42_rrr0p75_ttl32_v1` | $76,147 (+$66,147) | 3.87 | -15.38% | Short-only, `rrr=0.75`, `risk=1.42%`, `ttl=32`. |
| `island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1` | $82,602 (+$72,602) | 3.40 | -16.35% | Adds an entry-known skip rule for weekend entries with stop distance >= 2.05%. |
| `island_short_r1p35_rrr0p75_ttl32_weekend_stop_filter_v1` | $75,227 (+$65,227) | 3.40 | -15.62% | Lower-risk filtered variant; roughly $1,517/month average over 43 months. |

These variants remain research/archive candidates, not promoted production
strategies: the drawdown is still above the strict 10% mandate limit and 2025
does not pass the monthly floor. They are useful because the edge is now
clearer: short-only engulfing signals, faster profit taking, and an
entry-known weekend wide-stop skip rule.

If this family is revived, start from the selected branch above, not from the
original long+short config.

After fixing multi-signal trailing parity, the selected Island branch was
combined with selected SMAC long in
`island_short_smac_long_portfolio_v1`. The exact portfolio run turned $10,000
into $168,657 (+$158,657), kept 1,087 trades / about 6.00 trades per week, and
had -16.98% recalculated drawdown. This is the first combined Island-centered
artifact worth further drawdown work.

## Local artifacts

- Discovery: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/island_qd_seed2026/`
- Manual candidate: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/manual_candidates/island_2023_021396_engulfing_bb_trend_wr45_research.json`
- Optuna: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/`
- Best run: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/best_run/`
- Best trial: `results/optuna_island_2023_021396_engulfing_bb_trend_big/20260622_094851/best_trial.json`
- Short-only baseline: `results/island_short_rrr075_minrisk/island_short_r1p42_rrr0p75_ttl32_v1/20260626_171914/`
- Weekend stop filter: `results/island_short_weekend_stop_filter_v1_full/20260626_172556/`
- Weekend stop risk grid: `results/island_short_weekend_stop_filter_risk_grid/`
- Island short + SMAC long portfolio:
  `results/island_short_smac_long_portfolio_v1_trailing_fixed_full/20260626_180002/`
