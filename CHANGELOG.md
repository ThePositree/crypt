# Changelog

All notable changes to this project will be recorded here, session by session.

Format: keep entries terse. Date in `YYYY-MM-DD`. Newest on top.

---

## 2026-06-05 — Post-margin-fix validation grids (owner-run)

- Owner completed bounded H1 short-only grids at `risk_percent = 1.0`, `0.5`,
  `0.25` after ADR-0026.
- Confirmed monotonic `peak_locked_margin_pct_initial` on all seven windows;
  aggregate return scales `+10.12%` → `+5.06%` → `+2.51%`; max peak margin
  `46.38%` → `23.19%` → `11.59%` (no `96.62%` plateau).
- Margin audit acceptance passed; candidate still not mandate-promotable.
- Next: P0 mandate-metrics CLI.

**ADRs:** ADR-0026 applies.

**Verification:** owner-run `compare-grid` artifacts; Python cross-check of
three `grid.csv` files.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — Isolated-margin leverage selection (ADR-0026)

- Audited donor margin geometry after the H1 `max_positions = 1` grid kept peak
  locked margin at `96.62%` when `risk_percent` was lowered.
- Added `margin_policy.py`; unified per-slot caps across `risk_model.py` and
  `execution_sim.py`; switched to max-leverage locked-margin selection when the
  position fits the cap.
- Added `tests/backtester/test_margin_policy.py`; updated execution-sim margin
  expectations.
- Next: re-run bounded H1 short-only grids, then P0 mandate-metrics CLI.

**ADRs:** ADR-0026 (new).

**Verification:** `uv run pytest tests/backtester -q` (all passed).

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`.

## 2026-06-05 — Owner investment mandate (ADR-0025)

- Documented auto-trading candidate gates in `docs/investment_mandate.md`:
  +15%/month ($1 500 on $10k), 2025 full-year SOL-first backtest, 10% intra-month
  max DD, capped positive outliers at 20%, archive/discard/full-Optuna funnel.
- Added ADR-0025; surfaced mandate in `README.md`, `AGENTS.md` session-start
  list, and `BACKLOG.md` header.
- Approved capped-profit policy from `IDEAS.md`; added backlog items for mandate
  metrics, trailing stop, stop-limit Optuna dims, and archive layout.

**ADRs:** ADR-0025 (new).

**Verification:** documentation only.

**Files touched:** `docs/`, `README.md`, `AGENTS.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 finite-position grid result

- Inspected the completed owner-started `max_positions` grid at
  `results/crypt_ensemble_h1_short_only_max_positions_grid/20260605_125237`.
- Best aggregate row: `rrr = 1.5`, `ttl = 42`, `max_positions = 1`,
  `risk_percent = 1.0`, totaling `+10.12%` across seven windows.
- Reran that bounded row at `risk_percent = 0.5` and `0.25`. Returns/drawdowns
  scaled down to `+5.06%` / `-4.45` and `+2.51%` / `-2.24`, but peak locked
  margin still reached `96.62%` of initial capital.
- Decision: not promoted; lower risk sizing alone does not fix the margin
  realism blocker. Added a P0 follow-up to audit finite-position margin sizing
  semantics before H1 promotion.

**ADRs:** ADR-0024 applies; none added.

**Verification:** owner-started artifact inspection plus two completed
`backtester compare-grid` lower-risk repeats; no tests run.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — `max_positions` search wiring

- Added optimizer search for `max_positions` via explicit
  `--max-positions-values`, with low/high/step range flags still available.
- Added `compare-grid --max-positions-values` so bounded execution grids can
  compare `rrr` / `ttl` / concurrent-position caps while reusing one signal
  frame per window.
- Exported `max_positions` in fixed/grid/signal-quality summaries and made
  optimizer `best_run/` respect the selected value.
- Updated README/MTF docs and task trackers for the finite-position-cap
  workflow required by ADR-0024.

**ADRs:** ADR-0024 applies; none added.

**Verification:** targeted optimizer/report pytest `11 passed`; changed-file
formatter check clean; changed-file `ruff check --select E,F,I --ignore E501`
clean; `optimize --help` and `compare-grid --help` show the new flags.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 margin-realism audit

- Added trade-level margin exports: `locked_margin`,
  `available_balance_before`, `open_positions_before`,
  `total_locked_margin_before`, and `total_locked_margin_after_entry`.
- Added report-level peak margin/concurrency columns to `compare-fixed` /
  execution-grid summaries and margin rows to `trade_diagnostics.csv`.
- Reran the seven-window short-only H1 audit at
  `results/crypt_ensemble_h1_short_only_margin_audit/20260605_122841`.
- Result: unconstrained short-only remains `+3.96%` overall but is not
  promotable; peak simultaneous positions reached 18 and peak locked margin
  reached `104.42%` of initial capital.
- Updated docs to make finite `max_positions` the next required P0 before
  owner-run promotion checks.

**ADRs:** ADR-0024 applies; none added.

**Verification:** targeted backtester pytest `49 passed`; changed-file
formatter check clean; changed-file `ruff check --select E,F,I --ignore E501`
clean. Full root ruff still fails on pre-existing donor style debt.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 short-only candidate validation

- Completed fixed-candidate validation for
  `strategies/backtester/crypt_ensemble_h1_filter_short_only.json` with
  `rrr = 1.25`, `position_ttl_bars = 36`, and `risk_percent = 1.0`.
- Seven-window result across SOL Jan/Feb/Mar 2025 and TON Jan/Feb/Mar/Apr
  2025: total `+3.96%`, 470 short-only trades, 3 positive windows, 3 negative
  windows, 1 flat no-trade window. Worst window was TON March at `-10.65%`,
  `profit_factor = 0.66`, max drawdown `-20.52`; TON April produced no trades.
- Conclusion: useful diagnostic, not promoted. ADR-0024 still blocks H1
  promotion until margin usage, concurrent positions, and finite
  `max_positions` behavior are auditable.
- Added a P2 backlog follow-up to align `compare-fixed` defaults/docs with the
  seven-window candidate-validation acceptance set.

**ADRs:** ADR-0024 applies; none added.
**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — Margin-realistic H1 concurrency documented

- Recorded ADR-0024: H1 candidates cannot be promoted until concurrent
  position and margin usage are auditable.
- Documented that `capital_before` / `capital_after` are realized-equity
  fields, not free-margin fields.
- Added P0 follow-ups to export margin diagnostics and make `max_positions` a
  bounded Optuna/search dimension before promoting short-only.
- Added a P1 follow-up for explicit isolated-futures liquidation/effective-stop
  modeling before using maximum leverage as a candidate assumption.

**ADRs:** added ADR-0024.

**Verification:** documentation-only update; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

## 2026-06-04 — H1 filter comparison and ablations

- Ran full base-vs-filtered H1 signal-quality diagnostics across SOL
  Jan/Feb/Mar 2025 and TON Jan/Feb/Mar/Apr 2025.
- Added focused ablation configs for short-only, no-liquidity-sweep,
  max-72h-anchor-age, and short-plus-no-liquidity-sweep comparisons.
- Results: base `-12.72%`; full filter `+2.31%`; short-only `+3.96%`;
  no-liquidity-sweep `-8.29%`. The full filter is not promoted; the next
  bounded candidate should be short-only.
- Updated task trackers with the completed artifacts and the next validation
  handoff.

**ADRs:** none.

**Verification:** completed `backtester signal-quality` runs with
`UV_CACHE_DIR=/tmp/uv-cache` for base, full filter, short-only, and
no-liquidity-sweep reports.

**Files touched:** `strategies/`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — H1 signal-quality diagnostics and filters

- Added `backtester signal-quality` for report-only H1 diagnostics across
  SOL/TON windows, exporting `signals.csv` / `groups.csv`, Markdown copies,
  fail-soft `errors.csv`, and per-window donor artifacts.
- Added H1 diagnostic filters to `crypt_ensemble`: `allowed_sides`,
  `blocked_sl_anchor_types`, `max_anchor_age_hours`, and
  `block_context_reversal`, with `signal_filter_reason` exported on signals.
- Added `strategies/backtester/crypt_ensemble_h1_filtered.json` as a
  diagnostic profile for short-only, no-liquidity-sweep-anchor, max-72h-anchor
  age, and context-reversal checks.
- Updated `AGENTS.md` so task docs must include what/why/gain/acceptance and
  agents must explain selected task intent at session start and read the next
  step back at session end.
- Updated README, MTF spec, migration docs, and task trackers for the new
  diagnostic workflow.

**ADRs:** none.

**Verification:** `uv run pytest tests/backtester -q` -> 114 passed with 4
existing pandas timezone-to-period warnings; `uv run ruff check` on changed
backtester tests clean; `uv run backtester --help` and
`uv run backtester signal-quality --help` verified with `UV_CACHE_DIR=/tmp`;
short SOL base and filtered `signal-quality` smokes completed under `/tmp`.

**Files touched:** `AGENTS.md`, `README.md`, `src/backtester/`,
`tests/backtester/`, `strategies/`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — Document mise as optional

- Clarified that `uv` / `pyproject.toml` are the canonical dependency,
  script, and Python-tooling surface.
- Documented root `mise.toml` as an optional local convenience layer that
  wraps the same `uv` commands.

**ADRs:** none.

**Verification:** documentation-only update; no tests run.

**Files touched:** `README.md`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — Root-integrated backtester package

- Added ADR-0023 for the new layout: `backtester` now lives under
  `src/backtester/` inside the root `uv` project.
- Moved donor tests to `tests/backtester/` and strategy JSON configs to
  `strategies/backtester/`.
- Removed the old nested `backtester/` project boundary: donor
  `pyproject.toml`, donor `uv.lock`, Hatch/versioningit config, donor
  `mise.toml`, donor `.cursor` rules, local venv/cache/results, and unused
  donor dashboard/scripts/gui files.
- Added root `mise.toml` and root `backtester` console script.
- Merged donor runtime dependencies into root `pyproject.toml` and refreshed
  `uv.lock`.
