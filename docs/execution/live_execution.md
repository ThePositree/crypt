# Live execution module (M4)

Spec for `src/crypt/execution/` — the component that turns backtester strategy
signals into real OKX orders.

Read ADR-0033 before this document. The ADR records architectural decisions;
this document records the runtime contract.

---

## 1. Parity contract

**The single most important rule**: every sizing, SL, TP, TTL, and margin
decision in the live module must be computed by the same code that runs in
the backtester.

| Backtester component | Live equivalent |
|---|---|
| Any registry strategy `generate(strategy_data)` | `LiveSignalRunner.get_latest_signal_batch()` |
| `BasicRiskModel.calculate_position(ctx)` | `LiveRiskCalculator.calculate(ctx)` |
| `ExecutionSim._risk_base_capital_for_entry()` | `LiveRiskCalculator.monthly_risk_base()` |
| `ExitGeometryConfig` + `resolve_exit_levels()` | same imports, same call |
| `margin_policy.select_leverage_and_locked_margin()` | same imports, same call |
| `StaticPercentFeeModel` | same class, same params |

If the backtester's classes change, the live module must be updated in the
same commit and the change tagged in CHANGELOG as a live-trading parameter
change.

---

## 2. Module layout

```
src/crypt/execution/
    __init__.py
    settings.py          # ExecutionSettings (pydantic-settings, from .env)
    position_state.py    # LivePosition dataclass + JSON persistence
    exchange_sync.py     # Exchange snapshot + local/exchange reconciliation
    risk_calculator.py   # LiveRiskCalculator — wraps BasicRiskModel
    signal_runner.py     # LiveSignalRunner — runs registry strategies on Parquet
    okx_order_client.py  # OKXTradingClient — order placement / management
    notifications.py     # Execution Telegram notifications
    executor.py          # LiveExecutionManager — H1 tick orchestrator
```

---

## 3. Settings (`ExecutionSettings`)

Loaded from `.env` via `pydantic-settings`. All keys prefixed `EXECUTION_`.

| Key | Default | Description |
|---|---|---|
| `EXECUTION_ENABLED` | `false` | Must be set to `true` to activate |
| `EXECUTION_DRY_RUN` | `true` | Log orders without placing them |
| `EXECUTION_DRY_RUN_CAPITAL` | `0.0` | Optional dry-run-only sizing capital; `0` uses real OKX balance |
| `EXECUTION_STRATEGY_CONFIG` | `strategies/live/active.json` | Path to the selected strategy JSON |
| `EXECUTION_DATA_DIR` | `data` | Root Parquet directory |
| `EXECUTION_STATE_PATH` | `data/live_positions.json` | State file |
| `EXECUTION_EXIT_GEOMETRY` | `sl_rrr` | Fallback exit geometry for legacy/sparse events |
| `EXECUTION_TP_MOVE_PCT` | `0.016` | Fallback TP percent for legacy single-signal strategies |
| `EXECUTION_STRUCTURAL_SL_MODE` | `cap` | Fallback structural SL handling |
| `EXECUTION_MIN_TP_MOVE_PCT` | `0.004` | Fallback minimum TP move for `tp_pct` |
| `EXECUTION_RRR` | `2.0` | Fallback reward/risk ratio |
| `EXECUTION_TTL_BARS` | `0` | Fallback H1 bars; `0` disables fallback TTL |
| `EXECUTION_RISK_PERCENT` | `1.0` | Fallback % of monthly base per trade |
| `EXECUTION_TRAIL_ACTIVATION_RRR` | `0.0` | Fallback trailing activation; `0` disables trailing |
| `EXECUTION_TRAIL_DISTANCE_ATR` | `0.0` | Fallback trailing distance |
| `EXECUTION_MAX_POSITIONS` | `0` | Backtester-compatible cap; `0` means unlimited and is the Core v4 default |
| `EXECUTION_MAX_LEVERAGE` | `25.0` | OKX isolated margin max |
| `EXECUTION_RISK_BASE_PERIOD` | `monthly` | Same as backtest |
| `EXECUTION_TAKER_FEE` | `0.0005` | 0.05% |
| `EXECUTION_MAKER_FEE` | `0.0002` | 0.02% |
| `EXECUTION_INSTRUMENT_PRECISION_POLICY` | `okx_sol_usdt_swap_2026_07_01` | Dated contract/amount/tick policy; must match strategy JSON |
| `EXECUTION_MAX_CAPITAL_RISK_PCT` | `10.0` | Circuit breaker |
| `EXECUTION_REQUIRE_EXCHANGE_SYNC` | `true` | When live money is enabled, block new entries unless OKX account state is synced |

