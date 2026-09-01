# Final Implementation Approval

Revision: 1
Status: approved by owner on 2026-09-01
Date: 2026-09-01

## Outcome And Scope

Build the first production-quality local implementation of the public Russian
`crypt docs` portal under `site/`.

The implementation will create a manually curated Next + Tailwind
documentation portal that explains how the `crypt` codebase works. It will not
render repository Markdown directly and will not show runtime execution
results.

## Explicit Scope Boundaries

- In scope: 11 approved routes, curated Russian content, top navigation, left
  tree navigation, server-side full-text search API, search suggestions,
  search results page, home system map, signal journey preview and deep page,
  overview/deep-dive tabs or accordions, glossary filters, recipes,
  operational scenarios, light/dark theme, responsive behavior, accessible
  focus states, and generated visual assets integrated into the UI.
- Out of scope: authentication, deployment, live account/runtime values,
  performance/result dashboards, direct Markdown rendering, financial-advice
  disclaimer, external search services, mutating external systems.

## Stack And Sources Of Truth

- Stack: Next.js App Router, React, TypeScript, Tailwind CSS.
- Next.js documentation checked through Context7:
  `/vercel/next.js`; App Router route handlers live in `app/**/route.ts` and
  export HTTP methods such as `GET`.
- Tailwind documentation checked through Context7:
  `/tailwindlabs/tailwindcss.com`; Tailwind v4 uses
  `@import "tailwindcss"` and CSS-first theme customization, with class-based
  dark mode available through `@custom-variant dark`.
- Portal source of truth: approved frontend artifacts, repository docs/source
  inspection, and curated content records in `site/`.
- Live execution truth remains loaded runtime config/env and OKX state, not
  portal copy.

## Approved Product Surface Revision

- `docs/frontend/product-surface-model.md` revision 1, approved 2026-09-01.

## Approved Visual Direction Revision

- `Storybook Control Room`, selected from board 2 on 2026-09-01.
- Primary reference:
  `docs/frontend/visual-references/positive/2026-09-01-board-2-storybook-control-room.png`.
- Secondary references:
  - board 3 for dense article layout;
  - board 4 for home map and signal journey clarity;
  - board 5 for recipes, glossary, and learning routes.

## Approved Flows

- `docs/frontend/flows/portal-navigation-and-learning.md` revision 1.

## Approved Wireframes By Page Or Screen

| Route | Wireframe | Screen Contract |
| --- | --- | --- |
| `/` | `docs/frontend/wireframes/home.html` | `docs/frontend/screens/home.md` |
| `/search` | `docs/frontend/wireframes/search.html` | `docs/frontend/screens/search.md` |
| `/overview` | `docs/frontend/wireframes/overview.html` | `docs/frontend/screens/overview.md` |
| `/architecture` | `docs/frontend/wireframes/architecture.html` | `docs/frontend/screens/architecture.md` |
| `/data` | `docs/frontend/wireframes/data.html` | `docs/frontend/screens/data.md` |
| `/strategies` | `docs/frontend/wireframes/strategies.html` | `docs/frontend/screens/strategies.md` |
| `/backtesting` | `docs/frontend/wireframes/backtesting.html` | `docs/frontend/screens/backtesting.md` |
| `/live-execution` | `docs/frontend/wireframes/live-execution.html` | `docs/frontend/screens/live-execution.md` |
| `/operations` | `docs/frontend/wireframes/operations.html` | `docs/frontend/screens/operations.md` |
| `/glossary` | `docs/frontend/wireframes/glossary.html` | `docs/frontend/screens/glossary.md` |
| `/signal-journey` | `docs/frontend/wireframes/signal-journey.html` | `docs/frontend/screens/signal-journey.md` |

## Content And Capability Contract

- Implement curated content as structured TypeScript data, not generated pages
  from Markdown files.
- Every route must have enough content to be a real page: mental model, moving
  parts, contracts/invariants, recipes or scenarios where relevant, failure
  modes, related links, and glossary links.
- Content must explain code behavior and system boundaries, not execution
  results.
- Search corpus must include all curated page text, headings, summaries,
  glossary entries, recipes, and related metadata.
- Post-implementation review must record page count, search corpus count,
  glossary entry count, recipe count, and route coverage.

## Discovery Contract

- Build a server-side `/api/search` route over a file/structured-data-backed
  index.
- Implement global search suggestions with highlighted matches.
- Implement `/search?q=...` with grouped results, section/type filters,
  snippets, empty query state, zero-result state, loading state, and error
  state.
- Keyboard search behavior must support focus, suggestion navigation, submit,
  and escape/close where applicable.

## Action Contract

Not applicable. The portal has no authentication, no destructive operations,
no deployment actions, no account mutation, and no exchange/API mutation.

## Implementation Units

- Project setup: package metadata, Next config, TypeScript config, Tailwind
  setup, lint/build scripts inside `site/`.
- Content model: curated sections, pages, glossary terms, recipes, system map,
  signal journey, and search index helpers.
- Layout shell: top navigation, responsive left tree/drawer, theme provider,
  search entry, page container.
- Core components: search dialog, search result list, system map, signal
  journey, overview/deep-dive panels, accordions, recipe cards, glossary
  filter/list, state panels, character panels.
- Routes: implement all 11 approved routes.
- Assets: create or move selected/generated raster assets into `site/public/`
  and reference them from UI.
- QA and docs: update component registry where useful, record final frontend
  review, changelog, and active task state.

## Acceptance Evidence To Collect

- `npm` or equivalent install/build commands used from `site/`.
- TypeScript/lint/build validation.
- Local dev server URL.
- Playwright rendered checks across six viewport classes for representative
  pages, including home, search, docs article page, glossary, and signal
  journey.
- Search QA for representative queries:
  `strategy`, `signal`, `execution`, `risk`, `candle`, `OKX`, `backtester`,
  `telegram`, `router`, `parity`, `sink`, `data flow`.
- Interaction inventory evidence for navigation, search, theme, tabs,
  accordions, map nodes, glossary filters, and signal steps.
- Accessibility evidence for landmarks, names, keyboard focus, contrast,
  target sizes, reading order, and reduced motion.
- Post-implementation content coverage audit.
- Final frontend rubric review.

## Known Risks And Assumptions

- Full curated content across 11 pages is broad; implementation should favor
  complete useful coverage over decorative flourish.
- Search quality depends on the structured corpus; content must be written in
  enough detail for body search to be meaningful.
- Generated board text is not source-of-truth copy; final UI copy must be
  authored manually in Russian.
- Visual style must avoid crowding article pages and must keep framework-docs
  density.
- No deployment will be performed by the agent.

## Approval Gate

Owner approved this package in chat with "утверждаю" on 2026-09-01.
