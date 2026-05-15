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

- Fees: OKX perpetual swap maker = `0.02%`, taker = `0.05%` (verify in
  Context7 at implementation time — fee schedule changes). Assume **taker**
  for BUY/SELL since we are reacting to a fresh signal.
- Slippage: `--slippage-bps` (default `5 bp = 0.05%`). Per round-trip:
  `2 * slippage_bps`.
- Total cost per round-trip: `2 * 0.05% + 2 * 5bp = 0.20%`.

`pnl_net = return_horizon * direction_intent - round_trip_cost`.

Document the fee/slippage values in `reports/.../meta.json` so future
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

1. Headline table: expectancy, hit rate, drawdown, alerts/day, by
   `(regime, symbol, fold)` with CI.
2. Equity curve per symbol per fold (matplotlib → png embedded).
3. Per-engine contribution to ensemble pnl (Shapley-like decomposition; if
   too expensive, use the simpler `weighted_contribution = weight *
   strength_at_alert`).
4. Fragility section: which 10% of weeks contained 50% of the loss?
5. Failure modes table: most-frequent `inputs_missing`, regime-flip
   frequency, alert clustering.
6. Baselines comparison.
7. Critique paragraph — owner-readable, explicitly listing where the
   model is fragile.

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

Separate but related CLI: `uv run python -m crypt.backfill`.

```bash
uv run python -m crypt.backfill \
    --symbol SOL-USDT-SWAP \
    --from 2023-01-01 \
    --to   2026-05-01 \
    [--data-types ohlcv,funding,oi,ls_ratio] \
    [--page-size 100] \
    [--max-rps 5]
```

Implementation notes:
- Pagination per OKX endpoint (`fetch_ohlcv` returns max 100 bars per
  call; loop with `since` parameter; respect `enableRateLimit`).
- Resume safety: re-running must not produce duplicates (rely on
  `_upsert` in `ParquetStore`).
- Progress bar in stdout (tqdm) — backfilling 3 years of H4 history is
  ~6600 bars per symbol, takes a few minutes.
- Logs every page fetched with `since` boundary so failures are
  diagnosable.

This CLI is a precondition for §4 — agents must run it before the first
backtest.

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
- XPL has < 1 year of history at the time of writing — its per-symbol
  results will have wide CIs. The report must surface this.
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
3. Implement `src/crypt/backtest/replay.py` with `ReplayParquetStore` first
   (the look-ahead guard).
4. Write `tests/backtest/test_no_lookahead.py` next — this is the single
   most important test in the milestone.
5. Implement the recorder, then the optimiser, then the report.
6. Run backfill CLI to populate ≥ 1 year of history for SOL/TON/XPL.
7. Run `--walk-forward-folds 5` and inspect the report.
8. Commit `weights.recommended.yaml` to `config/weights.yaml` once
   sanity guards pass.
9. Write a new ADR if any design point above was changed.
10. Append a CHANGELOG entry describing what the report says.
