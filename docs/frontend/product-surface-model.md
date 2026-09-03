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

- Primary: `README.md`, `docs/state/current.yml`, `docs/architecture.md`,
  `docs/backtester_regression.md`, `docs/execution/live_execution.md`,
  `docs/strategy_benchmark.md`, `docs/cli.md`.
- Supporting: `docs/agent/context_routes.yml`,
  `docs/backtester/candidate_archive.md`,
  `docs/discovery/direct_signal_search_v3.md`,
  `docs/strategies/incremental_router_runtime.md`,
  `docs/operations/observability.md`, `docs/operations/ci.md`, `pyproject.toml`,
  `src/crypt/`, `src/backtester/`.
- Contradictions or gaps: `docs/architecture.md` still includes historical
  architecture notes and says web dashboard is out of MVP, while owner now
  requests a documentation portal. The portal must describe active code and
  historical/deferred capabilities distinctly.

## Independent Factual Product Research Record

- Research brief: independent read-only Orca task
  `task_e82645aecda0`, run `run_87fce7d102ff`, asks for a factual system and
  capability map for a Russian documentation portal that explains `crypt` as a
  crypto framework.
- Researcher/session: Orca native `cursor` worker
  `ctx_ab8ef2e316a5`, model `gemini-3.7-flash-high`.
- Canonical sources inspected: worker reported inspection of repository docs,
  `src/crypt/`, and `src/backtester/`; main session verified the material
  claims against the Product Knowledge Sources above and module inventory.
- Factual system and capability map: accepted with one rejected path noted
  below. `crypt` has two active code contours: `src/backtester/` for research,
  DSS, Optuna geometry optimization, simulation, benchmark/regression reports,
  archive/replay workflows, and router research; `src/crypt/` for OKX data,
  runtime scheduling, live execution, exchange sync, risk-base continuity,
  order management, state persistence, and notifications.
- Distinct runtime or user paths: accepted paths are live Railway execution,
  local live dry-run/smoke, historical `backtester run`, backtester regression
  checkpoints, DSS v3 signal search, Optuna geometry optimization, explicit
  data backfill, and historical 4h signal alerting.
- Active, historical, deferred, and absent capabilities: active includes H1
  live OKX execution, Core v4 donor portfolio execution, shared
  backtest/live risk and margin code, immutable monthly risk-base checkpoints,
  OKX position sync, DSS v3, Optuna optimization, Parquet data pipeline, and
  Russian operational Telegram notifications. Historical includes the old 4h
  Telegram signal MVP, DSS v2, single-signal flat strategy configs, removed
  legacy CLIs, and live Phase A as audit context only. Deferred/proposed
  includes live promoted-router rollout, additional sentiment/liquidation/
  calendar engines, richer observability, CI hardening, and mandatory 1m
  production data. Absent/out of scope includes L2 orderflow/tape, neural
  black-box meta-aggregators, interactive production prompts, web trading
  controls, Postgres/Redis/Docker as core runtime requirements, automatic
  multi-broker trading, and automatic production strategy switching without
  owner decision.
- Contradictions and unresolved questions: `docs/architecture.md` is valuable
  for module boundaries but contains historical MVP framing; active live
  execution is governed by `docs/execution/live_execution.md`, runtime config,
  and OKX state. Worker incorrectly referenced
  `src/crypt/data/normalizer.py`; main session rejected that path because it
  does not exist on 2026-09-03. Remaining questions: role of 1m data in
  production preflight, promoted-router promotion criteria, whether DSS v3
  standard search should include 1m/5m, and whether the legacy 4h contour
  stays as monitoring or is removed.
- Design/control verification: accepted claims were checked against
  `README.md`, `docs/state/current.yml`, `docs/architecture.md`,
  `docs/backtester_regression.md`, `docs/execution/live_execution.md`,
  `docs/strategy_benchmark.md`, `docs/cli.md`, `pyproject.toml`, and module
  inventories under `src/crypt/` and `src/backtester/`.
- Accepted evidence used by this Product Surface revision: owner onboarding
  answers from 2026-09-03 plus main-session inspection of the primary and
  supporting sources above plus verified portions of Orca worker report
  `ctx_ab8ef2e316a5`.

## Scope Contract

- Outcome: build `crypt docs`, a large Russian documentation portal that
  explains how the repository works as a crypto trading framework.
