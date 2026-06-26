# Multi-signal execution

## Purpose

Multi-signal execution lets one strategy frame emit several independent entry
requests for the same OHLCV bar. This is required for filtered donor
portfolios where multiple strategies may pass their entry filters on the same
candle and should compete for the same shared capital/margin pool.

The goal is **not** to allocate fixed capital slices per strategy. Capital
remains shared. Each accepted event is processed by the existing risk, leverage,
margin, fee, TTL, trailing, and exit-geometry rules.

## Backward-compatible input contract

The legacy contract stays valid:

- one dataframe row per OHLCV bar;
- scalar `signal` and `sl_price`;
- optional per-row execution columns such as `risk_percent`, `rrr`,
  `position_ttl_bars`, `trail_activation_rrr`, `trail_distance_atr`,
  `exit_geometry`, `tp_move_pct`, `structural_sl_mode`, `min_tp_move_pct`,
  `position_group`, and `entry_price`.

The additive multi-signal contract uses:

- one dataframe row per OHLCV bar;
- normal OHLCV columns;
- `signal_events`: a list/tuple of event dictionaries for that bar.

Each event dictionary may contain:

- `signal`: `1` for long, `-1` for short, `0` to ignore;
- `sl_price`;
- optional execution overrides matching the scalar row columns;
- metadata fields such as `selected_strategy`, `filter_rule`, confidence,
  score, or rationale.

Rows may keep scalar `signal=0` and `sl_price=0` when `signal_events` is used.

## Execution order

For each OHLCV bar:

1. Update already open positions exactly once using the current bar high/low
   and next open, identical to the legacy simulator.
2. Update daily risk counters from newly closed trades.
3. If new entries are allowed by daily/session gates, process every event in
   `signal_events` in list order.
4. Each event is evaluated against the current active positions and currently
   locked margin after previous same-bar events.
5. If capital/margin/leverage/max-position gates reject an event, only that
   event is skipped; later events are still evaluated against the resulting
   state.

This avoids the invalid shortcut of duplicating OHLCV bars, which would update
exits multiple times for the same candle.

## Output

Trades keep the existing output schema. Event metadata is copied into the trade
row the same way scalar strategy metadata is copied today. A filtered portfolio
must include enough metadata to audit which donor and which filter accepted the
trade.

## Guardrails

- Multi-signal execution must be opt-in via `signal_events`.
- Legacy one-signal strategies must remain unchanged.
- `signal_events` must not contain post-entry outcome fields.
- Exact portfolio promotion still requires a normal `backtester run` artifact
  with `trades.csv`, `metrics.csv`, diagnostics, and charts.
