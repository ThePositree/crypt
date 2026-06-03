# In progress

## Status as of 2026-06-03 (session 35)

**Active work:** candidate A is now defined for an owner-run long diagnostic,
but it is not accepted calibration.

Completed this session:

- Added `backtester compare-fixed`, a cheap fixed-candidate comparison CLI for
  bounded H1 windows.
- The command defaults to SOL January/February/March 2025 and TON
  January/February 2025, runs one fixed execution profile per window, and
  writes `windows.csv`, `windows.md`, plus normal donor artifacts under
  `runs/<label>/`.
- Added focused tests for window parsing and report aggregation.
- Ran the fixed H1 candidate comparison at
  `/tmp/crypt_fixed_candidate_h1/20260603_134312`.

Fixed candidate A:

- Strategy config: `backtester/strategies/crypt_ensemble_h1.json`.
- Strategy params: current H1 diagnostic profile, including
  `max_sl_distance_atr = 4.0`, `optimized_windows = true`, H4 setup snapshots,
  and structural stops.
- Execution params: `rrr = 1.25`, `position_ttl_bars = 36`,
  `risk_percent = 1.0`, `risk_base_period = monthly`.

Bounded fixed-candidate result:

| Slice | Return | Profit factor | Max DD | Trades | Side profile |
|-------|--------|---------------|--------|--------|--------------|
| SOL Jan 2025 | `+1.99%` | `1.12` | `-5.68%` | 93 | long `+248.10`, short `-49.49` |
| SOL Feb 2025 | `+13.82%` | `5.40` | `-1.90%` | 53 | short-only `+1381.77` |
| SOL Mar 2025 | `-6.52%` | `0.66` | `-10.63%` | 63 | short-only `-651.92` |
| TON Jan 2025 | `+1.19%` | `1.07` | `-4.61%` | 87 | short-only `+118.50` |
| TON Feb 2025 | `+2.76%` | `1.18` | `-10.95%` | 95 | short-only `+275.53` |

Interpretation:

- Candidate A is positive on 4/5 bounded windows and is worth a longer local
  diagnostic run while the owner waits for limits to reset.
- It is not accepted calibration. SOL March 2025 is a material failure and
  TON February drawdown is large relative to its return.
- The side profile is heavily short-only after structural-stop/trigger
  filtering. Do not add an `allowed_sides` filter yet; there is no evidence
  that longs are consistently harmful across actual tradeable signals because
  four of five bounded windows had no long trades.
- Do not restart broad full-history `--strategy-param-search` during Codex
  time. Use candidate A full-history evaluation or a tiny execution-only grid
  around SOL March instead.

Owner-run command for the 5-day wait:

```bash
cd backtester
PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/matplotlib \
uv run --extra dev backtester compare-fixed \
    --data-dir ../data \
    --primary-timeframe 1h \
    --strategy strategies/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_candidate_a_full \
    --rrr 1.25 \
    --ttl 36 \
    --risk-percent 1.0 \
    --window sol_full:SOL-USDT-SWAP:2024-06-01:2026-06-01 \
    --window ton_full:TON-USDT-SWAP:2024-06-01:2026-06-01
```

Expected outputs:

- `results/crypt_ensemble_h1_candidate_a_full/<timestamp>/windows.csv`
- `results/crypt_ensemble_h1_candidate_a_full/<timestamp>/windows.md`
- per-window `runs/<label>/metrics.csv`, `trades.csv`,
  `trade_diagnostics.csv`, `signals.csv`, and `signal_diagnostics.csv`.

Next steps:

1. If the owner-run full-history candidate A check is positive or near
   break-even with tolerable drawdown, run a bounded walk-forward expansion
   across more SOL/TON months before touching strategy params.
2. If SOL March remains the obvious blocker, run a tiny execution-only grid
   around `rrr = 1.0, 1.25, 1.5` and `ttl = 30, 36, 42`; keep
   `--no-strategy-param-search`, no daily-limit search, and no trading-window
   search.
