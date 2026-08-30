# Public Documentation Portal Onboarding

- Date: 2026-08-30
- Status: proposed
- Affected artifact revisions: Product Surface Model revision 1; preliminary
  Design Identity revision 1

## Context

The repository has no active frontend application or established product
surface. The owner requested a public site that explains how the code works.
A 30-question adaptive D3 onboarding established the audience, scope, content
model, visual intent, interaction priorities, and success criteria.

## Decision

Propose a self-contained English documentation portal for a broad public
audience. It teaches the research, backtesting, strategy, and live-execution
architecture in plain language through pseudocode, diagrams, accurate styled
charts, safe research/backtest CLI examples, global search, and a separate
history section.

The proposed identity is a playful lo-fi crypto laboratory in pastel light and
dark themes, led by a recurring named human researcher. Mobile and desktop are
equal priorities. Animation is welcome but must honor
`prefers-reduced-motion`. No visitor-facing operation may trade, manage an
account or strategy, deploy code, or control live execution.

## Consequences

- Product Surface Approval is required before visual exploration.
- Five rendered visual direction boards are required before the identity or
  design system becomes final.
- Public production evidence needs explicit dates, methodology, limitations,
  and non-guarantee context.
- Research and backtest examples may be executable; live-money commands are
  excluded.
- The portal cannot use stale `docs/architecture.md` claims as current truth.

## Validation Or Revisit Trigger

Revisit if the portal gains operational controls, authentication, runtime data,
GitHub dependency, a different audience, or a different primary product goal.
Any operational capability would require a separate Action Contract.
