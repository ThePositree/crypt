# Product Surface Model

Status: proposed.
Revision: 1.
Approval: requested.

## Product Knowledge Sources

- Primary: `AGENTS.md`, `README.md`, `docs/state/current.yml`, and owner input
  collected during the 2026-08-30 frontend onboarding.
- Supporting: `docs/execution/live_execution.md`,
  `docs/backtester_regression.md`, `docs/strategy_benchmark.md`,
  `docs/discovery/direct_signal_search_v3.md`, `strategies/README.md`, and the
  active Python package structure under `src/crypt/` and `src/backtester/`.
- Contradictions or gaps: `docs/architecture.md` describes historical surfaces
  and must not be treated as the current product-level source without a
  separate correction. The frontend framework, deployment target, and content
  authoring pipeline are not selected yet.

## Scope Contract

- Outcome: a public, self-contained English documentation portal that makes
  the architecture and behavior of `crypt` understandable without requiring
  repository access.
- In scope: plain-language explanations, pseudocode, architecture diagrams,
  styled but numerically honest result charts, working research/backtest CLI
  examples, glossary, global search, light and dark themes, responsive mobile
  and desktop layouts, and a separate historical Telegram MVP section.
- Explicitly out of scope: trading controls, account access, strategy or
  deployment management, exchange mutations, live operator commands, secrets,
  environment configuration, and any claim of guaranteed returns.
- Assumptions: the first release is documentation rather than an operational
  dashboard; source facts are curated into the portal instead of fetched from
  a public repository at visit time.
- Unresolved decisions: exact production facts safe to publish, framework and
  hosting, content update workflow, named mascot details, and the exact set of
  CLI examples. These do not change the proposed product surface.

## User Capabilities And Goals

- Primary audience: public visitors, including readers without a software or
  quantitative-finance background.
- Primary goal: understand what `crypt` is and how market data moves through
  research, strategy decisions, backtesting, and live execution code.
- Secondary goals: learn core terminology; inspect accurate historical
  evidence; follow working research/backtest examples; browse sequentially as
  a course or retrieve one answer through navigation and search.

## Required Content And Features

### In scope

- A plain-language project introduction and explicit statement of what the
  portal cannot do.
- A visual end-to-end architecture narrative.
- Explanations of research, backtesting, strategy composition, and live
  execution behavior.
- Honest presentation of the owner-selected production configuration and
  historical results with dates, methodology, and non-guarantee context.
- A separate history narrative for the Telegram signal MVP.
- Pseudocode instead of source-code-first teaching.
- Working, copyable research and backtest CLI examples.
- Search, glossary, next/previous learning navigation, theme selection, and
  reduced-motion support.
- A recurring named human researcher mascot and optional lightweight playful
  interactions that do not hide documentation.

### Explicitly out of scope

- Authentication, user accounts, portfolio dashboards, current balance or
  position monitoring, trading or exchange controls, and strategy editors.
- Live startup, deployment, Railway, secret-management, or destructive CLI
  instructions.
- GitHub dependency for core reading, source browsing, or asset delivery.
- Gamification that gates required information or makes technical evidence
  less legible.

## User Journeys

### Guided first visit

- Actor and starting state: a public visitor with no prior `crypt` context
  lands on the home page.
- Goal: form a correct mental model of the product.
- Steps and decisions: read the plain-language introduction, inspect the
  simplified system map, choose a guided starting point, and continue through
  Architecture or Research.
- Error or recovery path: unfamiliar terms open short definitions and link to
  the glossary; every deep page offers a route back to the overview.
- Endpoint and feedback: the visitor can explain that `crypt` is a Python
  research workbench with a separate owner-selected OKX execution path and
  that the portal is explanatory only.

### Learn the system sequentially

- Actor and starting state: a curious reader starts from Overview.
- Goal: understand the system from data to decision to simulated or live
  execution.
- Steps and decisions: Overview -> Architecture -> Research -> Strategies ->
  Execution -> Concepts, using next/previous navigation and diagrams.
- Error or recovery path: glossary definitions and progressive disclosure keep
  domain detail from blocking the main narrative.
- Endpoint and feedback: the reader reaches a recap diagram and can revisit
  any stage independently.

### Find one answer

- Actor and starting state: a returning visitor has a specific term, module,
  or workflow in mind.
- Goal: reach the relevant explanation quickly.
- Steps and decisions: use global search or section navigation, open a result,
  and follow local cross-links.
- Error or recovery path: zero-result search suggests glossary terms and the
  top-level system map.
- Endpoint and feedback: the relevant explanation is visible with its scope,
  source date, and related concepts.

### Run a safe example

- Actor and starting state: a reader wants to reproduce a research or backtest
  workflow locally.
- Goal: understand and copy an example without entering the live-money path.
- Steps and decisions: select an example, read prerequisites and expected
  output, copy the command, and inspect an annotated result.
- Error or recovery path: common missing-data and configuration failures are
  explained explicitly.
- Endpoint and feedback: the reader understands what the command does and how
  to interpret its output; live execution commands are absent.

## Information Architecture

### Pages or screens

1. **Overview** — what `crypt` is, what it is not, the two main code surfaces,
   a simple system map, and guided entry points.
2. **Architecture** — market data, closed-candle decisions, shared pure logic,
   backtest/live branching, failure behavior, and an animated end-to-end
   diagram.
