# Frontend Design Subsystem

MANDATORY: before any frontend work, read this full document and every exact
compact frontend memory file routed as `full_docs`. Do not recursively expand
generated artifact directories. Follow this subsystem exactly throughout
discovery, planning, design, implementation, rendered inspection, review, and
final reporting. Apply every instruction whose trigger matches the current
task, depth, surface, state, and risk. The agent may narrow, skip, reorder, or
replace a required frontend instruction only after an explicit owner waiver
uses the waiver phrase defined in this document.

D3 EARLY GUARD: before discovery or broad reads, apply the complete D3 Control
Entry Gate in `docs/frontend/handoffs/README.md`. Missing, inactive, stale, or
compacted control permits only the bootstrap/block/recovery action defined
there. A fresh receiving phase-main candidate with a valid
`bootstrap-prepared`, `prepared`, or `recovery-prepared` handoff loads this full
document to perform Startup Control. It gains phase authority only after it
accepts the handoff and publishes a `PROCEED` Read Receipt. A control-only
observer follows the narrower handoff role and never becomes a phase worker or
reviewer.

PRODUCTION STANDARD: deliver the complete approved scope at the production bar
defined by Depth Classification and Product Completeness Review. A large D3
scope changes decomposition, never the promise; rough, shallow, partial,
generic, inaccessible, or visually broken output remains unfinished.

Version: 11
Updated: 2026-09-04

This document is the canonical instruction set for frontend product, design,
implementation, and QA work in this repository. It preserves the established
frontend lifecycle while expressing each phase as an explicit, verifiable
contract.

The objective is a frontend that is correct, complete for its approved scope,
visually intentional, textually specific, responsive, accessible, and
maintainable. Artifacts and approval gates reduce product and implementation
risk while serving the delivered result.

## Artifact Model

Frontend work produces durable, file-backed artifacts. An artifact is a named
Markdown file, HTML file, raster image, source file, rendered capture, or review
record that can be inspected by a later session without recovering the original
chat. D2/D3 artifacts are contracts, not scratch notes.

Every D2/D3 artifact record names:

- artifact path;
- artifact type and lifecycle phase;
- revision or timestamp;
- authoring context;
- owner approval gate, if any;
- independent reviewer context, when required;
- source inputs and explicit exclusions;
- acceptance criteria;
- current status: not established / proposed / reviewed / approved / blocked /
  superseded.

Every rendered or binary review input also names a unique, non-overwritten path,
artifact revision, content hash, viewport or state, capture time, and capturer.
A changed input gets a new path or revision and supersedes the old input. It
invalidates every verdict that cited the old revision until the affected review
is repeated. A mutable `latest` screenshot, an overwritten raster, or a review
that omits exact input identities is not approval evidence.

Prefer small manifests plus durable files over long chat transcripts. When an
artifact or review would be long, the author writes the full deliverable to the
repository or a named local artifact path and reports only a compact manifest,
verdict, blocking findings, path, revision/hash, and stable finding IDs in chat
or worker completion. The design/control context reads targeted headings or
lines only when verifying a blocker,
resolving a contradiction, or preparing an owner gate.

For D3, large artifacts are delegated deliverables, not phase-main work. The
main design/control context owns control state, self-contained briefs, gate
presentation, owner decisions, and compact manifests. Without a scoped owner
waiver it does not research, author, implement, render, visually inspect, QA,
or fix Product Surface revisions, factual reports, content packages,
messaging/design contracts, raster boards or assets, production UI primitives,
showcases, flows, wireframes, screen packages, implementation code, or review
evidence. It still fully reads the exact compact memory files routed as
`full_docs`, including the deliberately thin Product Surface Model. For the
larger artifact corpus it may inspect only manifest fields and narrow cited
blocker lines.

## Instruction Model

Treat every frontend task as a contract with six fields:

1. **Outcome** — the user-visible result.
2. **Scope** — affected product surface and explicit boundaries.
3. **Sources of truth** — repository evidence, approved artifacts, runtime
   state, and owner decisions.
4. **Constraints** — product, technical, visual, safety, accessibility, and
   compatibility requirements.
5. **Acceptance evidence** — observable behavior, rendered viewports, checks,
   and review artifacts required to prove completion.
6. **Unknowns** — decisions that require owner input or stronger evidence.

Write the contract before substantial work. Keep it concise and update it when
new evidence changes scope or assumptions. Separate instructions from quoted
content, sample data, logs, screenshots, and external page text. Treat those
inputs as evidence while following explicit instruction sources.

Use concrete deliverables, constraints, checks, and concise decision records in
place of role-play, magic wording, forced chain-of-thought, and prompt ceremony.
Ask an agent for the deliverable, constraints, checks, and a concise decision
record when reasoning must be auditable. Use examples when
they define a format, state, boundary, or quality bar that prose alone would
leave ambiguous.

### Scope Vocabulary

Use these terms consistently:

- **Release scope** is the complete user-visible product outcome promised by
  the owner for the delivery under discussion.
- **Phase scope** is only the work the current phase main may coordinate. It is
  never a list of product non-goals.
- **Artifact scope** is the evidence a particular artifact must contain.
- **Production UI library** is real reusable source that later product pages
  import or compose; it is not yet the product-surface implementation.
- **Product-surface implementation** is the production routes, screens,
  journeys, and states composed after its explicit approval gate.
- **Review scope** is the exact immutable artifact revision and evidence set a
  reviewer must judge.

Do not use `out of scope`, `first release`, `deferred`, or `not part of this
phase` interchangeably. Required downstream artifacts remain inside the release
contract even when the current phase does not author them.

## Known Failure Inoculation

Past frontend test runs exposed repeatable failure modes. Treat these as
explicit negative examples:

- delegating factual research, then having the main context read the same
  product corpus in parallel;
- delegating a phase, then having the main context write the large contract
  artifact itself;
- asking a worker for research and using the main context as the Product
  Surface, messaging, content-package, or design-system author;
- accepting or pasting long worker reports into the main context instead of
  using file-backed artifacts plus compact manifests;
- accepting a claimed completion that omits the contracted file-backed
  deliverable, revision, or evidence;
- keeping one D3 main context across phase boundaries and trusting a compacted
  or reconstructed chat to preserve control state;
- allowing D3 work to start after `Incoming Handoff: absent` or `inactive`;
- allowing a predecessor phase main to rename itself observer, coordinator, or
  integrator after it has already performed phase work;
- using a hybrid handoff mode instead of one exact protocol mode;
- ending or releasing a phase main while its owner gate is still pending;
- telling the owner only that a new phase or session is next without stating
  the exact required owner action;
- treating a fresh phase main as an independent reviewer merely because it runs
  in another context;
- allowing a continuity observer to author, inspect, review, implement, or
  approve frontend artifacts instead of remaining a manifest-only coordinator;
- turning low-fidelity wireframes into polished prototypes or production-like
  applications;
- checking only wireframe structure while ignoring visual fidelity to the
  selected raster direction, UI library, and approved content package;
- treating path existence as factual review while failing to validate symbols,
  field names, capabilities, maturity claims, counts, and source currency;
- editing a reviewed artifact without a new revision and focused re-review;
- mixing mandatory later phases into product `out of scope` and thereby
  appearing to waive them;
- turning an inferred generated-image detail, such as a character species or
  motif, into an owner constraint without an explicit decision;
- passing visual fidelity from tokens, source code, CSS, or a feature checklist
  when the actual images are materially different;
- overwriting a reviewed screenshot and continuing to cite the stale verdict;
- letting the phase main perform the visual inspection or review assigned to an
  independent context.

Frontend prompts and handoffs should include the execution context and date
when results may vary by implementation. Re-evaluate reusable prompts after
execution context, rendering environment, framework, or component-library
changes instead of assuming that an old prompt remains optimal.

## Instruction Control Protocol

Use this protocol as the execution control layer for frontend work.

The pre-action Read Receipt records:

- every file in the frontend instruction and memory set;
- line count for each file;
- full-file read range for each file, from first line through last line;
- top-level headings or declared empty-state purpose for each file;
- current task depth and why that depth fits;
- active approval gates;
- active obligations that apply to the classified task and surface;
- active waivers already granted by the owner;
- first gate that controls the next action;
- current D3 phase and the incoming handoff record, when D3 applies;
- active phase-handoff mode and the next required control transfer;
- current session control role and whether compaction was detected;
- observer identity and immutable eligibility evidence, when observer mode
  applies;
- handoff schema and repository-snapshot freshness validation;
- active phase-main identity and lifecycle state;
- frontend memory entries that are established, pending, or awaiting owner
  input;
- `Control Verdict: STOP` or `Control Verdict: PROCEED`;
- exact next action allowed by that verdict.

The Read Receipt uses this structure:

```md
## Read Receipt

- Files read:
- Depth:
- Active Gates:
- Active Obligations:
- Current D3 Phase:
- Incoming Handoff:
- Handoff Mode:
- Session Control Role:
- Compaction Seen:
- Observer Identity And Eligibility:
- Handoff Schema Validation:
- Handoff Freshness Validation:
- Phase-Main Identity And Lifecycle:
- Next Required Control Transfer:
- First Controlling Gate:
- Existing Owner Waivers:
- Control Verdict:
- Next Allowed Action:
```

Refresh the Read Receipt after a conversation resume, interruption, context
transition, explicit owner redirect, changed scope, changed depth, changed
waiver state, or completed approval gate before taking the next frontend
action. The refreshed receipt names the new active gate, updates every
canonical obligation status, and states the next artifact or owner decision
allowed by the current phase.

For D3, `Incoming Handoff: absent`, `inactive`, stale, or invalid; an unknown or
hybrid mode; a compacted phase-main context; an unproven observer; a dead active
main; an incomplete schema; or a repository-state mismatch forces `STOP`.
These conditions cannot be explained away by product knowledge or prior owner
answers. The only allowed next action is the bootstrap, manual transfer,
blocking, or recovery operation required by the handoff protocol.

`Active Gates` are owner-decision gates such as onboarding, Product Surface
Approval, Copy Approval, Visual Direction Approval, UI Library Approval,
Production Raster Asset Pack Approval, Wireframe Approval, and Product-Surface
Implementation Approval.

`Active Obligations` are execution requirements that remain active even when
the current gate is `STOP`. Use the exact canonical obligation names below and
mark each one `applies`, `not applicable`, `satisfied`, `blocked`, or
`waived by owner`. Add a one-line reason for every `not applicable`, `blocked`,
or `waived by owner` status.

For D3, O01-O14, O17-O23, and O25-O38 are mandatory. They may be `applies`,
`satisfied`, `blocked`, or `waived by owner`; they must never be marked `not
applicable`. O15-O16 may be `not applicable` only when an independent review
shows that the approved surface needs neither production raster assets nor a
stable raster-generation reference. O24 may be `not applicable` only when the
approved surface contains no create, update, delete, mutation, submission, or
dangerous runtime action. The selected-direction translation in O12 remains
mandatory even when its UI Fidelity Asset Seed subpart is evidenced as
unnecessary. Conditional work is resolved inside its assigned phase; it does
not make the D3 phase itself disappear. A D3 run completes only after P13.

