# Live/Backtest Reconciliation Card

Full source: `docs/execution/live_backtest_reconciliation_2026-07-28.md`

Use this card for July/August 2026 live/backtest reconciliation and phase
boundary context.

Current strict checkpoint:

- Phase C production boundary: Railway deploy `81a4e01` at
  `2026-07-29T12:12:04Z`.
- Accounting starts from first post-boundary OKX fill at
  `2026-07-29T13:00:35.321Z`.
- Replay signal/accounting boundary is `2026-07-29T12:00:00Z`.
- Replay warmup starts `2026-07-13T00:00:00Z`.
- Starting capital is `$83.09804366087424`.

Verdict snapshot:

- No critical production live money-path bug found in phase-C audit.
- `exchange_closed_unknown` fix commit `2704c83` was not deployed and affects
  notification/reconciliation classification, not known money behavior.
- Backtester parity requires `--load-from` warmup separate from `--from`.

Read the full reconciliation doc before changing final audit conclusions.