---

## 4. Signal runner

`LiveSignalRunner.get_latest_signal_batch(symbol) -> SignalBatch | None`

1. Loads `CryptParquetDataLoader(data_dir, symbol, primary_timeframe="1h").load()`
   to get `StrategyData` with all H1/H4/D1 history.
2. Loads the strategy JSON via the backtester registry. Core v4 is
   `filtered_donor_portfolio`, not `crypt_ensemble`.
3. Calls the strategy's `generate(strategy_data)` to produce the full signal
   DataFrame.
4. Returns the **last closed bar's complete entry event list**:
   - for Core v4, `signal_events` is a list of donor event dictionaries;
   - for legacy strategies, a non-zero scalar `signal`/`sl_price` row is
     converted to one event.
4. A "closed bar" is any bar before the current forming bar — the same
   no-lookahead rule enforced by the backtester.

The signal batch also carries the current forming H1 candle open when OKX
returns it. This is the live equivalent of the backtester's `next_open`. If the
next open cannot be known, the executor must skip new entries; it must not use
the signal candle close as a substitute.

**Data freshness**: before calling `generate()`, the runner updates the Parquet
files by fetching recent bars from OKX via `OKXClient.fetch_ohlcv()` and
appending any bars newer than the last stored timestamp. This ensures the signal
frame is up to date at each H1 tick.

For normal scheduled execution, the primary trigger is the OKX business
WebSocket described in `docs/execution/h1_websocket_trigger.md`. It connects at
`HH:59:30 UTC`, waits for exchange-confirmed H1/H4/D1 candles and the new H1
open, persists that boundary, and starts signal generation immediately. The
REST refresh at `*:02 UTC` is a fallback, not the primary clock.

`filtered_donor_portfolio` uses the validated latest-bar cache described in
`docs/execution/live_signal_cache.md`. The complete backtester `generate()`
path remains unchanged. On the current 39,734-bar SOL dataset, measured runtime
was 31.8 seconds for a full rebuild, 13.2 seconds for a cold live cache, and
6.8 seconds for the next validated hourly append.

---

## 5. Risk calculator

`LiveRiskCalculator.calculate(symbol, signal_event, capital) -> RiskResult | None`

Mirrors `ExecutionSim._try_open_position()` exactly:

1. `risk_base_capital = monthly_risk_base(entry_time, capital)` — same logic as
   `ExecutionSim._risk_base_capital_for_entry()`: captures balance at the start
   of each calendar month.
2. `total_locked_margin = sum(pos.locked_margin for all open positions)`
3. Calls `BasicRiskModel.calculate_position(EntryContext(...))`.
4. Checks `_can_open_position()` — leverage consistency, available balance.
5. Computes `fee_entry = taker_fee * position_value`.
6. Guards: `fee_entry < risk_value * 2` and `net_exposure >= min_net_exposure * balance`.

For multi-signal Core v4 events, the event's own `risk_percent`, `rrr`,
`position_ttl_bars`, `trail_activation_rrr`, `trail_distance_atr`,
`exit_geometry`, `tp_move_pct`, `structural_sl_mode`, `min_tp_move_pct`,
`maintenance_margin_rate`, `liquidation_fee_rate`,
`liquidation_buffer_pct`, and `maintenance_margin_tier_schedule` override the
fallback environment settings exactly as `ExecutionSim` does.

At startup, live execution validates the fallback settings against the loaded
strategy JSON `backtest_args` for all money-impacting defaults. A mismatch
raises before any order can be placed.

The validation includes maker/taker fee rates and the dated instrument
precision policy. Environment overrides may not silently change either.

If any guard fails → returns `None` (do not trade).

---

## 6. Order placement

`OKXTradingClient.open_position(symbol, risk_result, dry_run) -> str | None`

Steps:
1. Set OKX isolated leverage only for the side being opened:
   ```python
   await exchange.set_leverage(
       max_leverage,
       symbol,
       {'marginMode': 'isolated', 'posSide': 'long'},
   )
   ```
   OKX isolated leverage is side-specific in long/short position mode. Portfolio
   must never rewrite the opposite side because it may contain an open
   position or pending order.
2. Convert `risk_result.size` (asset units) to `contracts`:
   ```python
   market = exchange.market(ccxt_symbol)
   contracts = math.floor(risk_result.size / market['contractSize'])
   ```
   Round down to the market amount step and reject below the market minimum.
   For the dated `SOL-USDT-SWAP` metadata snapshot used by live execution
   (`okx_sol_usdt_swap_2026_07_01`), contract size is `1 SOL`, amount step and
   minimum are `0.01 contracts`, and price tick is `0.01 USDT`. The backtester
   applies the same policy before tier, liquidation, margin, fee, and PnL
   calculations.
