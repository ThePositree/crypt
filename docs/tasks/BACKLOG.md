# Backlog

Prioritised list of concrete items. Priority labels:

- **P0** — blocker / safety / can break the project. Do first.
- **P1** — important; the milestone is incomplete without it.
- **P2** — nice-to-have; revisit when higher priorities are clear.

Items move from here → `IN_PROGRESS.md` when work starts → `DONE.md`
when finished.

## P0 — Audit finite-position margin sizing before H1 promotion

**What:** audit and test the current position-sizing / margin-limit semantics
for finite `max_positions`, especially the `max_positions = 1` path in
`src/backtester/risk_model.py` where the derived margin cap can allow one
position to consume almost all available balance as isolated margin.

**Why now:** the 2026-06-05 lower-risk repeats of the best bounded H1 short-only
row (`rrr = 1.5`, `ttl = 42`, `max_positions = 1`) showed that reducing
`risk_percent` from `1.0` to `0.5` and `0.25` scales return/drawdown down but
does not remove the margin blocker: peak locked margin remains `96.62%` of
initial capital.

**Expected gain:** make margin diagnostics actionable enough to distinguish a
realistic bounded candidate from an artifact of the current leverage/margin
geometry.

**Acceptance:** focused tests describe and lock the intended semantics for
`risk_percent`, `max_positions`, `max_allowed_margin`, required leverage, and
`locked_margin`; the seven-window H1 bounded row is rerun or re-summarized with
the corrected semantics; the result explicitly says whether a candidate is
worth a longer owner-run check or whether ADR-0024's liquidation-aware leverage
work remains the blocker.

## P2 — Align H1 candidate validation window defaults and docs

**What:** make `compare-fixed` candidate-validation examples and defaults
explicit about their window set, or add a named preset matching the current
signal-quality acceptance set: SOL Jan/Feb/Mar 2025 plus TON Jan/Feb/Mar/Apr
2025.

**Why now:** the 2026-06-05 short-only candidate task expected seven windows,
but the documented `compare-fixed` command without explicit `--window` options
ran only SOL Jan/Feb/Mar and TON Jan/Feb by default. The missing TON March/April
windows had to be run as supplemental reports.

**Expected gain:** reduce operator error and make future candidate validation
reports complete without manual window reconstruction.

**Acceptance:** README/task examples either pass all intended `--window`
options explicitly or the CLI exposes a preset/default that writes all seven
candidate-validation windows in one `windows.csv`.

> **Important reading:** the 2026-05-15 planning session created several
> specs under `docs/` that this backlog references repeatedly. Read them
> before starting work on any non-trivial item.

---

## Currently completed (M1 done)

The whole M1 (signal-only, manual trading) block is done and deployed.
See `docs/tasks/DONE.md` and the M1 entry in `CHANGELOG.md`.

The remaining items from the original P0/P1 reliability lists are all
checked-off; only post-M1 work is listed below.

---

## P0 — must do soon after the 14-day run ends

### CI / quality gates

- [x] **GitHub Actions CI** — `.github/workflows/ci.yml` (2026-05-29).
- [x] **Pre-commit hooks** — `.pre-commit-config.yaml` (2026-05-29).

### Threshold transparency

- [x] **`[UNCALIBRATED]` marker on Telegram alerts** — ADR-0011; shipped
      2026-05-29. Removed when M2 calibration lands (ADR-0014).
- [ ] **`config/weights.yaml` header comment** — make it explicit at
      the top of the file that values are placeholders pending M2
      calibration.

### Latent code issues from planning session

See `docs/post_m1_code_fixes.md` for the technical detail of each. The
priorities below are the BACKLOG view.

- [x] **Closed-candle invariant** — `post_m1_code_fixes.md` §1. Shipped 2026-05-29.
- [x] **Critical-inputs guard refactor** — `post_m1_code_fixes.md` §2. Shipped 2026-05-29.

### Package name / stdlib conflict

- [x] **`crypt` vs Python stdlib `crypt`** — ADR-0013; `pythonpath = ["src"]`
      in `pyproject.toml` (2026-05-29). `uv run pytest` now works without
      manual `PYTHONPATH=src`.

### M2 architecture redirect — donor backtester migration

ADR-0018 makes `backtester/` the canonical future M2 backtest architecture.
ADR-0021 tracks it in this monorepo. Implementation details live in
`docs/backtester_migration.md`.

### Urgent owner-limited profitability sprint

The owner has about 2-3 Codex sessions left before usage limits reset. For
those sessions, prioritize tasks that can produce a profitable bounded
candidate and an owner-run long backtest command. Defer low-leverage
engineering polish unless it directly supports that outcome.

- [x] **Build fixed-candidate H1 comparison across windows** — P0. Compare the
      fixed candidate `rrr = 1.25`, `position_ttl_bars = 36`,
      `risk_percent = 1.0`, H1 diagnostic strategy config
      `max_sl_distance_atr = 4.0`, with strategy-param, daily-limit, and
      trading-window search disabled. Cover completed windows (SOL January
      2025, SOL February 2025, TON January 2025) plus at least SOL March 2025
      and TON February 2025. Produce one table with return, profit factor, max
      drawdown, trades, long PnL, short PnL, exit distribution, and signal
      side counts. This may be a small tested report script/CLI if faster than
      manual artifact stitching. Completed 2026-06-03 with
      `backtester compare-fixed`; artifacts:
      `/tmp/crypt_fixed_candidate_h1/20260603_134312`.
- [x] **Select first long-run candidate from bounded evidence** — P0. If the
      fixed candidate is positive or near break-even across most windows,
      freeze it as candidate A. If it fails, run a tiny execution-only grid
      over `rrr = 1.0, 1.25, 1.5` and `position_ttl_bars = 30, 36, 42` on the
      same windows. Do not enable `--strategy-param-search` for this step.
      Acceptance for "worth a long local run" is not final profitability; it
      is a bounded profile with positive total return on multiple windows,
      profit factor above 1 on most windows, drawdown not exploding, and no
      obvious single-window overfit. Completed 2026-06-03: candidate A is the
      fixed `rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0` H1 diagnostic
      profile. It is positive on 4/5 bounded windows but failed SOL March
      2025; this makes it worth a long diagnostic run, not accepted
      calibration.
