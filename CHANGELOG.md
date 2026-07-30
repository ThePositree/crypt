# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

---

## 2026-07-30 — DSS v3 multi-timeframe search direction

- Added ADR-0062 for DSS v3 persistent multi-timeframe search while keeping the
  DSS name.
- Added `docs/discovery/direct_signal_search_v3.md` with the candidate model:
  trigger/filter instances are `name + timeframe + params`, repeated filter
  names are allowed across different timeframes, and exact duplicate instances
  are invalid.
- Specified shared random unseen/novelty injection for all DSS search backends.
- Clarified DSS v3 as Stage 1-only directional labeling: no DSS Stage 2/3
  backtests and no RRR/risk/TTL/ATR-stop/trailing/portfolio sizing fields in
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
  made `search-signals` default to Stage 1-only; and added frequency-class
  Stage 1 behavior/export reporting.
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
