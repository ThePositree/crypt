# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

---

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
