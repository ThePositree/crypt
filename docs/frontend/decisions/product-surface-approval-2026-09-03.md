# Product Surface Approval

- Date: 2026-09-03
- Status: approved
- Affected artifact revisions:
  - `docs/frontend/product-surface-model.md` Revision 2
  - `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`
  - `docs/frontend/reviews/product-surface-contract-review-2026-09-03.md`
  - `docs/frontend/reviews/product-surface-contract-rereview-2026-09-03.md`

## Context

The owner requested a large Russian documentation portal for `crypt`, aimed at
developer-crypto-traders. The portal is a framework-style documentation site,
not a live dashboard. It must use Next.js and Tailwind CSS, include both a
guided learning route and reference navigation, provide full-content search,
show architecture and data-flow diagrams, include light and dark themes, and
avoid live account metrics, current positions, balances, PnL, and raw source
code quotations.

Independent factual research produced
`docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`. Revision 1
of the Product Surface Model received an independent contract review with one
blocking factual finding and several non-blocking fixes. Revision 2 resolved
those findings and passed independent re-review with zero blocking findings.

## Decision

The owner approved `docs/frontend/product-surface-model.md` Revision 2 in chat
with the message `апрув`.

Revision 2 is now the canonical frontend product surface for `crypt docs`.
Downstream messaging, design identity, design system, flows, wireframes, screen
contracts, implementation briefs, and QA briefs must preserve this approved
scope and its explicit prohibitions.

## Consequences

The approved surface unlocks the next D3 frontend phases:

- Messaging Identity and page-level Messaging Contracts.
- Design Identity and Design System for the playful lo-fi documentation portal.
- Flow, wireframe, and screen contract artifacts for the approved routes and
  global search.
- Final Implementation Approval before production Next.js/Tailwind code.

Any future change that adds live account data, runtime metrics, trading
actions, code quotation, external CMS, or unapproved product claims requires a
new owner decision and affected contract updates before implementation.

## Validation Or Revisit Trigger

Revisit this decision when:

- the portal scope changes from documentation to live monitoring or operation;
- the content language changes from Russian;
- the stack changes away from Next.js and Tailwind CSS;
- live account state, execution actions, or source-code quotation becomes
  requested scope;
- independent contract review finds a contradiction in the approved surface.
