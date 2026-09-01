# Docs Portal Scope And Identity

- Date: 2026-09-01
- Status: approved
- Affected artifact revisions: Product Surface Model revision 1, Messaging revision 1, Design Identity revision 1, Design System revision 1

## Context

The repository had no established frontend product surface. The owner requested
a website, then clarified that it should be a large, local, manually curated
docs portal for crypto developers. It should explain how the code works, use
Next.js and Tailwind CSS, include full-content search and interactive diagrams,
and avoid live results or performance claims.

## Decision

Build a local Next.js App Router docs portal in the repository root. The portal
uses curated English page content, a pastel cartoon lo-fi developer desk visual
identity, full-content local search, a clickable architecture map, a pipeline
stepper, and module tabs. It covers Overview, Architecture, Pipeline, Research,
Backtester, Strategies, Candidate Archive, Live Execution, Risk Controls,
Operator Runbooks, and Known Risks.

## Consequences

The portal is a product documentation surface rather than a markdown renderer.
Content must be maintained deliberately as the codebase changes. Deployment
configuration remains out of scope until the owner requests it.

## Validation Or Revisit Trigger

Revisit when the owner requests deployment, real data, rendered markdown,
authentication, live runtime controls, or a different visual identity.