3. Only after execution geometry is stable should a future agent consider a
   side filter or strategy-param search, and any side-filter change must update
   `docs/crypt_ensemble_mtf.md` first with focused tests.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/__main__.py backtester/src/backtester/fixed_candidate_report.py backtester/tests/test_fixed_candidate_report.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/__main__.py backtester/src/backtester/fixed_candidate_report.py backtester/tests/test_fixed_candidate_report.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_fixed_candidate_report.py -q`
  in `backtester/` -> 2 passed.
- Fixed-candidate comparison command above with default bounded windows
  completed and exported artifacts.

---

## Status as of 2026-06-03 (session 34)

**Active work:** urgent M2 profitability sprint handoff. The owner has only
about 2-3 Codex sessions left before limits reset, so the next agents should
prefer high-impact, end-to-end tasks that can produce a candidate worth a long
unattended local backtest over broad architecture work.

Owner direction:

- Work in Russian chat, but keep code and docs in English.
- Maximize useful progress per session. Do not spend the remaining sessions on
  low-leverage refactors, dashboards, CI niceties, or broad exploratory
  changes unless they directly unblock the profitability run.
- The target outcome before limits run out is not a fully accepted strategy.
  The target is a defensible, documented candidate that is profitable on
  bounded/out-of-sample checks and can be launched by the owner as a long
  full-history or multi-day Optuna/backtest run while waiting for limits to
  refresh.

Process note from this session:

- The owner started a curiosity run:
  `backtester optimize --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --strategy strategies/crypt_ensemble_h1.json --output results/sol_h1_full_all_optuna --trials 100 --study-name sol_h1_full_all --target total_return_pct --rrr-low 1.0 --rrr-high 3.0 --rrr-step 0.25 --ttl-low 12 --ttl-high 48 --ttl-step 6 --risk-percent-low 0.5 --risk-percent-high 2.0 --risk-percent-step 0.25 --strategy-param-search --daily-limit-search --trading-window-search --export-best-run`.
- It was still alive after about 2h23m, using 100% CPU. Output directory:
  `backtester/results/sol_h1_full_all_optuna/20260603_110457`.
- Trial 0 ran from `2026-06-03 14:04:57` to `15:53:00` MSK and completed with
  `total_return_pct = -9.47`, `max_drawdown = -24.75`, `total_trades = 482`,
  `sharpe_ratio = -0.5945`. Trial 1 had started but had not completed when
  inspected.
- The owner said they would stop this run. Treat any partial artifacts as a
  curiosity diagnostic, not as accepted calibration. It confirms that
  full-history H1 `--strategy-param-search` is too expensive for the remaining
  Codex budget because each strategy-param trial rebuilds signals.

### Next-session priority order

1. **Build a cheap fixed-candidate comparison harness/report before more
   broad Optuna.** Compare fixed `rrr = 1.25`, `position_ttl_bars = 36`,
   `risk_percent = 1.0`, `max_sl_distance_atr = 4.0`, no daily-limit search,
   no trading-window search, no strategy-param search across already completed
   windows and at least SOL March 2025 + TON February 2025. If this can be done
   by a small script or CLI subcommand, implement it with tests; otherwise run
   explicit commands and summarize artifacts.
2. **Find the fastest profitable candidate, not the most general optimizer.**
   If fixed `rrr = 1.25` / `ttl = 36` is positive across most windows, freeze
   it as the first long-run candidate. If it fails, try a very small
   execution-only grid around `rrr = 1.0, 1.25, 1.5` and `ttl = 30, 36, 42`.
   Keep strategy-param search disabled until there is a stable execution
   baseline.
3. **Attack side skew only if it directly improves the candidate.** SOL
   February and TON January best runs were short-only, while SOL January was
   mixed. The shortest useful investigation is to summarize H4 setup verdict
   side counts, tradeable signal side counts, structural stop availability,
   and PnL by side for each bounded window. If long trades are consistently
   harmful, test an explicit diagnostic `allowed_sides = short` or equivalent
   strategy param only after writing/updating the MTF spec and adding focused
   tests.
4. **Prepare an owner-run command for the 5-day wait.** Before handing back,
   provide a single command the owner can launch locally for a long run,
   plus expected output files and how to monitor progress. Prefer either
   execution-only full-history with frozen strategy params, or bounded
   walk-forward windows, over broad full-history strategy-param Optuna.
5. **Document every result immediately.** Update `IN_PROGRESS.md`,
   `BACKLOG.md`, `DONE.md`, and `CHANGELOG.md` at the end of each session so
   the next agent can continue without rediscovery.

Guardrails for the next agent:

- Do not silently rewrite `docs/tasks/ROADMAP.md`.
- Do not accept any candidate based only on one in-sample Optuna best.
- Do not run full-history broad `--strategy-param-search` during a Codex
  session unless the owner explicitly asks; it can consume hours per trial.
- If adding side filters or new strategy parameters, update
  `docs/crypt_ensemble_mtf.md` first and add tests before interpreting PnL.

---

## Status as of 2026-06-03 (session 33)

**Active work:** continue M2 donor H1 setup-geometry validation after the
first adjacent-window and non-SOL optimizer diagnostics.

Completed this session:

- Inspected the existing SOL January optimizer best-run artifacts at
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`.
- Confirmed the January result is mixed-side and fragile: 39 long trades
  produced `+304.88`, while 58 short trades produced `-58.48`; all tradeable
  signals used `trigger_type = 1h_candle_confirm` and `sl_source_tf = 1h`.
- Ran the same 12-trial execution-only bounded optimizer slice on adjacent
  SOL February 2025 at
  `/tmp/crypt_donor_h1_mtf_optuna_sol_feb/20260603_104255`.
- Ran the same 12-trial execution-only bounded optimizer slice on TON January
  2025 at `/tmp/crypt_donor_h1_mtf_optuna_ton_jan/20260603_104642`.
- Skipped XPL for this pass; its H1 history is shorter and already flagged as
  less suitable for long H1 diagnostics.

Current bounded optimizer diagnostics:

| Slice | Best params | Return | Profit factor | Max DD | Trades | Side profile |
|-------|-------------|--------|---------------|--------|--------|--------------|
| SOL Jan 2025 | `rrr = 1.25`, `ttl = 30` | `+2.46%` | `1.14` | `-5.70%` | 97 | long `+304.88`, short `-58.48` |
| SOL Feb 2025 | `rrr = 1.25`, `ttl = 36` | `+13.82%` | `5.40` | `-1.90%` | 53 | short-only `+1381.77` |
| TON Jan 2025 | `rrr = 1.50`, `ttl = 36` | `+1.95%` | `1.12` | `-5.51%` | 86 | short-only `+194.85` |

Interpretation:

- `ttl = 36` appears in the adjacent SOL and TON best trials, but this is not
  enough to accept it as calibrated.
- The profile is not stable: SOL January needed mixed long/short trades, while
  SOL February and TON January were short-only.
- The TON result is only marginally positive with drawdown similar to SOL
  January, so setup geometry should still be treated as diagnostic.
- Do not enable broader strategy-param search yet. More out-of-sample windows
  are needed before spending cache misses on `max_sl_distance_atr`, SL buffer,
  or confidence/filter search.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/__main__.py backtester/src/backtester/cli_runner.py backtester/src/backtester/optimizer.py backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_optimizer.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/__main__.py backtester/src/backtester/cli_runner.py backtester/src/backtester/optimizer.py backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_optimizer.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_optimizer.py tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 29 passed.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 102 passed, 2 existing pandas warnings.
- SOL February and TON January bounded optimizer CLI diagnostics completed and
  exported `trials.csv`, `best_trial.json`, and `best_run/` diagnostics.

### Next steps

1. Run at least two more out-of-sample H1 optimizer diagnostics before
   accepting any setup geometry: SOL March 2025 and TON February 2025 are the
   next most direct adjacent windows.
2. Compare all completed windows with a fixed candidate (`rrr = 1.25`,
   `ttl = 36`) in addition to per-window Optuna bests, so the next decision is
   not based only on each slice's in-sample best trial.
3. Investigate the short-only skew in SOL February and TON January before
   adding long/short filters. The current trigger is still the single
   `1h_candle_confirm` rule, so side skew may be coming from H4 setup verdicts
   or structural-stop availability rather than trigger logic.
4. Keep first-signal-build performance in scope: SOL February took about
   3 minutes 30 seconds for 673 H1 bars; TON January took about 3 minutes
   58 seconds for 745 H1 bars. Cached execution trials remain fast.

---

## Status as of 2026-06-03 (session 32)

**Active work:** continue M2 donor H1 setup-geometry tuning after the first
operator-facing bounded optimizer slice.

Completed this session:

- Added `backtester optimize`, an operator-facing CLI around the existing donor
  `ParameterOptimizer`.
- The command reuses donor strategy JSON params, supports bounded
  `crypt-parquet` input with `--from` / `--to`, exposes execution-only search
  knobs for `rrr`, `position_ttl_bars`, fixed or ranged `risk_percent`, daily
  limits, trading windows, and strategy-param search, and writes `trials.csv`,
  `best_trial.json`, the Optuna journal log, and donor `best_run/` diagnostics.
- Fixed fixed-risk handling in `ParameterOptimizer`: when
  `risk_percent_range = None`, it now uses the configured fixed
  `risk_percent` instead of always falling back to `1.0`.
- Added a public cached-signal accessor and made `best_run/` export reuse the
  cached best signal frame when possible. The best-run export no longer pays
  for a second `crypt_ensemble.generate()` in execution-only searches.
- Updated README and `docs/crypt_ensemble_mtf.md` with the optimizer command,
  artifact contract, cache behaviour, and bounded diagnostic result.
- Ran a real bounded SOL H1 optimizer slice at
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`.

Current bounded optimizer diagnostic:

- Slice: SOL H1 `2025-01-01` to `2025-02-01`, 745 signal rows.
- Search: 12 execution-only trials over `rrr = 1.0..2.0 step 0.25` and
  `position_ttl_bars = 18..42 step 6`; strategy-param, daily-limit, and
  trading-window search disabled.
- First signal build: about 3 minutes 59 seconds.
- Cached trials after the first build: about 0.05 seconds each.
- `signal_cache_size = 1`.
- Best tiny in-sample diagnostic: `rrr = 1.25`, `position_ttl_bars = 30`,
  `total_return_pct = 2.46`, `profit_factor = 1.14`, max drawdown `-5.7`,
  97 trades.
- Signal distribution: 39 long, 66 short, 640 neutral.
- Exit distribution: 38 stop-loss, 35 take-profit, 24 TTL-expired.
- Side PnL: long `+304.88`, short `-58.48`.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/__main__.py backtester/src/backtester/cli_runner.py backtester/src/backtester/optimizer.py backtester/tests/test_optimizer.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/__main__.py backtester/src/backtester/cli_runner.py backtester/src/backtester/optimizer.py backtester/tests/test_optimizer.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_optimizer.py -q`
  in `backtester/` -> 3 passed.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 102 passed, 2 existing pandas warnings.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/matplotlib uv run --extra dev backtester optimize ...`
  bounded SOL H1 12-trial slice -> completed and exported diagnostics.
- Short cache smoke at
  `/tmp/crypt_donor_h1_mtf_optuna_cli_cache_smoke/20260603_103348` confirmed
  `best_run/` export reuses cached signals and does not show a second
  `crypt_ensemble` progress build.

### Next steps

1. Do not treat the `2.46%` January SOL result as accepted calibration. It is
   an in-sample bounded setup-geometry diagnostic only.
2. Inspect `best_run/trades.csv`, `trade_diagnostics.csv`, and
   `signal_diagnostics.csv` from
   `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`, especially why shorts
   remain negative while longs flipped positive in this bounded slice.
3. Run the same bounded optimizer command on adjacent SOL windows and at least
   one non-SOL symbol before widening strategy-param search.
4. After execution-only diagnostics across windows, decide whether to enable
   strategy-param search (`max_sl_distance_atr`, SL buffer, optional
   `min_confidence`). These will create new signal-cache keys and be slower.
5. Keep first-signal-build performance in scope: one 745-bar H1 signal build
   is still about 4 minutes even though repeated execution trials are fast.

---

## Status as of 2026-06-03 (session 30)

**Active work:** proceed to focused H1 setup-geometry grids after the first
parity-safe performance pass.

Completed this session:

- Added the `crypt_ensemble` reference-vs-optimized performance contract to
  the MTF spec before code changes.
- Added `optimized_windows` as an explicit strategy parameter. Default is
  `false`; `backtester/strategies/crypt_ensemble_h1.json` opts in with
  `true`.
- Implemented a closed-window context cache for candles/extras only. It does
  not cache verdicts, SMC states, trigger decisions, or stops across bars.
- Added parity tests for cached context windows and H1 MTF strategy output.
- Reran bounded SOL H1 optimized-window smoke:
  `/tmp/crypt_donor_h1_mtf_smoke_optimized_windows/20260603_083245`.

Current bounded optimized-window diagnostic:

- Runtime: about 5 minutes 3 seconds for 745 H1 bars, improved from the
  previous max-4 reference smoke at about 6 minutes 35 seconds.
- 98 trades, final capital 9947.0, `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`.
- Exit distribution: 37 `ttl_expired`, 35 `stop_loss`, 26 `take_profit`.
- Long PnL -45.67, short PnL -7.33. Both sides remain slightly negative in
  this bounded window.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 25 passed, 1 existing pandas warning.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 98 passed, 3 existing pandas warnings.
- Bounded optimized smoke command:
  `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --from 2025-01-01 --to 2025-02-01 --strategy strategies/crypt_ensemble_h1.json --output /tmp/crypt_donor_h1_mtf_smoke_optimized_windows`
  -> completed.

### Next steps

1. Start the focused H1 setup grid on the same bounded SOL slice, using the
   optimized H1 config: compare `ttl` 24, 36, 48; `rrr` 1.0, 1.25, 1.5; keep
   `max_sl_distance_atr = 4.0` for the first 9-run slice.
2. Inspect side/trigger diagnostics after each slice. The optimized-window run
   kept the same near-break-even total result, but long and short PnL remain
   slightly negative.
3. Do not add verdict, SMC, or cross-bar decision caching before writing a
   separate parity contract and tests for event-age/freshness behaviour.
4. Do not run full-history H1 acceptance until setup geometry is clearer.

---

## Status as of 2026-06-02 (session 29)

**Active work:** continue M2 donor H1 MTF setup-geometry tuning after the
first explicit stop-distance cap diagnostic.

Completed this session:

- Added `max_sl_distance_atr` to donor `crypt_ensemble` as an explicit
  strategy parameter. Default remains `8.0`, preserving existing H4 behavior
  when the parameter is omitted.
- Added `max_sl_distance_atr` to `suggest_params()` so future donor Optuna can
  tune it explicitly instead of relying on a hidden constant.
- Set `max_sl_distance_atr = 4.0` in the H1 diagnostic strategy config.
- Added a focused unit test proving an explicit tighter cap neutralizes a
  structurally valid but too-wide stop.
- Updated README, BACKLOG, DONE, MTF docs, and CHANGELOG with the diagnostic
  contract and smoke result.
- Reran bounded SOL H1 MTF smoke:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_max4/20260602_195943`.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean after formatting the strategy file.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 23 passed, 1 existing pandas warning.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 96 passed, 3 existing pandas warnings.
- Bounded SOL H1 MTF smoke command:
  `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --from 2025-01-01 --to 2025-02-01 --strategy strategies/crypt_ensemble_h1.json --output /tmp/crypt_donor_h1_mtf_smoke_h1_max4`
  -> completed in about 6 minutes 35 seconds.

