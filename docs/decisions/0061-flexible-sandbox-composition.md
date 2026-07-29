# ADR-0061: Flexible sandbox composition

- Status: accepted
- Date: 2026-07-29

## Context

The owner wants strategy research and live operation to remain a flexible
sandbox: experiments should be assembled from parts, applied to a portfolio or
one donor, and removed without rewriting the core strategy. Hard-coded global
rules make comparisons and rollback unnecessarily risky.

## Decision

New trading components must expose an explicit configuration mount, support the
broadest useful scope plus narrower overrides where practical, and default to
no behavioral change when unmounted. Components that affect trading decisions
must share a pure decision function between backtest and runtime and emit
configuration/decision audit fields. Existing configuration keys may remain as
compatibility aliases, but new documentation uses the composable mount.

## Consequences

- Experiments can be enabled for all donors, a selected donor set, or no donors
  with a small config change.
- Rollback is a config operation when state/order migration is not required.
- Component contracts and audit output become part of acceptance criteria,
  increasing short-term implementation work but reducing hidden coupling.
- This is a design rule, not a requirement to force incompatible internals into
  one universal plugin interface.
