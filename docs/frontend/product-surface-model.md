# Product Surface Model

Status: approved.
Revision: 1
Approval: owner approved in chat on 2026-09-01.

## Product Knowledge Sources

- Primary: owner chat on 2026-09-01.
- Supporting: `README.md`, `docs/state/current.yml`,
  `docs/agent/context_routes.yml`, and repository documentation under `docs/`.
- Contradictions or gaps: no contradiction found. The portal is a new curated
  documentation product, while existing Markdown files are only source material.

## Scope Contract

- Outcome: a large public documentation portal that explains how the `crypt`
  codebase works as an engineering system.
- In scope: manually curated Russian docs pages, framework-style navigation,
  server-side full-text search, interactive system map, signal journey block on
  the home page, dedicated deep signal journey page, glossary, recipes, live
  execution architecture explanations without secrets or runtime values,
  light/dark themes, generated raster visual direction boards, and a noticeable
  cartoon lo-fi pastel identity with multiple section-role characters.
- Explicitly out of scope: rendering repository Markdown files as pages,
  displaying code execution results, showing live account/runtime values,
  authentication, financial-advice disclaimers, deployment by the agent.
- Assumptions: the first implementation is locally runnable and deployable by
  the owner later; the portal content can reference repository concepts without
  exposing raw internal file paths as a primary product surface.
- Unresolved decisions: exact dependency versions, final search implementation
  details, final visual direction board selection, final page-level wireframes,
  and final screen contracts.

## User Capabilities And Goals

- Primary goals: understand the whole system, navigate its architecture, learn
  how data becomes strategy decisions and execution behavior, and extend the
  codebase safely.
- Secondary goals: search all curated documentation content, follow learning
  paths, use glossary relationships, and understand operational scenarios.

## Required Content And Features

- In scope: `Обзор`, `Архитектура`, `Данные`, `Стратегии`, `Бэктестер`,
  `Live Execution`, `Операции`, `Глоссарий`.
- Explicitly out of scope: raw result dashboards, live PnL/account state,
  automatic Markdown rendering, private operator secrets, auth flows.

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory: curated
  portal content derived from repository docs, README, source inspection, and
  approved owner decisions.
- User-facing coverage promised by the request and product surface: all major
  project areas, explained like a framework documentation site.
- Included entities, sections, items, states, levels, views, or workflows:
  home system map, top-level docs sections, left navigation tree, search
  suggestions, search result page, overview/deep-dive page modes,
  accordions/tabs, signal journey, glossary, recipes, operational scenarios,
  light and dark themes, generated character/illustration system.
- Boundaries requiring owner approval: visual direction, page inventory,
  wireframes, final implementation scope, and any reduction of content depth.
- Required depth by important page, panel, step, result, or interaction:
  overview pages must orient; deep sections must explain moving parts,
  contracts/invariants, failure modes, and extension recipes; search must
  expose the full curated content, not only titles.
- Source-of-truth proof: each page contract should name the repository docs or
  source areas used to curate it.
- Freshness, update, or synchronization expectations: content is static curated
  docs and updates through code changes, not live runtime synchronization.
- Measurable coverage evidence: page-to-contract index, search index corpus
  count, glossary entry count, route coverage, and post-implementation content
  coverage audit.

## Discovery Contract

- Discovery surfaces: global search input, quick suggestions while typing,
  highlighted matches, dedicated search results page, top navigation, left
  section tree, glossary filters, related-section links.
- Searchable or filterable corpus: all curated portal text, page titles,
  headings, summaries, glossary entries, recipe titles, and section metadata.
- Indexed fields and body-content coverage: title, section, body, headings,
  tags, glossary terms, recipes, related concepts.
- Ranking, grouping, sorting, or recommendation behavior: exact title/heading
  matches first, then body matches, grouped by top-level section with visible
  snippets.
- Result snippets, labels, or explanations: each result shows section, title,
  highlighted snippet, and type label.
- Empty and zero-result behavior: empty input shows suggested learning routes;
  zero-result state suggests broader terms and glossary browsing.
- Keyboard and focus behavior: search opens from keyboard, suggestions are
  navigable, result selection works from keyboard, focus returns predictably.
- Representative queries or discovery tasks: `strategy`, `signal`,
  `execution`, `risk`, `candle`, `OKX`, `backtester`, `telegram`, `router`,
  `parity`, `sink`, `data flow`.
- Coverage evidence: implementation review must list query outcomes and corpus
  coverage.

## Messaging Requirements

- Starting user state: the reader knows this is a crypto strategy codebase but
  may not know the system model.
