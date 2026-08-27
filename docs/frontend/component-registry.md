# Component Registry

Record meaningful reusable frontend components here.

Before creating a new component, check in order:

1. Existing project component.
2. Existing UI-library primitive.
3. Composition of existing primitives.
4. New component or primitive.

Use this format:

```md
## Component Name

- Location:
- Purpose:
- Built from:
- Usage constraints:
- States:
- Related screens:
```

## Planned First Implementation Components

These components are planned for the first Next.js/Tailwind documentation site.
Locations will be filled after implementation.

## TopNav

- Location: to be implemented.
- Purpose: global product-docs navigation for `crypt`.
- Built from: Next.js links, Tailwind layout, icon primitives where available.
- Usage constraints: primary items are Docs, Architecture, Research, and
  Backtester.
- States: normal, hover, active, mobile open/closed.
- Related screens: all public docs screens.

## SearchBox

- Location: to be implemented.
- Purpose: full-text search over curated frontend documentation content.
- Built from: client-side search index or simplest reliable local alternative.
- Usage constraints: must show title, section, and excerpt.
- States: empty, focused, results, no results.
- Related screens: docs shell, home, docs index.

## DocsSidebar

- Location: to be implemented.
- Purpose: section navigation inside documentation routes.
- Built from: curated docs IA.
- Usage constraints: hide changelog and task docs.
- States: normal, active, collapsed/mobile.
- Related screens: docs pages.

## SafetyCallout

- Location: to be implemented.
- Purpose: highlight runtime truth, exchange truth, no look-ahead, benchmark
  caveats, and public-safe limitations.
- Built from: semantic color variants.
- Usage constraints: use stronger visual emphasis than ordinary notes without
  turning pages into warning banners.
- States: note, benchmark caveat, safety warning, runtime truth.
- Related screens: live execution, backtester, research, setup.

## FlowDiagram

- Location: to be implemented.
- Purpose: web-native diagrams for architecture and live runtime flow.
- Built from: responsive HTML/CSS components.
- Usage constraints: must remain readable on mobile through stacking or
  simplified layouts.
- States: desktop flow, mobile stacked flow.
- Related screens: home, architecture, live execution, backtester.