Current bounded smoke diagnostic:

- 745 H1 signal rows.
- Signal distribution: 39 long, 66 short, 640 neutral.
- 105 tradeable signals; all 98 executed trades used `sl_source_tf = 1h`.
- 98 trades: 39 long, 59 short.
- Final capital 9947.0 from 10000; `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`.
- Exit distribution: 37 `ttl_expired`, 35 `stop_loss`, 26 `take_profit`.
- TTL share improved from 50.0% to 37.8%, and trade frequency fell from 6.27
  to 3.89 trades/day. This is still a bounded SOL diagnostic, not full-history
  H1 acceptance.

### Next steps

1. Do not run full-history H1 acceptance yet. The bounded January smoke still
   takes about 6 minutes 35 seconds for 745 H1 bars.
2. Continue focused H1 geometry grids before broad Optuna: compare `ttl` 12,
   24, 36, 48; `rrr` 1.0, 1.25, 1.5; and `max_sl_distance_atr` 3.0, 4.0,
   5.0 on the same bounded slice.
3. Add trigger/side diagnostics before accepting metrics: the max-4 run is
   near break-even overall, but both long and short PnL remain slightly
   negative in this window.
4. Profile/cache MTF SMC replay only after parity tests prove no-lookahead
   output remains identical.

---

