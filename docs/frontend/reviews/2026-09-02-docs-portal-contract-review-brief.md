# Frontend Lead Contract Review Brief - Docs Portal

Status: ready for independent read-only review
Date: 2026-09-02
Coordinator: current design/control session
Scope: proposed `crypt docs` Product Surface, Visual Direction, flow,
wireframe package, and screen contracts

## Reviewer Role

Act as an independent frontend lead inheriting this portal without access to
the authoring session's implicit context. This is a read-only contract review.
Do not edit files. Do not approve production implementation. Report findings
ordered by severity with file and line references where possible.

## Files To Read Completely

- `AGENTS.md`
- `docs/agent/context_routes.yml`
- `docs/state/current.yml`
- `docs/agent/frontend_design_subsystem.md`
- `docs/frontend/context.md`
- `docs/frontend/product-surface-model.md`
- `docs/frontend/messaging.md`
- `docs/frontend/design-identity.md`
- `docs/frontend/design-system.md`
- `docs/frontend/visual-references/interpretation.md`
- `docs/frontend/visual-references/boards/README.md`
- `docs/frontend/flows/docs-portal-navigation.md`
- `docs/frontend/wireframes/docs-portal/README.md`
- `docs/frontend/wireframes/docs-portal/index.html`
- every file under `docs/frontend/screens/docs-portal/`
- `docs/frontend/reviews/2026-09-02-docs-portal-wireframe-preflight.md`
- `docs/frontend/decisions/2026-09-02-docs-portal-product-direction.md`
- `docs/tasks/IN_PROGRESS.md`
- `CHANGELOG.md`

## Approved Decisions

- Product Surface revision 1 approved by owner on 2026-09-02 with "апрув".
- Visual Direction Board 3, `System Islands Atlas`, approved by owner on
  2026-09-02 with "3".
- Portal language: Russian.
- Audience: developer-crypto trader.
- Stack for production implementation: Next.js + Tailwind.
- Content model: manually curated source-authored pages, no CMS, no direct
  repository Markdown rendering.
- Out of scope: runtime command results, current live production state,
  balances, positions, PnL, and live/backtest result displays.

## Review Questions

1. Can a future implementer understand the approved product surface, visual
   direction, content boundaries, and interaction requirements without guessing?
2. Do the Product Surface, Messaging, Design Identity, Design System, flow,
   wireframe README, HTML wireframe, and screen contracts agree?
3. Does every approved first-release page have a screen contract and stable
   directly openable wireframe address?
4. Are the search/discovery requirements testable enough for implementation
   and QA?
5. Are live-money, OKX execution, configuration, and no-look-ahead boundaries
   explicit enough to prevent accidental dashboard/runtime-result behavior?
6. Do the wireframe interactions map to screen-contract interaction inventory?
7. Are responsive, accessibility, content coverage, and Text Inventory gaps
   clearly marked as pending rather than silently treated as done?
8. What would block Wireframe Approval or Final Implementation Approval?

## Severity Rules

- Critical: contradiction or missing requirement that could cause production
  implementation to build the wrong product, show forbidden runtime content,
  skip mandatory gates, or start production code before approval.
- High: missing page/state/interaction/source mapping that would make
  wireframe approval or implementation ambiguous.
- Medium: unclear wording, incomplete evidence, weak testability, or missing
  acceptance detail that should be fixed before implementation.
- Low: polish, naming, or organizational improvements that do not block the
  next gate.

## Required Output Format

Return:

1. Verdict: `block` or `pass-with-notes`.
2. Findings ordered by severity, each with file/line reference, issue, impact,
   and recommended fix.
3. Open questions or assumptions.
4. Specific statement whether Wireframe Approval can be requested after fixing
   the findings.