3. `side = 'sell' if short else 'buy'`
4. Place an idempotent market order with a stable client ID and direct OKX
   `attachAlgoOrds` structural SL. Attach the fixed TP only when it lies
   strictly before native trailing activation.
   ```python
   await exchange.create_order(
       ccxt_symbol, 'market', side, contracts,
       params={
           'marginMode': 'isolated',
           'positionSide': 'long' if is_long else 'short',
           'stopLoss': {
               'triggerPrice': exchange.price_to_precision(ccxt_symbol, sl_price),
               'type': 'market',
               'triggerPriceType': 'last',
           },
           'takeProfit': {
               'triggerPrice': exchange.price_to_precision(ccxt_symbol, tp_price),
               'price': exchange.price_to_precision(ccxt_symbol, tp_price),
               'type': 'limit',
               'triggerPriceType': 'last',
           },
       }
   )
   ```
   `signal_executor` uses OKX's direct `attachAlgoOrds` payload for the same
   structure (`tdMode=isolated`, `posSide`, market SL, optional limit TP). Live execution
   keeps `last` trigger prices because the backtester uses last-trade OHLCV;
   switching the stop to mark price would make live stop behavior diverge from
   the historical candles.
5. Confirm the average fill and filled contracts from OKX. For a
   trailing-enabled event, place a separate reduce-only `move_order_stop`
   using the geometry planned before submit from the H1 next-open, not the
   later actual fill:
   - `activePx = H1_open +/- stop_distance * trail_activation_rrr`;
   - `callbackSpread = closed_entry_ATR14 * trail_distance_atr`.
6. Persist the entry, fixed protection IDs, native trailing client/algo IDs,
   actual fees, liquidation geometry, and maintenance-margin tier schedule.
   Entry fees reduce available backtest capital immediately, matching OKX cash
   timing; closing a trade credits gross price PnL less only the exit fee.
   Backtests charge triggered TP limits as taker because OKX may execute them
   immediately; live reconciliation stores the actual exchange fee.

All logical entries on one instrument side share the OKX position's aggregate
average entry for realized PnL, margin, and liquidation accounting. Increasing
the side updates that average; a partial close preserves it. Logical entry
prices remain attached to their own protection geometry. Every successful
exchange synchronization adopts OKX `avgPx` and `liqPx` for all local
constituents on that side (ADR-0058).

### Durable order lifecycle

Every entry persists an explicit lifecycle before the first exchange write:

```text
entry_intent -> entry_submitted -> entry_filled -> protected
```

Every forced/TTL close persists:

```text
open -> closing -> closed
```

On startup, deterministic client IDs are queried before side-level inference:

- an unsubmitted/not-found intent with no matching exchange position is
  cancelled locally;
- a filled entry adopts actual order ID, average price, contracts, and fee;
- a filled trailing entry keeps the pre-submit H1-open trailing geometry,
  then confirms all required protection, repairs it idempotently with that same
  geometry, or closes reduce-only;
- a `closing` record adopts its close fill, or retries the same deterministic
  reduce-only close while the exchange side remains open;
- lifecycle records are never excluded merely because their status is not
  `open`.

Recovery must converge without duplicating an entry or close.

See `docs/execution/native_okx_trailing.md`.

**Symbol conversion**: OKX native `SOL-USDT-SWAP` → ccxt unified `SOL/USDT:USDT`
via `exchange.market_id(symbol)` reverse lookup after `load_markets()`.

---

## 7. Exchange sync and exit management

Before startup reconciliation, before every H1 entry decision, and after every
order placement, the executor must fetch an OKX account snapshot:

- USDT total/free/used balance;
- open positions for every configured symbol;
- regular open orders;
- pending algo orders including SL/TP when available;
- native `move_order_stop` protection for every trailing-enabled position;
- recent fills/trades when available.
- account position mode; it must be OKX long/short mode, not net/one-way mode.

The snapshot is compared with `data/live_positions.json`.

Blocking mismatches:

- OKX has an open position that is not represented in local state;
- OKX has open regular or algo orders for a symbol with no tracked live
  position;
- local state says a position is open, but OKX has no matching position and the
  close/fill cannot be classified;
- OKX account is not in long/short position mode;
- balance or position endpoints fail while `EXECUTION_DRY_RUN=false`.

