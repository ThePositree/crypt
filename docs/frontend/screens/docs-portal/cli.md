# CLI

## Purpose

Provide practical command snippets and explain command families without
showing command output.

## Required Content

- Research smoke command family.
- Backtester run and optimize concepts.
- Execution-only dry-run concept.
- Required environment prefixes such as `UV_CACHE_DIR=/tmp/uv-cache` for agent
  commands.
- Copyable snippets.

## Sources

- `README.md`
- `docs/cli.md`
- `docs/agent/operating_rules.md`

## Primary Action

Copy a command shape and follow the linked subsystem explanation.

## Information Hierarchy

- Available owner-facing command families.
- Backtester run/optimize/search concepts.
- Runtime/data module commands.
- Agent-safe environment prefix guidance.
- Explicit no-output boundary.

## Components

- Breadcrumbs, command badges, source notice, command-family tabs, accordions,
  copyable snippets, next-reading cards, right TOC.

## Interaction Inventory

- Command family tabs switch snippets and explanations.
- Copy buttons copy commands only.
- Search routes backtester run, optimize, search-signals, backfill, and
  execution-only here.

## Data Sources And Trust Boundaries

- Curated from README, CLI runbook, and operating rules.
- Command outputs, result tables, logs, and generated artifacts are never
  embedded.
- Commands are examples; production execution still depends on runtime env and
  external state.

## States

- Default command overview.
- Backtester/optimize/backfill/execution tabs.
- Copy success state.
- Search overlay with CLI query.
- Dark theme.

## Responsive Behavior

- Long commands scroll inside snippet containers.
- Command groups stack on mobile.

## Accessibility Requirements

- Snippets are keyboard copyable.
- Copy success has a non-color indication.
- Commands preserve readable monospace wrapping/scrolling.

## Acceptance Criteria

- Commands are useful as snippets.
- No command-result tables or output snapshots appear.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=cli`
