# Live execution module (M4)

Spec for `src/crypt/execution/` — the component that turns
`crypt_ensemble` signals into real OKX orders.

Read ADR-0033 before this document. The ADR records architectural decisions;
this document records the runtime contract.

---

## 1. Parity contract

**The single most important rule**: every sizing, SL, TP, TTL, and margin
decision in the live module must be computed by the same code that runs in
the backtester.

| Backtester component | Live equivalent |
|---|---|
| `crypt_ensemble.generate(strategy_data)` | `LiveSignalRunner.get_latest_signal()` |
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
    risk_calculator.py   # LiveRiskCalculator — wraps BasicRiskModel
    signal_runner.py     # LiveSignalRunner — runs crypt_ensemble on Parquet
    okx_order_client.py  # OKXTradingClient — order placement / management
    executor.py          # LiveExecutionManager — H1 tick orchestrator
```

---

## 3. Settings (`ExecutionSettings`)

Loaded from `.env` via `pydantic-settings`. All keys prefixed `EXECUTION_`.

| Key | Default | Description |
|---|---|---|
| `EXECUTION_ENABLED` | `false` | Must be set to `true` to activate |
| `EXECUTION_DRY_RUN` | `true` | Log orders without placing them |
| `EXECUTION_STRATEGY_CONFIG` | — | Path to strategy JSON (required) |
| `EXECUTION_DATA_DIR` | `data` | Root Parquet directory |
| `EXECUTION_STATE_PATH` | `data/live_positions.json` | State file |
| `EXECUTION_TP_MOVE_PCT` | `0.016` | Matches Optuna best |
| `EXECUTION_RRR` | `2.5` | Reward/risk ratio |
| `EXECUTION_TTL_BARS` | `36` | H1 bars |
| `EXECUTION_RISK_PERCENT` | `1.5` | % of monthly base per trade |
| `EXECUTION_MAX_POSITIONS` | `1` | Max simultaneous open positions |
| `EXECUTION_MAX_LEVERAGE` | `25.0` | OKX isolated margin max |
| `EXECUTION_RISK_BASE_PERIOD` | `monthly` | Same as backtest |
| `EXECUTION_TAKER_FEE` | `0.0005` | 0.05% |
| `EXECUTION_MAKER_FEE` | `0.0002` | 0.02% |
| `EXECUTION_MAX_CAPITAL_RISK_PCT` | `10.0` | Circuit breaker |

---

## 4. Signal runner

`LiveSignalRunner.get_latest_signal(symbol) -> SignalRow | None`

1. Loads `CryptParquetDataLoader(data_dir, symbol, primary_timeframe="1h").load()`
   to get `StrategyData` with all H1/H4/D1 history.
2. Calls `crypt_ensemble.generate(strategy_data, params, backtest_args)` to
   produce the full signal DataFrame.
3. Returns the **last closed bar's row** if `signal != 0` and `sl_price` is
   not NaN, otherwise `None`.
4. A "closed bar" is any bar before the current forming bar — the same
   no-lookahead rule enforced by the backtester.

**Data freshness**: before calling `generate()`, the runner updates the Parquet
files by fetching recent bars from OKX via `OKXClient.fetch_ohlcv()` and
appending any bars newer than the last stored timestamp. This ensures the signal
frame is up to date at each H1 tick.

---

## 5. Risk calculator

`LiveRiskCalculator.calculate(symbol, signal_row, capital) -> RiskResult | None`

Mirrors `ExecutionSim._try_open_position()` exactly:

1. `risk_base_capital = monthly_risk_base(entry_time, capital)` — same logic as
   `ExecutionSim._risk_base_capital_for_entry()`: captures balance at the start
   of each calendar month.
2. `total_locked_margin = sum(pos.locked_margin for pos in open_positions[symbol])`
3. Calls `BasicRiskModel.calculate_position(EntryContext(...))`.
4. Checks `_can_open_position()` — leverage consistency, available balance.
5. Computes `fee_entry = taker_fee * position_value`.
6. Guards: `fee_entry < risk_value * 2` and `net_exposure >= min_net_exposure * balance`.

If any guard fails → returns `None` (do not trade).

---

## 6. Order placement

`OKXTradingClient.open_position(symbol, risk_result, dry_run) -> str | None`

Steps:
1. `await exchange.set_leverage(max_leverage, symbol, {'mgnMode': 'isolated'})`
2. Convert `risk_result.size` (asset units) to `contracts`:
   ```python
   market = exchange.market(ccxt_symbol)
   contracts = math.floor(risk_result.size / market['contractSize'])
   ```
   Minimum 1 contract. If `contracts < 1` → reject (position too small).
3. `side = 'sell' if short else 'buy'`
4. Place market order with embedded SL and TP:
   ```python
   await exchange.create_order(
       ccxt_symbol, 'market', side, contracts,
       params={
           'stopLoss': {'triggerPrice': exchange.price_to_precision(ccxt_symbol, sl_price)},
           'takeProfit': {'triggerPrice': exchange.price_to_precision(ccxt_symbol, tp_price)},
       }
   )
   ```
5. Returns OKX order ID (or `None` in dry_run).

**Symbol conversion**: OKX native `SOL-USDT-SWAP` → ccxt unified `SOL/USDT:USDT`
via `exchange.market_id(symbol)` reverse lookup after `load_markets()`.

---

## 7. Exit management

At each H1 tick, for each open position:

### 7a. SL/TP fill detection

Query OKX positions: `await exchange.fetch_positions([ccxt_symbol])`.
If the position for this `position_id` is no longer open (size = 0), it was
closed by SL or TP. Update state file with realized PnL from OKX trade history.

### 7b. TTL expiry

```python
ttl_expiry = position.entry_time + timedelta(hours=position.ttl_bars)
if datetime.now(UTC) >= ttl_expiry:
    # 1. Cancel OKX algo orders (SL/TP)
    await client.cancel_algo_orders_for_position(symbol, order_id)
    # 2. Place market close
    await client.close_position_at_market(symbol, opposite_side, contracts)
    # 3. Update state
```

This mirrors `ExecutionSim._update_active_positions()` where TTL fires at
`next_open` of bar `bar_opened + ttl_bars`.

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
  "schema_version": 1,
  "risk_window_month": [2026, 6],
  "monthly_risk_base": 10000.0,
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
      "status": "open"
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
2. For each position with `status = "open"`, queries OKX.
3. If OKX has no open position for that symbol → treat as externally closed,
   log INFO, remove from state.
4. If OKX has an open position → keep tracking.
5. Monthly risk base is read from state file; if missing (fresh start), set to
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

`src/crypt/__main__.py` registers a second periodic task alongside the existing
H4 tick:

```python
if settings.execution_enabled:
    scheduler.add_h1_job(execution_manager.on_h1_close)
```

The H1 job runs 5 seconds after each H1 close (same buffer as H4).
