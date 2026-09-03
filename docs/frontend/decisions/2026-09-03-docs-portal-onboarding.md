# crypt docs Portal Onboarding

- Date: 2026-09-03
- Status: proposed, contract-reviewed
- Affected artifact revisions: Product Surface Model revision 1, Messaging
  revision 1, Design Identity revision 1, Frontend Context proposed stack

## Context

The owner requested a site for `crypt` and answered the first D3 onboarding
round. The requested surface is not a runtime dashboard. It is a large Russian
documentation portal for a developer-crypto trader, written as framework-style
documentation for how the codebase works.

## Decision

Use Next.js plus Tailwind CSS for the first production frontend application.
Build `crypt docs` as a documentation portal with guided learning and
reference navigation, full-content search, command palette, breadcrumbs, left
navigation, right desktop table of contents, light and dark themes, diagrams,
copyable CLI snippets, maturity labels, risk markers, next-reading blocks, and
playful lo-fi abstract mascots.

Do not show live execution results, balances, positions, or current production
state. Do not provide live trading controls. Keep all content directly in
source-controlled frontend code or content modules; no CMS is planned.

Allowed snippets are CLI commands, shell environment examples, YAML/JSON
configuration examples, route/content data shapes, and conceptual type
signatures. Quoting implementation bodies from `src/`, including function or
class bodies, is outside the portal contract.

Production diagrams should be React SVG components styled through Tailwind and
CSS variables for light/dark support. The visual language may imitate
hand-drawn lo-fi diagrams, but the implementation contract is not Mermaid,
canvas-only, or raster-only diagrams by default.

## Consequences

The work remains D3 and must pass the repository frontend gates before
production implementation: Product Surface Approval, Visual Direction
Approval, selected visual translation, UI component showcase, wireframes,
screen contracts, independent contract review, Final Implementation Approval,
separate implementation context, and independent QA unless the owner grants a
scoped `FRONTEND WAIVER:`.

## Validation Or Revisit Trigger

Revisit if the owner changes the portal audience, asks for live data or
trading controls, changes the stack, removes search, or narrows the first
release below the promised full documentation scope.

Independent contract review:

- Initial review: Orca native `cursor` worker `ctx_211d42ca5202`, verdict
  `approve-with-fixes`.
- Re-review: Orca native `cursor` worker `ctx_8c234d5de26d`, verdict `PASS`.