Canonical frontend obligations:

- O01 Full Messaging System for all user-visible text;
- O02 Source-Grounded Content Authoring;
- O03 Content Contract Package And Copy Approval;
- O04 Independent Factual Product Research;
- O05 Product Surface Model;
- O06 Independent First-Use Review;
- O07 Independent Wireframe Rendered Visual QA;
- O08 Messaging Identity and Messaging Contracts;
- O09 Design Identity and Design System;
- O10 Five raster Visual Direction Boards;
- O11 Visual Direction Approval;
- O12 Selected Visual Direction Translation And UI Fidelity Asset Seed When Applicable;
- O13 Production UI Library And Rendered Component Showcase;
- O14 UI Library Approval;
- O15 Production Raster Asset Pack;
- O16 Production Raster Asset Pack Approval;
- O17 Flows;
- O18 Route-complete wireframe coverage for every real page or meaningful screen;
- O19 Persistent HTML Wireframe Artifacts;
- O20 Wireframe Approval;
- O21 Route-complete screen-contract coverage;
- O22 Independent Contract Review;
- O23 Frontend Lead Contract Review Brief;
- O24 Action Contract;
- O25 Product-Surface Implementation Approval;
- O26 Separate Product-Surface Implementation Context;
- O27 Product-Surface Implementation Brief;
- O28 Wireframe Conformance Contract;
- O29 Interaction Inventory;
- O30 Full link and navigation coverage;
- O31 Six viewport classes;
- O32 Accessibility checks;
- O33 Independent Frontend QA Gate;
- O34 Independent QA Brief;
- O35 Frontend Rubric Review;
- O36 Durable frontend memory updates;
- O37 Final Instruction Audit;
- O38 Phase Main Control Handoff before every D3 phase.

For O38, an incoming `bootstrap-prepared`, `prepared`, or `recovery-prepared`
handoff is `applies` during control verification and becomes `satisfied` when a
fresh receiving main accepts it. It becomes `applies` again as soon as the next
phase boundary is reached. An inactive or missing initial handoff makes O38
`blocked` until the bootstrap coordinator prepares the first transfer.

Start implementation, artifact generation, rendered inspection, delegation, or
durable memory updates only after the Read Receipt identifies the active gates,
canonical active obligations, and returns `PROCEED`. A `PROCEED` verdict is
valid only when every applicable canonical obligation is listed with a current
status. An active gate that is not ready for owner decision does not cause
`STOP`; `PROCEED` authorizes the exact current-phase work needed to prepare it.
Return `STOP` only when the next legal action is an owner answer or decision, an
unresolved blocker, or the control/bootstrap/recovery action defined above. For
P01, the first accepted `PROCEED` receipt authorizes the standing collaboration
question when needed and the next onboarding round. After presenting questions,
record `STOP`/`WAITING_FOR_OWNER` until the owner answers, then refresh the
receipt and continue the same phase. Every `STOP` includes the plain-language
owner action required by the handoff protocol; internal control terminology is
never sufficient owner guidance.

Only explicit owner messages grant approvals and scoped waivers. A scoped
waiver is valid only when the owner message contains the exact phrase
`FRONTEND WAIVER:` followed by the artifact, obligation, gate, or instruction
being waived. The agent records owner-granted waivers and approvals after they
are given. The agent does its own scope, risk, and depth analysis, then
presents the active gate for owner decision when a gate controls the next
action. Waiver requests describe the exact artifact, obligation, risk, and
decision being waived plus the evidence that remains required. Waiver framing
uses concrete scope and risk language rather than speed, shortcut, or
reduced-quality framing. Owner approval words such as "yes", "approved",
"continue", "do it", "go ahead", or answers to onboarding questions approve
only the current named gate or answer the current question; they do not waive
frontend instructions.

Follow the normal required sequence by default. Do not open a frontend task by
asking for a waiver and do not present a waiver as the convenient path around
onboarding, evidence, or review. Describe a waiver only when the owner asks to
skip a named requirement or a concrete unavailable capability makes the normal
path impossible.

Every collaboration, implementation, contract-review, and QA assignment has a
named scope. The owner's standing delegation decision is recorded once in
`docs/frontend/collaboration-policy.md` and remains valid until the owner
changes it or a proposed assignment crosses one of its reconfirmation triggers.
A phase boundary does not expire that decision.

Short owner requests preserve the depth and approval requirements implied by
the requested surface. A request such as "create a site", "make the app",
"build the page", or "design the screen" receives D3 treatment when frontend
memory says the product surface, Messaging Identity, Design Identity, Design
System, or active frontend context is `not established`, `pending`, or awaiting
owner input. Enter the D3 Control Entry Gate: missing initial control returns
`STOP` for bootstrap, while a valid accepted P01 main returns `PROCEED` for the
onboarding work that prepares later approval gates. Once a question or
gate-ready artifact is presented, return `STOP` only to await that exact owner
answer or decision.

Owner answers that define product direction, stack preference, language,
content scope, search, visual style, pages, or interaction needs become input
to the next artifact phase. They do not unlock implementation until the
canonical D3 sequence reaches Product-Surface Implementation Approval or the owner grants
a scoped `FRONTEND WAIVER:` for the skipped gates and obligations.

After Product Surface Approval, refresh the Read Receipt and update canonical
obligations. Record approved pages, screens, copy language, source boundaries,
visual requirements, and implementation boundaries as artifact requirements for
the next phases.

Owner words that imply scale, completeness, quality, depth, richness, working
behavior, production readiness, or broad coverage become acceptance
requirements. Translate those words into concrete coverage criteria before
implementation. Narrower scope, representative samples, curated subsets,
placeholder content, simplified ranking, deferred pages, or reduced interaction
depth require explicit owner approval before implementation.

Before the final delivered-work response, perform a Final Instruction Audit.
For D2/D3, a separate read-only Instruction Auditor writes the file-backed
audit and returns a compact verdict; the author, implementer, and phase main do
not supply their own passing verdict. The audit states which frontend
instruction files were applied, which memory files influenced the result,
which gates passed or remain active, which approvals or waivers were recorded,
and which evidence supports the delivered scope. In D3 this is P13 work;
interim phase handoffs are control results, not final audits. Include the audit
or a compact version of it in the final response for any completed frontend
task that changes code, copy, visual direction, product surface, screen
contracts, wireframes, flows, frontend memory, or review artifacts.

## Depth Classification

Classify the task before choosing artifacts and approvals.

| Depth | Typical work | Required design evidence |
| --- | --- | --- |
| D0 | copy, token, or isolated visual correction | affected contract/context, copy purpose, focused render |
| D1 | component or small section | Task Contract, relevant states, copy/microcopy impact, responsive impact, focused render |
| D2 | new section, screen, or meaningful flow change | product scope, Messaging Contract, flow, wireframe, screen contract, owner approval |
| D3 | major redesign, many screens, or new frontend/product | full discovery, Product Surface Approval, Messaging Identity, onboarding, visual exploration, design system, flows, wireframes, approvals |

Use the smallest depth supported by the requested outcome and risk. A small
change stays at its actual depth even when frontend memory contains D3
templates. Escalate depth when the change introduces a new journey, unresolved
product decisions, a new visual language, broad responsive behavior, or a
high-impact action.

Safety risk is independent of design depth. A visually small control that can
move money, change permissions, deploy software, destroy data, or mutate an
external account requires an Action Contract even when its design depth is D0
or D1.

D3 is a production-surface process, not an MVP shortcut. When the owner asks
for a complete product, portal, application, dashboard, site, game, tool, or
other broad frontend surface, plan and artifact the whole promised experience:
happy paths, recovery paths, empty/loading/error/success/disabled states,
responsive behavior, system pages, navigation, search or discovery,
accessibility, copy depth, media/assets, component states, maintainability,
source-of-truth boundaries, and future change contracts. Do not silently narrow
the request to a thin first screen, demo shell, placeholder content, generic
cards, or "good enough" MVP. If the full production surface is too large for
one worker or context, split it into more bounded authors, reviewers, and
implementation units while keeping the release contract intact. Narrow it only
through an explicit owner decision that names the removed product behavior. A
repository-wide preference for MVP-first delivery never silently overrides an
explicit D3 production-complete request; surface the conflict for an owner
decision before reducing scope.

## Lifecycle

All depths use the same lifecycle, with evidence proportional to scope:

```text
PHASE MAIN BRIEF -> INDEPENDENT AUTHOR/IMPLEMENTER -> AUTHOR PREFLIGHT
                 -> INDEPENDENT REVIEW -> AUTHOR FIX -> REVIEWER RECHECK
                 -> PHASE MAIN OWNER GATE -> RECORD DURABLE KNOWLEDGE
```

For D0 and D1, phases may be brief and use existing artifacts. For D2 and D3,
make each phase output explicit. A phase may legitimately finish before
production code when an owner decision is required or the next phase needs a
fresh bounded context.

For D3, process quality outranks implementation speed. Complete each required
artifact phase with inspectable files, owner-facing decision options, and a
recorded owner decision before moving to the next phase. A summary can explain
an artifact, but the gate is satisfied by the artifact itself: existing files,
paths, rendered views, coverage notes, and the decision record.

For D3, the visual-to-implementation sequence is strict unless the owner grants
a scoped waiver: Visual Direction Approval, Selected Visual Direction
Translation plus an applicable UI Fidelity Asset Seed, Production UI Library
and Rendered Component Showcase, UI Library Approval, Production Raster Asset
Pack and approval when raster assets apply, Flows, Wireframes, Screen
Contracts, then Product-Surface Implementation Approval. Production UI-library
source and its showcase are the intentional pre-approval exception: product
routes and pages must not start before the later Product-Surface Implementation
Approval.

## D3 Phase Control Continuity

`docs/frontend/handoffs/README.md` is the only normative D3 phase-control
contract. Apply its P01-P13 catalog, fresh-main boundary, observer/manual modes,
owner-gate lifecycle, entry and rotation budgets, progress-loop guard, plain
owner action, state machine, recovery, and ledger literally. O38 tracks this
contract. No remembered chat or local alternative may replace its file-backed
handoff.

## Owner Steering Contract

At the start of meaningful frontend work, tell the owner that collaboration is
continuous: they may interrupt, correct an assumption, choose a different
proposal, change priorities, narrow or expand the requested direction, or
provide their own alternative at any time. Treat new direction as task input
that updates the process.

Repeat this invitation briefly when starting first-time design onboarding. The
owner may:

- answer the current questions in any order;
- skip a question or mark it irrelevant;
- replace suggested answers with their own direction;
- pause the questionnaire to discuss a concern or idea;
- point out that the agent is exploring the wrong direction;
- request synthesis or examples before continuing.

When the owner redirects the work, summarize the changed decision and its
effect on scope, remaining unknowns, and the next phase. Continue from the
owner's chosen format. Preserve unanswered material decisions in the
Uncertainty Check and seek evidence before acting on them.

## Collaboration Check

