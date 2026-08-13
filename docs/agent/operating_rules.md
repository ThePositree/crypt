# Agent Operating Rules

This file holds the detailed rules that used to make `AGENTS.md` expensive to
load every session. Read it only when a task touches planning policy, docs/task
hygiene, incident response, dependencies, long-running commands, or live-money
operations.

## Owner Override And Benchmark

`docs/strategy_benchmark.md` is the main optimization target, not a hard
production gate. Agents should use it to report whether a strategy is strong,
weak, risky, or benchmark-quality.

If the owner chooses a benchmark-failing strategy for production:

- accept the selection as current direction;
- record known benchmark failures and money risks once;
- do not keep re-litigating the same objection;
- keep improving safety, reconciliation, and strategy quality from the active
  config.

## Planning

Plan locally. Do not ask the owner to create implementation plans. For
non-trivial work, keep the todo-list tool updated.

## Running Commands, Backtests, And Optimizers

Agents may run any in-scope command they need, including `backtester` and
optimizer commands, but long work must be controlled by visible progress:

- always set `UV_CACHE_DIR=/tmp/uv-cache` for `uv` commands so dependency cache
  writes stay sandbox-writable;
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

## Dependencies Before Custom Implementations

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

## Owner-Run Process Visibility

Owner-started processes may be outside the agent's PID namespace. A missing PID
from agent-side `ps`/`pgrep` does not prove the process stopped.

Use owner-pasted output, logs, artifact modification times, and owner-side
status commands to determine state.

## One-Off Commands

Do not persist one-off diagnostic CLIs or scripts. Use ephemeral shell commands
or existing project functions. Add a durable CLI only when the owner asks for a
reusable command, the workflow is recurring, or tests/automation need it.

## Task Documentation

`docs/tasks/IN_PROGRESS.md` must contain only active work. `BACKLOG.md` must
contain only unfinished queued work. Completed or historical material belongs
in `CHANGELOG.md`, `CHANGELOG_ARCHIVE.md`, or archive docs.

When adding active/backlog work, include:

- **What**
- **Why now**
- **Expected gain**
- **Acceptance**
- **Links**

Ideas in `docs/tasks/IDEAS.md` are reminders, not tasks. Do not implement,
spec, or move an idea to `BACKLOG.md` without explicit owner approval.

## Specs And ADRs

For any new engine, sink, execution component, or non-trivial module, update
the relevant spec under `docs/` before or alongside code. The spec must define
inputs, outputs, logic, edge cases, missing-data behavior, and audit fields.

Write a new ADR when a decision commits the project to a trade-off that future
agents could reasonably question or reverse. ADRs are append-only: supersede
old decisions instead of silently rewriting them.

## Data Availability

Never assume exchange/data availability. Missing data should degrade to neutral
signals, blocked entries, or explicit operator errors as appropriate; it must
not silently create false confidence.

For any process that requires historical candles before expensive work or live
order logic, check candle availability before starting the work. Research and
backtest CLIs should fail fast with an explicit `python -m crypt.backfill`
command covering the missing symbol/date range/timeframe family. Production
runtime must either auto-backfill through the configured bootstrap path or fail
fast from configuration/preflight.

## Backtester Regression Checks

When the owner asks whether the backtester is broken, use
`docs/backtester_regression.md` instead of reconstructing reference periods
from chat or old changelog entries. The canonical checks are the current
production v6 full replay plus live phases B and C.

## Flexible Sandbox Composition

Components should be configurable, default-off for experiments, mountable at
useful scopes, and auditable. See
`docs/architecture/flexible_sandbox.md`.
