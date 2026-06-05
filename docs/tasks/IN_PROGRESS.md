# In progress

## Next steps — P0 mandate-metrics CLI

Post-ADR-0026 margin validation is **complete**. Owner ran all three
`risk_percent` grids (`1.0`, `0.5`, `0.25`); peak margin scales monotonically
on every window; economics scale linearly (`+10.12%` → `+5.06%` → `+2.51%`).

**Take next:** implement P0 mandate evaluation from `BACKLOG.md` — CLI/report
that reads a donor backtest artifact and exports per-month raw/capped returns,
intra-month max DD, consecutive losing months, and a
promote/archive/discard/full-Optuna verdict per `docs/investment_mandate.md`.

**Reference artifacts (post-margin-fix bounded row):**

- `results/crypt_ensemble_h1_short_only_post_margin_fix/20260605_152526/`
- `results/crypt_ensemble_h1_short_only_post_margin_fix_rp05/20260605_154035/`
- `results/crypt_ensemble_h1_short_only_post_margin_fix_rp025/20260605_154905/`

**Candidate params (unchanged):** `rrr=1.5`, `ttl=42`, `max_positions=1`,
short-only filtered H1 strategy. Not promotable under mandate (+15%/month).
