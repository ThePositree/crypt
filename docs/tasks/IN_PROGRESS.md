# In progress

## Status as of 2026-06-02 (session 24, continued)

**Monorepo (ADR-0021):** owner is folding `backtester/` into this repository.
Documentation is updated. After `rm -rf backtester/.git`, commit from the
`crypt` root with `git add backtester/` (see ADR-0021 if a gitlink was staged
earlier). Do not commit donor changes only inside a nested repo — that layout
is retired.

---

## Status as of 2026-06-02 (session 24)

**Active work:** unified MTF `crypt_ensemble` implementation is started but
not fully smoke-accepted. The first additive contract slice is in place:
existing H4 mode remains the default, while H1 can now be selected as the
primary/execution timeframe for donor experiments.

Completed this session:

- Added `primary_timeframe` support to the donor `crypt-parquet` loader and
  CLI. Default remains `4h`; `--primary-timeframe 1h` makes
  `StrategyData.primary` use H1 while H4/D1 stay available under `candles`.
- Added `timeframes` role config to `CryptEnsembleStrategy` with
  `context`, `setup`, `trigger`, and `execution` roles.
- Preserved H4 default behavior: output index still uses H4 close time and
  the current `backtester/strategies/crypt_ensemble.json` remains the default
  smoke config.
- Added a first H1 MTF mode: D1 context filter, H4 ensemble setup verdict, H1
  candle-confirm trigger, H1 execution tick index, and MTF diagnostics
  (`context_tf`, `setup_tf`, `trigger_tf`, `context_bias`,
  `setup_direction`, `trigger_type`, `trigger_known_at`, `sl_source_tf`).
- Added `backtester/strategies/crypt_ensemble_h1.json` with H1 execution,
  `ttl = 24`, `rrr = 1.5`, and monthly risk base.
- Added tests for H1 primary loader semantics, CLI propagation, H4 default
  output shape, H1 execution index/diagnostics, H4 forming-candle exclusion,
  and D1 opposite-context blocking.
- Attempted the full SOL H1 smoke:
  `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --strategy strategies/crypt_ensemble_h1.json --output /tmp/crypt_donor_h1_mtf_smoke`.
  It loaded 21517 H1 bars and started correctly, but did not reach export
  before the session process ended; no output directory was produced.

Verification:

- `uv run ruff check backtester/src/backtester/data_loader.py backtester/src/backtester/cli_runner.py backtester/src/backtester/__main__.py backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_data_loader.py backtester/tests/test_cli_data_sources.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_data_loader.py tests/test_cli_data_sources.py tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 41 passed, 3 existing pandas warnings.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 88 passed, 3 existing pandas warnings.

### Next steps

1. Do not treat H1 MTF as performance-reviewed yet. First add either a date
   range limiter for donor `crypt-parquet` smokes or a parity-safe cache for
   repeated ensemble/SMC replay; the full SOL H1 run is too slow for normal
   session feedback.
2. Rerun the SOL H1 MTF smoke after the run-time limiter/performance pass and
   inspect `signals.csv`, `trades.csv`, `trade_diagnostics.csv`, and
   `signal_diagnostics.csv`.
3. Expand MTF no-lookahead tests before accepting smoke metrics: D1 forming
   candle exclusion, future-known H4 structural object ignored, and H1
   trigger/entry timing through donor execution.
4. Improve stop-source behavior for H1 mode. Current first slice always uses
   H4 structural stop source diagnostics; the spec still calls for H1
   structure to provide a closer protective stop when aligned with H4.
5. Keep H4 setup-geometry findings in scope: H1 `ttl`, `rrr`, and stop
   distance caps are placeholders until diagnostics from a completed H1 smoke
   are reviewed.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 23)

**Active work:** owner wants the next agent to start a unified
multi-timeframe `crypt_ensemble` implementation. The target model is top-down:
D1 context -> H4 setup -> H1 trigger/execution. The design must stay generic
so a future 15m trigger can be added by config and retuning, not by rewriting
the strategy again.

Completed this session:

- Added `docs/crypt_ensemble_mtf.md` as the implementation handoff/spec.
- Captured why the current strategy is not already D1 -> H4 -> H1:
  execution is H4, H1 has no distinct trigger layer, and several rules are
  H4-semantic (`tick_time`, SMC age, sweep freshness, ATR distance, TTL).
- Defined a reusable timeframe-role contract:
  `context`, `setup`, `trigger`, and `execution`.
- Documented first H1 slice:
  load H1 as primary/execution, keep H4/D1 as context/setup, compute SMC state
  per timeframe, require D1 not opposite + H4 setup + H1 trigger, and export
  trigger/stop-source diagnostics.
- Documented future 15m path: use the same role config, add/load 15m data,
  retune TTL/freshness/ATR/slippage, and add 15m no-lookahead tests.

### Next steps

1. Read `docs/crypt_ensemble_mtf.md` before editing code.
2. Implement the MTF contract additively:
   - preserve existing H4 default mode;
   - add `primary_timeframe`/`timeframes` config to `crypt_ensemble`;
   - make `crypt-parquet` able to use H1 as `StrategyData.primary`;
   - build closed D1/H4/H1 contexts at each H1 tick.
3. Add tests before the full smoke:
   H4 mode unchanged, H1 primary semantics, D1/H4 forming candles excluded,
   H1 trigger enters next H1 open, future-known structure ignored, and
   missing-data graceful neutral behavior.
4. Add a first `backtester/strategies/crypt_ensemble_h1.json` and run SOL H1
   smoke after tests.
5. Keep H4 setup-geometry findings from session 22 in mind: wide stops plus
   distant TP caused TTL-heavy exits. Retune H1 `ttl`, `rrr`, and stop-distance
   caps; do not inherit H4 `ttl = 6` blindly.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 22)

**Active work:** TTL-heavy exits are diagnosed. The next implementation pass
should tune setup geometry on H4 before any lower-timeframe migration:
structural stop selection/distance, `rrr`, `ttl`, and possibly side-specific
long filtering.

Completed this session:

- Added donor `trade_diagnostics.csv` export in
  `backtester/src/backtester/results_analyzer.py`.
- The report summarizes exit reasons, long/short exit counts, PnL by
  side/reason, holding duration, trades per day, `sl_distance_atr` by exit
  reason, and stop-anchor distance by anchor type.
- Generated the report for the existing structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827/trade_diagnostics.csv`
  without rerunning the slow backtest.