## Status as of 2026-06-02 (session 28)

**Active work:** continue M2 donor MTF acceptance after H1 structural
stop-source selection.

Completed this session:

- Updated the MTF spec with the H1-vs-H4 structural stop-source contract.
- Implemented H1 structural stop-source selection in donor `crypt_ensemble`.
  H4 remains the primary setup stop; H1 execution mode can replace it only
  with a valid, same-direction, known, closer H1 structural stop.
- Added focused tests for choosing a closer H1 stop and keeping H4 when the
  H1 candidate is wider.
- Reran bounded SOL H1 MTF smoke:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`.
- Updated BACKLOG, DONE, MTF docs, and CHANGELOG with the diagnostic result.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean after formatting one test file.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 22 passed, 1 existing pandas warning.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 95 passed, 3 existing pandas warnings.
- Bounded SOL H1 MTF smoke command:
  `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --from 2025-01-01 --to 2025-02-01 --strategy strategies/crypt_ensemble_h1.json --output /tmp/crypt_donor_h1_mtf_smoke_h1_stop_source`
  -> completed in about 6 minutes 35 seconds.

Current bounded smoke diagnostic:

- 745 H1 signal rows.
- Signal distribution: 57 long, 102 short, 586 neutral.
- 159 tradeable signals; stop-source distribution among them: 153 H1, 6 H4.
- 158 trades: 57 long, 101 short.
- Final capital 9058.19 from 10000; `total_return_pct = -9.42`,
  `profit_factor = 0.66`, max drawdown `-10.44`.
- Exit distribution: 79 `ttl_expired`, 51 `stop_loss`, 28 `take_profit`.
- Trade frequency rose to 6.27 trades/day, so this is contract acceptance for
  H1 stop-source diagnostics, not profitability acceptance.

### Next steps

1. Do not run full-history H1 acceptance yet. The bounded January smoke now
   takes about 6 minutes 35 seconds for 745 H1 bars because H1 stop-source
   selection adds another SMC pass.
2. Retune H1 setup geometry before broad Optuna: TTL, RRR, stop-distance caps,
   and trigger filters. The latest bounded smoke still has 50% TTL exits and
   much higher trade frequency than the previous 35-trade diagnostic.
3. Profile/cache MTF SMC replay only after parity tests prove no-lookahead
   output remains identical.
4. Keep long-side filtering in scope. The latest bounded smoke produced 57
   long trades with total PnL -499.45 and 101 short trades with total PnL
   -442.36; both sides remain negative in this diagnostic window.

---

## Status as of 2026-06-02 (session 27)

**Active work:** continue M2 donor MTF acceptance after the no-lookahead test
expansion and entry-timing fix.

Completed this session:

- Added explicit H1 MTF no-lookahead tests for D1 forming-candle exclusion,
  future-known H4 structural stop-anchor rejection, and donor execution timing
  after a closed H1 trigger candle.
- Fixed donor `crypt_ensemble` rows to leave `entry_price` empty. This lets
  `ExecutionSim` enter at the next execution-bar open instead of treating the
  signal candle close as a custom current-bar entry.
- Reran bounded SOL H1 MTF smoke after the entry-timing fix:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`.
- Updated README, MTF spec, BACKLOG, DONE, and CHANGELOG with the next-open
  entry contract.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check backtester/src/backtester/strategies/crypt_ensemble.py backtester/tests/test_crypt_ensemble_strategy.py`
  -> clean.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_crypt_ensemble_strategy.py -q`
  in `backtester/` -> 20 passed, 1 existing pandas warning.
- `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q`
  in `backtester/` -> 93 passed, 3 existing pandas warnings.
- Bounded SOL H1 MTF smoke command:
  `PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev backtester run --data-source crypt-parquet --data-dir ../data --primary-timeframe 1h --symbol SOL-USDT-SWAP --from 2025-01-01 --to 2025-02-01 --strategy strategies/crypt_ensemble_h1.json --output /tmp/crypt_donor_h1_mtf_smoke_bounded_next_open`
  -> completed in about 4 minutes 7 seconds.

Current bounded smoke diagnostic:

- 745 H1 signal rows.
- H4 setup distribution: 124 BUY, 228 SELL, 393 HOLD.
- 176 `1h_candle_confirm` trigger rows; 35 had valid H4 structural stops and
  became tradeable signals.
