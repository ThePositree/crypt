# Backtest harness (M2)

This document is the **contract** for the backtest harness that calibrates
the weight set in `config/weights.yaml` and produces the M2 exit-criteria
report. It is detailed on purpose: a future agent should be able to
implement this end-to-end without re-deriving the design.

If anything below contradicts `docs/architecture.md` or an ADR, **the ADR
wins** — flag the contradiction in chat and update this doc.

---

## 1. Goal

Replay the live pipeline against historical OKX H4 data so we can:

1. Estimate **per-engine hit rate** (how often each engine's direction
   matches the actual next-N-bar return sign).
2. Estimate **ensemble expectancy** (average return per BUY/SELL alert,
   net of fees and slippage).
3. Produce a **calibrated `weights.yaml`** — i.e. per-regime weights and
   per-regime decision thresholds that maximise expectancy on a held-out
   slice of history.
4. Surface **where the model is fragile** (regimes / symbols / market
   periods with negative expectancy, drawdown clusters, look-ahead leaks).

The harness is **not** a trading simulator. It evaluates verdicts, not
fills. The trading simulator is `docs/paper_trading.md` (M3).

---

## 2. Non-goals

- Tick-level replay. We replay H4 closed candles only. Intra-candle
  evolution of OI / funding is out of scope (and we do not have that data).
- Multi-venue replay. OKX only, same as live (ADR-0002).
- Genetic / Bayesian hyperparameter optimisation. Grid + coordinate
  descent is enough at this scale; record the choice as an ADR if you
  decide otherwise.

---

## 3. CLI surface

```bash
uv run python -m crypt.backtest \
    --from 2025-01-01 \
    --to   2026-05-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --weights config/weights.yaml \
    --report-dir reports/backtest_2026-05/ \
    [--no-fees] [--slippage-bps 5] [--walk-forward-folds 5]
```

Required:
- `--from`, `--to` (ISO date, UTC).
- `--symbols` (comma-separated OKX `instId`).

Optional:
- `--weights` — path to weights YAML (defaults to `config/weights.yaml`).
- `--report-dir` — where to put the HTML report + CSV artefacts.
- `--no-fees` — skip the fee model (debugging only).
- `--slippage-bps` — override the default slippage (see §7).
- `--walk-forward-folds N` — see §8.
- `--seed N` — for bootstrap CI reproducibility.

Exit codes:
- `0` — completed and report written.
- `1` — data preconditions failed (e.g. not enough history for a symbol;
  see §5).
- `2` — runtime error in the replay loop.

---

## 4. Data preconditions

The harness must refuse to start if any of these is false. Print a clear
error message and exit `1`.

- For each symbol in `--symbols`, the parquet store contains at least
  `H4` candles spanning `[from - 250 * 4h, to]` (so EMA200 has warm-up).
- For each symbol, funding history covers at least `[from - 7d, to]`.
- For each symbol, OI history (`1h`) covers at least `[from - 7d, to]`.
- L/S ratio history is optional; if missing, log a WARNING and disable
  the L/S sub-signal in the derivatives engine (same as live).
- All input parquet files pass schema validation:
  - `open_time` monotonic, no duplicates, `tz=UTC`.
  - No gaps larger than `2 * timeframe` (one missed bar is tolerated).

If the dataset fails preconditions, the agent should first run the
backfill CLI (see §13) to refill the store.

---

## 5. Replay loop

Conceptually:

```python
for tick_time in iterate_h4_boundaries(from_, to):
    for symbol in symbols:
        ctx = ContextBuilder(store).build(symbol, tick_time)
        # IMPORTANT: store must return only candles with open_time < tick_time
        signals = run_engines(ctx, weights)
        regime  = signals.regime
        verdict = aggregate(signals, regime, weights)
        verdict = decision_filter.apply_guard(verdict)
        recorder.record(verdict, tick_time)
```

### 5.1 No look-ahead bias — hard contract

Every test in `tests/backtest/` must enforce this invariant:

> At `tick_time = T`, no engine has access to any datum with
> `open_time >= T` (candles) or `ts >= T` (funding/OI/LS-ratio).

Implementation:

- `ContextBuilder.build(symbol, T)` must filter `df = df[df.open_time < T]`
  before returning to engines. Live code does this implicitly because new
  data has not landed yet; backtest must do it explicitly.
