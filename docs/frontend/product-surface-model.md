# Product Surface Model

Status: draft, awaiting owner confirmation.

Use this file for durable frontend product-surface understanding. It should be
filled before substantial new site/app work, major redesigns, or broad product
surfaces.

Do not ask the owner to repeat product information that already exists in the
repository. First discover product knowledge from sources such as `README.md`,
project docs, requirements, specs, current state, task context, or a canonical
`product.md`/`PRODUCT.md` when present.

## Product Knowledge Sources

- Primary: `README.md`, `docs/state/current.yml`, owner frontend brief in chat
  on 2026-08-27.
- Supporting: `docs/architecture.md`, `docs/strategy_benchmark.card.md`,
  `docs/backtester_regression.card.md`, `docs/execution/live_execution.card.md`.
- Contradictions or gaps: the repository previously had no active frontend
  surface. The first screen priority is confirmed as a short intro followed by
  fast documentation entry. Detailed page-level content extraction and final
  visual system remain unconfirmed.

## User Capabilities And Goals

- Primary goals:
  - Let a public technical audience understand what `crypt` is and how the
    workbench is structured.
  - Make the repository's important docs discoverable without requiring readers
    to know the internal documentation map.
  - Explain the relationship between research, backtesting, live execution,
    benchmark policy, and archived strategy candidates.
- Secondary goals:
  - Give crypto developers enough context to evaluate the system boundaries and
    reproducibility posture.
  - Surface safety constraints: closed-candle logic, no look-ahead bias,
    exchange truth for live money, and runtime config as the live source of
    truth.

## Required Content And Features

- In scope:
  - Public documentation site for developers and crypto-native readers.
  - Local-only initial implementation.
  - Next.js, Tailwind CSS, pnpm, oxlint, oxfmt, and Ultracite as requested
    stack/tooling.
  - First version focused on curated documentation navigation and product
    explanation, not live account controls.
  - Public live execution overview that explains the active execution module
    without exposing secrets or private operational state.
  - Production-grade documentation site, not an MVP placeholder.
  - Real documentation content sourced from repository markdown, not only
    high-level summaries.
  - Live execution runtime flow coverage: sync, orders, state, Telegram, and
    Railway/deployment context where public-safe.
  - Manual documentation information architecture, not automatic publication of
    every file under `docs/`.
  - Full-text search in the first production version.
  - Search implementation may use the simplest reliable local approach selected
    during implementation.
  - Sidebar navigation inside documentation sections.
  - Setup, API, and CLI pages as first-class documentation sections even when
    they are not top-level navigation items.
  - Documentation content copied or transformed into the frontend content
    structure instead of rendering directly from arbitrary repository markdown
    paths.
  - Syntax highlighting for code and shell command blocks.
  - Web-native visual diagrams for architecture and live runtime flow.
  - English-only public site content.
  - Site UI name: `crypt`.
  - A primary lo-fi/cartoon hero illustration on the home page.
  - Public research archive coverage for curated candidates and routers.
  - Warning/safety callouts on live execution and backtester pages for runtime
    truth, no look-ahead bias, exchange truth, and related correctness rules.
- Explicitly out of scope:
  - Public deployment.
  - Authentication.
  - Live trading controls.
  - Mutation of OKX, Telegram, Railway, GitHub, or ticket state.
  - Exposing secrets, account balances, private runtime configuration, or
    unpublished live-money details.
  - Public changelog and task documents, including `CHANGELOG.md`,
    `CHANGELOG_ARCHIVE.md`, and `docs/tasks/*`.

## User Journeys

- Journey: a developer lands on the site, understands the project shape, then
  opens the right docs for architecture, setup, backtesting, live execution, or
  strategy research.
- Endpoint: reader can navigate to the relevant canonical repository docs and
  knows which areas are historical, active, safety-critical, or benchmark-only.
- Journey: a crypto-native evaluator scans benchmark and live-execution
  framing before deciding whether the project is relevant.
- Endpoint: reader understands that benchmark results are reporting targets,
  live runtime config is authoritative, and strategy promotion is owner-led.

## Information Architecture

- Pages or screens:
  - Home / overview.
  - Docs map.
  - Research and strategy archive overview.
  - Backtester and reproducibility overview.
  - Live execution overview.
  - Architecture overview.
  - Setup / local run commands.
  - CLI reference.
  - API/internal contracts reference where source documentation supports it.
- Navigation model:
  - Documentation-first top navigation with confirmed primary items: Docs,
    Architecture, Research, Backtester.
  - Home page should start with a short intro, then optimize for fast entry into
    the documentation.
  - Deep pages should link back to canonical markdown sources where details
    already live.
  - Separate routes are preferred over a single long page.
  - Documentation routes use a sidebar for section-level navigation.
  - Top navigation remains curated and does not expose internal task/changelog
    history.

## Sections And Components

- Section: project orientation.
  - Purpose: establish `crypt` as a research workbench plus live OKX execution
    module.
  - Required interactions: links to README, architecture, benchmark, and setup.
- Section: documentation routes.
  - Purpose: group docs by task: research, backtester regression, live
    execution, architecture, agent/development context.
  - Required interactions: cards or rows linking to canonical docs.
- Section: system model.
  - Purpose: show the flow from config/data through decisions, backtests, and
    live execution.
  - Required interactions: readable diagram or structured list.
- Section: safety and truth hierarchy.
  - Purpose: prevent readers from mistaking prose docs for runtime truth.
  - Required interactions: none beyond links to live execution docs.
- Section: commands.
  - Purpose: present setup and smoke commands without hunting through README.
  - Required interactions: copyable command blocks if supported in the initial
    scope.
- Section: source-backed document pages.
  - Purpose: render actual repository markdown content in a reader-friendly web
    docs surface.
  - Required interactions: page navigation, sidebar, full-text search, in-page
    table of contents where useful, source links, and readable code blocks.
- Section: visual diagrams.
  - Purpose: explain architecture, research workflow, backtester parity, and
    live runtime flow through web-native diagrams.
  - Required interactions: responsive diagrams with readable labels and links to
    relevant docs where useful.

## Completeness Review

- Primary goals covered: draft.
- Secondary goals covered: draft.
- Necessary content present: incomplete until owner confirms first-screen
  priority and visual direction.
- Core interactions present: planned; not implemented.
- Journey endpoints clear: draft.
- Placeholder/demo-only surfaces removed or marked out of scope: required for
  implementation.
- Required states covered: not applicable for static documentation v1 except
  responsive navigation and link states.
