# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

## 2026-09-02 - Documentation portal product contracts

- Drafted the D3 product direction for `crypt docs`, a curated Russian
  Next.js/Tailwind documentation portal for developer-crypto traders.
- Recorded first-release scope across Overview, Architecture, Backtester,
  Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations,
  and Glossary, with full-content search and guided/reference navigation.
- Captured explicit boundaries: no repository Markdown rendering, no CMS, no
  command-result displays, and no current live production state, balances,
  positions, or runtime metrics.
- Seeded messaging, design identity, design-system direction, and active task
  notes before the required frontend approval and visual-board gates.
- Recorded owner Product Surface Approval and generated five raster Visual
  Direction Boards for the pending visual approval gate.
- Recorded owner Visual Direction Approval for Board 3, `System Islands
  Atlas`, and finalized the atlas-based design identity/system direction for
  artifact work.
- Added proposed navigation flow, page-level screen contracts, directly
  openable HTML wireframe package, and Orca browser preflight notes for the
  documentation portal.
- Ran independent Orca contract review for the wireframe/screen-contract
  package, recorded the block verdict, and addressed the findings by expanding
  page/search contracts, adding search expected-result criteria, correcting
  screen index evidence, aligning Board 3/breakpoint records, and replacing the
  fictional wireframe command with source-backed snippets.

---

## 2026-09-01 - Frontend HTML wireframes and separated execution roles

- Required directly openable, operable HTML wireframes for every approved page,
  screen, and applicable state; screenshots now serve only as QA evidence.
- Added state matrices and Wireframe Conformance Contracts that freeze approved
  structural and behavioral invariants through production implementation.
- Required every frontend Markdown contract package to pass independent
  read-only review by a potential frontend lead before approval or use.
- Separated frontend design/control, write-scoped production implementation,
  and final independent QA into distinct agent or session contexts with
  self-contained briefs.
- Reverted the unfinished documentation-portal artifact series before applying
  the instruction revision.

---

## 2026-09-01 - Independent frontend QA gate

- Reverted the generated documentation site commit so the repository returns to
  instruction-only frontend hardening before further process changes.
- Required frontend implementation QA to be performed outside the implementation
  session by read-only delegated reviewers, or by an owner-run fresh-session QA
  fallback when subagents are unavailable.
- Added Independent QA Brief requirements with explicit route, interaction,
  viewport, discovery, accessibility, text, evidence, and pass/fail criteria
  written for literal reviewers.
- Strengthened copy review around exhaustive Text Inventory coverage for every
  user-visible text fragment, not only prominent or important text.

---

## 2026-09-01 - Frontend phase transition gates

- Required refreshed frontend Read Receipts after resumes, interruptions,
  owner redirects, scope changes, waiver changes, and completed approval gates.
- Added gate-level evidence requirements for Product Surface Approval, Visual
  Direction Approval, Wireframe Approval, and Final Implementation Approval.
- Blocked D3 Wireframe Approval until every approved page or meaningful screen
  appears in a page-to-wireframe index with artifact paths, screen-contract
  paths, viewport coverage, states, interactions, content/discovery coverage,
  and inspection evidence.
- Required one screen contract file per approved page or meaningful screen for
  D3 multi-page or multi-screen work.

---

## 2026-09-01 - Frontend explicit waiver phrase

- Required frontend agents to follow the full subsystem exactly unless the
  owner grants a scoped waiver with the exact phrase `FRONTEND WAIVER:`.
- Added canonical Active Obligations names and statuses to the frontend Read
  Receipt so agents cannot replace required obligations with vague summaries.
- Clarified that onboarding answers, stack choices, page lists, language
  choices, visual direction, and search requirements move the artifact
  sequence forward and do not approve implementation by themselves.

---

## 2026-09-01 - Frontend read receipt obligations

- Required frontend Read Receipts to separate owner-decision gates from active
  execution obligations.
- Required receipts to name applicable messaging, content, discovery,
  interaction, responsive, accessibility, rubric, rendered evidence, memory,
  and final audit obligations before frontend action.
- Clarified waiver framing around exact artifacts, obligations, risks, and
  remaining evidence instead of shortcut or reduced-quality framing.

---

## 2026-09-01 - Frontend all-text messaging pass

- Clarified that the full Messaging System applies to every user-visible text
  fragment and microcopy point in the affected frontend surface, not only major
  headings or prominent copy.
