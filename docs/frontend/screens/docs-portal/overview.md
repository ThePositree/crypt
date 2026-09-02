# Overview

## Purpose

Explain the high-level framework shape: research workbench plus live OKX
execution module for owner-selected strategies.

## Required Content

- What `crypt` is.
- What the portal explains.
- What the portal does not show.
- Main subsystem list and reading order.

## Sources

- `README.md`
- `docs/state/current.yml`
- `AGENTS.md`

## Primary Action

Continue to Architecture or open Search to jump into a subsystem.

## Information Hierarchy

- Page title and scope boundary.
- Framework contours: research, data, strategies, backtester, live execution,
  operations.
- Explicit exclusions: no live state and no command output.
- Next-reading cards.

## Components

- Breadcrumbs, badges, source-boundary notice, tabbed explanation panel,
  closed-candle flow, accordion details, snippet block, next-reading cards,
  right table of contents.

## Interaction Inventory

- Tabs switch between concept, flow, and config explanation.
- Accordions expand required content sections.
- Snippet copy button copies only the snippet text.
- TOC links scroll to sections.

## Data Sources And Trust Boundaries

- Copy is curated from README, current state, and AGENTS.
- Runtime configuration and exchange/account state are not read.
- Source code must not be quoted; only concepts and public module roles are
  described.

## States

- Default page.
- Tab variants.
- Accordion expanded/collapsed.
- Search overlay from header.
- Dark theme.

## Responsive Behavior

- Desktop shows left nav, main content, and right TOC.
- Tablet hides TOC.
- Mobile stacks all panels and uses drawer navigation.

## Accessibility Requirements

- Breadcrumbs, tabs, accordions, and copy controls are keyboard reachable.
- Active tab has a programmatic selected state in production.
- Snippet copy status is announced without moving focus in production.

## Acceptance Criteria

- Reader can explain the difference between research, backtester, strategy,
  data, live execution, and operations.
- Runtime-result boundaries are visible.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=overview`