During the first applicable P01, establish
`docs/frontend/collaboration-policy.md` once for the repository. Reuse it in
later phases and future frontend tasks. For D2, establish it with the Task
Contract only when no valid policy exists. Record:

- availability: available / current-session / unknown;
- required collaboration interface;
- available worker or runtime choices;
- standing authorization by role: researcher, author, implementer, reviewer,
  rendered QA, and first-use reviewer;
- context-budget purpose and minimal input rule;
- read/write, command, network, rendering, security, privacy, cost, and
  concurrency boundaries;
- preferred phase-control topology and neighboring-session fallback;
- exact conditions that require owner reconfirmation.

Ask for this decision once and persist the answer. Before each assignment,
verify that its role, access, and cost fit the standing policy and record the
bounded brief; do not ask the owner again merely because a new phase or worker
starts. Reconfirm only when capability changed, the owner revoked permission,
or the task crosses a recorded security, privacy, write, cost, or external-
service boundary. Product, visual, wireframe, and implementation approvals do
not silently broaden the Collaboration Policy.

Delegation is also a context-budget contract. For D3, follow the exact
author -> independent reviewer -> author fix -> reviewer recheck loop in the
handoff protocol. The phase main writes briefs, records owner decisions, and
reads compact manifests and cited blockers only; it does not duplicate broad
research, authoring, implementation, rendering, fixes, or review, and it never
imports a long worker report. Missing file-backed output, missing independence,
or unavailable required contexts leaves the phase blocked unless the owner
grants the exact scoped waiver.

For D0/D1 work, use the existing Collaboration Policy when present. If none
exists, ask about delegation only when it provides a clear, specific benefit.

### Independent Execution Contexts

`Independent` means a separate execution context that did not author the
artifact it evaluates. It may be another agent, a subagent, an isolated or
neighboring session, or another compatible context. No particular agent
feature, vendor, CLI, or orchestration product is required. When the current
environment cannot create such a context, provide a self-contained brief for
the owner to run in a separate session and wait for the returned result.

A predecessor main, receiving phase main, or continuity observer is not an
independent reviewer for artifacts carried through that handoff. Those contexts
receive control history and approved decisions, so use another context for each
required independent review.

Independence does not mean maximum repository access. Give every independent
context only the role, product summary, artifacts, criteria, and source
material required for its bounded task. Do not make it read this complete
frontend subsystem, repository bootstrap, task history, changelog, or unrelated
contracts unless its assigned task is specifically to audit those sources.
Include all applicable `role_docs` paths from
`docs/agent/context_routes.yml`; those bounded schemas replace the full
subsystem for the worker's artifact and review roles.
Require a compact result containing the verdict, blocking findings, evidence,
and recommended fixes. On re-review, provide the previous blockers, changed
artifacts, and closure criteria instead of replaying the whole project history.
For long research, content, review, QA, or implementation work, require a
file-backed deliverable and a compact result containing its path, revision,
hash, status, verdict, blockers, and stable finding IDs. A summary without the
contracted artifact is incomplete. Worker-runtime mechanics belong to the
execution environment, not this frontend subsystem.

Keep these roles distinct:

- a Factual Product Researcher inspects only the canonical product, runtime,
  architecture, and implementation sources needed to establish how the product
  actually works before Product Surface Approval;
- a Contract Reviewer inherits and challenges contracts as a future frontend
  lead;
- a First-Use Reviewer experiences the rendered surface as a new user and is
  intentionally blind to repository and authoring context;
- a Content Author reads approved product and source context to write grounded
  interface content;
- a Copy Reviewer evaluates rendered words and user understanding without the
  author's rationale;
- an Implementation QA Reviewer verifies production behavior against approved
  contracts.

Four completion questions remain separate:

- **Functional QA:** does the requested journey work?
- **Visual QA:** does the rendered interface look intentional at relevant
  viewports and states?
- **Copy QA:** does the text explain, guide, support claims, answer objections,
  and sound specific to this product?
- **Product Completeness Review:** does the approved product surface contain
  the content, actions, states, and journey endpoints it promises?

## Context Loading

Apply the exact `control_first`, distinct `full_docs`, and `role_docs` routing in
`docs/agent/context_routes.yml`. Never recursively load artifact directories.
The handoff ledger is targeted evidence: read only events named by `current.md`,
except during final audit or ambiguous-control recovery.

Always begin with the repository bootstrap and each distinct routed frontend
`full_docs` path exactly once. After that read, load only additional sources
triggered by the task and not already present in `full_docs`:

- in D0-D2 execution contexts, the exact canonical product-source sections
  named by the Product Surface Model when the task needs them;
- compact generated manifests for affected flows, wireframes, screens,
  components, content, assets, decisions, and review evidence;
- exact phase-artifact paths assigned to the current bounded role;
- action/runtime sources of truth when the UI can mutate important state.

Do not reread a routed `full_docs` file merely because it is relevant to more
than one bullet, role, or phase concern.

After full reading, select the artifacts and rules that apply to the classified
depth and affected surface. Resolve contradictions before implementation.
Runtime configuration and real service state govern operational behavior;
approved product/design artifacts govern intended UI behavior until explicitly
superseded.

For D3, the phase main does not load the full canonical product source, repeat
repository discovery, or expand manifests into artifact bodies. It gives exact
source sections to the bounded researcher, author, implementer, or reviewer
that needs them and consumes only their returned manifests, stable finding IDs,
and cited blockers. A targeted source or artifact read by the main requires a
recorded contradiction or blocker that cannot be resolved from compact
evidence; it is not routine research or gate preparation.

## First-Use And Product Discovery

For D0-D2, inspect the applicable stack, component, asset, responsive, and
canonical product sources before deciding implementation; persist dated
evidence in `docs/frontend/context.md` and ask only about material unknowns.
Consult current authoritative documentation for non-trivial external APIs or
libraries.

For D3, P02 uses a separate Factual Product Researcher before Product Surface
authoring. Give it bounded repository entry points and exclusions, not the
frontend subsystem, visual proposal, or draft it might defend. Its file-backed
result identifies primary/supporting sources, real topology, active/historical/
deferred/absent capabilities, fact-level citations, contradictions, and open
decisions. The phase main reads only the manifest and then assigns the distinct
Product Surface Author defined below; Contract Review is not the discovery pass.

## Product Surface Model

`docs/frontend/product-surface-model.md` is the canonical frontend source of
truth for what product the site is building. It exists to prevent later agents
from reconstructing the product from chat, scattered decisions, or visual
artifacts.

Before D3 Product Surface Approval, create or update this file. When
collaboration is available and approved, a separate authoring context writes
the Product Surface Model from owner onboarding, canonical product sources, and
the Independent Factual Product Research artifact. The main design/control
context must not write the Product Surface Model. If an independent authoring
context is unavailable, stop and use a neighboring author session or obtain an
exact scoped owner waiver for single-context authoring.

Required D3 Product Surface delegation sequence:

1. A Factual Product Researcher finds the canonical product source, or writes a
   factual product research artifact if no sufficient source exists.
2. A separate Product Surface Author writes
   `docs/frontend/product-surface-model.md` from owner onboarding, canonical
   product sources, and the factual research artifact.
3. A separate read-only Contract Reviewer checks the Product Surface Model
   against the source list, frontend scope, exclusions, approval criteria,
   cited symbols and capabilities, source currency, counts, arithmetic, and
   internal consistency.
4. The Product Surface Author fixes blocking findings in the artifact.
5. The Contract Reviewer rechecks the changed artifact and previous blockers.
6. The main design/control context reads only compact manifests, verdicts, and
   cited blocker lines before presenting Product Surface Approval.

The researcher, author, reviewer, and phase main must have four distinct
recorded context identities. A phase main running in a child process is still
the phase main and cannot count as the researcher or author. After review, it
enters `gate-waiting` and remains active until the owner decision is recorded;
only then may it prepare P03 and finish.

The main design/control context must not read the full research artifact and
then author the Product Surface Model itself. It may create the briefs,
preserve the artifact paths, route blockers between contexts, and present the
owner decision once the delegated artifact is reviewed.

If the repository already has a canonical product source such as `product.md`,
`PRODUCT.md`, `project.md`, `PROJECT.md`, a PRD, a product spec, or a current
README product section, the Product Surface Model links to that source and
keeps only the frontend-specific delta, boundaries, approval status, and
conflicts. Do not duplicate the full product description. If no stronger
source exists, the Product Surface Model records the product surface directly
until such a source is created.

Record every canonical product source with path, revision or content hash,
currentness, precedence, and the facts it owns. Name one primary source or an
explicit precedence rule. Give every audience, job, route, screen, overlay,
system page, journey, endpoint, capability, data boundary, action boundary,
state family, genuine product exclusion, and content requirement a stable ID.
For a large product, keep the Product Surface Model as a compact root and put
concrete route/template/content mappings in a sharded Route And Template
Catalog using the schema in `docs/frontend/product-surface-model.md`. Every
route resolves to one current template, reserved `content_id`, Content Coverage
Keys, state families, navigation/discovery membership, and
responsive/accessibility family. P03 later resolves those content identities
to reviewed canonical leaves before Copy Approval.
Downstream content, flows, wireframes, screens, assets, components,
implementation units, and QA evidence reference those IDs and revisions
instead of repeating or silently changing the product map.

Separate genuine owner-approved product non-goals from `Phase Delivery
Boundaries`. The latter names mandatory later frontend work that the current
phase does not author. Product Surface Approval is blocked when wireframes,
visual work, content, the UI library, assets, system routes, implementation, or
QA appear as product non-goals merely because they occur later. It is also
blocked by contradictory lifecycle statuses or duplicated approval records.

Product Surface Model authoring output is file-backed. The authoring worker
completion message contains only a compact manifest: artifact path, source
links, Route And Template Catalog path/revision/hash and closure counts when
used, unresolved conflicts, and approval-readiness verdict. A separate
Contract Reviewer checks the Product Surface Model before Product Surface
Approval is presented to the owner. The review validates full production
coverage, including global shell, system routes such as not-found and access or
availability states when applicable, non-happy paths, content/data breadth,
search/discovery, media, responsive behavior, and accessibility. It cannot
approve a thin happy-path map under a broad production-complete request. For a
catalog-backed surface it also blocks nonzero missing, duplicate, orphan, or
unreviewed route/template/state/content mappings.

Infer what the repository already establishes. Ask the owner for information
that remains unresolved after repository discovery. When clarification is required, ask a small adaptive batch
of high-information questions and explain which decision each answer unlocks.

Visual polish, build success, screenshots, and console cleanliness validate
rendering quality. Content depth, corpus coverage, data correctness,
interaction breadth, and discovery quality need their own evidence. A beautiful
shell with shallow substance remains incomplete frontend work.

## Messaging System

Frontend copy is a product layer. Text explains,
sells when selling is appropriate, guides action, reduces doubt, supports
claims, and shapes how the product is perceived.

Every user-visible text fragment must do useful work. It should do at least
one of these:

- explain the product or the current state;
- move the user to the next meaningful step;
- answer an objection;
- provide proof for a claim;
- guide an action;
- reduce friction or uncertainty;
- strengthen product positioning.

