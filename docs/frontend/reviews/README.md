# Frontend Visual Reviews

Store visual review notes for rendered frontend work here when a review produces
durable knowledge.

Use the evidence schema from `docs/agent/frontend_design_subsystem.md`. A review
records the Task Contract revision, execution context and methods, tested
commit or working-tree state, implementer session, independent QA owner or
session, Independent QA Brief, QA iteration, QA decomposition, scope, viewport
sizes and screenshots, exercised interactions, automated checks,
console/network status, data/API states, accessibility checks, copy review,
Text Inventory coverage, content/capability coverage, discovery/search
coverage, interaction inventory, link/navigation coverage, rubric review,
separate QA verdicts, known gaps, and the exact next action.

For D2/D3 or context-heavy work, also record the Collaboration Check:
delegation availability, required collaboration/runtime interface, proposed
scope, owner decision, and whether an independent result was reviewed before
integration.

`Independent` means a separate execution context, not a specific agent feature
or vendor. Give each reviewer the minimum context for its role. Contract
reviewers read the applicable contracts, not the complete frontend subsystem
unless instruction compliance is under review. Re-review briefs contain prior
blockers, changed artifacts, and closure criteria rather than full history.

Record Independent First-Use Review separately. Its reviewer receives only a
neutral two-to-five-sentence product description, the rendered surface,
first-use tasks, and an evidence format. The reviewer must not read repository
files, contracts, frontend instructions, changelogs, task history, author
notes, or earlier reviews. This review measures whether the interface itself is
understandable, navigable, trustworthy, and visually coherent to a new member
of the approved audience.

Record Independent Wireframe Rendered Visual QA separately from First-Use
Review. Give the reviewer the short neutral product description, clickable
wireflow entry address, required journeys, viewport sizes, prepared states, and
finding format. The reviewer must render and visually inspect every required
viewport and report alignment, spacing, hierarchy, wrapping, containment,
clipping, overlap, horizontal overflow, stable dimensions, navigation reach,
primary-action behavior, and responsive transformations. Source inspection,
DOM output, accessibility snapshots, and the author's screenshots without an
independent rendered check do not satisfy this gate.

Wireframe visual blockers are any overlap, clipped or unreadable required text,
horizontal page overflow, unreachable approved screen, dead primary action,
broken route/state transition, or missing required viewport inspection. A
review containing one cannot return pass, pass-with-minor-fixes, or approval
readiness. Re-render and independently recheck every affected viewport and
journey after fixes.

For substantial D2/D3 text, record a Source-Grounded Content Author and a
separate Copy Reviewer. The author receives approved messaging/page contracts
and only relevant canonical product sources. The reviewer sees rendered copy,
audience and voice criteria, but not the author's rationale.

Do not claim that a check passed without naming its evidence. Apply the visual
rubric to hierarchy, spacing, alignment, typography, density, composition,
consistency, semantic color, responsive transformations, states,
accessibility, Design Identity, Signature Traits, Anti-Identity, selected
references, and rejected-reference avoidance.

Apply the copy rubric to every user-visible text fragment, not only important
or marketing text. Cover message trajectory, text hierarchy, specificity,
Messaging Identity fit, claim/proof proximity, objection coverage, action-copy
specificity, microcopy usefulness, density, and generic-copy risk. The review
must include a Text Inventory matrix or reference to one, with location, exact
text or text pattern, semantic job, Messaging Contract link, proof status,
decision, and reviewer verdict for navigation labels, buttons, links,
headings, body copy, badges, tooltips, form text, placeholders, empty/loading/
error/success/disabled states, table/chart labels, alt text, footer text, and
repeated generated labels.

Apply the content and discovery rubric to the surface promised by the owner:
corpus or data coverage, information depth, included entities or states,
searchable body content, ranking or grouping behavior, representative queries,
empty results, and evidence that users can find and use the important material.

Apply the functional interaction rubric to every clickable, focusable,
stateful, eventful, or navigational element and region. Record expected
response, actual response, route or URL changes, state changes, observable
requests or events, keyboard behavior, feedback, and recovery behavior.

Frontend implementation reviews must be independent from the implementation
context. The implementing agent may provide preflight evidence, but the final
review must identify the separate execution context that exercised the surface.
If no independent context is available, the implementing agent must stop and
provide the owner with the exact QA prompt to run in a new session; completion
remains blocked until returned findings are fixed and rechecked. Mandatory QA
gaps are not backlog items.

Every new or materially changed frontend Markdown contract also requires an
independent read-only review before approval or implementation. The reviewer
acts as a potential frontend lead inheriting the project without the authoring
session's implicit context. Record the Frontend Lead Contract Review Brief,
reviewer/session, every contract read, contradictions and guesses found,
severity, fixes, and re-review verdict. Contract review is separate from
production QA.

Production frontend implementation is performed in a separate write-scoped
execution context from the design/control context. Final QA uses a third
independent context. Reviews record all three owners: design/control,
implementation, and QA, plus any scoped owner waiver that collapses roles.

Wireframe review links to directly openable HTML artifacts first and records
W0-W3 fidelity, demonstrated interaction intent, deferred production behavior,
and Independent First-Use Review evidence. Screenshots are viewport/state
evidence only. Production review includes the Wireframe
Conformance Contract and an invariant-by-invariant comparison between approved
HTML wireframes and production behavior.

Use the six viewport classes from the frontend subsystem for D2/D3 reviews
unless an owner-approved viewport boundary narrows the surface. Record the
Frontend Rubric Review verdicts and evidence for every applicable category.
For artifact-phase approvals, record the rubric against the artifact package
being approved and include the page-to-artifact path map when pages or screens
are part of scope.

Record instruction control with the canonical obligation names from the
frontend subsystem, their final statuses, and any owner messages containing
`FRONTEND WAIVER:` that skipped, narrowed, reordered, or replaced an otherwise
applicable instruction.
