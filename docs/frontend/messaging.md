# Messaging

Status: proposed.
Revision: 1
Approval source: owner Product Surface Approval on 2026-09-02.

Use this file for durable frontend messaging knowledge: public product voice,
page-level text contracts, proof needs, objection maps, microcopy rules, and
copy review findings.

## Messaging Identity

- Directness: high; explain mechanisms plainly and avoid marketing suspense.
- Formality: professional Russian technical documentation with readable,
  human phrasing.
- Technical depth: advanced enough for a developer-crypto trader; assume
  comfort with trading systems, CLI, config, candles, and execution concepts.
- Claim confidence: precise and bounded; no performance promises and no
  unsupported safety claims.
- Emotional intensity: calm, curious, and focused; playful visuals should not
  make the copy unserious.
- Humor: light visual play is allowed through abstract mascots; copy should
  avoid jokes that weaken trust.
- Relationship to the user: expert guide for a peer who wants to understand
  the framework quickly.
- Natural phrases: "как устроено", "поток данных", "жизненный цикл",
  "граница ответственности", "источник истины", "без look-ahead bias",
  "следующий раздел".
- Foreign phrases: hype language, profit promises, dashboard/live-monitoring
  language, and vague generic SaaS copy.
- Owner preference signals: Russian language, framework-docs style, curated
  pages in source, no raw code quotation, no runtime results, playful lo-fi
  pastel style.
- Private owner language not suitable for public copy: casual chat shorthand
  should be translated into clear product documentation.
- Evidence: owner onboarding answers on 2026-09-02 and project README/current
  state docs.

## Messaging Contract

- Page or screen: full `crypt docs` portal.
- Why it exists: explain how the codebase works as a crypto strategy research
  and live execution framework without forcing the reader through raw source or
  historical Markdown.
- Audience: developer-crypto trader.
- Starting user state: needs a trustworthy mental model, subsystem map, and
  quick answers.
- Intended leaving state: knows the core flows, can navigate architecture and
  learning paths, and understands live-money boundaries.
- Main idea: curated framework documentation for `crypt`, not a runtime
  dashboard and not a Markdown mirror.
- First messages: what `crypt` is, who the docs are for, what is intentionally
  excluded, and where to start.
- Later messages: subsystem details, diagrams, configuration hierarchy,
  command examples, operational guarantees, risks, and glossary definitions.
- Objections to answer: whether the portal is current, why results are absent,
  what prevents look-ahead bias, how live execution is bounded, and how to find
  a specific concept.
- Required proof: page sources, diagrams, status labels, command snippets, and
  cross-links.
- Natural action: start guided reading, search, or open a subsystem reference.
- Generic-copy risks: "powerful platform", "unlock insights", "seamless
  trading", and any performance-oriented language.

## Message Trajectory

- Starting state: the reader sees a complex trading research/execution repo.
- Problem or tension: the system spans research, backtesting, strategies, data,
  operations, and live OKX execution; raw source alone is slow to learn.
- Product explanation: `crypt docs` presents the system as a framework with
  curated conceptual pages.
- Mechanism: guided path, architecture reference, full-content search,
  diagrams, CLI snippets, glossary, and next-reading links.
- Proof: each page is grounded in named repository docs or code areas and
  avoids showing runtime results.
- Objection handling: risk badges and explanatory notes mark live money,
  OKX execution, config, no-look-ahead, operational, research, stable, and
  archived topics.
- Action: choose guided start or search a concept.

## Text Hierarchy

- Level 1 main promise: "crypt docs" explains the framework model behind the
  research workbench and live execution code.
- Level 2 section arguments: each major page explains one subsystem, why it
  exists, how it connects, and what risk boundary applies.
- Level 3 supporting copy: concise mechanism explanations, diagrams, examples,
  config notes, and source references.
- Level 4 action copy: "Начать маршрут", "Открыть архитектуру", "Скопировать
  команду", "Искать по документации", "Следующий раздел".
- Level 5 microcopy: status labels, risk labels, empty-search guidance,
  command-copy confirmation, theme toggle names, and diagram state labels.

## Proof System

- Claim: the portal explains how `crypt` works.
- Required proof: all named first-release sections exist with curated content,
  diagrams, search coverage, and next-reading links.
- Available proof: repository documentation corpus and owner-approved scope.
- Missing proof: implemented pages and rendered QA.
- Decision: add proof during page contracts and implementation.

- Claim: the portal does not display runtime results.
- Required proof: page contracts and implementation must exclude live balances,
  positions, current PnL, and command output result tables.
- Available proof: owner explicitly excluded results on 2026-09-02.
- Missing proof: implementation audit.
- Decision: add proof.

## Objection Map

- Objection: "Is this a dashboard?"
- Where it arises: home and live execution pages.
- Response: clarify that the portal documents architecture and operations, not
  current runtime state.
- Placement: first viewport and Live Execution scope note.
- Evidence: owner answer on 2026-09-02.

- Objection: "Can I trust backtest/live explanations?"
- Where it arises: Backtester, Live Execution, Data Pipeline.
- Response: explain closed-candle/no-look-ahead boundaries and exchange truth
  boundaries without promising performance.
- Placement: risk/status callouts near relevant mechanisms.
- Evidence: `AGENTS.md`, `docs/state/current.yml`, `README.md`.

## Microcopy Rules

- Buttons and links: use concrete Russian action labels that name the result.
- Navigation labels: keep subsystem names stable and scannable.
- Forms: search input uses clear placeholder text and keyboard hint.
- Loading states: explain what is being searched or opened when visible.
- Empty states: suggest top-level docs areas and glossary terms.
- Error states: explain missing local content or unavailable search index
  without implying runtime failure.
- Success states: command copy confirmation names what was copied.
- Confirmations: no destructive or live-money confirmations in scope.
- Tooltips and badges: define maturity and risk labels briefly.

## Text Inventory

Every user-visible text fragment must be inventoried for D2/D3 work and for
any implementation that changes copy. Do not sample only important text.

- Page / screen / state:
- Location / component:
- Exact text or repeated text pattern:
- Text category:
- Semantic job:
- Messaging Contract link:
- User starting state:
- Intended leaving state or local action:
- Claim made:
- Proof nearby:
- Objection or friction handled:
- Action expectation:
- Microcopy state:
- Keep / rewrite / cut decision:
- Reviewer verdict:
- Evidence:

## Copy Review

- Scope reviewed:
- Text Inventory coverage:
- Pages/screens/states covered:
- Navigation/action/microcopy covered:
- Clarity:
- Specificity:
- Information depth:
- Messaging Identity fit:
- Claim/proof fit:
- Objection coverage:
- Action-copy strength:
- Microcopy usefulness:
- Scannability:
- Density:
- Coverage gaps:
- Slop risks:
- Decision:
- Date:
