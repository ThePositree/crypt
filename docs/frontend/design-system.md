# Design System

Status: approved direction translated into proposed production rules.
Revision: 1
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

- Viewports checked: visual source at 390 x 844, 1440 x 1000, and 1728 x 1117.
- Components/screens sampled: Pocket Field Lab overview board and all required
  documentation primitives.
- Accessibility checks: semantic HTML, visible focus, text alternatives,
  non-color state labels, reduced motion, and local overflow regions required.
- Known exceptions: final contrast and production typography metrics must be
  rechecked after implementation.

## Typography

- Editorial headings: Georgia, `Times New Roman`, serif. Use strong scale and
  compact line height; never use script or imitation handwriting for content.
- UI and prose: system sans stack. Body text targets 16-18 px and at least 1.55
  line height.
- Code and evidence labels: system monospace stack, never below 12 px.

## Spacing And Density

- Base unit: 4 px; primary steps: 8, 12, 16, 24, 32, 48, 64, and 80 px.
- Moderate content density. A specimen may be compact internally, but chapters
  require clear separation and a readable narrative order.
- Reading measure: 68-76 characters for prose; evidence regions may be wider.

## Color

- Light paper: `#f4eedf`; raised paper: `#fffaf0`; faded ink: `#24332f`;
  muted ink: `#64706a`; line: `#40514b`.
- Dusty mint: `#9fcdb8`; sand: `#e4cf9d`; coral: `#dc8f78`; faded blue:
  `#9ebfd0`; tape yellow: `#eadb86`.
- Dark paper: `#18221f`; raised dark paper: `#22302b`; primary text:
  `#edf2e9`; muted text: `#b8c5be`.
- Semantic states pair words/icons with color: success mint, warning sand,
  error coral, informational blue, disabled neutral ink.

## Surfaces And Geometry

- Use paper panels with 1-2 px ink borders, 6-10 px radii, and restrained
  offset shadows. Cards may rotate by at most one degree when it does not
  disturb alignment or scanning.
- Tape, stamps, index tabs, and dashed annotation lines are signature accents,
  not universal decoration.
- Avoid translucent glass, photoreal texture, deep blur, and dashboard grids.

## Icons And Illustration

- Prefer simple inline SVG with rounded strokes and explicit accessible names.
- The recurring human guide uses one stable name and role in production.
  Final name must be selected before copy freeze because exploration boards
  contain inconsistent names.
- Crypto cues should appear as candle, chain, coin, or market-data specimens,
  never exchange-style action controls.

## Motion

- Use 120-240 ms transitions for menus, overlays, and feedback. Longer ambient
  motion may illustrate data flow but cannot signal live activity.
- `prefers-reduced-motion: reduce` removes nonessential animation and smooth
  scrolling without hiding information.

## Controls And States

- Minimum target: 44 x 44 px. Focus rings must remain visible on every paper
  and ink surface.
- Search always provides normal, loading, empty, and error recovery language.
- Disabled controls state why they are unavailable. Documentation examples may
  never resemble enabled live-money actions.

## Tables And Charts

- Exact labels, units, dates, methodology, and accessible summaries are
  mandatory. Illustrative data is marked as such next to the title.
- Narrow screens use contained horizontal scrolling with a visible cue; the
  document itself must never acquire horizontal overflow.

## Responsive Principles

- Mobile below 600 px: one guided specimen trail, compact header, full-width
  primary actions, local overflow for wide evidence.
- Intermediate 600-999 px: one or two columns based on reading dependency.
- Desktop 1000-1599 px: asymmetric notebook spreads and persistent primary
  navigation where it remains readable.
- Wide 1600 px and above: increase margins and reading separation, not body
  density or line length.
