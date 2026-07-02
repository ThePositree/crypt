# Minute intrabar execution

## Purpose

Use historical OKX one-minute candles to replay the order of events inside an
H1 execution bar without changing the strategy signal timeframe.

H1/H4/D1 closed candles remain the only signal inputs. One-minute data is an
execution input: it determines whether an already-open position encounters a
stop, native trailing activation/stop, take profit, or liquidation first.

## Inputs

The Parquet store provides two complete UTC series:

- `ohlcv_1m/YYYY-MM.parquet`: OKX last-trade OHLCV;
- `mark_ohlcv_1m/YYYY-MM.parquet`: OKX mark-price OHLC with zero volume.

Both series contain only confirmed closed candles. The backfill workflow
retrieves them through the existing recurring `crypt.backfill` operator
surface using `--data-types execution_1m`. Independent `last_1m` and `mark_1m`
data types allow the two disjoint downloads to run safely in parallel.

The backtester receives the two frames as typed `IntrabarExecutionData`.
Strategy implementations do not receive or copy these frames.

## Signal and entry contract

- Strategy generation continues on closed H1/H4/D1 candles.
- A signal emitted for closed H1 bar `T` enters at the last-trade H1 open at
  `T + 1h`, exactly as before.
- One-minute candles at and after the entry boundary may close or update the
  new position.
- Minute data cannot create, remove, delay, or modify a strategy signal.

## Exit logic

For every H1 interval, the simulator processes its 60 one-minute candles in
ascending timestamp order:

1. last-trade OHLC evaluates structural stop, take profit, and native trailing;
2. mark-price OHLC evaluates liquidation;
3. gap-through market triggers fill at the adverse one-minute open;
4. ambiguity remaining inside one minute follows the configured bar exit
   policy; `worst_case` chooses the economically worse reachable exit;
5. H1 TTL and portfolio drain rules remain anchored to H1 boundaries.

Native trailing keeps its fixed entry-time callback geometry. Under
`worst_case`, an active trailing stop is checked before a favorable extreme
tightens it. A stop tightened by a one-minute candle cannot use an earlier
adverse extreme from that same candle.

If a constituent exit makes the remaining same-side aggregate position unsafe,
the existing fail-safe still closes at the next H1 synchronization boundary,
matching the live executor's synchronization cadence.

## Completeness and fallback

When `intrabar_execution_timeframe` is configured as `1m`, every simulated H1
interval must have exactly 60 aligned last-trade candles and 60 aligned
mark-price candles. The 60 last-trade candles must also aggregate exactly to
the stored H1 high/low/close. OKX can publish a different H1 open and first
1m open while retaining identical H1 range and close; the H1 open remains the
entry model and the first 1m open starts the subsequent intrabar path. That
minute open must still lie inside the H1 range. Duplicate, missing, off-grid,
unsorted, out-of-range, or materially cross-timeframe-inconsistent rows are
fatal.

There is no silent H1 fallback. A mixed-resolution result cannot be compared
to live execution or to another canonical artifact.

When minute execution is not configured, the existing conservative H1 model
remains available for legacy strategies and tests.

## Live behavior

Live does not wait for one-minute candles to manage protection:

- OKX holds stop/take-profit/native-trailing orders continuously;
- OKX liquidation uses its real-time mark price;
- the executor synchronizes state and applies TTL at H1 boundaries.

Historical one-minute data reproduces those intrahour events in the
backtester. Polling a completed one-minute candle in live would be slower than
the native exchange orders and is therefore not an execution control.

## Missing data

Minute storage is partitioned by UTC month so a multi-year backfill can
checkpoint progress without rewriting millions of older rows after every API
page. Each monthly Parquet write upserts by timestamp and is atomic. If OKX
returns no page before the requested exclusive end, backfill fails instead of
declaring success. The operator must rerun the same command until continuity
validation passes.