- Replay-only seam: a `ReplayParquetStore` wraps `ParquetStore` and
  enforces the `open_time < T` filter at the store level — engines stay
  unchanged.
- The "future bar" used to label the outcome (§6) is loaded via a separate
  helper, never via `ContextBuilder`.

Write a regression test that deliberately injects future data and asserts
the result changes (i.e. the harness was leaking). It should fail before
the filter is added and pass after.

### 5.2 Replacing live sinks

In backtest:
- `TelegramSink` — replaced by a no-op.
- `JsonLogSink` — replaced by `BacktestRecorder` that appends verdicts to
  an in-memory list and writes a single parquet at the end.
- `ConsoleSink` — kept (optional `--quiet` flag to silence it).
- `ExecutionStub` — replaced by `BacktestExecutionSimulator` (see §7).

### 5.3 Reproducibility

- `--seed` controls every `random.*` call in the run (jitter in
  `TelegramSink` should be skipped entirely since the sink is no-op, but
  if a future engine ever uses `random`, it must accept a seeded RNG).
- The harness must persist `git_sha`, `weights_sha`, `dataset_window`,
  `seed`, and `--slippage-bps` in `reports/.../meta.json`. Two runs with
  the same meta must produce identical reports.

---

## 6. Outcome labelling

For each verdict produced at `tick_time = T`, compute:

- `return_h4 = (close[T + 4h] - close[T]) / close[T]` — single-bar forward
  return. Used only if the candle at `T + 4h` is fully present and closed
  in the dataset.
- `return_h24 = (close[T + 24h] - close[T]) / close[T]` — 6-bar forward
  return.
- `return_h96 = (close[T + 96h] - close[T]) / close[T]` — 4-day forward
  return (matches the typical hold-time for an H4 swing).
- `mae` (maximum adverse excursion) and `mfe` (maximum favourable
  excursion) over `[T, T + 96h]` — for SL/TP analysis.

Drop the **last** `96h / 4h = 24` ticks from the dataset because their
forward labels are not fully observed.

The "hit" definition per timeframe:
- `hit_h4 = sign(return_h4) == sign(direction_intent)` for `bullish` →
  `+1`, `bearish` → `-1`. `neutral` verdicts are excluded from hit-rate.

Use `h24` as the default for the report headline. Show `h4`, `h24`, `h96`
side-by-side: the right horizon for our H4 engine is an empirical
question.

---

## 7. Fee and slippage model

Apply to every BUY/SELL verdict (HOLD verdicts have no fee).

### 7.1 Fee rates

- OKX perpetual swap: maker = `0.02%`, taker = `0.05%` (verify via
  Context7 at implementation time — fee schedule changes).

### 7.2 Entry vs exit fee asymmetry

This is the most important nuance missed in naive models:
**entry and different exit types use different fee rates**.

| Event | Order type | Fee rate |
|-------|-----------|----------|
| Entry (market reaction to signal) | Taker | `0.05%` |
| Exit via Take Profit (resting limit) | Maker | `0.02%` |
| Exit via Stop Loss (market order) | Taker | `0.05%` |
| Exit via TTL timeout (market order) | Taker | `0.05%` |

Reference: `backtester/src/backtester/fee_model.py` —
`StaticPercentFeeModel.calculate_exit_fee()` (line 117) applies
`maker_fee` when `is_maker=True` (TP exits), `taker_fee` otherwise.

Using a single taker fee for all exits over-penalises TP exits by ~2.5×
and makes calibrated weights unnecessarily conservative.

### 7.3 Slippage

- `--slippage-bps` (default `5 bp = 0.05%`). Applied per side (entry
  and exit separately); per round-trip: `2 * slippage_bps`.

### 7.4 P&L formula

For a verdict at horizon `h`:

```
pnl_gross = return_h * direction_sign   # +1 BUY, -1 SELL
pnl_net   = pnl_gross
            - taker_fee                  # entry
            - exit_fee(exit_type)        # see table above
            - 2 * slippage_bps
```

For verdict-level forward-label evaluation (§6) we do not know the
actual exit type at label time. Use the **expected** exit fee:

```
expected_exit_fee = win_rate * maker_fee + (1 - win_rate) * taker_fee
```

Bootstrap the win rate from the first fold; use `taker_fee` as a
conservative fallback if win rate is unknown.

### 7.5 Min net-exposure guard

Reject an entry if the fee alone exceeds the expected risk reward:

