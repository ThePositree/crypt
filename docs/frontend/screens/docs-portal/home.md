# Home

## Purpose

Introduce `crypt docs` as a curated Russian documentation portal and present
both the guided route and the architecture/reference route.

## User Goals

- Understand what the portal is and what it intentionally excludes.
- Choose a learning path or jump to a subsystem.

## Primary Action

Start the guided route or open the framework map.

## Information Hierarchy

- First viewport: name, audience, scope, risk badges, guided route, reference
  route.
- Framework map: atlas of required sections.
- Browse/filter area: major areas and maturity/risk labels.
- Next-reading block.

## Components

- Documentation shell, header search, theme toggle, left navigation, framework
  atlas, route cards, filter chips, maturity/risk badges, next-reading cards.

## Interaction Inventory

- Guided route card opens Overview.
- Reference route card opens Architecture.
- Filter chips reduce visible page cards by area.
- Header search and `Cmd/Ctrl+K` open the global search overlay.
- Theme toggle switches between approved light and dark palettes.

## Content And Capability Contract

- Required coverage: all first-release pages are discoverable from Home.
- Source proof: owner onboarding, README, current state, context routes.
- Boundaries: no runtime dashboard, no metrics, no live state.

## Data Sources And Trust Boundaries

- Curated source content only; no markdown rendering pipeline and no CMS.
- Source material may inform copy, but production content is authored in Next
  source files.
- The page must not imply that it can read OKX, Railway, local logs, or
  current runtime configuration.

## States

- Default Home.
- Filtered page-card list.
- Search overlay opened from header.
- Dark theme fixture.
- Mobile drawer fixture.

## Responsive Behavior

- Desktop keeps left navigation and right table of contents visible.
- Tablet removes the right table of contents.
- Mobile replaces left navigation with the drawer trigger and stacks route
  cards, atlas islands, and page cards.

## Accessibility Requirements

- First focusable route after header is the guided route card.
- Filter buttons expose the selected state visually and programmatically in
  production.
- Atlas links have text labels; mascot/abstract visuals are decorative.

## Acceptance Criteria

- Reader can identify the portal scope and exclusions before opening a
  subsystem page.
- Every first-release page is reachable from Home.
- No live balances, positions, PnL, command output, or generated repository
  markdown are displayed.

## Related Flows And Wireframes

- Wireframe: `docs/frontend/wireframes/docs-portal/index.html?page=home`
