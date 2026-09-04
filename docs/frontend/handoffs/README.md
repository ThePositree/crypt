# Frontend Phase Control Handoffs

Protocol version: 2

This protocol moves D3 frontend control to a fresh main context before every
phase and after any context compaction. Its purpose is continuity without chat
memory: the new main rebuilds control from repository state, canonical
artifacts, explicit owner decisions, and a compact file-backed handoff.

`current.md` is both the rolling control record and the complete prompt for the
active or next phase. `ledger.md` is the compact append-only history of control
events. Neither file is a product, design, implementation, or review contract.

## Invariants

1. At most one phase main is active. Exactly one is active while phase work or
   an owner gate is in progress; a valid `prepared` transfer may briefly have
   zero active mains after the predecessor stops and before the receiver accepts.
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
11. `Mode` is exactly `manual-neighbor` or `observer-managed`; runtime,
    harness, provider, model, CLI, and orchestration details are not modes.
12. Observer eligibility is fixed before the first phase main starts and is
    permanently lost if that context performs phase work or compacts.
13. Artifact readiness does not finish a phase whose stop condition includes an
    owner decision. Its phase main remains active and addressable through that
    decision, requested fixes, and required re-review.
14. Every control stop tells the owner exactly who acts next, whether owner
    action is required, and the one concrete action that follows.
15. Required researcher, author or implementer, and reviewer roles use distinct
    execution contexts. A phase main orchestrates them but does not impersonate
    one of those roles.

## D3 Control Entry Gate

For a known or presumptive D3 frontend request, and after every resume or
detected compaction, inspect the repository bootstrap, frontend route, and the
control header of `current.md` before discovery, onboarding, broad frontend
reads, or delegation.

- A missing or `inactive` handoff permits only the Bootstrap Envelope flow.
- An invalid or stale handoff permits only blocking or recovery control work.
- A context that detected compaction while it was phase main has permanently
  lost authority for that D3 run. It cannot bootstrap, recover, continue, or
  complete its former phase.
- Owner chat, pasted onboarding answers, existing product files, and remembered
  session context never substitute for an accepted handoff.
- Before a fresh phase main accepts control, no discovery questions,
  onboarding, product research, artifact work, implementation, review, or
  phase-worker delegation is allowed. Only the control files may be created or
  repaired.

An initial control-only context may prepare the bootstrap envelope after a
compaction that occurred before any phase work. It does not become P01 main.
If it cannot prove that no phase work preceded compaction, it records
`RECOVERY_REQUIRED` instead of guessing.

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

`Mode` is a strict enum with exactly two legal values: `manual-neighbor` and
`observer-managed`. Do not combine them and do not put an execution product,
agent, CLI, model, provider, or runtime name in this field. Put those details in
the separate `Execution interface` field. A value such as `manual/native
coordination` is invalid. A generic owner message such as `continue`, `do it`,
or `go ahead` does not change the selected mode and does not create an
observer.

The mode is selected in the bootstrap envelope and remains immutable for that
D3 control run. The owner may choose either mode before P01 accepts control. A
normal recovery keeps the same mode. For a later capability loss or requested
mode change, mark the current run `superseded`, append `SUPERSEDED` with the
reason or owner decision, stop every old control role, and let a fresh
control-only context create a new `bootstrap-prepared` handoff ID. The new run
selects its mode from scratch. It never promotes the current or former phase
main into an observer. Previously approved artifacts may be referenced by the
new run, but they do not waive its bootstrap.

### Manual Neighboring Session

Use this mode when there is no persistent parent capable of two-level nested
delegation.

1. The outgoing main writes a `prepared` `current.md` and appends a `PREPARED`
   ledger event.
2. It prints the exact file content under `NEXT MAIN SESSION PROMPT`, ends with
   the mandatory `MANUAL_HANDOFF` owner-action block, and stops.
3. The owner places that prompt in a new top-level neighboring session.
4. The receiving session verifies and accepts it, appends `ACCEPTED`, publishes
   the Read Receipt, and becomes the sole phase main.

