# Backlog

Only unfinished queued work belongs here. Completed work is recorded in
`CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, and archive docs.

Priority labels:

- **P0** — blocker / safety / can break live money or research truth.
- **P1** — important; do after P0 unless the owner redirects.
- **P2** — useful later.

Read `docs/strategy_benchmark.md` before strategy evaluation. The benchmark is
the main optimization target, not a hard limit on owner production selection.

## P0 — Make backfill fail when required downloads fail

**What:** make `python -m crypt.backfill` return a non-zero exit code and a
clear operator error when all required exchange fetches fail or when a requested
timeframe remains missing after the run.

**Why now:** during DSS v3 portfolio evaluation, a sandboxed backfill attempt
printed `Backfill complete` after exchange fetch failures and did not populate
the missing 15m candles. Research/backtest preflight must not treat this as a
successful data repair.

**Expected gain:** missing-candle recovery becomes trustworthy: expensive DSS,
backtest, optimizer, and live bootstrap workflows either have the data or stop
with an exact backfill/error message.

**Acceptance:** failed exchange/network fetches produce a non-zero process
exit when requested data remains unavailable; successful partial repairs report
which timeframes were filled and which remain blocked; tests cover all-failed,
partial-failed, and complete-success backfills.

**Links:** `src/crypt/backfill/__main__.py`,
`src/backtester/cli_runner.py`, `src/crypt/data/store.py`.

## P1 — Add portfolio marginal-impact gate for DSS candidates

**What:** add an explicit post-Optuna gate that tests promoted DSS candidates
against the current production portfolio one-by-one and only marks candidates
portfolio-ready when they improve money/risk metrics.

**Why now:** DSS v3 candidates can pass standalone DSS criteria and Optuna
replay while still being neutral or negative inside the current shared-capital
portfolio. The first one-by-one comparison also exposed mixed-timeframe
composition bugs, so portfolio promotion needs a reproducible current-code
marginal check rather than trusting standalone edge.

**Expected gain:** DSS can keep discovering standalone entries, while promotion
decisions become aligned with the owner's actual portfolio account curve.

**Acceptance:** candidate reports include standalone metrics, optimized exit
geometry, portfolio delta in dollars, return, win rate, profit factor, trade
count, and both drawdown measures; failing candidates remain archived but are
not marked portfolio-ready; the gate is reproducible from saved configs and
metrics.

**Links:** `results/dss_v3_candidate_portfolio_eval_20260804/summary.md`,
`results/recheck_v6_plus_dssv3_016949_after_event_schedule_fix/20260804_134940`,
`results/recheck_v6_baseline_after_event_schedule_fix/20260804_135921`,
`src/backtester/strategies/filtered_donor_portfolio.py`,
`docs/discovery/direct_signal_search.md`.

## P1 — Promote stop-loss selection into explicit post-DSS SL families

**What:** make stop-loss placement an explicit execution-geometry family
searched after DSS, instead of a hidden fallback split between
`directional_sl_move_pct`, legacy `atr_sl_mult`, and strategy-provided
`sl_price`.

**Why now:** DSS v3 intentionally searches entry logic first, then sends
leaders to Optuna for money geometry. SL distance controls position size,
TP distance, liquidation exposure, and exit timing, so it must be a first-class
Optuna choice alongside `exit_family`, `rrr`, `position_ttl_minutes`, and
`risk_percent`.

**Expected gain:** new DSS candidates can fairly compare fixed-percent,
ATR-based, and structural stop families; old archive/prod candidates remain
replayable through their saved legacy geometry.

**Acceptance:** strategy/backtest/optimizer config has an explicit `sl_family`
field; Optuna can search `fixed_pct` (`directional_sl_move_pct`) and `atr`
(`atr_sl_mult`) at minimum; existing `structural` strategy stops are preserved
as their own family/mode; exported best-trial summaries state the winning SL
family and parameters in money-readable terms; legacy candidates with
`atr_sl_mult` reproduce old behavior.

**Links:** `src/backtester/strategies/dss_strategy.py`,
`src/backtester/strategies/dss_incremental.py`,
`src/backtester/optimizer.py`, `docs/backtester/exit_geometry.md`,
`docs/discovery/direct_signal_search_v3.md`.

## P0 — Archive exact live entry snapshots for replay

**What:** persist an immutable replay packet for every live entry: emitted
`signal_event`, closed H1 bar, required warmup/data hashes, next open used for
entry, live order request, actual fill, and protection ids.

**Why now:** fresh recomputation on repaired parquet can change ATR-derived
stop/TP values. Live/backtest parity needs exact live-time inputs.

**Expected gain:** future live replay checks become deterministic and do not
depend on later candle repairs.

**Acceptance:** every live entry writes a compact replay artifact; a replay
utility or documented procedure reproduces planned entry, SL/TP, and
backtester stop/TP minute from that packet.

**Links:** `docs/archive/candidates/post_adr0058_tail_control_portfolio/live_replay_20260714.md`,
`src/crypt/execution/executor.py`, `src/crypt/execution/signal_runner.py`.

## P1 — Finish live/backtest reconciliation report

**What:** complete the July 2026 live SOL cash reconciliation from OKX ledger,
orders/fills, Railway logs/state, Telegram notifications, and exact replay
artifacts.

**Why now:** live execution is a normal project mode; the active production
strategy must be judged against actual exchange behavior, not only backtests.

**Expected gain:** a trusted account-level baseline for future live PnL
interpretation.

**Acceptance:** `docs/execution/live_backtest_reconciliation_2026-07-28.md`
contains matched/unmatched trades, missed signals, stale/catch-up entries,
fees, slippage, cash bridge, and final discrepancy verdict.

**Links:** `docs/tasks/IN_PROGRESS.md`,
`docs/execution/live_backtest_reconciliation_2026-07-28.md`.

## P1 — Attest Railway persistent execution volume before live startup

**What:** add an operator-created immutable volume marker/identifier and
preflight check proving execution state, checkpoint directory, and logs all
resolve under the intended Railway volume before OKX order logic starts.

**Why now:** Railway can create an ephemeral `/app/data` if the volume is
absent or paths drift. Risk-base checkpoints reduce one failure mode but do
not prove durable storage is mounted.

**Expected gain:** bad Railway mount/path configuration becomes an explicit
startup failure instead of a live service with non-durable state.

**Acceptance:** live-money preflight rejects absent/wrong markers before order
placement; staging proves marker/state/checkpoint/log survival; tests cover
correct and incorrect path combinations.

**Links:** ADR-0059, `docs/deploy/railway.md`,
`src/crypt/runtime/deploy_preflight.py`, `scripts/railway_live_start.sh`.

## P1 — Add a single-writer lease for live execution state

**What:** introduce a durable lease or generation compare-and-swap around live
state reconciliation, checkpoint rollover, and entry-intent persistence.

**Why now:** checksums protect torn writes but do not prevent two overlapping
processes from reading the same generation and overwriting each other.

**Expected gain:** redeploys, scheduler overlap, or accidental second process
cannot race a live order intent or erase newer lifecycle state.

**Acceptance:** concurrent-process tests show only one manager can hold the
lease; a second manager fails before order placement; crash/expiry recovery is
documented; state generation never regresses in a forced race.

**Links:** ADR-0033, ADR-0055, ADR-0059,
`src/crypt/execution/executor.py`, `src/crypt/execution/position_state.py`.

## P1 — Accumulate a longer forward sample for the distant-TP mount

**What:** re-evaluate the current `freq_4pw_r03_catcma_011465` 6%/RRR-3
distant-TP mount on a materially longer unseen forward period.

**Why now:** the first holdout beat baseline but contains only 15 days and 24
portfolio trades.

**Expected gain:** distinguish repeatable improvement from small-sample noise
before widening scope or changing thresholds.

**Acceptance:** a longer forward report compares baseline and candidate in
dollars, trade count, win rate, profit factor, and both drawdown measures.

**Links:** `docs/tasks/IN_PROGRESS.md`,
`docs/backtester/tp_reachability_diagnostics.md`.

## P1 — Revalidate or retire legacy SOM/Forest strategy families

**What:** decide whether legacy `som` and `forest` ML strategies should be
rerun, retrained, or retired after the causal order-block feature fix.

**Why now:** old model artifacts and backtests used different feature
semantics and may be inflated.

**Expected gain:** prevent invalid ML artifacts from contaminating future
portfolio selection or filter research.

**Acceptance:** archived notes mark old artifacts invalid, or corrected
rerun/retrain reports show honest dollars, drawdown, liquidation count, and
benchmark verdict.

**Links:** `src/backtester/strategies/som.py`,
`src/backtester/strategies/forest.py`, `tests/backtester/test_som_features.py`.

## P1 — Calibrate H1 execution and mark-price liquidation realism

**What:** compare baseline against measured H1-open slippage, historical
triggered-limit rejection, taker TP, and mark-price liquidation scenarios.

**Why now:** live fills occur seconds after H1 open and OKX liquidates on mark
price; last-trade H1 OHLC cannot reproduce this exactly.

**Expected gain:** reports distinguish deterministic policy parity from
unavoidable exchange execution uncertainty and quantify the dollar cost.

**Acceptance:** a report documents the selected execution model and its impact
on dollars, drawdown, liquidation count, and rejected entries.

**Links:** `docs/execution/live_backtest_parity_audit_2026-06-30.md`,
ADR-0054, ADR-0056.

## P1 — Core portfolio off-switch research

**What:** research entry-known portfolio-level controls for current production
portfolio branches: day-level loss pauses, session windows,
volatility/trend-regime gates, and per-strategy risk throttles.

**Why now:** strong portfolios still have concentrated damage in specific
months/regimes. Simple global risk cuts reduce dollars too much.

**Expected gain:** preserve most production-branch upside while reducing
worst-period drawdowns.

**Acceptance:** exact artifacts compare baseline against at least three
controls in dollars, drawdown, positive/negative months, worst month, median
month, and top-month profit concentration.

**Links:** `docs/archive/candidates/post_adr0058_tail_control_portfolio/`.

## P2 — Investigate pytest shutdown hang after H1 executor thread-pool test

**What:** isolate why
`test_on_h1_close_rechecks_sync_after_marking_missing_position_closed` passes
but the pytest process may not terminate after `run_in_executor`.

**Why now:** a hanging focused test weakens confidence in one-command execution
test runs.

**Expected gain:** restore a trustworthy execution test suite and confirm clean
shutdown after threaded signal generation.

**Acceptance:** the isolated test exits with code 0, and
`pytest tests/execution -q` terminates successfully.

**Links:** `src/crypt/execution/executor.py`,
`tests/execution/test_executor_multi_event.py`.

## P2 — Bring donor backtester under root quality gates

**What:** gradually bring `src/backtester/` and `tests/backtester/` under root
strict mypy and ruff rules.

**Why now:** the donor package is root-integrated but still excluded from some
strict checks because of inherited style/type debt.

**Expected gain:** reduce hidden breakage in the research engine without mixing
style churn into strategy work.

**Acceptance:** CI expands strict checks to donor code with targeted ignores
only where justified.

**Links:** `src/backtester/`, `tests/backtester/`, `pyproject.toml`.

## P2 — Documentation and operator hygiene

**What:** keep operator docs current as live execution changes: Telegram
commands, observability, runbooks, and archive reading instructions.

**Why now:** production execution depends on fast owner interpretation of
alerts, state blockers, and replay/audit artifacts.

**Expected gain:** fewer ambiguous incidents and faster handoff between
agents.

**Acceptance:** docs updated alongside behavior changes; archive docs explain
how to read candidate packages without maintaining a separate status table.

**Links:** `docs/operator.md`, `docs/operations/`,
`docs/archive/candidates/README.md`.
