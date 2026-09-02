# Docs Portal Navigation Flow

Status: proposed for Wireframe Approval
Revision: 1
Date: 2026-09-02
Related product surface: `docs/frontend/product-surface-model.md` revision 1
Approved visual direction: Board 3, `System Islands Atlas`

## Scope

This flow covers the curated `crypt docs` portal before production
implementation. It defines navigation and discovery behavior only; it does not
authorize live-money controls, runtime dashboards, or command-result displays.

## Actors

- Developer-crypto trader learning the framework from first principles.
- Returning developer searching for a subsystem, term, command family, or risk
  boundary.

## Top-Level Flow

1. User lands on Home.
2. User chooses one of two primary routes:
   - Guided route: Overview -> Architecture -> Data Pipeline -> Strategies ->
     Backtester -> Configuration -> Live Execution -> CLI -> Operations ->
     Glossary.
   - Reference route: use left navigation, architecture map, search,
     command palette, breadcrumbs, page TOC, status/risk filters, or glossary
     links.
3. User reaches a curated page with:
   - page purpose and maturity/status labels;
   - source-boundary note;
   - conceptual explanation;
   - diagram or structured map when relevant;
   - practical command snippets when relevant;
   - next-reading block.
4. User either continues through next-reading links, opens a related reference
   page, or searches for a new term.

## Search Flow

1. User focuses the header search field or presses `Cmd/Ctrl+K`.
2. Command palette opens with grouped full-content results.
3. Results are grouped by area and include page title, matched section,
   snippet, and status/risk label.
4. Arrow keys move active result; Enter opens; Escape closes and returns focus
   to the trigger.
5. Empty query shows high-value starting points.
6. Zero-result query suggests browsing the framework map and glossary.

Representative queries: `backtester`, `OKX`, `no look-ahead bias`,
`strategy config`, `candles`, `CLI`, `Railway`, `risk base`, `glossary`.

## Theme Flow

1. User toggles light/dark theme from the shell.
2. Theme changes the documentation chrome and content surfaces.
3. Content hierarchy, risk color meaning, and focus visibility remain
   equivalent.
4. Preference persists in production implementation if storage is approved.

## Mobile Flow

1. Left navigation collapses into a drawer.
2. Page TOC becomes an in-page expandable region.
3. Search remains visible through header icon and command palette.
4. Atlas maps become stacked subsystem cards.
5. Next-reading remains at the end of every page.

## Failure And Recovery

- Search unavailable: show an explicit local documentation search error and
  keep left navigation usable.
- No results: show zero-result guidance and link to the framework map and
  glossary.
- Missing page content: production implementation must not ship placeholder
  pages; incomplete sections must be clearly scoped or blocked before final
  approval.

## Endpoints

- Guided learning endpoint: Glossary or Operations page with next links back
  to Overview and Architecture.
- Reference endpoint: target subsystem section opened with TOC and next-reading
  paths visible.
- Recovery endpoint: user reaches Architecture or Glossary from a failed
  search.

