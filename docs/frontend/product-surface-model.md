# Product Surface Model

Status: approved.
Revision: 1.
Approval: approved by owner on 2026-09-01.
Updated: 2026-09-01.

## Task Contract

- Outcome: a public Russian-language documentation portal that teaches an
  experienced Python developer and crypto trader how `crypt` is structured,
  installed, configured, researched with, backtested, dry-run, and operated.
- Scope: a curated Next.js and Tailwind CSS site with deep authored pages,
  local full-text search, responsive navigation, branded diagrams, code-copy
  controls, configuration tabs, expandable explanations, and a dark pastel
  lo-fi visual identity.
- Sources of truth: current `src/crypt/` and `src/backtester/` behavior,
  `pyproject.toml`, `docs/cli.md`, engine and execution contracts, current
  runtime configuration, and owner decisions recorded on 2026-09-01.
- Constraints: Russian-only public copy; no direct Markdown rendering; no
  performance results or strategy promotion; no authenticated or mutating
  product surface; main branch only; desktop and mobile have equal priority.
- Acceptance evidence: every approved page has a screen contract and rendered
  wireframes; all promised content maps to a canonical source; search finds
  representative concepts and commands; the quick-start journey ends in a
  safe dry-run; all interactions and six viewport classes receive independent
  rendered QA.
- Unknowns: none that block Product Surface Approval. Exact wording and visual
  treatment remain subject to later messaging, visual, and wireframe gates.

## Product Knowledge Sources

- Primary: `src/crypt/`, `src/backtester/`, `pyproject.toml`, `docs/cli.md`,
  `docs/backfill.md`, `docs/backtest.md`, `docs/execution/live_execution.md`,
  and `docs/deploy/railway.md`.
- Supporting: `README.md`, `docs/state/current.yml`, engine specifications,
  strategy-discovery specifications, execution ADRs, tests, and `.env.example`.
- Contradictions or gaps: `docs/architecture.md` retains a historical
  signal-only overview and an execution stub, while current code includes the
  live execution manager, OKX synchronization and recovery, persistent state,
  H1 websocket scheduling, and execution safety controls. The portal must use
  current code and specialized execution documents for this area.

## Scope Contract

- In scope: current-framework concepts, installation, data preparation,
  authored strategy configuration, backtesting, optimization and signal
  discovery concepts, dry-run, detailed live execution, CLI, configuration,
  development, testing, troubleshooting, and safety boundaries.
- Explicitly out of scope: strategy returns, rankings, benchmark verdicts,
  account balances, active production performance, candidate promotion,
  historical project chronology, repository Markdown rendering, trading UI,
  account authentication, order controls, and documentation version switching.
- Assumptions: the reader already understands Python development, perpetual
  futures, leverage, orders, risk, and common quantitative-trading vocabulary.
- Unresolved decisions: none at product-surface level.

## Users And Goals

- Primary user: a developer who is also an experienced crypto trader.
- Primary goal: understand the system well enough to install it, prepare data,
  run an existing strategy through the backtester, inspect the artifact types,
  and complete an execution-only dry-run safely.
- Secondary goals: locate exact CLI/configuration details, understand module
  and trust boundaries, extend or test the framework, and diagnose failures.

## Information Architecture

Global navigation uses a classic documentation shell: persistent section
sidebar, central article, contextual table of contents, top search, and mobile
drawers that preserve the same information architecture.

