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

## 2026-06-26 follow-up: long-only SMAC branch

The full-period donor archive showed that SMAC has the best long-side component
among the archived donor strategies, but it is much weaker than the Island
short branch:

| Variant | Result on $10k | Trades/week | Recalculated DD | Notes |
| ------- | -------------- | ----------- | --------------- | ----- |
| Original long+short SMAC | $24,133 (+$14,133) | 5.56 | -17.70% | Longs +$9,910, shorts +$4,223. |
| `smac_long_r0p75_rrr1p5_ttl116_v1` | $19,106 (+$9,106) | 2.61 | -14.31% | Long-only baseline. |
| `smac_long_r0p95_rrr1p25_ttl64_v1` | $20,377 (+$10,377) | 2.61 | -14.59% | Current selected long-only branch. |

The selected branch is not a standalone production candidate. It is kept as a
possible long-side complement to the selected Island short-only branch. A
negative-oracle check found wide-stop skip rules, but exact replay cut
frequency to 1.1-1.4 trades/week, below the owner's minimum, so no additional
SMAC long filter is selected.

After fixing multi-signal trailing parity, the combined
`island_short_smac_long_portfolio_v1` run turned $10,000 into $168,657
(+$158,657), with 1,087 trades, about 6.00 trades/week, and -16.98%
recalculated drawdown. This makes SMAC long useful as an add-on to Island
short, not as a standalone center of gravity.

## Local artifacts

- Discovery: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/smac_qd_seed5151/`
- Manual candidate: `results/dss_stage1_matrix_all_2022_2025_smc_wr45_threshold_only/manual_candidates/smac_003335_double_bottom_body_to_range_wr45_research.json`
- Optuna: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/`
- Best run: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/best_run/`
- Best trial: `results/optuna_smac_003335_double_bottom_body_to_range_big/20260622_094809/best_trial.json`
- Direction split: `results/smac_direction_split/`
- Long-only grid: `results/smac_long_grid/`, `results/smac_long_fine/`
- Selected long-only run: `results/smac_long_selected_full/20260626_174726/`
- Rejected wide-stop filters: `results/smac_long_stop_filter/`
- Island short + SMAC long portfolio:
  `results/island_short_smac_long_portfolio_v1_trailing_fixed_full/20260626_180002/`
