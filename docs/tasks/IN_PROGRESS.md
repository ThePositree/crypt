# In progress

Only active work belongs here. Historical research notes belong in
`CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, or archive docs.

## Public documentation portal

**What:** design and build a public Russian-language documentation portal that
presents `crypt` as a research-to-execution framework for developers who also
trade crypto.

**Approved direction:** curated Next.js and Tailwind CSS pages rather than
repository Markdown rendering; deep technical content; local full-text search;
classic documentation navigation; equal desktop/mobile priority; dark pastel
cartoon lo-fi crypto workshop identity with recurring researcher, backtester
robot, and live-execution operator characters. Strategy performance results and
all trading controls are out of scope.

**Current phase:** D3 Product Surface revision 1 was approved by the owner on
2026-09-01. Three raster Visual Direction Boards were generated and inspected
under an owner waiver that narrows the canonical five-board requirement.
Visual Direction Approval is complete. Thirteen page contracts, three flows,
and 78 rendered wireframes are ready; Wireframe Approval is now the active gate.
Production frontend code has not started.

**Next steps:**

1. Obtain Wireframe Approval for revision 1.
2. Complete production content/source manifests and the bounded Final
   Implementation Approval package.

**Links:** `docs/frontend/product-surface-model.md`,
`docs/frontend/messaging.md`, and
`docs/frontend/decisions/0001-docs-portal-onboarding.md`.

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
- Phase C preliminary boundary: the latest production deploy that changed live
  behavior was Railway deployment `53cb7675-7d0d-4cbb-bc94-fbfab71c5594`
  (`81a4e01`, `2026-07-29T12:12:04Z`), which added the live distant-TP
  reachability adjustment and changed the production strategy JSON. The later
  production deploy `0f4d69e7-cf5b-411a-a72d-7a1297ab8651` (`0b76c30`,
  `2026-07-30T15:32:49Z`) was documentation/status cleanup for runtime code.
  The `exchange_closed_unknown` OKX child-fill classifier fix is local commit
  `2704c83` and is not deployed to Railway production.
- Phase C accounting starts from the first post-boundary fill at
  `2026-07-29T13:00:35.321Z`; deterministic replay should start at signal bar
  `2026-07-29T12:00:00Z` to include that `13:00` next-open entry.
- Preliminary phase-C artifacts live under
  `results/live_reconciliation/phase_c_20260729/`: OKX fills/orders/algo
  orders/account bills, grouped order fills, and a closed-window replay through
  `2026-08-10T22:00:00Z` with `$83.0980436609` starting cash.
- Phase C OKX truth through the closed `2026-08-10` UTC window: 20 phase
  entries, 17 phase closes, and 3 phase positions still open before
  `2026-08-11T00:00Z`. One additional OKX close at
  `2026-07-30T13:47:32Z` is a carried-in pre-phase short close and must be
  handled separately in the cash bridge.
- The unreleased `exchange_closed_unknown` fix affects close classification
  for OKX child fills that lack the expected attached-order identity. It does
  not change OKX money, entries, sizing, SL, or TP; use it as notification and
  reconciliation-label context only.
- Log-backed phase-C join artifacts now include
  `log_extracts/railway_live_entries.csv`,
  `log_extracts/railway_live_closures.csv`,
  `phase_c_live_backtest_match_log_joined.csv`, and
  `phase_c_live_backtest_match_81a4e01_log_joined.csv`.
- Replaying with local `HEAD` was misleading for at least one mismatch: the
  `2026-08-03T18:00Z` live long had live raw SL `72.9871` rounded to
  `72.99`, and production-commit replay (`81a4e01`) also exits at
  `2026-08-04T00:58Z` with SL `72.99`. The later local `HEAD` replay computes
  SL `72.98` and exits on `2026-08-06T13:05Z`.
- Production-commit replay exposed a separate backtester audit gap: old CLI
  `--from` cut history before feature generation. Starting exactly at the
  phase boundary missed the live `2026-07-29T12:00Z` signal; starting with
  warmup from `2026-07-13T00:00Z` restored that signal with live SL `74.2025`,
  but also changed phase sizing/capital because pre-phase trades were
  executed.
- Current phase-C verdict: no critical production live money-path bug has been
  found. The required backtester fix for separate warmup and accounting
  windows is implemented via `--load-from`; deployed-commit pinning remains
  an audit discipline. The unreleased `exchange_closed_unknown` patch is
  useful reconciliation/notification cleanup but not urgent for money safety.
- Backtester `run` now supports explicit `--load-from` warmup separate from
  `--from` execution/accounting, and `docs/backtester_regression.md` includes
  phase C as a strict checkpoint.
- OKX phase-C money snapshot through entries known by `2026-08-11T06:00Z`:
  22 phase entries, 17 closed, 5 open; closed gross PnL
  `-9.6593364339` USDT, closed net PnL with entry/close fees
  `-11.2359839739` USDT, and realized net including entry fees for still-open
  phase trades `-11.3644334239` USDT. Current OKX account query showed
  total equity about `$74.25`, cash balance about `$63.78`, isolated position
  equity about `$10.54`, and open-position unrealized PnL about `+$0.24`.

**Next steps:**

1. Re-run the phase-C cash bridge on production commit `81a4e01`, using OKX
   fills as truth for fill prices, fees, and close times.
2. Extend phase-C replay once current-day last/mark 1m data is complete enough
   to include `2026-08-11T00:00Z` and later entries.
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
