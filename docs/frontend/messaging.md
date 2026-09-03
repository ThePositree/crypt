# Messaging

Status: proposed.
Revision: 1
Approval source: pending Product Surface and later Text Inventory approval.

Use this file for durable frontend messaging knowledge: public product voice,
page-level text contracts, proof needs, objection maps, microcopy rules, and
copy review findings.

## Messaging Identity

- Directness: direct, practical, and explicit about risks.
- Formality: professional but not corporate; Russian interface language with
  English technical terms where they are canonical (`Backtester`, `DSS`,
  `Live Execution`, `OKX`, `CLI`).
- Technical depth: high-level framework documentation down to subsystem
  contracts and key concepts, without quoting source code bodies.
- Claim confidence: confident about documented architecture and code contracts;
  cautious around live runtime state, strategy quality, exchange availability,
  and profitability.
- Emotional intensity: calm and useful, with playful lo-fi visual support but
  serious wording around money and execution.
- Humor: light visual personality is allowed through abstract mascots; risky
  operational text stays plain.
- Relationship to the user: peer documentation for a developer-crypto trader.
- Natural phrases: "как устроено", "источник правды", "путь данных", "контракт
  исполнения", "что читать дальше", "зрелость раздела", "риск live money".
- Foreign phrases: generic "next-gen trading platform", unsupported profit
  claims, hype around AI, and vague "simple powerful tools".
- Owner preference signals: Russian portal, framework-doc style, huge curated
  content in source, playful lo-fi, no code quotations, no execution results.
- Private owner language not suitable for public copy: raw chat shorthand such
  as "делаем сайт" should become explicit product language.
- Evidence: owner onboarding answers from 2026-09-03; `README.md`;
  `docs/state/current.yml`; `docs/strategy_benchmark.md`;
  `docs/execution/live_execution.md`.

## Messaging Contract

- Page or screen: portal home / Start Here.
- Why it exists: orient a developer-crypto trader to `crypt` and route them
  into guided learning or reference lookup.
- Audience: developer-crypto trader.
- Starting user state: understands trading systems but not this repository.
- Intended leaving state: knows the framework shape, key safety boundaries,
  and the next page/search path to use.
- Main idea: `crypt` connects research, backtesting, archived strategy
  evidence, and live OKX execution through shared strategy/execution contracts.
- First messages: what `crypt` is; why it exists; guided path and reference
  path; live-money/source-of-truth warning.
- Later messages: subsystem map, data/decision flow, maturity statuses,
  recommended reading, glossary/search entry.
- Objections to answer: "is this a bot?", "does the portal show production
  state?", "can I trade from here?", "where is the real runtime truth?".
- Required proof: subsystem map, links to canonical docs, diagrams, maturity
  labels, and CLI snippets.
- Natural action: start guided reading, open a reference page, or search.
- Generic-copy risks: inflated product claims and vague framework positioning.

## Page Messaging Contracts

| Route | Starting user state | Intended leaving state | Main idea | Required proof | Natural action |
| --- | --- | --- | --- | --- | --- |
| `/docs/overview` | User needs project framing. | User understands current product shape and historical boundaries. | `crypt` is research workbench plus live OKX execution, not only a signal bot. | `README.md`, `docs/state/current.yml`. | Open Architecture or Data Pipeline. |
| `/docs/architecture` | User wants the framework map. | User knows the two code contours and which docs govern active vs historical behavior. | `src/backtester` researches and replays; `src/crypt` handles runtime data and live execution. | Module map and source caveat. | Open Data Pipeline or Backtester. |
| `/docs/data-pipeline` | User needs to know where market data comes from. | User understands OKX fetches, Parquet storage, timeframes, preflight, and closed-candle rules. | Data availability and candle closure are explicit contracts, not assumptions. | Data modules, CLI backfill, no-lookahead notes. | Open Backtester or Risk Boundaries. |
| `/docs/backtester` | User wants replay mechanics. | User knows how historical candles become simulated trades and regression evidence. | Backtester is the honest replay path for strategy evidence and parity checks. | Regression runbook, execution sim concepts, risk/margin/fee model references. | Open DSS v3, Optuna, or CLI. |
| `/docs/backtester/dss-v3` | User wants to discover strategy candidates. | User understands directional search, trigger/filter instances, timeframe alignment, and downstream limits. | DSS v3 finds directional candidates; it does not finish money geometry. | DSS v3 contract and strategy discovery modules. | Open Optuna Geometry or Strategies. |
| `/docs/backtester/optuna-geometry` | User has a candidate and needs money parameters. | User understands exit-family/risk/TTL optimization and why it follows DSS. | Optuna tunes execution geometry after signal discovery. | CLI runbook and optimizer/exit policy references. | Open Backtester or Strategies. |
| `/docs/strategies` | User wants to understand strategy configs and portfolios. | User knows active archives, donor portfolios, router research, and owner promotion rights. | Strategies are source-controlled evidence and runtime inputs with different maturity statuses. | Candidate archive, strategy JSON paths, router runtime contract. | Open Live Execution or Risk Boundaries. |
| `/docs/live-execution` | User wants live architecture without account state. | User knows how signals become OKX orders and where live truth lives. | Live execution mirrors backtester decisions where possible and defers money truth to OKX/runtime config. | Live execution spec, settings, parity table, state/sync modules. | Open Configuration or Operations. |
| `/docs/cli` | User needs a command. | User knows which command surface is current and which jobs are long/risky. | CLI snippets are operational entry points, not embedded execution results. | CLI runbook and README setup. | Copy a snippet or open a related section. |
| `/docs/configuration` | User needs safe settings context. | User understands env/config source-of-truth boundaries and dry-run/live separation. | Config controls runtime behavior; docs explain it but do not override it. | Execution settings, README, live spec. | Open Live Execution or Risk Boundaries. |
| `/docs/operations` | User needs deployment/monitoring context. | User knows Railway, preflight, logs, notifications, CI status, and proposed observability gaps. | Operations are explicit runbooks with proposed and active maturity clearly separated. | Railway, observability, CI, notifications docs. | Open CLI or Configuration. |
| `/docs/risk-boundaries` | User may over-trust docs or UI. | User knows closed-candle, OKX truth, benchmark override, and live-money boundaries. | Safety is a cross-cutting framework contract. | AGENTS, state, benchmark, live execution, regression docs. | Return to relevant subsystem. |
| `/docs/glossary` | User has a term or acronym. | User can map terms to pages, source docs, aliases, and maturity/risk labels. | Glossary is the bridge between crypto, code, and operations vocabulary. | All page source maps. | Search or open linked term pages. |

