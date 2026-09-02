# Strategies

## Purpose

Explain strategy lifecycle and how strategy definitions become signals and
execution decisions.

## Required Content

- Strategy archive concept.
- Candidate/research/promoted boundaries.
- Decision code and closed-candle signals.
- Portfolio composition and owner production override.
- Risk labels around production strategy selection.

## Sources

- `docs/strategy_benchmark.md`
- `docs/backtester/candidate_archive.md`
- `docs/archive/candidates/README.md`
- `docs/discovery/direct_signal_search_v3.md`
- `docs/strategies/incremental_router_runtime.md`

## Primary Action

Choose between the lifecycle explanation and the active-config boundary.

## Information Hierarchy

- Strategy lifecycle from candidate to archived/promoted strategy.
- Decision-code and closed-candle signal rules.
- Portfolio and owner override boundaries.
- Risk labels around production selection.

## Components

- Breadcrumbs, research/config badges, source notice, lifecycle diagram,
  tabs, accordions, strategy-config snippet, next-reading cards, right TOC.

## Interaction Inventory

- Lifecycle and archive sections expand independently.
- Strategy config snippet is copyable as a shape, not as a runnable production
  mutation.
- Search routes candidate, archive, router, and risk-base terms here.

## Data Sources And Trust Boundaries

- Curated from benchmark, candidate archive, discovery, and runtime strategy
  docs.
- Performance values and result tables are excluded.
- Production strategy selection is described as owner-controlled and loaded
  from runtime config.

## States

- Default lifecycle page.
- Active config tab.
- Archive accordion expanded.
- Search overlay with strategy/candidate queries.
- Dark theme.

## Responsive Behavior

- Lifecycle diagram collapses into a vertical path on mobile.
- Cards and snippets keep stable dimensions across labels.

## Accessibility Requirements

- Lifecycle steps are available as text.
- Risk labels include text, not only color.
- Snippet copy feedback is announced in production.

## Acceptance Criteria

- Reader can distinguish research candidates, archived strategies, and active
  runtime-selected production config.
- No performance/result claims are shown.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=strategies`
