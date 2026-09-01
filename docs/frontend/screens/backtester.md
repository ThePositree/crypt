# Backtester

- Route: `/docs/backtester`.
- Purpose: teach exact replay, warmup/accounting boundaries and artifact types.
- Primary action: copy a bounded `backtester run` command.
- Hierarchy: mental model; data loading; strategy registry; execution simulation;
  `--load-from` versus `--from`; fees/risk/exits; artifacts; validation failures.
- Messaging: from `How trustworthy is replay?` to `I know its contracts and limits`.
- Content contract: explain outputs without showing repository performance results.
- Discovery: commands, flags, artifact names, replay/parity and missing-candle terms.
- Interactions: command tabs, copy, artifact accordion, flow nodes, related links.
- States: successful artifact set, missing candles, invalid bounds/config,
  partial minute data, local overflow.
- Responsive: simulation pipeline becomes numbered vertical stages.
- Accessibility: artifact table headers and diagram alternative are complete.
- Related: Quick Start, Data, Strategies, Live Execution.
- Acceptance: reader can run bounded replay and explain every artifact category.