- [x] **Run minimal side-skew attribution before adding filters** — P0. For
      the same windows, summarize H4 setup verdict side counts, H1 tradeable
      signal side counts, structural-stop availability by side, and realized
      PnL by side. Only if longs remain consistently harmful should the next
      agent add an explicit side filter such as `allowed_sides = short`; that
      change must update `docs/crypt_ensemble_mtf.md` first and include
      focused tests. Completed 2026-06-03 at the bounded-report level:
      `compare-fixed` exports setup verdict counts, tradeable signal side
      counts, and realized PnL by side. Result: all windows except SOL January
      are short-only after structural-stop/trigger filtering.
- [x] **Prepare owner-run long backtest/Optuna command** — P0. End the sprint
      with a single command the owner can run unattended for the 5-day limit
      reset window. Prefer full-history execution-only evaluation of frozen
      strategy parameters, or a bounded walk-forward batch, over broad
      full-history strategy-param Optuna. Document expected output files,
      monitoring commands, and how to interpret `trials.csv`, `best_trial.json`,
      `best_run/metrics.csv`, `trade_diagnostics.csv`, and
      `signal_diagnostics.csv`. Completed 2026-06-03: use the documented
      `compare-fixed` command with explicit full-history `--window` entries for
      SOL/TON to evaluate candidate A without strategy-param search.
- [x] **Avoid broad full-history strategy-param Optuna during Codex time** —
      P0. A curiosity run started on 2026-06-03 with full-history SOL H1,
      `--trials 100`, `--strategy-param-search`, daily-limit search, and
      trading-window search. Trial 0 alone took about 1h48m and returned
      `total_return_pct = -9.47`, `max_drawdown = -24.75`, `total_trades =
      482`. Treat this as evidence that broad full-history strategy-param
      search is too expensive until a smaller candidate is already justified.
      Guardrail documented 2026-06-03.

- [x] **Run tiny execution-only grid around candidate A if SOL March remains
      the blocker** — P1. If the owner-run full-history check or the next
      bounded pass confirms that SOL March is the main failure mode, compare
      `rrr = 1.0, 1.25, 1.5` and `ttl = 30, 36, 42` with
      `--no-strategy-param-search`, no daily-limit search, and no
      trading-window search before touching strategy params or side filters.
      Completed 2026-06-03 with `backtester compare-grid` at
      `/tmp/crypt_execution_grid_sol_mar/20260603_153612`: all 9 candidates
      remained negative on SOL March; best was `rrr = 1.0`, `ttl = 30`,
      `total_return_pct = -6.15`, `profit_factor = 0.66`, max drawdown
      `-11.20`, 64 short-only trades. This confirms the blocker is not just
      the fixed candidate's `rrr = 1.25` / `ttl = 36` geometry.

- [x] **Parallelize fixed-window `compare-fixed` before broad Optuna** — P1.
      Added `compare-fixed --jobs N` on 2026-06-03. It parallelizes independent
      windows at the process level, preserves deterministic `windows.csv` /
      `windows.md` row order, rejects duplicate labels that would overwrite
      run artifacts, and leaves the default serial (`--jobs 1`).
- [x] **Parallelize tiny execution grids before broad Optuna** — P1. After a
      tiny execution-only grid runner exists, add bounded `--jobs` at the
      window/candidate level. Do not turn on broad full-history
      `strategy-param-search` parallelism for this. Acceptance: default remains
      serial/reproducible, `--jobs > 1` writes one timestamped report with
      deterministic aggregation, and worker failures are surfaced clearly.
      Completed 2026-06-03 as `backtester compare-grid --jobs N`; the SOL
      March grid completed with `--jobs 3` and deterministic `grid.csv` row
      order. Follow-up session 39 changed `compare-grid` to reuse one
      precomputed signal frame per window, so `--jobs` now parallelizes
      independent windows rather than candidates inside the same window.
- [ ] **Add disk-backed `crypt_ensemble` signal cache for optimizer workers**
      — P1 before multi-process strategy-param search. Current optimizer
      signal caching is in-memory per `ParameterOptimizer`, so multiple
      workers would rebuild the same expensive signal frames. Add a Parquet
      cache keyed by strategy params, symbol, primary timeframe, from/to
      window, strategy/cache schema version, and relevant config. Acceptance:
      cache hits are visible in trial/user attrs or logs, cache writes are
      atomic enough for concurrent workers, stale schema versions miss safely,
      and no-lookahead parity tests still pass.
- [ ] **Add guarded optimizer parallelism (`--jobs`) only for safe modes** —
      P1 after the fixed-window/grid parallel runner. Optuna supports
      `study.optimize(..., n_jobs=N)` and multiple processes sharing storage,
      but this project should expose it only with guardrails. Acceptance:
      `--jobs > 1` is allowed for execution-only search with precomputed or
      disk-cached signals; broad `--strategy-param-search` with `--jobs > 1`
      is rejected or requires the disk signal cache; Optuna journal/RDB
      storage choice is documented; progress output remains readable.
- [x] **Precompute signals explicitly for execution-only optimization** —
      P1. Add an execution-only path that builds `crypt_ensemble` signals once
      for a fixed strategy config, then runs `rrr`/`ttl`/`risk_percent`
      candidates against the precomputed signal frame. This can be a dedicated
      helper behind `compare-fixed`/optimizer rather than a second broad
      optimizer. Acceptance: first signal build happens once per
      symbol/window/strategy config, every execution candidate reuses the same
      signal frame, and best-run export does not regenerate signals. Completed
      2026-06-03 for `compare-grid`: candidates are grouped by window, one
      signal frame is generated per window, execution candidates reuse it, and
      a tiny SOL smoke confirmed byte-identical `signals.csv` exports across
      two `rrr` candidates. Existing optimizer best-run cached-signal reuse
      remains in place; disk-backed worker sharing is tracked separately.
