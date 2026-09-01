# AGENTS.md - AI bootstrap

This repository is developed AI-first. The owner sets direction in chat;
agents own implementation planning, code, documentation, changelog entries,
and task files.

`crypt` is a research workbench for automated crypto perpetual strategies plus
a live OKX execution module for the owner-selected strategy. The old
signal-only Telegram MVP is historical context, not the main product framing.

## Start Here

Read only this bootstrap first, then route the rest of the context through:

1. `docs/agent/context_routes.yml` - deterministic task-to-doc routing.
2. `docs/state/current.yml` - compact current state and production snapshot.
3. The full docs named by the selected route.

If docs and active runtime config disagree, stop and ask the owner. For live
execution, the runtime source of truth is the loaded config/env, especially
`EXECUTION_STRATEGY_CONFIG`, not a prose summary.

## Hard Rules

- English in code and docs. Russian only in chat replies to the owner.
- Critical thinking over agreement. MVP-first; cut scope before adding optional
  systems.
- No look-ahead bias: indicators and features use closed candles only.
- Backtest and live behavior share the same pure decision code where possible.
- The owner may promote any strategy to production, including
  benchmark-failing strategies. Document known evidence and risks once, then
  continue from the active runtime source of truth.
- `docs/strategy_benchmark.md` is the money benchmark and reporting target, not
  a hard production gate.
- Use `docs/backtester_regression.md` when checking whether the backtester is
  broken. Do not reconstruct phase A/B/C checkpoints from chat.
- For live money work, OKX/exchange state is the source of truth for fills,
  fees, positions, and account equity.
- Never assume exchange/data availability. Missing data must degrade to neutral
  signals, blocked entries, or explicit operator errors.
- Production runtime must never ask an interactive `y/n` question.
- Prefer maintained dependencies over custom implementations when they reduce
  real risk, complexity, or maintenance cost.
- Use Context7 before writing non-trivial code against external libraries or
  APIs. If unavailable, warn the owner and proceed cautiously.
- Always set `UV_CACHE_DIR=/tmp/uv-cache` for `uv` commands run by agents.
- Long commands must expose progress and ETA. If ETA is above 3 minutes or no
  progress is visible, stop and hand the exact command/artifact path to the
  owner.
- Do not persist one-off diagnostic CLIs or scripts unless the workflow is
  recurring or the owner asks for a reusable command.
- Keep `docs/tasks/IN_PROGRESS.md` active-only and `docs/tasks/BACKLOG.md`
  unfinished-only. Historical material belongs in changelog/archive docs.
- When adding durable knowledge, update `docs/agent/context_routes.yml`,
  `docs/state/current.yml`, or the context benchmark when the new fact affects
  routing, current state, live money, or backtester checkpoints.
- Write or update specs before or alongside new engines, sinks, execution
  components, or non-trivial modules.
- Write a new ADR for decisions that commit the project to a future-questioned
  trade-off. ADRs are append-only: supersede instead of silently rewriting.

## Incident Response

When the owner says "fix" or pastes errors:

1. Reproduce the failure or state why reproduction is impossible.
2. Isolate root cause before refactoring.
3. Apply the smallest fix that resolves the cause.
4. Add or update tests for regressions and logic bugs.
5. Update docs/changelog/task files so the next agent is not blind.

## End Of Session

Before handing back:

1. Move completed active work out of `IN_PROGRESS.md`.
2. Keep `BACKLOG.md` limited to unfinished work.
3. Leave clear next steps in `IN_PROGRESS.md` if work remains.
4. Append a dated `CHANGELOG.md` entry.
5. Update `README.md` only when the public surface changes.
6. In final chat, state what remains, why it remains, and the next command or
   artifact the next agent should start from.

## Ownership

The owner controls final direction in chat, `docs/tasks/ROADMAP.md` substance,
production strategy selection, and final yes/no on ADRs marked `proposed`.

Agents control implementation details, tests, internal docs, task files,
archive notes, README, AGENTS, and changelogs unless the owner says otherwise.

Detailed operating rules live in `docs/agent/operating_rules.md`.
