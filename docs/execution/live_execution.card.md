# Live Execution Card

Full source: `docs/execution/live_execution.md`

Use this card for live OKX execution, state, sync, order placement, and
runtime behavior.

Truth hierarchy:

- Loaded runtime env/config, especially `EXECUTION_STRATEGY_CONFIG`.
- OKX fills, orders, positions, fees, account equity.
- Durable execution state and Railway logs.
- Prose docs only after runtime truth is known.

Safety reminders:

- Production runtime must not ask interactive questions.
- Dirty exchange sync blocks live orders.
- Missing data must fail fast, auto-bootstrap through configured paths, or
  produce explicit operator errors.
- Telegram notification labels are not money truth.

Read the full live execution doc and deploy runbook before changing live-money
behavior.
