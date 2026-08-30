# Wireframes

Store persistent HTML/CSS/JS wireframes here. Wireframes are durable UI
contracts, not throwaway sketches. They show screen layout and interaction
intent before production UI code changes.

Use plain gray-box rendering:

- labeled gray blocks for navigation, content, controls, images, data regions,
  and calls to action;
- short descriptions for complex blocks;
- interaction notes for accordions, tabs, collapses, menus, forms, filters,
  search, animation, loading, empty, error, and partial-data behavior;
- responsive states for important viewport widths;
- links to related Mermaid flows and screen contracts.

Each real site page or meaningful screen gets its own separate HTML wireframe.
Each real page also gets wireframe coverage for all relevant project
breakpoints, either as separate HTML files or clearly separated breakpoint
views inside that page's wireframe package.

For every UI edit, read the affected wireframes first. Update or create
wireframes before production implementation when layout, navigation,
interaction, state behavior, visual hierarchy, or responsive structure changes.
For an isolated copy, token, or visual correction that changes none of those
properties, verify that the existing wireframe remains accurate and record the
result in the Task Contract.

Before Wireframe Approval, record artifact revision, rendered viewport sizes,
covered states, open questions, and the exact implementation scope approval
unlocks.

## Public Portal Wireframe Set

Status: ready for owner Wireframe Approval.
Revision: 3.

- `overview.html`
- `architecture.html`
- `research.html`
- `strategies.html`
- `execution.html`
- `concepts.html`
- `history.html`
- `search.html`

Shared evidence: `wireframe.css` and `wireframe.js`.

Target render sizes: 390 x 844, 768 x 1024, 1440 x 1000, and 1728 x 1117.
Covered states: normal, loading, empty, error, disabled, overflow, and partial
evidence. Revision 2 adds generated hero illustration and an asymmetric,
overlapping Overview composition. Open question: final recurring guide name.
Approval unlocks the Next.js App Router + Tailwind CSS production
implementation for all eight pages.

Revision 3 extends the visual system across every page. Architecture uses a
forking field map; Research, Strategies, Concepts, and Search use differently
cropped evidence-bench scenes; Execution and History use a protected archive
vault. Chapter titles overlap imagery from alternating sides, and body regions
may use offset specimens instead of repeated symmetric bands.