- In scope: public-style documentation portal for a developer-crypto trader;
  explanation-first home page; guided learning path; reference navigation;
  full-content search; command palette; breadcrumbs; left navigation; desktop
  on-page TOC; light and dark themes; playful lo-fi visual identity with
  abstract mascots; curated source-embedded content for Overview,
  Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI,
  Configuration, Operations, and Glossary; diagrams for data and decision
  flows; practical CLI snippets without command output; risk markers for live
  money, OKX execution, config, and no-lookahead behavior; maturity labels;
  next-reading blocks on every page.
- Explicitly out of scope: live balances, positions, current production
  metrics, execution results, exchange mutations, CMS, external search backend,
  quoting implementation source code, and running strategy/backtest jobs from
  the site.
- Assumptions: first release is a static/documentation application with all
  content in source-controlled Next.js files; search index is generated from
  curated content at build time; live execution content is architectural and
  operational only.
- Unresolved decisions: exact first implementation package path, selected
  visual direction board, final component system, final content depth per page,
  and whether any third-party local search package is worth adopting.

## User Capabilities And Goals

- Primary goals:
  - Understand `crypt` as a crypto strategy research and execution framework.
  - Learn how data, strategy discovery, backtests, portfolio decisions, and
    live OKX execution fit together.
  - Find exact conceptual answers quickly through reference navigation and
    full-content search.
  - Follow safe operational boundaries around live money, runtime config, OKX,
    and no-lookahead behavior.
- Secondary goals:
  - Discover canonical CLI commands and when to use them.
  - Understand maturity status of each subsystem.
  - Move from high-level map to detailed framework-style docs without reading
    source code inline.

## Required Content And Features

- In scope:
  - Home page as both framework map and guided start.
  - Tutorial path: start here, data flow, strategy decisions, backtesting,
    DSS/research, live execution, operations.
  - Reference path: Overview, Architecture, Backtester, Strategies, Live
    Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.
  - Full-content search and command palette via `Ctrl/Cmd+K`.
  - Diagrams for candle ingestion, feature/indicator flow, candidate discovery,
    backtest execution, portfolio routing, and live order path.
  - Expandable explanations, tabs such as concept/flow/config where useful,
    filters by section and maturity, and copyable CLI snippets.
  - Light/dark mode.
- Explicitly out of scope:
  - Runtime dashboard data.
  - Live trading controls.
  - User accounts, auth, database, CMS, comments, analytics, and external docs
    ingestion.

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory: canonical
  repository docs and code-module inventory listed in Product Knowledge
  Sources; owner answers from 2026-09-03; generated raster visual direction
  boards and asset pack after approval.
- User-facing coverage promised by the request and product surface: "huge"
  documentation portal that fully describes how the code works, without source
  code quotations and without runtime result displays.
- Included entities, sections, items, states, levels, views, or workflows:
  Overview, Architecture, Backtester, Strategies, Live Execution, Data
  Pipeline, CLI, Configuration, Operations, Glossary; guided tutorial and
  reference modes; search results, empty search, command palette open/closed,
  theme switching, navigation states, copy-snippet success/failure, expandable
  diagram states.
- Boundaries requiring owner approval: any narrowing from all listed sections,
  any omission of search, any use of live runtime data, any visual direction
  without playful lo-fi mascots, any CMS or backend dependency.
- Required depth by important page, panel, step, result, or interaction:
  framework-doc depth: module concepts, runtime flows, contracts,
  source-of-truth warnings, config and CLI examples, maturity status, next
  reading, and glossary terms. Do not quote implementation bodies.
- Snippet policy: CLI commands, shell environment examples, YAML/JSON
  configuration examples, route/content data shapes, and conceptual type
  signatures are allowed. Implementation bodies from `src/`, class bodies,
  function bodies, and long source excerpts are prohibited. Short canonical
  identifiers, module names, class names, method names, and env var names are
  allowed when they serve reference navigation.
- Source-of-truth proof: each factual claim maps to a canonical docs/code path
  in the content inventory.
- Freshness, update, or synchronization expectations: portal content is
  source-controlled and updated when repository docs/code contracts change; it
  does not synchronize with live exchange state.
- Measurable coverage evidence: page inventory, text inventory, search index
  coverage matrix, link/navigation matrix, content source map, and rendered QA
  evidence before completion.

## Discovery Contract

- Discovery surfaces: header search input, command palette, left navigation,
  reference/tutor tabs, maturity filters, page TOC, next-reading blocks, and
  glossary cross-links.