- Updated copy QA and completion language to require evidence for all
  user-visible text across pages, screens, states, actions, labels, and
  repeated content patterns.

---

## 2026-09-01 - Frontend full QA and messaging audits

- Required the full Messaging System pass for frontend work that creates,
  changes, or approves user-visible text.
- Expanded responsive QA to six generic viewport classes and required evidence
  for each class on substantial frontend surfaces.
- Required interaction inventories, link/navigation coverage, representative
  discovery QA, before/after content coverage audits, and an always-present
  Frontend Rubric Review.
- Strengthened wireframe requirements so every real page or meaningful screen
  has its own wireframe package and implementation approval maps page-level
  artifact paths.

---

## 2026-09-01 - Frontend raster visual boards

- Clarified that Visual Direction Boards default to raster UI showcase
  artifacts because the final implementation stack may still be unknown during
  visual exploration.
- Limited HTML/CSS/JS visual board pages to fallback use when raster generation
  is unavailable or cannot produce inspectable artifacts.

---

## 2026-09-01 - Frontend visual board component showcase

- Clarified that Visual Direction Boards are rendered Design System /
  Component Showcase, Gallery, or Playground artifacts, not standalone mood
  images.
- Required boards to demonstrate representative UI fragments, component
  coverage, state examples, responsive behavior, and any supporting imagery in
  an interface context.

---

## 2026-09-01 - Frontend rendered artifact gates

- Clarified that D3 frontend phases prioritize completed gate evidence over
  implementation speed.
- Required Visual Direction Boards and wireframes to exist as rendered
  artifacts with stable paths, inspected viewports, coverage notes, and owner
  decision records before implementation approval.
- Clarified that summaries and written contracts explain rendered artifacts
  while the gate is completed by the artifact evidence itself.

---

## 2026-09-01 - Frontend content and discovery completeness

- Required frontend work to translate owner quality, depth, completeness,
  coverage, and production-readiness language into concrete acceptance
  criteria before implementation.
- Added generic Content And Capability Contract and Discovery Contract coverage
  to the canonical frontend subsystem and durable frontend artifact templates.
- Clarified that visual polish, successful builds, screenshots, and clean
  consoles do not prove completion when the promised frontend surface requires
  substantial content, data, interaction breadth, or discovery quality.

---

## 2026-09-01 - Frontend gate control verdicts

- Added explicit `STOP` / `PROCEED` Read Receipt verdicts for frontend work.
- Clarified that approvals and scoped waivers come from explicit owner
  messages, and short frontend requests keep their depth and approval gates.
- Required D3 onboarding and approval gating when new frontend surfaces are
  requested while product, messaging, design, system, or active context memory
  is not established.

---

## 2026-09-01 - Direct full-doc context routing

- Removed compact route-summary files and the routing layer that loaded them.
- Updated deterministic context routing, context helper validation, benchmark
  expectations, README documentation map, and agent bootstrap to use canonical
  full markdown docs directly.

---

## 2026-08-31 - Documentation regression tests removed

- Removed repository documentation regression tests so docs and instruction
  files are no longer enforced by exact structural test expectations.

---

## 2026-08-31 - Frontend messaging system

- Added a portable frontend messaging system that treats copy as a product
  layer rather than filler content.
- Added Messaging Identity, Messaging Contract, page message trajectory, text
  hierarchy, proof, objection mapping, microcopy, anti-slop review, and Copy QA
  requirements to the canonical frontend subsystem.
- Added `docs/frontend/messaging.md` and connected messaging requirements to
  product surface models, screen contracts, wireframes, flows, reviews,
  routing, and current state.

---

## 2026-08-30 - Frontend collaboration and owner steering contracts

- Added an Owner Steering Contract that tells the owner they may interrupt,
  correct assumptions, reject or replace a direction, change priorities, skip
  onboarding questions, or introduce their own direction at any time.
- Added a Collaboration Check for D2/D3 and context-heavy frontend work: detect
  the available subagent system and required interface/provider/model, define a
  bounded delegated outcome and review path, then ask the owner whether to use
  subagents for that scope.
- Clarified that silence is not delegation approval, declining subagents does
  not block single-agent progress, and workers are created only after the
  owner's answer.
- Extended frontend product and review templates plus regression tests for the
  new collaboration records.

