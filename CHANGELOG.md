# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

---

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
