# Search

## Purpose

Provide production-style discovery across all curated portal content.

## Primary Action

Search and open a result.

## Information Hierarchy

1. Search input and query state.
2. Highlighted suggestions or grouped results.
3. Filters by section/type.
4. Empty, zero-result, and error guidance.

## Messaging Contract

- Starting user state: reader has a term or partial memory.
- Intended leaving state: reader reaches the relevant page, glossary term, or
  recipe.
- Main idea: search covers curated portal content, not raw repo Markdown.
- Required proof: highlighted snippets and result grouping.
- Objections: explain zero results and index errors.
- Natural action: refine query, open result, or browse routes.
- Generic-copy risks: vague "no results" without recovery.

## Content And Capability Contract

- Source corpus: curated page records, glossary entries, recipes, and headings.
- Required coverage: title, section, body, tags, glossary, recipes.
- Required depth: all page body text is searchable.
- Coverage evidence: query QA set in review.

## Discovery Contract

Queries must cover `strategy`, `signal`, `execution`, `risk`, `candle`, `OKX`,
`backtester`, `telegram`, `router`, `parity`, `sink`, and `data flow`.

## Interaction Inventory

Search input, clear button, suggestion rows, result rows, section filters,
keyboard navigation, submit, zero-result route links, retry on index error.

## States

empty query, typing, loading, suggestions, results, zero-result, index error,
focused suggestion, dark theme.

## Responsive Behavior

Filters collapse into a horizontal scroller or drawer on mobile; result
snippets remain readable and do not overflow.

## Accessibility Requirements

Search is labeled, suggestions use listbox-style keyboard behavior, highlights
do not remove accessible text, and focus returns after selection or close.

## Related Flows And Wireframes

- `docs/frontend/flows/portal-navigation-and-learning.md`
- `docs/frontend/wireframes/search.html`

## Acceptance Criteria

- Search route supports direct query URLs.
- Empty and zero-result states offer useful navigation.
- Search never exposes runtime values or private files.