- Diagnosed the TTL issue: 1496/1672 trades (`89.47%`) closed by
  `ttl_expired`; the current `ttl = 6` on H4 is a 24-hour holding window.
- TTL-expired trades had median `sl_distance_atr = 3.985`; with `rrr = 2`,
  their TP is roughly 8 ATR away, which is usually too far for a one-day H4
  setup. This is setup geometry, not an execution bug.
- Current structural SOL smoke already produced about `1.88` trades/day on
  one symbol when the donor default does not apply the live `75` confidence
  threshold. The "too few trades" concern likely refers to live-alert gating
  or filtered/manual expectations, not the ungated donor smoke.
- Checked local data availability: SOL and TON have long H1 history in
  `data/`; XPL has only a short H1 window. Data is not the main blocker for an
  H1 experiment.

Verification:

- `uv run ruff check backtester/src/backtester/results_analyzer.py backtester/tests/test_results_analyzer.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_results_analyzer.py -q`
  in `backtester/` -> 6 passed.

### Next steps

1. Before Optuna, run a focused H4 setup-geometry pass: compare `ttl` values
   (`6`, `12`, `18`, `24` H4 bars), lower `rrr` values, and stop-distance
   caps/buckets. The immediate question is whether TTL exits become TP/SL
   resolved without destroying expectancy.
2. Improve order-block stop selection before trusting optimizer output:
   prefer closer/fresher OBs or reject OB stops above a tighter
   `sl_distance_atr` cap. Current OB anchors dominate and are often too wide.
3. Treat H1 as a separate strategy contract, not a one-line timeframe swap.
   A credible H1 migration needs a new spec/ADR, primary timeframe parameter
   in the donor loader/strategy, H1 retuning of H4-hardcoded engines, and
   no-lookahead tests. It is medium complexity, not hard, but doing it
   naively would duplicate H4 signals or add noise.
4. Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 20)

**Active work:** pause optimizer/backtest runs and replace the mechanical
ATR-only stop-loss in donor `crypt_ensemble` with a structural SMC stop first.
The owner explicitly corrected the process: `backtester/` is a high-risk
donor/source-of-truth package, so agents must adapt to it instead of adding
new broad donor semantics.

Correction applied this session:

- Removed the newly added donor walk-forward optimizer code and CLI command.
- Removed the new optimizer test file.
- Restored donor `crypt_ensemble.suggest_params()` to the existing surface
  (`sl_atr_mult`, `min_confidence`) and removed weight injection from code for
  now.
- Removed the README optimizer command.
- Added explicit donor safety rules to `docs/backtester_migration.md`.
- Added `docs/crypt_ensemble_structural_sl.md` as the next implementation
  spec. It requires structural stops using existing SMC outputs before
  optimizer/backtest interpretation.

Verification:

- `uv run ruff check backtester/src/backtester/optimizer.py backtester/src/backtester/__main__.py backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- Targeted donor pytest should be rerun after the structural-SL implementation;
  no optimizer/backtest run should start before that.

### Next steps

1. Implement `docs/crypt_ensemble_structural_sl.md` before any optimizer or
   backtest run. Keep donor `ExecutionSim` unchanged.
2. Preferred SL hierarchy: active SMC order-block boundary -> fresh liquidity
   sweep level -> confirmed pivot fallback -> conservative ATR fallback or no
   trade, with ATR buffer and wrong-side stop rejection.
3. Reuse `crypt.structure.smc` outputs and `pinescript/smc.pine` as reference;
   do not add a parallel SMC parser inside donor code.
4. Add synthetic tests for long/short OB stops, sweep stops, pivot fallback,
   wrong-side stop rejection, ATR buffer, and `known_at <= tick_time`.
5. Only after structural SL smoke works, revisit optimizer. Do not add
   `folds`; if optimizer wiring is needed, adapt the existing donor optimizer
   surface and keep `trials` as an optional/defaulted run knob.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 19)

**Active work:** start donor Optuna for `crypt_ensemble`. Do not spend more
time explaining the number `75`: ADR-0020 records it as an arbitrary live-alert
placeholder, not a calibrated threshold and not the default donor entry gate.

Completed this session:

- Added ADR-0020: `ALERT_CONFIDENCE_THRESHOLD = 75` is a placeholder.
- Superseded only the `75` rationale part of ADR-0011; the `[UNCALIBRATED]`
  marker policy remains accepted.
- Removed `min_confidence = 75` from `backtester/strategies/crypt_ensemble.json`.
  Donor `crypt_ensemble` now trades BUY/SELL verdicts by default.
- Kept `min_confidence` as an explicit optional diagnostic/Optuna parameter.
- Changed `signal_diagnostics.csv` confidence reporting to distribution
  quantiles (`p50`, `p75`, `p90`, `p95`, `p99`) instead of a hard-coded
  `confidence_ge_75` metric.
- Reviewed owner-provided smoke result after removing the default gate:
  `/tmp/crypt_donor_smoke/20260602_132627`.
- Smoke result: 1792 trades, final capital 6694.69 from 10000,
  `total_return_pct = -33.05`, `profit_factor = 0.88`, max drawdown `-36.96`.
  Long side remains materially negative (`total_pnl = -4483.27`,
  `profit_factor = 0.68`); shorts are slightly positive
  (`total_pnl = 1177.96`, `profit_factor = 1.08`).
- Export check: `trades.csv` includes `signal_time`, `risk_base_capital`,
  confidence, score, regime, decision, rationale, and per-engine strengths.

Verification:

- `uv run ruff check src/crypt/aggregator/ensemble.py src/crypt/decision/filters.py backtester/src/backtester/strategies/crypt_ensemble.py backtester/src/backtester/results_analyzer.py backtester/tests/test_crypt_ensemble_strategy.py backtester/tests/test_results_analyzer.py`
  -> clean.
- `PYTHONPATH=src:../src uv run --extra dev pytest tests/test_crypt_ensemble_strategy.py tests/test_results_analyzer.py -q`
  in `backtester/` -> 12 passed, 1 existing pandas warning.
- `PYTHONPATH=src:../src uv run --extra dev pytest tests -q` in
  `backtester/` -> 75 passed, 3 existing pandas warnings.

### Next steps

1. Implement donor Optuna support for `crypt_ensemble` with a meaningful
   search space: regime thresholds, regime weights for active engines,
   optional `min_confidence`, `sl_atr_mult`, and later `ttl` / `rrr` /
   `risk_percent` / `risk_base_period`.
2. Avoid optimizing on the same full SOL sample only. Add or reuse
   walk-forward/out-of-sample slicing before accepting any parameter set.
3. Keep monthly risk-base as the default for smokes, but include weekly and
   backtest-base sizing as search/report dimensions once the Optuna path is
   wired.
4. After the first optimizer run, compare long-only and short-only metrics
   explicitly; current smoke suggests long-side filtering or weighting is the
   main issue.
5. Performance work is still important, but it should follow the first
   optimizer wiring unless the naive Optuna runtime becomes unworkable.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 16)

**Active work:** donor `crypt_ensemble` is engine-wired and trade-producing.
The first completed SOL smoke was reviewed, but it used the old per-trade
current-capital risk sizing. ADR-0019 now makes monthly window-base sizing the
`crypt_ensemble` default, so the smoke should be rerun before interpreting the
new metrics.

Completed this session:

- Reviewed owner-completed SOL donor smoke:
  `/tmp/crypt_donor_smoke/20260602_101119`.
- Confirmed it was a plain donor `backtester run`, not an optimizer run.
- Recorded the old-mode result: 1792 trades, final capital 6548.74 from 10000,
  `total_return_pct = -34.51`, `profit_factor = 0.88`, long PnL -4428.94,
  short PnL +977.68.
- Fixed donor trade export so `trades.csv` preserves strategy attribution
  metadata (`signal_time`, confidence, score, regime, decision, rationale,
  `strength_<engine>`).
- Added `risk_base_period` to donor execution sizing: `trade`, `weekly`,
  `monthly`, `backtest`.
- Set `crypt_ensemble` to `risk_base_period = monthly`; each trade now exports
  `risk_base_capital`.
- Added ADR-0019 documenting the monthly risk-base decision.

Verification:

- `uv run ruff check backtester/src/backtester/execution_sim.py backtester/src/backtester/risk_model.py backtester/src/backtester/tester.py backtester/src/backtester/cli_runner.py backtester/src/backtester/__main__.py backtester/tests/test_execution_sim_run.py backtester/tests/test_risk_fee_models.py`
  → clean.
- `PYTHONPATH=src:../src uv run --extra dev pytest tests/test_execution_sim_run.py tests/test_risk_fee_models.py -q`
  in `backtester/` → 39 passed.
- `PYTHONPATH=src:../src uv run --extra dev pytest tests -q` in
  `backtester/` → 71 passed.

### Next steps

1. Rerun SOL donor smoke with the current `crypt_ensemble.json`:
   `PYTHONPATH=src:../src uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --symbol SOL-USDT-SWAP --strategy strategies/crypt_ensemble.json --output /tmp/crypt_donor_smoke`.
2. Inspect the new `trades.csv`: it should include `signal_time`,
   `risk_base_capital`, `confidence`, `score`, `regime`, `decision`,
   `rationale`, and `strength_<engine>` columns.
3. Compare the new monthly-risk-base metrics against the old per-trade result
   above. Treat this as smoke analysis, not calibration.
4. Only after the monthly smoke is reviewed, start performance profiling or
   Optuna work.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 15)

**Active work:** `crypt_ensemble` is now engine-wired in the donor backtester,
but the first full SOL smoke has not been completed. The straightforward replay
path is slow on 5545 H4 bars; progress output is now visible, and performance
work must wait for parity/no-lookahead tests before any algorithmic shortcut.

Completed this session:

- Wired `backtester/src/backtester/strategies/crypt_ensemble.py` to run the
  existing `crypt` engines and aggregator over `StrategyData` H4/H1/D1 frames.
- Preserved closed-candle semantics: each donor H4 row uses tick time equal to
  H4 `open_time + 4h`, and context candles are filtered to candles closed at or
  before that tick time.
- Added donor output columns: `signal`, `entry_price`, ATR-based `sl_price`,
  `confidence`, `score`, `regime`, `decision`, `rationale`, and
  `strength_<engine>` metadata.
- Added `progress` support for `crypt_ensemble`; it is enabled in
  `backtester/strategies/crypt_ensemble.json`.
- Fixed a real `open_time` ambiguity from project Parquet data where
  `open_time` was both index name and column label.
- Added tests proving BUY/SELL/HOLD mapping, ATR stop output, missing optional
  H1/D1/extras graceful handling, and `open_time`-named index handling.

Verification:

- `uv run ruff check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  → clean.
- `PYTHONPATH=src:../src uv run --extra dev pytest tests -q` in `backtester/`
  → 67 passed.
