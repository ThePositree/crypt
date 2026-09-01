# Design System

Status: proposed.
Revision: 1
Derived from Design Identity revision: 1.

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

- Viewports checked: pending rendered boards, wireframes, and implementation.
- Components/screens sampled: pending system map, navigation, search, guide
  step, glossary entry, version selector, and risk callout.
- Accessibility checks: pending contrast, keyboard navigation, focus states,
  semantic structure, and reduced-motion handling.
- Known exceptions: final tokens and component rules require Visual Direction
  Approval before production implementation.

## Proposed Rules

- Typography: friendly sans for interface text, readable mono for commands and
  sparse snippets, no viewport-width font scaling.
- Spacing: dense enough for docs scanning, with larger breathing room around
  diagrams and system-map clusters.
- Colors: light pastel base with distinct semantic zones; avoid a single-hue
  purple/blue or beige-only palette.
- Surfaces: soft paper-like page background, restrained panels, no nested cards.
- Borders: hand-drawn or slightly irregular accent treatment may be used on
  diagrams and mascots; text containers remain stable and readable.
- Radii: cards and panels stay at 8px or less unless the final visual board
  justifies a specific exception.
- Shadows and elevation: low-contrast, mostly functional separation.
- Density: docs pages prioritize scanning, table-of-contents, related links,
  and diagram labels over marketing whitespace.
- Iconography: simple line icons plus mascot illustrations; use standard icons
  for controls.
- Motion: small map highlighting and search state transitions; no motion that
  obscures reading.
- Forms: search is the primary form; it needs clear focus, loading, empty, and
  error states.
- Tables: use only where comparisons or inventories need them; keep mobile
  transformation explicit.
- Charts and diagrams: diagrams carry the explanation; code snippets support
  rather than dominate pages.
- Responsive principles: desktop emphasizes side navigation plus map/detail
  split; mobile emphasizes search, journey entry points, and one-column
  readable diagrams.
- Semantic states: loading, empty, error, disabled, partial-data, selected, and
  hover/focus states must be defined for search, map nodes, version selector,
  and copy buttons.
