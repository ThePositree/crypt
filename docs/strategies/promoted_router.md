# Promoted router strategy

## Purpose

Represent an accepted router as a normal backtester strategy. The strategy
internally selects one nested archived strategy and emits that strategy's
signals through the standard `BaseStrategy.generate()` contract.

No router-specific backtest command or execution simulator is allowed.

## Inputs

The strategy receives normal `StrategyInput` OHLCV data and JSON parameters:

- router scoring and state-matching parameters;
- rolling-label horizon and minimum history;
- fallback strategy;
- nested strategy JSON paths.

Each nested strategy JSON is loaded through the normal strategy registry and
its normal backtest arguments.

## Internal pipeline

1. Generate each nested strategy's signal frame.
2. Run an isolated donor backtest for each nested strategy over the supplied
   history.
3. Build daily 30-day strategy-performance labels from donor closed trades.
4. For each decision timestamp, score only labels where
   `label_end <= decision_timestamp`.
5. Apply the frozen router configuration.
6. Select exactly one nested strategy.
7. Emit only that strategy's signal and execution parameters.

Donor backtests are research state used to reconstruct historical router
decisions. They do not modify the outer portfolio. The outer standard
`ExecutionSim` is the only owner of real backtest capital and margin.

## Signal payload

The returned frame contains the standard columns:

- `signal`;
- `sl_price`;
- optional `entry_price`;
- `risk_percent`;
- `rrr`.

It may also contain generic per-signal execution overrides:

- `position_ttl_bars`;
- `trail_activation_rrr`;
- `trail_distance_atr`;
- `exit_geometry`;
- `tp_move_pct`;
- `structural_sl_mode`;
- `min_tp_move_pct`;
- `position_group`;
- `drain_on_group_change`.

`position_group` is the selected nested strategy id. With drain enabled, the
standard simulator rejects entries from a new group until every position from
the previous group closes naturally.

## Missing history

Before enough completed labels exist, the configured fallback strategy is
selected. There is no cash state.

If a nested strategy fails to generate signals or donor trades, it remains in
the universe with zero forward return where coverage exists. A malformed
nested config is a hard error.

## Outputs

The normal backtester outputs are unchanged:

- `trades.csv`;
- metrics and equity reports;
- signal diagnostics.

Trade metadata includes `router_id` and `selected_strategy`.

## Initial implementation

`router_v2_2687609`:

- score: same-state median return minus drawdown;
- lookback: 180 days;
- state subset: trend + structure;
- exact state matching;
- minimum samples: 10;
- minimum hold: 60 days;
- switch margin: 0.5 points;
- fallback: `crypt_ensemble_h1_discovery_nr4_vwap_robust`;
- universe: all six archived strategies used by Router Catalog v2.