- SOL `crypt-parquet` smoke loaded 5545 H4 bars and started engine replay with
  visible progress. It was intentionally stopped before completion because the
  full run was taking on the order of tens of minutes.

### Next steps

1. Run the SOL `crypt-parquet` smoke to completion, now that progress is
   visible:
   `PYTHONPATH=src:../src uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --symbol SOL-USDT-SWAP --strategy strategies/crypt_ensemble.json --output /tmp/crypt_donor_smoke`.
2. Inspect `trades.csv` and exported artifacts. If trades exist, verify they
   carry enough metadata to trace back to ensemble verdicts; if no trades
   exist, confirm the generated signaled frame truly emitted no BUY/SELL rows.
3. Only after a completed straightforward smoke, consider performance work.
   Any caching/incremental replay must be protected by parity tests proving
   identical outputs and unchanged no-lookahead behaviour.
4. Only after the engine-wired smoke works, start Optuna support for ensemble
   weights.

Do not delete or deprecate `src/crypt/backtest/` yet.

---

## Status as of 2026-06-02 (session 13)

**Active work:** owner redirected M2 backtesting architecture toward the donor
`backtester/` package. ADR-0018 is accepted; `docs/backtester_migration.md`
is the handoff spec. The next agent should implement the migration, not keep
extending `src/crypt/backtest/` by default.