- Searchable or filterable corpus: all curated portal page titles, headings,
  body content, summaries, glossary terms, maturity labels, section tags, CLI
  snippets, risk markers, and diagram labels.
- Indexed fields and body-content coverage: title, route, section, maturity,
  summary, headings, body text, aliases/synonyms, glossary terms, and code/doc
  source references.
- Ranking, grouping, sorting, or recommendation behavior: exact title and
  glossary matches first, then heading matches, then body matches; group by
  documentation section; show maturity and risk labels.
- Result snippets, labels, or explanations: result title, section, short
  matching excerpt, maturity label, and route.
- Empty and zero-result behavior: empty query shows recommended starting
  points; zero-result state explains that search covers curated portal content
  and suggests section browsing.
- Keyboard and focus behavior: `Ctrl/Cmd+K` opens command palette; arrow keys
  move results; Enter opens; Escape closes; focus returns to the invoking
  control.
- Representative queries or discovery tasks: `backtester`, `DSS`, `no
  look-ahead`, `OKX`, `EXECUTION_STRATEGY_CONFIG`, `risk base`, `CLI`,
  `glossary`, `router`, `parquet`, `live execution`.
- Coverage evidence: search-index build test or fixture, Discovery QA matrix,
  and rendered keyboard QA.

## Messaging Requirements

- Starting user state: developer-crypto trader knows trading systems but does
  not yet know this repository's boundaries, contracts, or safe operating
  paths.
- Intended leaving state: user understands what `crypt` is, which subsystem to
  read next, where runtime truth lives, and how to find framework-style
  reference material without reading source code first.
- Main idea: `crypt` is a research-to-live framework for crypto perpetual
  strategies: it discovers candidates, validates them through backtests,
  archives evidence, and runs the owner-selected strategy through live OKX
  execution with parity and safety contracts.
- Required proof: module maps, flow diagrams, canonical doc references,
  maturity labels, CLI snippets, and explicit source-of-truth warnings.
- Objections to answer: whether this is only a Telegram bot, whether live
  execution is safe to operate from the portal, whether docs show real current
  production state, whether search covers full content, and whether strategies
  are production-gated by benchmarks.
- Natural action: choose a guided path or search/open a reference section.
- Generic-copy risks: vague "powerful trading platform" claims, inflated AI
  strategy promises, unsupported profitability language, and copy that hides
  live-money constraints.

## User Journeys

- Actor and starting state: developer-crypto trader opens the portal for the
  first time.
  Goal: understand what the framework does and how to read it.
  Steps and decisions: scan home map, choose guided start or reference, open a
  section, follow next-reading links, search for a term, inspect maturity and
  risk markers.
  Error or recovery path: zero search results suggest section browsing and
  alternative terms; unavailable live data is never shown as missing because it
  is out of scope.
  Endpoint and feedback: user lands on a specific conceptual/reference answer
  with sources and next reading.
- Actor and starting state: developer wants a safe CLI command.
  Goal: find the correct command surface without triggering long jobs or live
  execution accidentally.
  Steps and decisions: search `CLI`, filter command section, read command
  purpose and risk markers, copy snippet.
  Error or recovery path: command copy failure leaves text selectable and shows
  non-blocking feedback.
  Endpoint and feedback: copied or selected snippet plus warning about data,
  runtime config, or live-money boundary when relevant.

## Information Architecture

- Canonical route map:
  - `/` — Home / Start Here, combining framework map and guided start.
  - `/docs/overview` — Overview.
  - `/docs/architecture` — Architecture.
  - `/docs/data-pipeline` — Data Pipeline.
  - `/docs/backtester` — Backtester overview.
  - `/docs/backtester/dss-v3` — Strategy Discovery / DSS v3.
  - `/docs/backtester/optuna-geometry` — Optimization / Optuna Geometry.
  - `/docs/strategies` — Strategies and Portfolio Runtime.
  - `/docs/live-execution` — Live Execution.
  - `/docs/cli` — CLI.
  - `/docs/configuration` — Configuration.
  - `/docs/operations` — Operations.
  - `/docs/risk-boundaries` — Risk and Source-of-Truth Boundaries.
  - `/docs/glossary` — Glossary.
  - Search / command palette — overlay state available from every route, not a
    standalone page.
