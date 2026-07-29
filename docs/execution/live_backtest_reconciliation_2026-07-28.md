# Live execution / backtest reconciliation — 2026-07-13 through 2026-07-28

## Status

The bounded reconciliation through 27 July is complete. It proves the
post-rollout signal set and isolates the operational exceptions. The still
incomplete 28 July UTC day remains a separate append-only replay/cash slice.

The observation timestamp is `2026-07-28T16:00:00Z`. The first reproducible
comparison window is `[2026-07-13T00:00:00Z, 2026-07-28T00:00:00Z)`: it ends
before the still-incomplete UTC day on 28 July. A follow-up window will append
the 28 July entries and exits after that day is complete.

## Frozen live inputs

| Item | Value |
|---|---|
| Symbol | `SOL-USDT-SWAP` |
| Effective portfolio | `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json` |
| Portfolio version | `post-adr0058-tail-control-v6-drop-negative-v5-archive-2026-07-13` |
| Portfolio SHA-256 | `d40289f91a3b6617cf9cfad16426c5f9b31c311ebc276769dd2b85eddad00499` |
| Railway H1 SHA-256 | `08cfaec337a8732f998aa89bb5a8ff1a9b6f0d57e98e97cb2035ecf18ad83cc5` |
| Railway H4 SHA-256 | `1695d9cf42ddfed749150a85914ecfb40dc49e5b42ce1924acbce52266b4edaf` |
| Railway D1 SHA-256 | `23788a46cbe041cf51a346f9523d31396ee775872fe5882d29f477a3442a65f7` |
| Last closed Railway H1 at observation | `2026-07-28T15:00:00Z` |

The local repository Parquet store ended on 30 June. The Railway volume is
the only current source for the strategy timeframes. It does not contain the
minute last-price and mark-price data required by the v6
`intrabar_execution_timeframe="1m"` execution model, so those two series must
be backfilled into an isolated audit copy before the strict replay.

## Accounting boundary

OKX aggregates same-side SOL constituents into one exchange position. The
Telegram/local position PnL is therefore not a cash ledger: it can allocate a
single aggregate close differently from the exchange. The reconciliation order
is consequently:

1. OKX fills, order history, algo-order history, and account bills establish
   cash and exchange-side fills.
2. Railway event payloads identify logical strategy constituents.
3. Telegram supplies an independent timestamped notification trail.
4. The backtest signal and trade tables are joined by `signal_time`, strategy,
   side, and then entry/exit window.

### OKX cash snapshot

The following direct OKX snapshot was captured at `2026-07-28T16:13:17.218Z`.
It includes 57 fills and 85 account-ledger rows. `Gross` is realised trading
PnL (`sum(fillPnl)`); OKX fees are signed negative values, so `net = gross +
fee`. The fill-PnL and trade-ledger rows reconcile exactly within every phase.

| UTC phase | Entry orders (fills) / contracts | Exit orders (fills) / contracts | Gross PnL | Fill fees | Net after fees | Separate type-8 ledger change |
|---|---:|---:|---:|---:|---:|---:|
| `[2026-07-13, 2026-07-18)` | 5 (6) / 3.38 | 5 (7) / 3.38 | `-$2.19120000` | `-$0.25484080` | `-$2.44604080` | `+$0.01119577` |
| `[2026-07-18, 2026-07-28)` | 16 (16) / 27.85 | 15 (17) / 27.29 | `-$5.03720000` | `-$1.92740173` | `-$6.96460173` | `-$0.17661450` |
| `[2026-07-28, snapshot)` | 5 (6) / 9.30 | 5 (5) / 8.24 | `-$6.70696129` | `-$0.63342384` | `-$7.34038513` | `-$0.02410117` |
| Total | 26 / 40.53 | 25 / 38.91 | `-$13.93536129` | `-$2.81566637` | `-$16.75102766` | `-$0.18951990` |

The trade net plus the separate type-8 balance changes is `-$16.94054757`.
That remains an as-of figure: one short constituent is still open. At the
phase-B cutoff it was the `0.56` short entered at `75.58`; at the snapshot it
was the `1.62` short entered at `73.18`, with OKX aggregate average
`73.16849462`, mark `74.09`, and unrealised `-$1.49283871`.

