# Product Surface Model

Status: initial static site artifact requires owner review.
Revision: 1
Approval: review required before treating this surface as approved product
state.

Use this file for durable frontend product-surface understanding. It should be
filled before substantial new site/app work, major redesigns, or broad product
surfaces.

First discover product knowledge from sources such as `README.md`, project
docs, requirements, specs, current state, task context, or a canonical
`product.md`/`PRODUCT.md` when present. Ask the owner for product information
that remains unresolved after repository discovery.

## Product Knowledge Sources

- Primary: `README.md`.
- Supporting: `docs/state/current.yml`, `docs/tasks/IN_PROGRESS.md`,
  `docs/tasks/BACKLOG.md`.
- Contradictions or gaps: frontend memory previously said no active frontend;
  the new `site/` surface supersedes that placeholder for the static website.

## Scope Contract

- Outcome: first read-only website surface for `crypt`.
- In scope: static homepage, project positioning, research/execution overview,
  evidence links, and dry-run command.
- Explicitly out of scope: exchange account UI, order placement, live API reads,
  authentication, dashboards backed by runtime state, deployment, and frontend
  framework adoption.
- Assumptions: the first site should explain the existing project rather than
  sell a public SaaS product.
- Unresolved decisions: target audience for a polished public site, whether a
  future app should expose live state, and preferred deployment target.

## User Capabilities And Goals

- Primary goals: understand the product shape and reach canonical docs.
- Secondary goals: see live-money boundaries and find a safe dry-run command.

## Required Content And Features

- In scope: hero statement, illustrative strategy panel, research loop,
  execution boundary explanation, evidence links, runbook command.
- Explicitly out of scope: forms, charts with real account data, alerts,
  strategy controls, exchange mutations, and login.

## Messaging Requirements

- Starting user state: knows the repository exists but not what the website
  surface represents.
- Intended leaving state: understands `crypt` as a strategy research and live
  execution workbench, and knows where to inspect evidence.
- Main idea: research evidence and live execution share the same project
  context, but the site is read-only.
- Required proof: links to README, strategy benchmark, current state,
  backtester regression, live execution, and candidate archives.
- Objections to answer: whether the site controls money; whether performance
  claims are live data; where source of truth lives.
- Natural action: open README, benchmark, evidence docs, or dry-run command.
- Generic-copy risks: profit promises, generic AI trading language, and
  over-polished SaaS claims unsupported by repository evidence.

## User Journeys

- Actor and starting state: owner or agent opens the local static page.
- Goal: orient to the project and navigate to the right evidence.
- Steps and decisions: read hero, inspect research/execution sections, choose a
  canonical doc link or copy the dry-run shape.
- Error or recovery path: broken links are local relative paths; inspect docs
  directly from repository if opened outside repo root.
- Endpoint and feedback: user reaches the relevant markdown source or runbook.

## Information Architecture

- Pages or screens: one homepage at `site/index.html`.
- Navigation model: sticky in-page navigation plus relative links to docs.

## Sections And Components

- Section: overview hero.
- Purpose: explain the product and show an illustrative strategy console.
- Required interactions: README and benchmark links.

- Section: research.
- Purpose: summarize discovery, exact backtests, and benchmark reporting.
- Required interactions: none.

- Section: execution.
- Purpose: make live-money boundaries explicit.
- Required interactions: none.

- Section: evidence.
- Purpose: route users to canonical docs.
- Required interactions: local documentation links.

- Section: runbooks.
- Purpose: expose the dry-run execution command shape.
- Required interactions: horizontal scroll for long command on small screens.

## Completeness Review

- Primary goals covered: yes.
- Secondary goals covered: yes for the static site slice.
- Necessary content present: yes.
- Messaging trajectory present: yes.
- Claims backed by proof or softened: yes; no profit promises are made.
- Objections answered where they arise: yes; execution section states the site
  is read-only and runtime/OKX remain truth.
- Core interactions present: yes; local links and in-page navigation.
- Journey endpoints clear: yes.
- Placeholder/demo-only surfaces removed or marked out of scope: the canvas
  chart is explicitly illustrative.
- Required states covered: normal and overflow states covered; live data states
  are out of scope.

## Approval Record

- Product Surface revision: 1.
- Decision: implemented as a narrow static initial surface from owner request
  "делаем сайт".
- Owner feedback or waiver scope: owner review is required before treating this
  read-only implementation as an approved frontend surface.
- Date: 2026-08-31.
- Next phase unlocked: owner review and optional dynamic frontend planning.

## Collaboration Record

- Delegation available: yes, through Orca-managed workflows when materially
  useful.
- Required collaboration/runtime interface: Orca CLI/orchestration.
- Proposed delegated scope: skipped because the implemented slice is small,
  read-only, and independently reviewable in this session.
- Owner decision: not requested for this narrow slice.
- Fallback: single-agent implementation and local validation.
