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

## Expected Result Matrix

| Query | Expected primary result | Expected supporting results |
| --- | --- | --- |
| `backtester` | Backtester / Model | CLI / Backtester command, Glossary / backtest |
| `OKX` | Live Execution / Boundaries | Configuration / env, Operations / Railway |
| `no look-ahead bias` | Data Pipeline / Closed candles | Backtester / Model, Glossary / alias |
| `strategy config` | Configuration / Runtime truth | Strategies / active config, Live Execution / loaded strategy |
| `candles` | Data Pipeline / Closed candles | Backtester / warmup, Glossary / candle |
| `CLI` | CLI / Available commands | Backtester / command snippets |
| `Railway` | Operations / Railway boundary | Live Execution / deploy context, Configuration / env |
| `risk base` | Glossary / risk base | Configuration / risk, Strategies / production selection |
| `warmup` | Backtester / Warmup versus accounting | Data Pipeline / feature preparation |
| `unknown` | Zero-results state | Architecture map recovery, Glossary recovery |

## Primary Action

Open the active search result or recover through Architecture/Glossary when no
result matches.

## Information Hierarchy

- Search input.
- Grouped results by area and section.
- Matched snippet.
- Empty-query starting points.
- Zero-result recovery links.

## Components

- Modal/dialog container, search input, result groups, active result state,
  snippet text, empty state, zero-result state, recovery cards.

## Interaction Inventory

- Header search focus opens palette.
- `Cmd/Ctrl+K` opens palette.
- Typing updates results.
- Arrow keys move active result.
- Enter opens active result.
- Escape closes and restores focus.
- Clicking backdrop closes the overlay.

## Data Sources And Trust Boundaries

- Search index is generated from curated page data authored in source files.
- Search does not index repository markdown directly, command outputs, logs,
  balances, positions, PnL, or runtime state.
- Result snippets are documentation excerpts, not live execution facts.

## States

- Closed.
- Open with empty query.
- Open with grouped matches.
- Active result moved by keyboard.
- Zero-result state.
- Dark theme.
- Mobile overlay.

## Responsive Behavior

- Desktop centers the palette over the current page and restores prior focus
  when closed.
- Mobile uses nearly full viewport width and keeps the search input visible
  above results.

## Accessibility Requirements

- Overlay uses dialog semantics and traps focus in production.
- Initial focus moves to the palette input.
- Escape and backdrop close return focus to the opener.
- Active result is communicated programmatically in production.

## Acceptance Criteria

- The matrix queries above produce the expected primary result class in the
  production implementation.
- Zero results never strand the reader.
- Search never exposes generated markdown rendering, command output, live
  exchange/account state, balances, positions, or PnL.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=home&palette=1`
- `docs/frontend/wireframes/docs-portal/index.html?page=home&palette=1&q=unknown`