- Retired and deleted the obsolete `src/crypt/backtest/` harness and
  `tests/backtest/` after usage search found no live imports outside stale
  docs/self-tests.
- Updated README, backfill/backtester docs, CI/pre-commit/mise commands, and
  task trackers for root-level backtester usage.

**ADRs:** added ADR-0023; updated ADR-0018 and ADR-0021 with supersession
notes.

**Verification:** `uv run pytest -q` -> 187 passed with 4 existing pandas
timezone-to-period warnings; `uv run pytest tests/backtester -q` -> 108
passed with the same warnings; `uv run mypy --strict src/crypt` clean; root
gated `ruff check` and `ruff format --check` clean; `uv run backtester --help`
works; `uv lock --check` clean.

**Files touched:** `src/backtester/`, `src/crypt/`, `tests/`,
`strategies/`, `docs/`, `.github/`, root tooling files.

## 2026-06-04 — Owner-run H1 artifacts and grid fail-soft

- Unpacked and inspected owner-provided `results.tar` from the unattended H1
  diagnostic commands.
- Reviewed full candidate A results: SOL full was only mildly positive
  (`+4.39%`, PF `1.09`) and TON full failed badly (`-54.65%`, PF `0.71`,
  max drawdown `-54.49`), so candidate A is rejected as calibration.
- Reconstructed the aborted monthly `compare-grid` from per-run artifacts:
  360 candidates across 10 completed windows, no robust `rrr`/`ttl` candidate,
  and no candidate with at least 7 positive windows.
- Changed `backtester compare-grid` to preserve completed summaries when some
  windows fail, writing `grid.csv` / `grid.md` plus `grid_errors.csv` /
  `grid_errors.md`.
- Added a focused regression test and updated README/task docs for the new
  fail-soft output and next diagnostic direction.

**ADRs:** none.

**Verification:** ruff check and format clean on changed report/test files via
root `uv --group dev`; targeted donor pytest `6 passed` with 4 existing
pandas timezone-to-period warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Precomputed execution-grid signals

- Inspected SOL March diagnostics for the best grid row and candidate A:
  failures are short-only, bearish-context, stop-loss dominated, and clustered
  around the March 11-14 rebound.
- Found order-block anchored shorts negative while pivot-anchored shorts were
  positive in both inspected SOL March rows.
- Changed `backtester compare-grid` to generate one `crypt_ensemble` signal
  frame per symbol/window and reuse it across `rrr` / `ttl` execution
  candidates.
- Kept deterministic grid report ordering and moved `--jobs` work units to
  independent windows after signal reuse.
- Added a focused test for one signal build across multiple execution
  candidates.
- Updated README and task docs for the new `compare-grid` signal-reuse path.

**ADRs:** none.

**Verification:** ruff check and format clean on changed report/test files;
targeted donor pytest `5 passed`; `compare-grid --help` verified; tiny SOL
smoke at `/tmp/crypt_compare_grid_precomputed_smoke/20260603_160558` completed
with one signal build, two candidate exports, and byte-identical `signals.csv`
files.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — SOL March execution grid

- Added `backtester compare-grid` for bounded execution-only `rrr` / `ttl`
  grid reports with `grid.csv`, `grid.md`, and per-candidate donor artifacts.
- Added `--jobs N` to `compare-grid` for process-level candidate/window
  parallelism.
- Backfilled missing local SOL OHLCV data via `crypt.backfill` so the SOL
  March 2025 H1 window can be reproduced locally.
- Ran the SOL March grid at
  `/tmp/crypt_execution_grid_sol_mar/20260603_153612`.
- Result: all 9 candidates remained negative; best was `rrr = 1.0`,
  `ttl = 30`, `total_return_pct = -6.15`, `profit_factor = 0.66`,
  max drawdown `-11.20`, 64 short-only trades.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/report/test
paths; targeted donor pytest `4 passed`; `compare-grid --help` verified; SOL
March grid completed and exported artifacts.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Parallel fixed-candidate windows

- Added `--jobs N` to `backtester compare-fixed` for process-level parallel
  execution of independent windows.
- Kept `--jobs 1` as the default serial path and preserved deterministic
  `windows.csv` / `windows.md` row order when workers finish out of order.
- Added duplicate window-label validation to prevent run artifact overwrites.
- Updated README fixed-candidate docs with the new `--jobs` option.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/report/test
paths; targeted donor pytest `3 passed`; `compare-fixed --help` shows
`--jobs`.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Optimization acceleration planning

- Documented the safe path for speeding up donor H1 optimization: parallelize
  fixed-window/tiny-grid workloads first, then add precomputed signal reuse,
  then disk-backed signal caching, and only then guarded optimizer `--jobs`.
- Added P1 backlog items for `compare-fixed`/tiny-grid parallelization,
  disk-backed `crypt_ensemble` signal cache, guarded optimizer parallelism,
  and explicit precomputed-signal execution-only optimization.
- Recorded the key guardrail: broad full-history `--strategy-param-search`
  should not be parallelized before workers can share or reuse generated
  signal frames.

**ADRs:** none.

**Verification:** documentation-only update; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

## 2026-06-03 — Owner idea parking lot

- Added `docs/tasks/IDEAS.md` for owner ideas that should be remembered for
  later but not implemented without explicit approval.
- Recorded the first idea: cap oversized monthly backtest profits for
  calibration/report ranking while still preserving raw monthly returns in the
  report.
- Updated `AGENTS.md` so future agents read `IDEAS.md`, remind the owner about
  relevant ideas, and ask for approval before moving any idea into backlog,
  specs, or code.

**ADRs:** none.

**Verification:** documentation-only process update; no tests run.

**Files touched:** `AGENTS.md`, `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Fixed H1 candidate comparison

- Added `backtester compare-fixed`, a fixed-candidate comparison CLI that runs
  bounded H1 windows and exports `windows.csv`, `windows.md`, and donor
  per-window run artifacts.
- Added tests for window parsing and fixed-candidate summary aggregation.
- Ran candidate A (`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`) across SOL
  January/February/March 2025 and TON January/February 2025 at
  `/tmp/crypt_fixed_candidate_h1/20260603_134312`.
- Bounded result: positive on SOL January `+1.99%`, SOL February `+13.82%`,
  TON January `+1.19%`, and TON February `+2.76%`; failed SOL March at
  `-6.52%`.
- Recorded candidate A as worth a long owner-run diagnostic, not accepted
  calibration, and documented the full-history SOL/TON owner-run command.

**ADRs:** none.

**Verification:** ruff check and format clean on the changed CLI/report/test
paths; targeted donor pytest `2 passed`; bounded `compare-fixed` run completed
and exported artifacts.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-03 — Urgent profitability sprint handoff

- Recorded owner direction for the next 2-3 Codex sessions: prioritize a
  bounded profitable candidate and an owner-run long backtest command over
  broad architecture work.
- Added a top `IN_PROGRESS.md` handoff with the next-session order: fixed
  `rrr = 1.25` / `ttl = 36` comparisons, tiny execution-only grid only if
  needed, side-skew attribution, and a final unattended local run command.
- Added P0 backlog items for fixed-candidate H1 window comparison, candidate
  selection, minimal side-skew attribution, and owner-run long backtest
  preparation.
- Documented the 2026-06-03 full-history SOL H1 curiosity Optuna run as too
  expensive for remaining Codex time: trial 0 took about 1h48m and returned
  `total_return_pct = -9.47`, `max_drawdown = -24.75`, `total_trades = 482`.

**ADRs:** none.

**Verification:** documentation-only handoff; no code or tests changed.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Adjacent H1 optimizer diagnostics

- Inspected the SOL January H1 optimizer best-run artifacts and confirmed the
  `+2.46%` result is mixed-side and fragile: longs contributed `+304.88`,
  shorts `-58.48`.
- Ran the same bounded execution-only optimizer search on adjacent SOL
  February 2025 at
  `/tmp/crypt_donor_h1_mtf_optuna_sol_feb/20260603_104255`: best trial
  `rrr = 1.25`, `position_ttl_bars = 36`, `total_return_pct = 13.82`,
  `profit_factor = 5.40`, max drawdown `-1.90`, 53 short-only trades.
- Ran the same bounded search on TON January 2025 at
  `/tmp/crypt_donor_h1_mtf_optuna_ton_jan/20260603_104642`: best trial
  `rrr = 1.50`, `position_ttl_bars = 36`, `total_return_pct = 1.95`,
  `profit_factor = 1.12`, max drawdown `-5.51`, 86 short-only trades.
- Recorded that XPL was intentionally skipped for this pass because its H1
  history is shorter.
- Kept H1 setup geometry in diagnostic status; broader out-of-sample windows
  and fixed-candidate comparisons are required before strategy-param search.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor code/test paths;
targeted donor pytest `29 passed`; full donor pytest `102 passed` with 2
existing pandas warnings; SOL February and TON January bounded optimizer CLI
diagnostics completed and exported `best_run/` artifacts.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Operator-facing H1 optimizer CLI

- Added `backtester optimize`, a CLI wrapper around the existing donor
  `ParameterOptimizer` for bounded `crypt_ensemble` H1 tuning.
- The command loads bounded `crypt-parquet`, preserves strategy JSON params,
  exposes execution/risk search ranges, writes `trials.csv`,
  `best_trial.json`, the Optuna journal log, and donor `best_run/`
  diagnostics.
- Fixed fixed-risk handling in `ParameterOptimizer`; `risk_percent_range =
  None` now uses the configured fixed `risk_percent`.
- Added cached best-signal reuse for `best_run/` export so execution-only
  optimizer runs do not rerun `crypt_ensemble.generate()` after Optuna.
- Ran a bounded SOL H1 12-trial optimizer diagnostic at
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`: best tiny in-sample
  result was `rrr = 1.25`, `position_ttl_bars = 30`,
  `total_return_pct = 2.46`, `profit_factor = 1.14`, max drawdown `-5.7`,
  97 trades. This is diagnostic only, not accepted calibration.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/optimizer/test
