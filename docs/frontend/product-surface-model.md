# Product Surface Model

Status: proposed.
Revision: 1
Approval: pending owner Product Surface Approval.

Use this file for durable frontend product-surface understanding. It should be
filled before substantial new site/app work, major redesigns, or broad product
surfaces.

Do not ask the owner to repeat product information that already exists in the
repository. First discover product knowledge from sources such as `README.md`,
project docs, requirements, specs, current state, task context, or a canonical
`product.md`/`PRODUCT.md` when present.

## Product Knowledge Sources

- Primary: owner onboarding answers on 2026-09-02.
- Supporting: `README.md`, `docs/state/current.yml`,
  `docs/agent/context_routes.yml`, and routed project documentation under
  `docs/`.
- Contradictions or gaps: existing Markdown docs are source material, not the
  portal rendering model. Runtime/live results must not appear in the portal.

## Scope Contract

- Outcome: create `crypt docs`, a large curated documentation portal that
  explains how the `crypt` codebase works as if it were a crypto-trading
  framework.
- In scope: Russian documentation pages, dual learning/reference navigation,
  full-content search, architecture and flow diagrams, practical CLI snippets,
  dark and light themes, framework-docs shell, playful pastel lo-fi visual
  language, abstract mascot support, and maturity/status labels.
- Explicitly out of scope: rendering repository Markdown files directly,
  showing execution results, live production balances, current positions,
  current backtest/live metrics, CMS integration, or runtime dashboards.
- Assumptions: all portal content is authored directly in Next.js/Tailwind
  source files and can use repository docs as curated source material.
- Unresolved decisions: exact first-release page tree, search library,
  component primitives, mascot asset production method, and final visual board.

## User Capabilities And Goals

- Primary goals: help a developer-crypto trader understand the system model,
  code architecture, strategy lifecycle, data flow, backtester semantics,
  execution constraints, configuration surfaces, operations model, and
  terminology without reading raw source first.
- Secondary goals: support quick reference lookup, guided learning, safe
  orientation around live-money concepts, and agent/developer onboarding.

## Required Content And Features

- In scope: Overview, Architecture, Backtester, Strategies, Live Execution,
  Data Pipeline, CLI, Configuration, Operations, Glossary, curated diagrams,
  search, breadcrumbs, left navigation, desktop page TOC, next-reading blocks,
  status labels, tabs, collapsible diagrams, section filters, command copy
  controls, and command palette search with `Cmd/Ctrl+K`.
- Explicitly out of scope: raw code quotes, auto-generated API docs from source
  comments, result tables from command execution, current account state, and
  mutable live execution controls.

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory: curated
  synthesis from repository docs, README, current state, architecture docs,
  execution docs, backtester docs, strategy docs, CLI docs, and code inspection
  where needed. Content is written in source files, not loaded from Markdown at
  runtime.
- User-facing coverage promised by the request and product surface: full first
  release coverage of all named sections with meaningful explanatory content.
- Included entities, sections, items, states, levels, views, or workflows:
  framework overview, learning path, architecture map, candle/data lifecycle,
  strategy decision lifecycle, portfolio/execution decision boundary,
  backtester accounting model, live OKX execution model, CLI command families,
  configuration hierarchy, operations and incident response, and glossary.
- Boundaries requiring owner approval: any live-money UI control, any display
  of current production state, any generated runtime results, and any CMS or
  Markdown-renderer pivot.
- Required depth by important page, panel, step, result, or interaction:
  framework-docs depth with conceptual explanation, diagrams, safe examples,
  and cross-links; no raw source quotation.
- Source-of-truth proof: every page contract must name the repository docs or
  code areas used as sources.
- Freshness, update, or synchronization expectations: content is manually
  curated and updated with source changes; no automatic sync is promised.
- Measurable coverage evidence: first release must map each required section
  to a page, source references, search index inclusion, next-reading links,
  and rendered QA evidence.

## Discovery Contract

- Discovery surfaces: header search field, command palette opened by
  `Cmd/Ctrl+K`, left navigation, page TOC, section filters, status labels,
  breadcrumbs, glossary links, and next-reading blocks.
- Searchable or filterable corpus: every curated page title, description,
  section heading, body content, glossary term, command snippet label, diagram
  caption, and status label.
- Indexed fields and body-content coverage: full curated content, not headings
  only.
- Ranking, grouping, sorting, or recommendation behavior: prioritize exact
  title and glossary matches, then section headings, then body matches; group
  results by documentation area.
- Result snippets, labels, or explanations: search results show page title,
  matched section, short snippet, and maturity/status label where available.
- Empty and zero-result behavior: explain that the query did not match curated
  content and offer top-level areas to browse.
- Keyboard and focus behavior: command palette is keyboard reachable, search
  results are arrow-key navigable, Escape closes overlays, and focus returns to
  the trigger.
- Representative queries or discovery tasks: `backtester`, `OKX`,
  `no look-ahead bias`, `strategy config`, `candles`, `CLI`, `Railway`,
  `risk base`, `glossary`.
