# Archived: dssv2_013321 MACD signal cross + recent squeeze

**Candidate id:** `dssv2_013321_ps_macd_squeeze_recent`  
**Archived:** 2026-06-18  
**Reason:** near_miss after owner review  
**Strategy:** `strategies/archive/dssv2_013321_ps_macd_squeeze_recent.json`

## Discovery labels

- Trigger: `pt_ps_macd_signal_cross` with `zero_filter=against_zero`
- Filters: `pf_ps_squeeze_recent` with `lookback=12`
- 254 Stage 1 signals on SOL 2023, 50.79% path-aware barrier win rate

## Best mandate run (SOL 2023, Optuna best-run)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Total return | **+234.58%** |
| Sum capped monthly | **+161.09%** |
| Months >= 15% | 7 / 12 |
| Worst consecutive losing | 2 |
| DD breach months | 2 (Oct -14.23%, Nov -15.24%) |
| Window | continuous 2023 best-run export |

**Execution (frozen):** `exit_geometry=sl_rrr`, `rrr=2.0`, `ttl=56`,
`risk=1.25%`, `trail_distance_atr=0.25`, trailing activates at `rrr`,
`structural_sl_mode=ignore`, monthly risk base.

## Why not promoted

The tuned 2023 run is economically interesting but fails the mandate gate:
5 months are below the 15% floor and 2 months breach the 10% intra-month
drawdown limit. It is also a single-window execution-tuned result, so it should
stay shelved unless the owner explicitly revives it for cross-year validation.

## Local artifacts

- Discovery: `results/dss_sol_pinescript_v1_2023_stage1_seed73024/`
- Optuna: `results/dssv2_013321_big_optuna_2023_trail_atr/20260617_132218/`
- Best run: `results/dssv2_013321_big_optuna_2023_trail_atr/20260617_132218/best_run/`
- Best trial: `results/dssv2_013321_big_optuna_2023_trail_atr/20260617_132218/best_trial.json`