| Page | Route | User outcome | Canonical source boundary |
| --- | --- | --- | --- |
| Home | `/` | Start the quick-start path immediately and understand the portal scope | README, current state, owner scope |
| Quick start | `/docs/quick-start` | Install dependencies, prepare safe configuration, run a bounded backtest, then dry-run | README, CLI, `.env.example`, runtime entrypoint |
| What is crypt | `/docs/overview` | Understand research workbench, backtester, and live execution boundaries | README, current state, source tree |
| Architecture | `/docs/architecture` | Follow data from OKX/Parquet through strategy decisions to artifacts or execution | current code, specialized architecture/execution docs |
| Data | `/docs/data` | Understand sources, closed-candle rules, Parquet layout, backfill, missing-data behavior | data layer, backfill contract, data contracts |
| Strategies | `/docs/strategies` | Understand strategy configs, registry, signals, execution context, and extension seams | strategy loader/registry, strategy specs |
| Backtester | `/docs/backtester` | Run exact replay, understand warmup/accounting boundaries and output artifact types | backtester code, CLI, regression contract |
| Research and optimization | `/docs/research` | Understand optimize and DSS workflows without publishing candidate results | CLI, discovery contracts, optimizer/search code |
| Live execution | `/docs/live-execution` | Understand dry-run/live modes, H1 scheduling, OKX truth, reconciliation, safety and recovery | runtime/execution code, live execution docs |
| CLI reference | `/docs/cli` | Find supported owner-facing commands, flags, defaults, and examples | `docs/cli.md`, actual command parsers |
| Configuration | `/docs/configuration` | Configure application, data, execution, credentials, paths, risk and deployment safely | settings classes, `.env.example`, Railway config |
| Development and testing | `/docs/development` | Navigate modules and run supported lint, type and test checks | pyproject, source tree, operating rules where public-safe |
| Troubleshooting | `/docs/troubleshooting` | Recover from missing data, configuration, sync, runtime and deployment failures | runbooks, explicit failure behavior, tests |

The first release includes every page above. Deep pages may use in-page
chapters, but their promised content may not be replaced with placeholder
cards or links back to repository Markdown.

## Primary Journey

1. The reader lands on Home and chooses `Начать быстрый старт`.
2. Quick start verifies prerequisites and installs with `uv`.
3. The reader prepares public data and environment configuration.
4. The reader runs a bounded existing-strategy backtest.
5. The page explains the generated artifact types without presenting project
   performance results.
6. The reader enables execution in dry-run mode with explicit fake sizing
   capital and `--execution-only --once`.
7. The portal confirms what was and was not mutated, then links to detailed
   live-execution safety and deployment material.
- Recovery: missing candles lead to a concrete backfill command; missing or
  unsafe execution configuration leads to an explicit blocked state.
- Endpoint: the reader has completed a non-ordering dry-run and understands
  the boundary before live money.

## Content And Capability Contract

- Source corpus: the primary and supporting repository sources named above,
  curated into original Russian documentation pages.
- Promised coverage: all 13 pages, the complete primary journey, supported CLI
  surface, important configuration groups, architecture boundaries, data and
  error states, safe dry-run, live execution model, and developer validation.
- Required depth: every article includes purpose, mental model, relevant
  diagram, runnable or illustrative examples, important constraints, failure
  behavior, and clear next/related pages. Reference pages additionally include
  complete supported command or configuration group coverage.
- Boundaries requiring approval: narrowing or removing any listed page,
  replacing deep content with summaries, externalizing required content to raw
  repository files, or introducing performance results.
- Source-of-truth proof: each authored page carries an internal source manifest
  linking its facts to current code or canonical docs; manifests are used for
  maintenance and are not presented as raw docs rendering.
- Freshness: documentation tracks current main only. A source change affecting
  commands, settings, architecture, or user journeys requires the relevant
  curated page and search index to change in the same work.
- Measurable evidence: a page/source coverage matrix, command/config inventory,
  pre/post content audit, text inventory, and independent QA review.

## Discovery Contract

- Discovery surfaces: global search, section sidebar, article table of
  contents, previous/next links, related-page links, and Home/Quick-start cards.
- Corpus: all authored page titles, descriptions, headings, body text, code
  samples, command names, configuration keys, aliases, and character guidance.
- Indexed fields: title and headings receive strongest weight; command/config
  exact matches rank above prose; body text and aliases provide recall.
- Results: grouped by documentation section with title, breadcrumb, matched
  excerpt, and matched command or setting when applicable.
- Empty query: recently or commonly useful destinations without pretending to
  know personal history. Zero results: preserve the query, explain that no
  page matched, and offer CLI, Configuration, and Troubleshooting destinations.
- Keyboard: `/` and `Ctrl/Cmd+K` open search; arrows move results; Enter opens;
  Escape closes and restores focus.
- Representative queries: `dry run`, `EXECUTION_DRY_RUN`, `backfill`,
  `search-signals-matrix`, `Parquet`, `закрытые свечи`, `синхронизация OKX`,
  `Railway`, `pytest`, and `нет свечей`.