- Tutorial path: a curated ordered view over existing routes, not a duplicate
  route tree. Sequence: Home -> Overview -> Architecture -> Data Pipeline ->
  Backtester -> DSS v3 -> Optuna Geometry -> Strategies -> Live Execution ->
  Operations.
- Reference path: left navigation grouped by domain. Backtester owns DSS v3 and
  Optuna as child pages; Risk Boundaries is a separate cross-cutting reference
  page because it applies to data, backtests, strategies, live execution, and
  operations.
- Navigation model: top shell with global search and theme toggle; left
  framework-doc navigation grouped by Tutorial and Reference; breadcrumbs on
  every page; right on-page TOC on desktop; next-reading section on every
  content page.

## Source Map Matrix

Each production page must cover the listed concepts and source paths before
Final Implementation Approval.

| Route | Maturity | Required concept coverage | Required source map |
| --- | --- | --- | --- |
| `/` | stable | project purpose, dual tutorial/reference entry, search, safety boundaries, maturity legend | owner input, `README.md`, `docs/state/current.yml` |
| `/docs/overview` | stable | research workbench, live OKX module, historical Telegram MVP boundary, benchmark as target not gate | `README.md`, `docs/state/current.yml`, `docs/strategy_benchmark.md` |
| `/docs/architecture` | stable/historical | `src/crypt` and `src/backtester` contours, module boundaries, legacy 4h contour caveat | `docs/architecture.md`, `src/crypt/`, `src/backtester/` |
| `/docs/data-pipeline` | operational | OKX REST data, Parquet storage, candle timeframes, backfill, preflight, no-lookahead data rules | `docs/cli.md`, `docs/backfill.md`, `src/crypt/data/`, `src/crypt/backfill/`, `src/backtester/data_loader.py` |
| `/docs/backtester` | stable | replay model, next-open entries, fees, margin, liquidation, regression checkpoints, output artifacts | `docs/backtester_regression.md`, `src/backtester/execution_sim.py`, `src/backtester/tester.py`, `src/backtester/risk_model.py` |
| `/docs/backtester/dss-v3` | research | trigger/filter instances, timeframe alignment, directional labeling, QD backends, frequency classes | `docs/discovery/direct_signal_search_v3.md`, `src/backtester/strategy_discovery/` |
| `/docs/backtester/optuna-geometry` | research | exit families, RRR/TTL/risk optimization, downstream role after DSS, owner command expectations | `docs/cli.md`, `src/backtester/optimizer.py`, `src/backtester/exit_geometry.py`, `src/backtester/tp_policy.py`, `src/backtester/trailing_policy.py` |
| `/docs/strategies` | research/operational | strategy JSONs, archived candidates, Core v4 donor portfolio, promoted router research, owner promotion rights | `docs/backtester/candidate_archive.md`, `docs/strategies/incremental_router_runtime.md`, `strategies/archive/`, `src/backtester/strategies/` |
| `/docs/live-execution` | operational | parity contract, settings, signal runner, risk calculator, order placement, exchange sync, state, notifications | `docs/execution/live_execution.md`, `src/crypt/execution/` |
| `/docs/cli` | stable | supported commands, snippets, long-command boundaries, sandbox env notes, no command outputs | `docs/cli.md`, `README.md` |
| `/docs/configuration` | operational | `EXECUTION_*`, OKX/Telegram/env source truth, strategy config, dry-run boundaries | `docs/execution/live_execution.md`, `README.md`, `src/crypt/execution/settings.py`, `src/crypt/config.py` |
| `/docs/operations` | proposed/operational | Railway, preflight, observability, CI, logs, Telegram notifications, known operational gaps | `docs/deploy/railway.md`, `docs/operations/observability.md`, `docs/operations/ci.md`, `docs/execution/telegram_notifications.md` |
| `/docs/risk-boundaries` | stable | runtime truth, OKX truth, no-lookahead, closed candles, benchmark/owner override, live-money warnings | `AGENTS.md`, `docs/state/current.yml`, `docs/execution/live_execution.md`, `docs/strategy_benchmark.md`, `docs/backtester_regression.md` |
| `/docs/glossary` | stable | domain terms, env vars, class/module identifiers, maturity labels, risk labels, common aliases | all page source maps above |

## Diagram Contract

- Rendering standard: production diagrams are React SVG components that use
  Tailwind classes and CSS variables for theme-aware stroke, fill, text, and
  focus states.
- Visual style: notebook-like, hand-drawn geometry may be simulated through
  rounded lines, slight offsets, dashed connectors, and playful abstract mascot
  callouts, but required labels must stay readable and selectable where
  practical.