Exchange order/fill identity is matched by both client ID and exchange order
ID. Trade IDs are deduplicated. Recovery queries deterministic order IDs
directly and does not depend only on a rolling latest-100 fill window.

When a blocking mismatch exists, the executor must persist the sync report,
log/alert it, and skip all new entries. It may still try safe risk-reducing
actions such as cancelling known orphan orders when an operator explicitly
enables that workflow.

### 7a. Telegram execution notifications

When `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured, live execution
must send:

- one full sync report per UTC day, persisted by date in `live_positions.json`
  so service restarts do not spam repeated daily reports;
- one `ENTRY ATTEMPT` message for every actionable donor event before risk
  sizing or OKX order calls;
- one terminal result for every entry attempt:
  - `ENTRY` when the position was recorded successfully;
  - `ENTRY REJECTED` when a deterministic risk, margin, group, size, or circuit
    breaker rejects the event;
  - `EXECUTION ERROR` when leverage setup, order placement, candle refresh,
    signal generation, exchange synchronization, or another execution step
    raises;
- one exit notification after a position is marked closed from OKX fills,
  startup reconciliation, or TTL market close.

Every attempt and rejection is also written to the normal service log with the
same symbol, side, strategy, prices, and rejection reason. Telegram is not the
only audit trail.

The daily sync report includes account balance, open local positions, exchange
positions, regular orders, algo SL/TP orders, current sync status, and blocking
reasons. Telegram failures must be logged and must not stop state persistence or
order management.

Entry-attempt messages include symbol, side, donor strategy, signal time,
expected entry, and structural SL. Rejection/error messages include the
operator-facing reason. A persistent exchange-sync blocker is sent on every H1
execution cycle while it remains active. Repeated alerts are intentional: the
operator must not miss a condition that prevents entries.

The notification contract is best-effort: failure to reach Telegram is retried
and logged, but never changes whether an otherwise valid order is placed or
whether state is persisted.

Entry drift is alert-only (ADR-0054). A quote or actual fill farther than
`EXECUTION_MAX_ENTRY_DRIFT_PCT` from the H1 backtest open must be logged and
sent to Telegram after submission; it must not reject the entry. The alert
contains the H1 open, pre-submit quote, actual fill, H1-to-fill drift, and
quote-to-fill drift. Telegram labels it `ENTRY DRIFT [OK]` and explicitly says
the entry executed; it is not an `EXECUTION ERROR`. Liquidation and leverage
safety remain independent blocking checks. Risk sizing, SL/TP placement, and
native trailing geometry are planned from the H1 next-open price used by the
backtester; the pre-submit quote is observability only and must not mutate the
planned trade.

At each H1 tick, for each open position:

### 7b. SL/TP fill detection

Query OKX positions: `await exchange.fetch_positions([ccxt_symbol])`.
If the position for this `position_id` is no longer open (size = 0), it was
closed by SL or TP. Update state file with realized PnL from OKX trade history.
`realized_pnl` is account-level PnL using the OKX side `aggregate_entry_price`
so it reconciles to equity. `constituent_realized_pnl` is diagnostic PnL from
that logical donor's own `entry_price` and is used for per-strategy attribution.

### 7c. TTL expiry

```python
ttl_expiry = position.entry_time + timedelta(hours=position.ttl_bars)
if datetime.now(UTC) >= ttl_expiry:
    # 1. Cancel this position's TP, structural SL, and native trailing algo
    await client.cancel_algo_orders_for_position(symbol, order_id)
    # 2. Place market close
    await client.close_position_at_market(symbol, opposite_side, contracts)
    # 3. Update state