- Coverage evidence: every representative query must return the intended page
  in the first result group and support keyboard-only selection.

## Messaging Requirements

- Starting state: an experienced technical reader sees a large research/live
  codebase but lacks a reliable entry path and system-level mental model.
- Intended leaving state: the reader knows where to begin, how components fit,
  how to run the safe workflow, and where the live-money boundary begins.
- Main idea: `crypt` is a coherent research-to-execution workbench whose data,
  decision, replay, and live boundaries can be inspected and operated.
- Proof: real module names, commands, configuration keys, data layouts,
  failure behavior, and diagrams derived from current code.
- Objections: “это просто бот”, “бэктест и live расходятся”, “непонятно, какие
  данные нужны”, “dry-run может отправить ордер”, and “документация устарела”.
- Natural action: follow Quick start, then deepen understanding through the
  page related to the reader's current task.
- Generic-copy risk: framework slogans, trading hype, unsupported safety
  claims, unexplained cute illustrations, and vague feature-card language.

## Interaction And State Requirements

- Search dialog: idle, typing, results, zero-result, keyboard selection, closed.
- Code blocks: copy idle, copied confirmation, copy failure, horizontal
  overflow without page overflow.
- Configuration tabs: selected/unselected, keyboard traversal, preserved
  readable fallback.
- Expandable explanations: collapsed/expanded with visible focus and correct
  semantics.
- Navigation: active page, active heading, mobile open/closed, previous/next,
  direct URL anchors, browser back/forward.
- Content: normal plus explicit unavailable-source or stale-contract build
  failure; the production site does not silently publish partial pages.

## Pre-implementation Content Coverage Audit

| Promise | Included before implementation | Evidence source |
| --- | --- | --- |
| Installation and first run | setup, prerequisites, safe env preparation | README, pyproject, `.env.example` |
| Complete learning path | install through execution-only dry-run | CLI and runtime entrypoint |
| System architecture | research, data, backtester, runtime, execution | current source modules |
| Data preparation | Parquet layout, backfill, missing-data behavior | backfill/data contracts |
| Strategy use | configs, registry, context, extension seams | backtester strategy code |
| Backtesting | supported run, boundaries, artifact types | CLI, backtester regression |
| Research workflows | optimize and DSS mechanics, no results | CLI and discovery code/docs |
| Live operation | modes, sync, recovery, scheduling, Railway | execution/runtime code and runbooks |
| Reference | commands, settings, checks, troubleshooting | parsers, settings, pyproject, runbooks |
| Discovery | local full-text search and complete navigation | owner decision and Discovery Contract |

## Completeness Review

- Primary goals covered: approved for revision 1.
- Secondary goals covered: approved for revision 1.
- Necessary content present: contracted; implementation not started.
- Pre-implementation Content Coverage Audit: complete for revision 1.
- Post-implementation Content Coverage Audit: pending implementation.
- Content and capability coverage proven: pending implementation.
- Discovery/search coverage proven: pending implementation.
- Interaction inventory covered: contract established; execution pending.
- Page/screen wireframes complete: pending.
- Rubric Review complete: pending artifact-phase review.
- Messaging trajectory present: yes, proposed.
- Claims backed by proof or softened: source boundaries recorded.
- Objections answered where they arise: contracted.
- Core interactions present: contracted; implementation pending.
- Journey endpoints clear: yes.
- Placeholder/demo-only surfaces removed or marked out of scope: required.
- Required states covered: contracted.

## Approval Record

- Product Surface revision: 1.
- Decision: approved.
- Owner feedback or waiver scope: owner replied `да` to the named Product
  Surface revision 1 approval gate; no waiver granted.
- Date: 2026-09-01.
- Next phase unlocked: Preliminary Identity and five rendered Visual Direction
  Boards, followed by Visual Direction Approval.

## Collaboration Record

- Delegation available: available through Orca CLI.
- Required collaboration/runtime interface: Orca CLI with `Cursor Grok 4.6 High Fast`.
- Proposed delegated scope: read-only product knowledge and source audit.
- Owner decision: declined; current-session work requested.
- Fallback: completed by the current session and verified against repository sources.
