# Static Portal Baseline

- Date: 2026-08-30
- Status: proposed

## Decision

Use a generated static site with semantic HTML, shared CSS, and small native
JavaScript modules as the implementation baseline. Keep authored content and
page metadata separate from generated output. Add a framework only if a
wireframe or content-authoring requirement proves that the zero-runtime
baseline is insufficient.

## Rationale

The portal is public, read-only, self-contained, and has no authenticated or
live-data surface. A static baseline minimizes security, maintenance, runtime,
and hosting constraints while supporting search, themes, diagrams, and all
approved journeys.

## Consequences

- No external client framework, remote font, analytics, or content API is
  required for the first release.
- Search uses a generated local index.
- Hosting remains portable across ordinary static hosts.
- This proposal becomes accepted when Wireframe Approval unlocks production
  implementation, unless the owner explicitly requests another stack.