## Message Trajectory

- Starting state: user needs orientation.
- Problem or tension: crypto strategy repos become hard to trust when research,
  backtests, live execution, and archived evidence are mixed together.
- Product explanation: `crypt docs` explains the repository as a framework,
  separating research, replay, strategy configs, live execution, and operations.
- Mechanism: guided pages and reference docs map each subsystem to its source
  of truth, flow, contracts, risks, CLI surface, and next reading.
- Proof: diagrams, source-backed claims, maturity labels, risk markers, and
  command snippets.
- Objection handling: portal does not expose live balances or trading controls;
  live truth remains runtime config and OKX state.
- Action: read the guided path or search the full content.

## Text Hierarchy

- Level 1 main promise: "crypt docs explains how the crypto strategy framework
  works, from candles and strategy research to backtests and live OKX
  execution."
- Level 2 section arguments: every section heading should advance a concrete
  understanding step: map, data flow, decision flow, safety boundary, command
  surface, or next reading.
- Level 3 supporting copy: mechanism, examples, constraints, source-of-truth
  proof, and operational caveats.
- Level 4 action copy: concrete actions such as "Начать маршрут", "Открыть
  Backtester", "Скопировать команду", "Искать по документации".
- Level 5 microcopy: stateful search hints, zero-result help, copy feedback,
  risk badges, maturity labels, and theme labels.

## Proof System

- Claim: portal fully describes how the code works at framework-documentation
  depth.
  Required proof: complete first-release section inventory, source map, search
  coverage matrix, and next-reading graph.
  Available proof: repository docs and module inventory.
  Missing proof: independent factual research report and final Text Inventory.
  Decision: add proof before implementation approval.
- Claim: live execution shares behavior with backtester where possible.
  Required proof: live parity contract references.
  Available proof: `docs/execution/live_execution.md`,
  `docs/backtester_regression.md`.
  Missing proof: page-level source map.
  Decision: add proof and keep runtime-state claims cautious.
- Claim: search covers the full curated portal content.
  Required proof: generated index includes every route's title, headings,
  body text, tags, maturity labels, risk labels, snippets, diagram labels, and
  glossary aliases.
  Available proof: Discovery Contract and Source Map Matrix.
  Missing proof: implemented search index coverage test.
  Decision: add test/fixture during implementation.

## Objection Map

- Objection: "Is this just the old Telegram signal MVP?"
  Where it arises: home page and Overview.
  Response: explain that the old signal-only Telegram MVP is historical; the
  current product is research workbench plus live OKX execution.
  Placement: first-screen risk/context note and Overview.
  Evidence: `README.md`, `docs/state/current.yml`.
- Objection: "Can the site place orders or show account state?"
  Where it arises: Live Execution and Operations.
  Response: no; portal is documentation only. Runtime env and OKX remain the
  source of truth.
  Placement: Live Execution intro and risk marker.
  Evidence: owner answer 19; `docs/execution/live_execution.md`.
- Objection: "Are benchmark results production gates?"
  Where it arises: Strategies and Strategy Benchmark content.
  Response: benchmark is a reporting target; owner can promote a strategy.
  Placement: Strategies page and glossary term.
  Evidence: `docs/strategy_benchmark.md`.

## Microcopy Rules

- Buttons and links: name the result directly in Russian; keep canonical
  technical names where they are product terms.
- Navigation labels: support both learning path and reference map.
- Forms: search fields say what corpus is covered.
- Loading states: only for search/index preparation and route transitions if
  needed; no live data loading states.
- Empty states: explain the boundary and offer a next useful route.
- Error states: state what failed and how to continue browsing.
- Success states: for copied snippets and settings such as theme switch.
- Confirmations: no destructive or live-money confirmations because the portal
  is read-only.
- Tooltips and badges: explain maturity (`stable`, `research`, `operational`,
  `archived`) and risk labels concisely.

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
