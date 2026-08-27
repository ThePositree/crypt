# Design System

Status: established for the first local production documentation site.

Applies to the Next.js/Tailwind documentation site for `crypt`.

## Typography

- Use a highly legible sans-serif for navigation, prose, headings, and UI.
- Use a compact monospace for commands, file paths, config keys, symbols, and
  code blocks.
- Keep docs-page headings practical and scannable. Avoid oversized marketing
  type outside the home hero.
- Do not use negative letter spacing or viewport-width font scaling.

## Spacing And Layout

- Use a documentation shell with top navigation, search, left sidebar, content
  column, and optional right-side table of contents on wide screens.
- Home page starts with a short intro and a primary docs entry grid.
- Keep page sections unframed. Use cards only for repeated doc entries, route
  summaries, and bounded tools such as search results.
- Use stable dimensions for route cards, icon buttons, search input, diagrams,
  and navigation rows so interaction states do not shift layout.
- Preferred radius: 8px or less for cards and controls.

## Color

Palette direction:

- pale peach and warm off-white for the page background;
- soft blue for live/runtime and selected navigation;
- mint for backtester parity and reproducibility;
- muted coral for warnings and safety-critical material;
- pastel yellow for orientation and docs-map highlights;
- dark warm gray for primary text.

Semantic use:

- Runtime/live: soft blue.
- Research/archive: pastel yellow.
- Backtester/reproducibility: mint.
- Warning/safety: muted coral.
- Neutral docs surfaces: off-white, paper, and low-contrast gray borders.

Avoid:

- neon exchange palettes;
- dominant dark blue/slate dashboards;
- one-hue pastel washes;
- purple-blue gradient-heavy AI defaults;
- profit-coded green/red trading theatrics.

## Surfaces

- Main background should feel like a warm docs canvas.
- Cards use subtle borders and very light shadows only when they improve
  separation.
- Code blocks use a calm high-contrast surface that remains readable inside the
  pastel system.
- Safety callouts should be visually stronger than ordinary notes without
  becoming alarming banners across the whole page.

## Iconography And Illustration

- Use simple line icons for navigation and actions when an icon library is
  present.
- Use AI-generated bitmap illustration for the primary hero if implementation
  time allows; otherwise use a designed CSS/HTML placeholder only as a temporary
  implementation detail before final visual QA.
- Hero art must depict a public-safe cartoon execution room: OKX sync, strategy
  config, backtester replay, docs, and Telegram reporting as conceptual panels.
- Do not include balances, secrets, real account state, or profit promises.

## Diagrams

- Architecture and runtime diagrams are web-native components, not markdown
  screenshots.
- Diagrams use labeled nodes, directional connectors, and responsive stacking.
- Labels must stay readable on mobile. Prefer simplified mobile versions over
  squeezed full diagrams.
- Use semantic colors consistently with page domains.

## Navigation

- Top navigation items: Docs, Architecture, Research, Backtester.
- Include search in the docs shell.
- Documentation pages use left sidebar navigation.
- Hide changelog and task documents from the public site.
- Deep pages link back to canonical markdown sources when useful.

## Search

- First version includes full-text search.
- Prefer the simplest reliable local implementation during build, such as a
  generated client-side index over curated frontend content.
- Search result items should show title, section, and a short excerpt.

## Code And Commands

- Provide syntax highlighting for code blocks and shell commands.
- Command blocks must preserve copyable text and wrapping behavior.
- Keep command explanations concise; the page should remain documentation-first.

## Responsive Principles

- Desktop: full docs shell with top navigation, sidebar, content, and optional
  right table of contents.
- Tablet: preserve sidebar if space allows, otherwise collapse it behind a
  clear navigation control.
- Mobile: prioritize search, current section, readable content, and route
  navigation. Diagrams may become stacked process lists.
- Text, buttons, cards, diagrams, and code blocks must not overlap or overflow
  incoherently.

## States

- Search: empty, focused, results, no results.
- Navigation: normal, hover, active, mobile open/closed.
- Docs content: normal, missing content/build error, long code overflow.
- Links/buttons: hover, focus-visible, disabled where applicable.
- Callouts: note, benchmark caveat, safety warning, runtime truth.
