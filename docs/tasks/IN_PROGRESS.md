# In progress

## Active candidate: NR4 vwap band (2026-06-09)

**Strategy:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`  
**Plan:** `docs/candidates/nr4_vwap_robust.md`

**Current mandate truth (ADR-0029 + ADR-0030 re-baseline, frozen Optuna params):**

| Metric | Value |
| ------ | ----- |
| Verdict | **discard** |
| Sum capped | **+164.75%** |
| Months ≥ 15% | **8 / 12** |
| Months below floor | **4** (Feb, Mar, Sep, Oct) |
| DD breach months | **2** (Feb −11.4%, Mar −20.21%) |
| Params | tp=0.016, rrr=2.5, ttl=48, risk=2% |

Artifact: `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/`

ADR-0029 (isolated always on) did not change NR4 numbers — all entries already
used max leverage. ADR-0030 removed Jan/Jun DD breaches vs v3 overnight; economics
unchanged.

**Next steps (priority order):**

1. **Weak-month attribution** — Feb/Mar/Sep/Oct trade charts under re-baseline
   `runs/`; look for SL clusters, session filter edge cases, overlapping positions.
2. **Mandate-aware Optuna** — replace `--target total_return_pct` with objective
   aligned to monthly floor + DD gates (BACKLOG P1; owner deferred implementation).
3. Optional realism knob: `max_positions=1` on frozen geometry (not yet run).

**Do not** re-run `compare-fixed` at risk=1% as a “search” — Optuna already
explored risk 1.0–2.0 and chose 2% for full-year return.

**Archived (2026-06-09):** NR7 and VWAP reclaim → `docs/archive/candidates/`.
Frozen JSON in `strategies/archive/`.
