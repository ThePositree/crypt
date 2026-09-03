# Frontend Design Subsystem

MANDATORY: before any frontend work, read this full document and the full
frontend instruction and memory set. Follow this subsystem exactly throughout
discovery, planning, design, implementation, rendered inspection, review, and
final reporting. Apply every instruction whose trigger matches the current
task, depth, surface, state, and risk. The agent may narrow, skip, reorder, or
replace a required frontend instruction only after an explicit owner waiver
uses the waiver phrase defined in this document.

READ RECEIPT GATE: before planning, editing, generating artifacts, launching
rendered checks, or delegating frontend work, publish a concise receipt in chat.
The receipt names every frontend instruction and memory file read, line counts,
full-file ranges covered, top-level headings observed, the classified depth,
the active gates, the active obligations, and the first owner approval gate
that controls the next action. It ends with `Control Verdict: STOP` or
`Control Verdict: PROCEED`. Frontend action begins after this receipt exists,
identifies the currently applicable instruction set and canonical obligations,
and returns `PROCEED`.

PRODUCTION STANDARD: every frontend surface is user-visible product quality
from its first delivered version. Plan and build for complete, accurate,
polished, accessible, responsive, and internally consistent behavior within the
approved scope. Production quality includes content depth, data coverage,
interaction completeness, search or filtering quality when present, and
credible product substance behind the visual shell. Treat rough drafts, vague
copy, visual glitches, broken states, unverified assumptions, approximate
flows, shallow content, partial indexes, and decorative-only product surfaces
as unfinished frontend work.

Version: 6
Updated: 2026-09-03

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
- current status: proposed / approved / blocked / superseded.

Prefer small manifests plus durable files over long chat transcripts. When an
artifact or review would be long, the author writes the full deliverable to the
repository or a named local artifact path and reports only a compact manifest,
verdict, blocking findings, path, and line index in chat or worker completion.
The design/control context reads targeted lines only when verifying a blocker,
resolving a contradiction, or preparing an owner gate.

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

`Active Gates` are owner-decision gates such as onboarding, Product Surface
Approval, Visual Direction Approval, Wireframe Approval, Action Contract
Approval, and Final Implementation Approval.

`Active Obligations` are execution requirements that remain active even when
the current gate is `STOP`. Use the exact canonical obligation names below and
mark each one `applies`, `not applicable`, `satisfied`, `blocked`, or
`waived by owner`. Add a one-line reason for every `not applicable`, `blocked`,
or `waived by owner` status.

Canonical frontend obligations:

- Full Messaging System for all user-visible text;
- Source-Grounded Content Authoring;
- Text Inventory And Copy Approval;
- Independent Factual Product Research;
- Independent First-Use Review;
- Independent Wireframe Rendered Visual QA;
- Pre-implementation Content Coverage Audit;
- Post-implementation Content Coverage Audit;
- Product Surface Model;
- Content And Capability Contract;
- Discovery Contract;
- Messaging Identity and Messaging Contracts;
- Design Identity and Design System;
- Five raster Visual Direction Boards;
- Visual Direction Approval;
- Selected Visual Direction Translation;
- UI Library And Component Showcase;
- UI Library Approval;
- Production Raster Asset Pack;
- Production Raster Asset Pack Approval;
- Flows;
- Page-level wireframes for every real page or meaningful screen;
- Persistent HTML Wireframe Artifacts;
- Wireframe Approval;
- Screen contracts for every real page or meaningful screen;
- Independent Contract Review;
- Frontend Lead Contract Review Brief;
- Action Contract;
- Final Implementation Approval;
- Separate Implementation Session;
- Frontend Implementation Brief;
- Wireframe Conformance Contract;
- Interaction Inventory;
- Full link and navigation coverage;
- Discovery QA;
- Six viewport classes;
- Accessibility checks;
- Independent Frontend QA Gate;
- Independent QA Brief;
- Frontend Rubric Review;
- Rendered evidence;
- Durable frontend memory updates;
- Final Instruction Audit.

Start implementation, artifact generation, rendered inspection, delegation, or
durable memory updates only after the Read Receipt identifies the active gates,
canonical active obligations, and returns `PROCEED`. A `PROCEED` verdict is
valid only when every applicable canonical obligation is listed with a current
status. When the first active gate requires owner approval, the Read Receipt
returns `STOP`; the next action is presenting the required artifact or question
and waiting for the owner decision.

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

Every collaboration, implementation, contract-review, and QA assignment has a
named scope. An owner decision about delegation applies only to the named phase
unless the owner explicitly grants a broader preference. A completed phase
expires its scoped collaboration decision. Run a fresh Collaboration Check
before another D2/D3 or context-heavy phase.

Short owner requests preserve the depth and approval requirements implied by
the requested surface. A request such as "create a site", "make the app",
"build the page", or "design the screen" receives D3 treatment when frontend
memory says the product surface, Messaging Identity, Design Identity, Design
System, or active frontend context is `not established`, `pending`, or awaiting
owner input. In that state, the Read Receipt verdict is `STOP: D3 onboarding
and approval gate required`.

Owner answers that define product direction, stack preference, language,
content scope, search, visual style, pages, or interaction needs become input
to the next artifact phase. They do not unlock implementation until the
canonical D3 sequence reaches Final Implementation Approval or the owner grants
a scoped `FRONTEND WAIVER:` for the skipped gates and obligations.

After Product Surface Approval, refresh the Read Receipt and update canonical
obligations. Record approved pages, screens, content/capability coverage,
discovery requirements, copy language, source boundaries, visual requirements,
and implementation boundaries as artifact requirements for the next phases.

Owner words that imply scale, completeness, quality, depth, richness, working
behavior, production readiness, or broad coverage become acceptance
requirements. Translate those words into concrete coverage criteria before
implementation. Narrower scope, representative samples, curated subsets,
placeholder content, simplified ranking, deferred pages, or reduced interaction
depth require explicit owner approval before implementation.

Before implementation and before final response, run a Content Coverage Audit
whenever the surface promises content, data, media, levels, items, workflows,
generated output, pages, sections, search, filtering, navigation, indexes,
catalogs, or interactive capabilities. The pre-implementation audit lists the
promised coverage and source of truth. The post-implementation audit maps each
promised item to the delivered page, section, component, state, interaction, or
explicit owner-approved boundary.