```

This mirrors `ExecutionSim._update_active_positions()` where TTL fires at
`next_open` of bar `bar_opened + ttl_bars`.

An attached limit TP and structural SL may be linked by OKX as OCO. Cancelling
the TP can therefore make a subsequent explicit SL cancellation return `51400`
(`filled, canceled or does not exist`). Protection cancellation is idempotent:
that terminal response is success, not a reason to abort the reduce-only close.

The market close order must include `reduceOnly=True`, `marginMode=isolated`,
and the original position side (`long` for closing a long, `short` for closing
a short).

---

## 8. Monthly risk base

At each H1 tick, `LiveRiskCalculator` checks whether the current calendar month
differs from the persisted `risk_window_month` in state. If yes:

1. Query OKX USDT balance.
2. Record as `monthly_risk_base` in state file.
3. Update `risk_window_month = (year, month)`.

This mirrors `ExecutionSim._risk_base_capital_for_entry()` for
`risk_base_period = "monthly"`.

---

## 9. State file schema (`data/live_positions.json`)

```json
{
  "schema_version": 6,
  "risk_window_month": [2026, 6],
  "monthly_risk_base": 10000.0,
  "last_exchange_sync_at": "2026-06-09T15:02:00+00:00",
  "last_exchange_sync_ok": true,
  "last_exchange_sync_errors": [],
  "last_daily_sync_report_date": "2026-06-09",
  "positions": [
    {
      "position_id": "uuid",
      "symbol": "SOL-USDT-SWAP",
      "signal_time": "2026-06-09T14:00:00Z",
      "entry_time": "2026-06-09T15:00:00Z",
      "entry_price": 145.30,
      "sl_price": 143.00,
      "tp_price": 148.05,
      "size": 68.97,
      "contracts": 68,
      "leverage": 25.0,
      "locked_margin": 394.85,
      "risk_base_capital": 10000.0,
      "is_long": false,
      "ttl_bars": 36,
      "entry_order_id": "okx-order-id",
      "status": "open",
      "selected_strategy": "dssv2_013321_ps_macd_squeeze_recent",
      "position_group": "dssv2_013321_ps_macd_squeeze_recent",
      "signal_event": {
        "signal": -1,
        "risk_percent": 0.85,
        "rrr": 2.0
      },
      "trail_activation_rrr": 0.0,
      "trail_distance_atr": 0.0,
      "trail_active": false,
      "trail_stop_price": null,
      "best_favorable_price": null,
      "last_sync_status": "ok",
      "last_sync_at": "2026-06-09T15:02:00+00:00"
    }
  ]
}
```

State is written atomically (write to `.tmp`, then rename) to prevent
corruption on crash.

---

## 10. Crash recovery

On startup, `LiveExecutionManager.reconcile()`:
1. Reads `live_positions.json`.
2. Fetches a full OKX snapshot for all configured execution symbols.
3. For each position with `status = "open"`, checks the exchange snapshot.
4. If OKX has no open position for that symbol → treat as externally closed,
   log INFO, remove from the open set, and recompute sync status.
5. If OKX has an open position → keep tracking.
6. Orphan exchange positions/orders still block new entries until an operator
   resolves or imports them.
7. Monthly risk base is read from state file; if missing (fresh start), set to
   current OKX balance.

---

## 11. Known biases vs backtester

| Bias | Direction | Magnitude |
|---|---|---|
| Entry fill price ≠ next bar open (market order latency) | Random ±0.02–0.10% | Small |
| SL trigger price ≠ SL fill price (gap slippage) | Adverse | 0–0.5% per event |
| Funding rate not deducted from PnL | Optimistic | ~0.21% per 168h hold |
| TP limit order may not fill immediately (thin book) | Adverse | Rare for SOL |
| Leverage set call may fail → entry rejected | Neutral | Documented in log |

These biases are accepted. Live equity will diverge from backtest equity over
time. Monthly mandate tracking against live results uses actual OKX balance,
not simulated.

---

## 12. Circuit breakers

1. **`dry_run = True`** — default, must explicitly disable.
2. **`EXECUTION_ENABLED = false`** — module skips all logic.
3. **Capital guard**: if `total_locked_margin / balance > max_capital_risk_pct`,
   skip new entries.
4. **Authentication guard**: if OKX API key is empty, refuse to start executor.
5. **Parquet freshness guard**: if newest H1 bar is older than 3 hours, log
   WARNING and skip signal check (likely data pipeline failure).

---

## 13. Integration with scheduler

`src/crypt/__main__.py` supports two runtime shapes:

```bash
# One-shot trading dry-run. This is the preferred operator check.
PYTHONPATH=src \
MPLCONFIGDIR=/tmp/matplotlib \
EXECUTION_ENABLED=true \
EXECUTION_DRY_RUN=true \
EXECUTION_DRY_RUN_CAPITAL=10000 \
EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
EXECUTION_SYMBOLS=SOL-USDT-SWAP \
uv run python -m crypt --once --execution-only

# Long-running trading service, H1 execution only.
PYTHONPATH=src EXECUTION_ENABLED=true uv run python -m crypt --execution-only

# Combined legacy H4 monitor plus H1 execution. Use only when both are wanted.
PYTHONPATH=src EXECUTION_ENABLED=true uv run python -m crypt
```

`--execution-only` skips the legacy H4 signal monitor and uses
`EXECUTION_SYMBOLS` for startup OKX symbol health checks. Operator dry-runs for
portfolio execution must use this mode; otherwise console output can include unrelated
`HOLD/conf/regime` verdicts from the older alerting pipeline.
