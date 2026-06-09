# Active candidate: NR4 + VWAP band + avoid doji

**Status:** near-miss — **archive** under ADR-0032 continuous mandate (2026-06-09)  
**Strategy:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`

## Active params (mandate-score Optuna best)

`tp=0.016`, `rrr=2.5`, `ttl=36`, `risk=1.5%`

## Mandate truth (ADR-0032 continuous — canonical)

**Artifact:** `results/nr4_mandate_score_best_compare/20260609_150212/`

| Metric | Value |
| ------ | ----- |
| Verdict | **archive** |
| Sum capped | **+185.06%** |
| Months ≥ 15% | **9 / 12** |
| Below floor | **3** — Jan 11.83%, Feb 0.69%, Mar −1.28% |
| DD breach | **1** — Mar −17.11% |
| Full-year return | +284.65% |

### Why archive, not promote

1. **Mar DD −17.11%** > 10% → **archive immediately** (mandate §3.1).
2. **9/12** months ≥15% — meets promote count, but DD gate blocks.
3. **3** months below floor — at the allowed limit (not auto-discard).

Optuna `mandate_score` continuous proxy **matches** this compare-fixed run
(9/12, +185.06%, archive). ADR-0032 alignment confirmed.

## Historical (isolated windows — superseded by ADR-0032)

| Profile | Mode | Verdict | Sum capped | Months ≥15% |
| ------- | ---- | ------- | ---------- | ----------- |
| Legacy ttl=48 risk=2% | isolated | discard | +164.75% | 8/12 |
| Mandate-score best | isolated | discard | +131.31% | 3/12 |
| Legacy ttl=48 risk=2% | continuous | *not run* | — | — |

Isolated mode reset capital each month — unrealistic; do not use for decisions.

## Next steps

1. Optional: continuous re-baseline **legacy** params (ttl=48, risk=2%) for A/B.
2. **Mar attribution** — DD breach month on continuous run:
   `.../150212/runs/sol_continuous/trade_chart.html`
3. Filter/signal work on Mar/Feb/Jan weakness, or formal **archive** NR4.

## Artifacts

- **Current truth:** `results/nr4_mandate_score_best_compare/20260609_150212/`
- Mandate-score Optuna: `results/nr4_mandate_score_optuna/20260609_133450/`
- Legacy isolated (historical): `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/`
- v3 overnight: `results/v3_robust_overnight_20260609/nr4_vwap/`
