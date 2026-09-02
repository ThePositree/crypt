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

## Acceptance Criteria

- Reader understands architecture and risk boundaries.
- The page cannot be mistaken for a live trading dashboard.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=live-execution`

