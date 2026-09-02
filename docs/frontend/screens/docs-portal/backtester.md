# Backtester

## Purpose

Explain historical execution simulation, accounting boundaries, warmup versus
accounting windows, and regression checkpoints.

## Required Content

- Execution/accounting model.
- Closed-candle and no-look-ahead behavior.
- `--load-from` warmup versus `--from` accounting.
- Risk, fees, slippage, and replay boundaries at a conceptual level.
- CLI snippets without results.

## Sources

- `docs/backtester_regression.md`
- `docs/backtest.md`
- `docs/backtester/exit_geometry.md`
- `docs/execution/live_backtest_reconciliation_2026-07-28.md`

## Primary Action

Read the accounting model and copy a runnable backtester command shape.

## Information Hierarchy

- Backtester responsibility and removed legacy harness boundary.
- Closed-candle simulation model.
- Warmup versus accounting windows.
- Fees, slippage, risk, replay, and reconciliation caveats.
- CLI snippets without output.

## Components

- Breadcrumbs, no-look-ahead badges, source notice, accounting flow, tabs,
  accordions, backtester snippet, next-reading cards, right TOC.

## Interaction Inventory

- Accordions split model, accounting, and commands.
- Copy button copies the command only, never saved results.
- Search queries for warmup, replay, and no look-ahead route here.

## Data Sources And Trust Boundaries

- Curated from backtester regression, current backtest docs, exit geometry, and
  reconciliation docs.
- Result snapshots, PnL tables, and benchmark values are out of scope.
- Historical simulation is explained as behavior, not current money state.

## States

- Default model page.
- Accounting tab.
- Commands accordion expanded.
- Search overlay with backtester query.
- Dark theme.

## Responsive Behavior

- Flow steps wrap without changing order.
- Long command snippets scroll horizontally on narrow screens.

## Accessibility Requirements

- Warmup/accounting distinction is textual.
- Keyboard users can expand commands and copy snippets.
- TOC links target unique anchors.

## Acceptance Criteria

- Reader knows why warmup data is not the same as reported/accounted window.
- CLI snippets do not include result output.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=backtester`