Before final response, perform a Final Instruction Audit. The audit states
which frontend instruction files were applied, which memory files influenced
the result, which gates passed or remain active, which approvals or waivers were
recorded, and which evidence supports the delivered scope. Include the audit or
a compact version of it in the final response for any frontend task that
changes code, copy, visual direction, product surface, screen contracts,
wireframes, flows, frontend memory, or review artifacts.

## Depth Classification

Classify the task before choosing artifacts and approvals.

| Depth | Typical work | Required design evidence |
| --- | --- | --- |
| D0 | copy, token, or isolated visual correction | affected contract/context, copy purpose, focused render |
| D1 | component or small section | Task Contract, relevant states, copy/microcopy impact, responsive impact, focused render |
| D2 | new section, screen, or meaningful flow change | product scope, Messaging Contract, flow, wireframe, screen contract, owner approval |
| D3 | major redesign, many screens, or new frontend/product | full discovery, Product Surface Model, Messaging Identity, onboarding, visual exploration, design system, flows, wireframes, approvals |

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
the current pass, stop and ask the owner to narrow scope or record a scoped
`FRONTEND WAIVER:`; do not continue with an implied partial build.

## Lifecycle

All depths use the same lifecycle, with evidence proportional to scope:

```text
DISCOVER -> CONTRACT -> DESIGN -> APPROVE WHEN REQUIRED -> IMPLEMENT
         -> RENDER -> INSPECT -> FIX -> RECORD DURABLE KNOWLEDGE
```

For D0 and D1, phases may be brief and use existing artifacts. For D2 and D3,
make each phase output explicit. A phase may legitimately finish before
production code when an owner decision is required or the next phase needs a
fresh bounded context.

For D3, process quality outranks implementation speed. Complete each required
artifact phase with inspectable files, rendered evidence, owner-facing
decision options, and a recorded owner decision before moving to the next
phase. A summary can explain an artifact, but the gate is satisfied by the
artifact itself: existing files, paths, rendered views, coverage notes, and the
decision record.

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

Before planning D2/D3 work, a context-heavy phase, or an independent review,
check whether delegation is available and appropriate. Record:

- availability: available / current-session / unknown;
- required collaboration interface;
- available worker or runtime choices;
- proposed delegated outcome and why it is independently verifiable;
- context-budget purpose: what reading, analysis, rendering, or review work is
  being moved out of the main context window;
- files and permissions the worker would receive;
- how its result would be reviewed and integrated;
- fallback using current-session work when the owner chooses single-agent work.

After presenting this bounded proposal, ask the owner whether delegation should
be used for the stated phase. The answer applies to that scope, with a broader
preference only when the owner states one. Delegation starts after explicit
owner approval. A decline still allows single-agent progress in the current
session.

Do not infer collaboration approval from approval of a product, visual,
wireframe, action, or implementation gate. Before starting each independent
worker or separate execution context, record the exact reviewed or authored
outcome and the owner's approval to use that context for that phase.

Independent contexts are also a context-window budgeting tool. Once a bounded
research, authoring, inspection, or review task is delegated, the main
design/control context must not perform the same broad read, crawl, analysis,
rendering, or QA pass in parallel. Doing duplicate work defeats the delegation
purpose, spends the owner's context twice, and can produce conflicting
unreviewed conclusions. The main context may read only enough to prepare a
precise brief, monitor progress, verify returned claims, inspect narrow
blockers, and integrate accepted findings. If the main context discovers that
it must redo the delegated task, stop, explain why the delegation failed, and
record the fallback before continuing.

For D2/D3, default heavy phase work to artifact-producing independent contexts
when collaboration is available and approved. The main design/control context
orchestrates phases, writes briefs, records owner decisions, checks manifests,
and integrates reviewed results. It should not load a full factual report,
content inventory, visual audit, QA log, or implementation report into its own
context when a file-backed artifact and a compact review verdict are enough.

Use paired independent contexts for high-impact artifacts:

- an authoring context gathers evidence and writes the artifact file;
- a separate review context reads the artifact and its required sources,
  reports blockers, and verifies fixes;
- the main design/control context reads the manifest, reviewer verdict, and
  targeted blocker lines, then presents the owner gate or assigns fixes.

If an authoring worker returns only prose instead of writing the required
artifact file, treat the phase as incomplete. If a review worker pastes a long
audit instead of writing or referencing a durable review artifact, ask for a
compact verdict and path before integrating the result.

Ask about delegation for D0/D1 work only when it provides a clear, specific
benefit. Create a worker after the owner answers the Collaboration Check with
approval. If repository or environment rules require a particular collaboration
interface, name that requirement in the proposal and use it after approval.

### Independent Execution Contexts

`Independent` means a separate execution context that did not author the
artifact it evaluates. It may be another agent, a subagent, an isolated or
neighboring session, or another compatible context. No particular agent
feature, vendor, CLI, or orchestration product is required. When the current
environment cannot create such a context, provide a self-contained brief for
the owner to run in a separate session and wait for the returned result.

Independence does not mean maximum repository access. Give every independent
context only the role, product summary, artifacts, criteria, and source
material required for its bounded task. Do not make it read this complete
frontend subsystem, repository bootstrap, task history, changelog, or unrelated
contracts unless its assigned task is specifically to audit those sources.
Require a compact result containing the verdict, blocking findings, evidence,
and recommended fixes. On re-review, provide the previous blockers, changed
artifacts, and closure criteria instead of replaying the whole project history.
When the collaboration interface has an explicit completion message such as
`worker_done`, the completion message body must contain the agreed deliverable
manifest. For short tasks, the body may be the full deliverable. For long
research, content, review, QA, or implementation evidence, the brief should
require a file-backed artifact and a compact completion body containing the
path, status, verdict, blockers, and line index. The brief must tell the
worker not to send a summary-only or empty completion signal and not to
continue producing a separate final report after completion. The design/control
context treats completion without the requested artifact path or deliverable
body as a failed or incomplete delegation, not as accepted evidence.

Keep these roles distinct:

- a Factual Product Researcher inspects only the canonical product, runtime,
  architecture, and implementation sources needed to establish how the product
  actually works before a Product Surface is drafted;
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

Read the full frontend instruction and memory set before applying
depth-specific context.

Always begin with the repository bootstrap and routed frontend full docs. Then read:

- `docs/frontend/context.md` for the active stack and conventions;
- the affected flows, wireframes, screens, components, and decisions;
- `docs/frontend/product-surface-model.md` for D2/D3 scope decisions;
- Messaging Identity and Messaging Contracts when page text, public voice, or
  user decision-making is affected;
- Design Identity, Design System, and visual references when visual direction
  is affected;
