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
4. `docs/investment_mandate.md` — owner economic targets and candidate
   promote/archive/discard gates (ADR-0025). **Mandatory** before any
   strategy search, optimizer run, or promotion decision.
5. `docs/tasks/ROADMAP.md` — global milestones (owner-defined).
6. `docs/tasks/IN_PROGRESS.md` — what the previous agent was doing. If it is
   non-empty and not yours, assume the previous session was interrupted and
   continue from where it left off, unless the owner says otherwise.
7. `docs/tasks/IDEAS.md` — owner ideas saved for later. These are not
   approved tasks unless moved into the mandate or `BACKLOG.md`.
8. `docs/tasks/BACKLOG.md` — what is queued next.
9. The 2 most recent entries in `CHANGELOG.md`.
10. Any ADR in `docs/decisions/` whose subject is relevant to the task
    (including ADR-0025 when evaluating candidates).

If any of these files contradict each other, stop and ask the owner.

---

## 2. During the session

### Plan locally, do not ask the owner to plan

The owner intentionally does not write implementation plans. You build the
local task plan yourself. If the task is non-trivial, use the todo-list tool
and keep it updated as you go.

### Owner-run backtests

Backtests and optimizer runs are owner-run by default. When the next useful
step requires a `backtester` command, agents must give the owner the exact
command to run, explain the expected artifact path or output files, and then
wait for the owner to return with the result. Do **not** run repository
backtests, `compare-fixed`, `compare-grid`, `signal-quality`, or optimizer
commands yourself unless the owner explicitly asks you to run that specific
command in chat.

### Document task intent, not only task mechanics

Task files must explain the work broadly enough that the next agent can
understand why the item exists without reconstructing the whole prior session.
When adding or rewriting a task in `BACKLOG.md`, `IN_PROGRESS.md`, or
`DONE.md`, include:

- **What:** the concrete change or investigation.
- **Why now:** the evidence, failure, owner request, or previous result that
  created the task.
- **Expected gain:** what the project wins if the task is completed.
- **Acceptance:** the observable output, command, report, test, or decision
  that proves the task is done.
- **Links:** relevant docs, ADRs, commands, or artifact paths when available.

At the start of a session, after reading the required files and choosing the
task or task chain, briefly tell the owner what you are taking, why it exists,
what it should give us, and how you will know it is done. If you take multiple
linked tasks, explain the dependency between them.

### Preserve owner ideas for later

The owner may explicitly say that something is an idea for later / "прозапас"
and not for implementation now. Record those ideas in
`docs/tasks/IDEAS.md`, not in `BACKLOG.md`, unless the owner explicitly
approves turning the idea into work.

Ideas in `IDEAS.md` are reminders, not tasks. Agents must:

- read `IDEAS.md` at session start;
- briefly remind the owner about relevant saved ideas when they fit the
  current work;
- say whether the timing looks good now or whether the idea should wait;
- ask for explicit owner approval before writing a spec, moving the idea to
  `BACKLOG.md`, or implementing code.

Agents must not implement saved ideas just because they are relevant.

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

### When the owner says "fix" / pastes errors (not "continue")

Chat instructions **override** stale assumptions from `IN_PROGRESS.md`. If the
owner opens a fresh session with logs, tracebacks, CI output, or "this broke",
treat it as **incident response**, not necessarily "resume the last bullet list".

**Goal:** reproduce → isolate root cause → minimal fix + tests → document so
the next agent is not blind.

1. **Classify the signal**
   - Build / lint / typecheck / unit test failure → run the same commands
     locally (or infer the CI job from the pasted log).
   - Runtime / deploy / exchange / infra → read any doc the error references
     (e.g. `docs/deploy/*.md`), then reproduce or state why you cannot.

2. **Reproduce before refactoring**
   - Prefer one failing command with a stable exit code over guessing.
   - If reproduction needs secrets or a host you do not have, say so in chat
     and record what is missing in `IN_PROGRESS.md` (owner-facing "blocked on
     …").

3. **Fix**
   - Smallest change that fixes the root cause; add or adjust tests when the
     failure was a regression or logic bug.
   - If the fix changes a public contract (CLI, env vars, engine behaviour),
     update the relevant spec under `docs/` first or in the same change set.

4. **Architectural or policy-changing fixes**
   - If the fix commits the project to a new trade-off (library, threshold,
     fallback exchange, deploy shape), add or supersede an ADR — same rule as
     normal development.

**Which markdown to touch (checklist)**

| Situation                                                      | Update                                                                                     |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Any completed fix worth a paper trail                          | `CHANGELOG.md` (dated; say what broke and how it was fixed).                               |
| You fixed something but another agent should verify / deploy   | Top of `docs/tasks/IN_PROGRESS.md` — short **next steps** + link to failing command or PR. |
| The fix closes a task line item                                | Move that item to `docs/tasks/DONE.md` with the date.                                      |
| You discovered follow-up risk (flaky test, missing monitoring) | `docs/tasks/BACKLOG.md` with `P0`/`P1`/`P2`.                                               |
| Behaviour or operator steps changed                            | Spec under `docs/` or `README.md` if commands / env / flags changed.                       |
| Owner-facing deploy or ops behaviour changed                   | Relevant file under `docs/deploy/` or feature doc.                                         |

**"Continue" vs "fix"**

- **Continue:** default when `IN_PROGRESS.md` describes unfinished work and the
  owner did not paste a new failure — pick up from **next steps** there.
- **Fix:** owner-supplied errors take priority; after the fix, reconcile
  `IN_PROGRESS.md` (remove obsolete next steps, or add new ones if still open).

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
6. In the final chat reply, read the next step back to the owner explicitly:
   what remains, why it remains, what it should give the project, and which
   command or artifact the next agent should start from.

---

## 4. What the owner controls

- The contents of `docs/tasks/ROADMAP.md` (you may _suggest_ edits in chat
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