Rewrite or cut any phrase whose product job is unclear.

Any frontend task that creates, changes, or approves user-visible text must
apply the full Messaging System. The pass covers Messaging Identity, Messaging
Contract, page or screen trajectory, text hierarchy, placement and density,
proof, objections, microcopy, anti-slop review, specificity, and Copy QA. For
D0/D1, apply the full pass to every user-visible text fragment in the affected
surface and its immediate context. For D2/D3, apply it to every user-visible
text fragment across every page, screen, state, navigation area, action,
microcopy point, data label, empty/error/loading/success message, and repeated
content pattern. Record the applied pass in the Task Contract, screen contract,
or review evidence.

For D3 P03, assign a write-scoped independent Messaging And Content Lead to
establish or update the compact Messaging Identity, integrate the root Content
Package manifest, and prepare the Copy Approval manifest. The phase main, not
the lead, assigns any additional disjoint Source-Grounded Content Authors for
large shards and routes their compact manifests to the lead. The lead is not
the phase main or any reviewer. For substantial D2/D3 content, give each author the approved
audience, Product Surface route/state/template records, Content Coverage Keys,
Messaging Identity and Messaging Contract, required depth, explicit shard
boundary, and only the canonical product sources needed for that shard. A
screen contract is an optional input only when one already exists; P03 must not
depend on the P10 screen-contract phase or author P10 early. Do not require the
Content Author to read the complete frontend subsystem.

The author writes a Content Contract Package as defined by
`docs/frontend/content/README.md`: a compact root or section manifest, finished
page-local production copy or links to an existing canonical content source,
and an exact shared UI copy registry for repeated chrome, actions, forms, and
states. Long copy exists once. A source map, claim/proof relationship, required
depth, unresolved fact, revision, and stable content ID live beside the copy or
in its compact manifest. Root, section, and leaf manifest edges pin revisions
and hashes. Every approved Content Coverage Key resolves exactly once to a
reviewed canonical leaf, and external content sources are pinned to immutable
versions or hashes. The phase main reads only aggregate manifests, verdicts,
and cited blockers.

Review every applicable content shard in another independent context. During
content authoring, the Copy Reviewer sees the final canonical copy, its factual
sources, approved audience and voice summary, required depth, and copy criteria,
but not the author's reasoning. It checks comprehension, completeness,
specificity, information depth, claim/proof proximity, objections, actions,
microcopy, and generic AI-generated language. An outline, synopsis, placeholder,
ellipsis, sample-only subset, or heading with token body text cannot pass as
finished content unless it is the literal owner-approved output. Counts and line
indexes are not semantic review. Rendered copy is checked again after
implementation. Content authorship and copy review do not replace owner
approval or final implementation QA.

After shard review, a separate package-level reviewer verifies transitive
manifest closure against the approved Product Surface and signs the compact
Copy Approval manifest defined in `docs/frontend/content/README.md`. P03 ends
only after that semantic and closure review passes and the owner records Copy
Approval. Zero-count closure is necessary but never sufficient without the
reviewer's content-quality verdict.

The text pass is exhaustive, not importance-based. Do not limit it to hero
copy, public marketing copy, important paragraphs, or high-risk messages. Every
visible fragment counts: navigation labels, breadcrumbs, tabs, filters,
buttons, links, headings, card titles, card bodies, badges, tooltips, alt text,
form labels, placeholders, helper text, validation messages, loading text,
empty states, error states, success states, disabled labels, table headers,
chart labels, legend text, metadata labels, footer text, legal text, command
labels, keyboard shortcut hints, toast text, dialog titles, menu items, and
repeated generated labels.

Before product-surface implementation, every planned page, screen, state,
action, and repeated copy family maps to a canonical content ID and revision.
Where the architecture permits, production renders or imports the canonical
content source directly. Otherwise implementation records the exact production
location for each ID and must stop on any proposed shortening, omission,
replacement, or unsupported expansion.

After implementation, reconcile each content shard and shared-copy family
against rendered evidence and source locations. Record expected revision/hash,
actual location, omitted or changed IDs, pass/fail verdict, and required fix.
A production page that follows the wireframe but drops approved depth, proof,
objections, state text, or source-backed explanations does not pass copy or
content coverage.

### Messaging Identity

Messaging Identity is the product's public voice. It transforms owner input
and product evidence into audience-facing language. It defines how the product speaks to
its audience.

Establish or update Messaging Identity when D3 work creates a new product
surface, when public-facing copy changes substantially, or when existing voice
rules need expansion for the task. Record:

- directness;
- formality or conversational level;
- technical depth;
- confidence level for claims;
- emotional intensity;
- allowed and disallowed humor;
- relationship to the user;
- phrases that sound natural for the product;
- phrases that sound foreign to the product;
- owner preference signals and how they were translated into product voice;
- private owner language that should be translated before public use.

Owner input can indicate preferences such as directness, more specificity,
less hype, example-led explanation, expert tone, or friendly tone. Translate
raw personal speech into product copy deliberately. Convert profanity, private
slang, fragmented chat phrasing, internal shorthand, and team-only jokes into
audience-appropriate language. The final source of truth is the product voice
approved for the audience and surface.

### Messaging Contract

For any page, screen, onboarding step, pricing surface, empty state, or public
product section with user-visible text, define the task of the text before
writing final copy. The Messaging Contract answers:

- why this page or screen exists;
- who it speaks to;
- what the user likely knows before reading;
- what state the user arrives in;
- what state the user should leave in;
- the main idea that must be understood;
- which messages must appear first;
- which messages can be revealed later;
- which objections must be answered;
- which proof is required;
- which action should feel natural after reading;
- where generic copy risk is highest.

Start from the semantic job of each block before using a page template. Decide
the semantic job of each block first. A hero usually orients quickly: what this is, who it is for, why it
matters, and what to do next. Mechanism, detail, proof, comparison, and
objection handling can appear later when the user is ready for them.

### Page Message Trajectory

A good page changes the user's state. Before writing or approving page copy,
identify the likely starting state and the intended leaving state.

Common starting states include:

- the user needs product orientation;
- the user doubts the claim;
- the user compares alternatives;
- the user needs trust signals;
- the user needs value clarity;
- the user needs a next step.

Common leaving states include:

- the user understands what the product or screen is;
- the user recognizes the problem or need;
- the user understands the mechanism;
- the user believes the promise or understands its limits;
- the user's main objection has an answer;
- the next step is clear;
- the user is ready to act or decide.

Use this trajectory as a sequence of semantic steps instead of a rigid marketing
formula:

```text
starting user state
-> problem or tension
-> product explanation
-> mechanism
-> proof
-> objection handling
-> action
```

Documentation, pricing, product pages, onboarding screens, empty states, and
application screens all need a trajectory. The tone may be quiet and
non-salesy, but the text still needs to know who is reading, what they already
understand, where they may get stuck, and what decision or action should become
easier.

### Text Hierarchy

Text needs hierarchy just as layout does. If a user reads only the primary
headline, section headings, and actions, they should still understand the
page's basic argument.

Use these levels:

- **Level 1: main promise.** The central claim or value of the page. It must be
  understandable outside the surrounding copy and specific to the product.
- **Level 2: section arguments.** Section headings move the explanation
  forward. They function as arguments.
- **Level 3: supporting copy.** Supporting text explains mechanism, examples,
  constraints, differences, objections, and proof. It should add substance
  beyond the heading.
- **Level 4: action copy.** Buttons, links, and form actions name what will
  happen next. Prefer concrete actions over vague labels.
- **Level 5: microcopy.** Small labels, helper text, errors, empty states,
  loading states, confirmations, badges, and tooltips reduce local friction.

### Message Placement And Density

The same message can succeed or fail depending on where it appears. Decide what
must be above it, below it, visually emphasized, short, expanded, repeated, or
left out.

Use density intentionally:

- hero copy is short, clear, and focused;
- problem sections may carry more recognition and tension;
- mechanism sections may be more detailed because the user is ready to
  understand how the product works;
- feature tiles stay short and specific, with one idea per tile;
- comparison and FAQ copy answers directly with concrete evidence;
- CTA copy is concise, confident, and action-oriented.

Repeat the main message only when each repetition adds a new angle: short
positioning, mechanism, example, proof, and action. Repeat only when the new
instance adds a new angle or useful emphasis.

### Proof System

Strong claims need proof near the claim. Proof can be visible product behavior,
an example, screenshot, workflow, comparison, file or data structure, user
scenario, result, constraint, or honestly stated limitation.

When a claim is strong, choose one proof action:

- add proof;
- weaken the claim;
- retire the claim.

Prefer mechanism-based value statements over interchangeable slogans. A claim
is usually stronger when it explains how the value appears, what workflow
changes, what result becomes possible, or what limitation is intentionally
accepted.

### Objection Map

Good copy anticipates why the user may hesitate before believing or acting.
Objections can live inside the section where they naturally arise.

Map:

- what may be unclear;
- what alternatives the user may compare against;
- what trust signal the user needs;
- what risk the user sees;
- what blocks the action;
- what simpler option the user may prefer.

Place answers according to timing. If doubt appears in the first viewport,
answer early. If doubt appears after mechanism explanation, answer near that
mechanism. If the objection is complex, move it to a comparison, detail, or FAQ
area.

### Microcopy

Microcopy is part of the user experience. It includes buttons,
links, navigation labels, form labels, placeholders, helper text, empty states,
errors, loading states, success states, tooltips, badges, and confirmation
messages.

Good microcopy answers a small user question at the moment it appears:

- error copy explains what happened, why it matters, and what to do next;
- empty-state copy explains why the area is empty, what will appear, and how to
  create the first useful object;
- loading copy explains the process when waiting is noticeable;
- success copy confirms what changed and gives a next step;
- button copy is specific about the resulting action.

The more important or risky the action, the less acceptable a generic action
label becomes.

### Anti-Slop Copy Review

Use semantic review instead of a static banned-word list. Words gain quality
from their job, specificity, support, placement, and proportion. Bad copy is
empty, interchangeable, unsupported, misplaced, or inflated.

During review, ask:

- does this explain the product or current state?
- does this move the user forward?
- does this answer an objection?
- does this provide proof?
- does this help an action?
- does this reduce friction?
- is this sentence specific to this product surface?
- is there a mechanism, example, result, or limitation?

If a sentence can be moved unchanged to a different product, agency, template,
productivity app, or generic software site, increase its specificity. Add specificity through mechanism, workflow, concrete user problem,
example, visible behavior, limitation, difference from alternatives, or
specific result.

### Product Surface Approval

Required for D3 and for D2 changes that materially expand navigation, journeys,
or capabilities. Present:

- Product Surface Model path and revision;
- Independent Factual Product Research brief, researcher/context, canonical
  sources, accepted factual map, and unresolved contradictions for D3;
- in-scope users, journeys, screens, and states;
- release scope, genuine product non-goals, and separate phase-delivery
  boundaries;
- global/system routes and production-completeness coverage;
- scope assumptions;
- unresolved decisions;
- the exact next phase unlocked by approval.

