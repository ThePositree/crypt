# Wireframes

Store persistent low-fidelity rendered HTML wireframes here. Wireframes are
durable, directly openable UI contracts, not screenshots, throwaway sketches,
or early production applications. They demonstrate structure, hierarchy,
interaction intent, representative states, and responsive intent before
production UI code changes. Screenshots are QA evidence for HTML wireframes and
never replace them.

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

Each real site page or meaningful screen gets its own separate wireframe. Each
real page also gets wireframe coverage for all relevant project breakpoints,
either as separate files or clearly separated breakpoint views inside that
page's wireframe package.
Each package must expose a stable directly openable HTML address for the page
and every applicable demonstration state. A shared renderer is allowed when
these addresses remain stable and are indexed individually. D2/D3 defaults to
W1 fidelity: controls may reveal prepared states, while production algorithms,
real search/ranking, persistence, clipboard integration, exhaustive keyboard
behavior, and production-grade focus management remain deferred to production
and are specified in screen contracts. W2 clickable journeys are used only
when sequence is under approval. W3 functional prototypes require explicit
owner approval.
For multi-page surfaces, keep a page-to-wireframe index that names every
approved page or meaningful screen and its directly openable HTML artifact
address. Shared
shell or layout wireframes supplement page-level wireframes and are linked
from each affected page package.
The index should also include route or state, HTML artifact address, linked
screen-contract path, six viewport classes or approved viewport waiver, state
matrix, W0-W3 fidelity, demonstrated interaction intent, behavior deferred to
production, content/discovery coverage, screenshots, and rendered inspection
evidence for each page or screen. Link HTML first and screenshots separately.

For every UI edit, read the affected wireframes first. Update or create
wireframes before production implementation when layout, navigation,
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

Wireframe Approval freezes structural and behavioral invariants. Production
may replace gray-box styling with the approved Design System, but it must
preserve approved hierarchy, sections, navigation, actions, interactions,
states, responsive transformations, accessibility relationships, and journey
endpoints. Record those invariants in a Wireframe Conformance Contract and map
them to production units before implementation.