```python
if fee_entry >= risk_value * 2:
    skip_entry()
```

Reference: `backtester/src/backtester/execution_sim.py` line 730.
This prevents entries where the fee consumes the entire expected gain.

Document all fee/slippage values in `reports/.../meta.json` so future
re-runs are comparable.

---

## 8. Walk-forward validation

Single train/test split is forbidden — it leaks the future into weights.

Required scheme: **expanding-window walk-forward** with `--walk-forward-folds N`
folds.

```
fold k uses:
    train = [from, from + (T/N) * (k+1)]
    test  =        [from + (T/N) * (k+1), from + (T/N) * (k+2)]
```

For each fold:
1. Use `train` slice to optimise weights (see §9).
2. Evaluate the fitted weights on `test` slice.
3. Record test-only expectancy.

The **headline number** in the M2 report is the mean test-slice expectancy
across folds, with bootstrap CI (§10).

If `N = 1` (single split), the harness must print a WARNING that the
result is not robust.

---

## 9. Weight optimisation

Given a train slice:

### 9.1 Search space

For each regime in `{TRENDING, RANGING, HIGH_VOL}` and each directional
engine in `{trend, meanrev, derivatives}`:

- Weight grid: `[0.0, 0.1, 0.2, ..., 0.9, 1.0]`, constrained to
  `sum_engines = 1.0` per regime.
- Threshold grid (per regime, on `|score|`): `[0.15, 0.20, ..., 0.55]`.

This gives `O(11^3 * 9) ≈ 12k` combinations per regime, times 3 regimes —
tractable.

### 9.2 Objective

Maximise: `mean(pnl_net) - 0.5 * std(pnl_net)` on the train slice
(Sharpe-like, but additive cost).

Tie-breaker: prefer the combination with the **lowest** number of alerts
(fewer trades → lower operational cost and less p-hacking).

### 9.3 Algorithm

1. **Grid search** (cheap, parallelisable, exhaustive).
2. **Coordinate descent** to refine: starting from the grid winner, vary
   one variable at a time on a 5x finer grid; stop when no variable
   improves the objective.

Skip Bayesian optimisation / genetic algos at this scale unless a future
ADR motivates it.

### 9.4 Sanity guard

After optimisation, refuse to write the new `weights.yaml` if any of:

- Any single engine has weight `1.0` in any regime (over-fit one-engine
  policy).
- Train-test expectancy gap > 50% relative (over-fit).
- Test-slice expectancy < 0 (calibrated weights are worse than nothing).

If guard fires, write `weights.candidate.yaml` instead and an `WARNING:
optimisation produced suspicious weights, see §9.4` line in the report.

---

## 10. Bootstrap confidence intervals

For every headline metric (hit rate, expectancy, drawdown), produce a 95%
bootstrap CI by resampling verdicts **with replacement** N = 1000 times,
recomputing the metric, and taking the 2.5th / 97.5th percentile.

When the CI of expectancy crosses zero, label the result `NOT
SIGNIFICANT` in red on the report. We must not be misled by point
estimates.

---

## 11. Baseline comparison

Every report must include these baselines for context:

1. **Buy-and-hold** of each symbol over the test slice (long only).
2. **Always HOLD** (zero return, zero cost).
3. **Random direction** with the same alert frequency as the ensemble,
   averaged over 100 seeds.

An ensemble that does not beat all three (with overlapping or higher CI)
is **not** a strategy; flag this loudly in the report.

---

## 12. Report contents (`reports/<timestamp>/`)

Files produced:

- `meta.json` — git_sha, weights_sha, dataset window, fee/slippage, seed.
- `summary.html` — single-page report (no server; just `<html>`).
- `verdicts.parquet` — all verdicts produced during replay.
- `weights.optimal.yaml` — best weights per fold.
- `weights.recommended.yaml` — production candidate (intersection of
  folds; see §13).
- `figures/*.png` — charts referenced by `summary.html`.

`summary.html` must contain, in order:

### 12.1 Headline metrics table

Per `(symbol, fold)` and aggregated across all folds:

| Metric | Description |
|--------|-------------|
| `total_alerts` | BUY + SELL count |
| `alerts_per_day` | Frequency check |
| `win_rate` | `hits / total_alerts` (direction correct) |
| `profit_factor` | `sum(wins) / abs(sum(losses))` — a PF > 1 means the strategy earns more than it loses |
| `expectancy` | `mean(pnl_net)` per alert with 95% bootstrap CI |
| `total_return_pct` | `(final_capital - initial) / initial * 100` |
| `max_drawdown` | Rolling peak-to-trough as `%` (negative value) |
| `sharpe_ratio` | Annualized Sharpe from monthly returns: `(MR - RFR_monthly) / SD_monthly * sqrt(12)` |
| `avg_holding_bars` | Average H4 bars between alert and exit |

Reference implementation for all these metrics:
`backtester/src/backtester/results_analyzer.py` — `ResultsAnalyzer.generate()`.
The Sharpe calculation at lines 186–225 is tested and correct for
monthly resampling; port it directly.

Show each metric with its bootstrap CI (§10). Flag `NOT SIGNIFICANT`
in red when the expectancy CI crosses zero.

### 12.2 Long / short breakdown

Separate the headline table by direction. The ensemble may have
asymmetric quality for BUY vs SELL — this is the most common fragility
in momentum-based systems.

Reference: `backtester/src/backtester/results_analyzer.py` —
`_compute_side_metrics()` (lines 277–286).

### 12.3 Exit distribution

Count `take_profit / stop_loss / ttl_expired` exits. A healthy system
has a TP rate consistent with the win rate. An unusually high TTL rate
suggests signals that neither hit target nor stop — a sign of underpowered
signals.

Reference: `backtester/src/backtester/results_analyzer.py` —
`_compute_exit_distribution()` (line 153).

### 12.4 Equity curve

Per symbol per fold (matplotlib → PNG embedded). Use `capital_after`
timeline from the trade recorder.

### 12.5 Monthly returns table

```
Month      MoM return (%)   Cumulative (%)
2025-01    +3.2             +3.2
2025-02    -1.4             +1.8
...
```

Reference: `backtester/src/backtester/results_analyzer.py` —
`_compute_monthly_returns_pct()` (lines 228–253).

### 12.6 Per-engine contribution

Shapley-like decomposition: if too expensive, use
`weighted_contribution = weight * strength_at_alert`.

### 12.7 Fragility section

Which 10% of weeks contained 50% of the loss? Regime-flip frequency,
alert clustering, most-frequent `inputs_missing`.

### 12.8 Baselines comparison

See §11.

### 12.9 Critique paragraph

Owner-readable, explicitly listing where the model is fragile.

---

## 13. Recommended weights file

Across folds, weights vary. Producing **the** `weights.yaml` requires
taking an intersection.

Rule: for each `(regime, engine)`, take the **median** weight across
folds, then renormalise per regime to sum to `1.0`. For thresholds, take
the **max** (conservative — fewer false alerts).

Justification: median dampens outliers from a single fold; max threshold
biases towards under-trading. Both are recoverable by the operator
turning the knob in production.

---

## 14. Backfill CLI (precondition for backtest)

Full contract: **`docs/backfill.md`**. ADR: **`docs/decisions/0015-coinglass-historical-backfill.md`**.

Separate CLI: `uv run python -m crypt.backfill`.

```bash
# Recommended for M2: OHLCV from OKX, deep derivatives from Coinglass
PYTHONPATH=src uv run python -m crypt.backfill \
    --source coinglass \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 \
    --to   2026-05-01 \
    [--data-types ohlcv,funding,oi,ls_ratio] \
    [--page-size 100] \
    [--max-rps 5]
```

OKX-only (shallow derivatives history):

```bash
PYTHONPATH=src uv run python -m crypt.backfill \
    --source okx \
    --symbol SOL-USDT-SWAP \
    --from 2024-01-01 \
    --to   2026-05-01
```

Implementation notes:
- Pagination per vendor endpoint (OKX max 100; Coinglass max 1000 per call).
- Resume safety: re-running must not produce duplicates (rely on
  `_upsert` in `ParquetStore`; duplicate `ts` → last write wins).
- Operator order when mixing sources: Coinglass historical pass first,
  then OKX pass to overwrite recent rows with exchange-native values
  (`docs/backfill.md` §2).
- Progress bar in stdout (tqdm).
- Logs every page fetched with time boundary so failures are diagnosable.

This CLI is a precondition for §4 — agents must run it before the first
backtest. For meaningful `derivatives` weight calibration, Coinglass
backfill is required for windows longer than ~90 days.

---

## 15. Tests

`tests/backtest/`:

- `test_no_lookahead.py` — inject a future bar into the dataset, assert
  the ContextBuilder filters it out; reverse: inject and bypass the
  filter, assert the deliberately-rigged engine "knows" the future (proof
  the test would catch a real leak).
- `test_walk_forward_split.py` — given a synthetic 1-year dataset with
  `--walk-forward-folds 4`, assert no test slice ever appears in any
  train slice.
- `test_grid_search_smoke.py` — tiny grid, tiny dataset, assert the loop
  completes without raising.
- `test_baseline_buy_and_hold.py` — handcrafted dataset; assert reported
  buy-and-hold matches manual computation.
- `test_fees_and_slippage.py` — assert `pnl_net = pnl_gross - round_trip_cost`.
- `test_sanity_guard.py` — feed weights that hit guard rules, assert
  `weights.candidate.yaml` is produced instead of `weights.optimal.yaml`.

---

## 16. Known limitations (be honest in the report)

- H4 forward labels look 96h ahead — only ~2200 non-overlapping samples
  per symbol per year. Statistical power is modest.
- OKX OI snapshot timing is opaque; large OI deltas may be exchange
  bookkeeping, not market activity. Robust z-score normalisation absorbs
  some of this but not all.
- **Derivatives history provenance:** when Coinglass backfill is used
  (ADR-0015), backtest `derivatives` signals come from Coinglass OKX
  pair history; live/paper uses OKX Rubik directly. Report must state
  `data_provenance: coinglass+okx` and note possible train/live drift.
- XPL has < 1 year of history at the time of writing — its per-symbol
  results will have wide CIs. The report must surface this. XPL may also
  be absent from Coinglass — verify before backfill.
- Walk-forward with 5 folds means each test slice is ~10 weeks. Regime
  transitions that span only one fold can produce misleading per-regime
  expectancy. Add per-week granularity charts in the report so the
  operator can see this.
- Fee schedule and slippage are **assumptions**, not measurements. They
  affect the rank order of weight candidates only mildly; the
  `--no-fees` ablation in the report shows how much.

---

## 17. Workflow for the agent who builds this

1. Read this doc fully.
2. Read `docs/architecture.md` §6 (backtest section).
3. Read §18 (reference implementation) below — do not reinvent wheel.
4. Implement `src/crypt/backtest/replay.py` with `ReplayParquetStore` first
   (the look-ahead guard).
5. Write `tests/backtest/test_no_lookahead.py` next — this is the single
   most important test in the milestone.
6. Implement the recorder, then the optimiser, then the report.
7. Run backfill CLI to populate ≥ 1 year of history for SOL/TON/XPL.
8. Run `--walk-forward-folds 5` and inspect the report.
9. Commit `weights.recommended.yaml` to `config/weights.yaml` once
   sanity guards pass.
10. Write a new ADR if any design point above was changed.
11. Append a CHANGELOG entry describing what the report says.

---

## 18. Reference implementation: `backtester/`

There is a battle-tested backtester in `backtester/` (a separate git repo
nested inside `crypt/`). The owner has run it in production and trusts it.
**Do not reinvent anything that already exists there.** Port or adapt
directly; add a comment citing the source file.

The backtester's architecture does not plug directly into crypt's pipeline
(different entry point, BingX-centric data loader, strategy-based rather
than engine-based) — but its **execution simulation, risk model, fee model,
and metrics computation are directly reusable**.

### 18.1 What to port

#### Execution simulation — `BacktestExecutionSimulator`

Our `BacktestExecutionSimulator` (§5.2) should be adapted from
`backtester/src/backtester/execution_sim.py` — `ExecutionSim` class.

Key mechanics proven correct:

**Entry timing** (lines 690–697): signal fires on bar `i`; position opens
at `bar[i+1].open`. Optional `entry_price` column allows intra-bar entries
within `[low, high]`.

**Intra-bar TP/SL ambiguity** (lines 523–586, `_resolve_bar_exit`): when
both TP and SL lie within the same bar's `[low, high]` range, the true
exit order is unknowable from OHLC data. The backtester resolves this via
a configurable policy:

```python
bar_exit_policy = "worst_case"   # conservative default — prefer SL
bar_exit_policy = "best_case"    # optimistic — prefer TP
```

Always use `worst_case` in our backtest (pessimistic, prevents overfitting
to bars where both were touched). Report both in the report so the owner
can see the spread.

