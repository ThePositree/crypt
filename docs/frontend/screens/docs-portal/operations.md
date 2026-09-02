# Operations

## Purpose

Explain operational practices: Railway context, preflight checks, incident
response, logging, observability, and task/changelog hygiene.

## Required Content

- Railway deployment/runbook boundaries.
- Preflight and volume/state risk.
- Incident response sequence.
- Telegram/notification role.
- Long-command progress expectations.
- Task and changelog hygiene.

## Sources

- `docs/deploy/railway.md`
- `docs/operations/observability.md`
- `docs/operations/telegram_commands.md`
- `docs/agent/operating_rules.md`
- `AGENTS.md`

## Primary Action

Open the incident-response flow or Railway/runbook boundary.

## Information Hierarchy

- Railway deployment and runbook boundaries.
- Preflight and volume/state risk.
- Incident response sequence.
- Notification and observability roles.
- Long-command progress and docs/task hygiene.

## Components

- Breadcrumbs, operational/risk badges, source notice, runbook flow, tabs,
  accordions, Railway start-command snippet, next-reading cards, right TOC.

## Interaction Inventory

- Runbook sections expand independently.
- Snippet copy button copies a start-command shape only.
- Search routes Railway, preflight, incident response, logs, Telegram, and
  observability here.

## Data Sources And Trust Boundaries

- Curated from Railway, observability, Telegram command, operating rules, and
  AGENTS docs.
- The portal must not query Railway, mutate deployment settings, or show live
  logs.
- External state must be verified outside the portal before live changes.

## States

- Default operations page.
- Incident response accordion expanded.
- Preflight warning state.
- Search overlay with Railway/preflight query.
- Dark theme.

## Responsive Behavior

- Runbook flow becomes a vertical checklist on mobile.
- Warning blocks remain near their related action context.

## Accessibility Requirements

- Incident sequence is ordered in text.
- Warnings are not color-only.
- Keyboard users can navigate runbook sections and copy snippets.

## Acceptance Criteria

- Reader knows where operational truth comes from.
- Reader understands what requires external verification before live changes.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=operations`
