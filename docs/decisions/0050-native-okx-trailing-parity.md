# ADR-0050: Native OKX trailing-stop parity

- **Status**: accepted
- **Date**: 2026-06-29
- **Supersedes**: the dynamic per-bar ATR trailing interpretation in live Core4

## Context

The accepted causal v3 portfolio emits trailing parameters, but live execution
only placed fixed SL/TP orders. The historical simulator also recalculated the
ATR distance on every later H1 candle, while OKX `move_order_stop` accepts one
fixed callback ratio or price spread at order placement. Those behaviors cannot
produce auditable live/backtest parity.

The owner explicitly chose to retain trailing and rerun the full backtest after
the liquidation correction.

## Decision

- Live execution places a native OKX `move_order_stop`.
- The activation price is entry plus/minus structural risk distance multiplied
  by `trail_activation_rrr`.
- The callback uses OKX `callbackSpread`, fixed from entry-known closed ATR14
  multiplied by `trail_distance_atr`.
- Backtester positions store and use those same fixed values.
- A fixed TP is placed only when it lies strictly before activation.
- The structural stop remains active.
- H1 intrabar ambiguity stays governed by the declared best/worst-case policy;
  exact trade replay additionally checks exchange algo history and fills.

## Consequences

- All previous trailing-enabled v3 results are invalid and must be rerun.
- Live positions gain a separate stable trailing client ID and exchange algo ID.
- Missing ATR or missing native trailing protection blocks entry/reconciliation.

## References

- `docs/execution/native_okx_trailing.md`
- `docs/execution/liquidation_safe_leverage.md`
- OKX API v5 `POST /api/v5/trade/order-algo`