- action/runtime sources of truth when the UI can mutate important state.

After full reading, select the artifacts and rules that apply to the classified
depth and affected surface. Resolve contradictions before implementation.
Runtime configuration and real service state govern operational behavior;
approved product/design artifacts govern intended UI behavior until explicitly
superseded.

## First-Use Discovery

Before establishing or changing project-specific rules, inspect the repository
and record evidence for:

- frontend framework and build system;
- styling approach, tokens, themes, and typography;
- UI libraries and local primitives;
- form, chart, table, icon, animation, and visualization libraries;
- responsive conventions and layout patterns;
- assets and imagery;
- component documentation, examples, or catalogs;
- established screen and component patterns;
- legacy areas, migrations, and active inconsistencies.

Treat stable, actively used choices as intentional until stronger evidence
changes that conclusion.
Ask the owner only about unresolved choices that materially change the result.
Persist verified choices in `docs/frontend/context.md`, including the evidence
and date observed.

For non-trivial use of an external library or API, consult current
authoritative documentation before implementation. If authoritative
documentation is limited, state that limitation and proceed cautiously.

## Product Knowledge Discovery

For D2 and D3 work, discover product knowledge before deciding pages or
features. Search current canonical sources such as README, product specs,
architecture, task context, current state, and approved decisions. Identify:

- primary source;
- supporting sources;
- contradictions or stale claims;
- open decisions that affect the requested surface.

For D3 work, perform this discovery in a separate Factual Product Researcher
context before drafting the Product Surface Model. Give the researcher a
bounded product question, the repository entry points needed to find canonical
sources, explicit exclusions, and a compact output schema. Do not give it the
frontend subsystem, visual direction, proposed page structure, authoring
rationale, or a draft Product Surface to defend.

The researcher returns:

- a factual system and capability map;
- distinct runtime or user paths and their real topology;
- active, historical, deferred, and absent capabilities;
- source-of-truth references for every material fact;
- contradictions and unresolved product questions;
- facts that must not be inferred from names or historical documentation.

The design/control context reviews this result against the named sources,
records accepted evidence in the Product Surface Model, and only then drafts
pages, journeys, diagrams, discovery behavior, or messaging. Contract Review
must not be used as the first factual product-discovery pass.

Infer what the repository already establishes. Ask the owner for information
that remains unresolved after repository discovery. When clarification is required, ask a small adaptive batch
of high-information questions and explain which decision each answer unlocks.

## Product Surface Model

Build or update `docs/frontend/product-surface-model.md` before D3 screen
design and whenever D2 work changes product scope.

Derive it in this order:

```text
product evidence
-> users and goals
-> capabilities and content
-> journeys and endpoints
-> messaging trajectory and proof needs
-> information architecture
-> screens
-> sections and components
-> required states
```

The model must distinguish approved scope, boundaries, assumptions, and
unresolved decisions. Completeness means the approved product surface fulfills
its promised journeys at production quality.

Before approval, mentally strip styling from the structure. When the remaining
structure fails to form a useful product surface, repair the surface before
visual design.

## Content And Capability Completeness

Any frontend surface that presents information, data, media, levels, items,
tools, workflows, catalog entries, generated output, or interactive states
needs a Content And Capability Contract before production implementation. The
contract defines:

- source corpus, data source, asset set, or capability inventory;
- user-facing coverage promised by the owner request and product surface;
- included entities, sections, items, states, levels, views, or workflows;
- boundaries that require owner approval;
- depth required for each important page, panel, step, result, or interaction;
- proof that content comes from canonical sources or approved product
  decisions;
- freshness, update, or synchronization expectations when content can change;
- measurable coverage evidence before final handoff.

For search, filtering, navigation, recommendations, maps, indexes, generated
lists, catalogs, or any discovery interface, define a Discovery Contract. It
states the searchable corpus, indexed fields, body-text or metadata coverage,
ranking or grouping behavior, snippets or result explanations, empty and
zero-result states, keyboard behavior, and representative queries that prove
the user can find important content.

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

For substantial D2/D3 content, use a separate Source-Grounded Content Authoring
context after the owner approves its bounded collaboration scope. Give the
Content Author the approved audience, Product Surface, Messaging Identity,
page or screen contracts, explicit content boundaries, and only the canonical
product sources needed for those pages. Do not require the Content Author to
read the complete frontend subsystem. The author returns finished copy, a
source map for factual claims, unresolved facts, and Text Inventory coverage
by writing the named content and Text Inventory artifacts directly. For D3,
this content work produces a named Text Inventory artifact before
implementation approval. The design/control context does not replace it with
ad hoc bullets, ledes, summaries, implementation-time copy, or a full rewrite
inside the main session. It may inspect targeted inventory lines to resolve
review findings or present owner approval.

Review substantial copy in another independent context. The Copy Reviewer sees
the rendered pages, the approved audience and voice summary, and the copy
criteria, but not the author's reasoning. It checks comprehension,
specificity, information depth, claim/proof proximity, objections, actions,
microcopy, and generic AI-generated language. Content authorship and copy
review do not replace owner approval or final implementation QA.

The text pass is exhaustive, not importance-based. Do not limit it to hero
copy, public marketing copy, important paragraphs, or high-risk messages. Every
visible fragment counts: navigation labels, breadcrumbs, tabs, filters,
buttons, links, headings, card titles, card bodies, badges, tooltips, alt text,
form labels, placeholders, helper text, validation messages, loading text,
empty states, error states, success states, disabled labels, table headers,
chart labels, legend text, metadata labels, footer text, legal text, command
labels, keyboard shortcut hints, toast text, dialog titles, menu items, and
repeated generated labels.

Before implementation, create a Text Inventory at a named path for every
planned page, screen, state, action, and repeated pattern. For D3, the
inventory is an approved contract, not internal notes. Record for each item:
location, exact text or text pattern, minimum intended depth or length when
the owner requested rich content, semantic job, Messaging Contract link,
claim/proof status, objection or friction handled when relevant, source map,
authoring owner, approval status, and reviewer verdict. Implementation must
render the approved inventory or stop and report a contract deviation before
changing, shortening, omitting, or replacing planned copy.

After implementation, reconcile the approved Text Inventory against rendered
interface evidence and source code. The reconciliation records for each item:
expected copy, actual copy or omission, rendered location, source-code
location, pass/fail verdict, and required fix. A production page that follows
the wireframe but drops approved depth, proof, objections, microcopy, or
source-backed explanations does not pass copy or content coverage.

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

