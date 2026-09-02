# Docs Portal Screen Contracts

Status: proposed for Wireframe Approval
Revision: 1
Date: 2026-09-02

This package contains screen contracts for the approved first-release
documentation portal pages. Shared rules live in `shell.md`; page-level
contracts are scoped to curated content and interactions for each route.

## Page Map

| Page | Route | Contract | Wireframe |
| --- | --- | --- | --- |
| Home | `/` | `home.md` | `../../wireframes/docs-portal/index.html?page=home` |
| Overview | `/overview` | `overview.md` | `../../wireframes/docs-portal/index.html?page=overview` |
| Architecture | `/architecture` | `architecture.md` | `../../wireframes/docs-portal/index.html?page=architecture` |
| Backtester | `/backtester` | `backtester.md` | `../../wireframes/docs-portal/index.html?page=backtester` |
| Strategies | `/strategies` | `strategies.md` | `../../wireframes/docs-portal/index.html?page=strategies` |
| Live Execution | `/live-execution` | `live-execution.md` | `../../wireframes/docs-portal/index.html?page=live-execution` |
| Data Pipeline | `/data-pipeline` | `data-pipeline.md` | `../../wireframes/docs-portal/index.html?page=data-pipeline` |
| CLI | `/cli` | `cli.md` | `../../wireframes/docs-portal/index.html?page=cli` |
| Configuration | `/configuration` | `configuration.md` | `../../wireframes/docs-portal/index.html?page=configuration` |
| Operations | `/operations` | `operations.md` | `../../wireframes/docs-portal/index.html?page=operations` |
| Glossary | `/glossary` | `glossary.md` | `../../wireframes/docs-portal/index.html?page=glossary` |
| Search overlay | global | `search-overlay.md` | `../../wireframes/docs-portal/index.html?page=home&palette=1` |

## Wireframe Approval Index

| Page or state | Six viewport coverage | State matrix | Operable interactions | Content/discovery coverage | Inspection evidence |
| --- | --- | --- | --- | --- | --- |
| Home | required, pending full run | normal, palette, zero-search, mobile-nav, dark | route cards, filters, search, theme, nav | all first-release pages discoverable | Orca desktop preflight |
| Overview | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | framework orientation | pending page-specific full run |
| Architecture | required, pending full run | normal, dark, mobile-nav | nav, tabs, accordion, copy, TOC, next links | subsystem atlas and boundaries | Orca desktop preflight |
| Data Pipeline | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | closed-candle data flow | pending page-specific full run |
| Strategies | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | strategy lifecycle | pending page-specific full run |
| Backtester | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | simulation and accounting | pending page-specific full run |
| Configuration | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | runtime truth and config boundaries | pending page-specific full run |
| Live Execution | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | OKX architecture without live state | pending page-specific full run |
| CLI | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | command snippets without output | pending page-specific full run |
| Operations | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | runbooks and incident response | pending page-specific full run |
| Glossary | required, pending full run | normal, dark | nav, tabs, accordion, copy, TOC, next links | terms and aliases | pending page-specific full run |
| Search overlay | required, pending full run | empty, results, zero-results | keyboard open/close, input, results, recovery link | full curated content search contract | Orca desktop zero-state preflight |

## Shared Acceptance

- Every page uses Russian user-facing copy.
- Every page is manually curated in source, not rendered from repository
  Markdown.
- No page displays runtime command results, live balances, current positions,
  current production state, or live/backtest PnL metrics.
- Every page has breadcrumbs, shell navigation, search access, status/risk
  labels, source-boundary notes, content sections, and next-reading links.
- Every page is included in full-content search.