- [x] **Preserve partial `compare-grid` summaries when a window fails** — P1.
      Completed 2026-06-04 after owner-provided `results.tar` showed the
      extended grid aborted on missing `sol_2025_05` data after 360 candidate
      runs had already completed. `compare-grid` now writes `grid.csv` /
      `grid.md` for completed windows and `grid_errors.csv` /
      `grid_errors.md` for failed windows.
- [x] **Add report-only H1 signal quality diagnostics before more execution
      grids** — P0. Why: candidate A is rejected after SOL full `+4.39%` but
      TON full `-54.65%`, and the completed monthly grid has no robust
      `rrr`/`ttl` candidate. Gain: attribute PnL and trade counts by side,
      setup month, confidence bucket, anchor type, anchor age/freshness,
      context/setup direction, and reversal/stale markers before changing
      signal logic. Completed 2026-06-04 with `backtester signal-quality`,
      which writes `signals.csv` / `groups.csv` plus Markdown and fail-soft
      `errors.csv` artifacts.
- [x] **Implement bounded H1 setup/anchor filters after diagnostics** — P0.
      Why: the next likely signal-quality fixes are side gating, stale-anchor
      rejection, liquidity-sweep-anchor rejection, and context-reversal
      blocking; these needed to be testable without changing the base H1
      config. Gain: future bounded comparisons can use one explicit filtered
      diagnostic strategy instead of ad hoc CSV editing. Completed 2026-06-04:
      `crypt_ensemble` now supports default-off `allowed_sides`,
      `blocked_sl_anchor_types`, `max_anchor_age_hours`, and
      `block_context_reversal`; `crypt_ensemble_h1_filtered.json` enables the
      first diagnostic combination.
- [x] **Run base-vs-filtered H1 signal-quality comparison** — P0. What: run
      `backtester signal-quality` across default SOL Jan/Feb/Mar and TON
      Jan/Feb/Mar/Apr windows with both
      `strategies/backtester/crypt_ensemble_h1.json` and
      `strategies/backtester/crypt_ensemble_h1_filtered.json`. Why now: the
      implementation is in place but only short SOL smoke windows were run in
      this session. Expected gain: decide whether the first filter combination
      improves the harmful groups identified by diagnostics without deleting
      too much useful signal flow. Acceptance: two output directories with
      `signals.csv`, `groups.csv`, Markdown copies, and per-window runs; a
      written comparison of return/PnL by side, anchor type, anchor age bucket,
      context/setup alignment, stale marker, and reversal marker. Completed
      2026-06-04 with base
      `results/crypt_ensemble_h1_signal_quality_base/20260604_141103`, full
      filter
      `results/crypt_ensemble_h1_signal_quality_filtered/20260604_142009`,
      short-only ablation
      `results/crypt_ensemble_h1_signal_quality_filter_short_only/20260604_143218`,
      and no-liquidity-sweep ablation
      `results/crypt_ensemble_h1_signal_quality_filter_no_liquidity_sweep/20260604_144227`.
- [x] **Validate narrow H1 short-only candidate before promoting filters** —
      P0. What: run a candidate-style bounded report for
      `strategies/backtester/crypt_ensemble_h1_filter_short_only.json` over
      the default SOL Jan/Feb/Mar and TON Jan/Feb/Mar/Apr windows. Why now:
      short-only improved the 7-window aggregate to `+3.96%` by removing
      harmful longs, while the full filter was weaker (`+2.31%`) and
      no-liquidity-sweep alone stayed negative (`-8.29%`). Expected gain:
      determine whether short-only is a simple owner-run candidate or whether
      SOL March / TON March failures still block promotion. Acceptance: one
      timestamped report with return, profit factor, max drawdown, trades,
      side PnL, and a written promote/reject/follow-up decision.
      Completed 2026-06-05: seven-window result was `+3.96%` but not
      promoted; ADR-0024 margin/concurrency guard remained blocking.
- [x] **Audit H1 concurrent-position and margin realism before promotion** —
      P0. What: add/report enough donor execution state to audit simultaneous
      positions under isolated-margin futures: `locked_margin`,
      `available_balance_before`, `open_positions_before`, peak concurrent
      position count, peak locked margin, and peak locked-margin percentage.
      Why now: owner review of the SOL January short-only artifact showed that
      `capital_before` / `capital_after` are realized-equity fields, not free
      margin fields, and reconstructing margin from the old artifact showed up
      to 16 simultaneous positions with roughly 100% of initial capital locked.
      Expected gain: prevent promotion of an H1 candidate that only works
      because the simulator permits unrealistic pyramiding or opaque margin
      usage. Acceptance: a bounded short-only report over the default SOL/TON
      windows includes the new margin diagnostics, documents whether old
      `capital_before` semantics were misleading but intentional, and states
      whether finite `max_positions` must be enforced before owner-run checks.
      Completed 2026-06-05: unconstrained short-only still totals `+3.96%`,
      but peak simultaneous positions reach 18, peak locked margin reaches
      `104.42%` of initial capital, and finite `max_positions` is mandatory
      before owner-run promotion checks.
- [x] **Expose `max_positions` as a donor Optuna/search dimension** — P0
      after the margin-realism audit. What: let bounded optimizer/report flows
      search `max_positions` over explicit finite values such as `1`, `2`,
      `3`, and `5`, with `0` allowed only as an unconstrained diagnostic
      baseline. Why now: the owner wants Optuna to decide how many positions
      can be open, and the 2026-06-05 audit showed unconstrained H1 entries can
      consume roughly all available margin with up to 18 simultaneous
      positions. The margin state is now auditable.
      Expected gain: replace manual guesses about concurrent positions with
      reproducible bounded evidence while keeping real margin constraints
      visible. Acceptance: `trials.csv` / `best_trial.json` / report Markdown
      include `max_positions`, best-run export respects the selected value,
      focused tests prove the search parameter is passed into `ExecutionSim`,
      and docs warn that unconstrained `max_positions = 0` is not promotable
      without separate justification. See ADR-0024.
      Completed 2026-06-05: optimizer supports explicit
      `--max-positions-values` choices plus contiguous low/high/step ranges,
      `compare-grid` supports `--max-positions-values`, summaries include
      `max_positions`, best-run export respects the selected value, and
      focused tests cover the wiring.
