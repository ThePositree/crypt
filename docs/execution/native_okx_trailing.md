# Native OKX trailing-stop parity

## Scope

Trailing-enabled Core4 events use an OKX `move_order_stop` algo in live
execution and the same fixed activation/callback geometry in `ExecutionSim`.
The trigger price source is OKX last price, matching the H1 OHLCV source.

## Entry-known inputs

- confirmed average entry price;
- structural stop;
- side;
- filled contract count;
- `trail_activation_rrr`;
- `trail_distance_atr`;
- closed-candle ATR14 available at the entry bar open.

The ATR uses the same true-range definition as the backtester. It includes the
signal candle and no forming entry candle data.

## OKX order geometry

```text
stop_distance = abs(entry - structural_stop)
callbackSpread = entry_atr14 * trail_distance_atr
```

For a long:

```text
activePx = entry + stop_distance * trail_activation_rrr
```

For a short:

```text
activePx = entry - stop_distance * trail_activation_rrr
```

The live order is a reduce-only `move_order_stop` with `callbackSpread`,
`activePx`, `tdMode=isolated`, the position side, filled size, and a stable
client algo ID. The callback spread is fixed when the entry fills; it does not
change with later ATR values.

The structural market stop remains active as disaster protection.

## Fixed take-profit interaction

If the fixed take-profit lies strictly before the trailing activation price,
it remains attached and may close the trade before trailing activates. If the
activation price is equal to or before take-profit, no fixed take-profit is
placed because it could race the active trailing order.

## Backtester model

`ExecutionSim` stores the entry-time callback spread and activation price on
the position. After activation it tracks the best favorable price and triggers
after a reversal of exactly `callbackSpread`, matching OKX price-distance mode.

H1 OHLC does not reveal tick order inside one candle. The normal intrabar
policy remains explicit:

- `worst_case`: evaluate the adverse extreme against the stop that existed at
  bar open before applying the favorable extreme. A trailing stop activated or
  tightened during the bar can trigger only from a later bar. This avoids
  assuming an unobserved favorable-then-adverse path;
- `best_case`: activation/favorable extreme followed by callback in the same
  bar is allowed.

Gap-through exits fill at the adverse bar open.

This reproduces OKX order geometry but cannot reconstruct tick-exact ordering
from H1 candles. Exact live-trade verification therefore uses OKX algo history
and fills in addition to the H1 replay.

## Failure behavior

If a trailing-enabled event has no valid entry-known ATR, the entry is rejected.
If the entry fills but trailing placement fails, fixed structural protection is
kept, Telegram receives an execution error, state is persisted, and new entries
remain blocked until reconciliation sees the required trailing order.
