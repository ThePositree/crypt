# Design System

Status: established for artifact design; production pending.
Revision: 2
Derived from Design Identity revision: 2.

Define technical visual rules only after Design Identity exists or after an
existing frontend application has clear conventions that can be inferred.

When established, give reusable values, composition rules, responsive behavior,
semantic meaning, and implementation references for:

- typography;
- spacing;
- colors and semantic color usage;
- surfaces;
- borders;
- radii;
- shadows and elevation;
- density;
- iconography;
- motion;
- forms;
- tables;
- charts;
- responsive principles;
- semantic states.

Reuse established values instead of inventing one-off visual values per task.

For every material rule, record one of:

- existing implementation evidence;
- approved visual/product rationale;
- accessibility or platform constraint.

## Validation

- Viewports checked: none yet; six viewport classes required after wireframes
  and implementation.
- Components/screens sampled: none yet.
- Accessibility checks: pending.
- Known exceptions: no production frontend exists yet.

## Established Direction

- Typography: readable Russian technical documentation with enough contrast for
  long reference pages. Use a sturdy sans-serif for UI and headings; optional
  handwritten accent text is allowed only in illustrations, labels, or small
  mascot notes.
- Spacing: framework-docs density for reading and scanning. Architecture maps
  receive more whitespace so subsystem "islands" and bridges remain legible.
- Colors and semantic color usage: pastel multi-hue atlas palette. Use
  seafoam for overview/stable areas, coral for strategy/decision attention,
  lemon for configuration and caution, powder blue for data/reference, soft
  green for operational health, and charcoal for text. Lilac may appear only
  as a small accent; avoid a purple-dominant theme.
- Surfaces: paper-like documentation canvas with soft panels for navigation,
  maps, callouts, search results, and next-reading regions. Do not use metric
  cards or live dashboard panels.
- Borders: subtle sketch-like borders and bridge lines may support maps and
  diagrams when readability remains high.
- Radii: 8px or less for content cards and controls. Mascot/artwork shapes can
  be softer because they are not reusable controls.
- Shadows and elevation: soft paper elevation only; no glossy SaaS or finance
  terminal treatment.
- Density: home and architecture pages can be more visual; subsystem reference
  pages use Board 4-style density with Board 3 color/identity.
- Iconography: implementation should use a maintained icon library for
  commands and controls. Abstract guide markers are decorative/helpers, not
  command icons.
- Motion: small purposeful transitions for search, command palette, map
  expansion, navigation drawers, theme changes, tabs, and accordions;
  reduced-motion support is required.
- Forms: search-first controls with keyboard support and visible focus.
- Tables: allowed for reference matrices, maturity/risk labels, and glossary
  structure; forbidden for runtime result tables.
- Charts: explanatory architecture/data-flow diagrams only. Do not show
  current PnL, balances, live positions, or backtest output charts.
- Responsive principles: left navigation collapses into a mobile drawer, page
  TOC becomes a compact on-page region, atlas maps become stacked subsystem
  cards, and search remains globally reachable.
- Semantic states: normal, hover/focus, selected, loading, empty, error,
  disabled, overflow, and partial-content states must be represented in
  wireframes and implementation QA where applicable.
