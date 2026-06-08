# In progress

## Owner-run overnight — v3 robust candidates (2026-06-09)

Two converted strategies ready for donor validation + tp_pct Optuna:

- `strategies/backtester/crypt_ensemble_h1_discovery_vwap_reclaim_robust.json`
  (238 label events, 57.1% WR)
- `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`
  (404 label events, 57.2% WR)

**Owner:** run overnight script from chat (2026-06-09): baseline `compare-fixed`
→ full-year Optuna 1200 trials (`tp_pct`) → 12-month `compare-fixed` with best
params. Send `mandate_summary.md` + `best_trial.json` per candidate.

---

## Owner-run overnight batch (2026-06-08)

Two parallel owner-run jobs. **Do not start new strategy work until results
return** unless the owner says otherwise in chat.

### PC1 — NR7 execution tuning (tp_pct + risk_percent)

Three-phase bash script: baseline `compare-fixed` (12 SOL 2025 months) →
full-year Optuna (1200 trials: `tp_move_pct`, `rrr`, `ttl`, `risk_percent`
1.0–2.0) → `compare-fixed` with Optuna best params.

Output root: `results/nr7_tp_pct_overnight_<date>/`

**When done, send:**

- `03_optuna_best_compare/<timestamp>/mandate_summary.md`
- `02_optuna_full_year/<timestamp>/trials.csv` (top rows)
- `02_optuna_full_year/<timestamp>/best_trial.json`

### PC2 — deep strategy discovery

12 monthly SOL 2025 windows, `beam-width=50`, `max-filter-depth=5`,
`keep-sparse-triggers`. Goal: find trigger+filter stacks better than NR7.

Output root: `results/discovery_sol_h1_deep_<date>/`

**When done, send:**

- `<timestamp>/top_score.csv`
- `<timestamp>/robust_min_window_win_rate_50.csv`
- `<timestamp>/candidate_windows.csv` for top 3 ranks

### Next agent steps (after owner returns)

1. Compare PC1 `mandate_summary.md` vs Jan baseline (+6.3% single month is not
   enough; need 12-month capped sum and consecutive-loss streak).
2. If PC2 beats NR7 on robust per-window metrics, `convert-discovery-strategy`
   top ranks and run `compare-fixed` with PC1 best tp_pct params.
3. **v3 catalog ready** (44 triggers + 100 filters). For a fresh discovery run
   with expanded catalog, reuse the PC2 command but expect **much longer**
   runtime (100 filters × beam 50 × depth 5). Optional first pass:
   `--beam-width 30 --max-filter-depth 3`. Label experiment:
   `--label-atr-mult 1.5 --label-horizon-bars 36`.
3. Record promote/archive/discard per ADR-0025; update `BACKLOG.md` with
   follow-ups (donor-eligibility gate in discovery, friction floor P1).