- Accessibility: every diagram has a text summary, visible step labels, and an
  accessible name. Complex diagrams also expose the same flow as an ordered
  text list near the SVG.
- Required first-release diagrams: data ingestion/storage flow, DSS v3
  candidate flow, backtester replay loop, strategy-to-execution parity path,
  live OKX order path, and source-of-truth boundary map.
- Deferred behavior: diagrams may have expandable step descriptions and tabs,
  but they do not run code, fetch live data, or compute strategy results.

## Sections And Components

- Section: Home framework map.
  Purpose: orient the user and expose both guided and reference routes.
  Required interactions: search, command palette, theme toggle, section cards,
  maturity filters, next-reading links.
- Section: Page content template.
  Purpose: explain one subsystem at framework-doc depth.
  Required interactions: TOC anchors, expandable risk notes, tabs for concept,
  flow, config, copyable snippets, next-reading.
- Section: Search overlay.
  Purpose: find any curated content by full text.
  Required interactions: keyboard open/close, typeahead filtering, result
  navigation, empty and zero-result states.
- Section: Diagram blocks.
  Purpose: explain data and decision flow visually.
  Required interactions: expandable steps or tabs where useful; static fallback
  content remains readable.

## Completeness Review

- Primary goals covered: proposed, pending artifact completion.
- Secondary goals covered: proposed, pending artifact completion.
- Necessary content present: pending content inventory and source map.
- Pre-implementation Content Coverage Audit: required before implementation.
- Post-implementation Content Coverage Audit: required after implementation.
- Content and capability coverage proven: pending.
- Discovery/search coverage proven: pending.
- Interaction inventory covered: pending.
- Page/screen wireframes complete: pending.
- Rubric Review complete: pending.
- Messaging trajectory present: proposed in this revision.
- Claims backed by proof or softened: pending content inventory.
- Objections answered where they arise: proposed, pending page contracts.
- Core interactions present: pending implementation.
- Journey endpoints clear: proposed, pending flow/wireframe contracts.
- Placeholder/demo-only surfaces removed or marked out of scope: required.
- Required states covered: pending screen contracts.

## Approval Record

- Product Surface revision: 1
- Decision: pending
- Owner feedback or waiver scope: onboarding answers accepted as input on
  2026-09-03; Product Surface Approval not yet requested until independent
  factual research is returned and verified.
- Date: 2026-09-03
- Next phase unlocked: after approval, Visual Exploration and Design System
  artifact work.

## Collaboration Record

- Delegation available: yes.
- Required collaboration/runtime interface: Orca native subagents.
- Proposed delegated scope: independent factual product research, contract
  review, first-use review, wireframe rendered visual QA, copy review,
  implementation, and final QA as required by D3.
- Owner decision: approved in chat on 2026-09-03.
- Fallback: none required unless Orca launch or worker deliverables fail.

## Independent Contract Review Record

- Frontend Lead Contract Review Brief: Orca task `task_4ab5481eb26a`, run
  `run_87fce7d102ff`, read-only review of Product Surface, Messaging, Design
  Identity, Frontend Context, and onboarding decision.
- Reviewer/session: Orca native `cursor` worker `ctx_211d42ca5202`, model
  `gemini-3.7-flash-high`.
- Contracts reviewed: `docs/frontend/context.md`,
  `docs/frontend/product-surface-model.md`, `docs/frontend/messaging.md`,
  `docs/frontend/design-identity.md`,
  `docs/frontend/decisions/2026-09-03-docs-portal-onboarding.md`.
- Blocking findings and fixes: initial verdict `approve-with-fixes`; blockers
  were route taxonomy mismatch, home-only messaging coverage, unmeasurable
  "huge" content scope, undefined diagram technology, and unclear snippet vs
  source-code quotation boundary. Fixes added canonical route map, page
  messaging contracts, Source Map Matrix, Diagram Contract, and Snippet policy.
- Re-review verdict: `PASS` from Orca native `cursor` worker
  `ctx_8c234d5de26d`; all five blockers closed and Product Surface Approval
  can be presented to the owner.

## Implementation Separation Record

- Design/control session:
- Frontend Implementation Brief:
- Implementation worker/session:
- Allowed production files and units:
- Wireframe Conformance Contract:
- Independent QA worker/session:
- Owner waivers affecting role separation:
