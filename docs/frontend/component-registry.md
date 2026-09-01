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
- Why existing primitives were insufficient:
- Usage constraints:
- States:
- Content, data, or capability coverage:
- Discovery/search behavior:
- Accessibility behavior:
- Responsive behavior:
- Related screens:
- Validation evidence:
```

## PortalShell

- Location: `site/components/shell.tsx`
- Purpose: shared documentation shell with brand, top categories, responsive
  left tree, global search trigger, and theme toggle.
- Built from: Next `Link`, local content registry, lucide icons, local
  `SearchDialog`.
- Why existing primitives were insufficient: first frontend implementation in
  the repository has no existing shell primitives.
- Usage constraints: used by `site/app/layout.tsx` for every route.
- States: active route, mobile tree open/closed, light/dark theme.
- Content, data, or capability coverage: exposes all approved top-level
  sections.
- Discovery/search behavior: opens global search dialog.
- Accessibility behavior: labeled navigation regions, button labels, focus
  visible through global CSS.
- Responsive behavior: top nav collapses on tablet/mobile; left tree becomes a
  drawer.
- Related screens: all portal screens.
- Validation evidence: `npm run typecheck`, `npm run build`, Playwright route
  and viewport checks on 2026-09-01.

## SearchDialog And SearchResultsPage

- Location: `site/components/search-dialog.tsx`,
  `site/components/search-page.tsx`, `site/app/api/search/route.ts`
- Purpose: server-backed full-text discovery over curated portal content.
- Built from: Next App Router route handler, local search corpus in
  `site/lib/content.ts`, React client components.
- Why existing primitives were insufficient: the portal requires custom
  curated-content search, snippets, highlights, and recovery states.
- Usage constraints: searches structured portal content only, not raw Markdown
  files or runtime data.
- States: empty query, loading, results, zero-result, error, highlighted
  snippets.
- Content, data, or capability coverage: pages, glossary terms, recipes,
  journey steps, headings, summaries, tags, and body text.
- Discovery/search behavior: representative queries returned non-zero results
  in API QA.
- Accessibility behavior: labeled dialog/input and keyboard escape handling;
  full click/keyboard interaction QA is limited by available Playwright tools.
- Responsive behavior: suggestions and grouped results stack on mobile.
- Related screens: home, search, all routes through global shell.
- Validation evidence: `/api/search` returned non-zero counts for `strategy`,
  `signal`, `execution`, `risk`, `candle`, `OKX`, `backtester`, `telegram`,
  `router`, `parity`, `sink`, and `data flow`.

## SystemMap And SignalJourney

- Location: `site/components/portal-widgets.tsx`
- Purpose: teach system relationships and the end-to-end path from market data
  to decision/execution behavior.
- Built from: local content registry and React state.
- Why existing primitives were insufficient: these are product-specific
  interactive education widgets.
- Usage constraints: explain behavior only; never show runtime results,
  balances, or PnL.
- States: selected map node, selected signal step, related section links,
  mobile stacked layout.
- Content, data, or capability coverage: every approved top-level section is
  represented on the map; every signal journey stage has state and contract
  copy.
- Discovery/search behavior: links into curated sections and glossary.
- Accessibility behavior: nodes and steps are buttons with selected state.
- Responsive behavior: grids stack across tablet/mobile breakpoints.
- Related screens: home, signal journey, architecture.
- Validation evidence: Playwright screenshots for home and signal journey.

## CuratedDocPage

- Location: `site/components/doc-page.tsx`
- Purpose: shared template for curated docs pages with overview/deep-dive,
  contracts, recipes, failure modes, related links, and source evidence.
- Built from: local widgets and structured `DocPage` records.
- Why existing primitives were insufficient: pages are manually curated but
  share the same framework-docs contract.
- Usage constraints: content must be authored in structured data, not rendered
  from Markdown.
- States: tab selected, accordions open/closed, related links, source chips.
- Content, data, or capability coverage: each content page includes mental
  model, moving parts, contracts, deep dive, recipes, failure modes, glossary
  terms, and sources.
- Discovery/search behavior: body content feeds server search.
- Accessibility behavior: semantic article sections and native `details`.
- Responsive behavior: article cards and grids stack on smaller screens.
- Related screens: overview, architecture, data, strategies, backtesting, live
  execution, operations, signal journey.
- Validation evidence: `npm run build` route output and Playwright architecture
  screenshot.
