# Active candidate: NR4 + VWAP band + avoid doji

**Status:** near-miss — **not archived**, **not promoted** (2026-06-09)  
**Strategy:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`

## Why this one matters

Best discovery→execution transfer so far on SOL 2025 tp_pct pipeline:

| Metric | NR4 Optuna best | NR7 (archived) | VWAP reclaim (archived) |
| ------ | --------------- | -------------- | ----------------------- |
| Sum capped monthly | **+164.75%** | +58.82% | +50.26% |
| Months ≥ 15% | **8 / 12** | 2 / 12 | 1 / 12 |
| Full-year Optuna objective | **+461%** | +159% | +59% |
| Verdict | discard | discard | discard |

## Mandate truth (ADR-0029 + ADR-0030 re-baseline)

**Artifact:** `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/`

| Metric | Value |
| ------ | ----- |
| Verdict | **discard** |
| Sum capped | **+164.75%** |
| Months ≥ 15% | **8 / 12** |
| Months below 15% floor | **4** — Feb, Mar, Sep, Oct |
| DD breach months (>10%) | **2** — Feb −11.4%, Mar −20.21% |
| Frozen params (trial #59) | tp=0.016, rrr=2.5, ttl=48, risk=2% |

### Why discard, not promote

1. **4 months below 15% floor** (mandate allows max 3).
2. **2 DD breach months** after ADR-0030 window-start DD (was 3 under old rolling-peak DD: Jan, Mar, Jun).
3. Optuna optimized **full-year `total_return_pct`** (+461%), not mandate monthly gates — misaligned objective.

### Re-baseline notes

- **ADR-0029** (isolated always on): no numeric change vs v3 overnight — all trades already used 25× leverage.
- **ADR-0030** (DD from window-start): Jan and Jun no longer DD-breach; economics unchanged.

## Recommended next steps

### Step A — weak-month attribution (cheap, do first)

Inspect Feb, Mar, Sep, Oct under re-baseline:

`results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/runs/sol_2025_0{2,3,9,10}/trade_chart.html`

Look for: clustered SL streaks, session filter edge cases, overlapping positions
(`max_positions=0` = unlimited in Optuna).

### Step B — mandate-aware Optuna (requires code)

Replace `--target total_return_pct` with objective aligned to mandate:

- maximize min monthly return (or mandate capped sum);
- hard constraint or penalty for DD > 10% per month;
- optionally 12-window evaluation per trial (expensive, exact mandate match).

See BACKLOG **P1 — Mandate-aware Optuna objective**. Owner deferred implementation
(2026-06-09 chat).

**Not useful:** re-run `compare-fixed` at risk=1% only — Optuna already searched
risk 1.0–2.0 and chose 2% for full-year return.

### Step C — realism knob

Re-run frozen geometry with **`max_positions=1`** — unlimited concurrent positions
in Optuna may inflate returns and DD.

## Decision matrix

| Outcome | Action |
| ------- | ------ |
| ≥9 months ≥15%, all DD ≤10% | **Promote path** — TON validation, margin sim |
| 8 months ≥15%, 0–1 DD breach after mandate Optuna | **Full Optuna §5.4** with DD constraint |
| Still 2+ DD breaches after mandate Optuna | Filter/label tweak or archive as near-miss |
| <7 months ≥15% | Trade-off: economics vs risk — owner call |

## Artifacts

- v3 overnight: `results/v3_robust_overnight_20260609/nr4_vwap/`
- Optuna: `.../02_optuna_full_year/20260609_095346/best_trial.json`
- v3 mandate (pre-ADR-0030): `.../03_optuna_best_compare/20260609_104342/`
- **Current truth:** `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/`
