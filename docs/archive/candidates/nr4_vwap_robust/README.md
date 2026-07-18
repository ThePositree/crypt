# Archived: NR4 VWAP robust

**Candidate id:** `nr4_vwap_robust`  
**Archived:** 2026-06-22  
**Reason:** research_seed  
**Strategy:** `strategies/archive/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`

## Discovery labels

- Trigger: `h1_nr4_breakout`
- Filters: `avoid_doji`, `vwap_dist_max_1pct`, `vwap_dist_min_0_2pct`
- Discovery source:
  `20260608_193549/best_candidates/robust_min_window_win_rate_50/rank_007_strategy.json`
- Discovery metrics: 404 passed events, 57.1788% label win rate, score 3.135357

## Best run (SOL 2022-2024, Optuna best-run)

| Metric | Value |
| ------ | ----- |
| Verdict | discard |
| Total return | **+148.71%** |
| Final capital | **$24,870.60** |
| Total trades | **1,109** |
| Win rate | **40.22%** |
| Profit factor | **1.27** |
| Sharpe | **1.5696** |
| Mandate score | **-18,526.95** |
| Sum capped monthly | **+141.00%** |
| Months >= 15% | **6 / 36** |
| DD breach months | **2** |
| Worst monthly DD | **-13.84%** |

**Execution (frozen):** `exit_geometry=tp_pct`, `tp=0.026`, `rrr=1.75`,
`ttl=52`, `risk=0.5%`, `trail_activation_rrr=1.75`,
`trail_distance_atr=0.25`, `structural_sl_mode=cap`, monthly risk base.

## Why kept / why not promoted

The tuned execution is profitable over the 2022-2024 research window and is
useful for regime-routing evidence, especially because earlier oracle
experiments showed NR4 can dominate selected 2025 months. It is not promoted:
the mandate verdict is `discard`, only 6 of 36 months reach the 15% floor, two
months breach the drawdown gate, and the worst losing streak reaches three
months.

## Local artifacts

- Active source strategy:
  `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`
- Optuna:
  `results/optuna_nr4_vwap_robust_big_2022_2025/20260622_153157/`
- Best run:
  `results/optuna_nr4_vwap_robust_big_2022_2025/20260622_153157/best_run/`
- Best trial:
  `results/optuna_nr4_vwap_robust_big_2022_2025/20260622_153157/best_trial.json`
