# Visual Direction Boards - crypt docs

Date: 2026-09-02
Status: pending Visual Direction Approval
Tool: built-in image generation
Product Surface: `docs/frontend/product-surface-model.md` revision 1

These raster boards explore visual directions for the curated Russian
`crypt docs` portal. They are direction studies, not production UI contracts.
Production implementation must wait for the approved direction, finalized
Design Identity and Design System, HTML wireframes, screen contracts,
independent contract review, and Final Implementation Approval.

## Board Evidence Table

| Board | Artifact | Product hypothesis | Representative UI fragments | Component/state coverage | Inspection evidence | Strengths | Trade-offs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Soft Workshop Map | `board-01-soft-workshop-map.png` | Warm workshop docs with a clear framework shell and helper accents. | Desktop docs page, mobile page, left nav, breadcrumbs, search, command palette, right TOC, architecture map, next-reading cards. | Badges, buttons, tabs, accordion, command copy, empty search, success/error-style states. | Generated and visually inspected in-session; PNG 1536x1024. | Balanced, readable, strong docs shell, good component showcase. | Less distinctive than the atlas/workshop directions. |
| Pastel Control Room Notebook | `board-02-pastel-control-room-notebook.png` | Notebook-like technical control room for curated framework docs. | Data Pipeline page, mobile page, component gallery, dark theme preview, tabs, flow diagram, glossary chips. | Buttons, tabs, badges, accordion, chips, toggles, search results, empty/loading/error/success states. | Generated and visually inspected in-session; PNG 1672x941. | Strong documentation credibility, good state coverage, clear component thinking. | Purple accent needs constraint so the system does not drift into a purple-heavy palette. |
| System Islands Atlas | `board-03-system-islands-atlas.png` | The framework is an atlas of connected subsystem islands. | Home page with guided route and reference map, mobile shell, command palette, filters, TOC, risk labels, dark preview. | Navigation, filters, status/risk badges, accordion risk panel, search results, next-reading cards. | Generated and visually inspected in-session; PNG 1536x1024. | Most memorable, excellent dual learning/reference metaphor. | Must be kept as diagrams and navigation support, not a game-like map that slows reference reading. |
| Reference Desk Playground | `board-04-reference-desk-playground.png` | Dense framework reference desk with restrained playful details. | Backtester reference page, command palette, full-content search, glossary popover, mobile nav drawer, TOC, command snippet. | Tabs, accordion, copy button, popover, state matrix, navigation states, dark component sample. | Generated and visually inspected in-session; PNG 1672x941. | Closest to serious framework docs, strongest reference readability. | Less playful and less unique; mascots are subtle. |
| Lo-fi Signal Workshop | `board-05-lofi-signal-workshop.png` | Expressive playful workshop explaining decision flows step by step. | Home page, docs page, mobile page, command palette, empty search, dark sample, candles-to-execution flow diagram. | Buttons, badges, tabs, toggles, alerts, chips, progress steps, command palette, zero-result state. | Generated and visually inspected in-session; PNG 1536x1024. | Strong first-screen personality, excellent abstract mascot direction and flow explanation. | Needs careful density control so playful shapes do not crowd long reference pages. |

## Approval Question

Select one board as the primary direction, request a mix, or reject all and ask
for another iteration. A mixed direction should name which properties to keep
from each board.

## Current Recommendation

Use Board 5 as the primary emotional direction, mix in Board 4 for reference
density and Board 3 for architecture-map moments. This keeps the portal
distinctive while preserving framework-docs readability.