- artifact path and revision;
- Independent Factual Product Research brief, researcher/context, canonical
  sources, accepted factual map, and unresolved contradictions for D3;
- in-scope users, journeys, screens, and states;
- scope boundaries and assumptions;
- unresolved decisions;
- the exact next phase unlocked by approval.

Record approval or a scoped waiver in a frontend decision file.

## Design Onboarding

Run deep one-time onboarding when D3 work needs an established Design Identity,
or when the existing identity needs expansion for the requested product surface.
The established practice is exactly 25 questions in five rounds of five,
followed by an Uncertainty Check.

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
Then move to Preliminary Identity and Visual Exploration.

## Preliminary Identity

Synthesize a preliminary identity from repository evidence and owner answers.
Label inference separately from explicit owner decisions. Cover core feeling,
personality, desired perception, visual tension, density, candidate signature
traits, and anti-associations. This is input to exploration before the final
design system.

## Visual Exploration

For first-time D3 onboarding, create exactly five rendered raster Visual
Direction Boards. A later D3 visual reset may use a narrower exploration only
after explicit owner approval.
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

Render and inspect every board before presenting it. Fix overlap, blank areas,
unreadable text, broken responsive composition, or insufficient component
evidence. Boards are direction studies before production assets.

Visual Direction Board completion requires five existing generated raster artifacts with
stable paths, inspected desktop and mobile views, visible representative UI
fragments, component showcase coverage, state examples, and concise comparison
notes. Text-only descriptions, mood summaries, written design contracts, HTML
pages, and screenshots of coded pages do not satisfy this gate. Written notes support
the discussion after the boards exist. This gate is complete when the rendered
board artifacts and comparison evidence are present.

Before Visual Direction Approval, present a board evidence table. For each
board, include artifact path, format, product hypothesis, representative UI
fragments shown, component showcase coverage, state examples, desktop/mobile
inspection evidence, strengths, trade-offs, and what the direction leaves out.

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

Finalize Design Identity and Design System after this approval passes or the
owner records a scoped waiver.

### Selected Visual Direction Translation

After Visual Direction Approval, translate the selected raster direction into
an implementation-facing contract before writing production pages. Record:

- selected board or merged-board artifact path;
- visual properties that are mandatory in production;
- visual properties that are mood-only or forbidden to copy literally;
- component families implied by the board;
- layout, density, surface, border, color, typography, illustration, icon, and
  motion rules needed to reproduce the direction;
- asset needs for hero media, section art, empty/error states, diagrams,
  thumbnails, mascots, or product imagery;
- counterexamples from rejected boards and generated artifacts;
- visual fidelity checks the implementation and QA contexts must run.

This translation is the bridge between generated image evidence and working
interface code. A selected raster board is not enough by itself; production
must follow the translated component system and visual fidelity rules.

### UI Library And Component Showcase

For D3 work, build the approved visual direction into a real production UI
library or component system before building production pages. This is not a
throwaway HTML demo, visual-only mockup, screenshot reproduction, or isolated
showcase artifact. The production pages must import, compose, or otherwise use
the same approved components, tokens, primitives, assets, state styles, and
layout patterns demonstrated in the showcase. This can wrap an existing
owner-approved UI library, design system, framework primitives, or local
components. If the owner wants a ready-made UI library, record how its
primitives map to the selected visual direction and where custom styling,
tokens, slots, or components are required. Do not treat a third-party library
as the product identity.

Before creating the UI library or component showcase, obtain the required stack
contract for the production frontend: framework/runtime, styling approach,
component library preference if any, package boundaries, target deployment or
static output constraints, asset handling, accessibility expectations, and
repo-local build/test commands. If the owner wants the agent to choose, record
that as an explicit owner decision and choose conservatively from repository
evidence rather than vendor preference.

Create a storybook-like rendered component showcase before production page
implementation. The showcase renders the actual production UI library, not a
parallel approximation. It demonstrates the shell, navigation, buttons, links,
forms, search/filter controls, cards, article layouts, badges, tables or
lists, diagrams or media frames, overlays/drawers/modals, empty/loading/error/
success/disabled states, focus/hover/selected states, responsive variants, and
every signature visual trait. The showcase may be an internal route, static
HTML artifact generated from the same component source, framework story page,
or equivalent rendered artifact, but it must be openable and inspectable.

The UI Library Approval gate passes only after an independent read-only visual
fidelity review receives the rendered component showcase, the selected raster
board or merged final board, the Selected Visual Direction Translation, and a
short product description. The reviewer must judge whether the implemented
primitive system looks like the selected image in practice: composition logic,
surface treatment, density, typography direction, color semantics, borders,
shadows, icon/illustration treatment, state styling, responsive behavior, and
signature traits. If the showcase does not look like the selected image, the
gate fails even when the components are technically reusable or accessible.
Production pages do not start before this approval or a scoped
`FRONTEND WAIVER:`.

After production pages are implemented, QA must verify that pages use the
approved UI library/components instead of recreating visually similar one-off
markup. Any production page that bypasses the approved primitive system must
record an approved exception or be treated as a visual fidelity defect.

### Production Raster Asset Pack

When the selected visual direction depends on raster imagery, illustration,
characters, physical metaphors, product media, thumbnails, or generated visual
language, create a Production Raster Asset Pack before production page
implementation. The pack is a raster collage or asset sheet with reusable
production-image references such as hero art, section illustrations,
empty/error/loading/success imagery, mascot or character poses, diagram style
samples, content thumbnails, texture treatments, and media crops.

The asset pack is separate from Visual Direction Boards. Boards prove the UI
direction; the asset pack gives future production image generation and asset
selection a stable reference. Store it at a named path, inspect it for
readability, nonblank output, visual consistency, unwanted text, licensing or
source constraints when applicable, and fidelity to the selected board. Ask
for Production Raster Asset Pack Approval before using it as production
evidence.

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

Use a clear text-based or rendered diagram format under `docs/frontend/flows/`
for navigation, user flows, and state transitions when the interaction needs
a richer artifact. Flows describe:

- actor and starting state;
- available action;
- decision or permission condition;
- resulting state and feedback;
- error/recovery path;
- journey endpoint.

Create or update flows before production implementation when navigation,
state transitions, permissions, or journey endpoints change. A purely visual
D0 change may reference an unchanged flow instead of rewriting it.

## Wireframes