---

## 2026-08-30 - Frontend instruction system v2

- Rewrote the canonical frontend subsystem and compact route summary around an
  explicit Task Contract: outcome, scope, sources of truth, constraints,
  acceptance evidence, and unresolved material decisions.
- Preserved the established frontend practices: product discovery, minimum
  30-question adaptive onboarding, five rendered Visual Direction Boards,
  named owner gates, Mermaid flows, persistent HTML wireframes, screen
  contracts, Action Contracts, responsive/functional/visual/completeness QA,
  phased handoffs, independent review, and durable frontend memory.
- Added D0-D3 depth classification, task-proportional artifact triggers,
  instruction/data separation, model/tool revision metadata, explicit
  assumption handling, and evidence-based QA records.
- Updated every frontend memory template to capture revisions, evidence,
  trust boundaries, acceptance criteria, validation, and approval state.
- Replaced brittle exact-sentence regression tests with structural and
  behavioral invariants for the preserved workflow and new prompt contracts.

---

## 2026-08-28 - Frontend gate protocol hardening

- Strengthened the frontend subsystem with named approval gates, scoped
  waivers, mandatory Uncertainty Check structure, Action Contract requirements,
  precise completion labeling, final pre-implementation summaries, rendered
  artifact review, durable implementation reviews, and component-primitive
  coverage for Visual Direction Boards.
- Replaced the fixed route-summary line-count rule with a relative compactness
  check so summaries remain materially smaller than their full source docs.
- Updated docs regression coverage for the new frontend gate protocol and
  relative compactness rule.

---

## 2026-08-28 - Frontend phase-based work rhythm

- Added a positive frontend work rhythm that frames all frontend tasks as
  deliberate phase-based product work where correctness, product fit, visual
  quality, and durable memory outrank immediate implementation.
- Clarified that a frontend session can be successful when it completes
  discovery, onboarding, product modeling, visual direction, wireframes, review,
  or handoff without starting production UI code.
- Updated docs regression coverage so the full subsystem and compact summary keep
  the phase-based framing visible to future agents.

---

## 2026-08-28 - Frontend subagent continuation

- Strengthened frontend phase continuation so capable agents use isolated
  subagents for substantial next phases whenever subagents are available, with
  fresh-session handoff as the fallback.
- Updated the compact frontend summary and docs regression coverage for the
  subagent continuation rule.

---

## 2026-08-28 - Frontend wireframe contracts

- Added persistent HTML/CSS/JS wireframes as a UI contract gate after rendered
  Visual Direction Boards and before production UI code changes.
- Clarified Mermaid as the default format for frontend user flows, navigation
  maps, and state diagrams, kept current alongside wireframes and screen
  contracts.
- Routed `docs/frontend/wireframes/` through frontend context and added docs
  regression coverage for Mermaid flows, wireframes, owner approval, and
  production UI gating.

---

## 2026-08-28 - Frontend positive workflow contracts

- Reworked frontend subsystem wording toward concrete positive completion
  criteria: phase outputs, minimum interview depth with uncertainty checks,
  rendered visual direction boards, owner-gate completion, canonical handoff
  truth, and responsive composition verdicts.
- Updated compact frontend summary and docs regression tests to preserve the
  positive workflow contracts instead of relying on negative instruction
  phrases.

---

## 2026-08-27 - Frontend owner decision gates

- Added Owner Decision Gates to separate completed interviews from completed
  onboarding, design approval, and readiness for implementation.
- Required explicit owner confirmation for stack selection, product surface,
  visual direction, scope/completeness, and final pre-implementation approval on
  substantial frontend work.
- Strengthened Visual Exploration so Visual Direction Boards require owner
  feedback, remain direction studies rather than production assets, and cannot
  be used to finalize Design Identity, Design System, or implementation without
  approval.
- Updated the compact frontend subsystem summary and docs regression tests for the
  new gate semantics.

---

## 2026-08-27 - Frontend phase handoff strategy

- Added Phase Handoff Strategy to the frontend design subsystem so large
  frontend tasks are split into explicit phases instead of overloading one
  continuous agent context.
- Defined temporary durable handoff artifacts, required handoff contents,
  canonical source-of-truth persistence, consumed-handoff deletion, optional
  isolated subagent continuation, fresh-session fallback, and the rule that
  agents must not pretend they can remove prior conversation history from
  context.
