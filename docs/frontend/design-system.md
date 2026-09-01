# Design System

Status: approved.
Revision: 1
Derived from Design Identity revision: 1.

These rules define the first implementation target for the curated
documentation portal. Values are product constraints, not final Tailwind token
names; implementation may translate them into CSS variables and Tailwind theme
extensions.

## Typography

- Use a readable sans-serif UI face for navigation, controls, and article body.
- Use a slightly warmer rounded display face only for large section titles,
  map labels, and character cards.
- Do not scale font sizes with viewport width.
- Letter spacing is `0`.
- Body copy must remain dense enough for framework documentation: avoid
  oversized marketing-style paragraphs.
- Russian UI labels must be short, direct, and specific.

Evidence: owner approved framework-style documentation depth and board 2, while
repo frontend guidance requires text to fit and avoid hero-scale type inside
compact surfaces.

## Spacing

- Use compact docs spacing in navigation trees, search results, glossary rows,
  and article sections.
- Use larger breathing room only around the home map, signal journey, and
  character-led teaching panels.
- Prefer predictable vertical rhythm over decorative staggering.
- Component groups should align to a visible grid.

Evidence: selected board 2 uses a rich illustrated canvas; board 3 remains the
secondary reference for article density.

## Colors And Semantic Color Usage

- Base light theme: warm off-white paper background, graphite ink, soft cream
  panels.
- Base dark theme: dark ink background with warm low-contrast panels, not
  blue/slate-dominant.
- Accent set: dusty rose, sage, powder blue, pale apricot, muted teal, soft
  amber, and gentle lilac.
- Use multiple accent families across section roles; avoid a one-hue theme.
- Semantic states:
  - success: sage/green;
  - warning: soft amber;
  - error: coral/red;
  - info: powder blue;
  - selected: stronger accent fill with clear border and text contrast;
  - disabled: desaturated paper/ink with clear non-interactive affordance.

Evidence: board 2 palette and repo frontend guidance against one-note,
dominant purple-blue, beige/brown, and dark blue/slate palettes.

## Surfaces

- Primary docs surfaces are flat paper panels with subtle texture.
- Navigation, search, selected node drawers, and article cards may use bordered
  panels.
- Avoid cards inside cards. Repeated items, dialogs, and framed tools may use
  cards; page sections should not become decorative floating card stacks.
- Illustrations must live beside or inside useful UI structure, not replace
  content.

Evidence: selected board 2 uses station panels; repo frontend guidance forbids
nested-card layouts and decorative-only product surfaces.

## Borders, Radii, Shadows, And Elevation

- Default radius: 8px or less for UI components.
- Larger hand-drawn container corners are allowed only for map stations and
  illustration frames where they are part of the storybook identity.
- Borders should be visible enough to separate dense documentation regions.
- Use soft shadows sparingly for overlays, search modal, and selected node
  drawers.

Evidence: repo frontend guidance caps cards at 8px unless the design system
requires otherwise; the selected board uses framed station metaphors.

## Density

- Articles, navigation trees, glossary lists, search results, and recipes are
  dense and scan-friendly.
- Home map and signal journey are visually richer, but still keep primary
  actions and labels visible.
- Avoid landing-page hero composition. The first screen is the usable portal
  home with map, search, and navigation.

Evidence: owner requested documentation portal, not marketing site; repo
frontend guidance says apps/tools should show the actual usable experience.

## Iconography And Characters

- Use a consistent icon set for controls and navigation where available.
- Use generated raster characters as section-role helpers, not as decorative
  mascots without a content job.
- Character roles:
  - architecture guide;
  - data/source keeper;
  - strategy logic guide;
  - signal courier;
  - backtester inspector;
  - live execution operator;
  - glossary librarian;
  - extension engineer.
- Characters can introduce, clarify, or route content, but article claims must
  stand on text and diagrams.

Evidence: owner requested multiple permanent characters; selected board 2
shows subsystem stations with characters.

## Motion

- Motion should be subtle and explanatory: signal-path progress, selected node
  transitions, accordion/tabs changes, search suggestion entry, and theme
  transition.
- Respect reduced-motion preferences.
- Avoid decorative looping motion that distracts from reading.

Evidence: owner requested mini-animations and step-by-step mechanisms.

## Forms And Search

- Search is a primary portal control.
- Provide quick suggestions while typing, highlighted matches, keyboard
  navigation, loading state, zero-result state, error state, and a dedicated
  results page.
- Search results show section, title, snippet, highlighted term, and content
  type.
- Empty query should suggest learning routes and glossary entry points.

Evidence: approved Discovery Contract in Product Surface Model revision 1.

## Tables, Lists, And Glossary

- Prefer lists and definition rows over heavy tables for conceptual docs.
- Use tables only where comparison or matrix structure is clearer.
- Glossary supports alphabetical browsing, filters, search, related concepts,
  and links back into docs sections.

Evidence: owner approved glossary with search/filtering and relationships.

## Charts And Diagrams

- Do not show performance charts or runtime result dashboards.
- Use diagrams for architecture, data flow, signal journey, contracts,
  recipes, and state transitions.
- Diagrams should use human-readable labels first and technical names only when
  they improve understanding.

Evidence: owner selected human-friendly system map and explicitly excluded
execution results.

## Responsive Principles

- Top navigation remains available across desktop and mobile, with mobile
  condensation into a menu.
- Left tree navigation is persistent on desktop and becomes a drawer or
  section switcher on mobile.
- The home map becomes a scrollable/stacked station map on mobile with a
  selected-node drawer below it.
- Article pages keep heading, current section, search, and next actions
  reachable on mobile.
- Component dimensions should be stable to prevent layout shift on hover,
  selection, loading, and dynamic search states.

Evidence: six viewport classes are required by the frontend subsystem; visual
boards include desktop, mobile, and dark-mode previews.

## Semantic States

- Required states for implementation contracts: loading, normal, selected,
  hover, focus, disabled, empty, zero-result, error, overflow, and partial
  content.
- Focus states must be high-contrast and visible in both themes.
- Error states should explain what failed and provide a navigational fallback
  when search or content loading fails.

Evidence: Product Surface Model revision 1 requires production-style search and
state coverage.

## Validation

- Viewports checked: visual boards include desktop/mobile/dark-mode previews;
  production implementation must inspect all six viewport classes.
- Components/screens sampled: visual boards cover top navigation, left tree,
  search, map, selected node, signal journey, tabs, accordions, glossary
  filters, recipes, empty states, error states, focus states, and dark mode.
- Accessibility checks: pending implementation; required for focus, keyboard
  search, contrast, reading order, landmark structure, target sizes, and
  reduced motion.
- Known exceptions: generated visual-board text is not the source of truth for
  final copy; final Russian copy must be curated in code and screen contracts.
