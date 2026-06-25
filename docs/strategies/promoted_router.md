# Promoted router strategy

Architecture: ADR-0043 and ADR-0044.

## Purpose

Represent an accepted router as a normal backtester strategy. The strategy
internally selects one nested archived strategy and emits that strategy's
signals through the standard `BaseStrategy.generate()` contract.

No router-specific backtest command or execution simulator is allowed.

## Inputs

The strategy receives normal `StrategyInput` OHLCV data and JSON parameters:

- router scoring and state-matching parameters;
- the frozen router `validation_start`;
- a persisted rolling-label/model-state artifact owned by the router;
- fallback strategy;
- nested strategy JSON paths.

Each nested strategy JSON is loaded through the normal strategy registry and
its normal backtest arguments.

The composite strategy exposes `progress`, enabled by default. For selected
`crypt_ensemble` signal generators it overrides the archived standalone
`progress: false` setting so interactive full-period runs show candle progress.
This affects display only; it does not launch a nested execution simulation.

The external backtester is an immutable boundary. It receives one ordinary
strategy object and knows nothing about `labels_path`, nested strategies, or
router state. `promoted_router` may load its own state exactly as an ML model
loads weights, but it must not instantiate `Backtester`, call `run_backtest`,
or reconstruct the real portfolio. It is one composite signal generator from
the backtester's point of view.

## Internal pipeline

The final runtime contract is specified in
`docs/strategies/incremental_router_runtime.md`: one chronological
`on_closed_bar` state machine shared by historical replay and live execution.

The rolling-label artifact is versioned router state, analogous to model
weights rather than market input required by the backtester. The evaluator
must retain the `label_end <= decision_timestamp` gate. In production this
state is updated by the paper/shadow-performance pipeline and persisted
between process restarts. Missing state is a router initialization error; the
strategy must never silently launch historical backtests to rebuild it.

`validation_start` is part of the frozen model state, not a reporting option.
It defines when the stateful hold/switch machine starts. Before that timestamp
historical replay uses the configured fallback strategy.

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

After the final label timestamp, the last causal selection is carried forward
and its staleness must be visible in diagnostics. A malformed nested config,
missing label artifact, or unknown selected strategy is a hard error.

## Outputs

The normal backtester outputs are unchanged:

- `trades.csv`;
- metrics and equity reports;
- signal diagnostics.

Trade metadata includes `router_id` and `selected_strategy`.

## Initial implementation

`router_v2_2687609`:

- validation start: 2024-01-01;
- score: same-state median return minus drawdown;
- lookback: 180 days;
- state subset: trend + structure;
- exact state matching;
- minimum samples: 10;
- minimum hold: 60 days;
- switch margin: 0.5 points;
- fallback: `crypt_ensemble_h1_discovery_nr4_vwap_robust`;
- universe: all six archived strategies used by Router Catalog v2.