- Updated the compact frontend subsystem summary and docs regression tests so the
  phase handoff rules remain visible through selective routing.

---

## 2026-08-25 - Frontend design subsystem

- Clarified that first-time frontend onboarding is deep, not short: agents must
  not describe it as quick/brief/lightweight, must ask 30 total questions in 6
  adaptive rounds of 5, and must not promise implementation immediately after
  the owner's next answer while frontend memory is still unestablished.
- Reframed the frontend onboarding stop gate as state-based: when frontend
  memory is not established, the first substantial frontend task must pause for
  full onboarding, not only tasks labeled as new site/app work.
- Clarified that the owner's first answer to onboarding questions does not
  establish frontend memory; agents must continue through product surface,
  adaptive interview, preliminary identity, visual exploration, owner feedback,
  final identity, and design system before implementation unless waived.
- Clarified that Visual Direction Boards are direction studies for owner
  feedback and cannot be replaced by one production hero image or site asset.
- Added Product Knowledge Discovery, Product Surface Model, and Product
  Completeness Review so substantial frontend work first determines what users
  must understand and do before visual screen design begins.
- Added Responsive Design Pass and Responsive Transformation Reasoning:
  responsive work must evaluate each important viewport as an intentional
  composition, not only a layout that survived without overflow.
- Split final substantial frontend verification into Functional QA, Visual QA,
  and Product Completeness Review, with each check covering a different failure
  mode.
- Updated frontend onboarding to ask questions in adaptive 5-question rounds
  instead of dumping every possible design question at once.
- Added an explicit implementation-stack gate for new site/app work when the
  repository does not already establish the stack, so agents ask about static
  versus framework/UI-library preferences instead of assuming.
- Tightened rendered QA requirements: new site/app work must check more than
  one desktop/mobile pair, include large-screen breakpoints when relevant, and
  exercise every added interactive element, button, link, and post-interaction
  state.
- Tightened the frontend subsystem with explicit non-negotiable onboarding
  gates: agents must stop before implementation for a new frontend/product when
  Design Identity is not established, unless the owner waives onboarding or
  prior frontend memory already proves the direction.
- Added a docs regression test so the frontend onboarding stop gate remains
  present in both the full subsystem document and compact summary.
- Added a portable frontend design subsystem for AI agents in
  `docs/agent/frontend_design_subsystem.md`, covering proportional design
  depth, first-use discovery, design onboarding, visual exploration, persistent
  identity, component reuse, screen contracts, rendered inspection, visual
  review, anti-AI-default UI checks, responsive behavior, and state design.
- Added a compact frontend route summary and routed frontend/UI tasks through
  `docs/agent/context_routes.yml`.
- Added persistent frontend memory scaffolding under `docs/frontend/` for
  context, design identity, design system, component registry, visual
  references, flows, screen contracts, decisions, and visual reviews.
- Recorded the new canonical frontend subsystem paths in
  `docs/state/current.yml`.

---

## 2026-08-11 — Phase-C reconciliation boundary and first artifacts

- Added `--load-from` to `backtester run` so live replay checks can load a
  warmup window while starting execution/accounting at a later `--from`
  boundary.
- Fixed DSS archived default ATR stop replay to use the previous closed ATR
  window and signal close as the stop basis. This restores phase-C parity with
  the production `81a4e01` live signals, including the
  `2026-08-03T17:00Z` raw SL `72.987143` stop that exits on
  `2026-08-04T00:58Z`.
- Added phase C as a strict backtester regression checkpoint in
  `docs/backtester_regression.md`, with the `2026-07-13` warmup start,
  `2026-07-29T12:00Z` accounting start, expected metrics, and signal-level
  pass/fail targets.
- Identified the phase-C production boundary from Railway deployments:
  `81a4e01` deployed at `2026-07-29T12:12:04Z` was the latest deployed
  live-behavior change, adding live distant-TP reachability adjustment and the
  owner-selected production strategy JSON change. The later `0b76c30`
  production deploy was documentation/status cleanup for runtime code.
- Confirmed the `exchange_closed_unknown` OKX child-fill classifier fix is in
  local commit `2704c83` and has not been deployed to Railway production.
