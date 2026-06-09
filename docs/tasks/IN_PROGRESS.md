# In progress

## Active candidate: NR4 vwap band (2026-06-09)

**Strategy:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`  
**Plan:** `docs/candidates/nr4_vwap_robust.md`

### Mandate truth (ADR-0032 continuous, canonical)

**Active params:** tp=0.016, rrr=2.5, ttl=36, risk=1.5% (mandate-score Optuna best)

| Metric | Value |
| ------ | ----- |
| Verdict | **archive** |
| Sum capped | **+185.06%** |
| Months ≥ 15% | **9 / 12** |
| Below floor | **3** (Jan 11.83%, Feb 0.69%, Mar −1.28%) |
| DD breach | **1** (Mar −17.11%) |
| Full-year return | +284.65% (continuous run) |

Artifact: `results/nr4_mandate_score_best_compare/20260609_150212/`

Optuna continuous proxy and compare-fixed **match** (9/12, +185.06%, archive).
ADR-0032 alignment confirmed.

**Why archive, not promote:** Mar intra-month DD −17.11% > 10% limit → archive
per mandate §3.1 (no deep dive required). Also 3 months below 15% floor (within
allowed 3, but DD gate dominates).

### Historical (pre-ADR-0032 isolated mode — do not use for decisions)

| Params | Verdict | Sum capped | Months ≥15% |
| ------ | ------- | ---------- | ----------- |
| Legacy risk=2%, ttl=48 isolated | discard | +164.75% | 8/12 |
| Mandate-score isolated | discard | +131.31% | 3/12 |

### Next steps

1. **Owner-run legacy continuous** (tp=0.016, rrr=2.5, ttl=48, risk=2%) — compare
   vs current best under ADR-0032; command in `docs/candidates/nr4_vwap_robust.md`.
2. **Mar attribution** — `.../150212/runs/sol_continuous/trade_chart.html` + Mar
   SL cluster (DD breach month).
3. Filter/signal tweak or archive NR4 as near-miss if Mar DD cannot be fixed.

**Archived (2026-06-09):** NR7 and VWAP reclaim → `docs/archive/candidates/`.
