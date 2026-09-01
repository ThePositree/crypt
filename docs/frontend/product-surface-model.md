# Product Surface Model

Status: proposed.
Revision: 1
Approval: pending owner approval.

Use this file for durable frontend product-surface understanding. It should be
filled before substantial new site/app work, major redesigns, or broad product
surfaces.

Do not ask the owner to repeat product information that already exists in the
repository. First discover product knowledge from sources such as `README.md`,
project docs, requirements, specs, current state, task context, or a canonical
`product.md`/`PRODUCT.md` when present.

## Product Knowledge Sources

- Primary: owner onboarding answers on 2026-09-01.
- Supporting: `README.md`, `docs/state/current.yml`,
  `docs/strategy_benchmark.md`, `docs/operator.md`, and
  `docs/tasks/IN_PROGRESS.md`.
- Contradictions or gaps: runtime/live-money details are intentionally not
  public surface truth for the first site even though the repository contains
  live execution docs. The public site should explain neutral architecture and
  workflows without exposing private operational values or current account
  state.

## Scope Contract

- Outcome: a production-ready public curated docs platform for `crypt`, a
  Python research workbench for crypto strategy discovery, backtesting, and
  neutral live-execution architecture.
- In scope: a large multi-page docs portal under `site/`; system-map home;
  dual navigation by topic and user journey; global backend-backed search;
  semver-aware docs structure; curated pages for Overview, Architecture,
  Strategy Lifecycle, Backtester, Live Execution, Glossary, For Developers,
  For Crypto Traders, Guides, API/reference-style code explanations, Risk &
  Limits, and versioned docs.
- Explicitly out of scope: rendering existing Markdown files directly as the
  product; private runtime details; live account equity; current OKX positions;
  API keys, deployment secrets, private alerts, or operational values; trading
  advice; authenticated private pages.
- Assumptions: docs copy is English; code/docs remain English per repository
  policy; first production UI uses Next.js and Tailwind CSS; search indexes only
  curated public content generated for the site; runtime mutation is not part of
  this surface.
- Unresolved decisions: exact first semver labels, package manager, search
  index storage format, whether the first deployment target is OpenAI Sites or
  another host, and final visual direction after rendered boards.

## User Capabilities And Goals

- Primary goals: understand what `crypt` is, how the Python modules fit
  together, how a strategy moves from idea to exact backtest to production
  architecture, and how to run or inspect representative workflows.
- Secondary goals: compare developer and crypto-trader mental models, discover
  concepts through search, follow copy-command/output/explanation guides, and
  understand risk limits without private live-money context.

## Required Content And Features

- In scope: curated prose; diagrams and flow cards; interactive system map;
  snippets used sparingly; guide steps; searchable concepts; glossary entries;
  version selector; public risk section; mascot-supported lo-fi visual identity.
- Explicitly out of scope: uncurated Markdown mirroring; exhaustive private
  operations runbook replication; auto-ingestion of every repository document;
  trading signal dashboards; order controls; account mutation controls.

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory: repository
  README and selected docs under `docs/`, code structure under `src/crypt` and
  `src/backtester`, curated owner-approved product decisions, and generated or
  hand-authored mascot/diagram assets.
- User-facing coverage promised by the request and product surface: "everything
  about the project" at portal level, meaning every major subsystem and public
  workflow has a curated entry point, not that every historical note or private
  runtime artifact is published.
- Included entities, sections, items, states, levels, views, or workflows:
  system overview, architecture map, data ingestion, strategy composition,
  decision engines, backtester, strategy archive concept, result reading,
  neutral live execution architecture, OKX as an integration boundary,
  Telegram/reporting as an operator channel, risk and limits, developer setup,
  crypto-trader interpretation, glossary, search results, empty search state,
  version switcher, and guide pages.
- Boundaries requiring owner approval: publishing any specific live-money
  values, current production strategy details beyond neutral architecture,
  public claims about returns, mascot final direction, and first version labels.
- Required depth by important page, panel, step, result, or interaction:
  Overview and Architecture require full-screen curated diagrams; Backtester,
  Strategy Lifecycle, Live Execution, and Guides require step-by-step flows;
  Glossary and Search require structured indexable entries; Risk & Limits
  requires direct disclaimers without repeated page-level warnings.
- Source-of-truth proof: each page should cite or link to the underlying public
  repo source path or curated docs source in page metadata or inline source
  notes.
- Freshness, update, or synchronization expectations: docs versions are
  semver-scoped; the first release can be manually curated, with no promise of
  automatic synchronization from repository Markdown.
- Measurable coverage evidence: page inventory, search index entry count,
  glossary count, architecture-node coverage map, rendered route list, and
  validation screenshots.

## Discovery Contract

- Discovery surfaces: global search, topic navigation, journey navigation,
  interactive system map, glossary index, and contextual related links.
- Searchable or filterable corpus: curated pages, guide steps, glossary terms,
  architecture nodes, concepts, module references, and version metadata.
- Indexed fields and body-content coverage: title, description, headings,
  tags, section body, glossary aliases, subsystem, audience, journey stage, and
  version.