- Intended leaving state: the reader can explain the major parts, pick a
  learning route, search concepts, and understand how to extend or operate the
  system.
- Main idea: `crypt` is an engineering workbench where market data moves
  through strategy research, backtesting, shared decision logic, and live OKX
  execution.
- Required proof: concrete system maps, moving-parts explanations, contracts,
  recipes, and operational scenarios from repository evidence.
- Objections to answer: whether the portal is showing live results; whether
  Markdown docs are directly rendered; whether live execution secrets or
  runtime values are exposed; how much depth each page provides.
- Natural action: choose a section, follow a learning path, inspect the signal
  journey, or search a concept.
- Generic-copy risks: vague AI-docs language, financial-product marketing
  language, overpromising autonomous trading safety, raw developer file-path
  dumps in the primary UI.

## User Journeys

- Actor and starting state: new technical reader opens the portal.
- Goal: understand the system at a high level.
- Steps and decisions: scan home system map, choose a top-level section, open
  overview, switch to deep-dive blocks, follow related concepts.
- Error or recovery path: if unsure of terminology, use search or glossary.
- Endpoint and feedback: reader reaches a section page, recipe, or glossary
  definition with related links.

- Actor and starting state: returning developer wants to extend the system.
- Goal: find the correct extension path.
- Steps and decisions: search or browse recipes, read contracts/invariants,
  inspect failure modes, follow related architecture pages.
- Error or recovery path: zero-result search suggests broader terms and
  glossary routes.
- Endpoint and feedback: developer reaches an extension recipe with conceptual
  constraints and validation expectations.

- Actor and starting state: operator wants to understand live execution
  behavior.
- Goal: understand dry-run, preflight, Railway, Telegram, incident response,
  and runtime truth boundaries.
- Steps and decisions: open Operations or Live Execution, read overview,
  expand operational scenarios, follow signal journey or glossary terms.
- Error or recovery path: missing operational values are explained as outside
  the public portal.
- Endpoint and feedback: operator understands what the code path does and which
  private runtime sources govern production.

## Information Architecture

- Pages or screens: home, search results, overview, architecture, data,
  strategies, backtester, live execution, operations, glossary, signal journey,
  recipe pages or recipe sections within major pages.
- Navigation model: top-level category bar plus left tree navigation, with
  related links and glossary backlinks.

## Sections And Components

- Section: home system map.
- Purpose: explain the whole system with human names and clickable nodes.
- Required interactions: node selection shows a short explanation and links to
  deeper pages.

- Section: signal journey.
- Purpose: show how market data becomes a decision and, when enabled, execution
  behavior.
- Required interactions: step-by-step progression, state cards, mini-animation,
  and link to dedicated deep page.

- Section: documentation page template.
- Purpose: support both quick overview and deep framework-style learning.
- Required interactions: overview/deep-dive tabs or accordions, section TOC,
  related concepts, extension recipes, failure modes.

- Section: search.
- Purpose: production-style discovery across all curated portal content.
- Required interactions: highlighted suggestions, keyboard navigation,
  dedicated results route, empty and zero-result states.

- Section: glossary.
- Purpose: alphabetic concept reference with relationships to sections.
- Required interactions: search/filter, term selection, related page links.

## Completeness Review

- Primary goals covered: pending implementation.
- Secondary goals covered: pending implementation.
- Necessary content present: pending page contracts.
- Pre-implementation Content Coverage Audit: required before implementation.
- Post-implementation Content Coverage Audit: required after implementation.
- Content and capability coverage proven: pending implementation review.
- Discovery/search coverage proven: pending search QA.
- Interaction inventory covered: pending implementation review.
- Page/screen wireframes complete: pending.
- Rubric Review complete: pending.
- Messaging trajectory present: proposed in this model.
- Claims backed by proof or softened: pending page contracts.
- Objections answered where they arise: pending page contracts.
- Core interactions present: pending implementation.
- Journey endpoints clear: proposed in this model.
- Placeholder/demo-only surfaces removed or marked out of scope: pending
  implementation.
- Required states covered: pending screen contracts.

## Approval Record

- Product Surface revision: 1
- Decision: approved
- Owner feedback or waiver scope: owner answered "да" after being asked to
  approve Product Surface Model revision 1.
- Date: 2026-09-01
- Next phase unlocked: visual direction boards, final messaging identity, flows,
  wireframes, and screen contracts.

## Collaboration Record

- Delegation available: yes through Orca, but declined by owner for this work.
- Required collaboration/runtime interface: current session only.
- Proposed delegated scope: none.
- Owner decision: declined on 2026-09-01.
- Fallback: current-session artifact and implementation work.
