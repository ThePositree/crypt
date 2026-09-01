# Portal Navigation And Learning Flow

Revision: 1
Status: proposed for Wireframe Approval
Date: 2026-09-01

## Actor And Starting State

The reader opens the public Russian `crypt docs` portal and needs to understand
how the codebase works without seeing runtime results or raw Markdown files.

## Primary Flow

1. The reader lands on `/`.
2. The portal shows top categories, left docs tree, global search, a human
   system map, learning routes, and a signal journey preview.
3. The reader chooses one of four routes:
   - select a system-map station;
   - open a top-level docs section;
   - follow the signal journey;
   - search a concept.
4. Section pages present overview/deep-dive modes, moving parts, contracts,
   failure modes, recipes, related glossary terms, and next sections.
5. The reader reaches either a conceptual endpoint, an extension recipe, a
   glossary definition, or an operations scenario.

## Search Flow

1. The reader focuses global search or opens `/search`.
2. Empty search shows learning-route suggestions.
3. Typing sends the query to server-side search over curated portal content.
4. Suggestions show highlighted matches grouped by section.
5. Selecting a suggestion navigates to the page or anchor.
6. Submitting the query opens `/search?q=...`.
7. Zero-result state suggests broader terms, glossary browsing, and route
   categories.
8. Search errors keep navigation usable and explain that the index could not be
   read.

## Signal Journey Flow

1. The reader sees the compact journey on `/`.
2. The reader steps through data capture, normalization, strategy evaluation,
   risk checks, backtest simulation, optional live execution, and feedback.
3. Each step shows a state card and links to a deeper section.
4. Opening `/signal-journey` expands the same sequence into contracts,
   boundaries, failure modes, and recipes.

## Recovery Paths

- Unknown term: use glossary filter or related terms.
- Lost in IA: return to map or learning routes.
- Search failure: use top categories and left tree.
- Live execution details: public page explains architecture only and excludes
  secrets, runtime values, and live account state.

## Endpoints

- Reader understands a subsystem.
- Reader finds the correct section or glossary term.
- Reader follows an extension recipe.
- Operator understands a scenario boundary without seeing private runtime data.