On 28 July the five short constituents totalled 9.30 contracts but were one
OKX same-side aggregate position. Consequently an exchange exit PnL is
calculated from the aggregate average, not the individual local constituent
entry. Trade-set matching is therefore constituent-level, while money is
reconciled at phase or aggregate-side level.

## Confirmed events that must be overlaid on a fresh replay

| UTC interval / event | Classification | Reconciliation treatment |
|---|---|---|
| 2026-07-13/14 first three v6 shorts | `matched_archived_signal_payload` | Stored live signal payload replay has three stop exits: backtest `-1.685379` versus OKX `-1.689069` USDT. A fresh run cannot be expected to reproduce two ATR-derived levels after later H1 repairs. |
| 2026-07-14 01:32–01:37 | `state_sync_defect` | Local short was `1.29` contracts while OKX held `0.66`; subsequent `exchange_reduced_unknown` is an accounting/recovery issue, not evidence that the exchange fill was absent. |
| 2026-07-15 11:00 and 18:02 | `callback_failure_candidate` | Invalid forming-H1 callback and timeout respectively. Backtest signals in these windows must be checked before classifying a missed entry. |
| 2026-07-16 18:07 | `matched_late_execution` | Fresh replay emits the same 17:00 r02 short with the same planned geometry. Live filled seven minutes late after startup, then a non-model market close ended it at 19:05. It is not a missed signal or an extra strategy event. |
| 2026-07-18 22:10 | `callback_failure_candidate` | H1 refresh could not persist a conflicting closed candle; the callback failed. |
| 2026-07-19 03:00 | `state_reset_risk_base` | The live state set the July risk base to `102.34`, after earlier July entries used `104.77`. Code only resets a monthly base at a UTC month boundary, so this is a state reinitialisation/loss across the 18 July deployment/restart sequence rather than a normal monthly reset. |
| 2026-07-22 21:00 long 0.54 | `local_recovery_misclassification` | The exchange did fill the entry and its conditional stop filled at `2026-07-23T12:37:22Z` at `76.85`; a later local `exchange_closed_unknown` notification was not a phantom exchange trade. |
| 2026-07-23 13:00–20:00 | `state_sync_blocked` | Eight hourly callbacks were blocked by missing stop protection and local `1.04` versus exchange `0.50` long size. Candidate missed strategy signals have `signal_time` 12:00 through 19:00 UTC. |

The 18 Telegram notifications headed `actual fill risk ... [BLOCKED]` are
not rejections. Their body states that drift is alert-only, and each is paired
with an `ENTRY [OK]`; they are expected execution-price differences, not
missed signals.

### State-epoch evidence

The July risk-base change is proved to be a continuity defect rather than a
normal restart. `update_monthly_risk_base()` changes it only when the UTC
year/month changes; JSON loading correctly restores `[2026, 7]` as a tuple,
and state saving is atomic. A persistent-volume restart with the same state
could therefore not turn `104.77` into `102.34` during July.

Railway had five deployment events at `2026-07-18T21:30:44Z`, `21:32:11Z`,
`21:51:52Z`, `22:08:40Z`, and `22:17:39Z`. The stable process subsequently
logged `New risk window (2026, 7) — monthly_risk_base set to 102.34` at
`2026-07-19T03:00:13.963570Z`. The current persisted state has an exact base
of `102.3381502678064`; its earliest retained position has signal time
`2026-07-19T02:00:00Z`, and all 21 retained post-rollout positions use that
base. The exact loss mechanism cannot be reconstructed without the prior
state snapshot (for example, a different state path, file recreation, or an
earlier instance), but the reset itself is not ambiguous.

### Proven execution availability windows

The following table distinguishes a process/callback failure from a signal
that the strategy would actually have traded. A `candidate` must be matched to
`signals.csv`; it is not automatically a missed trade.