The old session may only explain a start failure or correct an invalid handoff.
If the owner replies `continue`, `do it`, or similar in the stopped session, it
repeats the exact transfer action; it does not resume phase work. Same-session
continuation requires an exact scoped `FRONTEND WAIVER:`.

### Observer Managed

Use this mode when a persistent observer can create a fresh phase main and that
main can create its own independent workers.

```text
observer
`-- phase main
    |-- factual researcher when required
    |-- independent author or implementer
    `-- independent reviewer or QA context
```

The observer retains only phase ID, gate state, owner decisions, compact
manifests, and handoff pointers. It may create or retire one phase main, relay
owner messages, and check the structure of a phase result. It must not read
large artifacts or the full next-main prompt; author, edit, implement, render,
review, or fix frontend work; task phase workers directly; approve owner gates;
or keep multiple phase mains active.

The observer identity and eligibility evidence are recorded before P01 starts.
An eligible observer has never been a phase main, artifact author,
implementer, reviewer, or QA context for this D3 run; has not read the full
frontend artifact set; and has not compacted. Eligibility is immutable. A
predecessor main cannot later rename itself observer, coordinator, or
integrator. If no eligible persistent observer was established in advance,
use `manual-neighbor`. A later observer must be a fresh control-only top-level
context recorded through recovery; a former main can never take that role.

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
- phase-main lifecycle: stopped
FRONTEND CONTROL STATE:
NEXT ACTOR:
ACTION REQUIRED FROM OWNER:
WHAT HAPPENS NEXT:
```

The observer treats any `PHASE RESULT` emitted before the catalog stop
condition as an invalid premature completion. It keeps or restores same-phase
control instead of launching the next phase. It retires the phase main only
after validating the terminal result and the fresh handoff pointer.

The observer starts the next main with a short instruction to read and execute
the exact `current.md`. If the third level or persistent observer becomes
unavailable, block the current run. Restore the same-mode capability or use the
explicit `SUPERSEDED -> new bootstrap` transition; never switch modes inside
the run.

At a boundary with no owner decision, the observer starts the next phase main
automatically in the same owner turn and continues waiting for its material
result. It must not end by telling the owner only what the next phase is or make
the owner reply `continue`.

At an owner gate, the phase main emits a nonterminal `OWNER ACTION REQUIRED`
message and remains active. The observer relays that question verbatim and
routes the owner's reply back to the same phase main. The main records the
decision, performs any requested correction and re-review, prepares the next
handoff, and only then emits its terminal `PHASE RESULT`. If the execution
interface cannot keep that main addressable across the owner gate, it does not
support `observer-managed` for that phase. Block and supersede the run, then
start a new control-only bootstrap in the desired mode; do not switch the
existing run to `manual-neighbor`.

## Phase-Main Lifecycle Through Owner Gates

Use this lifecycle independently of the handoff file status:

```text
prepared -> accepted -> working -> gate-waiting
gate-waiting -> working         # owner requested changes
gate-waiting -> phase-approved  # owner approved
phase-approved -> next prepared -> stopped
working -> next prepared -> stopped  # phase has no owner gate
```

`Artifacts ready for approval` means `gate-waiting`, not completed. A phase
main must not send a terminal completion signal, declare itself done, be
released, or be replaced before the catalog stop condition is true. For a phase
with an owner gate, that includes recording the explicit owner decision. If the
active main dies, compacts, or becomes unreachable while waiting, mark the
handoff `recovery-required`; a fresh same-phase recovery main must accept
control before any decision is recorded or next phase begins.

## Owner-Facing Control Action

Every owner-facing message that contains `Control Verdict: STOP`, reaches a
phase boundary, waits at an owner gate, reports a recovery, or reports a blocker
must end with this complete block:

```text
FRONTEND CONTROL STATE: AUTO_TRANSFER | WAITING_FOR_OWNER | MANUAL_HANDOFF | RECOVERY_REQUIRED | BLOCKED | COMPLETE
NEXT ACTOR: OBSERVER | OWNER | NEW_PHASE_MAIN | NONE
ACTION REQUIRED FROM OWNER: NONE | <one exact action or answer format>
WHAT HAPPENS NEXT: <one concrete system action>
```

The choices have exact behavior:

- `AUTO_TRANSFER`: owner action is `NONE`; the observer has already started or
  is immediately starting the next main and does not end the workflow waiting
  for a generic owner acknowledgement.
- `WAITING_FOR_OWNER`: name the exact gate, show the artifact/revision being
  decided, give the accepted answer form or options, and say what each answer
  causes. The current phase main remains active.
- `MANUAL_HANDOFF`: tell the owner to open a new top-level neighboring session
  and paste the full prompt printed immediately above the block. Never provide only
  a path or a description of the next phase.
- `RECOVERY_REQUIRED`: tell the owner or observer exactly which fresh context
  must open which handoff and why the old main cannot continue.
- `BLOCKED`: name the missing fact or invalid state and the single action that
  can clear it.
- `COMPLETE`: owner action is `NONE`; no later phase remains.

`Control Verdict: STOP`, `next step is ...`, or `a new session should ...`
without this block is invalid. Internal control terminology never replaces an
explicit instruction to the owner.

## Bootstrap Envelope

A new D3 request without an accepted handoff begins in a control-only bootstrap
context, not P01. That context selects the supported mode and creates a minimal
`bootstrap-prepared` `current.md` containing only:

- protocol version, handoff ID, date, mode, repository root and visible
  revision/state;
- the owner's raw request and facts explicitly present in it;
- target phase `P01` and its catalog stop condition;
- the instruction for the new main to read the full frontend set, validate and
  accept control, classify O01-O38 for the initial Read Receipt, expand the
  control checkpoint, and only then begin the P01 Task Contract after
  `PROCEED`.

Unknown scope, obligations, approvals, and artifacts remain explicitly
`unclassified`; the bootstrap context does not infer or research them. It
appends `BOOTSTRAP_PREPARED`, transfers control by the selected mode, and does
no P01 work. The first phase main accepts this envelope after its full read; it
does not create another pre-P01 handoff.

The bootstrap context must not publish a phase-main Read Receipt or return
`PROCEED`. In `observer-managed` mode it records the eligible observer identity
and immediately starts P01 main after the envelope is durable. In
`manual-neighbor` mode it prints the entire prompt and the required owner action.

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
- Execution interface:
- Bootstrap context identity:
- Observer identity and eligibility evidence: <identity and evidence> / N/A
- Repository root:
- Visible revision and dirty state:
- Raw owner request:
- Explicit facts from the owner request:
- Scope, O01-O38, approvals, waivers, and artifacts: unclassified
- P01 stop condition: Task and collaboration contracts exist; required
  onboarding reached question 25 and its Uncertainty Check, or established
  onboarding/identity evidence explicitly makes new onboarding unnecessary

Read the repository bootstrap, routed frontend sources, the complete frontend
subsystem and memory set, and this file. Verify the repository and bootstrap
control fields. If valid, mark this handoff accepted and append ACCEPTED; this
is control bookkeeping, not P01 work. Then classify O01-O38 from the available
evidence, expand this file to the full accepted control schema, and publish the
combined Read Receipt and Phase Control Accepted record. Do not establish the
Task Contract, ask onboarding questions, or perform any other P01 work before
that receipt returns PROCEED. At the P01 stop condition, prepare P02 and transfer
control.
```

