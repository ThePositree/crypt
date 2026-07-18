# Incremental router runtime

## Purpose

Provide one causal state machine for promoted-router historical replay and
future live execution.

The external backtester is an immutable adapter. It supplies historical closed
bars quickly and executes the one composite signal stream returned by the
router strategy. Live execution supplies one newly closed bar at a time.

Router configuration and persisted rolling-label state are private constructor
dependencies of the router, analogous to an ML model's architecture and
weights. They are not inputs to, or requirements imposed by, the external
backtester.

## Core contract

```python
decision = runtime.on_closed_bar(bar_bundle, state)
```

`on_closed_bar` is the only place that may:

1. update market features;
2. update every shadow strategy;
3. advance shadow positions and performance;
4. mature completed forward-performance labels;
5. score the router;
6. change the selected strategy;
7. emit the selected strategy's signal.

Historical replay is:

```python
for bar_bundle in historical_closed_bars:
    decisions.append(runtime.on_closed_bar(bar_bundle, state))
```

Live execution calls the same method once after every new closed H1 bar.

## Inputs

Each step receives:

- one newly closed H1 bar;
- any H4 or D1 bars that became closed at the same timestamp;
- symbol metadata;
- the previous serialized runtime state.

Bars must be strictly increasing and idempotent by H1 close timestamp. Forming
candles are rejected.

## Strategy processing

All six archived strategies remain active as shadow strategies. On each H1
step every strategy:

- updates only indicators affected by the new bar;
- emits zero or one hypothetical signal;
- advances its own shadow positions using archived execution parameters;
- updates realized shadow PnL.

Only the router-selected strategy's signal is copied into the real composite
output. Shadow portfolios never affect real capital or margin.

The router does not know concrete strategy ids, trigger names, or filters.
Strategy configs are resolved through an incremental adapter registry keyed by
strategy class (`name` in the strategy JSON). Adding or removing a portfolio
member changes only `strategy_paths`; adding a new strategy class requires that
class to provide one adapter implementation.

## Shadow execution

Shadow execution must match externally validated execution semantics:

- signal on a closed bar enters at the next H1 open unless an explicit valid
  entry price is supplied;
- archived risk percent, RRR, TP geometry, structural-stop mode, trailing, and
  TTL are preserved;
- maker/taker fees and monthly risk-base behavior match the candidate config;
- same-bar TP/SL resolution uses the same conservative policy;
- multiple positions are allowed when the strategy config allows them.

Parity tests compare each shadow strategy against a standalone external
backtest over the same synthetic bars.

## Rolling labels

The runtime opens one forward-performance observation per router cadence
(currently daily). An observation created at `T` matures at `T + 30 days`.

When it matures, the state records the shadow return of every strategy over
`[T, T + 30d)`, plus market features known at `T`.

Router scoring may use only matured observations:

```text
label_end <= decision_timestamp
```

An initial persisted label snapshot seeds the router. Historical replay may
read a versioned snapshot containing rows across the replay range, but each
decision may consume only rows whose full forward window has matured:
`label_end <= decision_timestamp`. Live execution appends newly matured rows
to the same logical state.

## Router decision

The frozen `router_v2_2687609` policy remains:

- validation/state-machine start at 2024-01-01;
- all six strategies available;
- exact trend + structure state matching;
- median return minus drawdown score;
- 180-day lookback;
- at least 10 matching observations;
- minimum 60-day hold;
- switch only when improvement is at least 0.5 points;
- no cash state.

## Output

Each step emits:

- standard `signal` and `sl_price`;
- selected strategy's risk, RRR, TTL, trailing, and exit geometry;
- `router_id`;
- `selected_strategy`;
- `position_group`;
- `drain_on_group_change = true`;
- router score/sample diagnostics.

## Persistence

Serializable state contains:

- last processed H1 timestamp;
- indicator state for every strategy;
- six shadow portfolios;
- pending and matured label observations;
- current selected strategy and selected-since timestamp;
- router score inputs.

Backtest keeps this state in memory. Production persists it atomically after
each processed bar. Storage technology is outside this MVP.

## Failure behavior

- Duplicate bar: idempotent no-op.
- Gap: process missing closed bars chronologically before the newest bar.
- Missing H4/D1 context: affected strategies emit neutral.
- Corrupt state or out-of-order bar: hard error before any real order.
- Shadow strategy failure: that strategy emits neutral and records the failure.

## Acceptance

1. Batch historical replay and one-bar-at-a-time replay produce identical
   composite signal frames.
2. Restarting from serialized state produces identical later decisions.
3. Appending future bars cannot change prior decisions.
4. Every shadow strategy matches its standalone external backtest on synthetic
   parity fixtures.
5. `promoted_router.generate()` performs one chronological replay and never
   invokes nested backtests or full-history nested `generate()` calls.
6. Live processing handles one new closed H1 bar without replaying prior bars.

The contract test is parameterized from `strategy_paths`. It must not contain a
test function or router branch for a concrete strategy id.