Use persistent low-fidelity rendered HTML wireframes under
`docs/frontend/wireframes/` as UI contracts. A wireframe is a directly
openable HTML artifact, not a screenshot. Each real page or meaningful screen
receives its own stable HTML route or artifact entry plus relevant breakpoint
and state evidence. A shared renderer is allowed when every approved page,
meaningful screen, and applicable state has a stable directly openable address.
Multi-page sites, apps, dashboards, games, portals, catalogs, onboarding flows,
and tools need a separate wireframe package for every real page or meaningful
screen. A shared shell wireframe can document global navigation or layout
system behavior and is paired with page-level wireframes for the actual
surfaces.

For multi-page or multi-screen work, the required artifact is a clickable
wireflow: low-fidelity page wireframes connected through the same navigation,
route, overlay, and prepared-state transitions that the production surface will
expose. A reviewer must be able to start at the entry screen and traverse every
primary approved journey by activating the corresponding controls in the
wireframe. Do not require the reviewer to open each HTML file manually.

Screenshots are rendered QA evidence for the HTML artifact. They never replace
the artifact. A directory containing only screenshots is not a wireframe
package. The page-to-wireframe index links first to the directly openable HTML
artifact and separately to screenshots or other inspection evidence.

Wireframes show:

- information hierarchy and labeled regions;
- navigation, controls, data, content, and primary actions;
- interaction notes;
- loading, empty, error, disabled, overflow, and partial-data states where
  relevant;
- responsive transformations;
- links to related flows and screen contracts.

Keep wireframes visually neutral so reviewers judge structure instead of
premature visual design:

- use grayscale only, with plain white, gray, and black surfaces, borders, and
  text;
- use rectangles and an `X` placeholder for images, illustrations, video,
  charts, maps, or other media;
- do not apply brand colors, gradients, textures, shadows, decorative
  backgrounds, final imagery, mascots, visual-direction styling, or polished
  production treatments;
- preserve realistic block sizes, text density, and responsive geometry.

Use stable real text only where wording is part of information architecture:
product and page names, navigation labels, primary action labels, and approved
domain terminology. Replace headings, body copy, marketing copy, examples, and
other production prose with visible meta-text that states the block's semantic
job, intended content, approximate character or line range, proof or source
need, media presence and type, and interaction behavior.

Wireframes validate information architecture, hierarchy, page composition,
journeys, visible states, responsive intent, and interaction intent. They are
not early production applications. Do not implement production algorithms,
real full-text search or ranking, data fetching, persistence, clipboard APIs,
complete keyboard mechanics, production-grade focus management, or exhaustive
state-transition logic merely to make a wireframe functional.

Use the lowest fidelity that makes the approval decision observable:

- W0: rendered static structure for a page without meaningful interaction;
- W1: a clickable wireflow with production-equivalent navigation plus directly
  selectable demonstration states such as normal, overlay open,
  example results, zero results, loading, error, or mobile navigation;
- W2: a small clickable journey when sequence or navigation is itself an
  unresolved product decision;
- W3: a functional prototype only after explicit owner approval names the
  behavior whose implementation risk justifies it.

D2/D3 wireframes default to W1. Every production navigation, route change,
overlay entry/exit, and primary journey transition at W1 must navigate between
stable fixtures or reveal prepared local states. Search uses representative prepared
results rather than a search engine; copy controls may show prepared feedback
without using the clipboard; keyboard and focus requirements remain explicit
in screen contracts for production implementation and QA. A behavior may be
described in the interaction note when implementing it would test engineering
rather than product structure. Record every behavior deferred to production so
Wireframe Approval cannot be mistaken for functional QA.

For every page or meaningful screen, record a state matrix containing the
state name, stable HTML address, entry action or fixture, expected behavior,
relevant viewport evidence, and inspection verdict. Render screenshots for
the viewports and states needed to make approval decisions; do not multiply
screenshots when the same HTML evidence proves the behavior sufficiently.

Create or update wireframes before implementation when layout, hierarchy,
navigation, interaction behavior, states, or responsive structure changes.
For D0 changes that preserve those properties, verify that the existing
wireframe remains accurate and record that fact in the Task Contract.

Render and inspect affected wireframes at their declared viewports before
requesting approval.

Wireframe completion requires persistent, directly openable HTML artifacts at
stable paths or routes for each affected page or meaningful screen, the
approved W0-W3 fidelity, stable demonstration states, declared responsive
transformations, and an explicit list of behavior deferred to production.
Written screen descriptions and layout summaries link to the HTML wireframes.
Screenshots record inspection evidence only. This gate is complete when the
HTML artifacts, state matrix, interaction-intent evidence, deferred-behavior
list, and responsive inspection evidence are present for every page or screen
in the approved scope.

The package must also expose a clickable route/state flow for every primary
approved journey, with no dead primary action or manually opened intermediate
screen.

### Wireframe Approval

Required for D2/D3 production work and any lower-depth change that materially
alters a UI contract. Present paths, inspected sizes, state coverage, open
questions, and the exact implementation scope unlocked by approval.

For D3 multi-page or multi-screen work, Wireframe Approval is blocked until a
page-to-wireframe index covers every approved page and meaningful screen. Each
index row includes page or screen name, route or state, directly openable HTML
artifact address, screen-contract path, six viewport classes or approved
viewport waiver, state-matrix entries, declared fidelity and demonstrated
interaction intent, behavior deferred to production,
content/discovery coverage, and inspection evidence. A shared shell, template,
or combined overview wireframe can appear
in the index as a supporting artifact and does not replace page-level rows.

## Screen Contracts

Store agent-readable screen specifications under `docs/frontend/screens/`.
Keep them aligned with approved flows and wireframes. Each contract states:

- purpose and user goals;
- primary action and information hierarchy;
- sections and components;
- data sources and trust boundaries;
- states and recovery behavior;
- responsive transformations;
- accessibility requirements;
- related screens, flows, and wireframes;
- measurable acceptance criteria.

For D3 multi-page or multi-screen work, create one screen contract file per
approved page or meaningful screen. Shared shell, navigation, search, overlay,
or layout-system contracts are separate supporting files. A combined screen
contract summary can provide an index or shared rules and does not replace the
per-page or per-screen contract files required for approval.

## Independent Contract Review

Every new or materially changed frontend Markdown contract must receive an
independent read-only review before it is presented for owner approval, used to
authorize implementation, or declared complete. Review the complete applicable
contract package, not a sample. This includes Product Surface, messaging,
identity, design system, content/capability, discovery, flows, wireframe index
and state matrix, screen contracts, Action Contracts, Wireframe Conformance
Contracts, implementation briefs, and consequential frontend decisions.

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
or stylesheet inspection alone is not rendered evidence.

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

