# Documentation Shell

## Purpose

Provide the persistent framework-docs environment for `crypt docs`: navigation,
search, theme, breadcrumbs, page TOC, mobile drawer, and next-reading context.

## User Goals

- Move between guided learning and reference pages.
- Search full curated content quickly.
- Understand page maturity and risk boundaries before reading details.

## Primary Action

Search the documentation or open the next relevant page.

## Information Hierarchy

1. Global brand and search.
2. Left navigation grouped by learning/reference/operations.
3. Page content.
4. Right on-page TOC on desktop.
5. Next-reading links.

## Components

- Header search and command palette trigger.
- Left navigation and mobile drawer.
- Breadcrumbs.
- Theme toggle.
- Page TOC.
- Status/risk badges.
- Tabs, accordions, copy buttons, filters, glossary popovers.

## Interaction Inventory

- Header search focus opens command palette.
- `Cmd/Ctrl+K` opens command palette.
- Escape closes overlays.
- Theme toggle switches light/dark.
- Mobile menu opens/closes drawer.
- Left nav and breadcrumbs navigate.
- TOC links scroll to page sections.
- Tabs switch local panels.
- Accordions expand/collapse.
- Copy buttons produce copied feedback.

## Responsive Behavior

- Below 640px: left navigation becomes a drawer; page TOC is hidden or moved
  into the page; atlas maps stack as cards.
- 640px and above: mobile drawer remains available; cards can form two-column
  groups.
- 768px and above: persistent left navigation can return.
- 1024px and above: right TOC appears when space allows.
- 1280px and above: full three-column documentation shell.
- 1536px and above: content width remains constrained; maps gain whitespace,
  not larger unreadable text.

## Accessibility Requirements

- Keyboard reachable command palette, drawer, tabs, accordions, and copy
  buttons.
- Visible focus states.
- Contrast-safe semantic labels in light and dark themes.
- Reduced-motion support for production implementation.

## Related Flows And Wireframes

- Flow: `docs/frontend/flows/docs-portal-navigation.md`
- Wireframe: `docs/frontend/wireframes/docs-portal/index.html`

