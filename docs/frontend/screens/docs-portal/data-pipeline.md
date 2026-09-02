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

## Primary Action

Understand the closed-candle path, then continue to Strategies or Backtester.

## Information Hierarchy

- Market-data source and storage overview.
- Closed-candle invariant.
- Missing-data degradation behavior.
- Feature generation and consumer boundaries.

## Components

- Breadcrumbs, risk/no-look-ahead badges, source notice, flow diagram,
  accordion details, backfill snippet, next-reading cards, right TOC.

## Interaction Inventory

- Accordions separate sources, closed candles, and consumers.
- Snippet copy button copies the backfill command only.
- Search terms such as candles, backfill, and no look-ahead route here.

## Data Sources And Trust Boundaries

- Curated from data/backfill docs, regression docs, live signal cache docs, and
  tests as evidence.
- The page does not inspect local data files or exchange availability.
- Missing data behavior is documented as policy, not as current status.

## States

- Default page.
- Missing-data explanation expanded.
- Search overlay with a candle-related query.
- Dark theme.

## Responsive Behavior

- Desktop shows source notice, flow, details, and TOC in one scan path.
- Mobile stacks flow steps and prevents command text from resizing layout.

## Accessibility Requirements

- Flow order is readable as text.
- Command snippet is scrollable and copyable by keyboard.
- No color-only communication for risk or invariant badges.

## Acceptance Criteria

- Reader understands why missing data must degrade explicitly.
- Reader understands no-look-ahead implications for data and indicators.

## Wireframe

- `docs/frontend/wireframes/docs-portal/index.html?page=data-pipeline`