## Final Implementation Approval

Before D3 implementation, and before D2 implementation when product or visual
decisions required owner approval, present one bounded summary:

```md
## Final Implementation Approval

- Outcome and scope:
- Explicit scope boundaries:
- Stack and sources of truth:
- Approved Product Surface revision:
- Independent Factual Product Research and source map:
- Approved Visual Direction revision:
- Approved flows:
- Approved wireframes by page or screen:
- Approved screen contracts by page or screen:
- Independent Contract Review and reviewer/session:
- Independent First-Use Review and reviewer/session:
- Independent Wireframe Rendered Visual QA and reviewer/session:
- Source-Grounded Content Author and source map, if applicable:
- Independent Copy Review, if applicable:
- Wireframe Conformance Contract:
- Frontend Implementation Brief:
- Content And Capability Contract, if applicable:
- Discovery Contract, if applicable:
- Action Contract, if applicable:
- Implementation units:
- Acceptance evidence to collect:
- Known risks and assumptions:
```

Implementation begins after approval or a recorded scoped waiver. For D3,
request this approval after Product Surface Approval, Visual Direction
Approval, Selected Visual Direction Translation, UI Library Approval,
Production Raster Asset Pack Approval when raster assets apply, finalized
Design Identity and Design System, approved Text Inventory and Copy Review
when copy applies, flows, rendered HTML wireframes, screen contracts,
Independent Contract Review, Independent First-Use Review, applicable
Source-Grounded Content Authoring and Independent Copy Review, Content And
Capability Contract, Discovery Contract when relevant, Action Contract when
relevant, and their decision records exist at named paths. The approval summary
maps every approved page or meaningful screen to its flow, wireframe path,
screen-contract path, UI-library components, selected visual translation,
asset-pack reference when applicable, text-inventory coverage, content
coverage, discovery coverage when relevant, conformance invariants, and
implementation unit. A waiver must name what is waived, why, what remains
required, and the next active gate.

For D3, implementation commands, file creation, package installation, source
generation, or production-code edits begin after Final Implementation Approval
or a valid `FRONTEND WAIVER:` that names the skipped approval and remaining
evidence. Approval of a questionnaire answer, product direction, stack choice,
language, page list, visual style, visual board, raster asset pack, UI
library, component showcase, wireframe, search requirement, or copy direction
moves the artifact sequence forward and does not approve implementation unless
the owner explicitly grants Final Implementation Approval.

Wireframe Approval freezes structure and interaction intent; it does not
authorize production code, package installation, source generation, or
implementation inside the design/control context.

## Implementation

Production frontend implementation is separate work from the context that
authored or approved the design and contract package. After Final
Implementation Approval, prepare a self-contained Frontend Implementation
Brief and assign write-scoped implementation to an approved independent
execution context. The design/control context does not write production
frontend code. If no independent execution context is available, stop;
do not collapse design, implementation, and QA into one context.

The Frontend Implementation Brief includes repository and execution context,
approved scope, every contract and HTML wireframe address, exact allowed files,
implementation units, Wireframe Conformance Contract, Selected Visual
Direction Translation, approved UI Library/component showcase paths, Production
Raster Asset Pack paths when applicable, approved Text Inventory paths, sources
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
wireframes, text inventory, UI library, and selected visual direction. A
working shell, partial happy path, placeholder content, generic generated copy,
or page that only resembles the wireframe structurally is not complete.

### Wireframe Conformance Contract

Wireframe Approval freezes structural and behavioral invariants. For every
page, screen, and applicable state, record what production must preserve:

- route and journey position;
- region, section, and information hierarchy;
- primary action, navigation, and journey endpoint;
- required components, content/capability coverage, and discovery behavior;
- interactions, state transitions, feedback, focus, and recovery;
- responsive transformations and accessibility relationships;
- placement of critical proof, warning, confirmation, and recovery content.

Final color, typography, detailed spacing, illustration, elevation, motion,
source-backed copy, and component implementation may evolve through the
approved Design System. Production must not copy gray-box styling merely
because the wireframe uses it. Visual evolution may not change a frozen
structural or behavioral invariant.

Before implementation, create a mapping from each approved HTML wireframe
page/state/region to its production route, component or module, implementation
unit, invariant, and verification method. When implementation would change a
frozen invariant, stop production work, update the HTML wireframe and affected
contracts first, render and inspect the change, obtain renewed approval for the
affected decision, and only then continue implementation.

After implementation, compare each production page and applicable state with
the approved HTML wireframe. Record every invariant with wireframe evidence,
production evidence, and pass/fail verdict. An unexplained structural or
behavioral difference blocks completion even when the production interface is
visually polished.

Keep implementation inside the approved scope. When implementation
reveals a material contract defect, update the relevant artifact and obtain
renewed approval only for the affected decision.

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
screenshots, and user-flow QA. Pair code compilation with rendered evidence.

For search, filtering, sorting, recommendations, maps, indexes, catalogs,
navigation discovery, generated lists, and similar discovery interfaces, run a
representative Discovery QA set. Cover exact matches, partial matches,
synonyms or domain-adjacent terms when relevant, role or audience queries,
topic queries, metadata filters, combined filters, high-value target items,
empty query behavior, zero-result behavior, keyboard operation, result
selection, ranking/grouping expectations, and snippet or explanation quality.
Record queries, filters, expected results, actual results, and fixes.

## Independent Frontend QA Gate

Frontend implementation QA is independent work. The same agent/session that
implemented the frontend may run local preflight checks, builds, linting,
typechecks, route smoke tests, and exploratory sanity checks, but those checks
do not satisfy final QA and must not be presented as completion evidence.
The QA reviewer/session is also separate from the design/control session and
the implementation worker/session. Design, production implementation, and
final QA therefore use distinct contexts unless the owner grants a scoped
`FRONTEND WAIVER:` naming the collapsed roles and accepted risk.

After implementation and before claiming the frontend task complete, run the
Independent Frontend QA Gate:

1. Prepare an Independent QA Brief.
2. Use an approved independent read-only QA context.
3. If no independent context is available, stop and ask the owner to open a fresh session
   for QA. Provide the exact prompt that would have been given to the delegated
   reviewer and ask the owner to return the findings.
4. Fix every blocking finding in the implementation session.
5. Repeat independent QA on the changed surface until blocking findings are
   cleared or the owner explicitly grants a scoped `FRONTEND WAIVER:`.