files; targeted donor pytest `3 passed`; full donor pytest `102 passed` with 2
existing pandas warnings; bounded SOL H1 optimizer CLI diagnostic completed;
short cache smoke confirmed `best_run/` export does not show a second
`crypt_ensemble` progress build.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-03 — H1 optimizer speed path

- Extended the existing donor `ParameterOptimizer` instead of adding a second
  optimizer: baseline `strategy_params`, configurable `rrr` range/step,
  Optuna-controlled `position_ttl_bars`, preserved `risk_base_period`,
  optional daily/trading-window search, and optional strategy-param search.
- Added signal-frame caching inside `ParameterOptimizer`; execution-only
  `rrr`/`ttl` trials reuse the same generated `crypt_ensemble` signals.
- Added ADR-0022 and implemented H4 setup snapshots in H1 MTF mode. H4 setup
  verdicts are evaluated at the latest closed H4 setup time and reused across
  H1 trigger bars until the next H4 close.
- Added tests for setup snapshot invalidation and optimizer signal-cache reuse.
- Ran bounded SOL H1 Optuna speed check at
  `/tmp/crypt_donor_h1_mtf_optuna_speed_check`: first 745-bar signal build
  took about 226.9 seconds; the next two `rrr`/`ttl` trials completed in about
  0.05 seconds each from cache. Tiny diagnostic best was `rrr = 1.75`,
  `position_ttl_bars = 30`, `total_return_pct = 0.18`.

**ADRs:** 0022 (accepted).

**Verification:** ruff check and format clean on changed donor optimizer,
strategy, and tests; targeted donor pytest `28 passed`; full donor pytest
`101 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Parity-safe H1 window cache

- Documented the `crypt_ensemble` performance optimization contract before
  code changes: reference path must remain available, and optimized paths must
  pass reference-vs-optimized parity before tuning.
- Added `optimized_windows` to donor `crypt_ensemble`. Default remains
  `false`; the H1 diagnostic strategy config opts in.
- Implemented a closed-window context cache for candle/extras selection only,
  preserving closed-candle and timestamp bounds without caching verdicts, SMC
  states, trigger decisions, or stops across bars.
- Added parity tests for cached context windows and H1 MTF strategy output
  across signal, stop, trigger, rationale, metadata, and strength columns.
- Reran bounded SOL H1 MTF smoke with optimized windows at
  `/tmp/crypt_donor_h1_mtf_smoke_optimized_windows/20260603_083245`: 745 H1
  bars, 98 trades, final capital 9947.0, `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`.
- Runtime improved from about 6 minutes 35 seconds to about 5 minutes
  3 seconds on the bounded January SOL slice. Further speedups remain behind a
  separate parity contract for verdict/SMC/event-age caching.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `25 passed`; full donor pytest `98 passed` with
3 existing pandas warnings; bounded optimized SOL H1 smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — H1 stop-distance cap diagnostic

- Added `max_sl_distance_atr` as an explicit donor `crypt_ensemble` strategy
  parameter with the existing `8 ATR` guard preserved as the default.
- Exposed `max_sl_distance_atr` through `suggest_params()` for future donor
  Optuna work.
- Set `max_sl_distance_atr = 4.0` in the H1 diagnostic strategy config.
- Added a focused unit test for neutralizing a structurally valid stop that is
  wider than an explicit cap.
- Updated README, MTF spec, and task tracking with the stop-distance cap
  contract.
- Reran bounded SOL H1 MTF smoke at
  `/tmp/crypt_donor_h1_mtf_smoke_h1_max4/20260602_195943`: 745 H1 signal rows,
  105 tradeable signals, 98 trades, final capital 9947.0,
  `total_return_pct = -0.53`, `profit_factor = 0.97`, max drawdown `-7.41`.
- Compared with the previous H1 stop-source smoke: TTL exits fell from 50.0%
  to 37.8%, and trade frequency fell from 6.27 to 3.89 trades/day. This is
  still a bounded SOL diagnostic, not full-history H1 acceptance.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `23 passed`; full donor pytest `96 passed` with
3 existing pandas warnings; bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — H1 structural stop-source selection

- Updated the MTF strategy spec with the H1-vs-H4 structural stop-source
  contract.
- Implemented H1 stop-source selection in donor `crypt_ensemble`: H4 remains
  the primary setup stop, while H1 execution mode can replace it with a valid,
  known, same-direction H1 structural stop only when it is closer by execution
  ATR distance.
- Added tests for using a closer H1 stop and keeping H4 when the H1 candidate
  is wider.
- Reran bounded SOL H1 MTF smoke at
  `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`: 745 H1
  signal rows, 159 tradeable signals, 153 tradeable signals with
  `sl_source_tf = 1h`, 158 trades, final capital 9058.19,
  `total_return_pct = -9.42`, `profit_factor = 0.66`, max drawdown `-10.44`.
- H1 stop-source diagnostics are now contract-visible, but the result is still
  diagnostic only: trade frequency rose to 6.27 trades/day and setup geometry
  plus performance remain open before full-history H1 acceptance.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `22 passed`; full donor pytest `95 passed` with
3 existing pandas warnings; bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — MTF no-lookahead entry timing

- Added donor `crypt_ensemble` tests for D1 forming-candle exclusion,
  future-known H4 structural stop-anchor rejection, and H1 signal timing
  through `ExecutionSim`.
- Fixed donor `crypt_ensemble` to leave `entry_price` empty so execution
  enters at the next execution-bar open after a closed signal candle, instead
  of using the signal candle close as a current-bar custom entry.
- Updated README, MTF spec, and task tracking with the next-open entry
  contract.
- Reran bounded SOL H1 MTF smoke after the fix at
  `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`: 745 H1
  signal rows, 35 short trades, final capital 9357.25 from 10000,
  `total_return_pct = -6.43`, `profit_factor = 0.04`, max drawdown `-6.27`.
- Sample trades confirm next-open execution: first `signal_time` is
  `2025-01-03 13:00:00+00:00`, first `entry_time` is
  `2025-01-03 14:00:00+00:00`.
- H1 stop-source acceptance remains open: all 35 trades still used H4
  order-block stops.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `20 passed`; full donor pytest `93 passed`; full
suite still has 3 existing pandas warnings. Bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt-parquet` bounded smoke range

- Added inclusive `--from` / `--to` options to the donor `backtester run` CLI
  for `crypt-parquet` data.
- `CryptParquetDataLoader` now parses date bounds as UTC, limits
  `StrategyData.primary`/output rows by the requested range, and preserves
  pre-start candle history in `StrategyData.candles` up to `--to` for H4/D1
  warmup.
- Added tests for CLI propagation, inclusive primary filtering, and context
  warmup retention.
- Updated README, MTF smoke spec, and task tracking with the bounded H1 smoke
  command.
- Reran bounded SOL H1 MTF smoke locally after owner restored Parquet data:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded/20260602_191541`.
- Smoke produced 745 H1 signal rows, 35 short trades, final capital 9340.69
  from 10000, `total_return_pct = -6.59`, `profit_factor = 0.05`, max drawdown
  `-6.45`, and full signal/trade diagnostics. This is diagnostic only; full
  H1 acceptance remains open behind no-lookahead expansion, H1 stop-source
  behavior, setup geometry, and performance profiling.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`26 passed`; full donor pytest `90 passed`; both with 3 existing pandas
warnings. Bounded SOL H1 smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Vend `backtester/` into crypt monorepo (docs)

- Owner decision: fold the donor package into the `crypt` git repository
  instead of keeping a nested `backtester/.git` or submodule.
- Added ADR-0021 with one-time migration steps (`rm -rf backtester/.git`,
  root `git add backtester/`, gitlink cleanup).
- Updated `README.md` layout, `docs/backtest.md`, `docs/backtester_migration.md`,
  and ADR-0018 cross-references.
- Recorded follow-up: root CI does not yet run donor `pytest` (BACKLOG P2).

**ADRs:** 0021 (accepted).

**Verification:** docs-only; no tests run. Owner still removes `backtester/.git`
and commits the tree from the `crypt` root.

**Files touched:** `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — First MTF `crypt_ensemble` implementation slice

- Added donor `crypt-parquet` `primary_timeframe` support and CLI
  `--primary-timeframe`, preserving H4 as the default primary frame.
- Added timeframe-role config to `crypt_ensemble` (`context`, `setup`,
  `trigger`, `execution`) and a first H1 MTF path: D1 context filter, H4 setup
  verdict, H1 candle-confirm trigger/execution, and MTF diagnostics.
- Added `backtester/strategies/crypt_ensemble_h1.json` with H1 execution,
  `ttl = 24`, `rrr = 1.5`, and monthly risk base.
- Added tests for H1 primary loader semantics, CLI propagation, H1 execution
  index/diagnostics, H4 forming-candle exclusion, and D1 opposite-context
  blocking.
- Attempted the SOL H1 MTF smoke; it loaded 21517 H1 bars and started replay,
  but ended before export and produced no artifact. Full H1 smoke remains open
  behind a range limiter or performance pass.
- Updated README, migration docs, MTF spec, and task tracking.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`41 passed`; full donor pytest `88 passed`, both with 3 existing pandas
warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Unified MTF `crypt_ensemble` handoff

- Added `docs/crypt_ensemble_mtf.md` as the next implementation spec for a
  generic multi-timeframe strategy contract.
- Captured the owner-requested top-down model: D1 context, H4 setup, H1
  trigger/execution.
- Required extensibility for future 15m triggers through timeframe-role config
  (`context`, `setup`, `trigger`, `execution`) instead of special-case H1 code.
- Documented no-lookahead rules, data contract changes, first H1 slice,
  diagnostics, required tests, smoke command, and future 15m path.
- Updated task tracking so the next agent starts from the MTF spec.

**ADRs:** none.

**Verification:** docs-only; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor TTL exit diagnostics

