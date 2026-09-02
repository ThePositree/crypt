# Configuration

## Purpose

Explain configuration hierarchy, runtime truth, environment variables, and
safe boundaries for live-money settings.

## Required Content

- `EXECUTION_STRATEGY_CONFIG` as runtime source of truth for active strategy.
- Environment versus repository defaults.
- Strategy JSON role.
- Symbols, dry-run, risk, and execution mode boundaries.
- Explicit warning that portal is not a control surface.

## Sources

- `README.md`
- `docs/state/current.yml`
- `docs/execution/live_execution.md`
- `.env.example`

## Acceptance Criteria

- Reader understands that runtime config beats prose summaries for live
  execution.
- No page includes mutable controls for production configuration.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=configuration`

