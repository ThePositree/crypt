# Documentation Portal Product Surface Revision 1

- Date: 2026-09-01
- Status: approved
- Affected artifact revisions: `docs/frontend/product-surface-model.md`
  revision 1; `docs/frontend/messaging.md` revision 1.

## Context

The owner requested a large public documentation portal under `site/` that
fully explains how the `crypt` codebase works. The portal is not a Markdown
renderer and must not display runtime execution results.

## Decision

Approve Product Surface Model revision 1 as the scope for the documentation
portal. The approved surface is a manually curated Russian Next + Tailwind docs
portal with top-level sections for overview, architecture, data, strategies,
backtester, live execution, operations, and glossary.

The portal includes server-side full-text search over curated content,
highlighted suggestions, a search results page, top navigation, left tree
navigation, home system map, signal journey block plus deep page, glossary
filtering, overview/deep-dive page modes, operational scenarios, recipes,
light and dark themes, and a noticeable cartoon lo-fi pastel visual direction
with multiple generated section-role characters.

Explicit exclusions remain: no auth, no runtime result dashboard, no live
account values, no direct Markdown rendering, no financial-advice disclaimer,
and no agent deployment.

## Consequences

The next frontend phase is visual direction exploration: five raster Visual
Direction Boards must be generated, inspected, and presented for owner
selection before final Design Identity and Design System are written.

Implementation is still blocked until later D3 gates complete or receive a
scoped owner waiver.

## Validation Or Revisit Trigger

Revisit this decision if the owner changes the portal audience, content
coverage, search scope, implementation stack, public/private boundary, or
visual direction.