Record approval or a scoped waiver in a frontend decision file.

## Design Onboarding

Run deep one-time onboarding when D3 work needs an established Design Identity,
or when the existing identity needs expansion for the requested product surface.
The established practice is exactly 25 questions in five rounds of five,
followed by an Uncertainty Check.

After P01 control acceptance and its `PROCEED` receipt, begin the normal P01
sequence immediately. If `docs/frontend/collaboration-policy.md` is not
established, ask its one standing collaboration question, record the answer,
then start onboarding round one. If it is established, do not repeat the
question. Never ask for a frontend waiver instead of starting onboarding.

The five-round, 25-question protocol is mandatory. Every question must resolve
a material design or product decision; ask each question once and use
repository evidence for established facts. Later rounds must adapt to earlier
answers. Explain abstract questions with concrete alternatives while allowing
a custom answer.

Before the first round, remind the owner that the questions are navigation and
that their answers can reshape the path. They may redirect the discussion,
introduce their own design direction, choose a different framing, skip
questions, or ask the agent to explain why an answer matters. Adapt the
remaining rounds to that steering.

Cover, as relevant:

- product purpose, audience, expertise, and usage context;
- desired emotional response, personality, and perceived quality;
- information density and content/data characteristics;
- desired and conflicting visual associations;
- reference properties the owner likes or dislikes;
- platform and device priorities;
- motion, imagery, illustration, and iconography;
- brand and accessibility constraints;
- implementation stack, deployment, and maintainability preferences when the
  repository leaves them open;
- success criteria and failure criteria.

After each round, summarize newly established facts, cite their source as owner
input, and identify remaining uncertainty. Treat onboarding completion and
implementation authorization as explicit gates.

### Uncertainty Check

After question 25, record:

```md
## Uncertainty Check

- Product scope:
- Stack:
- Data and API:
- Auth and permissions:
- Content:
- Visual direction:
- Interaction and states:
- Accessibility and responsive behavior:
- Success criteria:

## Verdict

- Resolved evidence:
- Remaining material unknowns:
- Next phase:
- Required owner gate:
```

Do not add a sixth onboarding round. Record any remaining material unknowns in
the Uncertainty Check and resolve them through repository evidence, the
Factual Product Researcher, or a later owner decision at the applicable gate.
P01 then prepares and transfers control to P02. Preliminary Identity and Visual
Exploration begin only in P04, after P02 Product Surface Approval and P03 Copy
Approval reach their stop conditions.

## Preliminary Identity

Synthesize a preliminary identity from repository evidence and owner answers.
Label inference separately from explicit owner decisions. Cover core feeling,
personality, desired perception, visual tension, density, candidate signature
traits, and anti-associations. This is input to exploration before the final
design system.

## Visual Exploration

Every D3 P04 creates exactly five rendered raster Visual Direction Boards. A
later D3 visual reset still creates five unless the owner explicitly waives O10
with a scoped `FRONTEND WAIVER:` message.
The five boards must be meaningfully different but plausible interpretations
of the same product evidence. Each board must define and visibly demonstrate
its own composition, visual metaphor, signature trait, information-density
approach, illustration or imagery treatment, and component styling logic.

Each Visual Direction Board is a raster Design System Showcase, Component
Showcase, Component Gallery, or Component Playground for a possible product
direction. It is a rendered UI artifact that demonstrates how real interface
parts would look and behave together before the implementation stack is fully
known. Illustration, mascot, hero art, mood imagery, or brand art may support
the board only when they appear inside or alongside representative UI
structure.

Each board is a rendered UI artifact plus concise notes containing:

- hypothesis and product rationale;
- composition, hierarchy, typography, density, geometry, surfaces, and color;
- imagery, illustration, iconography, and motion direction where relevant;
- representative UI fragments from the requested surface;
- a component showcase area covering navigation, controls, forms, content
  tiles, lists/tables, data visualization, semantic states, overlays, and
  other primitives used by the product;
- example states such as normal, hover/focus, selected, loading, empty, error,
  disabled, overflow, and partial-data states where relevant;
- what the board leaves outside its direction;
- desktop and mobile viewport sizes inspected.

Each board must contain clearly identifiable desktop and mobile product frames,
not only an outer moodboard collage. Those frames become candidate reference
compositions for later image-to-image comparison. Use approved content or
clearly generic non-factual labels inside a board. Commands, integrations,
technology names, capability claims, and operational states must be grounded in
the approved product/content sources; attractive fictional product facts are
blocking defects.

Generate every board as a raster image. Place generated or assembled imagery in
a UI showcase context that proves component composition, hierarchy, state
handling, and responsive behavior. HTML, CSS, JavaScript, SVG, screenshots of
locally coded pages, and text-only descriptions are not Visual Direction Board
artifacts. If raster image generation is unavailable, the Visual Direction
Board gate is blocked; report the missing capability and do not substitute
another format or request Visual Direction Approval.

Every board must visibly express the Preliminary Identity traits applicable to
its hypothesis. If the identity calls for characters, illustration, physical
metaphors, distinctive imagery, unusual geometry, or another signature trait,
those properties must appear in the raster board itself rather than only in
its notes. A board that merely names an identity trait does not demonstrate it.

The write-scoped independent Visual Direction Author first synthesizes the
Preliminary Identity from approved inputs, then generates every board and
performs author preflight. A separate image-capable reviewer must open each raster itself and
inspect the desktop/mobile frames for overlap, blank areas, unreadable text,
broken composition, unsupported product claims, and insufficient component
evidence. The phase main neither generates nor visually inspects the boards; it
consumes the author and reviewer manifests. Boards are direction studies before
production assets.

Visual Direction Board completion requires five existing generated raster
artifacts with immutable paths, revisions and hashes, inspected desktop and
mobile frames, visible representative UI fragments, component showcase
coverage, state examples, and concise comparison notes. Text-only descriptions,
mood summaries, written design contracts, HTML pages, and screenshots of coded
pages do not satisfy this gate. Written notes support the discussion after the
boards exist. This gate is complete when the raster artifacts and independent
image-inspection evidence are present.

Before Visual Direction Approval, present a board evidence table. For each
board, include immutable artifact path, revision, content hash, dimensions,
desktop/mobile reference-frame bounds, format, product hypothesis,
representative UI fragments shown, component showcase coverage, state examples,
reviewer context, review report path/revision/hash and verdict,
desktop/mobile inspection evidence, strengths, trade-offs, and what the
direction leaves out.

### Visual Direction Approval

Ask the owner to select, mix, decline, or request iteration. Present the board
paths, the decision dimensions, and the consequences of each choice. Persist
approval and counterexample signals in
`docs/frontend/visual-references/interpretation.md`; store selected assets in
the corresponding signal directories.

If the owner selects a mix of multiple boards, generate or assemble one final
combined raster direction board before downstream work. The combined board
becomes the single selected visual reference. Do not ask production
implementation to reconcile multiple competing boards without this merged
reference or a written owner waiver.

Record incidental generated-image details as observations, not owner rules. A
mascot species, object, font category, motif, or layout detail becomes mandatory
or forbidden only when the owner selected it explicitly or the reviewed visual
translation demonstrates that it is necessary to the approved identity. Do not
turn an author's preference into an owner constraint.

Finalize Design Identity and Design System after this approval passes or the
owner records a scoped waiver.

### Selected Visual Direction Translation

After Visual Direction Approval, translate the selected raster direction into
an implementation-facing contract before writing production pages. Record:

- selected board or merged-board immutable path, revision, hash, dimensions,
  and the desktop/mobile reference-frame bounds;
- visual properties that are mandatory in production;
- visual properties that are mood-only or forbidden to copy literally;
- component families implied by the board;
- layout, density, surface, border, color, typography, illustration, icon, and
  motion rules needed to reproduce the direction;
- asset needs for hero media, section art, empty/error states, diagrams,
  thumbnails, mascots, or product imagery;
- counterexamples from rejected boards and generated artifacts;
- visual fidelity checks the implementation and QA contexts must run.

Include a finite Signature Traits Matrix. Every row names the exact board
region or crop, the observed composition/typography/geometry/color/asset trait,
its production rule, a forbidden counterexample, and an observable pass
condition. Preserve measured relative proportions, hierarchy, and density from
the selected frame. Do not weaken a visible requirement into a permissive
`either/or` threshold that allows a materially different composition.

The translation author and its separate image-capable reviewer must both open
the selected raster and record the inspection method, revision, hash, and
regions viewed. Reading metadata, notes, CSS, or a prior evidence table without
viewing the image cannot pass this contract. Review first judges the image and
translation holistically, then checks the matrix. It must identify invented
constraints, missing signature traits, generic substitutions, and any rule that
would permit a visibly different product identity.

A write-scoped independent Visual-System Author writes the translation, final
Design Identity/System revisions, and the UI Fidelity Asset Seed when required.
The phase main supplies the brief and consumes only the author's manifest and
the separate review verdict; it does not write or visually inspect P05
artifacts.

When the reference frame depends on custom typography, iconography,
illustration, mascots, textures, diagrams, or other non-generic assets, the P05
Visual-System Author also produces a minimal UI Fidelity Asset Seed. It contains
only the licensed or generated samples and rules needed to reproduce the reference composition in
the production UI-library showcase. A generic placeholder cannot replace a
signature seed asset. If no seed is needed, the image-capable reviewer records
why the frame remains reproducible without one. The complete Production Raster
Asset Pack remains a later post-showcase phase.

This translation is the bridge between generated image evidence and working
interface code. A selected raster board is not enough by itself; production
must follow the translated component system and visual fidelity rules.
After this translation is written and reviewed, the next controlling D3 gate is
UI Library Approval. Do not start Flows, Wireframes,
Screen Contracts, the complete Production Raster Asset Pack, or product-surface
implementation until UI Library Approval passes or the owner grants a scoped
waiver for that specific phase order.

### Production UI Library And Rendered Component Showcase

For D3 work, assign a write-scoped independent UI Library Implementer to build
the approved visual direction into a real production UI library or component
system before building production pages. The phase main provides the stack and
artifact brief and reads only compact implementation/review manifests; it does
not write, fix, render, or visually inspect the library or showcase. This is not a
throwaway HTML demo, visual-only mockup, screenshot reproduction, or isolated
showcase artifact. The production pages must import, compose, or otherwise use
the same approved components, tokens, primitives, assets, state styles, and
layout patterns demonstrated in the showcase. This can wrap an existing
owner-approved UI library, design system, framework primitives, or local
components. If the owner wants a ready-made UI library, record how its
primitives map to the selected visual direction and where custom styling,
tokens, slots, or components are required. Do not treat a third-party library
as the product identity.

P06 is allowed and required to create production UI-library source, its
dependencies, tokens, assets from the approved UI Fidelity Asset Seed when
required, and its rendered showcase before Product-Surface Implementation
Approval. When the seed is not required, cite its approved independent
non-applicability record. That later
gate blocks product routes and page composition, not the production primitives
needed to make the visual contract real.