- Coverage evidence: Discovery QA must run these queries and record expected
  sections before final implementation completion.

## Messaging Requirements

- Starting user state: a developer-crypto trader wants to understand a large
  research/live-execution workbench without reading all source and historical
  Markdown.
- Intended leaving state: the reader understands the framework mental model,
  knows where each subsystem lives, can follow data and decision flows, and can
  choose the next page for deeper work.
- Main idea: `crypt` is a research workbench and live execution framework for
  automated crypto perpetual strategies, documented through curated conceptual
  pages rather than raw generated docs.
- Required proof: concrete subsystem maps, flow diagrams, command examples,
  configuration boundaries, and links between learning and reference paths.
- Objections to answer: why no runtime results are shown, how live-money risk
  is kept separate, how backtests avoid look-ahead bias, and how curated docs
  stay grounded in source truth.
- Natural action: start the guided path, search a term, or open a subsystem
  reference page.
- Generic-copy risks: vague platform claims, trading performance promises,
  dashboard language, and unqualified safety claims.

## User Journeys

- Actor and starting state: developer-crypto trader entering the portal.
- Goal: learn how `crypt` works from first principles.
- Steps and decisions: read overview, inspect architecture map, follow data
  flow, open subsystem pages, use search for terms, follow next-reading links.
- Error or recovery path: search no-result state points to major areas and
  glossary; missing runtime state is explained as intentionally out of scope.
- Endpoint and feedback: reader reaches a subsystem page or glossary entry with
  clear next links.

- Actor and starting state: returning developer with a specific question.
- Goal: find the relevant explanation quickly.
- Steps and decisions: use header search or `Cmd/Ctrl+K`, filter by area, open
  result, use page TOC.
- Error or recovery path: zero-result state suggests alternate domain terms.
- Endpoint and feedback: the matched page section is reachable and scannable.

## Information Architecture

- Pages or screens: Home, Overview, Architecture, Backtester, Strategies, Live
  Execution, Data Pipeline, CLI, Configuration, Operations, Glossary, Search
  overlay, and shared documentation shell.
- Navigation model: dual navigation with guided learning sequence and
  architecture/reference grouping. Every page includes breadcrumbs, left nav,
  desktop right TOC, search entry, status label, and next-reading block.

## Sections And Components

- Section: documentation shell.
- Purpose: persistent navigation, search, theme switching, breadcrumbs, and
  page structure.
- Required interactions: left-nav links, command palette, header search,
  theme toggle, mobile navigation drawer, breadcrumbs, and TOC anchors.

- Section: curated content pages.
- Purpose: explain one subsystem in framework-docs style.
- Required interactions: tabs, expandable diagrams, command copy controls,
  next-reading links, glossary links, and status labels.

## Completeness Review

- Primary goals covered: pending implementation.
- Secondary goals covered: pending implementation.
- Necessary content present: pending page contracts and implementation.
- Pre-implementation Content Coverage Audit: required before production code.
- Post-implementation Content Coverage Audit: required after production code.
- Content and capability coverage proven: pending.
- Discovery/search coverage proven: pending.
- Interaction inventory covered: pending.
- Page/screen wireframes complete: pending.
- Rubric Review complete: pending.
- Messaging trajectory present: proposed in revision 1.
- Claims backed by proof or softened: required per page.
- Objections answered where they arise: required per page.
- Core interactions present: pending.
- Journey endpoints clear: proposed.
- Placeholder/demo-only surfaces removed or marked out of scope: required.
- Required states covered: pending.

## Approval Record

- Product Surface revision: 1
- Decision: pending
- Owner feedback or waiver scope: owner onboarding answers recorded from
  2026-09-02; explicit Product Surface Approval not yet requested.
- Date: 2026-09-02
- Next phase unlocked: owner approval unlocks Visual Direction Boards and
  detailed flow/wireframe/screen-contract artifacts.

## Collaboration Record

- Delegation available: Orca intended by repository rules, but local Orca CLI
  failed with `orca-ide: bad option: --no-sandbox` on 2026-09-02.
- Required collaboration/runtime interface: Orca CLI/orchestration when
  available; otherwise fresh-session owner-run review prompts are required by
  the frontend subsystem.
- Proposed delegated scope: independent contract review, separate production
  implementation, and independent QA after approvals.
- Owner decision: pending for each named phase.
- Fallback: current session may author contracts only; implementation and QA
  gates still require separate context or explicit owner waiver.

## Independent Contract Review Record

- Frontend Lead Contract Review Brief:
- Reviewer/session:
- Contracts reviewed:
- Blocking findings and fixes:
- Re-review verdict:

## Implementation Separation Record

- Design/control session:
- Frontend Implementation Brief:
- Implementation worker/session:
- Allowed production files and units:
- Wireframe Conformance Contract:
- Independent QA worker/session:
- Owner waivers affecting role separation:
