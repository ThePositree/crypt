# Data

- Route: `/docs/data`.
- Purpose: explain acquisition, closed-candle invariants, Parquet layout and recovery.
- Primary action: copy an appropriate backfill command.
- Hierarchy: sources; closed candles; timeframes; storage tree; backfill; idempotency;
  completeness checks; missing/partial/corrupt data behavior.
- Messaging: from `Which data is required?` to `I can prepare and verify it`.
- Content contract: current supported data types/endpoints and explicit availability limits.
- Discovery: file names, timeframes, `backfill`, flags, missing-data phrases.
- Interactions: data-type tabs, copy, file-layout disclosure, related links.
- States: complete, missing, partial, corrupt, exchange unavailable, copy failure.
- Responsive: storage tables scroll locally or become labeled rows.
- Accessibility: tables retain header relationships; status never color-only.
- Related: Quick Start, Architecture, Backtester, Troubleshooting.
- Acceptance: reader can identify required candles and recover from absence safely.