Before creating the UI library or component showcase, obtain the required stack
contract for the production frontend: framework/runtime, styling approach,
component library preference if any, package boundaries, target deployment or
static output constraints, asset handling, accessibility expectations, and
repo-local build/test commands. If the owner wants the agent to choose, record
that as an explicit owner decision and choose conservatively from repository
evidence rather than vendor preference.

Create a storybook-like rendered component showcase before production page
implementation. The showcase renders the actual production UI library, not a
parallel approximation. Everything presented as a reusable button, field,
table, card, navigation item, overlay, badge, diagram node, layout, or state is
an exported production primitive or composition at a named source path. Inline
showcase-only markup or styling does not satisfy that family.

Maintain a compact coverage matrix from Product Surface/content requirements to
production module, states, accessibility behavior, responsive behavior,
consumer, showcase address/state, revision, and hash. Demo data is allowed;
demo-only structure and styling are not.

The rendered showcase has two clearly separated purposes:

1. A **fidelity scene** composes only registered production primitives and the
   UI Fidelity Asset Seed when required, or cites its approved non-applicability
   record, into the same representative screen, viewport/aspect ratio,
   hierarchy, density, and signature composition as the selected desktop and
   mobile reference frames.
2. A **component catalog** demonstrates shell, navigation, buttons, links,
   forms, search/filter controls, cards, article layouts, badges, tables or
   lists, diagrams or media frames, overlays, empty/loading/error/success/
   disabled states, focus/hover/selected states, responsive variants, and every
   signature trait.

These may be separate routes or stable states of one rendered artifact. Do not
place phase IDs, debug badges, control metadata, or authoring commentary in the
user-visible fidelity scene unless the selected production UI genuinely
requires them.

The UI Library Approval gate is the next controlling D3 gate after Selected
Visual Direction Translation. It passes only after independent source/reuse
review and independent image-capable visual review. Neither role is the phase
main or the UI Library Implementer. The source reviewer proves that the
fidelity scene and catalog build successfully, import the registered production
components, contain no showcase-only substitute implementations, and cover
every required component family, state, focus/keyboard behavior,
accessibility behavior, responsive variant, and declared consumer. The visual
reviewer receives only a short neutral product description at first, the
selected raster reference frames, fresh immutable fidelity-scene captures for
all six required viewport classes, and fresh immutable component-catalog
captures for all six classes and every applicable stable state fixture. The
desktop/mobile fidelity captures use the declared reference viewport/aspect
ratios for direct comparison; the other four prove that the same signature
composition transforms deliberately rather than collapsing between them.

The visual reviewer must open the images and perform a first-pass holistic
side-by-side comparison before reading the translation checklist. Where the
images share geometry, use overlay, blink, crop, or difference inspection when
available. Then review composition, hierarchy and density, typography, geometry
and surfaces, color roles, borders and shadows, icon/illustration/assets,
responsive behavior, and every Signature Traits Matrix row. CSS, DOM, source,
tokens, accessibility trees, and feature presence cannot prove visual fidelity.
A pass lists the three largest remaining visible differences and explains why
none is material. A missing signature trait, generic/template appearance, stale
or absent viewport/state capture, broken component layout, clipped or unreadable
catalog content, or any unexplained material image difference blocks approval
even when the code is reusable and accessible. The reviewer opens and inspects
both fidelity-scene frames and the complete catalog evidence matrix; reviewing
the scene alone cannot approve the library.

Every reviewed reference and capture is identified by unique path, revision,
hash, dimensions, viewport/state, and capture time. Do not overwrite evidence.
Any UI or asset fix creates new captures and invalidates the affected visual
verdict until re-review. Production pages do not start before owner UI Library
Approval or a scoped `FRONTEND WAIVER:`.

After production pages are implemented, QA must verify that pages use the
approved UI library/components instead of recreating visually similar one-off
markup. Any production page that bypasses the approved primitive system must
record an approved exception or be treated as a visual fidelity defect.

### Production Raster Asset Pack

P07 creates this pack after UI Library Approval when the selected direction
needs raster imagery, illustration, characters, physical metaphors, product
media, thumbnails, or a stable generation language. A write-scoped independent
asset author and separate image-capable reviewer follow
`docs/frontend/assets/README.md`; the phase main reads only their manifests and
presents Production Raster Asset Pack Approval. Otherwise the independent
non-applicability evidence required for O15-O16 closes P07.

## Final Design Identity And Design System

After Visual Direction Approval, finalize:

- `docs/frontend/design-identity.md`: core feeling, personality, desired
  perception, visual tension, signature traits, and anti-identity;
- `docs/frontend/design-system.md`: typography, spacing, color semantics,
  surfaces, borders, radii, elevation, density, iconography, motion, forms,
  tables, charts, breakpoints, and UI states.

Every rule should include either evidence, an approved rationale, or an
existing implementation reference. Present defaults as implementation choices
with product rationale. UI libraries supply primitives while product identity
comes from approved decisions.

Signature traits must aid recognition while preserving usability.
Anti-identity records visual or interaction outcomes that would contradict the
approved direction.

## Reference Decomposition

Treat references as evidence for local principles. For each reference,
record:

- useful property;
- property to leave behind;
- product-specific element to translate rather than copy;
- the local product principle supported by the reference.

## Component Strategy

Before creating a component, check in this order:

1. existing project component;
2. existing library primitive;
3. composition of existing primitives;
4. new component or primitive.

Record reusable components in `docs/frontend/component-registry.md` with
location, purpose, states, accessibility behavior, constraints, consumers, and
evidence that a new abstraction is warranted.

## UX Flows

P08 creates or updates route-complete navigation, journey, permission, state,
feedback, recovery, and endpoint contracts under `docs/frontend/flows/` before
product-surface implementation. The write-scoped independent Flow Author and
separate Contract Reviewer follow `docs/frontend/flows/README.md`; the phase
main handles only their brief, manifests, blockers, and verdict. An unchanged
D0 visual edit may reference existing flows.

## Wireframes

P09 uses the complete role contract in `docs/frontend/wireframes/README.md`.
Its persistent artifact is a grayscale, route-complete, directly openable HTML
W1 clickable wireflow with stable prepared states and realistic meta-text, not
a screenshot or early production application. Every concrete route remains
indexed, reachable, mapped to content, and assigned to a reviewed template or
explicit exception; screenshots are immutable review evidence only.

Do not add brand styling, final assets/copy, real search, data fetching,
persistence, or other production algorithms to prove a wireframe. A
write-scoped independent Wireframe Author creates and preflights the package;
separate First-Use and image-capable reviewers traverse it and inspect the six
viewport classes and applicable prepared states. The phase main receives only
their coverage manifests, immutable evidence, verdicts, and cited blockers.

### Wireframe Approval

Required for D2/D3 product-surface work and lower-depth changes that alter a UI
contract. Approval is blocked until the route/template index, clickable primary
journeys, state matrices, deferred production behavior, content requirements,
six-viewport coverage or owner waiver, First-Use Review, and independent visual
QA cover every route and exception. Present the compact closure, immutable
evidence indexes, open questions, and exact scope the decision unlocks.

## Screen Contracts

P10 uses `docs/frontend/screens/README.md`. Its write-scoped independent Screen
Contract Author creates one contract per unique route template plus explicit
exception contracts, while every concrete route maps its Surface ID, content,
states, journeys, wireframe address, component consumers, and production unit.
A separate Contract Reviewer validates full cross-package closure; the phase
main reads only compact manifests, verdicts, and cited blockers.

## Independent Contract Review

Every new or materially changed frontend Markdown contract must receive an
independent read-only review before it is presented for owner approval, used to
authorize implementation, or declared complete. Review the complete applicable
contract package, not a sample. This includes Product Surface Approval records,
messaging, identity, design system, flows, wireframe index and state matrix,
screen contracts, Action Contracts, Wireframe Conformance Contracts,
implementation briefs, and consequential frontend decisions.

Phase-control handoff records are operational continuity metadata, not product
or implementation contracts, and do not recursively require Independent
Contract Review. Review them only when the assigned task is a control-protocol
or instruction-compliance audit.

The independent reviewer adopts the role of a potential frontend lead joining
the project after the current session. Assume this lead must understand,
challenge, implement, maintain, and defend the frontend without access to the
authoring agent's implicit context. The reviewer checks:

- whether every decision, invariant, boundary, unknown, and source of truth is
  explicit enough to inherit;
- contradictions, stale statuses, missing mappings, untestable acceptance
  criteria, and ambiguous ownership;
- whether the HTML wireframes and Markdown contracts agree;
- whether the implementation and QA briefs can be executed literally;
- whether the package preserves approved scope, messaging, responsive,
  accessibility, content, discovery, state, and action requirements;
- where a future lead would be forced to guess.

Prepare a self-contained Frontend Lead Contract Review Brief listing every file
to read, approval scope, prior decisions and waivers, HTML wireframe addresses,
required cross-file mappings, sources of truth, review rubric, severity rules,
and required finding format. Use a delegated read-only reviewer when available.
If delegation is unavailable, stop and ask the owner to run the brief in a
fresh session and return the findings. The authoring session fixes blocking
findings, then repeats independent review of the changed package. Contract
review and production QA are separate gates and require separate evidence.

The Contract Reviewer reads the complete applicable contract package, not the
complete frontend instruction system by default. Include this subsystem only
when instruction compliance is itself in review. Do not include changelogs,
task trackers, repository-wide instructions, or implementation history unless
one is a named source of truth for a decision under review.

## Independent First-Use Review

Before Wireframe Approval for D2/D3 and again before final completion, run an
Independent First-Use Review in a separate context. Simulate a person in the
approved audience encountering the surface for the first time.

The First-Use Reviewer receives only:

- a neutral two-to-five-sentence description of what the product is and who it
  serves;
- the rendered surface and instructions needed to open it;
- concrete first-use tasks or questions;
- the required finding and evidence format.

Explicitly forbid this reviewer from reading repository files, frontend
instructions, contracts, task history, changelogs, author notes, or prior
reviews. The reviewer evaluates what the interface itself communicates:
orientation, comprehension, perceived purpose, navigation, information scent,
visual hierarchy, terminology, trust, obvious actions, confusion, and unmet
expectations. It does not review contract completeness or implementation
internals. Record observed failures separately from suggested solutions so the
design/control context decides the fix.

First-Use Review does not replace Wireframe Rendered Visual QA. Before
Wireframe Approval, run a separate independent rendered review using a browser
or screenshots at every required viewport class and applicable prepared state.
Give this reviewer only the neutral product description, clickable wireflow,
concrete journeys, viewport list, and visual finding format. Require inspection
of alignment, spacing, hierarchy, text containment, wrapping, clipping,
horizontal overflow, overlap, stable dimensions, reachable navigation, primary
actions, and responsive transformations. DOM, accessibility-tree, source-code,
or stylesheet inspection alone is not sufficient visual inspection.

Any overlap, clipped or unreadable required text, horizontal page overflow,
unreachable approved screen, dead primary action, broken route/state
transition, or uninspected required viewport is a blocking finding. A pass or
approval-readiness verdict is forbidden until blockers are fixed and the
affected viewports and journeys are independently re-rendered and rechecked.

