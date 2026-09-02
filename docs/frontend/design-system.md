# Design System

Status: proposed seed.
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

- Viewports checked: none yet; six viewport classes required after wireframes
  and implementation.
- Components/screens sampled: none yet.
- Accessibility checks: pending.
- Known exceptions: no production frontend exists yet.

## Proposed Direction

- Typography: readable Russian technical documentation; final families pending
  visual boards and implementation approval.
- Spacing: dense enough for framework reference pages, with generous breathing
  room around diagrams and learning-path blocks.
- Colors and semantic color usage: pastel multi-hue palette with distinct
  semantic colors for stable, research, operational, archived, live-money,
  OKX, config, and no-look-ahead labels.
- Surfaces: soft lo-fi panels and documentation regions; avoid nested cards and
  dashboard metric cards.
- Borders: subtle hand-drawn or sketch-like accents may be used when they do
  not reduce readability.
- Radii: 8px or less for cards unless a specific component needs a softer
  illustrative treatment.
- Density: framework-docs density for content; playful accents are secondary.
- Iconography: use a maintained icon library in implementation when selected;
  abstract mascots are illustrative assets, not command icons.
- Motion: small, purposeful transitions for search, command palette, diagrams,
  and theme changes; reduced-motion support required.
- Forms: search-first controls with keyboard support.
- Tables: use for reference matrices, not runtime result tables.
- Charts: explanatory diagrams only; no live/backtest result visualization.
- Responsive principles: left navigation collapses on mobile, page TOC becomes
  secondary navigation, and search remains globally reachable.
- Semantic states: normal, hover/focus, selected, loading, empty, error,
  disabled, overflow, and partial-content states must be represented in
  wireframes and implementation QA where applicable.