## State Machine

Allowed `current.md` states are `inactive`, `bootstrap-prepared`, `prepared`,
`accepted`, `gate-waiting`, `phase-approved`, `blocked`,
`recovery-required`, `recovery-prepared`, `superseded`, and `completed`.

```text
inactive -> bootstrap-prepared -> accepted
accepted -> gate-waiting
gate-waiting -> accepted              # owner requested changes
gate-waiting -> phase-approved        # owner approved
phase-approved -> prepared -> accepted
accepted -> prepared -> accepted      # phase without an owner gate
bootstrap-prepared | prepared | accepted | gate-waiting | phase-approved | recovery-prepared -> blocked
accepted | gate-waiting -> recovery-required -> recovery-prepared -> accepted
blocked -> prepared | recovery-prepared
blocked | recovery-required -> superseded
superseded (old handoff ID) -> bootstrap-prepared (new handoff ID)
accepted -> completed
```

Every transition that retains a handoff ID also retains its mode. Only
`superseded (old handoff ID) -> bootstrap-prepared (new handoff ID)` may select
a different mode.

Preparing, accepting, blocking, or repairing control metadata is allowed before
the phase-action Read Receipt. No product or artifact work is. The receiving
main marks `accepted` only after verification, then publishes one combined Read
Receipt and `Phase Control Accepted` record with O38 satisfied.