**Exit types and TTL** (lines 459–520): three exit reasons —
`take_profit`, `stop_loss`, `ttl_expired`. TTL forces close at
`bar[TTL+1].open` with taker fee. For H4 horizon, a TTL of 6 bars (24h)
is a reasonable default; expose as `--position-ttl-bars`.

**Position sizing formula** (lines 189–193 in `risk_model.py`):
```python
risk_value     = available_balance * (risk_percent / 100)
sl_dist        = abs(entry_price - sl_price)
size           = risk_value / sl_dist
position_value = size * entry_price
```
SL price for crypt verdicts: use `entry_price - SL_ATR_MULT * atr_h4`
(same formula as paper trading in §5 of `docs/paper_trading.md`).

**Leverage and margin checks** (`risk_model.py` lines 196–213): guard
against leverage exceeding `max_allowed_leverage`. For OKX H4 with
default ATR-based SL, typical leverage is 3–8×; cap at 20× for safety.

**Isolated futures mode** (lines 326–353 in `execution_sim.py`): when
multiple positions are open, locked margin reduces available balance.
Use `is_isolated_futures=True` when simulating multi-symbol runs to avoid
over-counting capital.

**Daily limits** (lines 879–909): `max_daily_profit` and
`max_daily_loss` in RRR units. Useful for the sanity guard: a day with
`daily_rrr > 10` is probably a data artefact, not a real trading day.

**Trade record columns** (line 493–514, `trade_history.append(...)`).
Exact set our `BacktestRecorder` must emit:
```
entry_time, exit_time, entry_price, exit_price, size,
pnl_abs, pnl_rel, fee_entry, fee_exit, tp_price, sl_price,
exit_reason, capital_before, capital_after, holding_bars,
leverage, is_long, entry_bar_index, exit_bar_index
```

#### Fee model — `FeeModel` / `StaticPercentFeeModel`

Port `backtester/src/backtester/fee_model.py` verbatim; it is 140 lines.
The `FeeModel` abstract class is clean and allows future customisation
(e.g. tiered fees, funding-rate-adjusted fees) without touching the sim.

```python
class FeeModel:
    def calculate_entry_fee(self, position_value, ctx) -> float: ...
    def calculate_exit_fee(self, exit_value, *, is_maker, ctx) -> float: ...
```

#### Risk model — `RiskModel` / `BasicRiskModel`

Port `backtester/src/backtester/risk_model.py` verbatim; it is 234 lines.
`EntryContext` and `RiskResult` are frozen dataclasses — clean contract
between the sim loop and the sizing logic.

#### Metrics — `ResultsAnalyzer`

`backtester/src/backtester/results_analyzer.py` contains all metric
formulas we need (see §12). Port the following methods directly:

| Method | Lines | What |
|--------|-------|------|
| `_compute_basic_metrics` | 96–137 | win rate, profit factor, avg win/loss |
| `_compute_drawdown_metrics` | 178–183 | rolling max-drawdown |
| `_compute_sharpe_ratio` | 186–225 | annualized Sharpe (monthly resampling) |
| `_compute_monthly_returns_pct` | 228–253 | monthly returns table |
| `_compute_exit_distribution` | 152–155 | TP/SL/TTL counts |
| `_compute_side_metrics` | 277–286 | long/short split |

These methods are pure functions of a `pd.DataFrame` of trades — they
have no dependency on the rest of the backtester and can be copy-pasted
into `src/crypt/backtest/metrics.py`.

#### Tests as patterns

`backtester/tests/test_execution_sim_run.py` and
`backtester/tests/test_risk_fee_models.py` show the correct way to write
simulation tests: construct a minimal OHLCV `pd.DataFrame` with explicit
values, run the sim, and verify **exact numeric results** (using
`pytest.approx`). No mocks, no fixtures with side effects.

Adapt the following test patterns for `tests/backtest/`:
- `test_basic_long_take_profit_path` — verify math from first principles
- `test_intrabar_policy_best_case_prefers_take_profit` — the ambiguity
  test; port both best_case and worst_case variants
- `test_fee_too_large_blocks_position` — the min-net-exposure guard
- `test_ttl_expiration_exit` — TTL at `holding_bars == ttl_bars`

### 18.2 What NOT to port

