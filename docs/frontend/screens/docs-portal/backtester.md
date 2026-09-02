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

## Acceptance Criteria

- Reader knows why warmup data is not the same as reported/accounted window.
- CLI snippets do not include result output.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=backtester`

