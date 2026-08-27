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

These components are used by the first Next.js/Tailwind documentation site.

## TopNav

- Location: `components/top-nav.tsx`.
- Purpose: global product-docs navigation for `crypt`.
- Built from: Next.js links, Tailwind layout, icon primitives where available.
- Usage constraints: primary items are Docs, Architecture, Research, and
  Backtester.
- States: normal, hover, active, mobile open/closed.
- Related screens: all public docs screens.

## SearchBox

- Location: `components/search-box.tsx`.
- Purpose: full-text search over curated frontend documentation content.
- Built from: client-side search index or simplest reliable local alternative.
- Usage constraints: must show title, section, and excerpt.
- States: empty, focused, results, no results.
- Related screens: docs shell, home, docs index.

## DocsSidebar

- Location: `components/docs-shell.tsx`.
- Purpose: section navigation inside documentation routes.
- Built from: curated docs IA.
- Usage constraints: hide changelog and task docs.
- States: normal, active, collapsed/mobile.
- Related screens: docs pages.

## SafetyCallout

- Location: `components/safety-callout.tsx`.
- Purpose: highlight runtime truth, exchange truth, no look-ahead, benchmark
  caveats, and public-safe limitations.
- Built from: semantic color variants.
- Usage constraints: use stronger visual emphasis than ordinary notes without
  turning pages into warning banners.
- States: note, benchmark caveat, safety warning, runtime truth.
- Related screens: live execution, backtester, research, setup.

## FlowDiagram

- Location: `components/flow-diagram.tsx`.
- Purpose: web-native diagrams for architecture and live runtime flow.
- Built from: responsive HTML/CSS components.
- Usage constraints: must remain readable on mobile through stacking or
  simplified layouts.
- States: desktop flow, mobile stacked flow.
- Related screens: home, architecture, live execution, backtester.

## DocPage

- Location: `components/doc-page.tsx`.
- Purpose: shared source-backed documentation page header, safety callout
  insertion, markdown content rendering, and docs shell composition.
- Built from: `DocsShell`, `MarkdownContent`, `SafetyCallout`, and
  `lib/docs.ts`.
- Usage constraints: use for curated public docs only.
- States: normal, safety-callout present, no safety-callout.
- Related screens: all `/docs/[slug]` pages and section entry routes.

## MarkdownContent

- Location: `components/markdown-content.tsx`.
- Purpose: render copied frontend markdown content with headings, lists, links,
  tables, blockquotes, and language-labeled code blocks.
- Built from: local markdown block parser.
- Usage constraints: supports the markdown features used by the curated docs;
  upgrade to a full markdown renderer if future docs need richer syntax.
- States: normal, wide code/table overflow.
- Related screens: all source-backed docs pages.