For the minimal P01 bootstrap only, expanding `current.md` to the full control
schema and provisionally classifying O01-O38 after acceptance are also control
bookkeeping needed to construct that first receipt. They do not include the P01
Task Contract, onboarding, discovery, research, or any product artifact.

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
- Status: prepared / accepted / gate-waiting / phase-approved / blocked / recovery-required / recovery-prepared / superseded / completed
- Created at:
- Accepted at:
- Mode: manual-neighbor / observer-managed
- Execution interface:
- Session control role: phase-main
- Compaction seen in this context: no
- Observer identity and immutable eligibility evidence: <identity and evidence> / N/A
- Predecessor context:
- Receiving context: <identity> / pending for prepared transfer
- Active phase-main identity and lifecycle state:
- Previous phase stop evidence:
- Last allowed ledger event ID and type:
- Handoff schema version:

## Startup Control

1. Read the repository bootstrap and routed frontend sources, the complete
   `docs/agent/frontend_design_subsystem.md`, the complete frontend memory set,
   and this file.
2. Verify checkout identity, revision, dirty-state ownership, protocol version,
   owner decisions, active waivers, artifact revisions, review verdicts, and
   O01-O38 against canonical files. Canonical files and explicit owner decisions
   outrank a stale handoff.
3. Verify the exact mode enum, observer eligibility when applicable, predecessor
   stop evidence, active-main liveness, allowed ledger event, complete schema,
   and freshness invalidators. On any unresolved conflict, mark this handoff
   blocked or recovery-required, append the matching event, and stop. Do not
   guess or accept stale control.
4. If valid, mark this handoff accepted and append `ACCEPTED`. This is control
   bookkeeping, not phase work.
5. Publish the required Read Receipt and `Phase Control Accepted: <handoff ID>;
   phase <phase ID>; main <context identity>` in one message. Start phase work
   only when its Control Verdict is `PROCEED`.

## Repository State

- Absolute root:
- Branch or worktree identity:
- Exact commit, or base commit plus exact dirty fingerprint:
- Exact dirty-file list and state:
- Owner of every intentional uncommitted change:
- Frontend instruction version:
- Date and relevant execution context:
- Freshness invalidators checked:

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
- Phase lifecycle state: accepted / working / gate-waiting / phase-approved
- Last durable checkpoint:
- Completed phase units:
- Unfinished phase units:
- Active delegated work: role, context, status, expected artifact path:
- First controlling owner gate:
- Exact owner-gate state and active phase-main return channel:
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
- Distinct context identity for each researcher, author/implementer, and reviewer:
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
- Required owner-facing control action:

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
role/context provenance, owner-gate state, active-main lifecycle, predecessor
stop evidence, observer eligibility when applicable, freshness validation, or
the next control action. It is also invalid when it contains placeholders or
vague state; uses an unknown or hybrid mode; names a non-allowed ledger event;
disagrees with the actual revision or dirty state; lacks ownership for a dirty
file; names a completed, released, compacted, or unreachable main as active in
an `accepted` or `gate-waiting` state; leaves the predecessor active after a
prepared transfer; or lacks evidence that the prior phase reached its stop
condition. A `prepared` handoff may use `Receiving context: pending` and
`Active phase-main identity and lifecycle state: pending acceptance`; the
receiver replaces both during acceptance. Do not downgrade these failures to
advisory findings.

