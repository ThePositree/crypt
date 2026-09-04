# Current Frontend Phase Handoff

# NEXT MAIN SESSION PROMPT

You are the sole phase main for D3 frontend phase P02.

- Protocol version: 1
- Handoff ID: `crypt-docs-p02-2026-09-04`
- Status: accepted
- Created at: 2026-09-04
- Accepted at: 2026-09-04
- Mode: manual/native Orca coordination
- Predecessor context: primary Codex session
- Receiving context: dispatched phase main (`term_b095c115-2e3c-45ce-bc58-3ab5a82b338b`)
- Last ledger event: REVIEW_PASSED

## Startup Control

1. Read `AGENTS.md`, `docs/agent/context_routes.yml`, `docs/state/current.yml`, `docs/agent/frontend_design_subsystem.md`, and the full frontend memory set under `docs/frontend/`.
2. Verified against `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
3. P02 Read Receipt published.
4. Factual product research completed in `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`.
5. Product Surface Model updated in `docs/frontend/product-surface-model.md` (Revision 1).
6. Coordinator corrected missing source path references after verifying active repository paths.
7. Independent P02 review passed with 0 blocking findings in `docs/frontend/reviews/2026-09-04-crypt-docs-p02-product-surface-review.md`.
8. Next action: wait for owner decision on `Product Surface Approval` before unlocking P03.

## Repository State

- Absolute root: `/home/n-tretyakov/projects/crypt`
- Branch or worktree identity: `dev`
- Commit: `a36c612` (with working tree changes for P02)
- Dirty-state summary: P02 documentation artifacts modified/created.
- Owner of intentional uncommitted change: dispatched phase main (`term_b095c115-2e3c-45ce-bc58-3ab5a82b338b`)
- Frontend instruction version: 9
- Date: 2026-09-04

## Product And Task Contract

- Product name: `crypt docs`
- Product type: large documentation portal.
- Audience: developer-crypto-trader.
- Portal language: Russian.
- Stack selected by owner: Next.js plus Tailwind CSS.
- Content model: all curated content lives in static source files; no CMS.
- Primary job: explain how the `crypt` repository works as a crypto-trading framework.
- First screen: explain the project and how the code works; do not display runtime execution results.
- Required sections: Overview, Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.
- Navigation: both architecture-first left sidebar and guided learning paths.
- Search: full curated content, exposed through header search and `Cmd/Ctrl+K`.
- Interactions: expandable diagrams, tabs, filters, copyable command snippets.
- Page chrome: breadcrumbs, sidebar, desktop on-page TOC, "what to read next" on every page.
- Visual direction input: playful lo-fi, abstract mascots, light and dark themes.
- Risk markers: live money, OKX execution, config safety, and no-look-ahead bias.
- Status markers: stable, research, operational, archived.
- Exclusions: current balances, positions, live runtime metrics, execution results, source-code quotation as the main teaching mode, CMS, external account mutation.

## Phase State

- Completed phase: P01 Task Contract, Collaboration Check, onboarding, and Uncertainty Check.
- Current phase: P02 factual product research, Product Surface Model authoring, and preparation for Product Surface Approval.
- P01 artifact: `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
- P02 artifacts:
  - `docs/frontend/product-surface-model.md` (Revision 1)
  - `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md` (Revision 1)
  - `docs/frontend/reviews/2026-09-04-crypt-docs-p02-product-surface-review.md` (independent review pass)
- First controlling gate: Product Surface Approval (pending owner decision).
- Stop condition: owner Product Surface decision is recorded, or a blocker is reported.
- Forbidden next-phase actions: do not write Next.js/Tailwind code, do not start visual direction boards, wireframes, or P03 text inventory until Product Surface Approval is granted.

## Owner Control

- Existing owner waivers: none.
- Active controlling gate: Product Surface Approval.
- Pending owner question: Does the owner approve the Product Surface Model in `docs/frontend/product-surface-model.md` (Revision 1)?

## Obligation Ledger

- O01 Full Messaging System: applies (deferred to P03)
- O02 Source-Grounded Content Authoring: applies (deferred to P03)
- O03 Text Inventory And Copy Approval: applies (deferred to P03)
- O04 Independent Factual Product Research: satisfied (`docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`)
- O05 Product Surface Model: satisfied (`docs/frontend/product-surface-model.md` Rev 1)
- O06 Independent First-Use Review: applies (deferred to P09 wireframes)
- O07 Independent Wireframe Rendered Visual QA: applies (deferred to P09)
- O08 Messaging Identity and Messaging Contracts: applies (deferred to P03)
- O09 Design Identity and Design System: applies (deferred to P05)
- O10 Five raster Visual Direction Boards: applies (deferred to P04)
- O11 Visual Direction Approval: applies (deferred to P04)
- O12 Selected Visual Direction Translation: applies (deferred to P05)
- O13 UI Library And Component Showcase: applies (deferred to P06)
- O14 UI Library Approval: applies (deferred to P06)
- O15 Production Raster Asset Pack: applies (deferred to P07)
- O16 Production Raster Asset Pack Approval: applies (deferred to P07)
- O17 Flows: applies (deferred to P08)
- O18 Page-level wireframes for every real page or meaningful screen: applies (deferred to P09)
- O19 Persistent HTML Wireframe Artifacts: applies (deferred to P09)
- O20 Wireframe Approval: applies (deferred to P10)
- O21 Screen contracts for every real page or meaningful screen: applies (deferred to P10)
- O22 Independent Contract Review: satisfied for P02 Product Surface Model; applies again for later contract phases
- O23 Frontend Lead Contract Review Brief: applies (deferred to P10)
- O24 Action Contract: not applicable (documentation portal is read-only, has no external mutations)
- O25 Final Implementation Approval: applies (deferred to P11)
- O26 Separate Implementation Session: applies (deferred to P12)
- O27 Frontend Implementation Brief: applies (deferred to P11)
- O28 Wireframe Conformance Contract: applies (deferred to P10)
- O29 Interaction Inventory: applies (deferred to P10)
- O30 Full link and navigation coverage: applies (deferred to P10/P12)
- O31 Six viewport classes: applies (deferred to P09/P12)
- O32 Accessibility checks: applies (deferred to P12/P13)
- O33 Independent Frontend QA Gate: applies (deferred to P13)
- O34 Independent QA Brief: applies (deferred to P13)
- O35 Frontend Rubric Review: applies (deferred to P10/P13)
- O36 Durable frontend memory updates: applies (in progress throughout D3)
- O37 Final Instruction Audit: applies (deferred to P13)
- O38 Phase Main Control Handoff before every D3 phase: satisfied (P02 handoff accepted)