The implementer decides the number of QA workers. For D2/D3, many-screen, or
interaction-heavy work, decompose aggressively instead of using one broad
review. Default independent QA lanes:

- functional interaction, link, navigation, event, keyboard, and state QA;
- responsive visual, rendered layout, screenshots, accessibility, and console
  or network QA;
- copy, Messaging System, Text Inventory, content coverage, and discovery QA;
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
  contracts, content/capability contract, discovery contract, and Messaging
  Identity references;
- directly openable approved HTML wireframe addresses, the Wireframe
  Conformance Contract, and the page/state/region-to-production mapping;
- page, route, screen, state, component, and viewport lists to cover;
- Interaction Inventory with every clickable, focusable, typed, hoverable,
  draggable, scroll-controlled, stateful, eventful, navigational, or
  apparently interactive region;
- full Text Inventory and the required Messaging System checks for every
  user-visible text fragment;
- explicit Discovery QA query/filter set and expected outcomes;
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

Render the real interface at the relevant viewports. Compare it with the
approved messaging, identity, design system, references, wireframes, and screen
contracts. Inspect:

- hierarchy, spacing, alignment, typography, density, and composition;
- component consistency and semantic color;
- interaction and data states;
- accessibility and focus visibility;
- responsive transformations;
- signature traits and anti-identity;
- whether visual techniques have product rationale rather than generic
  AI-generated styling.

For D3, QA must explicitly compare production output against the selected
raster visual direction and the Selected Visual Direction Translation. Record
whether the implemented UI preserves the approved composition logic, density,
surfaces, typography direction, color semantics, illustration or imagery
treatment, signature traits, and rejected-board counterexamples. A production
surface that follows the wireframe but visually collapses into generic
unstyled cards, mismatched stock-like assets, or a different product identity
does not pass visual QA.

For D3, QA must also compare rendered copy against the approved Text Inventory.
Record missing, shortened, replaced, generic, unsupported, or misplaced text
items separately from visual and functional findings. A page that renders all
wireframe regions but omits promised depth, source-backed explanations,
objection handling, microcopy, or state text does not pass copy QA.

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
Approval, Wireframe Approval, and Final Implementation Approval. Apply the
rubric to the artifact package being approved: product surface, messaging,
content/discovery contracts, flows, wireframes, screen contracts, responsive
coverage, instruction control, and remaining implementation evidence. Visual
Direction Boards keep their board evidence table before approval; the full
rubric applies when the selected direction becomes part of the design system
and implementation package.

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
- Content and capability: promised corpus, data, pages, sections, states,
  workflows, media, generated output, and capabilities are covered.
- Discovery: search, filtering, sorting, recommendations, maps, indexes,
  catalogs, navigation discovery, and generated lists satisfy the Discovery
  Contract when present.
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
action, repeated pattern, and Text Inventory item inspected; records the rubric
result for each; maps rewrite decisions to the Messaging System concept that
required the change; and includes an independent reviewer verdict. Partial
sampling is allowed only with a scoped owner message containing
`FRONTEND WAIVER:`.

## Product Completeness Review

For D2/D3 work, verify that approved primary goals, relevant secondary goals,
navigation, messaging trajectory, content, interactions, endpoints, and states
exist. Verify Content And Capability Contract coverage and Discovery Contract
behavior when the surface includes information, data, media, tools, workflows,
search, filtering, navigation, recommendations, maps, indexes, generated lists,
catalogs, or other discovery interfaces. Label placeholder/demo-only surfaces
or replace them. Distinguish planned seams, mock data, disabled controls, and
future integrations from complete end-to-end behavior.

Content Coverage Audit is required before implementation and after
implementation. The pre-implementation audit records the promised corpus,
pages, sections, entities, states, capabilities, and source evidence. The
post-implementation audit verifies each promised item against implemented
routes, screens, components, data records, states, interactions, and owner-
approved boundaries.

## QA Evidence Record

Substantial implementation ends with a review under `docs/frontend/reviews/`.
Record evidence with verdicts:

```md
# Frontend Review

- Task Contract revision:
- Execution context and methods:
- Commit or working-tree state:
- Design/control session:
- Frontend Lead Contract Review Brief and reviewer/session:
- First-Use Review brief and reviewer/session:
- Source-Grounded Content Author and source map:
- Independent Copy Reviewer/session:
- Frontend Implementation Brief and implementation worker/session:
- Implementer session:
- Independent QA owner/session:
- Independent QA Brief:
- Independent QA iteration:
- Independent QA decomposition:
- Scope validated:
- Pre-implementation Content Coverage Audit:
- Post-implementation Content Coverage Audit:
- Content/capability coverage:
- Discovery/search coverage:
- Discovery QA query/filter set:
- Interaction Inventory:
- Approved HTML wireframe addresses and state matrix:
- Wireframe Conformance Contract and production mapping:
- Wireframe-to-production conformance verdict:
- Links and navigation exercised:
- Viewports and screenshots:
- Interactions exercised:
- Automated checks:
- Console/network status:
- Data/API states:
- Accessibility checks:
- Messaging System pass:
- Text Inventory coverage:
- Copy/content reviewer verdict:
- Rubric Review:
- Functional QA verdict:
- Visual QA verdict:
- Copy QA verdict:
- Responsive Design verdict:
- Product Completeness verdict:
- Instruction Control Audit:
- Known gaps and exact next action:
```

Claim each completed check with its evidence. Label the delivered
scope precisely in the final response.

## Phase Handoffs And Independent Review

Split D3 work, many-screen work, or any context-heavy task into bounded phases.
Use isolated contexts for contract review, first-use review, content authoring,
copy review, production implementation, and final QA after the Collaboration
Check records availability, the required
collaboration interface, the delegated contract, and the decision for that
named phase. Contract-review and QA workers are read-only. The production
implementation worker is write-scoped only to the files and implementation
units named in the approved Frontend Implementation Brief. Delegation does not
replace owner approval gates.

A delegated-work prompt must state the exact outcome, allowed files,
scope boundaries, required sources, approved decisions, acceptance evidence,
validation commands, and response format. Include the current Task Contract and
execution context when relevant. Provide the context the worker needs for the
assigned outcome. If the execution channel has a lifecycle completion event,
state whether the completion body must contain the full deliverable or a
compact artifact manifest. Long deliverables must be file-backed. Summary-only
completion, terminal-only prose, missing artifact paths, or post-completion
report typing does not satisfy the phase.

