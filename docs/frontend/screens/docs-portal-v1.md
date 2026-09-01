# Docs Portal V1

## Purpose

Explain the crypt codebase as a curated product documentation portal.

## User Goals

- Understand the research-first product shape.
- Navigate major subsystems.
- Search manually curated documentation content.
- Learn the architecture and pipeline without reading raw markdown first.

## Primary Action

Open Architecture or Pipeline from the home page.

## Information Hierarchy

1. Product explanation and portal promise.
2. Search and navigation.
3. Architecture map and pipeline stepper.
4. Curated pages and related next routes.

## Messaging Contract

- Starting user state: technical reader needs a map of the codebase.
- Intended leaving state: reader understands the system loops and boundaries.
- Main idea: research workbench first, optional live OKX runtime second.
- Required proof: subsystem pages, source-of-truth boundaries, interactive diagrams.
- Objections: no live results, no profit claims, no markdown rendering.
- Natural action: navigate to a subsystem page.
- Generic-copy risks: broad trading platform slogans.

## Layout

Sticky header with brand and search, side navigation on desktop, stacked
navigation on mobile, full-width content area with hand-drawn paper cards.

## Sections

- Home hero with desk illustration.
- Quick links.
- Architecture map.
- Pipeline stepper.
- Module tabs.
- Curated page grid.
- Individual docs page content.

## Components

PortalShell, SearchDialog, DeskIllustration, ArchitectureMap, PipelineStepper,
ModuleTabs, PageCard.

## Data Sources And Trust Boundaries

Curated static content lives in `lib/portal-content.ts`. The portal does not
read live exchange state, account data, backtest reports, or raw markdown files.

## States

- loading: handled by Next.js route loading defaults; no custom data loading.
- normal: page content and interactions render.
- empty: search empty state.
- error: unknown docs slug returns Next.js not-found behavior.
- disabled: none in scope.
- overflow: search results scroll inside the dialog.
- partial data: out of scope because content is static and curated.

## Responsive Behavior

Mobile and desktop are first-class. Header and navigation stack on mobile;
desktop uses sticky side navigation and wider grid compositions.

## Accessibility Requirements

Keyboard focus must be visible. Navigation is labeled. Search uses dialog
semantics and labeled close control. Icon-only controls require labels.

## Copy And Microcopy Requirements

Copy stays specific to crypt. Avoid performance claims. Runtime copy must make
the optional boundary and source-of-truth rules explicit.

## Visual Emphasis

Pastel cartoon lo-fi developer desk, hand-drawn borders, terminal/notebook/
sticky-note motifs, dark ink outlines, and light paper surfaces.

## Related Screens

All curated docs pages share the same screen shell.

## Related Flows And Wireframes

- `docs/frontend/flows/docs-portal-v1.md`
- `docs/frontend/wireframes/docs-portal-v1.md`

## Acceptance Criteria

- Observable behavior: home and all docs pages render; search returns relevant pages; architecture map, pipeline stepper, and tabs respond to user selection.
- Required states: search empty state and unknown route not-found behavior.
- Rendered evidence: desktop and mobile inspection recorded in review.
- Automated checks: `npm run build`.