- Added `trade_diagnostics.csv` export to donor `ResultsAnalyzer` for runs
  with trades: exit reasons, side/exit counts, PnL by side/reason, holding
  duration, trades per day, `sl_distance_atr` by exit reason, and anchor
  distance by stop type.
- Generated the diagnostic report for the existing structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827/trade_diagnostics.csv`.
- Diagnosed TTL-heavy exits as setup geometry rather than an execution bug:
  1496/1672 trades (`89.47%`) closed by `ttl_expired`; `ttl = 6` H4 bars is a
  24-hour window, while TTL-expired trades had median `sl_distance_atr = 3.985`,
  making the `rrr = 2` TP roughly 8 ATR away.
- Checked lower-timeframe feasibility: SOL and TON have long H1 Parquet
  history, but the strategy/engine contracts are H4-semantic and need a
  separate H1 spec/ADR before code changes.
- Updated README, migration docs, and task tracking with the new artifact and
  next steps.

**ADRs:** none.

**Verification:** ruff clean on changed analyzer/test files; targeted donor
pytest `6 passed`.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Structural SMC stop-loss for donor `crypt_ensemble`

- Replaced the donor `crypt_ensemble` default ATR-only stop with a structural
  SMC stop hierarchy: active order block, fresh liquidity sweep, confirmed
  pivot, then optional explicit ATR fallback.
- Added `sl_atr_buffer_mult` and `allow_atr_sl_fallback`; the default strategy
  JSON disables ATR fallback and neutralizes BUY/SELL verdicts without a valid
  structural stop.
- Added stop diagnostics to strategy output: `sl_anchor_type`,
  `sl_anchor_level`, `sl_anchor_known_at`, and `sl_distance_atr`.
- Added synthetic tests for long/short OB stops, sweep stops, pivot fallback,
  excessive-distance/no-anchor neutralization, and no-lookahead anchor timing.
- Reviewed owner-completed structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827`: 1672 trades,
  final capital 6683.68, `total_return_pct = -33.16`, `profit_factor = 0.84`,
  max drawdown `-35.38`. Structural SL removed 120 trades versus the previous
  no-structural smoke but did not improve aggregate metrics; long-side trades
  remain the main drag.
- Updated README, structural SL spec, migration docs, and task tracking. Next
  step is either focused order-block stop-quality analysis or minimal donor
  Optuna with out-of-sample caution.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`14 passed`; full donor pytest `82 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Structural SL handoff before donor optimizer

- Removed the newly added donor walk-forward optimizer code, CLI command, and
  tests; `folds` is not part of the first donor optimizer step.
- Restored donor `crypt_ensemble` optimizer surface to the existing
  `sl_atr_mult` and `min_confidence` suggestions; weight optimization remains
  a future task after structural stop-loss.
- Added `docs/crypt_ensemble_structural_sl.md`: structural stop-loss spec
  using SMC order blocks, liquidity sweeps, pivots, and ATR buffer.
- Added explicit donor safety rule: `backtester/` is high-risk source-of-truth
  code; prefer adapting `crypt_ensemble` over rewriting donor internals.
- Updated task tracking so structural SL is the next P0 before optimizer or
  backtest interpretation.

**ADRs:** none.

**Verification:** changed-file ruff clean. Targeted donor pytest should be
rerun after structural SL implementation.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — ADR-0020 removes donor default confidence gate

- Recorded the owner correction in ADR-0020: `ALERT_CONFIDENCE_THRESHOLD = 75`
  was arbitrary and must not be rationalized as a calibrated threshold.
- Removed default `min_confidence = 75` from donor `crypt_ensemble`; BUY/SELL
  verdicts are tradeable by default, while explicit `min_confidence` remains
  available for diagnostics or Optuna.
- Replaced the hard-coded `confidence_ge_75` signal diagnostic with confidence
  quantiles.
- Reviewed owner-provided SOL smoke at `/tmp/crypt_donor_smoke/20260602_132627`:
  1792 trades, final capital 6694.69, `total_return_pct = -33.05`,
  `profit_factor = 0.88`; long-side performance remains the main issue.
- Updated task handoff so the next step is donor Optuna, not further
  investigation of the number `75`.

**ADRs:** ADR-0020; ADR-0011 status updated.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`12 passed`; full donor pytest `75 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Threshold-correct donor smoke produced no live-threshold trades

- Added donor no-trade diagnostics: `signals.csv`, `signal_diagnostics.csv`,
  and non-empty `metrics.csv` now export even when no trades are opened.
- Reran SOL donor smoke with `min_confidence = 75` at
  `/tmp/crypt_donor_smoke/20260602_122510`.
- Confirmed 0 trades is expected under current confidence semantics:
  1798 directional verdicts existed, but max confidence was 52 and no row
  reached the live alert threshold of 75.
- Added follow-ups to audit confidence scale vs live threshold and add a cheap
  signal diagnostics report before Optuna.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; full donor pytest
`74 passed` with 3 existing pandas warnings; SOL donor smoke completed in
about 15 minutes.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt_ensemble` confidence threshold

- Reviewed the owner-rerun monthly-risk SOL donor smoke at
  `/tmp/crypt_donor_smoke/20260602_104522`.
- Confirmed metadata export is present, but diagnosed the run as trading every
  directional verdict: all exported trades had `confidence <= 55`, below the
  live alert threshold of 75.
- Added `min_confidence` to `crypt_ensemble` params and Optuna suggestions.
  Default JSON value is `75`.
- Low-confidence BUY/SELL verdicts now preserve verdict metadata but emit
  donor `signal = 0`.

**ADRs:** none.

**Verification:** ruff clean on changed strategy/test files; targeted donor
pytest `6 passed` with one existing pandas warning.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor risk-base sizing and trade attribution export

- Reviewed the owner-completed SOL donor smoke and confirmed it was a plain
  `backtester run`, not an optimizer run.
- Recorded old-mode smoke metrics: 1792 trades, final capital 6548.74 from
  10000 initial capital, `total_return_pct = -34.51`, `profit_factor = 0.88`;
  long trades were materially negative while shorts were slightly positive.
- Fixed donor execution export so trade rows retain `crypt_ensemble`
  attribution metadata: `signal_time`, confidence, score, regime, decision,
  rationale, and per-engine strengths.
- Added `risk_base_period` sizing modes (`trade`, `weekly`, `monthly`,
  `backtest`) and exported `risk_base_capital` per trade.
- Set `crypt_ensemble` to monthly risk-base sizing for donor M2 smokes.

**ADRs:** ADR-0019.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`39 passed`; full donor pytest `71 passed` with existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt_ensemble` engine wiring

- Wired donor `crypt_ensemble` to run the existing volatility, regime,
  directional engines, and aggregator over `StrategyData`.
- Added closed-candle H4 replay semantics in the donor strategy: each row is
  evaluated at `open_time + 4h`, with H4/H1/D1 contexts filtered to closed
  candles only.
- Added donor output metadata: `entry_price`, ATR-based `sl_price`,
  confidence, score, regime, decision, rationale, and per-engine strengths.
- Added per-bar progress for long `crypt_ensemble` runs and enabled it in the
  strategy JSON.
- Fixed project-Parquet `open_time` ambiguity when it is both index name and
  column label.
- Added donor tests for BUY/SELL/HOLD mapping, ATR stop output, missing
  optional frames, and `open_time`-named indexes.

**ADRs:** ADR-0018.

**Verification:** `PYTHONPATH=src:../src uv run --extra dev pytest tests -q`
in `backtester/` → 67 passed; ruff clean on changed donor files. SOL
`crypt-parquet` smoke loaded 5545 H4 bars and showed progress, but the full
run was stopped before completion due duration.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor backtester Parquet loaders and neutral ensemble skeleton

- Added donor `StrategyData` and adapted `Backtester`/CLI plumbing so old
  strategies still receive `pd.DataFrame` while richer strategies can receive
  project-aware data.
- Added donor `parquet` and `crypt-parquet` data sources, including support
  for project-style `open_time` + `o/h/l/c/volume` Parquet files.
- Registered `crypt_ensemble` with a neutral/no-trade skeleton and strategy
  JSON config.
- Added donor tests for loader modes, CLI data-source selection, and the
  neutral `crypt_ensemble` skeleton.
- Updated README and migration/task docs with the experimental donor command.

**ADRs:** ADR-0018.

**Verification:** `PYTHONPATH=src:../src uv run --extra dev pytest tests -q`
in `backtester/` → 65 passed; ruff clean on changed donor files; SOL
`parquet` and `crypt-parquet` smoke commands loaded 5545 H4 bars and wrote
no-trades reports.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor backtester migration plan

Owner redirected M2 architecture toward the donor `backtester/` package:
minimal additive changes, keep Parquet, keep one symbol per run, register the
existing ensemble as a donor strategy, and defer deletion of
`src/crypt/backtest/` until a donor-backed smoke run works.

- Added ADR-0018 accepting donor backtester as the future canonical M2
  strategy/backtester architecture.
- Added `docs/backtester_migration.md` with the implementation handoff:
  `StrategyData`, `parquet`, `crypt-parquet`, `crypt_ensemble`, smoke test,
  and later Optuna phase.
- Updated task tracking with P0/P1 migration steps for the next agent.

**ADRs:** ADR-0018.

**Verification:** docs-only; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-01 — M2 report reviewed; OHLCV calibration rejected

Owner reran the SOL/TON OHLCV-only backtest after the multi-symbol execution
fix. The replay completed, but the optimizer sanity guard fired on the first
two out-of-sample folds, so generated weights are not promoted.

- Added ADR-0014 documenting the rejected calibration result and the decision
  to keep alerts marked uncalibrated.
- Fixed `weights_to_yaml()` so candidate files containing numpy scalar weights
  are emitted as safe, portable YAML instead of Python object tags.
- Added a regression test for safe YAML serialization.
- Added follow-ups for guarded-report artifact semantics and weak long-side
  signals.

