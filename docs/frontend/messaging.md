# Messaging

Status: proposed.
Revision: 1
Approval source: pending owner approval.

Use this file for durable frontend messaging knowledge: public product voice,
page-level text contracts, proof needs, objection maps, microcopy rules, and
copy review findings.

## Messaging Identity

- Directness: direct and practical.
- Formality: professional Russian, readable without corporate gloss.
- Technical depth: framework-documentation depth; start with a mental model,
  then expose contracts, flows, recipes, and failure modes.
- Claim confidence: confident when backed by repository evidence; careful when
  describing live/runtime behavior because loaded config and OKX state remain
  sources of truth.
- Emotional intensity: calm, useful, curious.
- Humor: allowed through lo-fi characters and friendly visual moments, but copy
  stays technically grounded.
- Relationship to the user: a guide through the system, not a marketing voice.
- Natural phrases: "как устроено", "путь сигнала", "контракт модуля",
  "что можно расширить", "где проходит граница ответственности".
- Foreign phrases: financial-promotional claims, generic SaaS slogans,
  unexplained runtime promises, raw dumps of internal paths as primary copy.
- Owner preference signals: Russian language, documentation-portal framing,
  framework-like depth, product-style pages, noticeable cartoon lo-fi style,
  no financial-advice disclaimer.
- Private owner language not suitable for public copy: casual chat phrasing and
  shorthand should be translated into polished public Russian.
- Evidence: owner chat on 2026-09-01, `README.md`, `docs/state/current.yml`.

## Messaging Contract

- Page or screen: portal home.
- Why it exists: orient the reader in the whole `crypt` system and route them
  to the right learning path.
- Audience: public technical readers, future maintainers, and operators who
  need to understand the codebase behavior.
- Starting user state: the reader sees a large crypto strategy codebase and
  needs a map.
- Intended leaving state: the reader understands the main system areas and has
  selected a route, search query, or signal journey.
- Main idea: market data moves through research, strategy logic, backtesting,
  and optional live execution as one explainable engineering system.
- First messages: what the portal covers, how the system is organized, and how
  to start.
- Later messages: deeper contracts, extension recipes, operational boundaries,
  glossary relationships.
- Objections to answer: no live results shown; pages are manually curated; live
  execution details avoid secrets and runtime values.
- Required proof: clickable map, visible learning routes, search, and concrete
  section summaries.
- Natural action: select a system node, open a section, follow a learning
  route, or search a concept.
- Generic-copy risks: abstract "powerful platform" language and claims that do
  not map to a visible docs structure.

## Message Trajectory

- Starting state: reader needs orientation.
- Problem or tension: the codebase contains research, backtesting, and live
  execution paths that are easy to confuse without a system model.
- Product explanation: the portal is a curated Russian guide to how `crypt`
  works.
- Mechanism: top categories, left tree, interactive maps, signal journey,
  glossary, recipes, and full-text search.
- Proof: page contracts, system nodes, curated explanations, and repository
  evidence.
- Objection handling: the portal does not expose live runtime values and does
  not render Markdown files directly.
- Action: choose a learning path or search a concept.

## Text Hierarchy

- Level 1 main promise: curated Russian framework-style docs for understanding
  the `crypt` system.
- Level 2 section arguments: each top-level section explains a subsystem's role
  in the full trading workbench.
- Level 3 supporting copy: moving parts, contracts, invariants, flows,
  extension recipes, failure modes.
- Level 4 action copy: "Открыть раздел", "Показать путь сигнала", "Искать в
  документации", "Развернуть рецепт".
- Level 5 microcopy: search hints, empty states, zero-result suggestions,
  theme toggle labels, tab/accordion state labels.

## Proof System

- Claim: the portal explains the whole codebase.
- Required proof: complete top-level IA, page contracts, search corpus, and
  coverage audit.
- Available proof: README and existing docs establish major areas; owner
  approved all top-level sections.
- Missing proof: page-level contracts and implemented content coverage.
- Decision: add proof during screen contracts and implementation review.

## Objection Map

- Objection: "Is this showing live trading results?"
- Where it arises: home, Live Execution, Operations.
- Response: state that the portal explains architecture and behavior, not
  runtime results or account state.
- Placement: first-page scope copy and live execution page boundaries.
- Evidence: owner explicitly excluded execution results.

- Objection: "Are docs just copied from Markdown?"
- Where it arises: page content and search.
- Response: explain that pages are curated and repository docs are source
  material.
- Placement: portal intro and content coverage notes.
- Evidence: owner explicitly rejected direct Markdown rendering.

- Objection: "Can public readers see secrets or runtime values?"
- Where it arises: Live Execution and Operations.
- Response: describe architecture without secrets, loaded env values, or live
  account state.
- Placement: trust-boundary blocks.
- Evidence: owner approved detailed architecture without secrets/runtime values.

## Microcopy Rules

- Buttons and links: name the destination or action precisely.
- Navigation labels: use short Russian section names approved in the product
  surface model.
- Forms: search field label must explain that it searches the curated portal.
- Loading states: name index/search loading if visible.
- Empty states: suggest learning routes and glossary browsing.
- Error states: explain search/index failure and offer navigation fallback.
- Success states: not central in the initial portal, except copied links or
  selected filters if implemented.
- Confirmations: not central because no destructive actions exist.
- Tooltips and badges: explain interaction affordances and content type.

## Copy Review

- Scope reviewed: proposed Product Surface Model revision 1 and messaging
  identity.
- Clarity: pending final page copy.
- Specificity: proposed direction is specific to `crypt` and its subsystem
  model.
- Information depth: page contracts required before implementation.
- Messaging Identity fit: pending owner approval.
- Claim/proof fit: main claim requires page index and coverage audit.
- Objection coverage: initial objections mapped.
- Action-copy strength: proposed labels are concrete.
- Microcopy usefulness: pending component implementation.
- Scannability: pending wireframes.
- Density: pending design system.
- Coverage gaps: page-by-page copy and glossary entries not yet written.
- Slop risks: generic docs-portal wording and over-broad "everything" claims.
- Decision: use this as proposed messaging direction for Product Surface
  Approval.
- Date: 2026-09-01