Owner direction captured:

- Keep existing Parquet data; do not convert the project to CSV.
- Keep `backtester/` as a separate Python package for now (superseded for git
  layout by ADR-0021 — same repo, own `pyproject.toml`).
- Extend donor backtester additively and minimally.
- Add `parquet` and `crypt-parquet` data-source modes.
- Register the ensemble as one donor strategy named `crypt_ensemble`.
- One symbol per run is acceptable; multi-symbol means multiple runs.
- Do not start by deleting `src/crypt/backtest/`.

### Next steps

Read first:

- `docs/decisions/0018-donor-backtester-canonical-m2.md`
- `docs/backtester_migration.md`
- `backtester/src/backtester/__main__.py`
- `backtester/src/backtester/data_loader.py`
- `backtester/src/backtester/registry.py`
- `src/crypt/data/store.py`

Recommended implementation sequence:

1. Add `StrategyData` to the donor package and adapt CLI/backtester plumbing
   so existing donor strategies still receive a plain `pd.DataFrame`.
2. Add `ParquetDataLoader` and tests for both donor-style OHLCV columns and
   project-style Parquet columns (`open_time`, `o`, `h`, `l`, `c`, `v`).
3. Add `CryptParquetDataLoader` using the existing project `ParquetStore`
   layout; H4 required, H1/D1/extras optional and represented as empty frames
   when missing.
4. Register a first `crypt_ensemble` donor strategy that emits neutral rows
   before wiring all engines.
5. Wire the existing ensemble into `crypt_ensemble` and run a one-symbol SOL
   smoke backtest.
6. Only after the smoke run works, add Optuna support for ensemble weights.

Do not update `README.md` until a working donor-backed command exists.

---

## Status as of 2026-06-01 (session 12)

**Active work:** M2 OHLCV-only backtest report reviewed. The simulator bug from
session 11 is no longer the blocker; the optimizer sanity guard is a genuine
model/calibration failure on the first two out-of-sample folds.

Completed:

- Reviewed `reports/backtest_2026-06/` after the owner reran the full
  SOL/TON backtest.
- Wrote ADR-0014 rejecting promotion of the generated weights.
- Fixed `weights_to_yaml()` so future `weights.candidate.yaml` files are safe
  YAML without Python/numpy object tags.
- Rewrote the current `reports/backtest_2026-06/weights.candidate.yaml` with
  the safe serializer; weights are unchanged.
- Added regression coverage for numpy scalar YAML serialization.

### Next steps

Do not copy `reports/backtest_2026-06/weights.recommended.yaml` to
`config/weights.yaml`, and do not flip `uncalibrated = False`.

Recommended next implementation items:

1. Fix report artifact semantics: if any fold fires the sanity guard, do not
   present `weights.recommended.yaml` as promotable, and make
   `weights.candidate.yaml` contain an explicit aggregate candidate rather than
   the last fold's weights.
2. Investigate weak long signals before another calibration attempt. The
   reviewed report showed negative `h24` proxy expectancy on `SOL` BUY and
   `TON` BUY alerts.
3. Decide the next M2 modeling slice: either add cheap BTC/cross-symbol context
   or introduce a stricter long-side filter, then rerun the same walk-forward
   backtest.