## Action Contract

Before implementing any UI/API path that can move money, change permissions,
deploy software, alter an external account, destroy data, or perform another
material mutation, define:

- actor and permission model;
- confirmation behavior;
- exact mutation and idempotency expectations;
- runtime source of truth;
- audit record;
- success feedback;
- failure, retry, and recovery behavior;
- rollback or compensating action when available;
- validation and operator-visible states.

This contract is required regardless of visual depth. Production runtime should
use explicit non-interactive confirmation and recovery paths.

## Product-Surface Implementation Approval

Before D3 product routes/pages are implemented, and before D2 implementation
when product or visual decisions required owner approval, present one bounded
summary:

During P11, the phase main prepares the self-contained Product-Surface
Implementation Brief from compact approved manifests. A write-scoped
independent Implementation Planning Author creates the reviewed route
implementation manifest; a separate read-only Contract Reviewer checks that
manifest, the brief, and the complete cross-package mappings before the owner
gate. The phase main reads only their compact verdicts and cited blockers.

```md
PRODUCT-SURFACE IMPLEMENTATION APPROVAL RECORD

- Outcome and scope:
- Explicit scope boundaries:
- Stack and sources of truth:
- Approved Product Surface Model revision:
- Approved Route And Template Catalog revision/hash and closure:
- Independent Factual Product Research and source map:
- Approved Visual Direction revision:
- UI Fidelity Asset Seed or reviewed non-applicability:
- Approved flows:
- Approved route-to-wireframe index revision/hash and closure:
- Approved route/template screen-contract index revision/hash and closure:
- Independent Contract Review and reviewer/session:
- Independent First-Use Review and reviewer/session:
- Independent Wireframe Rendered Visual QA and reviewer/session:
- Source-Grounded Content Author and source map:
- Approved Content Contract Package and shared UI copy registry:
- Copy Approval manifest revision/hash and closure:
- Independent Copy Review:
- Approved Production UI Library, fidelity scene, and component catalog:
- Independent source/reuse and image-fidelity reviews:
- Wireframe Conformance Contract:
- Product-Surface Implementation Brief:
- Action Contract, if applicable:
- Implementation units:
- Acceptance evidence to collect:
- Known risks and assumptions:
```

Product-surface implementation begins after approval or a recorded scoped
waiver. For D3,
request this approval after Product Surface Approval, Visual Direction
Approval, Selected Visual Direction Translation, UI Library Approval,
Production Raster Asset Pack Approval when raster assets apply, finalized
Design Identity and Design System, the approved Content Contract Package and
Copy Review, flows, rendered HTML wireframes, screen contracts, Independent
Contract Review, Independent First-Use Review, Source-Grounded Content
Authoring and Independent Copy Review, and the Action Contract when relevant,
and their decision
records exist at named paths.
The approval summary
links to one reviewed route implementation manifest that maps every approved
page or meaningful screen to its template, flow, wireframe address,
screen-contract path, UI-library components, selected visual translation,
asset-pack reference when applicable, canonical content IDs/revisions, content
coverage, conformance invariants, and implementation unit. The bounded approval
record contains the manifest path/revision/hash and aggregate closure rather
than repeating every route row. A
waiver must name what is waived, why, what remains required, and the next
active gate.

For D3, commands, file creation, source generation, or code edits that implement
production product routes, screens, or their composition begin only after
Product-Surface Implementation Approval or a valid `FRONTEND WAIVER:` that
names the skipped approval and remaining evidence. Phase-scoped contract,
Markdown, raster, content, UI-library, flow, HTML-wireframe, screen-contract,
review, and control artifacts required by P01-P11 remain allowed only inside
their owning phase. The approved P05 UI Fidelity Asset Seed and P06 production
UI-library source, dependencies, showcase routes, and evidence are therefore
allowed before this gate; product-route/screen composition is not. Approval of
a questionnaire answer, product direction, stack choice,
language, page list, visual style, visual board, raster asset pack, UI library,
component showcase, wireframe, search requirement, or copy direction moves the
artifact sequence forward and does not approve product-surface implementation.

Wireframe Approval freezes structure and interaction intent; it does not
authorize product routes/pages or implementation inside the design/control
context.

## Product-Surface Implementation

Product-surface implementation is separate work from the context that authored
or approved the design and contract package. After Product-Surface
Implementation Approval, assign the already approved self-contained
Product-Surface Implementation Brief and route implementation manifest to a
write-scoped independent implementation context. The design/control context does not write production
frontend code. If no independent execution context is available, stop;
do not collapse design, implementation, and QA into one context.

The Product-Surface Implementation Brief includes repository and execution context,
approved scope, every contract and HTML wireframe address, exact allowed files,
implementation units, Wireframe Conformance Contract, Selected Visual
Direction Translation, approved UI Library/component showcase paths, Production
Raster Asset Pack paths when applicable, approved content package paths and IDs, sources
of truth, commands, acceptance evidence, checkpoint expectations, known risks,
and the required response format. The implementation worker may edit its
authorized files and create coherent checkpoints. It reports every proposed
contract deviation instead of silently implementing it.

The implementation session implements against the approved contract. Preserve
established stack and components. Keep domain and decision logic separable from
presentation code where practical. Missing data must produce an explicit
loading, empty, blocked, partial, or error state; represent operational
availability from real evidence.
For D3, production output must be production-grade across the whole approved
surface: complete routes and system states, rich approved copy, real approved
assets, responsive layouts, accessible controls, useful empty/error/recovery
paths, maintainable component boundaries, and direct fidelity to the approved
wireframes, content package, UI library, and selected visual direction. A
working shell, partial happy path, placeholder content, generic generated copy,
or page that only resembles the wireframe structurally is not complete.

### Wireframe Conformance Contract

Wireframe Approval freezes structural and behavioral invariants. For every
page, screen, and applicable state, record what production must preserve:

- route and journey position;
- region, section, and information hierarchy;
- primary action, navigation, and journey endpoint;
- required components, content requirements, and navigation behavior;
- interactions, state transitions, feedback, focus, and recovery;
- responsive transformations and accessibility relationships;
- placement of critical proof, warning, confirmation, and recovery content.

Final color, typography, detailed spacing, illustration, elevation, motion,
source-backed copy, and component implementation may evolve through the
approved Design System. Production must not copy gray-box styling merely
because the wireframe uses it. Visual evolution may not change a frozen
structural or behavioral invariant.

Before product-surface route/screen implementation, create a mapping from each
approved HTML wireframe page/state/region to its production route, component or
module, implementation unit, invariant, and verification method. When
implementation would change a frozen invariant, stop production work and invoke
the `Contract Regression And Re-entry` protocol in
`docs/frontend/handoffs/README.md`. Return to the earliest owning phase with a
fresh main, assigned authors, independent review, and renewed affected gates;
the P12/P13 context must not edit the HTML wireframe or earlier contracts.

After implementation, compare each production page and applicable state with
the approved HTML wireframe. Record every invariant with wireframe evidence,
production evidence, and pass/fail verdict. An unexplained structural or
behavioral difference blocks completion even when the production interface is
visually polished.

Keep implementation inside the approved scope. When implementation reveals a
material contract defect, use the same regression/re-entry protocol. Preserve
the prior decision as history, supersede only the affected revision and its
dependent authorizations, and obtain renewed approval for the replacement
before implementation resumes.

## Responsive Design Pass

Responsive quality is intentional composition beyond overflow control.
Inspect six viewport classes for every D2/D3 frontend surface and for any D0/D1
change whose layout can be affected:

- narrow mobile below 640px;
- mobile-wide or small tablet at 640px and above;
- tablet at 768px and above;
- desktop at 1024px and above;
- large desktop at 1280px and above;
- wide desktop at 1536px and above.

Choose concrete viewport sizes inside each class and record them. Add extra
project-specific viewports when analytics, target devices, embedded frames,
kiosks, dashboards, or dense data displays require them.

For each viewport, verify:

- hierarchy and primary action remain clear;
- controls remain usable and reachable;
- content density is appropriate;
- tables, charts, navigation, and overlays transform deliberately;
- text remains readable;
- focus order and keyboard interaction remain coherent;
- viewport is free of clipping, overlap, accidental whitespace, and hidden required content.

Record why each major transformation best preserves the function of the
desktop or source composition.

## Functional QA

Build an Interaction Inventory before rendered QA. Include every element or
region that a user can click, tap, focus, type into, drag, scroll as a local
control, hover for information, open, close, expand, collapse, select, submit,
copy, navigate through, or operate with a keyboard shortcut. Include visual
areas that look interactive and stateful areas expected to emit events,
navigation, data loading, feedback, animation, UI changes, route changes, URL
parameter changes, network requests, copied content, focus movement, or visible
state changes.

The implementer prepares the inventory; independent QA exercises it. The
inventory must be concrete enough for a literal reviewer with no product
intuition. For each item, record:

- stable selector or visible label;
- page, screen, and state where it appears;
- user action to perform;
- expected response;
- expected URL or route change;
- expected state change;
- expected request, event, or copied value when observable;
- keyboard and focus expectation;
- loading, success, failure, disabled, empty, overflow, and recovery behavior
  when applicable;
- evidence required to mark it passed.

Independent QA must exercise every inventory item in the rendered interface:
buttons, links, tabs, menus, forms, filters, toggles, dialogs, accordions,
content tiles with click behavior, maps, charts, tables, search fields,
pagination, command controls, copy buttons, overlays, drawers, media controls,
keyboard/focus behavior, and post-interaction states. For each item, record
expected response, actual response, URL or route changes, state changes,
emitted request or event when observable, focus behavior, loading feedback,
success feedback, and recovery behavior.

Validate success, failure, loading, empty, disabled, overflow, and partial-data
paths that are reachable in scope. Verify every internal navigation target,
external link target policy, anchor, back/forward behavior, and stateful URL
parameter that the surface creates. A screenshot, clean console, and successful
build support QA evidence and do not replace interaction coverage.

Use automated checks where behavior can be asserted reliably. Inspect the
rendered interface in an available rendered environment for interaction,
screenshots, and user-flow QA. Pair code compilation with browser inspection.

## Independent Frontend QA Gate

Frontend implementation QA is independent work. The same agent/session that
implemented the frontend may run local preflight checks, builds, linting,
typechecks, route smoke tests, and exploratory sanity checks, but those checks
do not satisfy final QA and must not be presented as completion evidence.
The QA reviewer/session is also separate from the design/control session and
the implementation worker/session. Design, product-surface implementation, and
final QA therefore use distinct contexts unless the owner grants a scoped
`FRONTEND WAIVER:` naming the collapsed roles and accepted risk.

After implementation and before claiming the frontend task complete, run the
Independent Frontend QA Gate:

1. Prepare an Independent QA Brief.
2. Use an independent read-only QA context allowed by the standing
   Collaboration Policy.
3. If no independent context is available, stop and ask the owner to open a fresh session
   for QA. Provide the exact prompt that would have been given to the delegated
   reviewer and ask the owner to return the findings.
