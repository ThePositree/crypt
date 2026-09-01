# Design System

Status: established.
Revision: 1
Derived from Design Identity revision: 1.

The first portal implementation establishes the following reusable rules.

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

- Viewports checked: pending rendered review record.
- Components/screens sampled: portal shell, home, curated page, search dialog, architecture map, pipeline stepper, module tabs.
- Accessibility checks: pending rendered review record.
- Known exceptions: no dark theme.

## Rules

- Typography: rounded system UI for general copy; monospace only for terminal-like fragments.
- Spacing: use roomy sections with compact text blocks; cards should preserve readable line length on mobile and desktop.
- Colors: pastel paper, mint, sky, lavender, rose, and lemon accents over dark ink; avoid market red/green as performance signals.
- Surfaces: light paper backgrounds with visible ink borders and simple offset shadows.
- Borders: 2px dark ink borders are the primary structural motif.
- Radii: 12px to 24px for illustrated portal surfaces; avoid pill-heavy generic SaaS composition except for small tags.
- Shadows: hard offset shadows only, using translucent ink.
- Density: documentation can be dense, but every page starts with a summary and clear next routes.
- Iconography: lucide icons inside controls and navigation.
- Motion: small hover translation only; no heavy animation in documentation content.
- Forms: search input uses explicit focus ring, close button, results, and empty state.
- Charts: decorative chart-paper motifs only; no result charts in the portal.
- Responsive principles: mobile and desktop are first-class; navigation stacks on mobile and becomes sticky side navigation on desktop.
- Semantic states: missing search results use an explicit empty state; live data states are out of scope because no live data is shown.