**ADRs:** ADR-0014.

**Verification:** `uv run pytest -q` passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`,
`reports/backtest_2026-06/`.

---

## 2026-06-01 — Hotfix: multi-symbol backtest execution uses symbol-local next bars

Owner backtest log showed impossible SL validation lines where prices from
different instruments were paired (for example SOL entry levels with TON stop
prices). Root cause: `ExecutionSim` used the next global row in a combined
multi-symbol DataFrame for next-open entries and TTL exits.

- `ExecutionSim.run()` now computes `next_open`, `next_time`, and bar number
  per symbol before the simulation loop.
- Backtest simulation frames now include explicit `entry_price = close` from
  the closed signal candle.
- Cleaned up pandas `pct_change(fill_method=None)` and timezone-aware UTC
  generation timestamps for warnings seen in the same run.
- Added a regression test for same-timestamp SOL/TON rows.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 124 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`.

---

## 2026-06-01 — Backtest optimizer recomputes candidate scores

- Fixed M2 calibration blocker: `BacktestRecorder` now persists
  `strength_<engine>` columns for scoring engines.
- Updated `optimizer._apply_weights` to recompute score/decision from replayed
  strengths under candidate weights instead of reusing the old final `score`.
- Added focused tests proving candidate weights change score, decision, and
  objective.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 119 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`.

---

## 2026-06-01 — SMC liquidity engine

- Extended SMC core with `SMCLiquidityLevel`, `SMCLiquiditySweep`, ATR-scaled
  equal high/low detection, swing liquidity levels, wick-distance metadata,
  and same-candle ambiguity flags.
- Added `SMCLiquidityEngine`: reversal signal from fresh equal/swing high-low
  sweeps with rejection bonus and neutral missing-data/ambiguous paths.
- Wired `smc_liquidity` into live orchestration, replay, aggregator scoring,
  placeholder weights, optimizer engine lists, and backtest docs.
- Added tests for equal-level confirmation timing, sweep timing, ambiguous
  double sweeps, bullish/bearish liquidity output, and missing H4 data.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 116 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/runtime/`, `src/crypt/backtest/`, `src/crypt/aggregator/`,
`tests/`, `config/`, `docs/`.

---

## 2026-06-01 — SMC order-block engine

- Extended SMC core with `SMCOrderBlock`, order-block extraction from
  pivot-to-break structure windows, high-volatility candle parsing, and
  mitigation state.
- Added `SMCOrderBlocksEngine`: active zone retest signal with structure-bias
  confluence, rejection bonus, ATR width filter, and neutral missing-data path.
- Wired `smc_order_blocks` into live orchestration, replay, aggregator scoring,
  placeholder weights, and optimizer engine lists.
- Added tests for order-block creation, mitigation, retest signal, no retest
  before the closed candle, and missing H4 data.
- Added a P0 backlog item for optimizer score recomputation before trusting
  M2 calibration output.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 109 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/runtime/`, `src/crypt/backtest/`, `src/crypt/aggregator/`,
`tests/`, `config/`, `docs/`.

---

## 2026-06-01 — ADR-0017: OHLCV-only M2 + first SMC structure engine

Owner direction: stop blocking M2 on paid/short derivatives history and first
prove value with free OKX candles.

- Added ADR-0017: primary M2 calibration is OHLCV-only; `derivatives` weight
  is `0` until deep OI/LS history is separately proven.
- Added SMC specs: `smc_core`, `smc_structure`, `smc_order_blocks`,
  `smc_liquidity`.
- Implemented first SMC core slice in `src/crypt/structure/smc.py`:
  confirmed pivots + BOS/CHoCH with explicit `known_at` timing.
- Added `SMCStructureEngine` and wired it into live orchestration and replay.
- Updated `config/weights.yaml`, aggregator scoring engines, backtest
  preconditions, README/backfill/backtest docs for OHLCV-only M2.
- Added no-lookahead tests for SMC pivot/event timing and engine output.

**ADRs:** 0017.

**Verification:** `uv run pytest` → 103 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `docs/`, `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/aggregator/`, `src/crypt/backtest/`, `src/crypt/runtime/`,
`tests/`, `config/`, `README.md`.

---

## 2026-06-01 — Hotfix: OI endpoint parameter `instId` (not `ccy`)

OKX `/rubik/stat/contracts/open-interest-history` requires `instId`
(e.g. `SOL-USDT-SWAP`), not `ccy` (`SOL`). ADR-0016 had the wrong parameter.
Also switched stored field from `row[1]` (contracts) to `row[3]` (oiUsd) for
USD-denominated OI, consistent with the prior `openInterestValue` field.

- `src/crypt/exchange/okx.py` — `fetch_oi_history` and `fetch_oi_history_page`:
  `ccy=ccy` → `instId=symbol`, `row[1]` → `row[3]` (oiUsd).

Discovered on first live backfill run (error code `50014 instId can't be empty`).

---

## 2026-06-01 — ADR-0016 code implementation: drop funding, fix OI endpoint

Session 6. All code changes from ADR-0016 implemented; 97 tests pass,
mypy 0 errors, ruff clean.

### Code changes

- `src/crypt/exchange/okx.py` — `fetch_oi_history` and `fetch_oi_history_page`
  replaced `ccxt`'s `fetch_open_interest_history` (9-day history) with direct
  call to `publicGetRubikStatContractsOpenInterestHistory` (data to Feb 2024).
- `src/crypt/engines/derivatives.py` — `_funding_signal` removed; weights
  rebalanced to OI 0.67 / LS 0.33; graceful degradation reworked.
- `src/crypt/models.py` — `EvaluationContext.funding` field removed.
- `src/crypt/data/context.py` — `_FUNDING_LIMIT`, `_df_to_funding`, funding
  loading removed.
- `src/crypt/data/store.py` — `save_funding`, `load_funding`, `_funding_path`,
  `_FUNDING_COLS` removed.
- `src/crypt/data/ingestor.py` — `_ingest_funding` removed.
- `src/crypt/backfill/__main__.py` — `_backfill_funding`, `funding` data-type
  removed; default `--data-types` changed to `ohlcv,oi,ls_ratio`.
- `src/crypt/backtest/replay.py` — `load_funding`, `_FUNDING_LIMIT` removed;
  `ReplayContextBuilder` updated.
- `src/crypt/backtest/__main__.py` — funding precondition check removed;
  `_build_funding_model` simplified to always return `ZeroFundingModel`;
  `_FUNDING_WARMUP_DAYS` constant removed.
- `tests/engines/test_derivatives.py` — rewritten without funding fixtures;
  6 OI+LS-only tests.
- `tests/backtest/test_no_lookahead.py` — funding fixture and
  `test_funding_boundary_excluded` removed; OI guard test retained.
- `tests/decision/test_filters.py`, `tests/conftest.py` — `funding` arg
  removed from `make_ctx`; `FundingSnapshot` import removed.
- `.env.example` — Coinglass env vars replaced with tombstone comment.

### Docs (unchanged from session 5 — already updated by prior agent)

`docs/backfill.md`, `docs/engines/derivatives.md`, `docs/decisions/0016-*`.

---

## 2026-06-01 — Drop funding; fix OI endpoint; retire Coinglass plan (ADR-0016)

**Decisions made in owner-agent design session.**

### Funding sub-signal dropped from `DerivativesEngine`

OKX perpetual swap contracts run on 1 h / 2 h / 4 h / 8 h funding settlement
cycles (e.g. TON-USDT-SWAP moved to 4 h in April 2025). The engine's
`_FUNDING_LIMIT = 200` window assumed a fixed 8 h cycle; a 4 h contract
silently halves the effective z-score window, producing miscalibrated weights
with no error signal. OKX also retains only ~3 months of funding history —
insufficient for M2. The sub-signal is removed; `DerivativesEngine` now runs
on OI momentum (0.67) + L/S ratio (0.33).

### OI endpoint corrected

`ccxt`'s `fetch_open_interest_history` calls
`/rubik/stat/contracts/open-interest-volume` (only ~9 days of history).
The correct endpoint is `/rubik/stat/contracts/open-interest-history`, which
OKX retains to February 2024. `OKXClient.fetch_oi_history_page` must be
updated to call `publicGetRubikStatContractsOpenInterestHistory` directly.

### Coinglass plan retired (ADR-0015 superseded)

With funding dropped and OI/LS both available from OKX native deep endpoints,
no remaining data gap requires a third-party vendor. `CoinglassClient` was
never implemented; no rollback needed.

### Product vision clarified

Session discussion captured in `BACKLOG.md`:
- Output goal: BUY/SELL + entry price + SL (ATR-based) + TP (2:1 R:R fixed).
- New engine categories planned: structural (S/R, VWAP, Fibonacci), volume
  (CVD, OBV), price action (Order Blocks, FVG, BOS/ChoCH).
- Engine = "alpha factor / signal generator", not a complete strategy.

**ADRs:** 0016 (new). 0015 (superseded).

**Docs updated:**

- `docs/decisions/0016-drop-funding-fix-oi-endpoint.md` — new ADR (accepted).
- `docs/decisions/0015-coinglass-historical-backfill.md` — status → superseded.
- `docs/engines/derivatives.md` — spec updated (no-funding design, new weights).
- `docs/backfill.md` — Coinglass section removed; OI endpoint table updated.
- `docs/tasks/IN_PROGRESS.md` — next steps rewritten for OI fix + engine cleanup.
- `docs/tasks/BACKLOG.md` — Coinglass items removed; product vision + new engine
  categories added.

**Code not yet written.** Next agent implements changes in `IN_PROGRESS.md`.

---

## 2026-05-29 — Coinglass backfill: spec + ADR (implementation pending)

Owner approved Coinglass as a read-only backfill source for deep
derivatives history (funding, OI, LS ratio, taker volume) where OKX
Rubik endpoints retain only ~9–90 days.

**Docs added/updated:**

