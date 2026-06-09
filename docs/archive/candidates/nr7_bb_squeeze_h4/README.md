# Archived: NR7 + bb_squeeze + h4_context_aligned

**Candidate id:** `h1_nr7_breakout__bb_squeeze__h4_context_aligned`  
**Archived:** 2026-06-09  
**Reason:** superseded by NR4 v3 discovery candidate  
**Strategy:** `strategies/archive/crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json`

## Discovery labels

- Trigger: `h1_nr7_breakout`
- Filters: `bb_squeeze`, `h4_context_aligned`
- 222 passed events, 58.6% label win rate (v2 discovery)

## Best mandate run (SOL 2025, tp_pct Optuna best)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Sum capped monthly | **+58.82%** |
| Months ≥ 15% | 2 / 12 |
| Worst consecutive losing | 1 |
| DD breach months | 2 (Feb −11.3%, Oct −10.4%) |
| Window | 12 × monthly `compare-fixed` |

**Execution (frozen):** `exit_geometry=tp_pct`, `tp=0.014`, `rrr=2.25`, `ttl=24`,
`risk=2.0%`, `structural_sl_mode=ignore`, monthly risk base.

## Why not promoted

Strong capped sum for a discovery candidate, but 10 months below the 15% floor
and 2 intra-month DD breaches. Superseded by NR4 (+164.75% capped, 8/12 months
≥15%) on the same SOL 2025 tp_pct pipeline.

## Local artifacts

- Optuna: `results/nr7_tp_pct_overnight_20260608/02_optuna_full_year/20260608_154533/`
- Mandate: `results/nr7_tp_pct_overnight_20260608/03_optuna_best_compare/20260608_163635/`
- SL-first baseline (historical): `results/crypt_h1_discovery_nr7_bb_squeeze_sol_2025/20260608_124701/`
