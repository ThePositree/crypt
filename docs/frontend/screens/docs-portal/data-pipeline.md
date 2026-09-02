# Data Pipeline

## Purpose

Explain how market data is fetched, normalized, stored, repaired, and consumed
without assuming availability.

## Required Content

- Candle sources and storage.
- Closed-candle invariant.
- Missing-data behavior.
- Feature generation boundaries.
- Consumers: strategies, backtester, live signal runner.

## Sources

- `docs/backfill.md`
- `docs/backtester_regression.md`
- `docs/execution/live_signal_cache.md`
- `tests/data/`

## Acceptance Criteria

- Reader understands why missing data must degrade explicitly.
- Reader understands no-look-ahead implications for data and indicators.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=data-pipeline`

