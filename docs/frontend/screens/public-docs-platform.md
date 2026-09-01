# Public Docs Platform

- Date: 2026-09-01
- Status: proposed for implementation approval
- Visual direction: Docs Town
- Wireframe:
  `docs/frontend/wireframes/public-docs-platform.html`
- Flow:
  `docs/frontend/flows/public-docs-platform.md`

## Purpose

Create a production-ready public docs platform that explains `crypt` as a
Python research desk for crypto strategies through curated pages, diagrams,
search, versioning, and guides.

## User Goals

- Understand the project from a system map before reading detailed pages.
- Navigate by topic or by role journey.
- Search all public curated docs, concepts, glossary terms, guides, and
  architecture nodes.
- Follow guide steps that show command, expected output, and explanation.
- Understand risk boundaries without private live-money details.

## Primary Action

Use the interactive Docs Town map or global search to choose the next page.

## Information Hierarchy

1. Product identity and global controls: `crypt`, search, version selector.
2. Docs Town interactive system map.
3. Topic navigation and journey navigation.
4. Curated page tiles and guide pattern.
5. Search results, glossary, source links, and risk boundary.

## Messaging Contract

- Starting user state: reader knows Python or crypto but does not yet understand
  how this repository fits together.
- Intended leaving state: reader can explain the project shape and choose a
  next subsystem or guide.
- Main idea: `crypt` is a curated Python research desk for strategy discovery,
  exact backtesting, result interpretation, and neutral execution boundaries.
- Required proof: architecture map, source-linked pages, version labels,
  guide steps, and clear risk limits.
- Objections: trading hype, private data exposure, unclear code path, generic
  docs shell, unsupported performance claims.
- Natural action: search, click a map node, choose a role journey, or open a
  guide.
- Generic-copy risks: broad trading slogans, invented APIs, ornamental mascot
  text, or unverified performance language.

## Layout

Desktop:
- left sidebar with topic navigation, version selector, and helper card;
- top bar with global search, utility icons, and active version;
- central illustrated Docs Town map;
- right rail for current journey, related docs, and page-local guidance;
- lower bands for curated page tiles, guide patterns, and component states.

Mobile:
- compact top bar with menu, search, and version;
- map becomes vertically scrollable or simplified into large tappable regions;
- topic and journey navigation move behind sheet/tabs;
- guide cards stack one column;
- search modal fills the viewport.

## Sections

- Docs Town Map: clickable regions for Data Station, Engine Workshop, Strategy
  Studio, Backtest Lab, Report Library, Execution Boundary Bridge, and Risk
  Clinic.
- Search: backend-backed global search over public curated content.
- Page Tiles: Overview, Architecture, Strategy Lifecycle, Backtester, Live
  Execution, Glossary, For Developers, For Crypto Traders, Risk & Limits.
- Guide Pattern: command, expected output, explanation.
- Version Selector: semver options and current marker.
- Risk Callout: one local card linking to the dedicated Risk & Limits page.

## Components

- App shell
- Topic sidebar
- Version selector
- Search trigger and search modal
- Interactive map node
- Journey progress
- Page tile
- Guide step
- Command copy control
- Expected output panel
- Explanation panel
- Glossary card
- Risk callout
- Mascot helper

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory: curated site
  content derived from repository README, selected docs, and public code
  structure.
- Required coverage: every approved first-version page must have curated body
  copy, source references, related links, and search index entries.
- Required depth: major subsystem pages require diagrams and workflow
  explanation; guide pages require command/output/explanation; glossary terms
  require plain but technical definitions.
- Source-of-truth proof: pages cite local source paths or docs paths.
- Coverage evidence: route inventory, search index count, and visual review.

## Discovery Contract

- Search, filter, navigation, recommendation, map, index, or catalog surfaces:
  global search, topic nav, journey nav, map nodes, glossary index, related
  links.
- Corpus and indexed fields: title, route, type, version, body summary,
  headings, tags, subsystem, journey, glossary aliases.
- Body-content coverage: all curated page summaries and important guide steps.
- Ranking, grouping, sorting, or result explanation: exact title/glossary
  matches first, then tags, then body; grouped by type.
- Empty and zero-result behavior: suggest broader project terms and route
  entry points.
- Representative queries or discovery tasks: `backtester`, `OKX`, `risk`,
  `strategy lifecycle`, `closed candles`, `fees`, `telegram`, `glossary`.
- Coverage evidence: API checks and manual rendered search QA.

## Data Sources And Trust Boundaries

- Public docs content is curated and versioned.
- Search index contains public content only.
- Live execution page explains architecture and constraints, not current
  account state, private runtime config, active positions, credentials, or
  trading instructions.
- The UI does not mutate exchange, deployment, or repository state.

## States

- loading: search results skeleton; page loading is minimized through static
  content;
- normal: map, navigation, pages, and search are available;
- empty: no search results with suggested routes;
- error: search API failure with retry and navigation fallback;
- disabled: unavailable version route or disabled copy action;
- overflow: long navigation scrolls; map labels stay clipped-safe;
- partial data: version missing a page shows version-index fallback.

## Responsive Behavior

- Desktop: full Docs Town map with sidebars.
- Tablet: sidebar may collapse; map remains primary.
- Mobile: single-column page with top controls, tappable map regions, stacked
  cards, and full-screen search.

## Accessibility Requirements

- Semantic landmarks for header, nav, main, aside, and footer.
- Keyboard-reachable search, version selector, map nodes, copy buttons, and
  links.
- Visible focus states.
- Text contrast must pass practical readability on pastel surfaces.
- Mascots and decorative map details must not be the only carrier of meaning.
- Motion must respect reduced-motion preferences.

## Copy And Microcopy Requirements

- Use English public documentation voice.
- Prefer mechanism and source-backed explanation.
- Avoid profit promises and trading advice.
- Commands must have copy buttons and expected output context.
- Search empty and error states must explain the next action.

## Visual Emphasis

Use Docs Town as the first-viewport signature. The map should be useful and
clickable, with soft pastel zones and abstract mascot helpers.

## Related Screens

- Search results
- Version index
- Subsystem docs page
- Guide page
- Glossary page
- Risk & Limits page
- 404/missing version page

## Related Flows And Wireframes

- `docs/frontend/flows/public-docs-platform.md`
- `docs/frontend/wireframes/public-docs-platform.html`
- `docs/frontend/visual-references/boards/board-05-docs-town.png`

## Acceptance Criteria

- Observable behavior: map nodes, search, version selector, navigation, guide
  copy controls, and related links work.
- Content/capability coverage: approved first-version pages are curated and
  indexed.
- Discovery/search coverage: representative queries return grouped results or
  useful empty state.
- Required states: normal, loading, empty, error, disabled, overflow, and
  partial-version states are represented.
- Rendered evidence: desktop and mobile screenshots after implementation.
- Automated checks: build, lint/type check, and search API checks.
