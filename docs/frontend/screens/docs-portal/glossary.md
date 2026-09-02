# Glossary

## Purpose

Define project and trading-system terms in Russian with stable cross-links to
the subsystem pages.

## Required Content

- Candle, closed candle, signal, strategy, portfolio, backtest, replay,
  warmup, accounting window, risk base, OKX, dry-run, live money, no look-ahead
  bias, Railway, configuration, archive, candidate, router, and reconciliation.
- Synonyms and search aliases.
- Links to relevant pages.

## Sources

- `README.md`
- `docs/state/current.yml`
- `docs/backtester_regression.md`
- `docs/execution/live_execution.md`
- `docs/strategy_benchmark.md`

## Primary Action

Search a term, then follow its subsystem cross-link.

## Information Hierarchy

- Alphabetical/domain grouped terms.
- Russian definition with English aliases.
- Source subsystem links.
- Boundary notes for live-money and result-sensitive terms.

## Components

- Breadcrumbs, reference/search badges, source notice, term index, alias chips,
  accordion definitions, glossary snippet, next-reading cards, right TOC.

## Interaction Inventory

- Term groups expand independently.
- Alias chips link to search results or subsystem pages in production.
- Search routes Russian, English, and domain-adjacent synonyms here.

## Data Sources And Trust Boundaries

- Curated from README, current state, backtester regression, live execution,
  and strategy benchmark docs.
- Definitions avoid performance claims and current runtime facts.
- Glossary links explain concepts; they do not render source markdown.

## States

- Default grouped glossary.
- Filtered/search-result glossary.
- Expanded term definition.
- Zero-result recovery via search overlay.
- Dark theme.

## Responsive Behavior

- Term index becomes a single column on mobile.
- Alias chips wrap without overlapping definitions.

## Accessibility Requirements

- Terms and aliases are text, not image-only labels.
- Expanded definitions expose state in production.
- Search recovery links are keyboard reachable.

## Acceptance Criteria

- Search queries can find terms by English and Russian/domain-adjacent labels.
- Definitions do not include performance claims.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=glossary`