- [ ] **Model liquidation-aware isolated-futures leverage explicitly** — P1.
      What: decide and implement how leverage is selected when liquidation is
      allowed to act as the effective stop in isolated futures. Why now: using
      maximum OKX leverage (`25x`) minimizes locked margin, but if liquidation
      is closer than the structural stop then the true risk and TP geometry
      must be based on liquidation, not the farther structural stop. Expected
      gain: make high-leverage candidate checks mathematically honest instead
      of treating liquidation as both harmless and invisible. Acceptance:
      strategy/backtester docs define liquidation-price inputs and formulas,
      exported trades include leverage and liquidation/effective-stop fields,
      tests cover liquidation closer/farther than structural SL, and no
      candidate can silently score risk against a stop that would not be
      reached before liquidation.

- [x] **Vend `backtester/` into crypt monorepo** — P1. Remove nested
      `backtester/.git`; commit donor sources from the `crypt` root. ADR-0021;
      docs shipped 2026-06-02. Owner completes the git add/commit after
      removing `.git`.
- [x] **Run donor `backtester` tests from the root project** — P2. Completed
      2026-06-04 via ADR-0023 root integration: donor tests now live in
      `tests/backtester/` and run under root `uv run pytest`.
- [ ] **Bring `src/backtester/` under strict mypy** — P2. The root-integrated
      donor package is not yet strict-typed, so CI still runs
      `mypy --strict src/crypt`. Add gradual typing or targeted ignores before
      expanding strict mypy to `src/backtester/`.
- [ ] **Bring `src/backtester/` under root ruff rules** — P2. The donor code
      still has many pre-existing style violations under the stricter root
      rules (`PTH`, `RUF`, `SIM`, Russian comments/docstrings, etc.), so CI
      currently excludes `src/backtester/` and `tests/backtester/` from ruff.
      Clean this separately from functional strategy work.

- [x] **Add donor `StrategyData` contract** — P0. Extend the donor package
      additively so strategies can receive either a plain `pd.DataFrame` or a
      richer object with primary OHLCV, timeframe candles, extras, and
      metadata. Existing donor strategies must keep working unchanged.
      Shipped 2026-06-02.
- [x] **Add `parquet` data source to donor CLI** — P0. Load one Parquet OHLCV
      file, accepting both donor-style columns and project-style
      `open_time`/`o`/`h`/`l`/`c`/`v` columns. Shipped 2026-06-02.
- [x] **Add `crypt-parquet` data source to donor CLI** — P0. Load the existing
      project Parquet layout for one symbol; H4 required, H1/D1/extras
      optional and represented as empty DataFrames when unavailable. Shipped
      2026-06-02.
- [x] **Register `crypt_ensemble` donor strategy** — P0. First skeleton may
      emit neutral/no-trade rows; final version adapts existing engines and
      aggregator into donor `signal` + `sl_price` output. Neutral skeleton
      shipped 2026-06-02.
- [x] **Run donor-backed SOL neutral smoke backtest** — P0. `parquet` and
      `crypt-parquet` modes loaded 5545 SOL H4 bars and wrote no-trades
      reports with the neutral `crypt_ensemble` skeleton (2026-06-02).
- [x] **Wire existing ensemble into `crypt_ensemble`** — P0. Adapt existing
      engines and aggregator into donor `signal` + `sl_price` output while
      preserving no-lookahead semantics and graceful missing-data behaviour.
      First engine-wired slice shipped 2026-06-02.
- [x] **Run first trade-producing donor-backed SOL smoke backtest** — P0. Use
      one symbol, existing Parquet data, and engine-wired `crypt_ensemble`;
      verify exported trades include enough verdict metadata before deleting or
      deprecating old commands in README. First owner-completed run produced
      1792 trades; donor export metadata was fixed afterward (2026-06-02).
- [x] **Rerun SOL donor smoke after monthly risk-base sizing** — P0. ADR-0019
      changed `crypt_ensemble` from per-trade current-capital sizing to
      monthly window-base sizing and added trade metadata export. Rerun the
      same SOL command and inspect `trades.csv` for `signal_time`,
      `risk_base_capital`, confidence, score, regime, rationale, and
      `strength_<engine>` columns. Completed 2026-06-02 at
      `/tmp/crypt_donor_smoke/20260602_104522`; result was diagnostic only
      because it exposed that donor entries ignored the live confidence
      threshold.
- [x] **Run diagnostic SOL donor smoke with `min_confidence = 75`** — P0.
      Completed 2026-06-02 at `/tmp/crypt_donor_smoke/20260602_122510`:
      0 trades, 1798 directional verdicts, max confidence 52, and 0 rows with
      `confidence >= 75`. ADR-0020 records the owner correction: `75` was an
      arbitrary placeholder, so this diagnostic should not block Optuna.
- [x] **Audit confidence scale vs live threshold** — P0. Closed by ADR-0020:
      do not search for a post-hoc rationale for `75`; it remains only a live
      alert placeholder. Donor `crypt_ensemble` no longer defaults to
      `min_confidence = 75`.
- [x] **Rerun SOL donor smoke after removing default `min_confidence = 75`** —
      P0. Owner-provided result reviewed at
      `/tmp/crypt_donor_smoke/20260602_132627`: 1792 trades, final capital
      6694.69 from 10000, `total_return_pct = -33.05`,
      `profit_factor = 0.88`, max drawdown `-36.96`; long side remains the
      main drag, shorts are slightly positive.
- [ ] **Add donor signal diagnostics command/report** — P1. `signals.csv` and
      `signal_diagnostics.csv` now exist, but operators still need a cheap
      way to summarize decision/confidence/regime distributions without
      rerunning the 15-minute SOL smoke.
- [x] **Replace mechanical ATR SL with structural SMC SL** — P0. Implement
      `docs/crypt_ensemble_structural_sl.md` before running another optimizer
      or interpreting donor backtest metrics. Keep donor `ExecutionSim`
      unchanged; compute only `crypt_ensemble`'s `sl_price` differently.
      Shipped 2026-06-02.
