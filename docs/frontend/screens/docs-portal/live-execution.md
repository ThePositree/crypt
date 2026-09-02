# Live Execution

## Purpose

Explain live OKX execution architecture and operational guarantees without
showing current exchange/account state.

## Required Content

- Execution-only mode.
- Signal runner to order lifecycle.
- OKX as truth for fills, fees, positions, and account equity.
- Dry-run versus live-money boundary.
- Protection orders, reconciliation, and operator-visible failures.
- Explicit exclusion of current balances, positions, PnL, and runtime state.

## Sources

- `docs/execution/live_execution.md`
- `docs/execution/live_backtest_reconciliation_2026-07-28.md`
- `docs/execution/telegram_notifications.md`
- `docs/deploy/railway.md`

## Primary Action

Understand the execution-only boundary and continue to Operations for runbooks.

## Information Hierarchy

- Strong exclusion of dashboard behavior.
- Execution-only architecture.
- Signal runner to order lifecycle.
- OKX truth boundaries for fills, fees, positions, and account equity.
- Dry-run/live-money, protection orders, reconciliation, and failure handling.

## Components

- Breadcrumbs, live-money/OKX badges, source notice, order-lifecycle flow,
  tabs, accordions, execution-only dry-run snippet, next-reading cards, right
  TOC.

## Interaction Inventory

- Accordions reveal boundaries, order lifecycle, and protection details.
- Snippet copy button copies a dry-run shape, not live production credentials.
- Search routes OKX, dry-run, reconciliation, protection orders, and live money
  here.

## Data Sources And Trust Boundaries

- Curated from live execution, reconciliation, notification, and Railway docs.
- The page must not show current balances, positions, PnL, fills, account
  equity, logs, or live runtime state.
- OKX is described as the source of truth, but the portal does not query OKX.

## States

- Default architecture page.
- Boundary warning visible.
- Dry-run tab.
- Search overlay with OKX/live-money query.
- Dark theme.

## Responsive Behavior

- Order lifecycle stacks vertically on mobile.
- Live-money warnings stay above fold on mobile and desktop.

## Accessibility Requirements

- Dashboard exclusion is textually explicit.
- Warning badges have accessible labels in production.
- Keyboard users can reach snippet copy and next-reading links.

## Acceptance Criteria

- Reader understands architecture and risk boundaries.
- The page cannot be mistaken for a live trading dashboard.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=live-execution`
