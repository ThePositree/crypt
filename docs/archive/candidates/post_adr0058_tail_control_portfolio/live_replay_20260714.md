# Live replay: v6 first real SOL trades

**Date:** 2026-07-14  
**Portfolio:** `filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5`  
**Symbol:** `SOL-USDT-SWAP`  
**Scope:** first three live entries and exchange-side stop exits.

## What happened

The live v6 run opened three short constituents from
`freq_4pw_r02_hyperband_004678`:

| Signal time UTC | Live entry time UTC | Live fill | Live SL | Live TP | OKX exit time UTC | OKX exit | OKX reason |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-07-13 12:00 | 2026-07-13 13:00 | 0.66 @ 75.84 | 76.62 | 73.46 | 2026-07-14 12:50:49.710 | 76.63 | stop loss |
| 2026-07-13 17:00 | 2026-07-13 18:00 | 0.63 @ 74.60 | 75.34 | 72.13 | 2026-07-14 00:55:09.934 | 75.35 | stop loss |
| 2026-07-14 06:00 | 2026-07-14 07:00 | 0.66 @ 75.07 | 75.88 | 72.77 | 2026-07-14 12:30:07.224 | 75.90 | stop loss |

OKX returned the triggered stop algo id in `clOrdId`, not in the regular order
id. The live fill classifier now treats that id as a protection-order match,
so these exits classify as `stop_loss` instead of `exchange_closed_unknown`.

## Data repair

The replay required complete 1m last-price and mark-price candles from
2026-06-30 through 2026-07-14 12:59 UTC. Both minute stores were backfilled and
checked:

- `ohlcv_1m`: 20,940 expected rows, 20,940 actual rows, no duplicates, no
  non-1m gaps.
- `mark_ohlcv_1m`: 20,940 expected rows, 20,940 actual rows, no duplicates, no
  non-1m gaps.

During replay validation, two local H1 rows did not aggregate from the 1m data
and were repaired from the minute candles:

- `2026-07-13T12:00:00Z`
- `2026-07-13T16:00:00Z`

After repair, the H1 rows in the replay window aggregate cleanly from 1m data.

## Replay result

The strict replay used warmup history for indicators, then started execution
from the first live-seen signal at `2026-07-13T12:00:00Z`. A technical
right-boundary row at `2026-07-14T13:00:00Z` was added only in memory so the
simulator could process the final `12:00-12:59` minute interval.

Using the exact `signal_event` payloads stored in `data/live_positions.json`,
the backtester produced three trades and all three exited by stop loss:

| Signal time UTC | Backtest entry | Backtest SL | Backtest TP | Backtest exit UTC | Backtest exit | Reason | Account PnL |
|---|---:|---:|---:|---:|---:|---|---:|
| 2026-07-13 12:00 | 75.82 | 76.62 | 73.42 | 2026-07-14 12:50 | 76.62 | stop_loss | -1.008516 |
| 2026-07-13 17:00 | 74.54 | 75.34 | 72.13 | 2026-07-14 00:55 | 75.34 | stop_loss | -0.141712 |
| 2026-07-14 06:00 | 75.10 | 75.88 | 72.77 | 2026-07-14 12:30 | 75.88 | stop_loss | -0.535150 |

The replay total account PnL was `-1.685379` USDT. The live exchange-account
classification from OKX fills was `-1.689069` USDT:

- first constituent: `-1.025657` account PnL, `-0.571715` constituent PnL;
- second constituent: `-0.120051` account PnL, `-0.519734` constituent PnL;
- third constituent: `-0.543362` account PnL, `-0.597620` constituent PnL.

The small difference is expected: live uses market fills several seconds after
the H1 open and OKX trigger fills can slip beyond the stop price, while the
backtester uses deterministic next-open entries and stop-price exits.

## Important caveat

Recomputing the strategy on the repaired current parquet does not reproduce the
second and third live stop prices exactly. OHLC values match, but ATR-derived
fields changed after H1 repair. For this incident, the correct parity source is
the archived live `signal_event` payload, not a fresh recomputation over a
mutated local history.

Future live runs should preserve exact signal/data snapshots for every live
entry so parity replay does not depend on later parquet repairs.