- 35 trades, all short.
- Final capital 9357.25 from 10000; `total_return_pct = -6.43`,
  `profit_factor = 0.04`, max drawdown `-6.27`.
- Exit distribution: 21 `ttl_expired`, 14 `stop_loss`.
- All stops still used H4 order-block anchors (`sl_source_tf = 4h`,
  `sl_anchor_type = order_block`).
- Sample trades confirm next-open execution: first `signal_time` is
  `2025-01-03 13:00:00+00:00`, first `entry_time` is
  `2025-01-03 14:00:00+00:00`.

### Next steps

1. Do not run full-history H1 acceptance yet. Bounded January smoke still takes
   about 4 minutes for 745 H1 bars, so full-history H1 needs parity-safe
   caching/profiling.
2. Improve stop-source behavior for H1 mode. Current first slice always uses
   H4 structural stop source diagnostics; the spec still calls for H1
   structure to provide a closer protective stop when aligned with H4.
3. Retune H1 setup geometry before broad Optuna. The bounded smoke still has
   60% TTL exits and all tradeable stops are H4 order blocks.
4. Keep long-side filtering in scope. The bounded January H1 smoke produced
   zero long trades because D1/H1 gating only allowed bearish aligned entries
   in that window; this is diagnostic, not acceptance.

---

## Status as of 2026-06-02 (session 26)

**Active work:** continue M2 donor MTF acceptance. The donor `crypt-parquet`
range limiter is implemented as inclusive `--from` / `--to` CLI bounds, and
the bounded SOL H1 MTF smoke now completes with project Parquet data.

Important fix this session: date bounds now limit `StrategyData.primary`
and output rows, while `StrategyData.candles` keeps pre-start H1/H4/D1 history
up to `--to` for engine warmup. The first local run after restoring data
produced zero trades because the earlier limiter clipped all H4/D1 warmup and
made every H4 setup `HOLD`.

Completed smoke command:

```bash
cd backtester
PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python \
  uv run --extra dev backtester run \
  --data-source crypt-parquet \
  --data-dir ../data \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --from 2025-01-01 \
  --to 2025-02-01 \
  --strategy strategies/crypt_ensemble_h1.json \
  --output /tmp/crypt_donor_h1_mtf_smoke_bounded
```

Observed loader error: `crypt-parquet requires H4 candles for symbol
'SOL-USDT-SWAP'` before owner restored local data. After data was available
and the warmup-preserving limiter fix landed, the same smoke completed at:

`/tmp/crypt_donor_h1_mtf_smoke_bounded/20260602_191541`

Diagnostic result:

- 745 H1 signal rows.
- H4 setup distribution: 124 BUY, 228 SELL, 393 HOLD.
- H1 trigger produced 35 tradeable signals, all short.
- 35 trades, `trades_per_day = 2.9167`.
- Final capital 9340.69 from 10000; `total_return_pct = -6.59`,
  `profit_factor = 0.05`, max drawdown `-6.45`.
- Exit distribution: 21 `ttl_expired`, 14 `stop_loss`.
- All stops used H4 order-block anchors (`sl_source_tf = 4h`,
  `sl_anchor_type = order_block`), so H1 stop-source behavior is still not
  accepted.

### Next steps

1. Do not run full-history H1 acceptance yet. The bounded January smoke took
   about 4 minutes 18 seconds for 745 H1 bars after warmup history was
   preserved, so full-history H1 still needs parity-safe caching/profiling.
2. Expand MTF no-lookahead tests before accepting smoke metrics: D1 forming
   candle exclusion, future-known H4 structural object ignored, and H1
   trigger/entry timing through donor execution.
3. Improve stop-source behavior for H1 mode. Current first slice always uses
   H4 structural stop source diagnostics; the spec still calls for H1
   structure to provide a closer protective stop when aligned with H4.
4. Retune H1 setup geometry before broad Optuna. The bounded smoke has 60%
   TTL exits and H4 order-block stops with median stop distance in the
   3-5 ATR range depending on exit reason.
5. Keep long-side filtering in scope. The bounded January H1 smoke produced
   zero long trades because D1/H1 gating only allowed bearish aligned entries
   in that window; this is diagnostic, not acceptance.

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