- [x] **Rerun SOL donor smoke after structural SMC SL** — P0. Use the current
      `strategies/backtester/crypt_ensemble.json`, inspect `signals.csv`,
      `signal_diagnostics.csv`, `trades.csv`, and metrics. Expect fewer trades
      because BUY/SELL verdicts without valid structural stop anchors now emit
      `signal = 0`. Completed 2026-06-02 at
      `/tmp/crypt_donor_structural_sl_smoke/20260602_143827`: 1672 trades,
      final capital 6683.68 from 10000, `total_return_pct = -33.16`,
      `profit_factor = 0.84`, max drawdown `-35.38`; long side remains
      materially negative while shorts remain slightly positive.
- [ ] **Investigate structural order-block stop quality** — P1 before
      trusting optimization output. Structural SL mostly selected order-block
      anchors (1589/1672 trades) and did not improve SOL smoke metrics versus
      the previous no-structural run; inspect whether OB stops are too wide,
      stale, or weakly related to the entry premise before treating optimizer
      improvements as robust.
- [ ] **Implement unified MTF `crypt_ensemble` contract** — P0. Owner wants
      top-down D1 context -> H4 setup -> H1 trigger/execution, with the design
      generic enough for a future 15m trigger. Start from
      `docs/crypt_ensemble_mtf.md`; preserve current H4 default mode, add
      timeframe-role config, use H1 as primary only in the H1 strategy config,
      and add no-lookahead tests before full acceptance. First additive code
      slice and bounded SOL H1 smoke shipped 2026-06-02; full H1 smoke remains
      open.
- [x] **Add donor smoke range limiter for project Parquet** — P0 before
      rerunning full H1 MTF smoke. The attempted SOL H1 smoke loaded 21517 H1
      bars and did not reach export during the session. Add `from`/`to` or
      equivalent range selection for `crypt-parquet` so MTF contract smokes can
      complete quickly before launching full-history long runs. Shipped
      2026-06-02 as `--from` / `--to` on the donor run CLI. Follow-up fix:
      bounds now limit primary/output rows while preserving pre-start candle
      history for H4/D1 warmup up to `--to`.
- [x] **Expand MTF no-lookahead tests before full H1 acceptance** — P0.
      Add explicit tests for D1 forming-candle exclusion, future-known H4
      structural object rejection, and donor execution entry timing after a
      closed H1 trigger candle. Shipped 2026-06-02. This also fixed
      `crypt_ensemble` to leave `entry_price` empty so donor execution enters
      at the next execution-bar open instead of the signal candle close.
- [x] **Implement H1 structural stop-source selection** — P0 before accepting
      H1 MTF metrics. The bounded SOL H1 smoke at
      `/tmp/crypt_donor_h1_mtf_smoke_bounded/20260602_191541` produced 35
      trades, all with `sl_source_tf = 4h` and order-block anchors. The MTF
      spec still calls for aligned H1 structure to provide a closer protective
      stop when available. Shipped 2026-06-02. Bounded SOL smoke after the
      change completed at
      `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`: 159
      tradeable signals, 153 with `sl_source_tf = 1h`; 158 trades, final
      capital 9058.19, `total_return_pct = -9.42`, `profit_factor = 0.66`.
      This is a contract diagnostic, not accepted profitability.
- [x] **Rerun bounded SOL H1 MTF smoke after next-open entry fix** — P0
      before comparing H1 metrics. The previous bounded smoke predates the
      `entry_price = NaN` fix, so its trades used signal-candle close entries
      rather than donor next-H1-open entries. Completed 2026-06-02 at
      `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`:
      745 H1 signal rows, 35 short trades, final capital 9357.25,
      `total_return_pct = -6.43`, `profit_factor = 0.04`, max drawdown
      `-6.27`; sample trades confirm entry on the next H1 open.
- [ ] **Tune H4/H1 setup geometry before broad Optuna** — P0 before
      interpreting MTF smokes or starting broad Optuna. Current structural SOL
      H4 smoke closed 1496/1672 trades by `ttl_expired`; median TTL-expired
      `sl_distance_atr` was 3.985, so with `rrr = 2` the TP is roughly 8 ATR
      away while `ttl = 6` H4 bars allows only 24 hours. For H1, retune `ttl`,
      `rrr`, and stop-distance caps instead of inheriting H4 values. The first
      bounded H1 smoke had 60% TTL exits and `profit_factor = 0.05`; after H1
      stop-source selection, the bounded smoke produced 158 trades with 50%
      TTL exits and `profit_factor = 0.66`. A first tighter H1
      `max_sl_distance_atr = 4.0` diagnostic reduced the same January slice to
      98 trades, 37.8% TTL exits, `profit_factor = 0.97`, and
      `total_return_pct = -0.53`. A parity-safe optimized-window rerun on
      2026-06-03 preserved the same key metrics and reduced bounded runtime to
      about 5 minutes 3 seconds. ADR-0022 and the optimizer signal cache now
      make execution-only `rrr` / `ttl` Optuna trials fast after the first
      signal build; continue with bounded optimizer diagnostics instead of
      manual grids before accepting H1 metrics. First operator-facing SOL H1
      12-trial slice completed 2026-06-03 at
      `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`: best in-sample
      diagnostic was `rrr = 1.25`, `position_ttl_bars = 30`,
      `total_return_pct = 2.46`, `profit_factor = 1.14`, max drawdown `-5.7`;
      this must be checked on adjacent windows and non-SOL symbols before any
      calibration acceptance. First adjacent/non-SOL pass completed
      2026-06-03: SOL February best was `rrr = 1.25`, `ttl = 36`,
      `total_return_pct = 13.82`, `profit_factor = 5.40`, max drawdown
      `-1.90`, 53 short-only trades; TON January best was `rrr = 1.50`,
      `ttl = 36`, `total_return_pct = 1.95`, `profit_factor = 1.12`, max
      drawdown `-5.51`, 86 short-only trades. This is encouraging but not
      accepted calibration because the side profile is unstable across
      windows.
