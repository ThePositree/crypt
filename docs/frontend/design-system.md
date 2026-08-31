# Design System

Status: initial static site established.
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

## Static Site Rules

- typography: system sans stack; headings use compact line-height and no
  negative letter spacing.
- spacing: section padding is broad on desktop and reduced on mobile.
- colors and semantic color usage: light paper background, white panels,
  graphite primary actions, blue navigation/proof accents, green read-only
  status, dark execution band.
- surfaces: full-width page sections; cards only for repeated items and the
  framed strategy preview panel.
- borders: 1px cool gray lines for structure.
- radii: 8px maximum for cards and controls, except pill status labels.
- shadows and elevation: one soft shadow for the primary preview panel.
- density: technical and scannable; no oversized marketing-only sections after
  the hero.
- iconography: none in the initial static site.
- motion: none.
- forms: not in scope.
- tables: not in scope.
- charts: canvas visual only; label illustrative data clearly.
- responsive principles: collapse from multi-column to two-column and then
  single-column layouts; keep code blocks horizontally scrollable.
- semantic states: read-only status and explicit runtime-truth copy.

## Validation

- Viewports checked: 1440x1000 desktop and 390x844 mobile on 2026-08-31.
- Components/screens sampled: site homepage.
- Accessibility checks: semantic landmarks and accessible snapshot inspected;
  visible focus states and contrast reviewed visually.
- Known exceptions: no automated accessibility tooling is configured.
