# In progress


## DSS v2 first SOL search — next owner action (2026-06-11)

**What remains:** owner needs to run the first real DSS v2 staged
quality-diversity search on SOL. The rewrite is implemented; agents should not
run this owner-scale search unless explicitly asked.

**Why now:** DSS v1 collapsed into `pt_ema_cross + rrr=4.0 + wide ATR stop`.
DSS v2 now stages cheap viability/proxy checks before full mandate scoring and
keeps a quality-diversity archive, so the next useful evidence is a real SOL
archive artifact.

**Expected gain:** determine whether the v2 search can produce diverse exported
candidate JSONs worth 2025 `compare-fixed` validation.

**Command:**
```bash
uv run backtester search-signals \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 50000 \
  --n-jobs 4 \
  --output results/dss_sol_v2
```

**Expected artifacts:** `results/dss_sol_v2/summary.md`, `archive.json`,
`archive.md`, `stage1_viability.csv`, `stage2_proxy.csv`,
`stage3_full_scores.csv`, `score_history.csv`, `candidate_manifest.md`, and
`candidates/*.json` if any archive elite exports.

---

## Walk-forward validation — next steps (2026-06-10)

**What remains:** owner needs to run the walk-forward command on real data.

**Command (full optimization, 6 windows, SOL):**
```bash
uv run backtester walk-forward \
  --data-dir data --symbol SOL-USDT-SWAP \
  --from 2022-01-01 --to 2025-12-31 \
  --is-months 12 --oos-months 6 \
  --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \
  --trials 50 --target mandate_score \
  --ttl-low 24 --ttl-high 60 \
  --risk-percent-low 1.0 --risk-percent-high 3.0 \
  --output results/walk_forward_nr4_sol
```

**Quick eval (no optimization, just per-year audit):**
```bash
uv run backtester walk-forward \
  --data-dir data --symbol SOL-USDT-SWAP \
  --from 2022-01-01 --to 2025-12-31 \
  --is-months 12 --oos-months 12 \
  --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \
  --trials 0 \
  --output results/walk_forward_nr4_sol_eval
```

**Expected artifact:** `results/walk_forward_nr4_sol/<timestamp>/summary.md` — table of IS vs OOS returns per window + interpretation verdict.

**Why this matters:** answers whether NR4 has genuine edge or is overfit to 2024-2025.

---

## M4 scheduler integration — next steps (2026-06-09)

Scheduler wired. Module is complete and integrated. **Next owner action: dry-run validation.**

**What remains:**
1. Deploy or start locally with `EXECUTION_ENABLED=true EXECUTION_DRY_RUN=true`.
2. After 1 H1 close (~:02 UTC), confirm logs show:
   - `"H1 tick at …"`
   - `"Signal for SOL-USDT-SWAP: signal=…"` or `"No actionable signal"`
   - `data/execution_state.json` created.
3. Switch `EXECUTION_DRY_RUN=false` only after owner confirms dry-run logs look correct.

**Key files:**
- `src/crypt/__main__.py` — H1 scheduler wired (H1Scheduler + LiveExecutionManager)
- `src/crypt/execution/` — complete module
- `.env.example` — all EXECUTION_* vars documented
- `docs/execution/live_execution.md` — spec
- `docs/decisions/0033-m4-live-execution-architecture.md` — ADR

---

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