- [x] **Add operator-facing bounded optimizer command for `crypt_ensemble`** —
      P0 before broad tuning. Shipped 2026-06-03 as `backtester optimize`.
      The command loads bounded `crypt-parquet`, preserves strategy JSON
      params, writes `trials.csv`, `best_trial.json`, the Optuna journal log,
      and donor `best_run/` diagnostics, and reuses cached best signals for
      execution-only best-run export.
- [x] **Run adjacent-window H1 optimizer diagnostics** — P0 before trusting
      the January SOL slice. Reuse `backtester optimize` with
      strategy-param search disabled on adjacent SOL windows and at least one
      non-SOL symbol; compare side PnL, exit distribution, drawdown, and
      whether the `rrr = 1.25` / `ttl = 30` result is stable. Completed first
      pass 2026-06-03 with SOL February and TON January; XPL intentionally
      skipped because H1 history is shorter.
- [ ] **Run broader out-of-sample H1 optimizer diagnostics** — P0 before
      enabling strategy-param search. Run at least SOL March 2025 and TON
      February 2025 with strategy-param, daily-limit, and trading-window
      search disabled. Compare each per-window Optuna best against the fixed
      candidate `rrr = 1.25`, `position_ttl_bars = 36` so calibration is not
      based only on in-sample best trials.
- [ ] **Investigate H1 short-only side skew before adding filters** — P0.
      SOL February and TON January best runs were short-only, while SOL
      January mixed longs and shorts. Inspect whether the skew comes from H4
      setup verdicts, D1 context filtering, structural-stop availability, or
      the single `1h_candle_confirm` trigger before adding side-specific
      filters.
- [ ] **Add minimal donor Optuna support for `crypt_ensemble` parameters** —
      P0 after structural SL. Adapt the existing donor optimizer shape rather
      than adding new donor-wide semantics. Register strategy parameters:
      structural SL buffer, optional `min_confidence`, regime thresholds, and
      active OHLCV engine weights. Do not add `folds`; keep `trials` as an
      optional/defaulted run knob.
- [x] **Add risk/setup dimensions to donor Optuna** — P1. Existing
      `ParameterOptimizer` now supports configurable `rrr`, Optuna-controlled
      `position_ttl_bars`, fixed or searched `risk_percent`, and preserved
      `risk_base_period` (2026-06-03).
- [ ] **Profile `crypt_ensemble` replay performance after parity tests** — P1.
      The straightforward engine-wired donor strategy is slow on 5545 SOL H4
      bars. Do not add caching/incremental shortcuts until tests prove outputs
      are identical to the straightforward closed-candle replay and preserve
      no-lookahead semantics. H1 stop-source selection added a second SMC pass
      per H1 tick. A first parity-safe closed-window cache is implemented and
      enabled only in the H1 diagnostic config; it reduced the bounded January
      smoke from about 6 minutes 35 seconds to about 5 minutes 3 seconds for
      745 H1 bars. ADR-0022 then introduced H4 setup snapshots for H1 MTF:
      the first 745-bar signal build still took about 226.9 seconds, but
      subsequent execution-only Optuna trials reused cached signals and
      completed in about 0.05 seconds each. Further speedups should target the
      first signal build, likely via indicator precomputation or more
      granular SMC state caching.
- [ ] **Compare risk-base periods out of sample** — P1. Monthly is the
      current `crypt_ensemble` default, but `weekly` and `backtest` should be
      compared in donor walk-forward/Optuna work before treating sizing mode
      as calibrated.
- [x] **Retire or freeze `src/crypt/backtest/` after parity** — P1. Completed
      2026-06-04 by ADR-0023: the old root-native harness and
      `tests/backtest/` were removed after usage search found no live imports.

---

## P1 — high value, schedule into M2 milestone

### M2 — Backtest harness (replaces the old 3-bullet sketch)

Full spec: **`docs/backtest.md`** (must-read before starting).

- [x] **Backfill CLI** — `src/crypt/backfill/__main__.py` (2026-05-29).
- [x] **`ReplayParquetStore` look-ahead guard** — `src/crypt/backtest/replay.py`;
      8 tests in `tests/backtest/test_no_lookahead.py` (2026-05-29).
- [x] **`BacktestRecorder` + `BacktestExecutionSimulator`** —
      `src/crypt/backtest/{recorder,execution_sim,fee_model,risk_model}.py`
      with all §18.4 fixes (2026-05-29).
- [x] **Forward-label loader** — `src/crypt/backtest/labels.py` (2026-05-29).
- [x] **Fee + slippage model** — `docs/backtest.md` §7. Wired into `__main__.py` (2026-05-29).
- [x] **Walk-forward CV** — `src/crypt/backtest/walkforward.py` (2026-05-29).
- [x] **Weight optimiser** — `src/crypt/backtest/optimizer.py` (2026-05-29).
- [x] **Bootstrap CI** — `src/crypt/backtest/metrics.py` (2026-05-29).
- [x] **Baseline comparison** — `src/crypt/backtest/metrics.py` + `__main__.py` (2026-05-29).
- [x] **HTML report** — `src/crypt/backtest/report.py` (2026-05-29).
- [x] **`weights.recommended.yaml` writer** — `optimizer.py` + `__main__.py` (2026-05-29).
- [x] **`tests/backtest/*`** — labels, walkforward, metrics tests added (2026-05-29).
- [x] **Coinglass backfill spec + ADR-0015** — superseded by ADR-0016 (2026-06-01).
      Coinglass not needed; funding dropped; OI/LS from OKX native endpoints.
- [x] **Fix OI endpoint** — `src/crypt/exchange/okx.py`: replaced with
      direct `publicGetRubikStatContractsOpenInterestHistory` call (2026-06-01).
- [x] **Remove funding from `DerivativesEngine`** — weights OI 0.67 / LS 0.33;
      removed from `EvaluationContext`, `context.py`, `store.py`, backfill CLI,
      `replay.py`, `backtest/__main__.py` (2026-06-01).
- [x] **ADR-0017: OHLCV-only M2 calibration** — primary M2 backtest uses
      free OKX candles only; derivatives weight is `0` until deep OI/LS is
      proven useful (2026-06-01).
- [x] **SMC core analyser** — `docs/engines/smc_core.md`; deterministic
      Python implementation of pivots, BOS/CHoCH, order blocks, equal
      highs/lows, sweeps; first slice covers pivots + BOS/CHoCH with
      no-lookahead tests (2026-06-01).
