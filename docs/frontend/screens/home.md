# Home

## Purpose

Orient readers through a human system map before they choose a docs route.

## User Goals

- Understand the whole `crypt` system at a glance.
- Select a subsystem station, learning route, or signal journey.
- Search a concept without knowing the navigation tree.

## Primary Action

Select a system-map station or start search.

## Information Hierarchy

1. Top categories and search.
2. Interactive system map with selected station drawer.
3. Signal journey preview.
4. Learning routes, glossary entry points, and character guidance.

## Messaging Contract

- Starting user state: reader sees a large codebase and needs orientation.
- Intended leaving state: reader knows where to go next.
- Main idea: `crypt` is an explainable workbench from market data to research,
  backtesting, and optional live execution.
- Required proof: map stations, route cards, signal journey, and search.
- Objections: no runtime results; curated pages only.
- Natural action: open a station, route, search, or journey.
- Generic-copy risks: marketing hero copy instead of usable docs home.

## Sections

- System map.
- Selected station drawer.
- Signal journey preview.
- Learning routes.
- Search suggestions entry.
- Character helper strip.

## Content And Capability Contract

- Source corpus: approved Product Surface Model and repository docs.
- Required coverage: every top-level section appears on the home map or route
  cards.
- Required depth: concise orientation, not deep article text.
- Source-of-truth proof: page links map to screen index.
- Coverage evidence: post-implementation route coverage.

## Interaction Inventory

- Top nav links navigate to section pages.
- Search opens suggestions and can submit to `/search`.
- Map node selection updates drawer.
- Signal journey step opens `/signal-journey`.
- Theme toggle switches theme.
- Mobile menu opens left tree.

## States

loading, normal, selected node, search suggestions, search error, empty route
fallback, mobile menu open, dark theme.

## Responsive Behavior

- Narrow mobile below 640px: stacked map stations, drawer below map.
- Mobile-wide or small tablet at 640px and above: two-column route cards.
- Tablet at 768px and above: map plus drawer.
- Desktop at 1024px and above: left tree, map, drawer.
- Large desktop at 1280px and above: add learning route rail.
- Wide desktop at 1536px and above: preserve readable max-width.

## Accessibility Requirements

Map nodes are buttons with names, selected state, keyboard focus, and matching
drawer heading.

## Related Flows And Wireframes

- `docs/frontend/flows/portal-navigation-and-learning.md`
- `docs/frontend/wireframes/home.html`

## Acceptance Criteria

- Every top-level route is reachable.
- The selected map node is visible and keyboard-operable.
- The home page contains no runtime results or live account values.