| UTC interval | Execution fact | Candidate signal time(s) | Replay classification |
|---|---|---|---|
| 2026-07-15 11:00 | Telegram reports a forming-H1 validation failure. The old executor did not persist its detailed callback logs to the volume. | `10:00` | `callback_failure_candidate` |
| 2026-07-15 18:02 | Telegram reports an H1 websocket timeout; detailed historical executor logs are unavailable. | `17:00` | `callback_failure_candidate` |
| 2026-07-16 18:07 | A short for the `17:00` signal was actually opened about seven minutes late. | `17:00` | late live execution; not a missed entry |
| 2026-07-18 21:58–22:10 | Deployment crash-looped because `strategies/live/active.json` was absent. The first viable executor started at `22:10:24`. | not determinable from retained logs before `21:00` | deployment availability gap |
| 2026-07-18 22:10–23:00 | The `22:00` callback failed to save a closed H1 candle. Recovery completed at `22:19:37` and explicitly skipped new entries until the next live H1 close. | `21:00` | `missed_due_recovery_candidate` |
| 2026-07-19 00:00–23:00 | Every H1 callback completed with exchange sync OK; logs identify the two live entries and `No actionable` for the remaining evaluated bars. | all | normal processing |
| 2026-07-23 13:00–20:00 | Eight live cycles explicitly skipped new entries because reconciliation found missing stop protection and local/exchange long-size mismatch. | `12:00` through `19:00` | `state_sync_blocked` |
| 2026-07-23 21:00 onward | Sync recovered; signals at `20:00` and `21:00` were evaluated and were not actionable. The next confirmed entry was the `23:00` signal, opened at 24 July 00:00. | `20:00`, `21:00`, `23:00` | normal processing |

## Replay design

One continuous replay is useful for its signal roster, but it is not a fair
dollar-size comparison across the live state reset. Use two execution phases:

| Phase | Replay range | Initial capital / July risk base | Purpose |
|---|---|---:|---|
| A | `2026-07-13T00:00Z` through `2026-07-17T23:00Z` | `104.77 USDT` | Reproduce the initial live regime. Interpret the first three events through archived signal payloads because repaired H1 history changes ATR. |
| B | `2026-07-18T00:00Z` through `2026-07-27T23:00Z` | `102.34 USDT` | Compare post-restart logical entries, protection exits, and the explicitly censored 23 July interval. Telegram confirms the account was flat at the phase boundary. |

For every backtest trade or signal, the final table must assign exactly one of:
`matched`, `matched_late_execution`, `slippage_only`, `missed_due_downtime`,
`state_sync_blocked`, `data_repair_changed_signal`, `local_accounting_only`,
or `unresolved`.

## Owner-run replay results

The owner created the isolated Railway snapshot, backfilled complete 1m last
and mark paths through 27 July, and ran the two prescribed v6 replays:

| Phase | Artifact | Backtest events | Closed / open | Backtest cash PnL | OKX trade net | Direct comparison verdict |
|---|---|---:|---:|---:|---:|---|
| A | `results/live_reconciliation/v6_capital_104_77/20260728_162345` | 7 | 5 / 2 | `+$5.40095151` | `-$2.44604080` | Not a valid aggregate parity result: repaired H1 history changed the event set and two replay positions remained open. |
| B | `results/live_reconciliation/v6_capital_102_34/20260728_162357` | 17 | 16 / 1 | `-$0.86116715` | `-$6.96460173` | Signal parity is 16 of 17, with exactly one confirmed blocked entry. |

The cash PnL above is `account_capital_at_end - initial_capital`, including
the entry fee already paid by any open position. It is more precise than
rounded values in `metrics.csv`. Type-8 OKX balance changes remain outside the
backtest contract.

### Phase B — decisive signal reconciliation

Every normal live entry after the rollout has a corresponding v6 event with
the same strategy and direction. The only event that did not reach OKX was
blocked by the confirmed dirty-sync gate.

