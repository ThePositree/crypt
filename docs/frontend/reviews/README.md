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
session. The implementing agent may provide preflight evidence, but the final
review must identify the separate reviewer/subagent/session that exercised the
surface. If no subagent is available, the implementing agent must stop and
provide the owner with the exact QA prompt to run in a new session; completion
remains blocked until returned findings are fixed and rechecked. Mandatory QA
gaps are not backlog items.

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
