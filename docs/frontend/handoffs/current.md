# Current Frontend Phase Handoff

# NEXT MAIN SESSION PROMPT

You are the fresh D3 frontend phase main for `crypt docs` P02.

## Startup Control

- Protocol version: 1
- Handoff ID: `crypt-docs-p02-2026-09-04`
- Status: `prepared`
- Prepared at: 2026-09-04
- Prepared by: primary Codex session
- Mode: manual/native Orca coordination
- Phase to execute: P02 factual product research, Product Surface Model
  authoring, independent review, and Product Surface Approval
- Repository path: `/home/n-tretyakov/projects/crypt`
- Repository state: verify `git status` and the P01 artifact path before
  authoring P02; the predecessor may have checkpoint-committed P01

## Required First Actions

1. Read `AGENTS.md`, `docs/agent/context_routes.yml`,
   `docs/state/current.yml`, `docs/agent/frontend_design_subsystem.md`, and the
   full frontend memory set under `docs/frontend/`.
2. Verify this handoff against
   `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
3. Publish the frontend Read Receipt before P02 product or artifact work.
4. Use Orca-managed native independent review for P02 if review delegation is
   needed; keep long outputs file-backed.

## Product And Task Contract

- Product name: `crypt docs`.
- Product type: large documentation portal.
- Audience: developer-crypto-trader.
- Portal language: Russian.
- Stack selected by owner: Next.js plus Tailwind.
- Content model: all curated content lives in source files; no CMS.
- Primary job: explain how the `crypt` repository works as a crypto-trading
  framework.
- First screen: explain the project and how the code works; do not display
  runtime execution results.
- Required sections: Overview, Architecture, Backtester, Strategies, Live
  Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.
- Navigation: both architecture-first and guided learning paths.
- Search: full curated content, exposed through header search and
  `Cmd/Ctrl+K`.
- Interactions: expandable diagrams, tabs, filters, copyable command snippets.
- Page chrome: breadcrumbs, sidebar, desktop on-page TOC, "what to read next"
  on every page.
- Visual direction input: playful lo-fi, abstract mascots, light and dark
  themes.
- Risk markers: live money, OKX execution, config, and no-look-ahead bias.
- Status markers: stable, research, operational, archived.
- Exclusions: current balances, positions, live runtime metrics, execution
  results, source-code quotation as the main teaching mode, CMS, external
  account mutation.

## Phase State

- Completed phase: P01 Task Contract, Collaboration Check, onboarding, and
  Uncertainty Check.
- P01 artifact:
  `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
- Next phase output: Product Surface Model revision with source boundaries,
  route/page model, audience jobs, required states, risk boundaries, approval
  question, and independent review evidence.
- Stop condition: owner Product Surface decision is recorded, or a blocker is
  reported.

## Context Loading Boundaries

- Use source-grounded research for the product surface, but do not implement
  Next.js/Tailwind code in P02.
- Do not start visual direction boards, wireframes, UI library showcase, or
  production implementation in this phase.
- Do not display or fetch current live account state.

## Owner Control

- Existing owner waivers: none.
- First controlling gate: Product Surface Approval.
- If implementation is requested before gates are satisfied, stop unless the
  owner provides an exact scoped `FRONTEND WAIVER:`.