- `docs/backfill.md` — full backfill contract (OKX + Coinglass sources,
  CLI `--source`, endpoint mapping, tier limits, M2 workflow).
- `docs/decisions/0015-coinglass-historical-backfill.md` — ADR (accepted).
- `docs/backtest.md` §14, §16 — cross-refs and provenance note.
- `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — implementation
  checklist.

**Code not yet written.** Next agent implements `CoinglassClient` and
`--source coinglass|auto` per `docs/backfill.md` §8.

**ADRs:** 0015.

---

## 2026-05-29 — Backfill: fix OKX history-wall performance bug

**Problem:** Running `python -m crypt.backfill --from 2024-01-01` for
ls_ratio / taker_vol / OI triggered OKX error `50030 "Illegal time range"`
for every historical window (OKX Rubik endpoints keep only ~30 days of
ls_ratio/taker_vol, ~9 days of OI, ~90 days of funding). Each failed window
was retried 5× with exponential backoff (~27 s/window), making the full
ls_ratio pass take an estimated ~150 hours for a 2-year range.

**Fixes:**

- `src/crypt/utils/retry.py` — added `no_retry_on` predicate parameter.
  When the predicate returns True the exception is re-raised immediately
  (no sleep). Permanent errors like `50030` should never consume backoff.
- `src/crypt/exchange/okx.py` — added `_is_okx_history_limit` predicate
  (matches `50030` in error string); wired into `fetch_oi_history_page`,
  `fetch_ls_ratio_range`, `fetch_taker_volume_range`.
- `src/crypt/backfill/__main__.py` — `_backfill_oi` and `_backfill_rubik`
  now track consecutive zero-data windows. After `_MAX_CONSECUTIVE_EMPTY=3`
  consecutive empties the cursor jumps forward `_HISTORY_SKIP_MS=90 days`,
  quickly landing on the edge of available OKX history instead of grinding
  through the full date range.

**Note on data availability:** OHLCV goes back 2+ years on OKX. All other
endpoints have hard limits imposed by OKX; no amount of retrying will
recover older data. What can be backfilled today per endpoint:
- funding: ~90 days
- ls_ratio / taker_vol: ~31 days
- OI: ~9 days

**Re-run guidance:** re-running is idempotent (ParquetStore upserts). To
skip already-fetched types use `--data-types oi,ls_ratio` etc.

---

## 2026-05-29 — M2 backtest harness: full pipeline steps 4–11

Completed the M2 backtest harness. All pipeline components are implemented,
typed, tested (97 tests, 0 mypy errors, ruff clean).

### New modules

- `src/crypt/backtest/labels.py` — forward-label loader (§6). Computes
  `return_h4/h24/h96`, `mae`, `mfe`, `hit_h4/h24/h96` for each verdict.
  Uses pandas Series reindex with UTC-aware DatetimeIndex.
- `src/crypt/backtest/metrics.py` — metrics engine adapted from
  `backtester/src/backtester/results_analyzer.py` with all §18.4 fixes:
  - `build_equity_curve`: removed `drop_duplicates(subset="exit_time")`; sorted by
    `(exit_time, entry_time)` to handle multi-symbol same-tick exits.
  - `compute_sharpe_ratio`: warning emitted when n_monthly_samples < 6;
    trade-level Sharpe added as complement.
  - `compute_bootstrap_ci`: 95% CI for any scalar metric (1000 resamples).
  - `compute_buy_and_hold`, `compute_random_direction_baseline`: baselines (§11).
  - `generate_metrics`: full metrics dict including hit rates and bootstrap CI.
- `src/crypt/backtest/walkforward.py` — expanding-window walk-forward CV (§8).
  `FoldSpec`, `generate_folds`, `slice_verdicts`, `slice_trades`. Hard guarantee:
  no test-slice timestamp ever in the train slice.
- `src/crypt/backtest/optimizer.py` — weight optimiser (§9). Grid search over
  weight triples × threshold grid (all regimes). Coordinate descent refinement.
  Objective: `mean(pnl_net) - 0.5*std(pnl_net)`. Sanity guards (§9.4).
  `aggregate_weights_across_folds`: median weights + max thresholds (§13).
- `src/crypt/backtest/report.py` — static HTML report generator (§12). Embeds
  matplotlib equity curves, monthly-return bar charts, metrics tables, exit
  distribution, long/short breakdown, baselines, weights YAML. No server needed.
- `src/crypt/backtest/__main__.py` — full CLI entry point (§3, §5). Implements:
  data precondition checks (§4), H4 replay loop with `ReplayContextBuilder`,
  forward labels, `ExecutionSim` wiring with per-symbol `ParquetFundingModel`,
  walk-forward folds, weight optimisation, HTML report generation.

### Tests

- `tests/backtest/test_labels.py` — 8 tests: label computation, monotone-up
  price hit rate, HOLD→NaN hits, drop-tail behaviour, incomplete-window drop,
  MAE/MFE direction.
- `tests/backtest/test_walkforward.py` — 8 tests: fold count, no-overlap
  guarantee, expanding train window, regression test on synthetic 1-year dataset.
- `tests/backtest/test_metrics.py` — 12 tests: basic metrics, equity-curve
  §18.4 fix (duplicate exit_time), Sharpe warning, bootstrap CI, buy-and-hold,
  generate_metrics integration.

### Dependencies

- `matplotlib>=3.8` added to runtime deps (for HTML report charts).

Stats: 97 tests (was 67); mypy 0 errors (12 backtest files); ruff clean.

ADRs introduced: none (implementation follows previously-decided contracts).

---

## 2026-05-29 — M2 backtest harness: backfill CLI + replay core (steps 1–3)

Implemented the first three steps of the M2 backtest harness spec
(`docs/backtest.md`). All new code passes mypy strict (43 files, 0 errors),
ruff clean, and 67/67 tests.

### New modules

- `src/crypt/backfill/__init__.py`, `__main__.py` — OKX backfill CLI.
  Supports OHLCV, funding, OI, LS ratio, taker volume. Paginated, resume-safe,
  rate-limited, tqdm progress. Usage:
  `uv run python -m crypt.backfill --symbol SOL-USDT-SWAP --from 2023-01-01 --to 2026-05-01`
- `src/crypt/backtest/replay.py` — `ReplayParquetStore` (time-fence at
  `tick_time`) and `ReplayContextBuilder` (drop-in for live `ContextBuilder`).
- `src/crypt/backtest/fee_model.py` — ported `FeeModel` / `StaticPercentFeeModel`
  (maker/taker asymmetry: TP exits use maker fee, SL/TTL use taker fee).
- `src/crypt/backtest/risk_model.py` — ported `RiskModel` / `BasicRiskModel`
  (ATR-distance position sizer).
- `src/crypt/backtest/execution_sim.py` — ported `ExecutionSim` with all §18.4 fixes:
  - 🔴 `FundingRateModel` interface + `ZeroFundingModel` + `ParquetFundingModel`
    (charges `position_value * rate * 0.5` per H4 bar).
  - 🔴 Multi-symbol capital pool: single sim instance, `symbol` column in df,
    positions per symbol, shared capital.
  - 🟡 SL gap-adjusted fill: `exit_price = min/max(sl_price, bar_open)` for gaps;
    `--sl-pessimism-pct` flag.
  - 🟡 `exit_time` off-by-one fixed: TP/SL use `bar_time`, TTL uses `next_time`.
- `src/crypt/backtest/recorder.py` — `BacktestRecorder` (verdict → Parquet sink).
- `src/crypt/backtest/__init__.py` — module-level exports.

### Modified

- `src/crypt/exchange/okx.py` — pagination methods: `fetch_ohlcv_page`,
  `fetch_funding_history_page`, `fetch_oi_history_page`, `fetch_ls_ratio_range`,
  `fetch_taker_volume_range`; `fetch_ohlcv` gains optional `since_ms` param.
- `pyproject.toml` — `tqdm>=4.66` runtime dep; `tqdm.*` mypy override.

### Tests

- `tests/backtest/__init__.py` — new package init.
- `tests/backtest/test_no_lookahead.py` — 8 tests for look-ahead guard
  (guard excludes future data; naïve builder leaks it — proof test is valid).

Stats: 67 tests (was 59); mypy 0 errors (43 files); ruff clean.

ADRs introduced: none.

---

## 2026-05-29 — Post-M1 run: P0 quality gates, post-mortem, stdlib name fix

M1 14-day run completed successfully (255 verdicts, 0 errors, 0 alerts). All P0
post-run work shipped in this session.

### Post-mortem

- `docs/post_mortems/2026-05-29-m1-run-summary.md` — full 14-day run analysis:
  tick completeness, decision distribution, regime breakdown, key observations
  (zero alerts, TON BUY streak at conf 50%, XPL bootstrapping behaviour).

### P0 quality gates (all 5 shipped)

- **GitHub Actions CI** — `.github/workflows/ci.yml`: ruff lint, ruff format,
  mypy strict, pytest, uv lock check, gitleaks secret scan.
- **Pre-commit hooks** — `.pre-commit-config.yaml`: ruff (with auto-fix) +
  mypy. README "Developer setup" section added.
- **`[UNCALIBRATED]` marker** — `Settings.uncalibrated: bool = True` added to
  `config.py`; `TelegramSink._format_message` now appends `⚠️ [UNCALIBRATED]`
  to the alert title when flag is True; wired through `Orchestrator._build_sinks`.
  Unit tests in `tests/sinks/test_telegram.py` (8 tests).
- **Closed-candle invariant** — `OKXClient.fetch_ohlcv` now uses time-based
  `closed` determination (bar_close + 5s safety buffer). `Ingestor._ingest_ohlcv`
  pre-filters to closed candles before `save_candles`. `ParquetStore.save_candles`
  raises `ValueError` on any non-closed candle. Tests in
  `tests/data/test_store_closed_invariant.py` (4 tests).
- **Critical-inputs guard refactor** — `Signal.critical_missing: list[str]`
  field added. `BaseEngine.critical_inputs: ClassVar[list[str]] = []` declared;
  TrendEngine, MeanRevEngine, VolatilityEngine, RegimeEngine declare
  `critical_inputs = ["candles[H4]"]`; DerivativesEngine keeps `[]`.
  `DecisionFilter._has_critical_missing` now reads `sig.critical_missing`
  instead of substring-matching `"candles[H4]"` in `inputs_missing`. New tests
  in `tests/decision/test_filters.py` (+5 tests).

### `crypt` stdlib name conflict fix (ADR-0013)

- `pyproject.toml` — `[tool.pytest.ini_options]` gets `pythonpath = ["src"]`;
  `uv run pytest` now works out of the box without `PYTHONPATH=src`.
- `docs/decisions/0013-crypt-stdlib-name-conflict.md` — ADR documenting root
  cause, fixes applied, agent instructions, what was deliberately NOT done.
- `docs/deploy/railway.md` — troubleshooting table updated with ADR-0013 link.

### Stats

- Tests: 59 passed (was 42); mypy 0 errors (36 files); ruff clean.
- New files: 8 (`ci.yml`, `.pre-commit-config.yaml`, post-mortem, ADR-0013,
  `test_telegram.py`, `test_store_closed_invariant.py`, `tests/sinks/__init__.py`,
  `tests/data/__init__.py`).
- Modified files: `config.py`, `sinks/telegram.py`, `runtime/orchestrator.py`,
  `exchange/okx.py`, `data/store.py`, `data/ingestor.py`, `models.py`,
  `engines/base.py`, `engines/trend.py`, `engines/meanrev.py`,
  `engines/volatility.py`, `engines/regime.py`, `decision/filters.py`,
  `pyproject.toml`, `README.md`, `docs/deploy/railway.md`,
  `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md`, `docs/tasks/DONE.md`.

ADRs introduced: 0013.

---

## 2026-05-29 — Fix Railway data export docs (`railway run` vs `railway ssh`)

`railway run` runs commands locally with injected env vars; `/app/data` exists only
inside the deployed container where the volume is mounted. Step 7 in the deploy guide
incorrectly used `railway run`, causing `find: '/app/data': No such file or directory`.

- `docs/deploy/railway.md` — Step 7 now uses `railway ssh`; added prerequisites,
  extract commands, and troubleshooting rows.
- `docs/operator.md`, `docs/decisions/0010-railway-deployment.md` — aligned references.

---

## 2026-05-15 — Planning session: post-M1 docs / specs / backlog refresh

Pure documentation session. **No code changes.** The M1 14-day Railway
run is in progress; pushes to `master` would trigger a redeploy and
downtime (ADR-0010), so all work landed under `docs/` only.

Owner asked the agent to brainstorm and document what else can land
during and after the 14-day window, with extra detail so future agents
can implement without re-deriving the design.

### New documents

- `docs/backtest.md` — full M2 harness spec (CLI, data preconditions,
  no-look-ahead guard, walk-forward CV, weight optimiser with sanity
  guards, bootstrap CI, baseline comparisons, HTML report, backfill
  CLI, tests).
- `docs/paper_trading.md` — full M3 spec (ledger schema, entry / exit
  logic, SL/TP via ATR, restart recovery, P&L attribution, calibration
  curve, owner ledger via Telegram commands, tests).
- `docs/operator.md` — owner-facing runbook (anatomy of an alert,
  red / green flags, post-calibration recipe, escalation).
- `docs/operations/telegram_commands.md` — `/status`, `/last`,
  `/explain`, `/health`, `/threshold`, `/pause`, `/trade`, etc.
- `docs/operations/observability.md` — per-tick metrics jsonl,
  error-to-Telegram webhook, engine telemetry log lines, OKX
  instrumentation, heartbeat enrichment.
- `docs/operations/ci.md` — GitHub Actions workflow, branch
  protection, pre-commit hooks.
- `docs/post_mortems/_template.md` — incident post-mortem template.
- `docs/post_m1_code_fixes.md` — 8 latent issues to address after the
  run (closed-flag invariant, critical-inputs guard, anti-flip-flop,
  produced_at semantics, confidence-scale mismatch, XPL warm-up,
  multiplier cap, `InputKey` enum).

### New engine specs (no code yet — implement post-M2)

- `docs/engines/sentiment.md` — CryptoPanic-backed (background polling,
  graceful degrade, vote-weight calibration in M2).
- `docs/engines/liquidations.md` — three implementation paths; default
  Path B (Coinglass).
- `docs/engines/btc_context.md` — BTC-as-leader alignment multiplier +
  crisis filter; not part of weighted-sum score.
- `docs/engines/calendar.md` — `config/events.yaml` manual schedule;
  pre- and post-event confidence suppression curve.
- `docs/engines/cross_symbol_confluence.md` — meta-engine, runs in
  aggregator layer.

### New ADRs

- `0011-thresholds-rationale-and-uncalibrated-marker.md` — explains why
  the current threshold values are placeholders and mandates an
  `[UNCALIBRATED]` tag on Telegram alerts until M2 calibration.
- `0012-liquidations-roadmap.md` — complements (does not supersede)
  ADR-0006; promotes liquidation engine to BACKLOG P1 post-M2 with
  three implementation paths. ADR-0006 status line updated to point
  here.

### Task tracking

- `docs/tasks/BACKLOG.md` — full rewrite with P0/P1/P2 sections
  cross-referencing all new specs. M2 (backtest) decomposed from 3
  bullets into 12; M3 decomposed; new engines sequenced; operability
  and observability tracks added.
- `docs/tasks/IN_PROGRESS.md` — explicit next-steps block for the agent
  picking up after the 14-day run, ordered: extract data → write
  post-mortem → P0 quality gates → M2 starting with the no-look-ahead
  test.

ADRs introduced: 0011, 0012. ADR-0006 annotated.

Files touched (directory level): `docs/`, `docs/engines/`,
`docs/decisions/`, `docs/operations/`, `docs/post_mortems/`,
`docs/tasks/`.

No `src/` or `tests/` changes. No `pyproject.toml` / `uv.lock` changes.

---

## 2026-05-15 — Fix: all log levels tagged `[err]` in Railway

**Root cause:** Loguru writes all levels to `sys.stderr` by default. Railway
labels every byte from stderr as `[err]`, regardless of log level.

**Fix:** Split the console sink in `_configure_logging`:
- `DEBUG` / `INFO` → `sys.stdout` (Railway: `[inf]`)
- `WARNING` and above → `sys.stderr` (Railway: `[err]`, correct)

File log (`crypt.log`) unchanged — still receives all levels.

Files touched: `src/crypt/__main__.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: aiogram 3.7.0 broke `Bot` initializer (`parse_mode` removed)

