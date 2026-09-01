# Design Identity

Status: approved.
Revision: 1
Approval source: owner selected Visual Direction Board 2 on 2026-09-01.

The portal identity is based on `Storybook Control Room`, with secondary
support from the other generated boards where they solve specific product
needs.

## Core Feeling

- Decision: a cozy technical control room that turns a complex crypto strategy
  codebase into an explorable system.
- Evidence: owner requested a public Russian documentation portal with
  noticeable cartoon lo-fi style, multiple permanent characters, system maps,
  signal journey, search, and framework-like depth.

## Personality

- Decision: friendly, curious, precise, and operationally calm.
- Evidence: the portal must teach code behavior deeply while avoiding runtime
  result dashboards, marketing hype, and raw Markdown rendering.

## Desired Perception

- Decision: readers should feel that `crypt` is understandable, structured,
  extensible, and serious enough for engineering work despite the warm visual
  layer.
- Evidence: owner requested documentation like a framework, with overview and
  deep-dive modes, recipes, glossary, operations pages, and production-grade
  search.

## Visual Tension

- Decision: storybook warmth plus framework-docs utility.
- Evidence: board 2 was selected for the storybook/control-room metaphor;
  board 3 remains a secondary reference for serious article density.

## Signature Traits

- Trait: subsystem rooms.
- Product purpose: major areas can be shown as connected stations so readers
  understand system relationships before reading details.

- Trait: section-role characters.
- Product purpose: recurring characters identify documentation roles such as
  architecture guide, signal courier, operator, strategy logic guide, glossary
  librarian, and extension engineer.

- Trait: visible signal path.
- Product purpose: the path from market data to decision and optional execution
  stays visible as a teaching device across home, journey, and related pages.

- Trait: warm paper and soft panel texture.
- Product purpose: gives the portal a lo-fi handcrafted feel while preserving
  readable documentation surfaces.

- Trait: component states shown plainly.
- Product purpose: interactions such as search, accordions, tabs, selected map
  nodes, empty results, focus, and dark mode must be obvious and teachable.

## Anti-Identity

- Avoid: trading-dashboard aesthetics, profit charts, live account widgets, and
  financial-product marketing.
- Reason: the approved portal explains code behavior and must not display
  runtime execution results.

- Avoid: raw Markdown-reader appearance.
- Reason: the owner requires separately curated pages rather than Markdown
  rendering.

- Avoid: excessive illustration that squeezes article reading.
- Reason: framework-style learning and searchability require dense, clear text
  hierarchy.

- Avoid: single-hue pastel, dominant dark blue/slate, dominant beige/brown, or
  purple-gradient themes.
- Reason: repo frontend guidance requires balanced palettes and warns against
  one-note themes.

## Implementation-Dependent Exploration Record

- Execution context and methods used: five raster UI mockup boards generated
  with the built-in image generation tool and saved under
  `docs/frontend/visual-references/positive/`.
- Date: 2026-09-01
- Approved Visual Direction revision: `Storybook Control Room`, board 2.
- Known limitations: generated boards are direction studies; final UI must use
  deterministic Next + Tailwind components, curated Russian copy, accessible
  contrast, responsive behavior, and verified interactions.
