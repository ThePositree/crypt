# Archived: smac_003335 double-bottom sweep + body-to-range

**Candidate id:** `smac_003335_double_bottom_body_to_range`  
**Archived:** 2026-06-22  
**Reason:** research_seed  
**Strategy:** `strategies/archive/smac_003335_double_bottom_body_to_range.json`

## Discovery labels

- Trigger: `pt_double_bottom_sweep` with `window=6`, `tolerance=0.3`
- Filters: `pf_body_to_range_min` with `ratio=0.7`
- Stage 1 WR45 threshold-only search:
  - 2022: 224 signals, 45.54% barrier win rate
  - 2023: 233 signals, 42.49% barrier win rate
  - rejection: `weak_barrier_win_rate:2023`

## Best run (SOL 2022-2024, Optuna best-run)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Total return | **+258.21%** |
| Final capital | **$35,820.97** |
| Total trades | **763** |
| Win rate | **44.69%** |
| Profit factor | **1.34** |
| Sharpe | **2.0967** |
| Mandate score | **-17,607.34** |
| Sum capped monthly | **+197.36%** |
| Months >= 15% | **9 / 36** |
| DD breach months | **4** |
| Worst monthly DD | **-22.53%** |

**Execution (frozen):** `exit_geometry=sl_rrr`, `rrr=1.5`, `ttl=116`,
`risk=0.75%`, `trail_distance_atr=0.25`, trailing activates at `rrr`,
`structural_sl_mode=cap`, monthly risk base.

## Why kept / why not promoted

The tuned execution is profitable over the 2022-2024 research window, but the
mandate verdict is `discard`: too many months are below the 15% floor and four
months breach the drawdown gate. It is kept as a `research_seed` because it is
a high-trade-count double-bottom family with useful 2022 positive behavior and
clear 2023 degradation for future regime/detector work.

## Local artifacts

- Discovery: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/smac_qd_seed5151/`
- Manual candidate: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/manual_candidates/smac_003335_double_bottom_body_to_range_wr45_research.json`
- Optuna: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/`
- Best run: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/best_run/`
- Best trial: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/best_trial.json`
