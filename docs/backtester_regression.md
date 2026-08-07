# Backtester Regression Runbook

Use this runbook when the owner asks whether recent code changes broke the
backtester or production portfolio replay.

## Current Production Portfolio

| Field | Value |
|---|---|
| Symbol | `SOL-USDT-SWAP` |
| Strategy | `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json` |
| Version | `post-adr0058-tail-control-v6-drop-negative-v5-archive-2026-07-13` |
| Reference capital | `$10,000` for full replay |

## Full Replay Check

This is the current-code canonical full replay after the 2026-08-05
last-price stop versus mark-price liquidation priority fix. Older archived
snapshots are useful provenance, but they still include false liquidation
priority in some paths and should not be used as the current pass/fail target.

```bash
PYTHONPATH=src uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output results/backtester_regression_v6_full
```

Expected current-code metrics:

| Metric | Expected |
|---|---:|
| Final capital | `$1,237,819.83` |
| Total return | `12278.20%` |
| Total trades | `1544` |
| Closed/open trades | `1543 / 1` |
| Win rate | `35.13%` |
| Profit factor | `1.38` |
| Drawdown below start | `-0.53%` |
| Peak-to-trough drawdown | `-26.58%` |
| Exit mix | `1045 stop_loss / 409 take_profit / 45 ttl_expired / 44 trailing_stop / 1 open` |

Small differences from candle repair or a deliberate execution-model fix must
be explained in `CHANGELOG.md`. Unexplained changes in final capital, trade
count, exit mix, or drawdown are regressions until audited.

## Live Phase B Replay Check

This is the most useful live/backtest smoke because it covers the post-rollout
production period after the July risk-base reset and has a stable replay
contract.

```bash
PYTHONPATH=src uv run backtester run \
  --from 2026-07-18T00:00:00+00:00 \
  --to 2026-07-27T23:00:00+00:00 \
  --capital 102.34 \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output results/backtester_regression_live_phase_b
```

Expected current-code metrics:

| Metric | Expected |
|---|---:|
| Final capital | `$101.47` |
| Total PnL | `-$0.87` |
| Total return | `-0.85%` |
| Total trades | `17` |
| Closed/open trades | `16 / 1` |
| Win rate | `31.25%` |
| Profit factor | `0.93` |
| Drawdown below start | `-9.68%` |
| Peak-to-trough drawdown | `-9.68%` |
| Exit mix | `10 stop_loss / 4 take_profit / 2 ttl_expired / 1 open` |

The historical reconciliation note records closed replay PnL around
`-$0.85356390`; the CLI summary rounds the same run to about `-$0.87`.

## Live Phase A Caveat

The 2026-07-13 through 2026-07-17 live window is not a strict fresh-replay
regression target. The first three v6 live shorts are reconciled from archived
live signal payloads because later H1 candle repairs can change ATR-derived
levels.

Fresh phase-A command for context only:

```bash
PYTHONPATH=src uv run backtester run \
  --from 2026-07-13T00:00:00+00:00 \
  --to 2026-07-17T23:00:00+00:00 \
  --capital 104.77 \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output results/backtester_regression_live_phase_a
```

Current fresh replay context: `$111.61` final capital, `10` trades, and
`5 stop_loss / 4 take_profit / 1 open`. Do not fail a regression check solely
because this window differs from archived payload replay.

## Agent Notes

- Owner-facing commands need only `PYTHONPATH=src`; sandboxed agents should
  also set `UV_CACHE_DIR=/tmp/uv-cache` and `MPLCONFIGDIR=/tmp/matplotlib-cache`.
- Use the loaded runtime config as the live source of truth. If Railway
  `EXECUTION_STRATEGY_CONFIG` differs from the strategy above, stop and ask.
- Exact live cash reconciliation still belongs in
  `docs/execution/live_backtest_reconciliation_2026-07-28.md`.
