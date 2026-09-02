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
| Home | `/` | `home.md` | `../wireframes/docs-portal/index.html?page=home` |
| Overview | `/overview` | `overview.md` | `../wireframes/docs-portal/index.html?page=overview` |
| Architecture | `/architecture` | `architecture.md` | `../wireframes/docs-portal/index.html?page=architecture` |
| Backtester | `/backtester` | `backtester.md` | `../wireframes/docs-portal/index.html?page=backtester` |
| Strategies | `/strategies` | `strategies.md` | `../wireframes/docs-portal/index.html?page=strategies` |
| Live Execution | `/live-execution` | `live-execution.md` | `../wireframes/docs-portal/index.html?page=live-execution` |
| Data Pipeline | `/data-pipeline` | `data-pipeline.md` | `../wireframes/docs-portal/index.html?page=data-pipeline` |
| CLI | `/cli` | `cli.md` | `../wireframes/docs-portal/index.html?page=cli` |
| Configuration | `/configuration` | `configuration.md` | `../wireframes/docs-portal/index.html?page=configuration` |
| Operations | `/operations` | `operations.md` | `../wireframes/docs-portal/index.html?page=operations` |
| Glossary | `/glossary` | `glossary.md` | `../wireframes/docs-portal/index.html?page=glossary` |
| Search overlay | global | `search-overlay.md` | `../wireframes/docs-portal/index.html?page=home&palette=1` |

## Shared Acceptance

- Every page uses Russian user-facing copy.
- Every page is manually curated in source, not rendered from repository
  Markdown.
- No page displays runtime command results, live balances, current positions,
  current production state, or live/backtest PnL metrics.
- Every page has breadcrumbs, shell navigation, search access, status/risk
  labels, source-boundary notes, content sections, and next-reading links.
- Every page is included in full-content search.