**Root cause:** aiogram 3.7.0 removed `parse_mode`, `disable_web_page_preview`,
and `protect_content` from the `Bot.__init__` signature. Passing `parse_mode`
directly raised `TypeError` on every startup, crashing the process in a
Railway crash-loop.

**Fix:** Replaced `Bot(token=..., parse_mode=ParseMode.HTML)` with
`Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`
as required by aiogram ≥ 3.7.0.

Files touched: `src/crypt/sinks/telegram.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `SettingsError` on Railway when `SYMBOLS` env var is empty

**Root cause:** pydantic-settings v2 tries `json.loads()` on every `list[str]`
field before calling `field_validator`. `SYMBOLS=` (empty string) → empty
`json.loads("")` → `JSONDecodeError` → process crash.

**Fix:**
- Added `enable_decoding=False` to `SettingsConfigDict`: pydantic-settings now
  passes the raw string to the `field_validator` instead of trying JSON first.
- Updated `_parse_symbols` validator to fall back to `_DEFAULT_SYMBOLS` when
  the env var is empty/blank.
- Added troubleshooting row to `docs/deploy/railway.md`.

Files touched: `src/crypt/config.py`, `docs/deploy/railway.md`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `ModuleNotFoundError: No module named 'crypt.data'` on Railway

**Root cause:** `.gitignore` contained `data/` (no leading slash), which matched any
directory named `data` anywhere in the tree — including `src/crypt/data/`.
Railway builds from the git repo, so the entire Python package `crypt.data`
(context, ingestor, store) was absent from the container.

**Fix:** Changed `data/` → `/data/` and `logs/` → `/logs/` in `.gitignore`
(leading slash limits the rule to the repository root only).
Added `src/crypt/data/__init__.py`, `context.py`, `ingestor.py`, `store.py`
to git tracking.

Files touched: `.gitignore`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: slow shutdown (SIGINT did not interrupt in-flight awaits)

### What broke
SIGINT only set `stop_event`, but long-running coroutines (`run_health_check`,
`bootstrap`, `tick`) were awaited directly with no cancellation path.
Shutdown took up to ~30 s because those operations ran to completion before
`stop_event.wait()` was ever reached.

### Fix
Signal handler now also calls `main_task.cancel()` on the main asyncio task.
`CancelledError` is raised at the current `await` point and propagates up
through `asyncio.gather` chains; `except asyncio.CancelledError: pass` in
`_main()` ensures the `finally` cleanup block still runs.

Files touched: `src/crypt/__main__.py`.

---

## 2026-05-15 — Fix: root cause of silent zero-exit (stdlib crypt.py name collision)

Package name `crypt` collides with the deprecated Python 3.12 stdlib module
`crypt.py`. In Python's module resolution order, stdlib comes before
site-packages and the editable-install `src/` path. So `python -m crypt`
silently executed the stdlib module (no `__main__` block → exit 0, no output).

Fix: prefix the start command with `PYTHONPATH=/app/src` (railway.toml).
This puts `src/` at the front of `sys.path` before stdlib, so our package
is found first. Same fix required locally: `PYTHONPATH=src` in `.env`.

Files:
- `railway.toml`
- `.env.example`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: pandas-ta 0.4.x numba/LLVM hang on Railway

pandas-ta>=0.4 (only version available for Python 3.12+) added numba as a
hard dependency. numba initialises LLVM via llvmlite at Python import time —
before logging is even configured — causing a complete silent hang in
CPU-constrained Railway containers.

Fix: `NUMBA_DISABLE_JIT=1` is now documented as a required Railway Variable
(and added to `.env.example`). With JIT disabled numba functions fall back to
plain Python; indicators remain correct, just slightly slower.

The `<0.4` constraint was tried but is not available for Python 3.12+ on PyPI.

Files:
- `pyproject.toml` (reverted <0.4 constraint, added explanatory comment)
- `.env.example` (NUMBA_DISABLE_JIT=1 added)
- `docs/deploy/railway.md` (moved to Required variables table)
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: silent container on Railway deploy (output buffering + health check hang)

Three issues caused the process to appear dead after bytecode compilation:
1. `python -u` not set → Python buffered stderr in non-TTY container, log lines never flushed.
2. Health check created `ccxt.okx` without `"timeout": 30_000` → `load_markets()` could hang indefinitely.
3. Railpack auto-detects start command without `--no-dev` → dev packages (mypy/ruff) installed on every start, adding ~30-60 s delay before Python even booted.

Fixes: `railway.toml` start command changed to `uv run --no-dev python -u -m crypt`; `health.py` ccxt instance gets explicit 30 s timeout; `railway.md` updated with `PYTHONUNBUFFERED=1` recommendation and expanded troubleshooting table.

Files:
- `railway.toml`
- `src/crypt/runtime/health.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Railway: `uv run --no-dev` + immediate stderr logs