Any commit, unlisted dirty change, owner redirect, instruction-version change,
artifact revision, review verdict, unexpected active-main termination,
compaction, or gate state change after handoff preparation invalidates its
repository snapshot until `current.md` is refreshed. The declared predecessor
stop that creates the legal prepared transfer gap is expected and does not
invalidate the handoff. A checkpoint commit made after handoff preparation must
be followed by an exact snapshot refresh; otherwise the handoff is stale.

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
The observer or fresh control-only recovery coordinator records
`RECOVERY_REQUIRED`; the compacted main cannot record its own recovery.

The fresh recovery main performs the full Startup Control sequence, compares
the last durable checkpoint with repository state, and marks either
`recovery-prepared` then `accepted`, or `blocked` if ownership or progress is
ambiguous. Unrecorded work is never presumed complete.

If the observer compacts or loses an unambiguous active-main identity, freeze
orchestration. Restore a fresh eligible observer in the same
`observer-managed` run from `current.md` plus the tail of `ledger.md`, or move
through `BLOCKED` or `RECOVERY_REQUIRED` to `SUPERSEDED`, stop the old roles,
and start a new bootstrap where `manual-neighbor` may be selected.

## Transition Ledger

Append one Markdown-table row to `ledger.md` for each
`BOOTSTRAP_PREPARED`, `PREPARED`, `ACCEPTED`, `GATE_WAITING`,
`PHASE_APPROVED`, `BLOCKED`, `RECOVERY_REQUIRED`, `RECOVERY_PREPARED`,
`SUPERSEDED`, `WAIVED`, or `COMPLETED` event. Record:

- timestamp and handoff ID;
- event, phase, predecessor, successor, and mode;
- repository revision or dirty-state fingerprint;
- owner-decision or waiver path when applicable;
- one-line evidence or blocker.

Never rewrite or delete prior rows. The final audit reads this ledger as phase
transition evidence. Normal phase startup reads only the last relevant rows
named by `current.md`, not the full history.

Only the event names above are valid control transitions. Artifact or review
verdicts such as `REVIEW_PASSED` belong in the artifact/review manifest, never
in the control ledger. Use full timestamps sufficient to establish ordering.

## Worker Boundary

Phase handoffs are for mains. A phase main may technically run in a child
process, but its frontend role is `phase-main`, not `worker`; its terminal
lifecycle must remain open through the phase stop condition. Only the phase main
may start or task workers in its phase. The observer never starts a researcher,
author, implementer, reviewer, or QA worker.

Independent workers receive role-minimal briefs: role, short product summary,
exact inputs, exclusions, permissions, deliverable path, acceptance criteria,
and compact completion format. They do not receive `current.md`, the full main
prompt, or unrelated repository context. Unless their brief explicitly assigns
control-plane maintenance, they must not edit `current.md`, `ledger.md`, task
files, or changelog.

Use this topology when all roles apply:

```text
optional observer
`-- phase main
    |-- factual researcher
    |-- artifact author or implementer
    `-- independent reviewer or QA
```

The phase main reads compact manifests and cited blockers; it does not repeat
the delegated research, author the large artifact, fix it itself, or perform its
review. Blocking findings return to the same author, then to the same reviewer
for focused re-review. Every post-review artifact change creates a new revision
and invalidates the prior verdict until re-review.

For P02 the literal required chain is: separate Factual Product Researcher ->
separate Product Surface Author -> separate read-only Contract Reviewer -> same
Product Surface Author for fixes -> same reviewer for re-review -> phase main
for the owner gate. Path-existence checks alone are insufficient. The reviewer
must validate cited symbols, field and type names, capability claims, maturity,
counts, source currency, and arithmetic against canonical sources. An
unverified `100%`, `fully aligned`, or zero-blocker claim is itself a blocking
review defect.
