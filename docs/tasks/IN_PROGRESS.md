# In progress

## Promoted router strategy — full-period owner run (2026-06-24)

**What:** run owner-promoted `router_v2_2687609` as a normal composite strategy
over the full locally available SOL 1h history.

**Why now:** the owner requires promoted routers to use the same strategy and
backtester contracts as every other candidate. Special replay commands are
diagnostics only and may not be the final validation surface.

**Expected gain:** obtain a canonical `trades.csv`, equity report, and standard
backtester metrics for the router across 2022-12-18 through 2026-06-09.

**Status:** implementation complete; waiting for owner run.

**Owner command:**

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --data-source crypt-parquet \
  --data-dir data \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --from 2022-12-18 \
  --to 2026-06-10 \
  --strategy strategies/archive/router_v2_2687609.json \
  --capital 10000 \
  --output results/router_v2_2687609_full
```

**Acceptance:** `results/router_v2_2687609_full/trades.csv` exists; every trade
contains `router_id`, `selected_strategy`, and `position_group`; no overlapping
open trades have different position groups; standard metrics cover the full
available history.

**Links:** `docs/strategies/promoted_router.md`,
`strategies/archive/router_v2_2687609.json`, ADR-0042.

---

## Active DSS search matrix — inspect all five (2026-06-12)

**Context for next agent:** the owner is intentionally running five different
DSS search algorithms before the next agent session. The next session should
start only after all artifacts have been gathered on one PC. Do not implement a
sixth algorithm before inspecting these five result sets.

**Important version note (2026-06-12 late):** DSS Stage 1 now includes a cheap
path-aware barrier label (`tp_first` vs `sl_first` vs `timeout`) and writes
`barrier_*` columns in `stage1_viability.csv`. Searches already running before
that change are still useful as pre-barrier diagnostics, but do not compare
their Stage 1 survivor rates directly with fresh runs started after this code.
The first barrier implementation used trigger reference price; the fixed
version uses the same next-open entry and resolved `sl_rrr` levels as Stage 2.
Restart any barrier run that began before this note if Stage 1/Stage 2
alignment matters for analysis.

**Superseded version note (2026-06-18):** fresh DSS Stage 1 runs no longer use
candidate `rrr`, `risk_percent`, `atr_sl_mult`, structural stops, TTL, or
`sl_rrr` levels. The active Stage 1 label is next-open entry, closed-candle
ATR14 as symbol volatility scale, SOL reference calibration of 0.7% favorable
TP and 0.4% adverse SL, same-bar TP+SL counted as SL, and unresolved
end-of-window tails excluded from `barrier_win_rate`. Compare results only
against artifacts produced after this note when evaluating the current Stage 1
policy.

| Machine | Algorithm | Output | Status / next check |
| --- | --- | --- | --- |
| Work PC | default `staged` DSS v2 | `results/dss_sol_v2` | Owner started 120k trials. When owner returns, inspect `summary.md`, `archive.md`, `stage2_proxy.csv`, `stage3_full_scores.csv`, `candidate_manifest.md`, and `candidates/*.json`. |
| Home PC | `catcma_qd` | `results/dss_sol_catcma_seed777_fast` | Run was observed at 23,698 generated / 2,464 Stage 2 rows with no Stage 3 and no proxy score above `-5000`; likely negative unless it later resumes and improves. Inspect before deciding. |
| Railway | `island_qd` | `data/results/dss_sol_island_qd_railway_seed2026` | `railway.toml` start command now launches this search. Inspect via `railway ssh`; key file is `island_scores.csv` plus any exported `candidates/*.json`. |
| Extra local/remote | `hyperband_qd` | `results/dss_sol_hyperband_seed4242` | Owner started or can start this fourth algorithm. Inspect `hyperband_rungs.csv`, `stage2_proxy.csv`, `stage3_full_scores.csv`, archive, manifest, and candidates. |
| Extra local/remote | `smac_qd` | `results/dss_sol_smac_seed5151` | Owner should start this fifth algorithm after pulling this session. Inspect `smac_qd_proposals.csv`, `smac_qd_observations.csv`, `smac_qd_state.csv`, normal DSS stage CSVs, archive, manifest, and candidates. |

**What the next agent should do first when results are available:**
1. For each output directory, count rows in `stage0_candidates.jsonl`,
   `stage1_viability.csv`, `stage2_proxy.csv`, and `stage3_full_scores.csv`.
2. Also inspect algorithm-specific artifacts:
   `island_scores.csv`, `hyperband_rungs.csv`, `smac_qd_observations.csv`, and
   `smac_qd_state.csv` when present.
3. Report best `robust_score`, best `score_min`, and whether any candidate JSONs
   exported across all five runs.
4. Note whether `stage1_viability.csv` has `barrier_*` columns; missing columns
   mean the artifact came from the pre-barrier Stage 1 policy.
5. If any `candidates/*.json` exist, prepare owner-run `compare-fixed` commands
   for SOL 2025 continuous validation. Do not run owner-scale validations unless
   explicitly asked.

**SMAC-QD command for the fifth run:**
```bash
uv run backtester search-signals \
  --algorithm smac_qd \
  --seed 5151 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_smac_seed5151
```

**Hyperband-QD command for the fourth run if it is not already running:**
```bash
uv run backtester search-signals \
  --algorithm hyperband_qd \
  --seed 4242 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_hyperband_seed4242
```

---

## Island-QD Railway search — next owner action (2026-06-12)

**What remains:** owner can run a separate Railway service/job with the new
`island_qd` DSS backend. This should run independently from the local
CatCMA-QD run and the work-machine default DSS v2 run.

**Why now:** local CatCMA-QD reached about 23.7k generated candidates without a
single proxy candidate above `-5000` robust/min score. The best candidates were
often only useful on one window, especially `2025H1`, while `2022` killed the
robust score. Island-QD directly tests whether per-window specialist families
exist before trying to find robust intersections.

**Expected gain:** produce `island_scores.csv` showing best candidate families
per window and possibly export replayable candidate JSONs that default robust
search would reject too early.

**Railway start command for a dedicated search service:**
```bash
PYTHONPATH=/app/src uv run --no-dev backtester search-signals \
  --algorithm island_qd \
  --seed 2026 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output data/results/dss_sol_island_qd_railway_seed2026
```

**Config-as-code:** `railway.toml` currently uses this search command as
`deploy.startCommand`. Revert it to `PYTHONPATH=/app/src uv run --no-dev python
-u -m crypt` before using the same Railway service for live alerts again.

**Expected artifacts:** `data/results/dss_sol_island_qd_railway_seed2026/summary.md`,
`island_scores.csv`, `archive.md`, `archive.json`,
`island_qd_state_<window>.csv`, `stage1_viability.csv`, `stage2_proxy.csv`,
`stage3_full_scores.csv` if robust checks run, `candidate_manifest.md`, and
`candidates/*.json` if archive elites export.

**Railway note:** `railway run` executes locally with Railway env vars. To run
on Railway compute, set the service Start Command or deploy a dedicated service.
The output path intentionally starts with `data/` so artifacts land on the
Railway volume mounted at `/app/data`. To inspect files in the container
volume, use `railway ssh`.

---

## CatCMA-QD SOL search — next owner action (2026-06-11)

**What remains:** owner can run the experimental CatCMA-inspired DSS backend at
home while the work machine continues the default staged DSS v2 run.

**Why now:** running another default staged search with the same code/seed would
mostly duplicate the work-machine candidate sequence. ADR-0037 adds a different
mixed-variable learning pressure over triggers, filters, and execution params.
The first local CatCMA-QD attempt reached 592/120000 with ETA ~6d because Stage
2 proxy scoring was too permissive; it was stopped and the backend now caps
Stage 2 to the top cheap-scored slice per batch.

**Expected gain:** increase search diversity and give the project a second,
non-identical archive to compare against the work-machine DSS v2 artifact.

**Command:**
```bash
uv run backtester search-signals \
  --algorithm catcma_qd \
  --seed 777 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_catcma_seed777_fast
```

**Expected artifacts:** `results/dss_sol_catcma_seed777_fast/summary.md`,
`archive.json`, `archive.md`, `catcma_qd_state.csv`, `stage1_viability.csv`,
`stage2_proxy.csv`, `stage3_full_scores.csv`, `score_history.csv`,
`candidate_manifest.md`, and `candidates/*.json` if any archive elite exports.

**Do not resume:** `results/dss_sol_catcma_seed777/` was produced with the old
uncapped Stage 2 policy and is diagnostic only.

---

## DSS v2 first SOL search — next owner action (2026-06-11)

**Status:** already started on the work machine with 120k trials per owner chat.
Leave it running and inspect the artifact when the owner returns.

**What remains:** owner needs to return with `summary.md` / `archive.md` from
the work-machine run. Agents should not run this owner-scale search unless
explicitly asked.

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
  --n-trials 120000 \
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
  --trials 50 \
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