- Exported phase-C OKX private artifacts under
  `results/live_reconciliation/phase_c_20260729/`: fills, regular orders,
  algo order history, account bills, and grouped order fills from
  `2026-07-29T13:00Z` onward.
- Backfilled SOL-USDT-SWAP H1/15m/4H/1d plus last/mark 1m data through the
  closed `2026-08-10` UTC window and ran a preliminary replay from signal bar
  `2026-07-29T12:00:00Z` through `2026-08-10T22:00:00Z` with
  `$83.0980436609` starting cash. The replay produced `20` trades,
  `17` closed and `3` open, `$72.39` final capital, and `-$10.71` PnL.
- Preliminary live/replay count check before `2026-08-11T00:00Z`: OKX has
  `20` phase entries and `17` phase closes, plus one carried-in pre-phase
  short close on `2026-07-30T13:47:32Z`. The first concrete mismatch to audit
  is the live `2026-08-03T18:00Z` long, which OKX stopped on
  `2026-08-04T00:58:40Z` while fresh replay keeps the analogous trade until
  `2026-08-06T13:05Z`.
- Pulled Railway archived execution logs for phase C and built log-backed join
  artifacts under `results/live_reconciliation/phase_c_20260729/`, including
  `railway_live_entries.csv`, `railway_live_closures.csv`, and
  `phase_c_live_backtest_match_81a4e01_log_joined.csv`.
- Re-ran the closed-window replay on the actual production commit `81a4e01`.
  With the deployed code, live/replay SL values match for joined phase-C
  entries; the `2026-08-03T18:00Z` long now exits at the same OKX stop minute.
  This exposed and fixed a replay-methodology gap: the CLI now supports
  `--load-from` so phase checks can warm up indicators without executing
  pre-phase trades.
- Fixed CI compatibility issues around `EvaluationContext` candle aliases,
  websocket boundary payload construction, router/shadow execution metadata,
  and stale test mocks.
- Reduced full pytest runtime by removing real sleeps from timeout tests,
  avoiding default-executor threadpool teardown in a live executor unit test,
  using the fast crypt-ensemble incremental adapter path, and shrinking
  synthetic research search spaces.
- Re-ran the canonical backtester checkpoints after the phase-C DSS stop-basis
  fix. Live phase A/B/C match the documented replay targets; the full
  2021-2026 v6 replay now uses the post-fix target `$1,411,788.62`,
  `1564` trades, `-4.14%` below-start drawdown, and `-33.26%`
  peak-to-trough drawdown.
- Fixed monthly return reporting for months with no closed trades: `ret_abs`
  now carries forward the latest known capital instead of printing `nan` while
  the month return is `0.0`.

## 2026-08-11 — AI-first context routing

- Replaced the long agent bootstrap with compact hard rules in `AGENTS.md` and
  routed detailed operating policy to `docs/agent/operating_rules.md`.
- Added deterministic context routing in `docs/agent/context_routes.yml` and a
  compact current-state snapshot in `docs/state/current.yml`.
- Added compact route summaries for backtester regression, strategy benchmark,
  live execution, live/backtest reconciliation, and the AI context system.
- Added `docs/agent/context_benchmark.md` with 20 typical agent questions for
  comparing routed markdown, routed markdown plus `rg`, vector retrieval, and archive
  image packs.
- Added machine-readable benchmark expectations in
  `docs/agent/context_benchmark.yml` plus `scripts/agent_context.py` for
  context validation, eager-vs-routed token budgeting, and archive-only PNG
  image-pack generation.
- Extended the context helper with deterministic `route` and `benchmark`
  commands so future vector/image retrievers must beat or match the routed
  markdown source-hit and required-term baseline before adoption.
- Recorded the 2026-08-11 deterministic benchmark baseline in
  `docs/agent/context_benchmark_results.md`: `20/20` source hits and `20/20`
  required-term hits.
- Added explicit knowledge-base expansion rules: durable knowledge must update
  routes, current state, or benchmark coverage when it affects future agent
  routing, current production facts, live money, or backtester checkpoints.
- Documented the vector/image retrieval policy: canonical rules and current
  state stay as text; vector and text-as-image are archive/discovery
  experiments until a 20-question benchmark proves accuracy.
- Added docs tests that validate route paths, compact source links, and
  bootstrap size.
- Kept `CHANGELOG.md` as recent history and moved older August entries to
  `CHANGELOG_ARCHIVE.md`.
