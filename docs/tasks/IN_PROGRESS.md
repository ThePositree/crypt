# In progress

Only active work belongs here. Historical research notes belong in
`CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, or archive docs.

## Live execution / backtest reconciliation audit

**What:** finish the evidence-backed reconciliation of the live SOL portfolio
from the first real July 2026 entry through the current live period. Compare
Railway logs/state, Telegram notifications, OKX fills/orders/ledger, deployment
boundaries, and exact replay artifacts.

**Why now:** live execution is a normal project mode. Strategy quality cannot
be judged from backtest PnL alone while the live path includes exchange sync
blocks, restarts, catch-up behavior, aggregate OKX accounting, and repaired
candle history.

**Expected gain:** a cash-level verdict for the active production strategy:
matched/unmatched entries, missed signals, extra stale/catch-up entries,
fees, slippage, balance changes, and final dollar discrepancy.

**Current evidence:**

- Effective portfolio path in the audit:
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`.
- Existing replay artifacts:
  `results/live_reconciliation/v6_capital_104_77/20260728_162345`
  and `results/live_reconciliation/v6_capital_102_34/20260728_162357`.
- Phase B matched all 16 real post-rollout entries and identified one missed
  short at `2026-07-23 12:00 UTC`, worth about `+$4.99897320` in deterministic
  replay.
- Phase A remains historically non-deterministic after H1 repair; use stored
  strict replay values for the first three entries rather than fresh
  recomputation.

**Next steps:**

1. Get the owner-run continuous phase-B extension and final OKX ledger/order
   snapshot for the 28 July events and later live period.
2. Join replay artifacts to OKX fills/orders/ledger.
3. Classify every unmatched row as normal fill/slippage, sync-blocked missed
   signal, delayed/catch-up entry, accounting/protection recovery, changed
   candle, or unresolved data gap.
4. Write the final verdict in
   `docs/execution/live_backtest_reconciliation_2026-07-28.md`.

**Acceptance:** the report gives live entry count, closed/open trade count,
gross/net dollars, fees, entry/exit drift, matched/unmatched rows, cash bridge,
and a clear discrepancy verdict.

**Links:** `docs/execution/live_backtest_reconciliation_2026-07-28.md`,
ADR-0048 through ADR-0059, `/app/data/live_positions.json`,
`/app/data/logs/crypt.log*`.

## Distant TP monitoring for current v6 portfolio

**What:** keep monitoring the owner-selected narrow distant-TP mount on the
current v6 production portfolio.

**Why now:** the owner selected the `freq_4pw_r03_catcma_011465` TP-distance
mount for production, but the untouched positive forward sample is short
(`2026-07-13` through `2026-07-27`, 24 portfolio trades).

**Expected gain:** determine whether the TP adjustment keeps improving dollars
and drawdown on a longer unseen sample before widening it to any other donor or
changing thresholds.

**Current evidence:**

- Full-history baseline v6:
  `results/strategy_review/v6_2022_2026_baseline_full/20260729_083245/`
  — 1,508 trades, `+$946,449.50` PnL, peak-to-trough DD `-39.23%`.
- Best targeted full-history mount:
  `results/strategy_review/v6_tp_search_r03_d6_only_rrr3/20260729_105954/`
  — 1,560 trades, `+$1,175,598.82` PnL, peak-to-trough DD `-33.26%`.
- First untouched forward check:
  baseline `+$307.89`, candidate `+$481.48`, same 24 trades, candidate DD
  `-8.71%` versus baseline `-9.50%`.
- Other tested donor mounts did not help enough to combine.

**Current production selection:** the canonical v6 portfolio keeps
`params.components.distant_tp.enabled=false` globally and enables only
`freq_4pw_r03_catcma_011465` with original RRR `>=4`, TP distance `>=6%`,
and effective RRR `3.0`.

**Next steps:**

1. Re-run baseline versus candidate on a materially longer unseen live/forward
   range once enough candles and trades exist.
2. Compare dollars, trade count, win rate, profit factor, peak-to-trough
   drawdown, and below-start drawdown.
3. Do not widen the mount unless the longer comparison beats unchanged v6 in
   dollars and risk without an unacceptable frequency change.

**Acceptance:** a longer forward report confirms or rejects the current narrow
mount. Any threshold or donor-scope change must be backed by a new exact
comparison artifact.

**Links:** `docs/backtester/tp_reachability_diagnostics.md`,
`docs/archive/candidates/post_adr0058_tail_control_portfolio/`,
`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`.