---

## Status as of 2026-06-01 (session 11)

**Active work:** M2 backtest run exposed a multi-symbol execution simulator
bug. The simulator used the next global DataFrame row for next-open entries
and TTL exits, so same-timestamp SOL/TON rows could mix prices across
symbols. This produced impossible stop-loss validation messages such as
SOL entries paired with TON stop prices.

Fixed:

- `ExecutionSim.run()` now derives `next_open`, `next_time`, and bar number
  per symbol before simulating entries and TTL exits.
- Backtest sim frames now include `entry_price = close` so execution uses the
  closed signal candle explicitly.
- pandas `pct_change` and UTC datetime deprecation warnings are cleaned up.
- Regression coverage added in `tests/backtest/test_execution_sim.py`.

Verification:

- `uv run pytest -q` → 124 passed.
- `uv run ruff check src tests` → clean.
- `uv run mypy src` → clean.

### Next steps

Re-run the owner command and review the new report:

```bash
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

If the optimizer guard still fires after this execution fix, treat that as a
model/calibration result rather than a simulator integrity bug and document it
in ADR-0014.

---

## Status as of 2026-06-01 (session 10)

**Active work:** SMC structure, order-block, and liquidity slices are
implemented and verified. Optimizer score recomputation is fixed. Next: run
OHLCV backfill/backtest.

Owner direction: do not pay for historical derivatives/order-flow data until
the product demonstrates value. Use free OKX candle history first. ADR-0017
captures this decision.

---

## Next steps for the implementing agent

### 1. SMC engines now implemented (P0)

Specs written:

- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/engines/smc_order_blocks.md`
- `docs/engines/smc_liquidity.md`

Completed:

- `src/crypt/structure/smc.py` — first deterministic analyser slice:
  confirmed pivots + BOS/CHoCH with `known_at` timing; now also creates and
  mitigates order-block zones from structure breaks; now also emits equal
  high/low levels and liquidity sweeps.
- `src/crypt/engines/smc_structure.py` — first directional SMC engine.
- `src/crypt/engines/smc_order_blocks.py` — active order-block retest engine.
- `src/crypt/engines/smc_liquidity.py` — equal/swing high-low sweep engine.
- Tests proving no-lookahead timing for pivot confirmation, structure signals,
  order-block creation/mitigation/retest, equal-level detection, sweep timing,
  ambiguous double sweeps, and liquidity-engine output.

### 2. Wire OHLCV-only M2 calibration (P0)

- `smc_structure` and `smc_order_blocks` are already wired into live/replay
  aggregation.
- `smc_liquidity` is now wired into live/replay aggregation.
- `config/weights.yaml` already sets `derivatives: 0.0` for primary M2.
- `BacktestRecorder` now persists `strength_<engine>` columns, and
  `optimizer._apply_weights` recomputes candidate scores from those strengths
  before deriving decisions/objectives.

### 3. Run candle backfill + backtest

Only OHLCV is required for the first M2 report:

```bash
for SYMBOL in SOL-USDT-SWAP TON-USDT-SWAP XPL-USDT-SWAP; do
    PYTHONPATH=src uv run python -m crypt.backfill \
        --symbol "$SYMBOL" \
        --from 2024-02-01 --to 2026-06-01 \
        --data-types ohlcv
done
```

Then:

```bash
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

### 4. After backtest report is reviewed

- Write **ADR-0014** — calibration result: final weights, expectancy CI,
  dataset window, and critique of weak/collapsed engines.
- Flip `Settings.uncalibrated = False` only if the report justifies it.
- Copy accepted `weights.recommended.yaml` → `config/weights.yaml`.

---

## Known limitations / caveats

- `pinescript/smc.pine` is a LuxAlgo CC BY-NC-SA reference. Do not copy code
  verbatim into proprietary Python modules. Implement the documented behaviour.
- PineScript MTF sections using `lookahead_on` must not be ported directly.
- `order_block`, `liquidity`, FVG, and Fibonacci can overfit easily; add one
  engine at a time and require synthetic no-lookahead tests.
- Context7 MCP was requested by project rules. In sessions 9 and 10 pandas
  docs were resolved via Context7 before touching DataFrame-based SMC/backtest
  code; no new libraries were added.

---

## Reading list

- `AGENTS.md`
- `docs/decisions/0017-ohlcv-only-m2-smc.md`
- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/backtest.md`
- `pinescript/smc.pine`
