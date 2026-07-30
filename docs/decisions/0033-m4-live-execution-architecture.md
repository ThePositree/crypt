# ADR-0033: M4 live execution module architecture

- **Status**: accepted
- **Date**: 2026-06-09
- **Owner**: owner direction in chat (explicit mandate override — no promoted candidate yet)

## Context

ADR-0025 originally framed the benchmark as a gate before live order routing.
The owner explicitly overrode that gate in chat and requested M4 auto-execution
to begin before a benchmark-quality candidate existed. Current project docs
therefore treat `docs/strategy_benchmark.md` as an optimization/reporting
target, while owner production selection remains authoritative.

This ADR records the architectural decisions for the live execution module so that
future agents can understand the design rationale and constraints.

## Decisions

### 1. Signal parity: run `crypt_ensemble.generate()` on live Parquet

The live execution module does **not** use `Verdict` objects from the M1 alert
pipeline. Instead, it loads the same OHLCV Parquet files that the backtester
uses and calls `crypt_ensemble.generate()` directly on that data at each H1 close.

**Rationale**: the benchmark result was evaluated using this exact code path.
Any deviation — even using a different signal format — would mean trading a
different strategy than the one that was backtested. The only accepted coupling
point between backtest and live trading is the `StrategyData → crypt_ensemble →
signal_row` interface.

### 2. Risk model parity: `BasicRiskModel` with identical params

Position sizing uses `backtester.risk_model.BasicRiskModel` with the same
execution parameters as the backtest run that was evaluated against the benchmark.
The `risk_base_period = "monthly"` logic is replicated exactly: at the start of
each calendar month, the current OKX USDT equity is recorded as the monthly base
and used for all risk calculations that month.

### 3. OKX order placement: embedded SL/TP via single `createOrder`

When OKX executes a market entry, SL and TP are attached as algo parameters in
one `create_order` call via ccxt:

```python
params = {
    "stopLoss": {"triggerPrice": sl_price},
    "takeProfit": {"triggerPrice": tp_price},
}
```

OKX creates conditional algo orders on its side. We do **not** separately place
limit orders for TP or stop-market orders for SL — OKX handles both natively.

This simplifies order tracking: one `position_id` mapped to the entry order ID.

### 4. TTL exits: wall-clock time, not bar index

The simulator counts `position_ttl_bars` (H1 bars) using positional bar indices.
In live execution, TTL is implemented as a wall-clock deadline:

```
ttl_expiry = entry_time + ttl_bars × 1 hour
```

At each H1 tick, if `now >= ttl_expiry`: cancel OKX algo orders, place market
close. This is equivalent to the simulator's bar-index TTL under the assumption
that H1 bars are continuous (no gaps longer than 1h in OKX perpetual swap data).

### 5. Isolated margin leverage: always 25× (ADR-0029)

The simulator always uses `max_allowed_leverage = 25` for isolated margin
(matching OKX perpetual swap max). The live module calls `set_leverage(25,
symbol, {'mgnMode': 'isolated'})` before each entry, enforcing the same
constraint.

### 6. `dry_run = True` by default

All order placement functions accept a `dry_run` flag. When `True`, the module
logs what it would do but makes no API calls. Must be explicitly set to `False`
in `.env` (`EXECUTION_DRY_RUN=false`) to place real orders.

### 7. State persistence: `data/live_positions.json`

Active positions are persisted to disk as JSON after every state change. On
restart, the manager reads this file and reconciles with OKX positions. Positions
that exist in the file but not on OKX are treated as externally closed (SL/TP
filled or manually closed).

### 8. Scheduler: separate H1 loop

The existing M1 H4 scheduler is not modified. The execution module registers its
own H1-aligned loop in `__main__.py`. H1 close detection reuses the same
`_CLOSED_SAFETY_BUFFER` logic from `OKXClient.fetch_ohlcv`.

## Consequences

- Signal logic in `crypt_ensemble.py` is now load-bearing for real money. Any
  change to `crypt_ensemble.generate()` is a trading parameter change and must
  be tagged in CHANGELOG with the execution impact.
- If the Parquet data has a gap (missing H1 bars), the executor skips that tick
  and logs WARNING. It does **not** assume the last known signal still applies.
- Funding rate PnL is not tracked. Live equity will diverge from backtest equity
  over long holds. Known bias, documented in `docs/execution/live_execution.md`.

## Override note

This ADR is conditional on the owner's explicit mandate override. If a candidate
is later promoted and re-evaluated, the override should be revisited and the
relevant mandate gate re-tested against the live execution record.
