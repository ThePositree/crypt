# Product Surface Model

Status: established.
Revision: 1
Approval: approved by owner on 2026-09-01.

Use this file for durable frontend product-surface understanding. It should be
filled before substantial new site/app work, major redesigns, or broad product
surfaces.

Do not ask the owner to repeat product information that already exists in the
repository. First discover product knowledge from sources such as `README.md`,
project docs, requirements, specs, current state, task context, or a canonical
`product.md`/`PRODUCT.md` when present.

## Product Knowledge Sources

- Primary: owner answers on 2026-09-01; `README.md`; `docs/state/current.yml`.
- Supporting: `AGENTS.md`; `docs/agent/context_routes.yml`; frontend onboarding documents.
- Contradictions or gaps: no conflict. Live runtime details stay governed by loaded runtime config and exchange state, not portal prose.

## Scope Contract

- Outcome: a large, manually curated docs portal that explains how the crypt codebase works as a crypto perpetual strategy research workbench.
- In scope: Overview, Architecture, Pipeline, Research, Backtester, Strategies, Candidate Archive, Live Execution, Risk Controls, Operator Runbooks, Known Risks, full-content local search, clickable architecture map, pipeline stepper, and module tabs.
- Explicitly out of scope: rendering repository markdown, showing live OKX data, showing backtest results, claiming performance, deploying the site.
- Assumptions: curated copy can derive from current canonical docs and owner input; live execution is presented as optional.
- Unresolved decisions: none blocking the first implementation.

## User Capabilities And Goals

- Primary goals: understand the product shape, navigate the system, learn how research, backtesting, archive, risk, and optional live execution fit together.
- Secondary goals: search curated content, use interactive diagrams to build a mental model, find runbook and risk context quickly.

## Required Content And Features

- In scope: all approved top-level pages, curated English copy, consistent pastel lo-fi developer desk visual language, responsive desktop and mobile layouts.
- Explicitly out of scope: live metrics, exchange account status, raw source tree browser, profit or result claims.

## Messaging Requirements

- Starting user state: crypto developer wants to understand what this repository does and where to start.
- Intended leaving state: reader can explain the workbench, its optional runtime boundary, and the main paths through the system.
- Main idea: crypt is research-first infrastructure for automated crypto perpetual strategies, with an optional live OKX execution module.
- Required proof: concrete system modules, source-of-truth boundaries, pipeline steps, and runbook/risk explanations.
- Objections to answer: whether it is a signal group, whether live execution is the core product, whether docs are raw markdown, whether results are being promised.
- Natural action: open Architecture or Pipeline, then move into the relevant page.
- Generic-copy risks: vague fintech claims, performance promises, and template documentation language.

## User Journeys

- Actor and starting state: crypto developer lands on the portal with partial context.
- Goal: understand how the codebase works.
- Steps and decisions: read hero, search or choose a section, inspect architecture map, step through pipeline, open related curated pages.
- Error or recovery path: search empty state suggests concrete system terms; navigation remains visible.
- Endpoint and feedback: reader reaches a page with summary, sections, related next pages, and interactive context where relevant.

## Information Architecture

- Pages or screens: Home plus curated docs pages for Overview, Architecture, Pipeline, Research, Backtester, Strategies, Candidate Archive, Live Execution, Risk Controls, Operator Runbooks, Known Risks.
- Navigation model: sticky top header with search; desktop left navigation; mobile stacked navigation; related-page cards at page endings.

## Sections And Components

- Section: Home hero.
- Purpose: explain the portal and route readers into architecture or pipeline.
- Required interactions: primary links.

- Section: Search.
- Purpose: find content across curated pages.
- Required interactions: modal open/close, query input, result links, empty state.

- Section: Architecture map.
- Purpose: explain subsystem responsibilities.
- Required interactions: clickable subsystem nodes and active detail panel.

- Section: Pipeline stepper.
- Purpose: explain research-to-runtime flow.
- Required interactions: step selection and related-page link.

- Section: Module tabs.
- Purpose: separate research, runtime, and docs loops.
- Required interactions: tab switching.

## Completeness Review

- Primary goals covered: yes, through top-level pages and diagrams.
- Secondary goals covered: yes, through search, related links, architecture map, pipeline stepper, and tabs.
- Necessary content present: yes for the first curated version.
- Messaging trajectory present: yes, from product orientation to mechanism to boundaries and next actions.
- Claims backed by proof or softened: yes; no performance claims are made.
- Objections answered where they arise: yes, especially optional runtime and no result-display boundaries.
- Core interactions present: yes.
- Journey endpoints clear: yes.
- Placeholder/demo-only surfaces removed or marked out of scope: yes.
- Required states covered: normal and search empty state; no live data states required.

## Approval Record

- Product Surface revision: 1
- Decision: approved
- Owner feedback or waiver scope: owner approved implementation after six onboarding rounds.
- Date: 2026-09-01
- Next phase unlocked: local Next.js portal implementation.

## Collaboration Record

- Delegation available: available in environment, but not used.
- Required collaboration/runtime interface: current session implementation.
- Proposed delegated scope: none; owner approved direct implementation.
- Owner decision: waived by proceeding with single-agent implementation.
- Fallback: current-session work.
