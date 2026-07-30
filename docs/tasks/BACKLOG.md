# Backlog

Only unfinished queued work belongs here. Completed work is recorded in
`CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, and archive docs.

Priority labels:

- **P0** — blocker / safety / can break live money or research truth.
- **P1** — important; do after P0 unless the owner redirects.
- **P2** — useful later.

Read `docs/strategy_benchmark.md` before strategy evaluation. The benchmark is
the main optimization target, not a hard limit on owner production selection.

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

## P1 — Implement DSS v3 persistent multi-timeframe search

**What:** evolve DSS without renaming it: make timeframe a first-class part of
every trigger/filter instance, allow repeated filter names on different
timeframes, add shared random unseen/novelty injection to all search backends,
remove DSS v2 Stage 2/3 backtests from DSS v3, keep Stage 1 directional
labeling as the only evaluator, replace the single min-trade gate with
frequency-class-aware archives so sparse and frequent candidates can be found
in one run, break DSS v2 compatibility where useful, and add resumable endless
search when `--n-trials` is omitted.

**Why now:** the current active strategy and catalog search are effectively
single-primary-timeframe. Useful edge may live in combinations such as
`trigger@5m`, local filter `@5m`, setup filter `@H1`, and regime filter `@H4`.
Large search space is intentional, but it needs persistent journals, stable
candidate hashes, feature caching, and forced exploration so long searches can
run continuously beside live execution. The final product is a portfolio, so
DSS must preserve both frequent candidates and rare high-quality candidates for
downstream combination tests.

**Expected gain:** a research engine that keeps looking for new strategy
families over large multi-timeframe spaces instead of only optimizing current
H1-style families, while staying fast because DSS v3 does not optimize trading
geometry.

**Acceptance:** DSS v3 candidate schema is implemented; exact duplicate
instances are rejected while same filter name on different timeframes is
allowed; seen-candidate registry prevents repeat evaluations; every backend
periodically injects valid random unseen candidates; DSS v3 candidates contain
no `rrr`, `risk_percent`, `position_ttl_bars`, `atr_sl_mult`, trailing, or
portfolio sizing fields; DSS v3 does not run Stage 2/3 backtests; endless mode
resumes from an existing output directory with durable journal/archive/backend
state; Stage 1 reports and archive cells distinguish sparse, medium, frequent,
and overactive candidates; a bounded smoke run can preserve both a `20-30`
signals/year candidate and a frequent candidate without separate command
profiles; archive/export ranking uses per-frequency-class quotas so sparse
high-win-rate candidates cannot fill the entire shortlist and frequent
candidates cannot erase sparse candidates through a global floor; old DSS v2
state/candidate/export artifacts are not required to resume through DSS v3;
bounded smoke searches prove no look-ahead in lower-timeframe trigger plus
higher-timeframe filter alignment.

**Links:** ADR-0062, `docs/discovery/direct_signal_search_v3.md`,
`src/backtester/strategy_discovery/`.

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