| Module | Why |
|--------|-----|
| `backtester/src/backtester/strategies/` | Strategy classes; our engines are the replacement |
| `backtester/src/backtester/data_loader.py` (BingX loader) | We use OKX via ccxt; BingX is irrelevant |
| `backtester/src/backtester/optimizer.py` | Uses Optuna; we use grid + coord-descent (§9) |
| `backtester/src/backtester/trade_analyzer.py` | Predicate-feature AUC/KS analysis; out of M2 scope |
| `backtester/scripts/` | Streamlit dashboards; our report is static HTML |
| `backtester/src/gui/` | GUI app; out of scope |

### 18.3 Integration sketch

```
crypt/backtest/
├── replay.py          # ReplayParquetStore (look-ahead guard)
├── recorder.py        # BacktestRecorder → trades.parquet
├── execution_sim.py   # Ported from backtester/src/backtester/execution_sim.py
├── fee_model.py       # Ported from backtester/src/backtester/fee_model.py
├── risk_model.py      # Ported from backtester/src/backtester/risk_model.py
├── metrics.py         # Ported from backtester/src/backtester/results_analyzer.py
├── optimizer.py       # Grid + coord-descent (new, see §9)
├── report.py          # HTML report generator (new)
└── __main__.py        # CLI entry point
```

The ported files should have a header comment:
```python
# Adapted from backtester/src/backtester/<original_file>.py
# Original: https://github.com/AuriumX/backtester
```

### 18.4 Known issues in the backtester — fix before use

These are problems found after detailed code review. Some are bugs, some
are simulation inaccuracies. All must be addressed during porting.

---

#### 🔴 Critical: `is_perpetual` is dead code — funding rate is not modelled

`execution_sim.py:155` — `is_perpetual: bool = False` is stored but never
used anywhere. There is no `if self.is_perpetual` in the entire file.

For OKX perpetual swaps, funding is charged every 8 hours. A position
held for the default TTL of 24 H4 bars (= 96 hours) accumulates 12
funding payments. At a calm rate of 0.01%/8h that is **0.12% unrealised
cost**, comparable to the round-trip fee. In high-funding periods
(0.1%/8h) it reaches **1.2% per position** — a number that will
materially affect weight calibration.

**Fix when porting**: add a `FundingRateModel` interface alongside
`FeeModel`. On each bar where a position is open, charge
`position_value * funding_rate_at_bar_open`. The funding data is already
in our Parquet store (`crypt/data/store.py`). A `ZeroFundingModel` can be
the default for backward-compatibility / `--no-funding` flag.

---

#### 🔴 Critical: single-asset architecture — capital is not shared

`Backtester(df, strategy)` takes one DataFrame for one symbol. Running
three independent `ExecutionSim` instances would give each its own full
`initial_capital`, tripling the simulated capital. There is no concept of
a shared pool in the backtester.

**Fix when porting**: run a single `ExecutionSim` whose input DataFrame is
the time-ordered union of signals from all three symbols. Each row carries
a `symbol` column so the recorder can group by symbol. Use
`is_isolated_futures=True` so locked margin per open position reduces the
available balance for subsequent entries.

---

#### 🟡 Important: SL fills at exact SL price — gap risk is missing

`execution_sim.py:572`:
```python
return ExitReason.STOP_LOSS, pos.sl_price
```

OKX stop-market orders execute at the best available price after
triggering, not at the trigger price. When price gaps through the SL
(e.g. a candle opens below SL for a long), the actual fill is at the
open, which can be significantly worse.

**Fix when porting**: for a long position, use
`exit_price = min(sl_price, current_bar_open_if_gapped_below_sl)`.
Practically: if `current_bar_low <= sl_price` AND
`current_bar_open < sl_price`, use `current_bar_open` as the fill price.
This requires passing `current_bar_open` into `_resolve_bar_exit`.

For H4 on liquid pairs (SOL, TON) the bias is small. For XPL or in
high-volatility regimes it can be meaningful. At minimum, expose a
`--sl-pessimism-pct` CLI flag that adds a fixed percentage slippage to
all SL exits (e.g. `--sl-pessimism-pct 0.1` = SL fills 0.1% worse than
the trigger price).

---

#### 🟡 Important: equity curve loses trades with equal `exit_time`

`results_analyzer.py:162`:
```python
equity.drop_duplicates(subset="exit_time", keep="last", inplace=True)
```

