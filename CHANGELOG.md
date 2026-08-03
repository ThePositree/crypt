# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

---

## 2026-08-03 — Production v6 regression audit

- Re-ran and fixed the current production strategy regression for
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`
- Root cause: old promoted DSS donor JSONs carry legacy `atr_sl_mult`, but the
  new DSS v3 executable-stop fallback used only `directional_sl_move_pct=0.004`.
  That made old production stops roughly half as wide and broke exit timing.
- Restored legacy DSS stop semantics: `dss_strategy` and `dss_incremental` now
  use `atr_sl_mult` when present, falling back to `directional_sl_move_pct` only
  for newer directional-only candidates.
- Added internal backtest/optimizer warmup loading: `--from/--to` remain the
  execution/reporting window, while crypt-parquet candle loading starts 30 days
  earlier for indicator context. Exported `ohlcv.csv` is trimmed back to the
  execution window.
- Phase B live/backtest reconciliation is restored on current code/data:
  `17` rows, `16/1` closed/open, exit distribution
  `10 stop_loss / 4 take_profit / 2 ttl_expired / 1 open`, closed PnL
  `-$0.85356390` versus archived `-$0.84001035`.
- Full archived-period v6 no longer shows the regression loss. Current repaired
  local data gives `$1,194,926.04` final capital, `11849.26%` return, `1544`
  trades, and `1.37` profit factor; the archived snapshot remains
  `$1,098,402.88`, `10884.03%`, `1515` trades, and `1.48` profit factor.
- Fixed a discovery dataset regression where callers that explicitly supplied
  an execution OHLCV frame no longer passed the remaining candle frames as
  H4/D1 context features.
- Fixed DSS matrix report refresh crashes on large `signal_identity_keys`
  CSV fields by raising the Python CSV field-size limit before reading DSS
  viability/ranked files. Verified a bounded all-backend matrix smoke.

## 2026-08-03 — DSS v3 audit fixes

- Fixed `search-signals` multi-symbol execution so repeated `--symbol` values
  produce distinct symbol-scoped windows instead of silently scanning only the
  first symbol.
- Made DSS signal-overlap novelty durable across resume/migrated journals by
  persisting and restoring `signal_identity_keys` from viability rows.
- Changed Island-QD and Hyperband-QD feedback loops to train on rejected and
  duplicate candidates, not only promoted candidates.
- Made adaptive backend `random_unseen` injections use an independent random
  DSS candidate sampler instead of only relabeling model proposals.
- Kept DSS missing-candle backfill hints owner-facing by removing agent-only
  `MPLCONFIGDIR` / `UV_CACHE_DIR` env prefixes from generated commands.

## 2026-08-03 — Default Optuna exit-family search

- Changed `backtester optimize` defaults into a post-DSS geometry search:
  one run now searches `exit_family`, `rrr`, `position_ttl_minutes`,
  `risk_percent`, `trail_distance_atr` for trailing exits, and `tp_move_pct`
  for TP-percent exits while keeping strategy parameter search disabled.
- Set default optimizer ranges to `rrr=1..10`, `risk_percent=0.25..3.0`,
  `position_ttl_minutes=60..10080`, `trail_distance_atr=0.5..10`, and
  `tp_move_pct=0.004..0.14`.
- Added `best_geometry_summary.txt` beside `best_trial.json` so the winning
  exit family and money parameters are readable without raw Optuna parsing.

## 2026-08-03 — TTL minutes source of truth

- Moved backtester/Optuna TTL search to `position_ttl_minutes`; simulator
  `position_ttl_bars` is now derived from the strategy execution timeframe.
- Updated DSS v3 exports so TTL is only a runnable downstream default
  (`position_ttl_minutes=720`), not a DSS search/evaluation parameter.
- Updated live execution TTL handling to expire by wall-clock minutes and
  migrate legacy open-position state from hour-like `ttl_bars` values to
  minute values.
- Updated owner CLI docs to prefer `--ttl-minutes*` overrides and keep old
  bar-based `--ttl*` flags as legacy reproduction inputs.

## 2026-08-03 — DSS signal-overlap novelty guard

- Fixed DSS backend novelty handling so promoted candidates are checked before
  viability rows are written, preventing duplicate signal sets from remaining
  exportable.
- Added signal identity keys to directional metadata and reject high-overlap
  promoted signal sets as `duplicate_signal_set`, not only exact fingerprint
  duplicates.
- Updated CatCMA-QD, Hyperband-QD, Island-QD, SMAC-QD, and directional search
  loops to use the shared pre-write novelty decision.

## 2026-08-03 — Backtester CLI surface pruning

- Removed dead owner-facing `backtester` Click commands from the product
  surface. The remaining backtester commands are only `run`, `optimize`,
  `search-signals`, and `search-signals-matrix`.
- Kept `python -m crypt` and `python -m crypt.backfill` as runtime/data module
  entrypoints.
- Removed obsolete help tests for the deleted commands and updated DSS reports
  to point validation toward `backtester run` / `backtester optimize`.
- Updated `docs/cli.md` with the complete current command list.

## 2026-08-03 — Compact owner CLI defaults

- Simplified owner-facing `backtester run`, `backtester optimize`,
  `search-signals`, and `search-signals-matrix` defaults: `data/`,
  `SOL-USDT-SWAP`, full available history, and `$10,000` capital are now the
  normal path.
- Hid rarely used technical flags from the main Click help while keeping them
  accepted for advanced/reproduction cases.
- Changed default Optuna trials from smoke-sized `25` to `50,000`.
- Added `full` / `all` aliases for omitted crypt-parquet date bounds.
- Added `docs/cli.md` as the compact command runbook and updated README/archive
  reproduction commands away from old manual timeframe/data-source flags.
- Replaced obsolete active DSS v2/PineScript multi-step wording with current
  DSS v3 directional search references.

## 2026-08-03 — DSS v3 endless runtime fixes

- Removed the old privileged timeframe semantics from the backtester/DSS/live
  code path: `StrategyData` now carries `candles_by_timeframe`, components use
  explicit timeframe accessors, and crypt-parquet loads all candle channels as
  equal bundle entries.
- Renamed discovery datasets from `primary` to `ohlcv` and migrated DSS
  feature builders, signal composer alignment, directional evaluation,
  backtester runners, optimizer/walk-forward adapters, live signal runner, and
  focused tests off `.primary` access.
- Updated the timeframe cleanup backlog: the remaining hard migration
  is the runner-selected `execution_timeframe`/`execution_frame()` surface, not
  the old privileged-frame contract.
- Removed the runner-selected `StrategyData.execution_frame()` surface:
  backtester, optimizer, walk-forward, fixed-candidate reports, regime matrix,
  DSS objective, and live signal generation now receive an explicit OHLCV
  frame from their caller or require a component-owned timeframe.
- Renamed the public crypt-parquet runner option to `--candle-timeframe`; it is
  now a CLI input-frame selector and is no longer stored in `StrategyData`
  metadata.
- Fixed DSS runtime progress so refreshed endless reports preserve the last
  exported candidate count instead of resetting `exported` to zero on regular
  per-candidate progress writes.
- Fixed directional candidate export to replace stale
  `directional_candidates/directional_*.json` files when the ranked top set
  changes, keeping the export directory aligned with the current shortlist.
- Fixed the default directional endless generator so adjacent batches no longer
  reuse the same batch-local RNG stream and stop after duplicate-only batches.
- Capped SMAC-QD surrogate training to the latest 5,000 observations and added
  a 512-evaluation refit cadence so resumed endless searches do not spend
  hours refitting the random forest on the full journal before updating
  progress.
- Updated `/tmp/dss_snapshot.py` to show stale backends and count exported
  candidate JSONs when older progress files under-report exports.
- Added DSS directional `signal_fingerprint`/`signal_set_size` audit fields and
  made directional candidate export deduplicate shortlist entries by exact
  `(window, bar_time, side)` signal sets, preventing multiple promoted JSONs
  for candidates that would enter the market at the same times.
- Added `/tmp/dss_candidate_audit.py` for top-candidate clone checks; it reports
  exact config clones, exact money-vector clones, repeated trigger/filter
  families, and optional recomputed signal timestamp overlap.
- Added backend-level DSS signal novelty tracking: directional, CatCMA-QD,
  Island-QD, Hyperband-QD, and SMAC-QD now distinguish new promoted signal sets
  from promoted clones, avoid using cloned signal sets as novelty parents or
  survivor increments, and feed duplicate promoted signals back to model-based
  backends as negative examples.
- Rebalanced DSS directional scoring/export toward active viable strategies:
  sparse candidates remain eligible, but medium/frequent candidates now receive
  stronger ranking and backend-feedback preference, and shortlist export
  round-robins `frequent -> medium -> sparse` instead of filling from sparse
  first. `/tmp/dss_snapshot.py` now shows the `freq` bucket explicitly.
- Added default execution geometry for DSS v3 directional candidates:
  exported JSONs now include `rrr=2.0`, `risk_percent=1.0`,
  `position_ttl_minutes=720`, and `directional_sl_move_pct`; `DSSStrategy`
  backfills missing/invalid directional stops from the next open with that
  percentage so old directional-only candidates can run through the regular
  backtester/optimizer.
- Removed manual candle-timeframe selection from `backtester run` and
  `backtester optimize`: both commands now derive the replay OHLCV timeframe
  from DSS candidate trigger metadata and pass that exact frame into the
  simulator/optimizer, preventing accidental mixed-timeframe replays.
- Added `--algorithms all` as the default DSS matrix backend selector and
  verified a bounded all-backend matrix smoke.
- Fixed DSS bounded-run artifacts so `progress.json` is finalized to
  `stopped`/`failed` instead of staying `running` after process exit.
- Added `trigger_timeframe` and `filter_timeframes` columns to
  `directional_viability.csv` so matrix/snapshot audits can inspect timeframe
  behavior without opening candidate JSONs.
- Moved strategy candle-timeframe resolution into shared CLI runner helpers and
  updated live signal generation to use the strategy-owned execution timeframe
  for candle freshness, loader selection, ATR context, and next-open tracking.

## 2026-07-31 — AI-first project template artifact

- Added `ai-first-project-template/` as a temporary in-repo starter kit for
  new AI-first projects.
- Included a one-time `.bootstrap/FIRST_RUN.md` marker and `AGENTS.md`
  bootstrap flow where the first agent asks only for a free-form project
  description, then fills product/task/architecture docs and removes the
  bootstrap instructions.
- Added portable docs for product brief, vision, requirements, architecture,
  roadmap, active work, backlog, ideas, ADRs, and reusable task/spec/bug
  templates.

## 2026-07-31 — DSS v3 audit hardening

- Added DSS preflight validation for all trigger/filter candle timeframes so
  missing `15m`/`1h`/`4h`/`1d` data fails before candidate search starts and
  prints a non-interactive `crypt.backfill` command for the needed symbol/date
  range.
- Added the same candle preflight to `search-signals-matrix` before child
  processes are spawned, so a missing timeframe now fails the matrix launcher
  before any backend starts.
- Lowered the default DSS directional barrier win-rate gate from `0.55` to
  `0.45` so endless search keeps more candidates for later money-like
  inspection instead of rejecting them too early.
- Extended `python -m crypt.backfill --data-types ohlcv` to fetch `15m`
  candles alongside `1h`/`4h`/`1d`, making DSS v3's 15m search space
  backfillable through the existing API.
- Documented the project-wide missing-candle contract: research CLIs fail fast
  with backfill commands, while production runtime uses env-driven auto-backfill
  or fail-fast preflight and never waits for `y/n`.
- Added the same backfill hint to the shared crypt-parquet data loader when
  required H4 or selected primary candles are empty, covering non-DSS
  backtester commands that use project candle storage.
- Fixed historical OHLCV backfill/REST repair so H1 writes are not blocked by
  strict aggregation mismatches against existing 1m execution candles; the
  H1-vs-1m invariant remains enabled by default for normal store writes.
- Replaced the old local weighted sampler with the maintained
  `cmaes.CatCMAwM` mixed-variable optimizer in `catcma_qd`, including
  continuous/integer/categorical DSS encoding, full-population ask/tell
  updates, and backend state probabilities.
- Added `cmaes>=0.13.0` and recorded a general agent rule to prefer maintained
  dependencies over custom implementations for any non-trivial code when they
  reduce risk or maintenance cost.
- Audited `search-signals-matrix` after DSS v3, fixed crypt-parquet empty
  timeframe frames so all five child backends can launch against v3 candle
  loading, and added a regression test that the matrix launcher passes current
  DSS options to child `search-signals` processes.
- Changed `search-signals-matrix --min-signals-per-week` default from `4.0` to
  `0.0` so default matrix runs can preserve sparse candidates instead of
  silently biasing all backends toward frequent signal families.
- Changed `search-signals-matrix --n-trials` to optional and made omitted
  `--n-trials` the default endless per-backend mode, matching the primary DSS
  workflow for journal migration across machines.
- Fixed `search-signals` endless CLI startup so omitted `--n-trials` no longer
  creates a bounded click progress bar with `length=None`; endless runs now use
  runtime `progress.json`/`heartbeat.json` files for progress tracking.
- Added a P1 backlog item to remove `primary` timeframe semantics across the
  project and treat concrete triggers/filters as explicit timeframe-contract
  components.
- Fixed crypt-parquet DSS windowing so `15m`, `H1`, `H4`, and `D1` candle
  frames are all clipped to the requested start/end range before search sees
  them.
- Fixed directional labeling to evaluate signal counts, overtrading,
  minimum-count gates, window duration, and barrier outcomes on the configured
  trigger timeframe instead of the run primary frame.
- Added conservative catalog timeframe eligibility for CLI search-space
  expansion so blocks are no longer blindly emitted on every timeframe.
- Changed `--n-trials` semantics to count unique evaluated candidates;
  duplicate hashes are journaled without consuming callback/evaluated budget,
  and exhausted search spaces exit instead of spinning.
- Made endless QD runs refresh directional ranked/export/archive reports after
  each completed batch.
- Removed active-run artifact migration from old names; DSS v3 now reads and
  writes only current `candidates.jsonl`/`directional_*` artifact names.
- Changed SMAC-QD observation fidelity labels from old wording to
  `directional_reject` and `directional_pass`.
- Made DSS search spaces expand catalog blocks into concrete `name@timeframe`
  instances for `15m`, `H1`, `H4`, and `D1`, so CLI searches now explore
  trigger/filter timeframe layouts instead of defaulting to H1.
- Updated directional, CatCMA-QD, Island-QD, Hyperband-QD, and SMAC-QD candidate
  generation, mutation, and surrogate encoding to sample and learn
  timeframe-aware trigger/filter instances while keeping param bounds on base
  catalog names.
- Fixed coarser-timeframe filter alignment to shift source candles to inferred
  close time before as-of joins, preventing lower-timeframe events from reading
  unfinished H4/D1 candles.
- Updated `SignalComposer` to pass filter-local event metadata from each
  aligned filter dataset, so existing metadata-based filters now actually use
  their configured timeframe.
- Hardened persistent runtime behavior: stale dead-PID locks are removed,
  failed runs write a failed heartbeat, and resumed summaries restore evaluated
  and survivor counts from existing directional reports.
- Fixed resume so candidates already recorded in `candidates.jsonl` but missing
  from `directional_viability.csv` are evaluated before new generation across
  directional, CatCMA-QD, Island-QD, Hyperband-QD, and SMAC-QD backends.
- Fixed resumed directional progress callbacks to account for already evaluated
  rows, and kept QD resume summaries on the actual candidate count even when a
  resumed output already contains more candidates than the current budget.
- Renamed active DSS v3 output artifacts to directional names:
  `candidates.jsonl`, `directional_viability.csv`,
  `directional_ranked.csv`, `directional_candidates/`,
  `backend_state/*.csv`, and `archive/directional_frequency_archive.csv`.
- Renamed the active search module/API/config away from old DSS naming:
  `dss_directional_search`, `DSSDirectionalResult`,
  `run_dss_directional_search`, and `--algorithm directional`.
- Removed remaining old-worded options from active `search-signals` and
  `search-signals-matrix` CLI/docs surface; `--directional-min-wr` is the
  supported win-rate gate.
- Added regression coverage for real timeframe instance generation and
  closed-candle as-of alignment.
- Verification: `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/backtester/test_dss.py -q`;
  `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run mypy src/backtester/strategy_discovery`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check` on changed DSS files.

## 2026-07-31 — DSS v3 persistent directional search completed

- Added timeframe-aware DSS trigger/filter instance serialization and stable
  hashes: `trigger_timeframe`, `filter_timeframes`, and `name@timeframe`
  labels are now part of candidate identity.
- Repeated filter names are allowed when timeframe or params differ; exact
  duplicate filter instances are rejected.
- Updated `SignalComposer` to resolve instance labels back to catalog block
  names while preserving timeframe labels in signal rationales, selecting the
  requested timeframe from `StrategyData`, as-of aligning filter datasets to
  trigger events, and caching `(data, timeframe, window, symbol)` features
  across candidates.
- Added `DSSSearchRuntime` with single-writer output locks,
  `candidate_journal.jsonl`, `seen_candidates.jsonl`, `progress.json`,
  `heartbeat.json`, `backend_state/`, and `archive/` directories.
- `search-signals --n-trials` is now optional: omitted means endless resumable
  search, provided means a bounded run.
- CatCMA, Hyperband, Island, SMAC, and the default runner now use the shared
  seen registry/journal/progress path and skip exact duplicate candidate hashes.
- Adaptive backends periodically inject random-unseen candidates and mutate
  directional survivors as novelty candidates.
- Added crypt-parquet `15m` candle loading and exposed `15m` as a DSS primary
  timeframe; missing unavailable timeframes fail explicitly instead of falling
  back silently.
- Removed active SMAC/package imports of legacy `dss_objective`, isolating the
  old Optuna/backtest helper from the DSS v3 search path.
- Reworded active DSS v3 summaries, manifests, spec, ADR, and task text around
  directional labeling instead of directional search wording.
- Removed the completed DSS v3 implementation task from active/backlog task
  files.
- Added regression coverage for timeframe-aware hashing, duplicate instance
  rejection, multi-timeframe as-of alignment, and durable runtime artifacts.
- Verification: `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/backtester/test_dss.py -q`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run mypy` on changed active DSS files;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check` on changed DSS files.

## 2026-07-30 — DSS v3 multi-timeframe search direction

- Added ADR-0062 for DSS v3 persistent multi-timeframe search while keeping the
  DSS name.
- Added `docs/discovery/direct_signal_search_v3.md` with the candidate model:
  trigger/filter instances are `name + timeframe + params`, repeated filter
  names are allowed across different timeframes, and exact duplicate instances
  are invalid.
- Specified shared random unseen/novelty injection for all DSS search backends.
- Clarified DSS v3 as directional-labeling-only: no replay backtests and no
  RRR/risk/TTL/ATR-stop/trailing/portfolio sizing fields in
  DSS candidates.
- Added DSS v3 frequency-class requirements so sparse and frequent candidates
  can be discovered and archived in the same search run, with independent
  archive/export quotas rather than a single global frequency floor.
- Recorded that DSS v3 may break DSS v2 candidate/state/journal/export
  compatibility; old DSS v2 artifacts are historical only.
- Specified endless `search-signals` mode when `--n-trials` is omitted, with
  resumable journals, seen registry, backend state, archive checkpoints,
  heartbeat/progress files, and live-execution isolation.
- Started the first implementation slice: removed DSS geometry fields from
  `TrialConfig`, `DSSCandidate`, and `DSSSearchSpace`; changed
  `SignalComposer` output to neutral SL/TP placeholders for directional rows;
  made `search-signals` default to directional labeling; and added
  frequency-class directional behavior/export reporting.
- Converted CatCMA, SMAC, island, and hyperband QD runners to active
  directional behavior: no replay scoring files are read or written, and local
  search models are updated from directional scores.
- Removed legacy replay runner entrypoints from the DSS directional search runner
  (`legacy replay scoring helpers`) so new DSS search code
  cannot import them accidentally.
- Added a P1 backlog task to implement DSS v3.
- ADRs: ADR-0062.
- Verification: `PYTHONPATH=src uv run pytest tests/backtester/test_dss.py -q`;
  `uv run ruff check` on the touched DSS files.
- Files touched: `src/backtester/strategy_discovery/`, `src/backtester/__main__.py`,
  `tests/backtester/test_dss.py`, `docs/discovery/`, `docs/decisions/`,
  `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-30 — Documentation reframed as research workbench + live execution

- Rewrote `README.md` as a shorter human-facing product surface: research
  workbench plus live execution module.
- Replaced `docs/investment_mandate.md` with `docs/strategy_benchmark.md`.
  The benchmark is now documented as an optimization/reporting target, while
  owner production promotion can override it.
- Rewrote `AGENTS.md` around the current project model, owner override rule,
  active runtime config source of truth, and ETA-controlled command policy.
- Added a current-reality note to `docs/tasks/ROADMAP.md` without rewriting
  owner-defined milestones.
- Cleaned `docs/tasks/IN_PROGRESS.md` down to active work only.
- Cleaned `docs/tasks/BACKLOG.md` down to unfinished queued work only.
- Removed the long historical `docs/tasks/DONE.md`; completed work now belongs
  in changelogs, archives, and ADRs.
- Updated distant-TP docs with the current owner-selected narrow v6 mount.
- Moved the previous long changelog to `CHANGELOG_ARCHIVE.md`.
- Removed `.cursor/rules/` because AGENTS is now the repository operating
  manual.
- ADRs: none.
- Files touched: root docs, `docs/tasks/`, `docs/backtester/`,
  `docs/archive/`, `docs/decisions/`, `.cursor/`.

## 2026-07-29 — Distant-TP component and v6 portfolio review

- Added signal-event exports and distant-TP diagnostics/audit fields.
- Added optional causal dynamic TP policy shared by backtest and live execution.
- Established flexible sandbox composition in ADR-0061 and docs.
- Tested global and targeted TP policies; only the narrow
  `freq_4pw_r03_catcma_011465` 6%/RRR-3 mount had positive evidence.
- Owner selected the narrow v6 mount for production; it remains intentionally
  narrow and should not be widened without longer forward evidence.

## 2026-07-28 — Live execution hardening and reconciliation audit

- Added durable monthly risk-base checkpoints and safer state recovery.
- Reworked Telegram execution notifications in Russian.
- Started live/backtest reconciliation for the July 2026 SOL live period.
- Identified the need for exact live entry replay snapshots and stronger
  Railway state/volume safety checks.