4. Fix every blocking finding in the implementation session.
5. Repeat independent QA on the changed surface until blocking findings are
   cleared or the owner explicitly grants a scoped `FRONTEND WAIVER:`.

The phase main decides the number of QA workers from the approved QA brief. For D2/D3, many-screen, or
interaction-heavy work, decompose aggressively instead of using one broad
review. Default independent QA lanes:

- functional interaction, link, navigation, event, keyboard, and state QA;
- responsive visual, rendered layout, screenshots, accessibility, and console
  or network QA;
- copy, Messaging System, Content Contract Package, and product completeness QA;
- instruction compliance, artifact path mapping, gates, waivers, and rubric
  audit.

Use fewer lanes only when the surface is small enough that decomposition would
not improve evidence quality. Use more lanes when specialized surfaces need
separate review, such as editor tools, dashboards, games, checkout flows,
authentication, data visualization, media, realtime updates, or admin actions.

Independent QA contexts are read-only by default. They inspect files, run the
app when needed, exercise behavior, capture evidence, and report findings.
They do not edit files unless the owner explicitly approves a write-scoped
delegation.

The Independent QA Brief must be self-contained and written for a literal,
ultra-obedient reviewer who follows instructions exactly but does not infer
common-sense coverage. Include:

- repository path, current commit or working-tree state, and whether changes
  are committed or uncommitted;
- local setup commands, server command, URL, ports, environment assumptions,
  and known unavailable tools;
- exact files and artifact paths to read before testing;
- approved owner scope, gates, waivers, visual direction, wireframes, screen
  contracts, and Messaging Identity references;
- directly openable approved HTML wireframe addresses, the Wireframe
  Conformance Contract, and the page/state/region-to-production mapping;
- page, route, screen, state, component, and viewport lists to cover;
- Interaction Inventory with every clickable, focusable, typed, hoverable,
  draggable, scroll-controlled, stateful, eventful, navigational, or
  apparently interactive region;
- the content-package index, applicable canonical copy shards, shared UI copy
  registry, and required Messaging System checks;
- exact viewport classes and concrete viewport sizes to inspect;
- exact accessibility, keyboard, focus, console, network, and error-state
  expectations;
- explicit pass/fail criteria for each checklist item;
- severity definitions;
- required evidence format: route, viewport, action, expected result, actual
  result, screenshot or log path when applicable, file/line reference when
  applicable, severity, and fix recommendation.

The independent reviewer must not accept vague assertions such as "looks good",
"links seem fine", "search works", "responsive checked", or "copy is clear".
Each passed area needs named evidence. Each failed area needs reproduction
steps and expected versus actual behavior.

If no independent QA result is available, the frontend task is not complete.
Do not move mandatory QA to backlog. Do not label the implementation
production-ready. The final response must say `Control Verdict: STOP`, include
the Independent QA Brief prompt for the owner to run in a separate session, and
state that completion is blocked on returned independent QA findings.

## Visual QA And Review Protocol

An independent image-capable visual reviewer renders or captures the real
interface at the relevant viewports and compares it with approved messaging,
identity, design system, reference frames, wireframes, and screen contracts.
The implementer may preflight, but neither implementer nor phase main supplies
the gate verdict. Inspect:

- hierarchy, spacing, alignment, typography, density, and composition;
- component consistency and semantic color;
- interaction and data states;
- accessibility and focus visibility;
- responsive transformations;
- signature traits and anti-identity;
- whether visual techniques have product rationale rather than generic
  AI-generated styling.

For D3, QA must explicitly compare production output against the selected
raster visual direction, the approved UI-library fidelity scene, and the
Selected Visual Direction Translation. Open the actual immutable images and
record their paths, revisions, hashes, dimensions, viewport/state, and capture
time. First judge whole-image composition side by side; then inspect critical
crops and the Signature Traits Matrix. Record
whether the implemented UI preserves the approved composition logic, density,
surfaces, typography direction, color semantics, illustration or imagery
treatment, signature traits, and rejected-board counterexamples. A production
surface that follows the wireframe but visually collapses into generic
unstyled cards, mismatched stock-like assets, or a different product identity
does not pass visual QA.

Do not infer rendered desktop, mobile, state, or visual fidelity from source,
CSS, DOM, tokens, accessibility snapshots, or another viewport. Every required
viewport/state needs current rendered evidence. A fix receives a new capture
path and affected re-review; never overwrite a reviewed screenshot.

For D3, QA must also compare rendered copy against the approved Content
Contract Package and shared UI copy registry. Record missing, shortened,
replaced, generic, unsupported, or misplaced stable content IDs separately from
visual and functional findings. A page that renders all wireframe regions but
omits promised depth, source-backed explanations, objection handling, microcopy,
or state text does not pass copy QA.

Ask two final questions:

1. Does this interface clearly belong to this product?
2. If styling were removed, would the approved useful product surface remain?

Fix observed defects and re-run the affected checks.

## Frontend Rubric Review

Every frontend task ends with a rubric review. For D0/D1, run the rubric
against the affected component, state, text, route, or viewport. For D2/D3, run
it against every delivered page, meaningful screen, flow, repeated component
pattern, and changed state.

For implementation work, the final rubric verdict must include independent QA
evidence from a separate execution context. The
implementer may draft a self-rubric as preflight, but self-rubric does not
close the gate. If no independent result exists, the rubric status is
`blocked: independent QA not returned`.

For D3 artifact phases, run the rubric before requesting Product Surface
Approval, Wireframe Approval, and Product-Surface Implementation Approval. Apply the
rubric to the artifact package being approved: approved surface, messaging,
flows, wireframes, screen contracts, responsive coverage, instruction control,
and remaining implementation evidence. Visual
Direction Boards keep their board evidence table before approval; the full
rubric applies when the selected direction becomes part of the design system
and implementation package.

The applicable independent Contract Reviewer produces the file-backed rubric
verdict for a D3 artifact gate. For D2/D3 implementation, the independent QA
context produces it. The phase main reads only the compact verdict and cited
blockers; it does not run or amend the rubric itself.

The artifact-phase rubric does not close an approval package until the
Independent Contract Review has examined every applicable Markdown contract
in that package and blocking findings have been fixed and re-reviewed.

Record a verdict and evidence for each category:

- Functional: journeys, interactions, navigation, links, forms, events, and
  state transitions work as promised.
- Responsive: all required viewport classes are inspected and each layout
  transformation preserves hierarchy, reachability, and content.
- Visual: hierarchy, spacing, typography, alignment, density, composition,
  component consistency, semantic color, and identity fit are intentional.
- Copy: the full Messaging System is applied to all user-visible text and
  microcopy.
- Product completeness: promised corpus, data, pages, states, workflows,
  media, generated output, and capabilities are present or owner-bounded.
- Search and navigation: queries, filters, result states, routing, and keyboard
  behavior work when present.
- Accessibility: landmarks, names, focus, keyboard operation, contrast, target
  sizes, reading order, and reduced-motion or motion safety are checked where
  relevant.
- Instruction control: read receipt, gates, approvals, waivers, artifact paths,
  and final audit match this subsystem.

The final response for frontend work includes a compact rubric summary with
category verdicts and named evidence. For implementation work, also name the
independent QA reviewer/session or the fallback owner-run QA prompt path.

## Copy QA And Review Protocol

Production-ready frontend combines polished layout with specific, useful text.
Review all user-visible copy as product behavior.

Inspect:

- Messaging Identity use;
- Messaging Contract fulfillment for each page, screen, and state with
  user-visible text;
- page or screen trajectory from starting state to intended leaving state;
- text hierarchy across main promise, section arguments, supporting copy,
  action copy, and microcopy;
- message placement and density;
- clarity of the main promise and page trajectory;
- specificity to the product, audience, workflow, and current state;
- enough concrete information to satisfy the promised surface;
- alignment with Messaging Identity;
- whether section headings advance the argument;
- whether supporting text adds mechanism, example, distinction, constraint, or
  proof instead of repeating the heading;
- claim/proof proximity;
- objection coverage and timing;
- action-copy specificity;
- microcopy usefulness in loading, empty, error, disabled, success, overflow,
  and partial-data states;
- scannability and text hierarchy;
- density by placement;
- copy is specific, supported, proportionate, and well placed.

For every user-visible text fragment, ask what job it performs. If the answer
is unclear, rewrite it or cut it. If a strong claim needs proof, add proof,
weaken the claim, or retire the claim.

Copy QA is complete only when the review names every page, screen, state,
action, repeated pattern, canonical content shard, and shared-copy family
inspected; records the expected revision/hash and rubric result for each; maps
rewrite decisions to the Messaging System concept that required the change;
and includes an independent reviewer verdict. Partial
sampling is allowed only with a scoped owner message containing
`FRONTEND WAIVER:`.

## Product Completeness Review

For D2/D3 work, verify that approved primary goals, relevant secondary goals,
navigation, messaging trajectory, content, interactions, endpoints, and states
exist. Label placeholder/demo-only surfaces or replace them. Distinguish
planned seams, mock data, disabled controls, and future integrations from
complete end-to-end behavior.

A separate independent QA context writes the D2/D3 Product Completeness Review
and its coverage manifest. The implementer may preflight completeness but
cannot close it; the phase main consumes only the verdict and cited blockers.

## QA Evidence Record

Substantial implementation ends with an independent file-backed review under
`docs/frontend/reviews/` using that role document's QA Evidence Record Template.
Claim each check with evidence and label the delivered scope precisely.

## Persistent Frontend Memory

Use the exact compact and role-specific roots in
`docs/agent/context_routes.yml`. Persist only durable product, stack,
collaboration, messaging, design, component, content, asset, flow, wireframe,
screen, decision, and review knowledge under `docs/frontend/`; keep large bodies
behind compact indexes. Handoff files own rolling control and append-only
transition evidence only and never become a second product source of truth.

## Completion Checklist

A frontend task is complete only when the Final Instruction Audit records:

- Read Receipt existed before frontend action and named gates, obligations,
  waivers, controlling gate, verdict, and next action;
- every applicable O01-O38 obligation is `satisfied` or explicitly
  `waived by owner` with a scoped `FRONTEND WAIVER:`;
- D3 product-surface implementation started only after O25 or a waiver, while
  the explicitly earlier production UI-library phase stayed within P06 scope;
- approved artifacts exist at named paths and match the delivered surface;
- required independent author/reviewer/implementation/QA contexts remained
  separate or the owner accepted the role collapse;
- every D3 phase began under a fresh accepted phase main, every outgoing main
  stopped at its boundary, and each phase-control transition is evidenced by
  the append-only ledger or an exact owner waiver;
- every blocking independent finding was fixed and rechecked or waived;
- production output matches approved scope, wireframes, Content Contract Package, UI
  library, selected visual direction, responsive targets, accessibility needs,
  interactions, links, navigation, and product completeness criteria;
- placeholders, seams, remaining failures, validation gaps, and next commands
  are explicitly reported.

Optimize this process through evaluation: compare the delivered behavior and
evidence with the Task Contract. Optimize for delivered behavior, evidence,
and useful artifacts over prompt length or procedural fluency.
