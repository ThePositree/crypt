# Frontend Phase Control Handoffs

This protocol moves D3 frontend control to a fresh main context before every
phase and after any context compaction. Its purpose is continuity without chat
memory: the new main rebuilds control from repository state, canonical
artifacts, explicit owner decisions, and a compact file-backed handoff.

`current.md` is both the rolling control record and the complete prompt for the
active or next phase. `ledger.md` is the compact append-only history of control
events. Neither file is a product, design, implementation, or review contract.

## Invariants

1. Exactly one phase main is active.
2. Every applicable D3 phase begins in a fresh main context.
3. A phase main owns only its named phase and stops at its stop condition.
4. Manual main transfer goes to a neighboring top-level session, never a
   subagent or worker.
5. Observer mode uses `observer -> phase main -> independent workers`; only the
   phase main delegates within its phase.
6. The observer, predecessor main, and receiving main do not satisfy any
   independent-review role for transferred artifacts.
7. Owner gates remain owner decisions.
8. The new main reads the full frontend instruction and memory set; its handoff
   directs that read but never replaces it.
9. The outgoing main writes the next handoff and stops before next-phase work.
10. Context compaction immediately invalidates phase-main authority.

## Phase Catalog

Each applicable row is a separate phase. Do not combine adjacent rows to avoid
a control transfer.

| ID | Phase outcome | Stop condition |
| --- | --- | --- |
| P01 | Task Contract, Collaboration Check, and applicable Design Onboarding and Uncertainty Check | Task and collaboration contracts exist; required onboarding reached question 25 and its Uncertainty Check, or established onboarding/identity evidence explicitly makes new onboarding unnecessary |
| P02 | factual product research, Product Surface Model authoring, independent review, and Product Surface Approval | owner Product Surface decision is recorded |
| P03 | Messaging Identity, source-grounded content, Text Inventory, independent copy review, and applicable copy approval | inventory and review cover approved scope; applicable owner decision is recorded |
| P04 | Preliminary Identity and five raster Visual Direction Boards | owner Visual Direction decision is recorded |
| P05 | Selected Visual Direction Translation and final Design Identity/System | translation and identity/system artifacts pass required independent contract review |
| P06 | production UI library and rendered component showcase | owner UI Library decision is recorded after independent visual-fidelity review |
| P07 | Production Raster Asset Pack when applicable | owner asset-pack decision is recorded, or non-applicability is evidenced |
| P08 | navigation and user flows | complete flow package passes independent contract review |
| P09 | page-level clickable wireframes, First-Use Review, and rendered visual QA | the full wireframe package and reviews are ready for screen-contract mapping; no Wireframe Approval is claimed yet |
| P10 | screen contracts, Wireframe Conformance Contract, and complete cross-package contract review | owner Wireframe decision is recorded against the complete page/screen index |
| P11 | Frontend Implementation Brief and final implementation package review | owner Final Implementation decision is recorded |
| P12 | production implementation in its approved independent context | implementation manifest and preflight evidence are complete; no final-QA claim is made |
| P13 | independent QA, implementation fixes, re-review, durable memory, and Final Instruction Audit | blockers are fixed and rechecked or waived; completion evidence is recorded |

Owner-requested corrections stay in the current phase. When no owner gate is
named, reaching the row's stop condition ends the phase. A materially different
outcome creates an earlier boundary rather than expanding the current phase.

## Modes

### Manual Neighboring Session

Use this mode when there is no persistent parent capable of two-level nested
delegation.

1. The outgoing main writes a `prepared` `current.md` and appends a `PREPARED`
   ledger event.
2. It presents the exact file content under `NEXT MAIN SESSION PROMPT` and
   stops.
3. The owner places that prompt in a new top-level neighboring session.
4. The receiving session verifies and accepts it, appends `ACCEPTED`, publishes
   the Read Receipt, and becomes the sole phase main.

The old session may only explain a start failure or correct an invalid handoff.
Same-session continuation requires an exact scoped `FRONTEND WAIVER:`.

### Observer Managed

Use this mode when a persistent observer can create a fresh phase main and that
main can create its own independent workers.

```text
observer
`-- phase main
    |-- independent author or implementer
    `-- independent reviewer or QA context
```

The observer retains only phase ID, gate state, owner decisions, compact
manifests, and handoff pointers. It may create or retire one phase main, relay
owner messages, and check the structure of a phase result. It must not read
large artifacts or the full next-main prompt; author, edit, implement, render,
review, or fix frontend work; task phase workers directly; approve owner gates;
or keep multiple phase mains active.

At a boundary, the phase main returns only:

