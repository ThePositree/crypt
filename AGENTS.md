# AGENTS.md — operating manual for AI agents

This repository is developed **AI-first**. The human owner sets global
direction in chat. Everything else — implementation plans, file layout under
`src/`, documentation, changelogs, task tracking — is owned by agents.

The owner does **not** maintain any markdown file directly. If the owner wants
to change direction or correct course, they will say so in chat, and the
acting agent is responsible for propagating that into the relevant docs.

---

## 1. Read this at the start of every session

Read in this order, fully:

1. `README.md` — current public surface.
2. This file (`AGENTS.md`).
3. `.cursor/rules/` (rules are also auto-applied, but read them so you know
   what you have committed to).
4. `docs/tasks/ROADMAP.md` — global milestones (owner-defined).
5. `docs/tasks/IN_PROGRESS.md` — what the previous agent was doing. If it is
   non-empty and not yours, assume the previous session was interrupted and
   continue from where it left off, unless the owner says otherwise.
6. `docs/tasks/BACKLOG.md` — what is queued next.
7. The 2 most recent entries in `CHANGELOG.md`.
8. Any ADR in `docs/decisions/` whose subject is relevant to the task.

If any of these files contradict each other, stop and ask the owner.

---

## 2. During the session

### Plan locally, do not ask the owner to plan

The owner intentionally does not write implementation plans. You build the
local task plan yourself. If the task is non-trivial, use the todo-list tool
and keep it updated as you go.

### Write the spec before the code

For any new engine, sink, or non-trivial module, **first** create or update
the spec in `docs/engines/<name>.md` (or `docs/<feature>.md`). The spec
contains: inputs, outputs (the `Signal` payload), logic, thresholds, edge
cases, what data is required and what happens when data is missing.

Only then write the code. The spec is the contract.

### Record architectural choices as ADRs

Whenever you make a decision that future agents could reasonably reverse or
question (library choice, data source, design pattern, threshold rule, etc.),
add a new ADR in `docs/decisions/NNNN-short-title.md`. Use the existing
ADRs as a template. ADRs are append-only — to change a decision, write a new
ADR that supersedes the old one and update the old one's status.

### Use Context7 (MCP) before writing any library- or API-related code

The owner's rule: always resolve library docs via the `user-context7` MCP
before generating non-trivial code that touches an external library or API.
If Context7 is unavailable for some reason, **explicitly warn the owner in
chat** and proceed with caution.

### Never assume data is available

OKX is the primary exchange, but some endpoints may be missing, rate-limited,
or temporarily down. Engines must degrade gracefully: missing data ⇒ the
engine emits `neutral` with reduced confidence, never raises into the pipeline.

---

## 3. End of every session

Before handing back to the owner, do **all** of:

1. Move every item you completed from `docs/tasks/IN_PROGRESS.md` to the top
   of `docs/tasks/DONE.md` with the date.
2. Update `docs/tasks/BACKLOG.md` with any new items you discovered. Mark
   priority (`P0` blocker / `P1` important / `P2` nice-to-have).
3. If you are leaving work unfinished, leave a clear "next steps" block at
   the top of `docs/tasks/IN_PROGRESS.md` for the next agent.
4. Append an entry to `CHANGELOG.md` — date (`YYYY-MM-DD`), short summary,
   list of ADRs touched, list of files touched at directory level.
5. If the public surface changed (run command, env vars, dependencies,
   feature flags), update `README.md`.

---

## 4. What the owner controls

- The contents of `docs/tasks/ROADMAP.md` (you may *suggest* edits in chat
  but do not silently rewrite it).
- Final yes/no on ADRs explicitly marked `status: proposed` and flagged for
  owner review.
- Anything the owner asks you to do in chat trumps these defaults.

## 5. What agents control

Everything else: file layout under `src/`, dependencies, internal
abstractions, tests, lint config, infra, and the contents of every doc
under `docs/` except `ROADMAP.md`.

---

## 6. Operating principles

- **Critical thinking over agreement.** Ensemble trading systems break in
  subtle ways. If you spot a flaw in a previous decision or in the owner's
  ask, say so — don't politely paper over it.
- **MVP-first.** Prefer cutting scope over building optional features.
- **Tests for every engine.** Synthetic-data unit tests are mandatory; the
  ensemble result is meaningless if any individual engine is wrong.
- **No look-ahead bias.** Indicators are always computed on **closed**
  candles. Backtest and live pipelines must share the same code path.
- **English in code & docs. Russian only in chat replies to the owner.**
