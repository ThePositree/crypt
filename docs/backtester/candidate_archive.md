# Candidate archive layout

Contract for shelving discovery→donor candidates that are **not promoted**
but worth keeping.

The archive has two roles:

1. preserve production near-misses and superseded candidates;
2. preserve research strategies for future regime discovery and detector
   training, even when they do not pass the full investment mandate.

Archive is **git-tracked** under `docs/archive/candidates/` and
`strategies/archive/`. Full backtest artifacts stay under `results/` (gitignored);
each archive entry records the local artifact paths in `provenance.json`.

## When to archive

| Situation | Action |
| --------- | ------ |
| Superseded by a better candidate (same symbol/horizon) | Archive with reason `superseded` |
| Mandate **archive** verdict (any month intra-month DD > 10%) | Archive with reason `mandate_dd` |
| Near-miss economics but owner stops work | Archive with reason `near_miss` |
| Regime-specific or weakly profitable strategy useful for detector research | Archive with reason `regime_seed` |
| Strategy with useful signal-quality/failure-mode evidence | Archive with reason `research_seed` |
| Mandate **discard** with no redeeming research value | Do **not** archive; note in BACKLOG only |

NR7 and VWAP reclaim (2026-06-09): archived as **superseded** by NR4 v3 candidate.

## Research archive criteria

A strategy may be archived for future regime work even if it does not promote
or meet the mandate archive tier. At least one of these must be true:

- positive or weakly positive return on a meaningful window;
- clear regime-specific performance;
- diversified trigger/filter family compared with existing archive entries;
- high Stage 1 signal quality but insufficient trade count;
- useful negative/failure mode that helps separate regimes;
- owner explicitly marks it as worth keeping.

The archive entry must state the reason. Do not hide mandate failure. Research
archive entries should make it obvious whether the candidate is production
near-miss, regime seed, or diagnostic seed.

## Directory layout

```text
docs/archive/candidates/
  README.md                          # index of all archived candidates
  <candidate_id>/
    README.md                        # owner-facing verdict/research note (required)
    mandate_snapshot.md              # copy of mandate_summary.md at archive time
    monthly_mandate.csv              # copy of monthly_mandate.csv
    execution_params.json            # frozen donor execution knobs
    provenance.json                  # metadata + results/ artifact paths

strategies/archive/
  crypt_ensemble_h1_discovery_<name>.json   # frozen strategy JSON (copy)
```

### `README.md` (per candidate)

One screenful:

1. **Candidate id** and trigger+filters one-liner
2. **Archive reason** (`superseded` | `mandate_dd` | `near_miss` |
   `regime_seed` | `research_seed`)
3. **Best run** (symbol, window, verdict if applicable, return, trade count)
4. **Best execution params** (exit geometry, tp/rrr/ttl/risk)
5. **Why kept / why not promoted** (one paragraph)
6. **Superseded by** (if applicable)
7. **Local artifact paths** (under `results/`)
8. **Regime/discovery value** when the reason is `regime_seed` or
   `research_seed`

### `execution_params.json`

Frozen execution layer used for the archived mandate snapshot:

```json
{
  "exit_geometry": "tp_pct",
  "structural_sl_mode": "ignore",
  "risk_base_period": "monthly",
  "tp_move_pct": 0.014,
  "rrr": 2.25,
  "ttl": 24,
  "risk_percent": 2.0
}
```

### `provenance.json`

```json
{
  "candidate_id": "h1_nr7_breakout__bb_squeeze__h4_context_aligned",
  "archived_at": "2026-06-09",
  "archive_reason": "superseded",
  "superseded_by": "h1_nr4_breakout__avoid_doji__vwap_dist_max_1pct__vwap_dist_min_0_2pct",
  "strategy_path": "strategies/archive/crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json",
  "discovery_artifact": "results/discovery_sol_h1_2025_v2/20260608_123558/",
  "mandate_artifact": "results/nr7_tp_pct_overnight_20260608/03_optuna_best_compare/20260608_163635/",
  "optuna_artifact": "results/nr7_tp_pct_overnight_20260608/02_optuna_full_year/20260608_154533/",
  "git_commit": "24c73a0c2c01b6d2915dacb726319ad5a56cfcd8"
}
```

## Active vs archived strategies

| Location | Role |
| -------- | ---- |
| `strategies/backtester/` | **Active** candidates only (currently NR4) |
| `strategies/archive/` | Frozen copies; safe to re-run for comparison |
| `docs/archive/candidates/` | Verdict/research notes + reproducibility metadata |

Do not delete archived strategy JSON from git. Do not run Optuna on archived
production candidates unless the owner explicitly revives one in chat. Research
archive entries may be used later by the regime performance matrix, Labeler,
Detector, and Portfolio Router work.

## Related

- ADR-0025 — promote / archive / discard gates
- ADR-0041 — regime discovery from archived strategy behavior
- `docs/investment_mandate.md` §3.1 — monthly DD archive rule
- `docs/mandate_reporting.md` — verdict logic
- `docs/regime_detection.md`