`uv run` includes the `dev` group by default, so every deploy was reinstalling
mypy/ruff before the app started. Start command now passes `--no-dev`. Stderr
logging uses colorize/enqueue only when stderr is a TTY so Railway log streams
see lines immediately.

Files:
- `railway.toml`
- `src/crypt/__main__.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix Railway `railway.toml` parse error

Removed invalid TOML line `$schema = ...` (that key belongs in `railway.json` only;
bare TOML keys cannot start with `$`). Railway deploy config now parses.

Files:
- `railway.toml`
- `CHANGELOG.md`

---

## 2026-05-14 — AGENTS: incident / "fix this" workflow

Clarified AI-first behaviour when the owner starts a session with errors or
CI logs instead of "continue": chat overrides stale assumptions, reproduce
before refactor, minimal fix + tests, and which task/changelog docs to touch.

Files:
- `AGENTS.md`
- `.cursor/rules/ai-first-workflow.mdc`

---

## 2026-05-14 — Session 6: Railway deployment

Railway deployment config for the M1 14-day continuous run.

Files created/modified:
- `railway.toml` — Railpack builder, production install, start command, restart policy.
- `.python-version` — pins Python 3.12.
- `src/crypt/config.py` — added `log_dir` field (env: `LOG_DIR`, default `logs/`).
- `src/crypt/__main__.py` — `_configure_logging` now accepts `log_dir` from settings.
- `.env.example` — documented `LOG_DIR`.
- `docs/decisions/0010-railway-deployment.md` — ADR (accepted).
- `docs/deploy/railway.md` — 8-step owner deployment guide with file extraction commands.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

ADRs introduced: 0010.

---

## 2026-05-14 — Session 5: reliability hardening

All P0/P1/P2 reliability items from BACKLOG completed. System is now ready
for the 14-day continuous run.

### What was done

- **`src/crypt/utils/retry.py`** (new) — `retry_with_backoff` coroutine helper
  with full-jitter exponential backoff (`uniform(0, min(max_delay, base*2^n))`).
- **`src/crypt/exchange/okx.py`** — all 5 fetch methods wrapped with
  `retry_with_backoff`; `"timeout": 30_000` added to ccxt config.
- **`src/crypt/data/ingestor.py`** — `ingest_all` and `_ingest_symbol`
  now log `BaseException` items from `asyncio.gather(return_exceptions=True)`.
- **`src/crypt/runtime/orchestrator.py`** — `tick()` logs exceptions from
  gather; sink exceptions logged by name; `_evaluate_symbol` returns
  `"ok"/"partial"/"failed"` status; tick summary log line at end.
  `Timeframe` added to imports.
- **`src/crypt/runtime/health.py`** — `_check_disk_space` added (logs WARNING
  if < 1 GB free on `data_dir` filesystem).
- **`src/crypt/__main__.py`** — log rotation changed to `rotation="00:00"` +
  `compression="gz"`; `_heartbeat_loop` background task (30-min liveness log +
  6h OKX health re-check); heartbeat task cancelled cleanly on shutdown.
- **`src/crypt/sinks/telegram.py`** — backoff jitter: `random.uniform(0.5, 1.5)`
  multiplier on retry wait.
- **`src/crypt/config.py`** — `okx_max_retries`, `okx_retry_base_delay`,
  `okx_retry_max_delay` settings exposed.
- **`.env.example`** — retry/backoff params documented (commented out).
- **`deploy/crypt.service`** (new) — systemd unit with `Restart=always`,
  `RestartSec=10`, `EnvironmentFile`, `WorkingDirectory`.
- **`README.md`** — "Running as a service" section added.

Results: mypy 0 errors / 36 files. ruff clean. 42/42 tests pass.

ADRs introduced: none.

---

## 2026-05-14 — Session 3: M1 validation

All M1 P0/P1 items resolved. System runs against live OKX without errors.

Files changed:

- `pyproject.toml` — added `pandas.*`, `pyarrow.*` to mypy overrides.
- `src/crypt/exchange/okx.py` — fixed `fetch_ls_ratio` and `fetch_taker_volume`: OKX rubik stat endpoints require `ccy` (base currency), not `instId`.
- `src/crypt/runtime/health.py` — **new**: startup health-check (OKX ping, symbol existence via market `id`, optional Telegram bot ping).
- `src/crypt/runtime/scheduler.py` — `stop()` guarded with `running` check.
- `src/crypt/__main__.py` — import `run_health_check`; call it before bootstrap; create `logs/` directory before file sink.
- `src/crypt/data/store.py` — typed lambda list; pyarrow `type: ignore`.
- `src/crypt/engines/derivatives.py` — `Direction` annotation; typed `_ls_signal` param; added imports.
- `src/crypt/engines/trend.py` — `Direction` annotation; `Direction` import.
- `src/crypt/engines/meanrev.py` — `Direction` annotation; `std=2.0`; `type: ignore[arg-type]`.
- `src/crypt/engines/volatility.py` — `npt.NDArray[Any]` for `_rank_pct`.
- `src/crypt/config.py` — `return list(v)` to silence mypy `no-any-return`.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

Results: mypy 0 errors / 34 files. ruff clean. 42/42 tests pass.
Smoke test: `uv run python -m crypt --once` exits 0, verdicts for all 3 symbols.
Symbol check: SOL-USDT-SWAP ✓, TON-USDT-SWAP ✓, XPL-USDT-SWAP ✓.

ADRs introduced: none.

---

## 2026-05-14 — Session 2: M1 implementation

Full M1 code layer implemented. Context7 was unavailable; proceeded with
in-context library knowledge.

Files created:

- `src/crypt/config.py`, `models.py`, `__main__.py`
- `src/crypt/exchange/__init__.py`, `base.py`, `okx.py`
- `src/crypt/data/__init__.py`, `store.py`, `ingestor.py`, `context.py`
- `src/crypt/engines/__init__.py`, `base.py`, `trend.py`, `meanrev.py`,
  `derivatives.py`, `volatility.py`, `regime.py`
- `src/crypt/aggregator/__init__.py`, `weights.py`, `ensemble.py`
- `src/crypt/decision/__init__.py`, `filters.py`
- `src/crypt/sinks/__init__.py`, `base.py`, `telegram.py`, `jsonlog.py`,
  `console.py`, `execution_stub.py`
- `src/crypt/runtime/__init__.py`, `scheduler.py`, `orchestrator.py`
- `src/crypt/backtest/__init__.py`
- `config/weights.yaml`
- `tests/conftest.py`, `tests/engines/test_{trend,meanrev,derivatives,
  volatility,regime}.py`, `tests/aggregator/test_ensemble.py`,
  `tests/decision/test_filters.py`

Also updated: `pyproject.toml` (`requires-python` bump to `>=3.12`),
`uv.lock` generated.

All 42 tests pass; `ruff` clean.

Next: live smoke test, `XPL-USDT-SWAP` existence check, mypy pass.

ADRs introduced: none.

---

## 2026-05-13 — Session 1: project bootstrap

Owner pinned down the high-level requirements: Python, OKX-only, 4h intraday,
3 starting symbols (`SOL-USDT-SWAP`, `TON-USDT-SWAP`, `XPL-USDT-SWAP`),
Telegram alerts, 0$ data budget, local execution, weighted-sum aggregator,
confidence threshold 75%, AI-first development.

Created the project scaffold:

- `README.md`, `AGENTS.md`, this `CHANGELOG.md`, `.gitignore`, `.env.example`
- `.cursor/rules/` — `project-context.mdc`, `ai-first-workflow.mdc`,
  `coding-standards.mdc`
- `docs/architecture.md`
- `docs/decisions/` — ADRs 0001–0008
- `docs/tasks/` — `ROADMAP.md`, `BACKLOG.md`, `IN_PROGRESS.md`, `DONE.md`
- `docs/engines/` — specs for `trend`, `meanrev`, `derivatives`, `volatility`,
  `regime`, `aggregator`, `decision`
- `pyproject.toml`, `src/crypt/__init__.py`, `tests/`

OKX API capabilities verified via Context7 (`/websites/okx_docs-v5_en` and
`/ccxt/ccxt`):

- OHLCV, funding rate (current + history), open interest history, long/short
  account ratio, taker volume — all available via public REST.
- Liquidations — only via WebSocket; deferred (ADR 0006).

No code yet. Next session: implement data layer + signal contracts (see
`docs/tasks/IN_PROGRESS.md`).

ADRs introduced: 0001..0008.