```text
PHASE RESULT
- completed phase and verdict:
- owner decision or blocker:
- artifact/review manifest paths:
- next handoff ID:
- current.md path:
- next phase:
- status:
```

The observer starts the next main with a short instruction to read and execute
the exact `current.md`. If the third level or persistent observer is unavailable,
use Manual Neighboring Session mode.

## Bootstrap Envelope

A new D3 request without an accepted handoff begins in a control-only bootstrap
context, not P01. That context selects the supported mode and creates a minimal
`bootstrap-prepared` `current.md` containing only:

- protocol version, handoff ID, date, mode, repository root and visible
  revision/state;
- the owner's raw request and facts explicitly present in it;
- target phase `P01` and its catalog stop condition;
- the instruction for the new main to read the full frontend set, establish the
  Task Contract, classify O01-O38, and expand the handoff after acceptance.

Unknown scope, obligations, approvals, and artifacts remain explicitly
`unclassified`; the bootstrap context does not infer or research them. It
appends `BOOTSTRAP_PREPARED`, transfers control by the selected mode, and does
no P01 work. The first phase main accepts this envelope after its full read; it
does not create another pre-P01 handoff.

Use this exact bootstrap shape:

```md
# NEXT MAIN SESSION PROMPT

You are the sole phase main for D3 frontend phase P01. This is the initial
control transfer. Do not create another pre-P01 handoff.

- Protocol version:
- Handoff ID:
- Status: bootstrap-prepared
- Created at:
- Mode: manual-neighbor / observer-managed
- Repository root:
- Visible revision and dirty state:
- Raw owner request:
- Explicit facts from the owner request:
- Scope, O01-O38, approvals, waivers, and artifacts: unclassified
- P01 stop condition: Task and collaboration contracts exist; required
  onboarding reached question 25 and its Uncertainty Check, or established
  onboarding/identity evidence explicitly makes new onboarding unnecessary

Read the repository bootstrap, routed frontend sources, the complete frontend
subsystem and memory set, and this file. Verify repository state; establish the
Task Contract; classify O01-O38; expand this file to the full accepted handoff
schema; append ACCEPTED to the transition ledger; then publish the combined
Read Receipt and Phase Control Accepted record. Do no P01 work before a PROCEED
verdict. At the P01 stop condition, prepare P02 and transfer control.
```

## State Machine

Allowed `current.md` states are `inactive`, `bootstrap-prepared`, `prepared`,
`accepted`, `blocked`, `recovery-prepared`, and `completed`.

```text
inactive -> bootstrap-prepared -> accepted
accepted -> prepared -> accepted
accepted -> recovery-prepared -> accepted
bootstrap-prepared | prepared | accepted | recovery-prepared -> blocked
blocked -> prepared | recovery-prepared
accepted -> completed
```

Preparing, accepting, blocking, or repairing control metadata is allowed before
the phase-action Read Receipt. No product or artifact work is. The receiving
main marks `accepted` only after verification, then publishes one combined Read
Receipt and `Phase Control Accepted` record with O38 satisfied.

The receiving context must see the exact checkout containing `current.md` and
all referenced artifacts. For another checkout, create a coherent checkpoint or
otherwise transfer the exact state first. A handoff that points to inaccessible
uncommitted changes is invalid.

## Current Handoff Prompt

Except for the minimal bootstrap envelope, replace every field below. The file
itself is the prompt: do not repeat the same facts in a second embedded prompt.