- [x] **`smc_structure` engine** — `docs/engines/smc_structure.md`; first
      candle-only SMC directional engine (2026-06-01).
- [x] **`smc_order_blocks` engine** — `docs/engines/smc_order_blocks.md`;
      retest signal from active order-block zones.
- [x] **`smc_liquidity` engine** — `docs/engines/smc_liquidity.md`;
      equal high/low and swing-level sweep signal (2026-06-01).
- [x] **Fix optimizer score recomputation** — P0 before trusting M2
      calibration. Fixed 2026-06-01: recorder persists `strength_<engine>`
      columns and optimizer recomputes candidate score/decision/objective from
      them before accepting `weights.recommended.yaml`.
- [x] **Run OHLCV backfill + full backtest** — OKX candles only.
      SOL/TON report reviewed in ADR-0014 (2026-06-01); generated weights
      rejected by sanity guard.
- [x] **ADR-0014** — calibration result after M2 report is reviewed. Written
      2026-06-01; weights rejected, not accepted.
- [ ] **Flip `uncalibrated = False`** — only after a future calibration ADR
      accepts weights that pass the sanity guard.
- [ ] **Fix guarded-report artifact semantics** — P1. If any walk-forward
      fold fires the optimizer sanity guard, do not present
      `weights.recommended.yaml` as promotable and make `weights.candidate.yaml`
      clearly represent the aggregate non-promotable candidate rather than the
      last fold's weights.
- [ ] **Investigate weak long-side signals** — P1. ADR-0014 report review
      showed negative `h24` proxy expectancy on `SOL` BUY and `TON` BUY
      alerts; add a filter or context engine before the next calibration run.

### Engine specs that will follow M2 calibration

These engines have specs in `docs/engines/*` and are sequenced **after**
M2 produces calibrated weights for the existing 5 engines, so the new
engines are introduced one at a time with a fresh backtest each.

- [ ] **`btc_context` engine** — `docs/engines/btc_context.md`.
      Cheap; should land first.
- [ ] **`cross_symbol_confluence`** — `docs/engines/cross_symbol_confluence.md`.
      Pure meta-engine; no new data source needed.
- [ ] **`calendar` engine** — `docs/engines/calendar.md`. Manual
      `config/events.yaml`.
- [ ] **`liquidations` engine** — `docs/engines/liquidations.md`,
      ADR-0012. Default to Path B (Coinglass). Reuse `CoinglassClient`
      from ADR-0015 backfill work.
- [ ] **`sentiment` engine** — `docs/engines/sentiment.md`. After
      liquidations because the data pipeline pattern is shared.

### Decision-layer improvements

From `docs/post_m1_code_fixes.md`:

- [ ] **Anti-flip-flop guard** — `post_m1_code_fixes.md` §3.
- [ ] **`produced_at` vs wall-clock semantics + test** —
      `post_m1_code_fixes.md` §4.

### Operability

- [ ] **Telegram bot commands** — `docs/operations/telegram_commands.md`.
      `/status`, `/last`, `/explain`, `/health`, `/threshold`,
      `/pause`, `/resume`, `/help`. P1 because the operator currently
      has zero introspection on a live system.
- [ ] **Per-tick metrics jsonl** — `docs/operations/observability.md`
      Gap A. New `tick_metrics.jsonl` next to verdicts.jsonl.
- [ ] **Error webhook (loguru → Telegram)** — `docs/operations/observability.md`
      Gap B. Rate-limited to 1/60 s.
- [ ] **Engine telemetry log lines** — `docs/operations/observability.md`
      Gap C.
- [ ] **OKX instrumentation** — `docs/operations/observability.md`
      Gap D. Request counters + p95 latency in heartbeat.
- [ ] **Heartbeat enrichment** — `docs/operations/observability.md`
      Gap E. Memory, disk, alert counts.

### Type-safety / correctness

From `docs/post_m1_code_fixes.md`:

- [ ] **Property-based aggregator tests (Hypothesis)** —
      `post_m1_code_fixes.md` §5.
- [ ] **`InputKey` enum for `inputs_missing`** —
      `post_m1_code_fixes.md` §8.
- [ ] **Combined-multiplier cap in aggregator** —
      `post_m1_code_fixes.md` §7.
- [ ] **XPL bootstrapping classification** —
      `post_m1_code_fixes.md` §6.

### Documentation hygiene

- [ ] **Operator runbook in production** — `docs/operator.md`. Mostly
      written; verify against the post-14-day Telegram experience and
      refine the "red flags" section.
- [ ] **First post-mortem(s)** — use `docs/post_mortems/_template.md`
      for any incident during the run. Even no-incident-period gets a
      single "summary" post-mortem at end of run.
- [ ] **Pin `aiogram>=3.7`** in `pyproject.toml` + note that
      `DefaultBotProperties(parse_mode=...)` is required since 3.7
      (carried over from earlier P1 dep-hygiene item).

### Railway post-run hygiene

- [x] **Extract `data/*.parquet` and `data/logs/`** — done; files in `prod/`
      (2026-05-29).
- [ ] **Decide retention** — Pro plan if we ever want > 7 days of
      cloud-side logs. Currently logs are on the persistent volume so
      this is mostly cosmetic.
- [ ] **Stop / pause Railway service** — owner action; Parquet data already
      extracted to `prod/`.

### Product output: entry / SL / TP in Verdict

From session 5 discussion: the system's goal is to output a complete trade
setup (direction + entry + stop-loss + take-profit), not just BUY/SELL/HOLD.
Proposed design for M3+:

- **Entry price**: close of the H4 candle that triggered the signal.
- **SL**: `Entry − 1.5 × ATR14(H4)` for longs (reversed for shorts).
  ATR is already computed in `VolatilityEngine`; needs to be exported via
  `Signal.meta` or a new field.
- **TP**: `Entry + 2 × (Entry − SL)` — fixed 2:1 R:R (mechanical, per owner request).

Implementation tasks (post-M2 calibration):