When two positions close on the same bar (which happens constantly in our
multi-symbol setup), only the last trade's `capital_after` survives in
the equity curve. `total_pnl_abs` is unaffected (it sums `pnl_abs`
directly), but **Sharpe ratio and drawdown are computed from the equity
curve** and will be wrong.

**Fix when porting**: do not drop duplicates. Instead, reconstruct the
equity curve by sorting all trades by `exit_time, entry_time` and
computing a running capital sum:
```python
trades_sorted = trades.sort_values(["exit_time", "entry_time"])
equity_curve  = trades_sorted.set_index("exit_time")["capital_after"]
```
Accept that multiple points can share a timestamp; `resample("ME").last()`
in the Sharpe calculation handles this correctly.

---

#### 🟡 Important: drawdown ignores unrealised P&L

`_compute_drawdown_metrics` builds the equity curve from `capital_after`
at trade-close events only. Between a position's entry and close, there
is no mark-to-market. A position that loses 40% unrealised intrabar and
then recovers to -5% at close will show max drawdown -5%, not -40%.

**Consequence for M2**: the reported max drawdown will be optimistic.
The weight optimiser's objective (§9) does not see drawdown peaks that
occur intra-position.

**Fix**: if funding data is available bar-by-bar (it will be, because we
need it for funding charges), build a parallel mark-to-market equity
series by computing `unrealised_pnl` on each bar for open positions and
inserting those data points into the equity curve before computing
drawdown. If too expensive, document the limitation explicitly in the
report (§16 lists it).

---

#### 🟠 Minor: `exit_time` is recorded as `next_time` (off by one bar)

`execution_sim.py:497`: `"exit_time": next_time`

When a TP or SL fires within bar `i`'s range, the fill happened sometime
during bar `i`. But `next_time` is bar `i+1`'s open timestamp. The trade
record timestamps the exit ~4 hours later than it actually occurred.

This does not affect P&L (exit price is correct). It does affect:
- `holding_bars` is overstated by 1 for every TP/SL exit
- Trade timestamps are confusing to read in the CSV/Parquet output

**Fix when porting**: use `df.index[i]` (current bar's close time) as
`exit_time` for TP/SL exits. Keep `next_time` only for TTL exits (which
genuinely execute at the next bar's open).

---

#### 🟠 Minor: Sharpe is unreliable for short test slices

`results_analyzer.py:211–225` — Sharpe is computed from monthly-resampled
returns. With 5 walk-forward folds on 1.5 years of H4 data, each test
slice is roughly 10 weeks (≈2.5 months). Two to three monthly data
points give a Sharpe with enormous confidence intervals.

**Fix when porting**: if `n_monthly_samples < 6`, print a visible warning
in the report:
```
⚠ Sharpe ratio computed from only N months — not statistically reliable.
```
As a complement, also report a **trade-level Sharpe**:
`mean(pnl_net) / std(pnl_net) * sqrt(annualised_trade_freq)`,
which uses all individual trades and is more stable for small samples.

---

#### 🔵 Trivial: redundant inner `if` in daily-limit logic

`execution_sim.py:880` and `894` — the same condition
`if self.max_daily_profit or self.max_daily_loss` appears twice,
the second nested inside the first. Harmless, but note that this
condition evaluates `max_daily_profit = 0` as **falsy**, silently
disabling the limit. The inner guards on lines 898 and 904 correctly
check `is not None and > 0`, so no actual bug, but the outer condition
is misleading.

---

#### Summary table

| Issue | Severity | P&L impact | Fix |
|-------|----------|-----------|-----|
| Funding rate not modelled | 🔴 Critical | Up to 1.2% per trade | Add `FundingRateModel` |
| Single-asset, capital not shared | 🔴 Critical | Capital tripled in multi-symbol | Unified multi-symbol sim |
| SL fills at exact trigger price | 🟡 Important | Optimistic bias, ~0.1–0.5% | Gap-adjusted exit price |
| Equity curve drops duplicate exit timestamps | 🟡 Important | Wrong Sharpe/drawdown | Remove `drop_duplicates` |
| Drawdown ignores unrealised PnL | 🟡 Important | Drawdown understated | Mark-to-market equity curve |
| `exit_time` off by one bar | 🟠 Minor | None (metadata only) | Use bar `i` close timestamp |
| Sharpe unreliable for ≤ 6 months | 🟠 Minor | Misleading metric | Warning + trade-level Sharpe |
| Redundant `if` in daily limits | 🔵 Trivial | None | Cleanup |