- Ranking, grouping, sorting, or recommendation behavior: prioritize exact
  title/glossary matches, then subsystem tags, then body matches; group results
  by page, concept, glossary term, and architecture node.
- Result snippets, labels, or explanations: each result shows title, type,
  version, route, excerpt, and why it matched when feasible.
- Empty and zero-result behavior: explain that only curated public docs are
  indexed and suggest topic/journey entry points.
- Keyboard and focus behavior: search opens from a visible control and a
  keyboard shortcut if implemented; result list is reachable and navigable by
  keyboard.
- Representative queries or discovery tasks: `backtester`, `OKX`, `strategy
  lifecycle`, `risk`, `closed candles`, `telegram`, `walk forward`, `fees`,
  `glossary`.
- Coverage evidence: automated index fixture, API response checks, and manual
  rendered search tests for representative queries.

## Messaging Requirements

- Starting user state: technically capable reader knows Python or crypto but
  does not yet understand how this repository turns research into execution.
- Intended leaving state: reader can navigate the system, trust the boundaries,
  and choose a next page or guide based on their role.
- Main idea: `crypt` is a research desk for crypto strategies: it explains the
  path from data and strategy hypotheses to exact backtests and neutral
  execution architecture.
- Required proof: visible architecture map, curated subsystem pages, source
  links, command/output/explanation guides, and honest risk boundaries.
- Objections to answer: "Is this just trading hype?", "Can I find the code
  path?", "Are live-money details exposed?", "Are results guaranteed?", "Is
  this for developers or traders?"
- Natural action: search, click a system-map node, choose a journey, or open a
  guide.
- Generic-copy risks: generic fintech claims, vague AI/trading language,
  unsupported performance promises, and decorative mascot content that does not
  help comprehension.

## User Journeys

- Actor and starting state: developer entering from repository link.
- Goal: understand architecture and run a representative workflow.
- Steps and decisions: start at system map, select Developer journey, read
  Architecture, open Backtester guide, copy command, inspect expected output,
  follow source links.
- Error or recovery path: if a command or concept is unclear, use search or
  glossary; if a result is missing, page should explain that the example is
  curated and version-scoped.
- Endpoint and feedback: developer knows which module or guide to inspect next.

- Actor and starting state: crypto-trader reader entering from public docs.
- Goal: understand strategy research without live private details.
- Steps and decisions: start at system map, select Crypto Traders journey, read
  Strategy Lifecycle, Result Reading, Risk & Limits, and neutral Live Execution
  Architecture.
- Error or recovery path: glossary explains technical terms; risk page explains
  limits and avoids return guarantees.
- Endpoint and feedback: reader understands project boundaries and can explore
  strategy/backtester pages.

## Information Architecture

- Pages or screens: Home/System Map, Overview, Architecture, Strategy
  Lifecycle, Backtester, Live Execution, Guides, Read Results, Risk & Limits,
  Glossary, For Developers, For Crypto Traders, Search Results, Version Index,
  Not Found.
- Navigation model: persistent topic navigation plus journey navigation,
  version selector, global search, related links, and clickable map nodes.

## Sections And Components

- Section: System Map.
- Purpose: show the project as connected subsystems.
- Required interactions: click nodes, highlight links, jump to relevant pages,
  filter or emphasize developer/trader journeys if approved.

- Section: Global Search.
- Purpose: discover curated docs, concepts, glossary entries, and architecture
  nodes.
- Required interactions: query input, grouped results, empty state, keyboard
  access.

- Section: Guide Step.
- Purpose: teach workflows through command, expected output, and explanation.
- Required interactions: copy command, expand explanation, source references.

- Section: Version Selector.
- Purpose: distinguish semver docs releases.
- Required interactions: select version and preserve route intent where
  possible.

## Completeness Review

- Primary goals covered: pending implementation evidence.
- Secondary goals covered: pending implementation evidence.
- Necessary content present: pending page inventory and copy review.
- Content and capability coverage proven: pending route/content map.
- Discovery/search coverage proven: pending search index/API validation.
- Messaging trajectory present: proposed in Revision 1.
- Claims backed by proof or softened: pending copy review.
- Objections answered where they arise: proposed in Revision 1.
- Core interactions present: pending implementation evidence.
- Journey endpoints clear: proposed in Revision 1.
- Placeholder/demo-only surfaces removed or marked out of scope: required for
  final review.
- Required states covered: pending wireframes, screen contracts, and QA.

## Approval Record

- Product Surface revision: 1
- Decision: pending
- Owner feedback or waiver scope: awaiting owner approval or corrections.
- Date: 2026-09-01
- Next phase unlocked: visual direction boards, flows, wireframes, and screen
  contracts for the first production implementation slice.

## Collaboration Record

- Delegation available: blocked for now.
- Required collaboration/runtime interface: Orca CLI/orchestration by local
  project preference.
- Proposed delegated scope: independent D3 visual board review or content
  coverage audit after product-surface approval.
- Owner decision: pending.
- Fallback: current-session single-agent work; Orca CLI failed on 2026-09-01
  with `/tmp/.mount_orca-lPgvcFl/orca-ide: bad option: --no-sandbox`.