3. **Research & Backtesting** — data preparation, causal feature rules,
   discovery, deterministic backtests, benchmarks, validation, results, and
   safe CLI examples.
4. **Strategies** — strategy contracts, JSON configuration, registry and
   composition, owner-selected production promotion, pseudocode, and evidence
   boundaries.
5. **Live Execution** — signal runner, risk, synchronization, executor,
   protection and recovery behavior, presented as documentation with a
   persistent no-controls message.
6. **Concepts** — searchable glossary for domain and project terminology,
   including closed candles, donor, DSS, parity, risk base, SL, TP, and TTL.
7. **History** — the old Telegram signal MVP and historical M1 pipeline,
   explicitly separated from the current product architecture.
8. **Search** — global search results with section, content type, and glossary
   context.

### Navigation model

- Primary navigation: Overview, Architecture, Research, Strategies,
  Execution, Concepts, History.
- Global utilities: search, light/dark theme selection, and reduced-motion
  behavior inherited from the operating system.
- Learning navigation: recommended path plus previous/next links.
- Retrieval navigation: search, local table of contents, glossary popovers,
  and contextual cross-links.

## Sections And Components

- Site header: product identity, primary navigation, global search, and theme
  control.
- Hero laboratory: plain-language promise, human researcher mascot, immediate
  crypto cues, and one guided-learning action.
- System map: animated but reduced-motion-safe data flow with progressively
  disclosed detail.
- Explanation chapter: concise prose, pseudocode, diagrams, terminology, and
  links to prerequisites and next concepts.
- Evidence panel: dated configuration or result, methodology, limitations, and
  source-of-truth label.
- CLI example: prerequisites, copyable research/backtest command, expected
  result, and safe failure guidance.
- Styled chart: exact values, readable axes and labels, methodology context,
  accessible summary, and pastel lo-fi presentation.
- Mascot note: optional contextual guidance that never gates or replaces core
  content.
- Search overlay and results: keyboard-accessible query, recent or suggested
  concepts, results, empty state, and clear close behavior.
- Site footer: portal scope, update date, historical-performance disclaimer,
  and navigation.

## Required States

- Search: closed, open, typing, results, no results, keyboard selection, and
  unavailable index.
- Content: normal, missing optional illustration, stale evidence warning, and
  unknown or unavailable operational data.
- Diagrams and charts: loading where generated, rendered, accessible text
  fallback, narrow viewport, and reduced motion.
- CLI examples: default, copied, prerequisites missing, expected failure, and
  command deprecated.
- Navigation: current section, expanded mobile menu, keyboard focus, and deep
  link to an anchored section.
- Themes: light, dark, system-derived first visit, persisted visitor choice,
  and sufficient contrast in both themes.

## Completeness Review

- Primary goals covered: yes, by Overview and the guided architecture journey.
- Secondary goals covered: yes, by search, Concepts, evidence panels, History,
  and CLI examples.
- Necessary content present: specified; content inventory remains an
  implementation-phase artifact.
- Core interactions present: specified; no operational mutations exist.
- Journey endpoints clear: yes.
- Placeholder/demo-only surfaces removed or marked out of scope: required
  before public launch.
- Required states covered: specified above; exact screen contracts remain to
  be written after Product Surface Approval.

## Uncertainty Check

- Product scope: sufficiently resolved for Product Surface Approval.
- Stack: unresolved; select after surface approval.
- Data and API: no runtime API is required for the approved documentation MVP;
  content sourcing and search indexing remain to be selected.
- Auth and permissions: no authentication or privileged visitor actions.
- Content: section model is resolved; exact publishable production details and
  CLI inventory remain to be curated.
- Visual direction: preliminary lo-fi pastel laboratory direction is resolved;
  five rendered direction boards are still required.
- Interaction and states: core journeys and required states are resolved;
  wireframes remain to be designed.
- Accessibility and responsive behavior: equal mobile/desktop quality, exact
  chart readability, keyboard access, light/dark contrast, and
  `prefers-reduced-motion` support are required.
- Success criteria: visual identity, architectural clarity, scoped content
  completeness, and public-launch readiness must all pass.

## Verdict

- Resolved evidence: public audience, English content, self-contained portal,
  plain-language teaching, pseudocode, visible crypto imagery, named human
  mascot, light and dark pastel lo-fi laboratory themes, moderate density,
  global search, diagrams, accurate styled charts, safe CLI examples, and
  separate History.
- Remaining material unknowns: none that change the proposed product surface.
- Next phase: Product Surface Approval, followed by preliminary visual identity
  and five rendered Visual Direction Boards.
- Required owner gate: approve, reject, or revise Product Surface Model
  revision 1.

## Approval Record

- Product Surface revision: 1
- Decision: pending
- Owner feedback or waiver scope: none yet
- Date: 2026-08-30
- Next phase unlocked: five rendered Visual Direction Boards and visual
  direction approval.

## Collaboration Record

- Subagent system available: yes, with a launcher integration limitation.
- Required interface/provider/model: Orca CLI orchestration with Cursor Grok
  4.6 High Fast.
- Proposed delegated scope: read-only independent MVP information architecture
  review.
- Owner decision: pending / approved / declined (selected: approved on
  2026-08-30).
- Result: the read-only analysis completed and informed revision 1; Orca
  rejected the lifecycle completion after Cursor approval UI caused the
  dispatch capability to expire. No files were modified by the worker.
- Fallback: coordinator verified and integrated the findings from the preserved
  terminal report.