```md
# NEXT MAIN SESSION PROMPT

You are the sole phase main for the D3 frontend phase named below. This is full
control transfer. Do not perform work from an earlier or later phase.

- Protocol version:
- Handoff ID:
- Status: prepared / accepted / blocked / recovery-prepared / completed
- Created at:
- Accepted at:
- Mode: manual-neighbor / observer-managed
- Predecessor context:
- Receiving context:
- Last ledger event:

## Startup Control

1. Read the repository bootstrap and routed frontend sources, the complete
   `docs/agent/frontend_design_subsystem.md`, the complete frontend memory set,
   and this file.
2. Verify checkout identity, revision, dirty-state ownership, protocol version,
   owner decisions, active waivers, artifact revisions, review verdicts, and
   O01-O38 against canonical files. Canonical files and explicit owner decisions
   outrank a stale handoff.
3. On unresolved conflict, mark this handoff blocked, append `BLOCKED`, and
   stop. Do not guess.
4. If valid, mark this handoff accepted and append `ACCEPTED`. This is control
   bookkeeping, not phase work.
5. Publish the required Read Receipt and `Phase Control Accepted: <handoff ID>;
   phase <phase ID>; main <context identity>` in one message. Start phase work
   only when its Control Verdict is `PROCEED`.

## Repository State

- Absolute root:
- Branch or worktree identity:
- Commit:
- Dirty-state summary:
- Owner of every intentional uncommitted change:
- Frontend instruction version:
- Date and relevant execution context:

## Product And Task Contract

- Neutral product summary:
- Outcome:
- Approved scope:
- Explicit exclusions:
- Sources of truth:
- Acceptance evidence:
- Material unknowns:

## Phase State

- Completed phase and evidence:
- Applicable owner decision:
- Current phase ID, outcome, and stop condition:
- Last durable checkpoint:
- Completed phase units:
- Unfinished phase units:
- Active delegated work: role, context, status, expected artifact path:
- First controlling owner gate:
- Forbidden next-phase actions:

## Owner Control

- Approvals in force with decision paths/revisions:
- Exact active `FRONTEND WAIVER:` messages:
- Pending owner questions:

## Obligation Ledger

- O01 through O38: status for each; reason for every not-applicable, blocked, or
  waived item.

## Artifact And Review Manifests

- For each relevant item: path, revision, status, author context, reviewer
  context, verdict, and cited blocker lines. Do not paste artifact bodies.

## Context Loading Boundaries

- Phase-specific full sources:
- Targeted sources only if triggered:
- Unrelated or forbidden context:

## Within-Phase Collaboration

- Required roles and independence boundaries:
- Minimal inputs for each role:
- Read/write permissions and disjoint write scopes:
- File-backed deliverables and compact completion format:
- Review, fix, and re-review loop:

Do not give bounded workers this main handoff, repository history, or the full
frontend subsystem unless they audit instruction compliance. Do not duplicate
their research, authoring, rendering, implementation, or review in the main
context.

## Phase Execution Contract

- Allowed actions:
- Required artifacts:
- Acceptance criteria:
- Validation and rendered evidence:
- STOP blockers:
- Required `PHASE RESULT` fields:

At the phase stop condition, do not start another phase. When another applicable
catalog phase remains, record every applicable owner decision, write its
`prepared` `current.md`, append `PREPARED`, and transfer control. In manual
mode, present the exact file and stop. In observer mode, return only the compact
`PHASE RESULT` and stop. After P13, or after the last applicable phase when later
rows are all inapplicable, mark `current.md` completed, append `COMPLETED`, and
end without creating another session.
```

A non-bootstrap handoff is invalid if it omits obligation state, dirty-change
ownership, applicable artifact revisions, exact phase scope, a stop condition,
or the next control action.

## Recovery Checkpoints

While active, the phase main keeps the compact phase-state, dirty-state,
artifact/review manifest, owner-control, and delegated-work fields current after
each material event. A material event is a durable artifact revision, worker
start or completion, review verdict, accepted fix, owner redirect or decision,
scope change, checkpoint, or new blocker. Do not add routine progress narration
or worker output.

If compaction is detected, the compacted main loses authority immediately. It
must not reread, reconstruct, edit artifacts, update `current.md`, or claim
completion. The observer starts a fresh recovery main from the last valid file;
without an observer, the owner gives that file to a fresh neighboring session.

The fresh recovery main performs the full Startup Control sequence, compares
the last durable checkpoint with repository state, and marks either
`recovery-prepared` then `accepted`, or `blocked` if ownership or progress is
ambiguous. Unrecorded work is never presumed complete.

If the observer compacts or loses an unambiguous active-main identity, freeze
orchestration and use a fresh top-level observer from `current.md` plus the tail
of `ledger.md`, or switch to Manual Neighboring Session mode.

## Transition Ledger

Append one Markdown-table row to `ledger.md` for each
`BOOTSTRAP_PREPARED`, `PREPARED`, `ACCEPTED`, `BLOCKED`,
`RECOVERY_PREPARED`, `WAIVED`, or `COMPLETED` event. Record:

- timestamp and handoff ID;
- event, phase, predecessor, successor, and mode;
- repository revision or dirty-state fingerprint;
- owner-decision or waiver path when applicable;
- one-line evidence or blocker.

Never rewrite or delete prior rows. The final audit reads this ledger as phase
transition evidence. Normal phase startup reads only the last relevant rows
named by `current.md`, not the full history.

## Worker Boundary

Phase handoffs are for mains. Independent workers receive role-minimal briefs:
role, short product summary, exact inputs, exclusions, permissions, deliverable
path, acceptance criteria, and compact completion format. They do not receive
`current.md`, the full main prompt, or unrelated repository context. A phase
main remains responsible for all worker author/reviewer separation and review
loops inside its phase.
