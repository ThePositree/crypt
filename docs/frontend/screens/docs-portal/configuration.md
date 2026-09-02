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

## Primary Action

Identify which config layer owns a setting before reading live execution docs.

## Information Hierarchy

- Runtime source-of-truth warning.
- Env versus repository defaults.
- Strategy JSON role.
- Symbols, dry-run, risk, and execution mode boundaries.
- Portal-as-documentation exclusion.

## Components

- Breadcrumbs, config/live-money badges, source notice, hierarchy diagram,
  tabs, accordions, env snippet, next-reading cards, right TOC.

## Interaction Inventory

- Config hierarchy sections expand independently.
- Env snippet copy button copies a non-secret example shape.
- Search routes env, strategy config, risk base, dry-run, and symbols here.

## Data Sources And Trust Boundaries

- Curated from README, current state, live execution spec, and `.env.example`.
- Secrets, current env values, and Railway variables are never displayed.
- The page contains no controls that mutate production configuration.

## States

- Default hierarchy page.
- Runtime truth warning visible.
- Env/JSON accordion variants.
- Search overlay with config query.
- Dark theme.

## Responsive Behavior

- Hierarchy diagram becomes a vertical stack on mobile.
- Secret-name lists remain readable without horizontal page overflow.

## Accessibility Requirements

- Warnings use text and icons, not color alone.
- Copyable snippets exclude secrets.
- Focus order follows hierarchy from source-of-truth to examples.

## Acceptance Criteria

- Reader understands that runtime config beats prose summaries for live
  execution.
- No page includes mutable controls for production configuration.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=configuration`