For D3, prefer this handoff shape:

1. The main design/control context creates a brief and allowed write scope.
2. An independent authoring context writes or updates the artifact file.
3. A separate independent reviewer checks the artifact and sources.
4. The authoring context fixes blocking findings in its write scope.
5. The reviewer rechecks only the changed artifact and previous blockers.
6. The main context records the compact author/reviewer manifests and presents
   the owner gate.

For independent QA, include the Independent QA Brief defined above. The prompt
must be more explicit than a normal engineering handoff: list every route,
interaction, viewport, text inventory category, discovery query, expected
state, and output field that must be checked. Assume the reviewer will miss
anything not listed.

For contract review, include the Frontend Lead Contract Review Brief. For
production implementation, include the Frontend Implementation Brief and
Wireframe Conformance Contract. Do not ask one worker or session to perform
contract approval, implementation, and final QA as a combined task.

When a phase must continue in another session or worktree, create a temporary
handoff containing:

- completed phase and evidence;
- canonical files changed;
- decisions and unresolved questions;
- exact next outcome;
- required and optional sources;
- constraints, risks, and validation;
- source of truth.

Move durable facts into canonical files. Archive or clear the consumed handoff
after its facts are confirmed. Fully completed tasks end with canonical
artifacts and a review.

## Persistent Frontend Memory

```text
docs/frontend/
|-- context.md
|-- product-surface-model.md
|-- messaging.md
|-- design-identity.md
|-- design-system.md
|-- component-registry.md
|-- visual-references/
|   |-- interpretation.md
|   |-- positive/
|   `-- negative/
|-- flows/
|-- wireframes/
|-- screens/
|-- decisions/
`-- reviews/
```

Persist only knowledge expected to survive the task. Context records the stack;
the Product Surface Model records capabilities; Messaging records public voice,
message contracts, proof, objections, and copy review decisions; identity and
references record visual intent; the Design System records reusable rules;
flows, wireframes, and screens record UI contracts; the component registry
records reusable building blocks; decisions record consequential trade-offs;
reviews record validation evidence.

## Completion Checklist

A frontend task is complete when:

- the Read Receipt was published before frontend action;
- the Read Receipt named active gates and active obligations separately;
- the Read Receipt used canonical obligation names and statuses;
- every skipped, narrowed, reordered, or replaced frontend instruction has a
  recorded owner message containing `FRONTEND WAIVER:`;
- D3 implementation began after Final Implementation Approval or a valid
  `FRONTEND WAIVER:` for that approval;
- D3 scope was treated as a production-grade complete surface, or a scoped
  owner waiver explicitly narrowed it;
- the requested outcome and approved scope are delivered;
- required gates or scoped waivers are recorded;
- relevant contracts match the implementation;
- D3 Product Surface drafting was preceded by Independent Factual Product
  Research, and the design/control context verified its accepted evidence;
- D3 visual boards, Selected Visual Direction Translation, UI Library/component
  showcase, directly openable HTML wireframes, state matrices, and screen
  contracts exist at named paths before implementation approval;
- UI Library Approval was recorded before production page implementation, or a
  scoped owner waiver records why it was skipped;
- Production Raster Asset Pack and approval were recorded before production
  page implementation when raster imagery, illustration, characters, product
  media, thumbnails, or generated visual language apply;
- every approved page or meaningful screen has its own wireframe package and
  screen contract, with shared shell artifacts recorded separately;
- wireframe packages link to HTML artifacts first and screenshots only as
  rendered evidence;
- every wireframe declares its W0-W3 fidelity, demonstrates the states and
  interaction intent required for approval, and lists behavior deferred to
  production;
- W3 behavior was created only after explicit owner approval;
- Independent First-Use Review was performed without repository or authoring
  context before D2/D3 Wireframe Approval and final completion;
- Independent Wireframe Rendered Visual QA inspected every required viewport
  and applicable prepared state before D2/D3 Wireframe Approval;
- the approved clickable wireflow contains no dead primary actions, broken
  route/state transitions, or manually opened intermediate screens;
- substantial D2/D3 copy was produced by a Source-Grounded Content Author and
  checked by an independent Copy Reviewer;
- D3 Text Inventory exists as a named approved artifact before implementation
  approval and maps planned text depth to rendered production copy;
- every applicable frontend Markdown contract passed Independent Contract
  Review by a potential-lead reviewer in a separate context;
- production frontend code was written in a separate implementation context by
  a write-scoped implementation worker using the approved Frontend
  Implementation Brief;
- the Wireframe Conformance Contract maps every approved page, state, and
  region to production implementation and verification evidence;
- production visual QA compared rendered pages against the selected raster
  direction, Selected Visual Direction Translation, UI library, Design Identity,
  and rejected-board counterexamples;
- production copy QA compared rendered pages and source code against the
  approved Text Inventory item by item;
- every production deviation from a frozen structural or behavioral invariant
  was re-artifacted, inspected, and approved before implementation continued;
- the full Messaging System was applied to every user-visible text fragment
  and microcopy point;
- the Interaction Inventory was exercised across links, controls, stateful
  regions, navigation, keyboard behavior, and expected events;
- independent frontend QA was performed in a separate execution context from
  the implementation context;
- design/control, production implementation, and final QA contexts remained
  separate unless a scoped owner waiver records otherwise;
- every blocking independent QA finding was fixed and independently rechecked,
  or a scoped owner message containing `FRONTEND WAIVER:` records why it
  remains;
- the required six viewport classes were inspected or a narrower owner-approved
  viewport scope was recorded;
- promised content, data, capability, and discovery coverage have evidence;
- pre-implementation and post-implementation Content Coverage Audits are
  recorded when the surface promises content or capabilities;
- search and discovery interfaces were checked with representative queries,
  filters, zero-result states, result selection, ranking/grouping behavior, and
  keyboard operation;
- the Frontend Rubric Review has verdicts and evidence for every applicable
  category and includes the independent QA verdict for implementation work;
- functional, rendered visual, copy, responsive, accessibility, and
  completeness checks proportional to depth have evidence;
- placeholders and integration seams are labeled accurately;
- durable knowledge is current and temporary handoffs are removed;
- the Final Instruction Audit names applied instructions, memory, gates,
  approvals, and evidence;
- validation passes or remaining failures are reported with cause and next command.

Optimize this process through evaluation: compare the delivered behavior and
evidence with the Task Contract. Optimize for delivered behavior, evidence,
and useful artifacts over prompt length or procedural fluency.
