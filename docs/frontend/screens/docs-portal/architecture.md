# Architecture

## Purpose

Show the atlas model of connected subsystems and the boundaries between them.

## Required Content

- Component map.
- Data and decision flow.
- Shared pure decision code principle.
- Runtime source-of-truth boundaries.
- Relation between backtest and live execution.

## Sources

- `docs/architecture.md`
- `docs/agent/context_routes.yml`
- `docs/state/current.yml`
- `README.md`

## Primary Action

Use the subsystem map to choose the next page or continue to Data Pipeline.

## Information Hierarchy

- High-level architecture statement.
- Component island map.
- Data and decision flow.
- Runtime/live-money boundary notes.
- Backtester versus live execution relationship.

## Components

- Breadcrumbs, source-boundary notice, atlas diagram, flow diagram, tabs,
  accordions, boundary snippet, next-reading cards, right TOC.

## Interaction Inventory

- Map links open subsystem pages.
- Tabs switch conceptual views.
- Accordions reveal component, flow, and boundary details.
- TOC anchors target distinct sections.

## Data Sources And Trust Boundaries

- Source material is `docs/architecture.md`, context routes, current state, and
  README.
- Runtime state is mentioned only as a boundary; the page must not read or
  display loaded env/config values.
- Live-money facts are framed as architecture responsibilities, not dashboard
  telemetry.

## States

- Default map.
- Active tab variants.
- Expanded accordion item.
- Search overlay opened from architecture query.
- Dark theme.

## Responsive Behavior

- Desktop can show map, content, and TOC simultaneously.
- Tablet hides TOC and keeps the map readable.
- Mobile stacks islands and keeps link labels visible without overlap.

## Accessibility Requirements

- Diagram information is duplicated in text.
- Map links have visible labels and focus states.
- The active TOC/section relationship is testable in production.

## Acceptance Criteria

- Reader can identify the responsibility of each subsystem island.
- Reader understands which boundaries are conceptual, runtime, and live-money.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=architecture`