- [ ] **Export ATR in `VolatilityEngine.meta`** — add `atr14_h4` to
      `Signal.meta` so the aggregator can use it.
- [ ] **Add `entry`, `sl`, `tp` to `Verdict`** — optional fields, populated
      when `decision != HOLD`. Aggregator computes from entry + ATR-based SL.
- [ ] **Update `TelegramSink`** — include entry/SL/TP in alert message.
- [ ] **Update `JsonlSink` + backtest recorder** — log new Verdict fields.

---

## P1 — M3 (paper trading) once M2 weights are calibrated

Full spec: **`docs/paper_trading.md`**.

- [ ] **`crypt/paper/ledger.py`** — JSONL ledger primitives.
- [ ] **`PaperLedgerSink`** — `docs/paper_trading.md` §3, §5.
- [ ] **Exit-check task** — `docs/paper_trading.md` §6.
- [ ] **`PaperLedgerSettings`** — `docs/paper_trading.md` §7.
- [ ] **Restart recovery** — `docs/paper_trading.md` §11.
- [ ] **Direction-flip handling** — `docs/paper_trading.md` §11.
- [ ] **`crypt/paper/report.py`** + HTML — `docs/paper_trading.md` §13.
- [ ] **Owner ledger via `/trade` / `/close`** — depends on Telegram
      commands shipping first.
- [ ] **Calibration curve** — `docs/paper_trading.md` §8. The output
      the owner cares about.
- [ ] **P&L attribution by engine** — `docs/paper_trading.md` §9.

---

## P2 — later / opportunistic

### Data layer

- [ ] **DuckDB-over-Parquet read helper** — for ad-hoc analysis in
      Jupyter. No code change to the live pipeline.
- [ ] **Universe rotation** — auto-pick top-N OKX SWAPs by volume.
      Needs an ADR because it breaks reproducibility between deploys.
- [ ] **Data quality monitor** — assert no gaps > `2 * timeframe`; auto
      repair when ingestion catches up.
- [ ] **Parquet partitioning by month** — when dataset crosses ~100 MB.

### Risk management (pre-M4)

- [ ] **Drawdown circuit breaker spec** — after N losses in paper
      ledger, send alert "strategy in drawdown".
- [ ] **Daily loss limit (info-only until M4)**.
- [ ] **Position sizing spec** — Kelly fraction, vol-targeting; before
      M4 is more than a stub.

### Engines further out

The product vision (session 5) is to aggregate **all** trader tools into one
verdict — indicators, structure, volume, price action — so the owner gets
in seconds what takes a trader hours to assemble manually.

Planned engine categories (post-M2, one at a time with fresh backtest each):

**Structural / level engines** (give price zones, feed future SL logic):
- [ ] **`support_resistance` engine** — classical S/R via pivot highs/lows
      on D1/H4. Lower priority now because ADR-0017 starts with SMC
      structure/order-block/liquidity engines.
- [ ] **`vwap` engine** — daily + weekly VWAP with ±1σ bands. Price position
      relative to VWAP as mean-reversion signal.
- [ ] **`volume_profile` engine** — POC, VAH, VAL from recent session volume.
      Requires tick-or-minute data; defer until data pipeline supports it.
- [ ] **`fibonacci` engine** — auto-drawn Fib retracements on the last
      significant swing. Defer until SMC core can provide reliable impulse
      legs; first use as confluence, not standalone direction.

**Volume / order-flow engines:**
- [ ] **`volume_delta` engine** — CVD (cumulative volume delta) / taker
      buy-sell volume imbalance. Directional pressure signal. Uses existing
      `taker_vol` data if backfilled.
- [ ] **`obv` engine** — On-Balance Volume trend confirmation.

**Price action / structure engines:**
- [x] **SMC specs** — `smc_core`, `smc_structure`, `smc_order_blocks`,
      `smc_liquidity` written for ADR-0017 (2026-06-01).
- [ ] **`fvg` engine** — Fair Value Gaps (imbalance candles). Defer until
      the PineScript `lookahead_on` MTF logic is rewritten safely.
- [ ] **`smc_premium_discount` engine** — premium/equilibrium/discount zones
      from the latest confirmed swing range. Defer until after first SMC report.

**Meta:**
- [ ] **ML meta-aggregator** — LightGBM on engine outputs. Decide
      after M3 paper trading shows reproducible expectancy.
- [ ] **Higher-frequency engine** (M15 or M5) — only if M3 data
      suggests sub-H4 information is being missed.

### Observability later

- [ ] **Sentry integration** — when the project scales beyond
      one operator. Until then, the error webhook in
      `docs/operations/observability.md` Gap B suffices.
- [ ] **Prometheus / OTLP exports** — once a metrics consumer exists.
- [ ] **Grafana dashboards** — depends on Prometheus.

### Operability later

- [ ] **Streamlit dashboard** — local-only browser UI over the
      JSONL/Parquet artefacts. Useful but adds maintenance.
- [ ] **`/event add ...` Telegram command** — manage
      `config/events.yaml` from chat.

### Deployment later

- [ ] **Docker compose** for an eventual self-hosted VPS deployment.
- [ ] **Railway Pro upgrade decision** — only if log retention > 7 d
      is needed mid-run.

---

## Known unknowns / things to verify before implementing

- **CryptoPanic free tier** — confirm endpoint + rate limit via
  Context7 before writing `docs/engines/sentiment.md` code. Spec
  describes the expected surface but APIs drift.
- **Coinglass freemium** — same. Confirm endpoints + rate limit before
  Path B in ADR-0012.
- **OKX REST liquidation endpoint** — ADR-0006 says WS-only as of MVP.
  Re-verify at implementation time; OKX has been known to add REST
  endpoints quietly.
- **OKX OI snapshot timing** — affects `derivatives` engine sensitivity;
  M2 should expose this in the report.
- **`pandas-ta` 0.4.x stability on Python 3.13+** — if we ever move off
  3.12, this stack may break (numba/llvmlite). Switching to plain
  `ta` is the fallback; would need an ADR.
- **`aiogram` 3.x release cadence** — they break minor APIs (e.g. the
  3.7.0 `Bot.__init__` change). Pin precisely.