| Signal UTC | Strategy / side | Backtest entry | Actual entry | Result |
|---|---|---:|---:|---|
| 19 Jul 02:00 | r07 long | `76.15 × 4.75` | `76.32 × 4.75` | matched; worse live entry by `$0.17` |
| 19 Jul 06:00 | r03 long | `76.07 × 0.78` | `76.08 × 0.80` | matched |
| 20 Jul 02:00 | r03 long | `76.92 × 0.57` | `76.96 × 0.57` | matched |
| 20 Jul 07:00 | r03 long | `76.17 × 0.50` | `76.18 × 0.50` | matched |
| 20 Jul 15:00 | r12 long | `77.73 × 1.57` | `77.78 × 1.57` | matched |
| 22 Jul 05:00 | r02 short | `77.37 × 0.92` | `77.40 × 0.92` | matched |
| 22 Jul 07:00 | r07 short | `77.07 × 3.18` | `77.01 × 3.15` | matched |
| 22 Jul 20:00 | r03 long | `77.75 × 0.54` | `77.76 × 0.54` | matched; exchange confirms normal stop, not phantom closure |
| 23 Jul 07:00 | r02 short | `77.11 × 0.85` | `77.07 × 0.85` | matched |
| **23 Jul 12:00** | **r07 short** | **`76.90 × 3.72`** | **none** | **blocked at 13:00 UTC; model TP `75.48`, `+$4.99897320` after fees** |
| 23 Jul 23:00 | r02 short | `75.83 × 0.81` | `75.82 × 0.81` | matched |
| 24 Jul 08:00 | r02 short | `75.73 × 0.93` | `75.73 × 0.95` | matched |
| 25 Jul 05:00 | r02 short | `73.93 × 1.29` | `73.93 × 1.29` | matched |
| 25 Jul 07:00 | r02 short | `73.74 × 1.40` | `73.72 × 1.40` | matched |
| 25 Jul 18:00 | r07 long | `74.62 × 5.35` | `74.59 × 5.45` | matched |
| 26 Jul 15:00 | r06 long | `75.45 × 3.75` | `75.46 × 3.74` | matched |
| 27 Jul 21:00 | r02 short | `75.56 × 0.56` | `75.58 × 0.56` | matched; open at cutoff |

The 15 matched closed backtest rows total `-$5.83898355`. Adding the missed
short yields `-$0.84001035` closed PnL; the `$0.02115680` entry fee on the
remaining open short produces the full phase-B cash result `-$0.86116715`.
Diagnostic subtraction of the missed row from that cash result yields
`-$5.86014035`, only `$1.10446138` better than the OKX trading net. This is
not a causal re-run without the position: it is a useful magnitude check only,
because same-side aggregation would redistribute later realised PnL.

The approximately `$1.10` residual is an execution/accounting difference,
not a missing-signal problem. The largest visible contributor is the 19 July
r07 long, whose live fill was `$0.17` above the planned entry; remaining
differences are tick rounding, market/stop fill movement, and aggregate-side
realisation.

### Phase A — historical data boundary

Fresh phase A cannot be interpreted as a strategy-money comparison. Two real
13 July signals vanished after H1 repair, while four events appear only in the
fresh recomputation:

| Signal UTC | Status |
|---|---|
| 13 Jul 12:00 and 17:00 | Real live r02 shorts; absent from the fresh replay, but already verified by stored exact payloads (`-$1.685379` replay versus `-$1.689069` OKX across the first three trades). |
| 14 Jul 06:00 | Matched r02 short; entry differed by `$0.03` and the stop filled `$0.08` beyond the fresh replay stop. |
| 16 Jul 07:00, 12:00, 16:00; 17 Jul 05:00 | Fresh-only candidates with no OKX entry. They are high-priority operational/data-history candidates, not proven historical missed signals because the old executor did not retain its H1 event payloads and later H1 repair can alter ATR/filter state. |
| 16 Jul 17:00 | Matched r02 short, filled seven minutes late; closed by a non-model market order at 19:05. |
| 17 Jul 12:00 | Matched r02 short; planned geometry and stop price agree, with normal minute/fill/aggregation differences. |

If the four fresh-only candidates had existed exactly as the repaired snapshot
now reports, two closed trades show about `+$5.66` constituent PnL, one about
`-$0.51`, and one is still open at phase end. They must not be added to actual
historical PnL without a contemporaneous candle/signal snapshot.

