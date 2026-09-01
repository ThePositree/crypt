# Design System

Status: established for wireframing and implementation planning.
Revision: 1.
Derived from Design Identity revision: 2.
Updated: 2026-09-01.

## Typography

- UI and article sans: `Inter Variable`, with system sans fallback. Use compact
  tracking for navigation and relaxed line-height for long Russian prose.
- Code: `JetBrains Mono`, with system monospace fallback.
- Display accent: the same sans family at heavier weight; handwritten lettering
  belongs only inside authored illustration, never essential interface text.
- Article measure: `68–76ch`; supporting lead text may use `55–64ch`.
- Evidence: Warm Workshop hierarchy and long-form documentation readability.

## Spacing And Layout

- Base spacing unit: `4px`; primary scale: `4, 8, 12, 16, 24, 32, 48, 64`.
- Desktop shell: left navigation `248–280px`, article fluid within measure,
  right contents `208–240px`; gutters never reduce article below readable width.
- Mobile shell: one content column; sidebar and contents become separate drawers.
- Section spacing is generous around concepts and compact within references.

## Color Semantics

- Canvas: near-black charcoal plum, approximately `#141218`.
- Raised surface: `#1C1921`; inset/code surface: `#111015`.
- Primary text: warm cream `#F2EDF1`; secondary text: muted mauve-gray.
- Primary/action: pastel lavender around `#A991E8` with contrast-adjusted text.
- Success/available: muted mint around `#86C6A1`.
- Warning/live boundary: warm peach/amber around `#D9A06F`.
- Error/blocked: muted coral around `#D87979`.
- Information: dusty blue around `#84A8CF`.
- Colors communicate semantics in combination with labels/icons, never alone.
- Final values require contrast measurement in implementation.

## Surfaces, Borders, Radii, Elevation

- Main surfaces are matte with subtle paper grain; no glassmorphism.
- Borders use low-contrast mauve-gray normally and semantic color when stateful.
- Radii: `6px` code/instrument nodes, `10px` controls, `14px` cards/panels,
  `18px` major illustrative frames. Avoid pill shapes except compact statuses.
- Elevation is sparse: one soft shadow for overlays and large floating panels;
  hierarchy otherwise comes from border, tone, and spacing.

## Density

- Articles: comfortable reading density with frequent diagrams and code.
- Reference inventories: compact but maintain `44px` minimum touch targets.
- Character art occupies at most one supporting region per article viewport and
  must collapse or move below content on narrow screens.

## Iconography And Illustration

- Interface icons: simple outlined technical symbols with consistent `1.5–2px`
  stroke; always paired with accessible names when actionable.
- Illustrations: hand-drawn lo-fi shading, limited pastel accents, warm local
  lighting, recognizable recurring characters.
- Diagrams: orthogonal connectors, labeled nodes, directional arrows, explicit
  sources of truth and failure boundaries; never decorative spaghetti lines.

## Motion

- Duration: `120–180ms` controls, `180–260ms` panels, up to `400ms` diagram
  emphasis. Use ease-out for entry and ease-in for exit.
- Allowed: focus/hover response, search opening, disclosure expansion, copied
  confirmation, and subtle diagram-path emphasis.
- Avoid: looping mascot motion near prose, parallax, cursor followers, and
  animated backgrounds.
- `prefers-reduced-motion` removes non-essential movement and uses instant or
  opacity-only state changes.

## Controls And States

- Buttons name the resulting action and retain visible focus rings.
- Search is a command-style field with `/` and `Ctrl/Cmd+K` hints.
- Tabs use roving keyboard focus and a persistent selected indicator.
- Accordions use native button semantics and announce expanded state.
- Code blocks provide language/context label, copy action, overflow containment,
  and success/failure feedback.
- Loading uses restrained skeletons or progress text; empty/error/blocked states
  explain cause and next action.

## Tables, Code, And Diagrams

- Tables keep headers visible when useful, use horizontal containment on narrow
  screens, and expose the same information in accessible markup.
- Code never wraps by default; horizontal scroll stays inside the block.
- Diagrams provide equivalent text descriptions and retain readable labels at
  every breakpoint; complex diagrams may transform into ordered vertical steps.

## Responsive Principles

- Narrow mobile `<640px`: one column, mobile header, drawers, vertical diagrams.
- Mobile-wide `>=640px`: more generous article gutter and two-column cards only
  when each card remains readable.
- Tablet `>=768px`: persistent compact left navigation may appear when space permits.
- Desktop `>=1024px`: full left navigation; right contents appears when article
  measure remains intact.
- Large desktop `>=1280px`: complete three-column docs shell.
- Wide desktop `>=1536px`: expand surrounding workshop atmosphere and gutters,
  not article line length.

## Accessibility

- WCAG AA contrast is the minimum for text and controls.
- Focus is never communicated by color alone and remains visible over every surface.
- Landmarks, skip link, heading order, accessible names, keyboard drawers,
  dialog focus trap/restore, reduced motion, and minimum targets are required.
- Character imagery uses useful alt text only when it communicates content;
  decorative art has empty alt text.

## Validation

- Viewports checked: direction board contains desktop and mobile compositions;
  six concrete classes remain required for wireframes and implementation.
- Components/screens sampled: docs shell, search, article, ToC, diagram, code,
  tabs, accordion, callout, cards, states, and navigation.
- Accessibility checks: directional only; contrast and behavior measurement pending.
- Known exceptions: raster board text is not production content.
