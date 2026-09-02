# Search Overlay

## Purpose

Support full-content discovery through header search and `Cmd/Ctrl+K` command
palette.

## User Goals

- Find a page, section, command concept, status label, risk boundary, or
  glossary term.
- Recover from zero-result queries.

## Discovery Contract

- Corpus: all curated source-authored page content, headings, labels,
  snippets, command labels, glossary terms, and diagram captions.
- Ranking: exact page/glossary matches first, headings second, body matches
  third, grouped by area.
- Snippets: show matched section and short contextual excerpt.
- Empty query: show high-value starting points.
- Zero results: suggest Architecture map and Glossary.

## Interaction Inventory

- Header search focus opens palette.
- `Cmd/Ctrl+K` opens palette.
- Typing updates results.
- Arrow keys move active result in production implementation.
- Enter opens active result in production implementation.
- Escape closes and restores focus.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=home&palette=1`
- `docs/frontend/wireframes/docs-portal/index.html?page=home&palette=1&q=unknown`

