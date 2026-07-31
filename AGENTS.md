# AGENTS.md — operating manual for AI agents

This repository is developed **AI-first**. The owner sets direction in chat;
agents own implementation planning, code, documentation, changelog entries,
and task files.

`crypt` is a research workbench for finding automated crypto perpetual
strategies plus a live execution module for the owner-selected strategy. The
old signal-only Telegram MVP is historical context, not the main product
framing.

The owner may promote any strategy to production, including strategies that do
not pass the benchmark. Treat that as a normal owner override: document the
evidence and risks once, then continue from the active runtime source of truth.

---

## 1. Read this at the start of every session

Read in this order:

1. `README.md` — public surface for humans and agents.
2. This file (`AGENTS.md`).
3. `docs/strategy_benchmark.md` — money benchmark and reporting target.
4. `docs/tasks/ROADMAP.md` — owner-defined milestones.
5. `docs/tasks/IN_PROGRESS.md` — active work only.
6. `docs/tasks/IDEAS.md` — owner ideas saved for later, not approved tasks.
7. `docs/tasks/BACKLOG.md` — queued unfinished work.
8. The recent entries in `CHANGELOG.md`; use `CHANGELOG_ARCHIVE.md` for older
   history.
9. Any ADR in `docs/decisions/` relevant to the task.

If docs and active runtime config disagree, stop and ask the owner. For live
execution, the runtime source of truth is the loaded config/env, especially
`EXECUTION_STRATEGY_CONFIG`, not a prose summary.

---

## 2. Project rules

### Owner override and benchmark

`docs/strategy_benchmark.md` is the main optimization target, not a hard
production gate. Agents should use it to report whether a strategy is strong,
weak, risky, or benchmark-quality.

If the owner chooses a benchmark-failing strategy for production:

- accept the selection as current direction;
- record known benchmark failures and money risks once;
- do not keep re-litigating the same objection;
- keep improving safety, reconciliation, and strategy quality from the active
  config.

### Planning

Plan locally. Do not ask the owner to create implementation plans. For
non-trivial work, keep the todo-list tool updated.

### Running commands, backtests, and optimizers

Agents may run any in-scope command they need, including `backtester` and
optimizer commands, but long work must be controlled by visible progress:

- always set `UV_CACHE_DIR=/tmp/uv-cache` for `uv` commands so dependency
  cache writes stay sandbox-writable;
- commands expected to take more than roughly one minute must show completed
  work, elapsed time, rate, and ETA;
- launch the command and immediately inspect progress/ETA;
- if ETA is `<= 3 minutes`, the agent may wait and inspect artifacts;
- if ETA is `> 3 minutes`, stop the command and give the owner the exact
  command, expected output path, and what to paste back;
- if there is no visible progress/ETA for a potentially long command, stop it
  and hand it to the owner;
- independent owner-run jobs should default to parallel commands when safe.

Do not let silent multi-hour jobs run inside the agent session.

### Dependencies before custom implementations

For any non-trivial code, prefer a maintained dependency over reimplementing
the same thing locally when that dependency materially reduces risk,
complexity, or maintenance cost. This applies broadly: algorithms, parsers,
serializers, file formats, protocols, exchange/API clients, optimizers,
statistics, ML, UI/runtime utilities, and infrastructure plumbing are examples,
not a closed list.

Before writing custom logic, search for an appropriate library, check current
docs, and add the dependency when it is a better engineering choice. Do not
avoid a dependency just to keep the dependency list short. Use local code only
when no suitable maintained package exists, the required behavior is
project-specific, or the dependency would create a clear operational risk.

### Owner-run process visibility

Owner-started processes may be outside the agent's PID namespace. A missing
PID from agent-side `ps`/`pgrep` does not prove the process stopped.

Use owner-pasted output, logs, artifact modification times, and owner-side
status commands to determine state.

### One-off commands

Do not persist one-off diagnostic CLIs or scripts. Use ephemeral shell commands
or existing project functions. Add a durable CLI only when the owner asks for a
reusable command, the workflow is recurring, or tests/automation need it.

### Task documentation

`docs/tasks/IN_PROGRESS.md` must contain only active work. `BACKLOG.md` must
contain only unfinished queued work. Completed or historical material belongs
in `CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, or archive docs.

When adding active/backlog work, include:

- **What**
- **Why now**
- **Expected gain**
- **Acceptance**
- **Links**

### Ideas

Ideas in `docs/tasks/IDEAS.md` are reminders, not tasks. Do not implement,
spec, or move an idea to `BACKLOG.md` without explicit owner approval.

### Specs before code

For any new engine, sink, execution component, or non-trivial module, update
the relevant spec under `docs/` before or alongside code. The spec must define
inputs, outputs, logic, edge cases, missing-data behavior, and audit fields.

### ADRs

Write a new ADR when a decision commits the project to a trade-off that future
agents could reasonably question or reverse. ADRs are append-only: supersede
old decisions instead of silently rewriting them.

### External libraries and APIs

Use Context7 before writing non-trivial code against external libraries or
APIs. If Context7 is unavailable, warn the owner and proceed cautiously.

### Data availability

Never assume exchange/data availability. Missing data should degrade to neutral
signals, blocked entries, or explicit operator errors as appropriate; it must
not silently create false confidence.

For any process that requires historical candles before expensive work or live
order logic, check candle availability before starting the work. Research and
backtest CLIs should fail fast with an explicit `python -m crypt.backfill`
command covering the missing symbol/date range/timeframe family. Production
runtime must never ask an interactive `y/n` question: it should either
auto-backfill through the configured bootstrap path or fail fast from
configuration/preflight.

---

## 3. Incident response

When the owner says "fix" or pastes errors, treat it as incident response:

1. Reproduce the failure or state why reproduction is impossible.
2. Isolate root cause before refactoring.
3. Apply the smallest fix that resolves the cause.
4. Add or update tests when the failure is a regression or logic bug.
5. Update docs/changelog/task files so the next agent is not blind.

If the fix changes public behavior, update the relevant spec or runbook.

---

## 4. End of every session

Before handing back:

1. Move completed active work out of `IN_PROGRESS.md`.
2. Keep `BACKLOG.md` limited to unfinished work.
3. Leave clear next steps in `IN_PROGRESS.md` if work remains.
4. Append a dated `CHANGELOG.md` entry.
5. Update `README.md` only when the public surface changes.
6. In final chat, state what remains, why it remains, and the next command or
   artifact the next agent should start from.

---

## 5. What the owner controls

- Final direction in chat.
- `docs/tasks/ROADMAP.md` substance. Agents may add a short current-reality
  note when approved, but should not silently rewrite milestones.
- Production selection of any strategy.
- Final yes/no on ADRs explicitly marked `status: proposed`.

---

## 6. What agents control

Everything else: file layout under `src/`, tests, lint/type config, internal
abstractions, docs under `docs/`, task files, archive notes, README, AGENTS,
and changelogs.

---

## 7. Operating principles

- Critical thinking over agreement.
- MVP-first; cut scope before adding optional systems.
- No look-ahead bias: indicators and features use closed candles only.
- Backtest and live behavior share the same pure decision code where possible.
- Flexible sandbox composition: components should be configurable, default-off
  for experiments, mountable at useful scopes, and auditable. See
  `docs/architecture/flexible_sandbox.md`.
- English in code and docs. Russian only in chat replies to the owner.
- Owner chat uses the language of money: dollars, percentages, months,
  drawdown, and what happens to a `$10,000` account.
