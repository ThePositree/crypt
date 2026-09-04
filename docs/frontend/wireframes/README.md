# Wireframes

Store persistent low-fidelity rendered HTML clickable wireflows here. Wireframes are
durable, directly openable UI contracts, not screenshots, throwaway sketches,
or early production applications. They demonstrate structure, hierarchy,
interaction intent, representative states, and responsive intent before
product-surface route/screen implementation. P06 production UI-library source
and its showcase intentionally precede wireframes. Screenshots are QA evidence
for HTML wireframes and never replace them.

Use plain gray-box rendering:

- labeled gray blocks for navigation, content, controls, images, data regions,
  and calls to action;
- short descriptions for complex blocks;
- notes for the semantic job of user-visible copy blocks;
- coverage notes for content, data, media, levels, tools, workflows, search,
  filtering, navigation, recommendations, maps, indexes, catalogs, and
  generated output when the surface promises them;
- interaction notes for accordions, tabs, collapses, menus, forms, filters,
  search, animation, loading, empty, error, and partial-data behavior;
- responsive states for important viewport widths;
- links to related flows and screen contracts.

Use grayscale only. Do not use brand colors, gradients, textures, shadows,
decorative backgrounds, final imagery, mascots, or polished visual-direction
styling. Represent media with a labeled rectangle and an `X` placeholder.

Keep real text only for product/page names, navigation, primary actions, and
approved domain terms where wording affects information architecture. All other
copy is visible meta-text stating the block purpose, intended content, expected
character or line range, proof/source need, media type or absence, and
interaction behavior. Preserve realistic density so wrapping and layout can be
reviewed before final copy exists.

Every real site page or meaningful screen gets its own route-index row and
stable directly openable HTML address for every applicable demonstration
state. Create one source package per unique route template and one delta
package per structural, interaction, state, responsive, or accessibility
exception. A route may share a package only when its Product Surface template
record proves those properties are identical; its fixture must still expose
the promised hierarchy, section count, media slots, actions, and realistic
content density. A shared renderer is allowed when addresses remain stable and
are indexed individually. D2/D3 defaults to W1 fidelity as a clickable
wireflow. Every production route, navigation action, overlay entry/exit, and
primary journey transition must work through linked fixtures or prepared
states, so reviewers never have to open screens manually.
Controls may reveal prepared states, while production algorithms,
real search/ranking, persistence, clipboard integration, exhaustive keyboard
behavior, and production-grade focus management remain deferred to production
and are specified in screen contracts. W2 clickable journeys are used only
when sequence is under approval. W3 functional prototypes require explicit
owner approval.
For multi-page surfaces, keep a page-to-wireframe index that names every
approved page or meaningful screen, Product Surface `template_id`, canonical
content ID, directly openable HTML artifact address, and evidence-equivalence
class. Shared shell or layout wireframes supplement template packages and are
linked from each affected route row.
The index should also include route or state, HTML artifact address, linked
screen-contract path, six viewport classes or approved viewport waiver, state
matrix, W0-W3 fidelity, demonstrated interaction intent, behavior deferred to
production, content requirements, screenshots, and visual inspection evidence
for each page or screen. A reviewed template may supply structural and rendered
evidence for identical routes; every exception needs its own evidence. Link
HTML first and screenshots separately.

For every UI edit, read the affected wireframes first. Update or create
wireframes before product-surface implementation when layout, navigation,
interaction, state behavior, visual hierarchy, or responsive structure changes.
For an isolated copy, token, or visual correction that changes none of those
properties, verify that the existing wireframe remains accurate and record the
result in the Task Contract.

Before Wireframe Approval, run an Independent First-Use Review whose reviewer
receives only a short neutral product description, rendered artifacts, and
first-use tasks, and is forbidden from reading repository or authoring context.
Then record artifact revision, the page-to-wireframe
index, directly openable HTML addresses, rendered viewport sizes, state matrix,
fidelity, demonstrated interaction intent, deferred production behavior, the
First-Use Review result, open questions, artifact-phase rubric verdicts,
and the exact implementation scope approval unlocks.

Run a separate Independent Wireframe Rendered Visual QA at every required
viewport and applicable prepared state. Browser screenshots or live rendered
inspection are required; DOM, accessibility snapshots, CSS reading, and author
self-checks are insufficient. Treat overlap, clipping, unreadable required
text, horizontal page overflow, dead primary actions, broken route/state flow,
unreachable approved screens, and missing viewport evidence as blockers. Do
not request Wireframe Approval while any such blocker or pending required
viewport remains.

Every screenshot uses a unique path and records wireframe revision, content
hash, viewport/state, capture time, and capturer. Do not overwrite evidence.
A write-scoped independent Wireframe Author creates the D3 wireflow. The
separate independent reviewer opens or captures it; author preflight and
phase-main inspection cannot satisfy this gate.

Wireframe Approval freezes structural and behavioral invariants. Production
may replace gray-box styling with the approved Design System, but it must
preserve approved hierarchy, sections, navigation, actions, interactions,
states, responsive transformations, accessibility relationships, and journey
endpoints. Record those invariants in a Wireframe Conformance Contract and map
them to production units before product-surface implementation.