### Artifact caveat

For a filtered donor portfolio, the scalar `signals.csv.signal` remains zero
and `signal_diagnostics.csv` reports `signal_count=0`. The authoritative
events are the Python-literal list in `signals.csv.signal_events` (seven in
phase A and 17 in phase B). Reconciliation must parse it with
`ast.literal_eval`; `execution_sequence` and the scalar signal field are not
join keys.

## Captured owner-run artifacts

The two captured runs contain `trades.csv`, `trade_diagnostics.csv`,
`metrics.csv`, `signals.csv`, `signal_diagnostics.csv`, `equity_curve.csv`,
and minute-path trade artifacts. The following commands reproduce the frozen
snapshot; the data copy is isolated in `/tmp` and does not overwrite the
repository's canonical data directory.

```bash
AUDIT_DATA_DIR=/tmp/crypt_live_audit_20260728T1600Z
mkdir -p "$AUDIT_DATA_DIR"

railway ssh --service crypt --environment production -- \
  "tar -C /app/data -cf - SOL-USDT-SWAP" \
  | tar -C "$AUDIT_DATA_DIR" -xf -

PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache \
uv run python -m crypt.backfill \
  --symbol SOL-USDT-SWAP \
  --from 2026-07-13 \
  --to 2026-07-28 \
  --data-types execution_1m \
  --data-dir "$AUDIT_DATA_DIR" \
  --page-size 100 \
  --max-rps 5
```

The backfill interval is deliberately date-exclusive at 28 July, so it gets
complete minute data through 27 July 23:59 UTC and cannot request future bars.
After it finishes, the two following commands are independent and may run in
parallel in separate terminals:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/crypt-mpl UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --data-source crypt-parquet \
  --data-dir /tmp/crypt_live_audit_20260728T1600Z \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --from 2026-07-13T00:00:00+00:00 \
  --to 2026-07-17T23:00:00+00:00 \
  --capital 104.77 \
  --output results/live_reconciliation/v6_capital_104_77
```

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/crypt-mpl UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --data-source crypt-parquet \
  --data-dir /tmp/crypt_live_audit_20260728T1600Z \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --from 2026-07-18T00:00:00+00:00 \
  --to 2026-07-27T23:00:00+00:00 \
  --capital 102.34 \
  --output results/live_reconciliation/v6_capital_102_34
```

`--from` and `--to` are inclusive timestamp bounds. A date-only `--to
2026-07-27` would mean midnight and discard almost all of that day. The final
primary bar intentionally has no next H1 open, so `23:00Z` is a safe right
boundary for the execution simulator.

Each `--output` root receives a timestamped child directory.

## Remaining 28 July append

After `2026-07-29T00:00:00Z`, complete the day in the same isolated data
directory and rerun the continuous phase B range; a standalone 28 July run
would lose the open short and account path from 27 July.

```bash
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache \
uv run python -m crypt.backfill \
  --symbol SOL-USDT-SWAP \
  --from 2026-07-28 \
  --to 2026-07-29 \
  --data-types ohlcv,execution_1m \
  --data-dir /tmp/crypt_live_audit_20260728T1600Z \
  --page-size 100 \
  --max-rps 5

PYTHONPATH=src MPLCONFIGDIR=/tmp/crypt-mpl UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --data-source crypt-parquet \
  --data-dir /tmp/crypt_live_audit_20260728T1600Z \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --from 2026-07-18T00:00:00+00:00 \
  --to 2026-07-28T23:00:00+00:00 \
  --capital 102.34 \
  --output results/live_reconciliation/v6_capital_102_34_through_20260728
```

## Sources

- Railway production volume: `/app/data/SOL-USDT-SWAP`,
  `/app/data/live_positions.json`, and `/app/data/logs/crypt.log*`.
- OKX private read-only history: fills, regular orders, algo orders, and
  account bills.
- Owner-supplied Telegram notifications (MSK, converted to UTC by subtracting
  three hours).
- `docs/archive/candidates/post_adr0058_tail_control_portfolio/live_replay_20260714.md`.
