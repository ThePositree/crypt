# Docs Portal V1 Flow

## Actor And Starting State

A crypto developer lands on the portal with partial knowledge of the repository
and wants to understand how the product system works.

## Actions

- Read the home hero and choose Architecture, Pipeline, or Search.
- Use the left navigation to open any curated page.
- Use search to query the curated page index.
- Select architecture nodes to understand subsystem responsibilities.
- Select pipeline steps to follow the research-to-runtime path.
- Select module tabs to separate research, runtime, and docs loops.

## Decisions And Conditions

- If the reader knows the term they need, search is the fastest path.
- If the reader is new to the system, Architecture and Pipeline are the intended first pages.
- If search has no match, the empty state suggests system terms.

## Resulting State And Feedback

The reader sees a page with a summary, curated sections, related-page links,
and interactive context where appropriate.

## Failure And Recovery

Search with no result shows a clear empty state. Navigation and related links
remain available from every page.

## Endpoint

The reader can explain crypt as a research-first strategy workbench with an
optional OKX execution runtime and knows which page to open next.
