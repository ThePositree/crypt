# Site Home

## Purpose

Introduce `crypt` as a research workbench and live OKX execution module while
keeping the first website surface read-only and operationally safe.

## User Goals

- Understand what the project does.
- Find the main research, benchmark, execution, and runbook docs.
- See that live-money truth is not controlled by the website.

## Primary Action

Open the README or benchmark documentation.

## Information Hierarchy

1. Product identity and current scope.
2. Research loop.
3. Live execution boundaries.
4. Evidence and runbook links.

## Messaging Contract

- Starting user state: aware of the repository but not the frontend surface.
- Intended leaving state: understands that the site is a read-only project
  surface for research and live-execution context.
- Main idea: `crypt` connects strategy research, exact backtests, archived
  evidence, and live OKX execution.
- Required proof: links to README, benchmark, current state, regression, live
  execution, and candidate archive docs.
- Objections: "Can this place orders?" and "What is the source of truth?"
- Natural action: inspect README, benchmark, or runbook.
- Generic-copy risks: vague fintech claims, profit promises, and dashboards
  that imply live exchange control.

## Layout

Single static page with sticky navigation, a first-viewport product statement,
an illustrative canvas chart, dense research/execution sections, evidence
links, and a dry-run command.

## Data Sources And Trust Boundaries

- Repository docs and README provide copy and links.
- Canvas chart is illustrative and must not be treated as live performance.
- No exchange credentials, live API calls, or account mutation paths exist.

## States

- normal: page renders static content and chart.
- overflow: long command scrolls horizontally inside its code container.
- disabled: not applicable; there are no mutating controls.
- loading, empty, error, partial data: not applicable for this static slice.

## Responsive Behavior

Desktop uses two-column hero and multi-column sections. Tablet collapses main
layout to one column and cards to two columns. Mobile uses one column and
horizontal nav scrolling.

## Accessibility Requirements

Use semantic landmarks, visible focus states, sufficient contrast, alt-equivalent
labels for the canvas context, and keyboard-accessible links.

## Acceptance Criteria

- Observable behavior: `site/index.html` opens as a static page without a build
  step and displays the chart.
- Required states: normal responsive layouts and code overflow behavior.
- Rendered evidence: desktop and mobile screenshots or manual browser
  inspection. Completed on 2026-08-31 with
  `docs/frontend/reviews/site-home-2026-08-31-desktop.png` and
  `docs/frontend/reviews/site-home-2026-08-31-mobile.png`.
- Automated checks: no console errors in a local browser inspection; linked
  repository docs returned HTTP 200 from a local static server.
