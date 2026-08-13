# Changelog

All notable changes to this project will be recorded here, session by session.

Format: keep entries terse. Date in `YYYY-MM-DD`. Newest on top.

---

## 2026-08-05 — Backtester regression runbook

- Added `docs/backtester_regression.md` as the canonical agent runbook for
  checking whether the backtester still reproduces the current production v6
  portfolio and the July 2026 live phase-B replay.
- Re-ran the current production v6 full replay on
  `2021-12-18T00:00:00Z` through `2026-06-29T14:00:00Z` after the
  last-price stop versus mark-price liquidation priority fix:
  `$1,237,819.83` final capital, `12278.20%` return, `1544` trades,
  `1.38` profit factor, `-0.53%` below-start drawdown, `-26.58%`
  peak-to-trough drawdown, and `0` liquidation exits.
- Re-ran the live phase-B replay on `2026-07-18T00:00:00Z` through
  `2026-07-27T23:00:00Z` with `$102.34` capital:
  `$101.47` final capital, `-$0.87` total PnL, `17` trades, `16/1`
  closed/open, and exit mix
  `10 stop_loss / 4 take_profit / 2 ttl_expired / 1 open`.
- Documented that the 2026-07-13 through 2026-07-17 fresh replay is context
  only because the first three live shorts require archived live signal
  payload replay after later H1 candle repairs.

## 2026-08-05 — Mixed-timeframe DSS v3 portfolio audit

- Found and fixed a mixed-timeframe portfolio composition bug in
  `filtered_donor_portfolio`: catalog filter features were computed once from
  the portfolio outer candle grid. Adding a `15m` DSS candidate made the
  whole portfolio emit on `15m`, which caused existing H1 v6 donors to be
  filtered with 15m-derived `catalog_*` features.
- Catalog filter features are now joined per donor frame, so each nested
  donor keeps its own execution timeframe features even when the portfolio
  outer grid is faster.
- Added a regression test proving an H1 donor mounted into a 15m portfolio
  uses H1 catalog features for portfolio filters.
- Re-ran DSS v3 timeframe regression over
  `2021-12-18T00:00:00Z` to `2026-06-29T14:00:00Z` for one `15m` candidate,
  one `H1` candidate, and four `H4` candidates. The audit confirmed all
  baseline v6 donor events remain identical after adding each candidate:
  `old_events_same=True`, `old_missing=0`, `old_extra=0` for all six mixed
  portfolios. Results are in
  `results/dss_v3_timeframe_regression_20260805/timeframe_regression_summary.csv`
  and
  `results/dss_v3_timeframe_regression_20260805/timeframe_event_invariant_audit.csv`.
- Re-audited the suspicious `v6 + smac_012981` branch that previously showed
  `-76.64%` peak-to-trough drawdown. Found a minute intrabar execution bug:
  when separate mark-price data touched liquidation and last-price data touched
  the nearer protective stop in the same minute, `worst_case` returned
  `liquidation` before checking the stop. The simulator now lets the nearer
  structural stop/trailing stop close first; mark-price liquidation still
  applies when the protective stop was not touched.
- Added a regression test for separate last/mark 1m execution proving a
  last-price stop precedes deeper mark-price liquidation. Re-running
  `v6 + smac_012981` over the same period changed the branch from
  `$2.20M`, `-76.64%` peak-to-trough DD, `6` liquidations to `$3.60M`,
  `-65.49%` peak-to-trough DD, `0` liquidations. Old v6 donor events stayed
  identical to baseline (`1853/1853`, no missing/extra events).

## 2026-08-05 — Entry rejection diagnostics export

- Added `ExecutionSim.entry_rejections` and durable
  `entry_rejections.csv` export from `backtester run` whenever a non-zero
  scalar signal or portfolio `signal_events` entry reaches execution but does
  not open a position.
- Captured rejection context for portfolio audits: `signal_time`,
  `intended_entry_time`, `reason`, side, selected strategy, position group,
  entry/SL price, risk/rrr, capital, risk-base capital, available balance,
  open-position counts, same-side counts, locked margin, position value,
  required margin, required leverage, and signal metadata.
- Covered execution blockers including `max_positions`,
  `drain_on_group_change`, missing SL, risk-model rejection, precision
  rounding, invalid post-precision geometry, leverage tiers, aggregate
  liquidation buffer, missing trailing ATR, invalid trailing callback, fee/risk
  sanity, minimum net exposure, and margin cap.
- Added rejection counts by reason, selected strategy, and position group to
  `signal_diagnostics.csv`.
- Added regression tests for multi-event portfolio rejection capture and
  `entry_rejections.csv` export.
- Verified the export on `v6_plus_dssv3_016949` over
  `2021-12-18T00:00:00Z` to `2026-06-29T14:00:00Z`. The run wrote
  `results/recheck_v6_plus_dssv3_016949_with_entry_rejections/20260805_114545/entry_rejections.csv`
  with `354` rejected entry events: `320` `aggregate_liquidation_buffer` and
  `34` `risk_model_rejected`. All `36` rejected `dssv3_dssv3_016949` events
  were blocked by `aggregate_liquidation_buffer`.

## 2026-08-05 — OKX stop-fill classification incident fix

- Investigated production Telegram close notification for position
  `21fd3392` (`freq_4pw_r03_catcma_011465`, long SOL, entered
  `2026-08-03T18:00:00Z` at `$73.68`) that was reported as
  `exchange_closed_unknown`.
- Confirmed through OKX private fills and algo history that the position was
  closed by its stop loss, not manually: stop algo
  `3800966052188999680` became `effective` with `actualSide=sl`,
  `actualSz=0.6`, `slTriggerPx=72.99`; the fill occurred at
  `2026-08-04T00:58:40.143Z` at `$72.99`, with gross PnL `-$0.414` and exit
  fee `$0.021897`. The native trailing order `3800966091346706432` was
  cancelled after the stop fired.
- Fixed `allocate_closed_position_fills` so OKX child close fills that omit
  the originating algo id can still be attributed when the fallback is unique
  and conservative: same symbol, side, position side, OKX stop subtype,
  exact contract amount, close price near the stored SL/TP/trailing level, and
  no foreign algo identity.
- Added regression coverage for the real OKX child-order shape and for the
  safety case where a foreign algo identity must not be fallback-matched.
- Made the reduced same-side executor regression independent of wall-clock
  date by increasing its synthetic TTL.

## 2026-08-04 — DSS v3 portfolio composition audit fixes

- Investigated why DSS v3 candidates looked profitable standalone but hurt the
  v6 filtered donor portfolio when mounted one by one.
- Fixed `ExecutionSim` TTL semantics for mixed-timeframe strategy composition:
  `position_ttl_minutes` is now a first-class execution field and takes
  precedence over legacy `position_ttl_bars`; TTL expiry is evaluated by clock
  time, not by the outer simulator bar count.
- Propagated `position_ttl_minutes` through `Backtester.run`,
  `backtest_run_kwargs`, filtered donor portfolio signal events, promoted
  router replay rows, and shadow portfolio entry contexts.
- Fixed `filtered_donor_portfolio` timeframe inference so an all-H4 portfolio
  uses H4 instead of falling back to H1.
- Fixed DSS incremental replay parity: nested DSS strategies now build
  per-filter timeframe datasets before calling `SignalComposer`, matching the
  standalone `DSSStrategy.generate()` path.
- Fixed DSS incremental trigger replay parity: nested DSS strategies now also
  build the trigger `DiscoveryDataset` on the trigger timeframe instead of
  accidentally reusing the portfolio outer timeframe.
- Fixed mixed-timeframe portfolio event scheduling. A slower donor signal is
  now emitted on the outer bar immediately before the donor's own next-bar
  entry time; for example, an H4 donor signal at `20:00` mounted into an H1
  portfolio emits at `23:00` and enters at `00:00`, matching standalone H4
  next-bar semantics. Signal-event exports include `donor_signal_time` for
  auditability.
- Fixed `build_backtest_args` so `null` values from strategy JSON
  `backtest_args` no longer wipe an execution window already derived from CLI
  `--from/--to`.
- Fixed CLI timeframe resolution precedence so an explicit portfolio
  `params.candle_timeframe` or strategy `backtest_args.candle_timeframe` wins
  before nested donor inference.
- Added regression tests for TTL-minute precedence, `ttl_minutes` propagation,
  portfolio donor timeframe inference, DSS portfolio event TTL preservation,
  null strategy-file execution windows, explicit portfolio timeframe
  precedence, and slower-donor event scheduling.
- Verified `dssv3_016949` standalone replay and single-donor portfolio replay
  now match on `2021-12-18T00:00:00Z` to `2026-06-29T14:00:00Z`: `174`
  trades, `$12,265.75` final capital, `22.66%` return, and `-14.56%`
  peak-to-trough drawdown. Earlier DSS v3 one-by-one portfolio comparison
  numbers should be recomputed before making promotion decisions.
- Rechecked `dssv3_016949` as a production-like single donor after the
  event-schedule fix using H1 outer candles plus 1m intrabar execution. It
  finished at `$11,382.34` (`13.82%`), with `176` trades, `6.25%` win rate,
  `1.22` profit factor, `-3.08%` drawdown below start, and `-18.70%`
  peak-to-trough drawdown. This is lower than H4 bar-close standalone but no
  longer suffers from early H1 entries.
- Rechecked `v6_plus_dssv3_016949` after the event-schedule fix on the same
  window. It finished at `$1,169,478.35` (`11594.78%`), with `1678` trades,
  `32.80%` win rate, `1.35` profit factor, `-0.85%` drawdown below start, and
  `-26.75%` peak-to-trough drawdown. The matching current-code baseline v6
  finished at `$1,194,926.04` (`11849.26%`), with `1544` trades, `35.06%` win
  rate, `1.37` profit factor, `-0.53%` drawdown below start, and `-26.87%`
  peak-to-trough drawdown. The candidate is therefore only slightly negative
  marginally (`-$25,447.69`) instead of the earlier invalid `-$302k`/`-$87k`
  conclusions.
- Decomposed the remaining `dssv3_016949` marginal loss after the timing fix.
  The full portfolio emitted `179` DSS signal events but opened `143` DSS
  trades, while the single-donor replay opened `176`. The `36` full-portfolio
  missing events correspond to only `+$1,483.89` in single-donor dollars, so
  they are not the main loss source. The marginal delta is explained by shared
  account interactions: DSS account PnL `-$15,307.87`, changed PnL on common
  non-DSS trades `-$17,712.58`, baseline trades absent after adding DSS
  `-$9,395.94`, and one extra non-DSS trade `+$16,966.27`.

## 2026-08-04 — DSS v3 candidate portfolio evaluation

- Evaluated all six currently promoted DSS v3 candidates from
  `results/dss_v3_sol_all_endless_wr45_balanced_v4` through the downstream
  path: Optuna geometry search, standalone best-run backtest, and one-by-one
  addition to the current archived production v6 filtered donor portfolio.
- Added `optimized_strategy.json` export to `backtester optimize`, so an
  optimizer result can be replayed or mounted into a portfolio without
  hand-copying `best_trial.json` parameters.
- Fixed timeframe inference for `filtered_donor_portfolio`: a portfolio now
  infers the fastest nested donor execution timeframe when
  `params.candle_timeframe` is absent, and each nested donor builds its
  execution args from its own timeframe rather than inheriting the portfolio
  timeframe.
- Fixed minute intrabar execution validation for non-H1 execution candles:
  15m/H4/etc. strategies now validate 1m coverage against their own candle
  intervals instead of assuming H1 boundaries.
- Made intrabar 1m slicing use timestamp intervals (`current_time` to
  `next_time`) instead of deriving windows from bar index position. This keeps
  minute execution correct when the execution timeframe is not H1.
- Replaced the filtered donor portfolio's direct `tqdm` event loop with the
  shared backtester progress callback, so long portfolio signal generation
  reports through normal CLI logs instead of noisy terminal progress rows.
- Backfilled and verified missing SOL-USDT-SWAP 15m candles for
  `2025-07-01` through `2026-06-30`; 15m/H1/H4/1d and 1m execution data are
  now continuous through the evaluation window.
- Baseline v6 on `2021-12-18T00:00:00Z` to `2026-06-29T14:00:00Z` remains
  `$1,194,926.04` final capital, `11849.26%` return, `1544` trades, `35.06%`
  win rate, `1.37` profit factor, and `-26.87%` peak-to-trough drawdown.
- None of the six DSS v3 candidates improved the v6 portfolio when added
  one-by-one without extra portfolio filters. The best added variant was
  `dssv3_016949` at `$892,041.06`, still `$302,884.98` below baseline with
  worse drawdown (`-29.42%` vs `-26.87%`).
- Wrote evaluation artifacts:
  `results/dss_v3_candidate_portfolio_eval_20260804/summary.csv` and
  `results/dss_v3_candidate_portfolio_eval_20260804/summary.md`.

## 2026-08-04 — Backtest and Optuna progress logs

- Added shared elapsed/rate/ETA progress logging for long CLI workflows.
- Updated `mandate_score` from a strict monthly-floor penalty into a
  money/drawdown-aware optimizer objective. The new score directly rewards
  total return, penalizes drawdown below initial capital non-linearly, penalizes
  peak-to-trough drawdown, and keeps monthly-floor diagnostics as softer
  penalties so sparse and medium-frequency DSS v3 candidates are not flattened
  into equivalent bad scores.
- `backtester run` now reports strategy-signal generation time and simulation
  progress by bars with ETA, while keeping optimizer-internal backtests quiet.
- Added a heartbeat for strategy signal generation, so long `strategy.generate`
  phases report elapsed time every 10 seconds instead of leaving the terminal
  silent until signals finish.
- Added real DSS signal-generation progress inside `SignalComposer`: feature
  builds by timeframe, trigger, filter alignment, and filtering are now reported
  as measurable steps with elapsed time and ETA.
- Added in-process discovery dataset/feature caching for DSS timeframe
  datasets, and made DSS Optuna signal caching ignore exit geometry because DSS
  signals do not depend on RRR/TP/trailing settings. Verified that the second
  Optuna trial reuses signals and that `best_run` export hits the same cache.
- `backtester optimize` now suppresses Optuna per-trial INFO spam and reports
  owner-readable trial progress with elapsed time, trial rate, ETA, and current
  best value.
- Compacted DSS strategy CLI summaries so large trigger/filter parameter
  dictionaries no longer dominate the command output.
- Optimized DSS discovery feature generation by caching timeframe datasets
  in-process and vectorizing the slow rolling linear regression, SMC
  order-block state, Supertrend, and ATR trailing-stop calculations. On the
  `smac_018020` DSS v3 smoke, signal generation dropped from roughly
  `48-54s` to `14s` while preserving the same `$10,802.32` final capital,
  `8.02%` return, `306` trades, `43.46%` win rate, and `1.04` profit factor.
- Added a native fixed-entry fast exit search for DSS optimizer runs where
  `strategy_param_search=False`. The command now builds DSS signals once,
  ranks exit family/RRR/TTL/risk/trailing/TP choices without Optuna
  `Study/Trial` overhead or full `ExecutionSim` scans per trial, and still
  exports `best_run` through the full backtester. A 5000-trial smoke completed
  in `33s` end-to-end after the cold signal build; a 100-trial smoke exported a
  full best run with `$16,058.90` final capital, `60.59%` return, `306` trades,
  `22.22%` win rate, and `1.28` profit factor. Standard non-DSS optimization
  keeps the previous Optuna TPE/Hyperband behavior.
- Fixed `backtester run` CLI override precedence for DSS candidate JSONs:
  explicit `--risk-percent`, `--rrr`, `--ttl-minutes`, trailing, and related
  execution flags now override DSS JSON defaults instead of being overwritten
  by `params`. Replaying the `smac_018020` optimizer winner now matches the
  optimizer `best_run`: `$15,638.10` final capital, `56.38%` return, `306`
  trades, `19.93%` win rate, and `1.17` profit factor.
- Fixed DSS fast optimizer scoring to honor `risk_base_period` the same way as
  `ExecutionSim`. The previous native fast path always sized risk from current
  capital, which inflated high-risk `tp_pct` proxy returns under the default
  monthly risk base and could mislead `mandate_score`. A 50k smoke after the
  fix selected `sl_rrr`, `rrr=9.0`, `position_ttl_minutes=3120`,
  `risk_percent=0.5`; fast proxy estimated `72.10%` return and the full
  best-run backtest produced `$16,716.41`, `67.16%` return, `306` trades,
  `22.22%` win rate, and `1.31` profit factor.
- Replaced the native DSS fast optimizer's pure random scan with an adaptive
  sampler: random warmup, top-128 elite local mutations, parameter dedup, and
  20% continued random exploration. Progress logs now include unique parameter
  count and sample-source counts. On `smac_018020`, adaptive search reached the
  previous random-50k best score by about 12k trials while preserving the same
  full best-run result.
- Made the native fast optimizer's elite archive behavior-diverse by tracking
  unique money/mandate outcomes instead of letting equivalent parameter rows
  fill the whole top archive.
- Fixed native fast `sl_rrr_trailing` evaluation to match the full simulator:
  invalid entry ATR now blocks the entry, activation no longer counts as fixed
  take-profit when activation and TP are the same level, and trailing stops use
  adverse gap-through fills. This removed a false trailing winner that proxy
  scored near `72%` while full `ExecutionSim` produced only `23.48%`.

## 2026-08-04 — DSS v3 candidate optimizer/backtest smoke

- Verified the top DSS v3 promoted candidate
  `smac_018020_pt_ps_smc_order_block_retest` through the downstream pipeline.
- `backtester optimize` accepted the DSS v3 JSON directly, inferred
  `Candle timeframe: 15m` from candidate metadata, and produced
  `best_trial.json`, `best_geometry_summary.txt`, and `best_run/`.
- One-trial Optuna smoke result chose `tp_pct`, `rrr=2.0`,
  `position_ttl_minutes=3060`, `risk_percent=0.5`, and `tp_move_pct=0.072`;
  the best run had `$16,821.00` final capital, `68.21%` return, `306` trades,
  `16.34%` win rate, and `1.23` profit factor.
- `backtester run` accepted the same DSS v3 JSON directly, inferred
  `Candle timeframe: 15m`, and completed with `$10,802.32` final capital,
  `8.02%` return, `306` trades, `43.46%` win rate, and `1.04` profit factor.
- Fixed endless DSS backend exhaustion handling: a batch containing only
  already-seen candidates no longer makes an endless backend exit with status
  `stopped`. Bounded searches keep the previous stop behavior. Verified a
  bounded all-backend matrix smoke after the loop fix.

## 2026-08-03 — Production v6 regression audit

- Re-ran and fixed the current production strategy regression for
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`
- Root cause: old promoted DSS donor JSONs carry legacy `atr_sl_mult`, but the
  new DSS v3 executable-stop fallback used only `directional_sl_move_pct=0.004`.
  That made old production stops roughly half as wide and broke exit timing.
- Restored legacy DSS stop semantics: `dss_strategy` and `dss_incremental` now
  use `atr_sl_mult` when present, falling back to `directional_sl_move_pct` only
  for newer directional-only candidates.
- Added internal backtest/optimizer warmup loading: `--from/--to` remain the
  execution/reporting window, while crypt-parquet candle loading starts 30 days
  earlier for indicator context. Exported `ohlcv.csv` is trimmed back to the
  execution window.
- Phase B live/backtest reconciliation is restored on current code/data:
  `17` rows, `16/1` closed/open, exit distribution
  `10 stop_loss / 4 take_profit / 2 ttl_expired / 1 open`, closed PnL
  `-$0.85356390` versus archived `-$0.84001035`.
- Full archived-period v6 no longer shows the regression loss. Current repaired
  local data gives `$1,194,926.04` final capital, `11849.26%` return, `1544`
  trades, and `1.37` profit factor; the archived snapshot remains
  `$1,098,402.88`, `10884.03%`, `1515` trades, and `1.48` profit factor.
- Fixed a discovery dataset regression where callers that explicitly supplied
  an execution OHLCV frame no longer passed the remaining candle frames as
  H4/D1 context features.
- Fixed DSS matrix report refresh crashes on large `signal_identity_keys`
  CSV fields by raising the Python CSV field-size limit before reading DSS
  viability/ranked files. Verified a bounded all-backend matrix smoke.
- Reduced endless DSS CSV bloat by writing full `signal_identity_keys` only for
  promoted rows; rejected rows keep `signal_fingerprint` and `signal_set_size`.
  Compacted `results/dss_v3_sol_all_endless_wr45_balanced_v4` from `7.5G` to
  `400M` while preserving the four promoted candidate exports.

## 2026-08-03 — DSS v3 audit fixes

- Fixed `search-signals` multi-symbol execution so repeated `--symbol` values
  produce distinct symbol-scoped windows instead of silently scanning only the
  first symbol.
- Made DSS signal-overlap novelty durable across resume/migrated journals by
  persisting and restoring `signal_identity_keys` from viability rows.
- Changed Island-QD and Hyperband-QD feedback loops to train on rejected and
  duplicate candidates, not only promoted candidates.
- Made adaptive backend `random_unseen` injections use an independent random
  DSS candidate sampler instead of only relabeling model proposals.
- Kept DSS missing-candle backfill hints owner-facing by removing agent-only
  `MPLCONFIGDIR` / `UV_CACHE_DIR` env prefixes from generated commands.

## 2026-08-03 — Default Optuna exit-family search

- Changed `backtester optimize` defaults into a post-DSS geometry search:
  one run now searches `exit_family`, `rrr`, `position_ttl_minutes`,
  `risk_percent`, `trail_distance_atr` for trailing exits, and `tp_move_pct`
  for TP-percent exits while keeping strategy parameter search disabled.
- Set default optimizer ranges to `rrr=1..10`, `risk_percent=0.25..3.0`,
  `position_ttl_minutes=60..10080`, `trail_distance_atr=0.5..10`, and
  `tp_move_pct=0.004..0.14`.
- Added `best_geometry_summary.txt` beside `best_trial.json` so the winning
  exit family and money parameters are readable without raw Optuna parsing.

## 2026-08-03 — TTL minutes source of truth

- Moved backtester/Optuna TTL search to `position_ttl_minutes`; simulator
  `position_ttl_bars` is now derived from the strategy execution timeframe.
- Updated DSS v3 exports so TTL is only a runnable downstream default
  (`position_ttl_minutes=720`), not a DSS search/evaluation parameter.
- Updated live execution TTL handling to expire by wall-clock minutes and
  migrate legacy open-position state from hour-like `ttl_bars` values to
  minute values.
- Updated owner CLI docs to prefer `--ttl-minutes*` overrides and keep old
  bar-based `--ttl*` flags as legacy reproduction inputs.

## 2026-08-03 — DSS signal-overlap novelty guard

- Fixed DSS backend novelty handling so promoted candidates are checked before
  viability rows are written, preventing duplicate signal sets from remaining
  exportable.
- Added signal identity keys to directional metadata and reject high-overlap
  promoted signal sets as `duplicate_signal_set`, not only exact fingerprint
  duplicates.
- Updated CatCMA-QD, Hyperband-QD, Island-QD, SMAC-QD, and directional search
  loops to use the shared pre-write novelty decision.

## 2026-08-03 — Backtester CLI surface pruning

- Removed dead owner-facing `backtester` Click commands from the product
  surface. The remaining backtester commands are only `run`, `optimize`,
  `search-signals`, and `search-signals-matrix`.
- Kept `python -m crypt` and `python -m crypt.backfill` as runtime/data module
  entrypoints.
- Removed obsolete help tests for the deleted commands and updated DSS reports
  to point validation toward `backtester run` / `backtester optimize`.
- Updated `docs/cli.md` with the complete current command list.

## 2026-08-03 — Compact owner CLI defaults

- Simplified owner-facing `backtester run`, `backtester optimize`,
  `search-signals`, and `search-signals-matrix` defaults: `data/`,
  `SOL-USDT-SWAP`, full available history, and `$10,000` capital are now the
  normal path.
- Hid rarely used technical flags from the main Click help while keeping them
  accepted for advanced/reproduction cases.
- Changed default Optuna trials from smoke-sized `25` to `50,000`.
- Added `full` / `all` aliases for omitted crypt-parquet date bounds.
- Added `docs/cli.md` as the compact command runbook and updated README/archive
  reproduction commands away from old manual timeframe/data-source flags.
- Replaced obsolete active DSS v2/PineScript multi-step wording with current
  DSS v3 directional search references.

## 2026-08-03 — DSS v3 endless runtime fixes

- Removed the old privileged timeframe semantics from the backtester/DSS/live
  code path: `StrategyData` now carries `candles_by_timeframe`, components use
  explicit timeframe accessors, and crypt-parquet loads all candle channels as
  equal bundle entries.
- Renamed discovery datasets from `primary` to `ohlcv` and migrated DSS
  feature builders, signal composer alignment, directional evaluation,
  backtester runners, optimizer/walk-forward adapters, live signal runner, and
  focused tests off `.primary` access.
- Updated the timeframe cleanup backlog: the remaining hard migration
  is the runner-selected `execution_timeframe`/`execution_frame()` surface, not
  the old privileged-frame contract.
- Removed the runner-selected `StrategyData.execution_frame()` surface:
  backtester, optimizer, walk-forward, fixed-candidate reports, regime matrix,
  DSS objective, and live signal generation now receive an explicit OHLCV
  frame from their caller or require a component-owned timeframe.
- Renamed the public crypt-parquet runner option to `--candle-timeframe`; it is
  now a CLI input-frame selector and is no longer stored in `StrategyData`
  metadata.
- Fixed DSS runtime progress so refreshed endless reports preserve the last
  exported candidate count instead of resetting `exported` to zero on regular
  per-candidate progress writes.
- Fixed directional candidate export to replace stale
  `directional_candidates/directional_*.json` files when the ranked top set
  changes, keeping the export directory aligned with the current shortlist.
- Fixed the default directional endless generator so adjacent batches no longer
  reuse the same batch-local RNG stream and stop after duplicate-only batches.
- Capped SMAC-QD surrogate training to the latest 5,000 observations and added
  a 512-evaluation refit cadence so resumed endless searches do not spend
  hours refitting the random forest on the full journal before updating
  progress.
- Updated `/tmp/dss_snapshot.py` to show stale backends and count exported
  candidate JSONs when older progress files under-report exports.
- Added DSS directional `signal_fingerprint`/`signal_set_size` audit fields and
  made directional candidate export deduplicate shortlist entries by exact
  `(window, bar_time, side)` signal sets, preventing multiple promoted JSONs
  for candidates that would enter the market at the same times.
- Added `/tmp/dss_candidate_audit.py` for top-candidate clone checks; it reports
  exact config clones, exact money-vector clones, repeated trigger/filter
  families, and optional recomputed signal timestamp overlap.
- Added backend-level DSS signal novelty tracking: directional, CatCMA-QD,
  Island-QD, Hyperband-QD, and SMAC-QD now distinguish new promoted signal sets
  from promoted clones, avoid using cloned signal sets as novelty parents or
  survivor increments, and feed duplicate promoted signals back to model-based
  backends as negative examples.
- Rebalanced DSS directional scoring/export toward active viable strategies:
  sparse candidates remain eligible, but medium/frequent candidates now receive
  stronger ranking and backend-feedback preference, and shortlist export
  round-robins `frequent -> medium -> sparse` instead of filling from sparse
  first. `/tmp/dss_snapshot.py` now shows the `freq` bucket explicitly.
- Added default execution geometry for DSS v3 directional candidates:
  exported JSONs now include `rrr=2.0`, `risk_percent=1.0`,
  `position_ttl_minutes=720`, and `directional_sl_move_pct`; `DSSStrategy`
  backfills missing/invalid directional stops from the next open with that
  percentage so old directional-only candidates can run through the regular
  backtester/optimizer.
- Removed manual candle-timeframe selection from `backtester run` and
  `backtester optimize`: both commands now derive the replay OHLCV timeframe
  from DSS candidate trigger metadata and pass that exact frame into the
  simulator/optimizer, preventing accidental mixed-timeframe replays.
- Added `--algorithms all` as the default DSS matrix backend selector and
  verified a bounded all-backend matrix smoke.
- Fixed DSS bounded-run artifacts so `progress.json` is finalized to
  `stopped`/`failed` instead of staying `running` after process exit.
- Added `trigger_timeframe` and `filter_timeframes` columns to
  `directional_viability.csv` so matrix/snapshot audits can inspect timeframe
  behavior without opening candidate JSONs.
- Moved strategy candle-timeframe resolution into shared CLI runner helpers and
  updated live signal generation to use the strategy-owned execution timeframe
  for candle freshness, loader selection, ATR context, and next-open tracking.

## 2026-07-31 — AI-first project template artifact

- Added `ai-first-project-template/` as a temporary in-repo starter kit for
  new AI-first projects.
- Included a one-time `.bootstrap/FIRST_RUN.md` marker and `AGENTS.md`
  bootstrap flow where the first agent asks only for a free-form project
  description, then fills product/task/architecture docs and removes the
  bootstrap instructions.
- Added portable docs for product brief, vision, requirements, architecture,
  roadmap, active work, backlog, ideas, ADRs, and reusable task/spec/bug
  templates.

## 2026-07-31 — DSS v3 audit hardening

- Added DSS preflight validation for all trigger/filter candle timeframes so
  missing `15m`/`1h`/`4h`/`1d` data fails before candidate search starts and
  prints a non-interactive `crypt.backfill` command for the needed symbol/date
  range.
- Added the same candle preflight to `search-signals-matrix` before child
  processes are spawned, so a missing timeframe now fails the matrix launcher
  before any backend starts.
- Lowered the default DSS directional barrier win-rate gate from `0.55` to
  `0.45` so endless search keeps more candidates for later money-like
  inspection instead of rejecting them too early.
- Extended `python -m crypt.backfill --data-types ohlcv` to fetch `15m`
  candles alongside `1h`/`4h`/`1d`, making DSS v3's 15m search space
  backfillable through the existing API.
- Documented the project-wide missing-candle contract: research CLIs fail fast
  with backfill commands, while production runtime uses env-driven auto-backfill
  or fail-fast preflight and never waits for `y/n`.
- Added the same backfill hint to the shared crypt-parquet data loader when
  required H4 or selected primary candles are empty, covering non-DSS
  backtester commands that use project candle storage.
- Fixed historical OHLCV backfill/REST repair so H1 writes are not blocked by
  strict aggregation mismatches against existing 1m execution candles; the
  H1-vs-1m invariant remains enabled by default for normal store writes.
- Replaced the old local weighted sampler with the maintained
  `cmaes.CatCMAwM` mixed-variable optimizer in `catcma_qd`, including
  continuous/integer/categorical DSS encoding, full-population ask/tell
  updates, and backend state probabilities.
- Added `cmaes>=0.13.0` and recorded a general agent rule to prefer maintained
  dependencies over custom implementations for any non-trivial code when they
  reduce risk or maintenance cost.
- Audited `search-signals-matrix` after DSS v3, fixed crypt-parquet empty
  timeframe frames so all five child backends can launch against v3 candle
  loading, and added a regression test that the matrix launcher passes current
  DSS options to child `search-signals` processes.
- Changed `search-signals-matrix --min-signals-per-week` default from `4.0` to
  `0.0` so default matrix runs can preserve sparse candidates instead of
  silently biasing all backends toward frequent signal families.
- Changed `search-signals-matrix --n-trials` to optional and made omitted
  `--n-trials` the default endless per-backend mode, matching the primary DSS
  workflow for journal migration across machines.
- Fixed `search-signals` endless CLI startup so omitted `--n-trials` no longer
  creates a bounded click progress bar with `length=None`; endless runs now use
  runtime `progress.json`/`heartbeat.json` files for progress tracking.
- Added a P1 backlog item to remove `primary` timeframe semantics across the
  project and treat concrete triggers/filters as explicit timeframe-contract
  components.
- Fixed crypt-parquet DSS windowing so `15m`, `H1`, `H4`, and `D1` candle
  frames are all clipped to the requested start/end range before search sees
  them.
- Fixed directional labeling to evaluate signal counts, overtrading,
  minimum-count gates, window duration, and barrier outcomes on the configured
  trigger timeframe instead of the run primary frame.
- Added conservative catalog timeframe eligibility for CLI search-space
  expansion so blocks are no longer blindly emitted on every timeframe.
- Changed `--n-trials` semantics to count unique evaluated candidates;
  duplicate hashes are journaled without consuming callback/evaluated budget,
  and exhausted search spaces exit instead of spinning.
- Made endless QD runs refresh directional ranked/export/archive reports after
  each completed batch.
- Removed active-run artifact migration from old names; DSS v3 now reads and
  writes only current `candidates.jsonl`/`directional_*` artifact names.
- Changed SMAC-QD observation fidelity labels from old wording to
  `directional_reject` and `directional_pass`.
- Made DSS search spaces expand catalog blocks into concrete `name@timeframe`
  instances for `15m`, `H1`, `H4`, and `D1`, so CLI searches now explore
  trigger/filter timeframe layouts instead of defaulting to H1.
- Updated directional, CatCMA-QD, Island-QD, Hyperband-QD, and SMAC-QD candidate
  generation, mutation, and surrogate encoding to sample and learn
  timeframe-aware trigger/filter instances while keeping param bounds on base
  catalog names.
- Fixed coarser-timeframe filter alignment to shift source candles to inferred
  close time before as-of joins, preventing lower-timeframe events from reading
  unfinished H4/D1 candles.
- Updated `SignalComposer` to pass filter-local event metadata from each
  aligned filter dataset, so existing metadata-based filters now actually use
  their configured timeframe.
- Hardened persistent runtime behavior: stale dead-PID locks are removed,
  failed runs write a failed heartbeat, and resumed summaries restore evaluated
  and survivor counts from existing directional reports.
- Fixed resume so candidates already recorded in `candidates.jsonl` but missing
  from `directional_viability.csv` are evaluated before new generation across
  directional, CatCMA-QD, Island-QD, Hyperband-QD, and SMAC-QD backends.
- Fixed resumed directional progress callbacks to account for already evaluated
  rows, and kept QD resume summaries on the actual candidate count even when a
  resumed output already contains more candidates than the current budget.
- Renamed active DSS v3 output artifacts to directional names:
  `candidates.jsonl`, `directional_viability.csv`,
  `directional_ranked.csv`, `directional_candidates/`,
  `backend_state/*.csv`, and `archive/directional_frequency_archive.csv`.
- Renamed the active search module/API/config away from old DSS naming:
  `dss_directional_search`, `DSSDirectionalResult`,
  `run_dss_directional_search`, and `--algorithm directional`.
- Removed remaining old-worded options from active `search-signals` and
  `search-signals-matrix` CLI/docs surface; `--directional-min-wr` is the
  supported win-rate gate.
- Added regression coverage for real timeframe instance generation and
  closed-candle as-of alignment.
- Verification: `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/backtester/test_dss.py -q`;
  `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run mypy src/backtester/strategy_discovery`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check` on changed DSS files.

## 2026-07-31 — DSS v3 persistent directional search completed

- Added timeframe-aware DSS trigger/filter instance serialization and stable
  hashes: `trigger_timeframe`, `filter_timeframes`, and `name@timeframe`
  labels are now part of candidate identity.
- Repeated filter names are allowed when timeframe or params differ; exact
  duplicate filter instances are rejected.
- Updated `SignalComposer` to resolve instance labels back to catalog block
  names while preserving timeframe labels in signal rationales, selecting the
  requested timeframe from `StrategyData`, as-of aligning filter datasets to
  trigger events, and caching `(data, timeframe, window, symbol)` features
  across candidates.
- Added `DSSSearchRuntime` with single-writer output locks,
  `candidate_journal.jsonl`, `seen_candidates.jsonl`, `progress.json`,
  `heartbeat.json`, `backend_state/`, and `archive/` directories.
- `search-signals --n-trials` is now optional: omitted means endless resumable
  search, provided means a bounded run.
- CatCMA, Hyperband, Island, SMAC, and the default runner now use the shared
  seen registry/journal/progress path and skip exact duplicate candidate hashes.
- Adaptive backends periodically inject random-unseen candidates and mutate
  directional survivors as novelty candidates.
- Added crypt-parquet `15m` candle loading and exposed `15m` as a DSS primary
  timeframe; missing unavailable timeframes fail explicitly instead of falling
  back silently.
- Removed active SMAC/package imports of legacy `dss_objective`, isolating the
  old Optuna/backtest helper from the DSS v3 search path.
- Reworded active DSS v3 summaries, manifests, spec, ADR, and task text around
  directional labeling instead of directional search wording.
- Removed the completed DSS v3 implementation task from active/backlog task
  files.
- Added regression coverage for timeframe-aware hashing, duplicate instance
  rejection, multi-timeframe as-of alignment, and durable runtime artifacts.
- Verification: `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/backtester/test_dss.py -q`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run mypy` on changed active DSS files;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check` on changed DSS files.

## 2026-07-30 — DSS v3 multi-timeframe search direction

- Added ADR-0062 for DSS v3 persistent multi-timeframe search while keeping the
  DSS name.
- Added `docs/discovery/direct_signal_search_v3.md` with the candidate model:
  trigger/filter instances are `name + timeframe + params`, repeated filter
  names are allowed across different timeframes, and exact duplicate instances
  are invalid.
- Specified shared random unseen/novelty injection for all DSS search backends.
- Clarified DSS v3 as directional-labeling-only: no replay backtests and no
  RRR/risk/TTL/ATR-stop/trailing/portfolio sizing fields in
  DSS candidates.
- Added DSS v3 frequency-class requirements so sparse and frequent candidates
  can be discovered and archived in the same search run, with independent
  archive/export quotas rather than a single global frequency floor.
- Recorded that DSS v3 may break DSS v2 candidate/state/journal/export
  compatibility; old DSS v2 artifacts are historical only.
- Specified endless `search-signals` mode when `--n-trials` is omitted, with
  resumable journals, seen registry, backend state, archive checkpoints,
  heartbeat/progress files, and live-execution isolation.
- Started the first implementation slice: removed DSS geometry fields from
  `TrialConfig`, `DSSCandidate`, and `DSSSearchSpace`; changed
  `SignalComposer` output to neutral SL/TP placeholders for directional rows;
  made `search-signals` default to directional labeling; and added
  frequency-class directional behavior/export reporting.
- Converted CatCMA, SMAC, island, and hyperband QD runners to active
  directional behavior: no replay scoring files are read or written, and local
  search models are updated from directional scores.
- Removed legacy replay runner entrypoints from the DSS directional search runner
  (`legacy replay scoring helpers`) so new DSS search code
  cannot import them accidentally.
- Added a P1 backlog task to implement DSS v3.
- ADRs: ADR-0062.
- Verification: `PYTHONPATH=src uv run pytest tests/backtester/test_dss.py -q`;
  `uv run ruff check` on the touched DSS files.
- Files touched: `src/backtester/strategy_discovery/`, `src/backtester/__main__.py`,
  `tests/backtester/test_dss.py`, `docs/discovery/`, `docs/decisions/`,
  `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-30 — Documentation reframed as research workbench + live execution

- Rewrote `README.md` as a shorter human-facing product surface: research
  workbench plus live execution module.
- Replaced `docs/investment_mandate.md` with `docs/strategy_benchmark.md`.
  The benchmark is now documented as an optimization/reporting target, while
  owner production promotion can override it.
- Rewrote `AGENTS.md` around the current project model, owner override rule,
  active runtime config source of truth, and ETA-controlled command policy.
- Added a current-reality note to `docs/tasks/ROADMAP.md` without rewriting
  owner-defined milestones.
- Cleaned `docs/tasks/IN_PROGRESS.md` down to active work only.
- Cleaned `docs/tasks/BACKLOG.md` down to unfinished queued work only.
- Removed the long historical `docs/tasks/DONE.md`; completed work now belongs
  in changelogs, archives, and ADRs.
- Updated distant-TP docs with the current owner-selected narrow v6 mount.
- Moved the previous long changelog to `CHANGELOG_ARCHIVE.md`.
- Removed `.cursor/rules/` because AGENTS is now the repository operating
  manual.
- ADRs: none.
- Files touched: root docs, `docs/tasks/`, `docs/backtester/`,
  `docs/archive/`, `docs/decisions/`, `.cursor/`.

## 2026-07-29 — Distant-TP component and v6 portfolio review

- Added signal-event exports and distant-TP diagnostics/audit fields.
- Added optional causal dynamic TP policy shared by backtest and live execution.
- Established flexible sandbox composition in ADR-0061 and docs.
- Tested global and targeted TP policies; only the narrow
  `freq_4pw_r03_catcma_011465` 6%/RRR-3 mount had positive evidence.
- Owner selected the narrow v6 mount for production; it remains intentionally
  narrow and should not be widened without longer forward evidence.

## 2026-07-28 — Live execution hardening and reconciliation audit

- Added durable monthly risk-base checkpoints and safer state recovery.
- Reworked Telegram execution notifications in Russian.
- Started live/backtest reconciliation for the July 2026 SOL live period.
- Identified the need for exact live entry replay snapshots and stronger
  Railway state/volume safety checks.

## 2026-07-29

- Added event-level portfolio signal exports (`signal_events.csv`), per-bar
  event counts, and event-aware diagnostics so donor portfolio audits no
  longer rely on the zero-valued legacy scalar signal.
- Clarified Telegram full-sync balance as total/free funds plus
  `в работе/маржа`, with OKX equity (including unrealized PnL) when available.
- Added the signal diagnostics and distant-TP analysis contracts under
  `docs/backtester/`.
- Added an opt-in causal dynamic TP policy shared by backtest and live
  execution. It lowers only effective RRR for configured wide/stale targets,
  preserves signal admission/SL/risk sizing, and records adjustment audit
  fields in trades and live position state.
- Added ADR-0060 and the TP policy contract in
  `docs/backtester/tp_reachability_diagnostics.md`.
- Mounted the distant-TP policy through canonical
  `params.components.distant_tp`, with portfolio-wide and per-donor mount/
  unmount overrides; kept `params.tp_policy` as a compatibility alias.
- Established the flexible-sandbox composition rule in `AGENTS.md`,
  `docs/architecture/flexible_sandbox.md`, and ADR-0061.
- Clarified the owner-authorized backtest rule: an explicitly requested run is
  launched once, observed for ETA, completed when under three minutes, and
  handed back to the owner only when it exceeds that threshold or lacks
  progress visibility. Ran the dynamic-TP portfolio and targeted comparisons;
  neither is production-ready after cross-period evaluation.
- Attempted to repair the 2026-06-30 minute-data gap; stopped after OKX network
  retries produced no progress, leaving the owner a one-day backfill command.
- Completed matched full-history replays for `2022-01-01` → `2026-06-30`:
  unchanged v6 baseline finished at `$956,449.50` (`+$946,449.50` PnL,
  1,508 trades, peak-to-trough DD `-39.23%`), while the targeted dynamic-TP
  mount finished at `$735,712.38` (`+$725,712.38`, 1,568 trades, DD
  `-33.27%`). The mount saved 5.96 pp of drawdown but lost `$220,737.12`
  of PnL, so it remains default-off. Artifacts are under
  `results/strategy_review/v6_2022_2026_{baseline,targeted}_full/`.
- Searched distance-only dynamic-TP thresholds on the full history. The best
  tested candidate mounts only on `freq_4pw_r03_catcma_011465`, triggers at
  TP distance `>=6%`, disables recency, and lowers RRR to `3.0`: 1,560 trades,
  `+$1,175,598.82` PnL, and `-33.26%` peak-to-trough DD versus baseline
  `+$946,449.50` and `-39.23%`. Candidate artifact:
  `results/strategy_review/v6_tp_search_r03_d6_only_rrr3/`; it remains
  default-off pending holdout validation.
- Ran separate donor checks before combining components: `sparse_r06` was
  PnL-neutral, while `sparse_r12` and `freq_r11` lost roughly `$94k` and
  `$99k` respectively. The current evidence supports only the `freq_r03`
  mount; combining all wide-TP donors is rejected.
- Completed the first untouched forward validation on the continuous live-audit
  window `2026-07-13` → `2026-07-27`. On the same 24 trades and `$10,000`
  start, baseline returned `+$307.89` (PF 1.23, peak-to-trough DD `-9.50%`)
  while the `freq_r03` 6%/RRR-3 candidate returned `+$481.48` (PF 1.38,
  DD `-8.71%`): `+$173.59` / `+56.4%` holdout PnL with no frequency loss.
  Artifacts are under `results/strategy_review/v6_holdout_{baseline,candidate*}`;
  the candidate remains a research mount because the window contains only 15
  days and 24 trades.
- Owner-approved the narrow production mount: the canonical v6 portfolio JSON
  now keeps `params.components.distant_tp.enabled=false` and enables only
  `freq_4pw_r03_catcma_011465` with `TP distance >=6%`, original RRR `>=4`,
  and effective RRR `3.0`. No Railway deploy was performed by the agent.

## 2026-07-28 — Hardened live risk-base continuity and Russian Telegram alerts

- Added immutable, checksummed primary/backup monthly risk-base checkpoints
  bound to the configured execution state path. Missing, partial, conflicting,
  non-finite, or future-schema state now blocks only new live entries instead
  of silently re-anchoring monthly sizing from the current balance.
- Added the exact-manifest July migration path (`2026-07`,
  `102.3381502678064`) and a Railway verification/runbook before migration
  variables are removed. New-month anchors require clean exchange sync.
- Added durable previous-snapshot recovery provenance, bounded idempotent missed-signal
  audit IDs, and persistence-before-background-delivery for risk-base/missed
  Telegram alerts so delivery retries cannot consume the H1 callback deadline.
- Rewrote live and legacy Telegram presentation in Russian, preserving PnL,
  SL/TP, OKX, strategy/order identifiers, the canonical `[UNCALIBRATED]`
  marker, HTML escaping, and the Telegram message-size cap.
- Added persistence, migration, checkpoint-pair, sync, state-path, Telegram
  escaping/length, non-SOL label, and callback-idempotency regressions.
- ADRs: ADR-0059; operational amendments to ADR-0010 and ADR-0054.
- Files touched: `src/crypt/execution/`, `src/crypt/sinks/`, `tests/execution/`,
  `tests/sinks/`, `docs/decisions/`, `docs/execution/`, `docs/deploy/`,
  `docs/tasks/`, `.env.example`, `scripts/`, `README.md`, `CHANGELOG.md`.

---

## 2026-07-28 — Started live execution / backtest reconciliation audit

- Verified read-only Railway production-volume/log access and OKX private
  fills, orders, algo-orders, and ledger access.
- Froze the v6 strategy/data provenance, split the comparison at the proven
  18–19 July state-epoch reset, and recorded exact owner-run replay commands.
- Classified known callback failures, the eight-hour 23 July sync gate, late
  startup behaviour, and aggregate-position accounting before interpreting
  PnL differences as strategy defects.
- Joined the owner-run replay artifacts: post-rollout signal parity is 16 of
  17, with one confirmed sync-blocked short worth `+$4.99897320` in replay;
  the pre-rollout fresh replay remains invalid for aggregate PnL because H1
  repair changed its historical event set.
- Added a P1 follow-up for monthly risk-base continuity across deployments.
- Added a P2 follow-up for zero-valued portfolio signal diagnostics.
- ADRs: none.
- Files touched: `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-24 — Fixed partial live-close recovery and audited missed signals

- Fixed same-side reduction attribution when an executed constituent stop
  disappears but its sibling TP or trailing order remains pending.
- Prefer an exact constituent-size match before consuming smaller candidates,
  preventing a `1.04 -> 0.50 SOL` reduction from closing the wrong local lot.
- Dirty exchange sync still blocks orders, but now runs the latest strategy
  read-only and logs one `MISSED SIGNAL` record per actionable event.
- Persisted `blocked_signal_events_total` in execution state schema v9.
- Added regressions for sibling-protection residue, exact-size attribution,
  missed-signal details/counting, and state persistence.
- Verified focused execution tests (`24 passed`) and ruff; strict mypy was
  stopped after two silent minutes under the progress policy.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-19 — Made REST authoritative for stored candle repair

- Added an explicit OHLC rewrite policy to `ParquetStore`: normal callers still
  reject conflicting closed-candle rewrites, while REST repair paths may replace
  stored OHLC with a warning.
- Live REST refresh and backfill now repair stored closed-candle conflicts
  instead of failing the H1 execution cycle.
- WebSocket candle conflicts no longer overwrite stored history; they trigger
  REST repair because REST is authoritative when the two disagree.
- Added regressions for explicit store repair and WebSocket-to-REST conflict
  repair.
- Verified the full CI command set locally.
- ADRs: none.
- Files touched: `src/crypt/data/`, `src/crypt/backfill/`,
  `src/crypt/execution/`, `tests/data/`, `tests/execution/`,
  `tests/backfill/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-19 — Fixed Railway preflight logging and strategy default

- Moved runtime logging setup into a shared helper used by `python -m crypt`,
  deploy preflight, and standalone backfill.
- Preflight/backfill now respect `LOG_LEVEL`; normal INFO logs go to stdout,
  warnings/errors go to stderr, and backfill progress bars write to stdout.
- Added a Railway entrypoint default for the archived live strategy config so
  a missing `EXECUTION_STRATEGY_CONFIG` env var no longer falls back to
  nonexistent `strategies/live/active.json` after a long backfill.
- Added a regression for stdout/stderr log routing.
- Verified the full CI command set locally.
- ADRs: none.
- Files touched: `src/crypt/`, `scripts/`, `tests/runtime/`, `docs/deploy/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-19 — Fixed local CI failures

- Fixed the execution 1m backfill test fake so it matches the production
  `has_complete_minute_range` keyword contract without ruff argument warnings.
- Applied ruff formatting to files that failed `ruff format --check`.
- Fixed strict mypy typing in deploy preflight timestamp helpers and live signal
  timestamp parsing.
- Verified the full CI command set locally: ruff check, ruff format check,
  mypy strict, pytest, and `uv lock --check`.
- ADRs: none.
- Files touched: `src/crypt/`, `tests/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-19 — Trimmed post-ADR-0058 portfolio archive

- Removed heavy reproducible run artifacts from
  `docs/archive/candidates/post_adr0058_tail_control_portfolio`, including full
  backtest trees, source-run directories, full signal/OHLCV/trade CSVs, charts,
  and per-trade candle reports.
- Kept decision-critical archive evidence: version summary, donor composition,
  strategy configs, reproduction commands, provenance, compact metrics/monthly
  snapshots, diagnostics, strategy attribution, and live replay note.
- Rewrote archive metadata and post-ADR-0058 strategy JSON research notes so
  they no longer point at deleted run-output directories.
- Verified archive size is `384K`; no remaining references to `results/`,
  `full_backtests`, `source_research`, or `full_artifact_paths`; JSON snapshots
  validate with `python -m json.tool`.
- ADRs: none.
- Files touched: `docs/archive/candidates/`, `strategies/archive/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-19 — Prepared Railway live execution deploy

- Switched Railway startup from the DSS search worker to a live execution
  entrypoint.
- Added `crypt.runtime.deploy_preflight`, which removes zero-byte parquet
  files, checks H1/H4/D1 live OHLCV coverage, and runs OKX backfill before
  `python -m crypt --execution-only` starts.
- Added Railway bootstrap environment variables and rewrote the Railway deploy
  guide for `/app/data` volume-backed data, logs, and live state.
- Made a date-sensitive execution test independent of the current wall clock.
- Verified focused runtime/execution slice: `44 passed`; ruff clean on touched
  Python files.
- ADRs: none.
- Files touched: `src/crypt/runtime/`, `scripts/`, `tests/runtime/`,
  `tests/execution/`, `docs/deploy/`, `docs/tasks/`, `railway.toml`,
  `.env.example`, `README.md`, `CHANGELOG.md`.

---

## 2026-07-16 — Extended REST fallback callback timeout

- Diagnosed a live OKX/Telegram connectivity outage where WebSocket triggers
  correctly fell back to REST, but the REST execution callback could be
  cancelled by the same 90s timeout used for WebSocket callbacks while OKX
  candle retries were still in progress.
- Added a separate 180s timeout for `rest_fallback` callbacks so degraded OKX
  REST retries can exhaust cleanly before the scheduler reports the boundary
  as failed.
- Added a regression proving REST fallback can outlive the shorter WebSocket
  callback timeout.
- Disabled new entries during `startup` H1 reconciliation. Startup still
  refreshes candles, syncs OKX, and manages existing positions, but it no
  longer opens a catch-up trade from the previous closed H1 bar.
- Added a regression matching a restart at `2026-07-16T18:06Z` after a
  `2026-07-16T17:00Z` signal.
- Verified focused execution/runtime slice: `38 passed`; ruff clean on touched
  files.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `src/crypt/runtime/`,
  `tests/execution/`, `tests/runtime/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-15 — Released H1 fallback after callback timeout

- Fixed an H1 scheduler edge case where a timed-out WebSocket execution callback
  could keep the boundary marked `in_flight` while Telegram error reporting
  retried, causing the `*:02` REST fallback to skip the same boundary.
- The boundary is now released for retry before slow error reporting runs; only
  fully successful callbacks are marked completed.
- Added a regression matching the live `orders-algo-pending` timeout followed by
  slow notification reporting.
- Verified focused runtime scheduler slice: `8 passed`; ruff clean on touched
  runtime files.
- ADRs: none.
- Files touched: `src/crypt/runtime/`, `tests/runtime/`, `docs/tasks/`,
  `CHANGELOG.md`.

---

## 2026-07-15 — Preserved WebSocket next open after outage repair

- Fixed live H1 recovery after an OKX/Telegram DNS outage: when WebSocket
  ingestion repairs missing candles through REST, the WebSocket boundary
  `next_open` now remains authoritative after the repair.
- This prevents the catch-up path from raising `forming H1 time is not after
  the signal bar` after REST repair temporarily records a stale forming H1
  open.
- Added a regression that reproduces the `2026-07-15T04:00Z -> 10:00Z` style
  gap repair and verifies the boundary open survives.
- Verified focused live signal/runtime slice: `16 passed`; ruff clean on
  touched files.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`, `docs/tasks/`,
  `CHANGELOG.md`.

---

## 2026-07-14 — Added per-trade profit sweep

- Added `--capital-sweep trade_profit` to bank trading capital above the
  initial capital immediately after each profitable closed trade.
- Kept `monthly_profit` behavior unchanged; both sweep modes use the same rule
  that recovery below initial capital is not withdrawn.
- Added focused execution-simulator regressions for repeated winning-trade
  sweeps and below-initial recovery.
- Verified focused backtester slice: `64 passed`; ruff clean on touched
  backtester files.
- ADRs: none.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/tasks/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-07-14 — Blocked silent H1 candle corruption

- Hardened `ParquetStore.save_candles()` so an already stored closed candle can
  no longer be silently overwritten with different OHLC values for the same
  `open_time`.
- Added H1-vs-1m validation: when complete last-price 1m data already exists
  for an H1 interval, the incoming H1 candle must aggregate from those minutes
  or the write is rejected.
- Verified current SOL data after repair: all complete 1m-backed H1 bars now
  match on high/low/close; only small historical first-minute open differences
  remain in older 2022-2023 data.
- Added regression tests for conflicting closed-candle updates and H1/1m
  mismatch rejection.
- Verified data/live focused slice: `39 passed`; ruff clean on touched files.
- ADRs: none.
- Files touched: `src/crypt/data/`, `tests/data/`, `docs/tasks/`,
  `CHANGELOG.md`.

---

## 2026-07-14 — Replayed first v6 live trades against backtester

- Backfilled and validated SOL 1m last/mark candles for the live replay
  window; both stores have complete 1m coverage through
  `2026-07-14T12:59:00Z`.
- Repaired two local SOL H1 rows from minute aggregation after replay
  validation caught H1-vs-1m mismatches.
- Fixed live fill classification for OKX triggered stop fills where the stop
  algo id is reported in `clOrdId`.
- Reclassified the three first real v6 SOL live exits in
  `data/live_positions.json` as `stop_loss` with OKX exit price, fee, account
  PnL, and constituent PnL.
- Added a live replay archive note showing that the three saved live signal
  events replay as three backtester stop losses at the same stop minutes.
- Verified focused execution tests: `13 passed`.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/archive/candidates/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-14 — Prevented mixed-timeframe candle writes

- Fixed WebSocket boundary ingestion to persist closed H1/H4/D1 candles in
  separate `ParquetStore.save_candles()` calls.
- Hardened `ParquetStore.save_candles()` so one write batch may contain only
  one symbol, timeframe, and price type.
- Repaired the live SOL D1 parquet file by removing two intraday rows that had
  been written into `ohlcv_1d.parquet` during the mixed-timeframe ingest.
- Verified store/signal-runner/runtime slice: `26 passed`.
- ADRs: none.
- Files touched: `src/crypt/data/`, `src/crypt/execution/`,
  `tests/data/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-14 — Reconciled reduced same-side live constituents

- Fixed live reconciliation for same-side aggregate OKX positions: when the
  exchange size decreases and one local constituent's protection orders are
  gone, that constituent is now closed locally instead of blocking sync with a
  `position_size_mismatch`.
- Applied the same reduced-away detection during startup reconcile and normal
  H1 position management.
- Added a regression for the live v6 case where two local shorts (`0.66+0.63`)
  become one exchange short (`0.66`) after the second constituent closes.
- Verified focused live reconciliation slice: `48 passed`.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-14 — Repaired live candle gaps around UTC midnight

- Fixed live WebSocket candle ingestion so continuity gaps detected after a
  boundary ingest are repaired through REST before signal generation.
- Kept existing higher-timeframe history when OKX temporarily returns no
  non-H1 candles, instead of failing the entire H1 execution cycle.
- Added regressions for WebSocket gap repair and empty D1 refresh handling.
- Verified focused runtime/live execution slice: `44 passed`.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Fixed OKX H1 WebSocket subscription id

- Fixed OKX H1 WebSocket subscribe requests to use alphanumeric request IDs
  without hyphens, matching the OKX V5 WebSocket contract and avoiding live
  `60033 Parameter id error` rejects.
- Made scheduler shutdown treat cancellation during REST fallback as normal
  operator stop instead of a noisy job exception.
- Updated H1 trigger docs to use portfolio-neutral wording.
- Verified runtime/live execution slice: `40 passed`.
- ADRs: none.
- Files touched: `src/crypt/runtime/`, `tests/runtime/`,
  `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Removed stale Core4 wording from live execution

- Removed Core4-specific wording from live CLI help and neutral no-signal logs
  so operator output reflects the selected strategy JSON instead of an old
  portfolio branch.
- Changed the live execution default strategy path to neutral
  `strategies/live/active.json`; production runs should pass
  `EXECUTION_STRATEGY_CONFIG` explicitly.
- Updated live execution examples to the current post-ADR-0058 v6 portfolio.
- Verified runtime help and focused live execution slice: `33 passed`.
- ADRs: none.
- Files touched: `src/crypt/`, `README.md`, `.env.example`,
  `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Made live signal timestamps fail closed

- Fixed live signal timestamp parsing so malformed signal/store timestamps raise
  instead of silently becoming `datetime.now(UTC)`.
- Added regression coverage for valid string timestamps and invalid timestamp
  rejection in the live signal runner.
- Verified data-loader/store/signal-runner slice: `29 passed`.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Removed legacy feature lookahead in strategy research

- Fixed legacy `som`/`forest` order-block features so confirmed OB labels are
  emitted only after the confirmation window closes, instead of backfilling the
  candidate candle with future impulse data.
- Kept OB size diagnostics tied to the confirmed OB zone, not the confirmation
  candle range.
- Fixed `TradeAnalyzer` Ichimoku `chikou_span` so predictor research uses the
  lagged close known at entry time instead of `close.shift(-26)`.
- Added regression tests for OB prefix stability and causal Chikou extraction.
- Verified focused backtester slice: `62 passed`.
- ADRs: none.
- Files touched: `src/backtester/strategies/`, `src/backtester/trade_analyzer.py`,
  `tests/backtester/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Preserved trailing geometry during live restart recovery

- Fixed live restart recovery so recovered filled entries no longer recompute
  native trailing activation from the actual fill price. They keep the
  pre-submit H1 next-open geometry used by the normal live path and
  `ExecutionSim`.
- Added a regression where an H1-open planned trailing entry at `100` recovers
  an actual fill at `101` and still keeps activation at `102`.
- Verified focused execution/backtester slice covering live multi-event
  execution, signal runner timing, risk, OKX order client, exchange sync, fill
  classification, trade replay, minute execution, and trailing policy.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Added donor-level PnL diagnostics

- Kept `pnl_abs` / live `realized_pnl` as account-level PnL from OKX
  same-side `aggregate_entry_price` for cash reconciliation.
- Added `constituent_pnl_abs` and `constituent_pnl_rel` to backtester trade
  exports, plus `constituent_realized_pnl` to live closed-position state and
  fill classification.
- Documented the accounting split so strategy attribution can use donor-level
  diagnostics without breaking account equity math.
- Verified focused execution/backtester slice: `139 passed`.
- ADRs: none.
- Files touched: `src/backtester/`, `src/crypt/execution/`, `tests/`,
  `docs/execution/`, `docs/tasks/`, `README.md`, `CHANGELOG.md`.

---

## 2026-07-13 — Restored authenticated live H1-open sizing parity

- Fixed authenticated live execution so the current OKX quote no longer replaces
  the H1 next-open price before risk sizing, SL/TP placement, or native trailing
  geometry.
- Kept quote/fill drift as alert-only observability under ADR-0054, with actual
  fill stop-risk alerts still emitted when slippage increases planned risk.
- Added authenticated drift coverage proving a quote different from H1 open does
  not mutate the planned order size or protection geometry.
- Verified focused execution/backtester slice: `137 passed`.
- ADRs: none.
- Files touched: `src/crypt/execution/`, `tests/execution/`, `docs/execution/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Live/backtest audit follow-ups

- Audited the current backtester/live execution path after the post-ADR-0058
  portfolio archive. Found one P0 parity risk: authenticated live execution
  sizes and resolves exits from the current quote instead of the H1 next-open
  price used by `ExecutionSim`.
- Added follow-up backlog items for authenticated H1-open sizing parity and
  per-donor PnL attribution under OKX side aggregation.
- Verified the focused unit-test slice covering execution parity, signal
  events, risk, OKX order params, exchange sync, fill classification, and
  margin policy: `137 passed`.
- ADRs: none.
- Files touched: `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-07-13 — Archived post-ADR-0058 portfolio lineage

- Created a complete candidate archive for the v1-v7 post-ADR-0058 portfolio
  branch at `docs/archive/candidates/post_adr0058_tail_control_portfolio/`.
- Preserved portfolio config snapshots, donor composition by version,
  owner-run reproduction commands, complete copied full backtests, source
  Optuna research artifacts, compact backtest snapshots, strategy attribution,
  and monthly strategy PnL for all seven versions.
- Recorded the current branch interpretation: v5 maximizes final account value
  (`$10,000` to `$1,360,197.25`), while v7 is the cleaner lower-DD branch
  (`$10,000` to `$866,481.95`, PF `1.90`, peak-to-trough DD `-32.33%`).
- ADRs: none.
- Files touched: `docs/archive/candidates/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-12 — Prepared sparse and frequent DSS seeds for Optuna

- Exported 24 current Stage 1 near-miss DSS strategies for owner-run Optuna:
  12 sparse seeds and 12 frequent 4-per-week seeds.
- Artifact root:
  `results/post_adr0058_top_for_optuna_20260712/`, with a combined
  `manifest.csv` and per-batch strategy JSONs.
- Added a progress-aware owner-run Optuna launcher for the split-RRR batch;
  it keeps per-strategy logs separate and shows active jobs, total trials,
  elapsed time, and ETA in one terminal view.
- Recorded the completed split-RRR Optuna result at
  `results/post_adr0058_optuna_top_train_big_split_rrr_20260712/`: all best
  trials remain mandate `discard` on 2022-2024 train, with the best sparse seed
  at `+374.37%` but 20 below-floor months, six DD breach months, and worst
  monthly DD `-26.56%`.
- Built an exploratory all-24 shared-capital portfolio at
  `results/post_adr0058_portfolio_all24_split_rrr_20260713/`, freezing each
  donor with its split-RRR Optuna best-trial execution parameters.
- Archived the all-24 portfolio as
  `strategies/archive/filtered_donor_portfolio_post_adr0058_all24_v1.json` and
  created the first reduced risk-capped cut as
  `strategies/archive/filtered_donor_portfolio_post_adr0058_reduced_v2_risk1.json`.
- Recorded owner-run v2 result: `$10,000` to `$62,074.13`, PF `1.10`,
  drawdown below start `-2.49%`, peak-to-trough DD `-39.28%`, 19 liquidations,
  and four unsafe liquidation-buffer exits.
- Created return-first v3 at
  `strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v3.json`,
  keeping all 12 v1 donors with positive all-period PnL and preserving original
  Optuna risk.
- Recorded owner-run v3 result: `$10,000` to `$883,881.46`, PF `1.09`,
  drawdown below start `-1.36%`, peak-to-trough DD `-62.81%`, 19 liquidations,
  and three unsafe liquidation-buffer exits.
- Created return-first v4 at
  `strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v4_positive_v3.json`,
  removing only the four donors that were net-negative in the v3 full-period
  run while preserving original Optuna risk for the remaining eight donors.
- Recorded owner-run v4 result: `$10,000` to `$340,047.49`, PF `1.09`,
  drawdown below start `-1.36%`, peak-to-trough DD `-58.44%`, 18 liquidations,
  and four unsafe liquidation-buffer exits.
- Created tail-control v5 at
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v5_filtered_v3.json`,
  keeping all 12 v3 donors and original Optuna risk while adding one
  entry-known catalog filter per donor.
- Recorded owner-run v5 result: `$10,000` to `$1,360,197.25`, PF `1.39`,
  drawdown below start `-6.79%`, peak-to-trough DD `-39.14%`, nine
  liquidations, and no unsafe liquidation-buffer exits.
- Created tail-control v6 at
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`,
  removing only the two v5 net-negative donors while preserving the remaining
  filters and original Optuna risk.
- Recorded owner-run v6 result: `$10,000` to `$1,098,402.88`, PF `1.48`,
  drawdown below start `-17.75%`, peak-to-trough DD `-39.23%`, nine
  liquidations, zero unsafe liquidation-buffer exits, and 1515 trades.
- Created tail-control v7 at
  `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v7_apr2026.json`,
  adding four extra entry-known filters to the main `2026-04` loss contributors
  while preserving v6 donors and original Optuna risk.
- Recorded owner-run v7 result: `$10,000` to `$866,481.95`, PF `1.90`,
  drawdown below start `-6.85%`, peak-to-trough DD `-32.33%`, five
  liquidations, zero unsafe liquidation-buffer exits, and 935 trades.
- Recorded owner-run all-24 full-period attribution: `$10,000` to
  `$172,325.77` but with profit factor `1.01`, peak-to-trough DD `-90.72%`,
  27 liquidations, and one unsafe liquidation-buffer exit.
- Marked frequent seeds as lower-trust research material because several top
  rows rely on tiny 2022 sample counts before failing the 4-per-week screen.
- ADRs: none.
- Files touched: `results/post_adr0058_top_for_optuna_20260712/`,
  `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-08 — Core4 v3 aggregate-average rerun result

- Recorded owner-run aggregate-average minute artifact
  `results/core4_v3_okx_aggregate_average_2026070/20260708_054313/`.
- Result: `$10,000` → `$24,195.85`, `+141.96%`, profit factor `1.05`,
  drawdown below start `-9.20%`, peak-to-trough drawdown `-42.84%`,
  3,425 entries, nine liquidations, and two open trades.
- Cash reconciles from `$10,000 + $14,204.343855912753 closed PnL -
  $8.4947749 open entry fees = $24,195.849081012755`.
- 2025 mandate remains `discard`: four of twelve months pass the 15% floor,
  eight are below floor, five breach monthly DD, and worst monthly drawdown is
  `-19.42%`.
- Verified the new artifact exports `aggregate_entry_price`; H1 OHLCV has
  39,711 continuous rows with zero gaps/duplicates.
- Could not locally compare signal/OHLCV hashes against
  `results/core4_v3_minute_last_mark_20260702/20260702_102019/` because that
  superseded artifact is absent in this workspace.
- Owner redirected the next research loop toward fresh post-ADR-0058 strategy
  discovery, candidate Optuna only after quick exact replay screens, and a new
  shared-capital portfolio from non-duplicative winners.
- Owner completed the first post-ADR-0058 all-window DSS matrix at
  `results/post_adr0058_dss_matrix_sol_20260708/`: 250,000 candidates across
  five algorithms, zero Stage 1 survivors, zero exported candidates. Next
  search should be single-window specialist discovery for a multi-strategy
  portfolio basket, not big Optuna.
- ADRs: none.
- Files touched: `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-03 — Correct OKX aggregate average-entry accounting

- Fixed Core4 same-side accounting to match OKX: increasing exposure updates
  one volume-weighted average entry, while partial closes preserve that
  average.
- Realized PnL now uses the exchange aggregate average instead of each logical
  constituent's entry. Logical entries continue to own their independent
  SL/TP/native-trailing/TTL geometry.
- Aggregate margin is allocated pro rata and liquidation is recalculated from
  the preserved average, remaining size, common leverage, and current size
  tier.
- Live synchronization adopts OKX `avgPx` and `liqPx` for every local
  constituent on the side. Live close/recovery PnL and replay use the same
  aggregate average.
- Added `aggregate_entry_price` to backtest exports and live state schema 8,
  with migration from earlier state files.
- Added regressions for partial-close PnL, same-side entry averaging, exchange
  synchronization, margin allocation, and fill classification.
- Validation: complete project test suite passes excluding the known
  assertion-passing pytest shutdown-hang test; focused Ruff and strict live
  mypy pass.
- The 2026-07-02 `$25,100.59` artifact is superseded; an owner-run canonical
  minute rerun is required.
- ADRs: added ADR-0058.
- Files touched: `src/backtester/`, `src/crypt/execution/`, `tests/`,
  `strategies/archive/`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`,
  `README.md`.

## 2026-07-02 — Minute last/mark execution replay

- Verified the conservative v2 artifact at `$32,956.20` final account,
  `-10.33%` drawdown, four liquidation-buffer fail-safe exits, and exact cash
  reconciliation from `$10,000`.
- Added resumable monthly-partitioned OKX 1m last-trade and mark-price
  backfill, including safe parallel `last_1m` / `mark_1m` jobs.
- Added a typed execution-only minute-data contract; H1/H4/D1 signals remain
  unchanged and do not copy or consume minute frames.
- Added sequential 1m stop/TP/native-trailing replay and mark-price
  liquidation. Minute-enabled runs reject missing, duplicate, unsorted, or
  misaligned coverage instead of falling back to H1.
- Owner backfilled both SOL series through `2026-06-29 23:59 UTC`: each has
  2,383,200 continuous rows. All H1 high/low/close aggregates match; eight
  official OKX H1 opens differ from the first 1m open by at most `$0.06`, so
  the validator retains H1 as entry and accepts the in-range minute open.
- Owner canonical minute artifact `20260702_102019` produced 3,422 entries,
  `$25,100.59` final account, `+151.01%`, `1.05` profit factor, and `-9.20%`
  below-start drawdown. Cash and all eight mark-price liquidations reconcile;
  signal and H1 OHLCV exports are byte-identical to H1 v2.
- Exposed the artifact's standard peak-to-trough drawdown of `-42.54%`
  separately instead of labeling the ADR-0030 below-start metric as generic
  maximum drawdown. Corrected monthly mandate ordering for overlapping trades
  from entry order to deterministic exit order.
- The corrected 2025 mandate verdict is `discard`: five drawdown-breach months,
  `-19.68%` worst monthly below-start drawdown, and only five months above the
  15% return floor.
- Kept live native exchange protection as the real-time source of truth; no
  delayed closed-minute live control loop was added.
- Validation: full non-hanging project suite and focused Ruff pass. Existing
  legacy strict-mypy findings in `ExecutionSim`/CLI remain unchanged.
- ADRs: added ADR-0056 and ADR-0057.
- Files touched: `src/crypt/backfill/`, `src/crypt/data/`,
  `src/crypt/exchange/`, `src/backtester/`, `tests/`, `strategies/`,
  `docs/backfill.md`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`,
  `README.md`.

## 2026-07-02 — Corrected backtest reporting and post-close liquidation safety

- Fixed `Initial Capital` being inferred from an arbitrary first exit row when
  multiple positions close on one H1 boundary; every trade now carries the
  explicit account initial capital and execution sequence.
- Preserved deterministic same-timestamp equity ordering in
  `ResultsAnalyzer`.
- Added fail-safe closure when a constituent exit moves the remaining
  aggregate OKX side inside its required liquidation buffer; live closes on
  synchronization and backtest closes at the next H1 open.
- Verified artifact `20260701_141907` cash accounting independently:
  `$10,000 + $22,450.407` closed PnL - `$11.403` open entry fees =
  `$32,439.005`. Its signal and OHLCV files are byte-identical to the previous
  baseline; the large performance reduction comes from conservative execution
  and compounding, not lost signals.
- Validation: full non-hanging project suite, focused Ruff, strict live mypy,
  and diff checks pass.
- ADRs: amended ADR-0055.
- Files touched: `src/backtester/`, `src/crypt/execution/`, `tests/`,
  `strategies/`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`.

## 2026-07-01 — Durable recovery and conservative execution parity

- Added durable entry lifecycle and restart adoption of actual OKX entry
  price, contracts, fee, liquidation, and protection by deterministic client
  ID.
- Kept `closing` positions managed across restart, accumulated exact close
  fills, and retry only remaining reduce-only contracts after partial closes.
- Made isolated leverage side-specific; sync now verifies exchange leverage,
  isolated mode, protection, precision, and exact fill/order identity.
- Changed H1 execution to nearer-stop-first liquidation ordering,
  adverse-before-favorable trailing under `worst_case`, gap-open market fills,
  per-close aggregate liquidation refresh, and conservative taker TP fees.
- Routed periodic/startup health failures to Telegram, made parquet writes
  atomic/refuse corrupt overwrite, and bounded H1 callbacks before REST
  fallback.
- Added fee/precision config parity and actual-fill stop-risk alerts. Funding
  remains excluded by owner decision.
- Validation: full non-hanging project test suite passes; focused changed live
  code passes Ruff and strict mypy. New owner-run Core4 v3 canonical backtest
  is required.
- ADRs: added ADR-0055.
- Files touched: `src/backtester/`, `src/crypt/`, `tests/`, `strategies/`,
  `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `.env.example`.

## 2026-07-01 — Full-code live/backtest re-audit

- Confirmed signal, precision, and entry-fee parity, then found incomplete
  restart adoption for persisted entry intents and `closing` positions.
- Found H1 path-model errors/ambiguities in stop-versus-liquidation precedence,
  native trailing, gap fills, and same-side aggregate liquidation updates.
- Recorded P1 gaps in side-specific leverage setup, fill recovery/identity,
  actual-fill risk, configuration parity, health alerts, atomic parquet writes,
  and WebSocket callback deadlines.
- Validation: non-hanging functional suite passes; repository-wide Ruff has
  232 findings, strict mypy has 280 errors in 24 files, and focused live
  execution mypy passes.
- ADRs: none.
- Files touched: `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-07-01 — Entry drift is alert-only

- Removed the `EXECUTION_MAX_ENTRY_DRIFT_PCT` entry rejection; the setting now
  controls only warning/Telegram sensitivity.
- Live proceeds at market, then reports `ENTRY DRIFT [OK]` with H1 open,
  pre-submit quote, actual fill, H1-to-fill drift, quote-to-fill drift, and
  explicit confirmation that the entry executed.
- Retained fail-safe closes for post-fill liquidation and leverage-tier
  violations.
- Validation: full execution tests excluding the known shutdown hang, focused
  Ruff, and strict mypy pass.
- ADRs: added ADR-0054; partially superseded ADR-0051.
- Files touched: `src/crypt/execution/`, `tests/execution/`,
  `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `.env.example`.

## 2026-07-01 — Crash-safe live execution and precision/fee parity

- Persisted live entry intent before order submission and added deterministic
  reduce-only compensation for missing trailing or unsafe post-fill state.
- Changed TTL to confirm the market close before cancelling protection and to
  persist confirmed close state immediately.
- Replaced multi-position fill guessing with one-time exact identity
  allocation; ambiguous fills remain unknown.
- Added dated OKX SOL contract/amount/price precision to both live and
  backtester execution, including rounded trailing geometry.
- Debited entry fees at entry in both same-bar live sizing and the backtester;
  final metrics now include entry fees on still-open positions.
- Made entry-attempt Telegram delivery non-blocking and removed the CCXT
  all-market health-check failure caused by malformed unrelated instruments.
- Funding remains excluded by owner decision.
- Owner-run canonical artifact `20260701_091336` produced 3,420 entries,
  `$588,744.28` final capital, `45.17%` wins, `1.24` profit factor,
  `-6.78%` maximum drawdown, and 144 liquidations. Signal and OHLCV artifacts
  are byte-identical to the prior baseline, so changes are execution-only.
- Validation: complete execution/backtester tests pass excluding one known
  pytest shutdown hang; focused Ruff and strict mypy pass.
- ADRs: added ADR-0053.
- Files touched: `src/backtester/`, `src/crypt/execution/`,
  `src/crypt/runtime/`, `strategies/archive/`, `tests/`, `docs/execution/`,
  `docs/decisions/`, `docs/tasks/`.

## 2026-06-30 — Full live/backtest parity audit

- Confirmed byte-identical signal/cache parity and shared risk, leverage,
  aggregate liquidation, TTL, and native-trailing policy paths.
- Found P0 live safety gaps: non-atomic post-fill state, protection removed
  before confirmed TTL close, non-fail-safe trailing/post-fill safety errors,
  and ambiguous multi-position fill attribution.
- Found economic model gaps requiring a new canonical run after fixes:
  exchange amount/tick rounding, entry-fee timing, funding, market
  slippage/drift rejection, triggered-limit fee class, and mark-price
  liquidation.
- All non-hanging tests pass; one assertion-passing executor test still hangs
  at shutdown. Focused static checks retain existing `ExecutionSim` findings.
- ADRs: none.
- Files touched: `docs/execution/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-30 — Validated live Core4 signal cache

- Added a live-only `generate_latest()` path for filtered donor portfolios.
- Cached complete donor frames, recalculated exact full-history discovery
  features, replayed only a 512-bar donor tail, and required exact agreement
  across 128 overlap bars before accepting an append.
- Revised history, missing overlap, or any donor-frame mismatch now forces a
  cold complete donor rebuild.
- Kept external `backtester run` on the unchanged complete `generate()` path.
- Measured on 39,734 SOL H1 bars: full `31.8s`, cold cache `13.2s`, hourly
  append `6.8s`; the complete latest event matched exactly.
- Owner reran the canonical 39,711-bar backtest through
  `2026-06-29 14:00 UTC`; all seven exported CSV artifacts are byte-identical
  to pre-cache artifact `20260629_160832`.
- Focused execution/backtester tests, ruff, and strict mypy pass.
- ADRs: added ADR-0052.
- Files touched: `src/backtester/`, `src/crypt/execution/`,
  `tests/backtester/`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`,
  `README.md`.

## 2026-06-30 — WebSocket-confirmed H1 execution

- Replaced the fixed `*:02 UTC` primary Core4 trigger with an OKX business
  WebSocket listener prepared at `HH:59:30 UTC`.
- Execution now waits for `confirm=1` on the closing H1 candle, relevant H4/D1
  confirmations, and the first forming H1 update containing the real next open.
- Added text ping, reconnect/resubscribe, per-symbol/hour duplicate protection,
  execution error alerts, and retained `*:02` REST as a fallback.
- Added normal INFO/WARNING logs for every `ENTRY ATTEMPT` and `ENTRY REJECTED`
  with the same reason sent to Telegram.
- Verified a real public `candle1H` subscription against OKX. Focused
  execution/runtime tests, ruff, strict mypy, and `uv lock --check --offline`
  pass.
- ADRs: added ADR-0051.
- Files touched: `src/crypt/runtime/`, `src/crypt/execution/`,
  `src/crypt/__main__.py`, `tests/runtime/`, `tests/execution/`,
  `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `README.md`,
  `pyproject.toml`, `uv.lock`.

## 2026-06-29 — OKX SOL tiered liquidation model before v3 rerun

- Added `okx_sol_usdt_swap_2026_06_29` maintenance-margin tier schedule so
  SOL backtests/live execution use higher MMR and lower max leverage after the
  OKX size thresholds instead of assuming `0.004` forever.
- Made leverage selection side-scoped: an open same-side position reuses its
  current leverage and rejects unsafe aggregate tier transitions, while an
  empty side chooses fresh leverage from the current OKX tier.
- Threaded the schedule through backtester CLI, risk model, simulator exports,
  live settings, persisted positions, replay, and startup parity validation.
- Updated v3 Core4 strategy config, docs, README, `.env.example`, and tests.
- Validation: focused pytest passed; strict `src/crypt/execution` mypy passed;
  focused ruff `E,F,I` passed.
- ADRs touched: ADR-0049.
- Files touched: `src/backtester/`, `src/crypt/execution/`, `strategies/`,
  `tests/`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `README.md`,
  `.env.example`.

---

## 2026-06-29 — Liquidation-safe v3 and native OKX trailing parity

- Added shared OKX linear-liquidation formulas, a 0.5% stop buffer, safe
  leverage selection, explicit worst-case liquidation exits, and same-side
  aggregate liquidation.
- Replaced dynamic per-bar ATR trailing with native OKX `move_order_stop`
  geometry: fixed entry-known ATR14 callback spread and actual-fill activation.
- Added stable entry/close/algo client IDs, fill confirmation and fees,
  per-position SL/TP/trailing binding/cancellation, candle-gap repair, repeated
  sync alerts, and exact closed-trade replay.
- Real close test filled `0.41` SOL contracts at `73.43`, reconciled
  `-$0.2270047` including both fees, and ended with zero positions/orders and
  clean sync. OKX OCO sibling cancellation code `51400` is now idempotent.
- Set owner-selected causal v3 as the live default; all previous performance
  artifacts require a full rerun.
- Validation: full unit suite passes excluding one assertion-passing pytest
  shutdown hang; focused ruff and strict execution mypy pass.
- ADRs: added ADR-0049 and ADR-0050.
- Files touched: `src/backtester/`, `src/crypt/execution/`, `strategies/`,
  `tests/`, `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `README.md`.

---

## 2026-06-29 — Complete live execution Telegram error reporting

- Added `ENTRY ATTEMPT` and `ENTRY REJECTED` Telegram messages so every
  actionable Core4 donor event has an operator-visible start and terminal
  result.
- Added immediate `EXECUTION ERROR` messages for leverage/order failures, TTL
  close failures, candle refresh and signal generation failures, execution
  tick crashes, startup/runtime failures, missing OKX credentials, and exchange
  sync blockers.
- Persistent exchange-sync errors are sent on every H1 execution cycle by
  explicit owner direction; repeated blocker alerts are intentional.
- Updated live execution documentation, README, and dry-run acceptance criteria.
- Validation: 57 terminating execution tests and 3 shared multi-signal tests
  passed; `ruff check` and strict `mypy` passed. One H1 thread-pool test reaches
  `PASSED` but hangs during pytest shutdown and is tracked in `BACKLOG.md`.
- ADRs touched: ADR-0048 contract implementation only; no new decision.
- Files touched: `README.md`, `docs/execution/`, `docs/tasks/`,
  `src/crypt/`, `tests/execution/`, `CHANGELOG.md`.

---

## 2026-06-28 — Core4 execution-only dry-run cleanup

- Added `python -m crypt --execution-only` so Core4 live dry-runs and service
  runs can skip the legacy H4 alert monitor and use `EXECUTION_SYMBOLS` for
  startup OKX symbol checks.
- Fixed live candle freshness checks for timezone-aware Parquet `open_time`
  values; dry-run no longer fails with pandas' `tzinfo with the tz parameter`
  error.
- Execution-only startup logs now print the execution symbols instead of the
  legacy monitor symbol basket.
- Added INFO-level operator logs for each execution H1 tick: exchange sync
  summary, strategy generation start, no-event result, elapsed time, open
  position count, and final sync status.
- Routed standard-library `logging` through loguru so live execution and
  backtester strategy INFO logs actually appear in the `crypt` console/file
  output.
- Fixed execution-only heartbeat health checks so the periodic 6-hour check
  keeps using `EXECUTION_SYMBOLS` instead of the legacy monitor basket.
- Added dry-run-only sizing capital (`EXECUTION_DRY_RUN_CAPITAL`) so operator
  dry-runs can test `$10k`/`$30k` position sizing while still syncing the real
  OKX account balance and positions.
- Fixed OKX SOL swap sizing: live execution now rounds base-asset size down to
  OKX `lotSz` / ccxt amount precision (`0.01` contracts for SOL-USDT-SWAP)
  instead of flooring to whole contracts. This allows small live accounts to
  place valid fractional-contract orders and matches the cloned
  `signal_executor` contract rounding model.
- Fixed OKX pending algo-order sync: the raw OKX endpoint is now queried with
  required `ordType` values (`conditional`, `oco`, `trigger`,
  `move_order_stop`) instead of calling it without `ordType`.
- Updated live execution docs and task instructions so the operator dry-run no
  longer emits unrelated `HOLD/conf/regime` verdicts for the old symbol basket.
- Validation: `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
  (57 tests), `ruff check src/crypt/__main__.py src/crypt/execution
  tests/execution`, and `mypy src/crypt/__main__.py src/crypt/execution`
  passed.
- ADRs touched: ADR-0048.
- Files touched: `README.md`, `docs/execution/`, `docs/tasks/`,
  `src/crypt/`, `tests/execution/`, `CHANGELOG.md`.

---

## 2026-06-28 — Live execution Telegram reporting

- Added execution Telegram notifications for Core4 live trading: one full sync
  report per UTC day, one message after every recorded entry, and one message
  after every recorded exit.
- Persisted `last_daily_sync_report_date` in `live_positions.json` so service
  restarts do not spam duplicate daily sync reports.
- Startup reconciliation now keeps missing OKX positions as closed history,
  classifies the close from recent fills when possible, and sends an exit
  notification instead of silently dropping the local position.
- TTL closes now record `exit_time` and `exit_reason=ttl_expired` before
  notifying.
- Tightened live/backtester parity after re-audit: live startup now validates
  money-impacting execution defaults against strategy JSON `backtest_args`,
  `SignalEvent` carries `drain_on_group_change`, and live entry state records
  `risk_result.required_leverage` rather than assuming the configured max.
- Removed the backlog item for live sync blocker alerts; daily full-sync
  reporting now surfaces blocked sync status and reasons when Telegram is
  configured.
- Validation: `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q` (53 tests),
  `ruff check src/crypt/execution tests/execution`, and
  `mypy src/crypt/execution` passed.
- ADRs touched: ADR-0048.
- Files touched: `README.md`, `docs/execution/`, `docs/tasks/`,
  `src/crypt/execution/`, `tests/execution/`, `CHANGELOG.md`.

---

## 2026-06-28 — OKX live order parameter audit

- Compared the live `OKXTradingClient` ccxt path against the cloned
  `signal_executor` direct OKX REST implementation.
- Aligned live order parameters with OKX long/short isolated execution:
  leverage is now set for both `long` and `short` sides, entry orders include
  isolated margin and `positionSide`, take-profit is a limit attached algo at
  the target price, and market closes include `reduceOnly`, isolated margin,
  and the original position side.
- Kept live SL/TP trigger type on `last` price for backtester parity. The
  cloned direct executor uses mark-price SL, but Core4 backtests use
  last-trade OHLCV; switching live SL to mark would create hidden divergence.
- Added full-sync validation for OKX account position mode. New entries are
  blocked unless the account is in long/short mode.
- Updated the live execution spec and README with the OKX long/short mode
  requirement.
- Validation: `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q` (46 tests),
  `ruff check src/crypt/execution tests/execution`, and
  `mypy src/crypt/execution` passed.
- ADRs touched: ADR-0048.
- Files touched: `README.md`, `docs/execution/`, `docs/tasks/`,
  `src/crypt/execution/`, `tests/execution/`, `CHANGELOG.md`.

---

## 2026-06-27 — Core4 monthly distribution research pass

- Exact-tested Core4 v4 monthly-profit sweep variants focused on drawdown and
  monthly distribution: DSS bar-range cap, DSS reduced-risk branches, daily
  loss limits, low-risk NR7 addition, and margin caps.
- Found no dominant replacement for v4. The best money baseline remains
  $43,271 total account on $10k with -14.57% DD; the best checked DD cut was
  DSS half-risk at $38,459 and -11.64% DD.
- Rejected low-risk NR7 addition because it worsened DD to -18.75%.
- Recorded that `max_positions` must not be used as a research/control lever
  for this project.
- Scanned strategy-search artifacts for sparse high-WR donor ideas. Local
  post-2026-06-19 Stage 1 gate-fix artifacts contain only 2023 specialist
  traces, not balanced exports; older v3 discovery sparse seeds were recorded
  as rerun candidates, not portfolio-ready strategies.
- Inspected the owner-run sparse donor Stage 1 matrix on the ADR-0046 train
  window (`2022-01-01` → `2024-01-01`). Out of 10,000 generated candidates,
  only two rare Stage 1 candidates exported: a 17-signal VWAP reclaim and a
  16-signal short-only SMC premium/discount reversal.
- After the two strict Stage 1 exports failed exact validation, mined the
  `weak_barrier_win_rate` near-miss layer and generated 15 replayable sparse
  shortlist JSONs under
  `results/sparse_donor_stage1_train_2022_2023_v2/weak_barrier_shortlist/`.
- Began Core v4 live-execution parity migration. Live execution now loads
  strategy configs through the backtester registry, defaults to the selected
  Core v4 config, supports multi-signal `signal_events`, requires a current H1
  next-open price instead of using signal-close as an entry proxy, stores
  donor/event metadata in state schema v2, and blocks new entries on full OKX
  exchange-sync mismatches.
- Added normalized exchange snapshot/reconciliation models and tests for
  orphan exchange positions/orders, missing exchange positions, multi-event
  signal extraction, same-bar multi-event executor handling, and event-level
  risk overrides.
- Added synthetic live-vs-`ExecutionSim` parity coverage for same-bar
  `signal_events`, including entry time, next-open entry price, side, SL, TP,
  size, risk base, donor id, and TTL.
- Fixed live sync ordering so a local position that has disappeared from OKX is
  marked closed and sync status is recomputed before deciding whether new
  entries can be opened in that H1 tick.
- Extended TTL cleanup to cancel OKX pending algo SL/TP orders through the
  ccxt-exposed OKX raw cancel-algos endpoint when available.
- Added live close classification from recent OKX fills: closed positions now
  persist exit time, exit price, exit reason, estimated realized PnL, and exit
  fee when a matching fill is available.
- Updated `.env.example`, README, and the live execution spec for Core v4
  defaults, `EXECUTION_STATE_PATH`, `EXECUTION_RISK_PERCENT`,
  `EXECUTION_MAX_POSITIONS=0`, and mandatory exchange sync.
- Aligned live fallback execution defaults with Core v4 `backtest_args`
  (`exit_geometry=sl_rrr`, `risk_percent=1.0`, `rrr=2.0`, `ttl=0`) and fixed
  live TTL handling so `ttl_bars=0` disables TTL as in `ExecutionSim`.
- Added ADR-0048 for Core v4 live execution parity and full exchange sync.
- Added `reports/core4_investor_report.html`, a plain-language Tailwind report
  for an investor/friend with Core4 regime summaries, yearly/monthly tables,
  $1k/$10k/$30k scaling, and a changelog-derived story of what worked and what
  was rejected.
- Validation: `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q` (40 tests),
  `ruff check src/crypt/execution tests/execution`, and
  `mypy src/crypt/execution` passed.
- ADRs touched: ADR-0048.
- Files touched: `.env.example`, `README.md`, `strategies/archive/`,
  `docs/execution/`, `docs/decisions/`, `docs/tasks/`, `src/backtester/`,
  `src/crypt/execution/`, `tests/execution/`, `reports/`, `CHANGELOG.md`.

---

## 2026-06-26 — Monthly profit sweep backtest mode

- Added `--capital-sweep monthly_profit` to `backtester run`. At each month
  boundary, realized trading capital above the configured initial capital is
  moved into banked profit; losing months are not topped up.
- Added sweep audit columns to `trades.csv`: `capital_sweep_amount`,
  `banked_profit_after`, and `trading_capital_after_sweep`.
- Updated result metrics and console output to report `Banked Profit` and
  `Total Account` when sweep mode withdraws money.
- Added `Withdrawn ($)` to the monthly console table so each month shows the
  dollars withdrawn that month, not the cumulative bank.
- Added regression tests for monthly sweep execution and banked-profit result
  accounting.
- Validation: targeted pytest passed; targeted ruff `F,I` passed.
- ADRs touched: none.
- Files touched: `src/backtester/`, `tests/backtester/`, `README.md`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-26 — Island short-only exact filter branch

- Added DSS replay controls: `allowed_signal` for long-only/short-only exact
  replay and `entry_skip_rules` for entry-known next-bar filters
  (`entry_dayofweek`, `stop_distance_pct`).
- Added tests for DSS side filtering and entry skip rules; targeted pytest,
  ruff, and mypy passed.
- Exact-tested Island short-only variants on SOL 2022-12-18 → 2026-06-10.
  The original Island run made +$50,599 on $10k with 7.32 trades/week and
  -23.91% recalculated equity drawdown.
- Best current money branch
  `island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1` made +$72,602 on
  $10k, kept 3.40 trades/week, and recalculated drawdown was -16.35%.
- Lower-risk checked branch
  `island_short_r1p35_rrr0p75_ttl32_weekend_stop_filter_v1` made +$65,227 on
  $10k, kept 3.40 trades/week, and recalculated drawdown was -15.62%.
- Marked
  `island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1` as the selected
  Island research branch in the archived candidate README.
- Scanned 259 `results/**/trades.csv` artifacts for the opposite profile
  (profitable longs, losing shorts). No strong full-period mirror of Island was
  found; only two aggregated strategy groups matched the sign pattern, both
  weak in dollars.
- Recorded the Island follow-up in the archived candidate README and task
  files. The branch remains research/archive, not promoted: drawdown is still
  above the 10% mandate and 2025 monthly floor coverage is weak.
- ADRs touched: none.
- Files touched: `src/backtester/strategies/`, `tests/backtester/`,
  `strategies/archive/`, `docs/archive/`, `docs/tasks/`, `README.md`,
  `CHANGELOG.md`.

---

## 2026-06-26 — SMAC long-only branch and Island/SMAC portfolio check

- Split archived SMAC into long-only and short-only exact DSS replays. Baseline
  full-period SMAC made +$14,133 on $10k with 5.56 trades/week and -17.70%
  recalculated drawdown; long-only made +$9,106 with 2.61 trades/week and
  -14.31% drawdown; short-only made only +$2,609 with -27.33% drawdown.
- Ran a SMAC long risk/RRR/TTL grid. Selected
  `smac_long_r0p95_rrr1p25_ttl64_v1`: +$10,377 on $10k, 471 trades,
  2.61 trades/week, and -14.59% recalculated drawdown.
- Negative-oracle research found wide-stop skip rules for SMAC long, but exact
  replay cut frequency to 1.1-1.4 trades/week, below the owner minimum, so no
  extra SMAC filter was selected.
- Fixed `filtered_donor_portfolio` to apply nested DSS `allowed_signal` and
  `entry_skip_rules` before emitting multi-signal events.
- Fixed multi-signal trailing parity: `ExecutionSim.run()` now detects
  `trail_activation_rrr` inside `signal_events` and enriches the frame with
  closed ATR just like scalar-signal runs.
- Confirmed one-strategy portfolio parity for selected Island and selected
  SMAC: trades, PnL, exits, and recalculated drawdown match standalone runs
  exactly.
- Exact-tested `island_short_smac_long_portfolio_v1` after the trailing fix:
  $10k → $168,657 (+$158,657), 1,087 trades, about 6.00 trades/week, and
  -16.98% recalculated drawdown.
- Re-ran every archived `filtered_donor_portfolio` config after the
  multi-signal trailing fix under `results/multisignal_rerun_after_trailing_fix/`.
  All pre-fix multi-signal money results should be treated as invalid.
  `causal_v1` now fails closed because it references unavailable fast-path
  fields. `causal_v2_deployable` becomes +$138,222 but with -55.61% drawdown.
  `causal_v3_core4` becomes +$656,185 with -22.42% drawdown. The selected
  Island+SMAC branch remains +$158,657 with -16.98% drawdown.
- Ran a core4 drawdown frontier. Selected
  `filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85`: $10k
  → $216,978 (+$206,978), 2,298 trades, 12.69 trades/week, and -14.91%
  recalculated drawdown. It removes Island longs and scales nested risk to
  85% of the v3 core4 configs.
- Validation: targeted ruff, mypy, execution-sim tests, and DSS tests passed.
- ADRs touched: none.
- Files touched: `src/backtester/`, `tests/backtester/`,
  `strategies/archive/`, `docs/archive/`, `CHANGELOG.md`.

---

## 2026-06-26 — Anti-overfit trade filter research

- Added `backtester negative-oracle-research`: it searches entry-known skip
  rules that identify repeatable losing trade clusters and reports how many
  dollars each rule would save/cut in train, validation, and stress.
- Ran negative-oracle research on
  `results/filtered_donor_portfolio_causal_v2_deployable_full/20260626_163108`:
  1,066 rules tested; best robust skip rule saved only +$315 validation and
  +$1,487 stress, so the current donor portfolio has no strong obvious
  entry-known "mine" filter.
- Invalidated `filtered_donor_portfolio_causal_v1` exact results: the fast
  portfolio signal path did not expose `confidence` or
  `strength_smc_structure`, so NR4 and NR7 filters silently rejected all events.
- Hardened `filtered_donor_portfolio` so unavailable filter features fail early
  with a clear error instead of producing incomplete portfolio results.
- Fixed portfolio `catalog_*` filters to use previous closed candles, matching
  `trade-filter-research` and avoiding current-candle leakage.
- Added deployable
  `strategies/archive/filtered_donor_portfolio_causal_v2_deployable.json`,
  replacing non-fast-path `confidence`/`strength_*` filters with entry-time and
  previous-closed-candle catalog filters.
- Signal-only diagnostics for v2 produced 3,787 pre-execution events across all
  six donors; the next exact result must come from normal owner-run backtest.
- Added ADR-0047 and `docs/multi_signal_execution.md`.
- Added backward-compatible `signal_events` support to `ExecutionSim` and
  `Backtester`: legacy scalar `signal` rows still work, while multi-signal rows
  update exits once per OHLCV bar and then process all same-bar entry events
  through shared capital/margin.
- Added `filtered_donor_portfolio` strategy and archived
  `strategies/archive/filtered_donor_portfolio_causal_v1.json`, using the
  causal donor filters selected from
  `results/trade_filter_research_donors_2022_2026_causal/`.
- Materialized donor exact backtest and causal filter research artifacts under
  `results/research_archive/` as physical copies, not hardlinks.
- Fixed archived `crypt_ensemble` donor configs so long owner-run donor
  backtests keep progress bars enabled; added a guard test that fails on
  `strategies/archive/*.json` with `params.progress=false`.
- Fixed catalog-feature trade filtering to use strictly previous OHLCV candles
  on exact `open_time` joins, preventing current-candle leakage.
- Ran causal donor-level filter research after owner completed parallel donor
  backtests. All six donors produced at least one robust-forward CSV filter;
  results are archived under
  `results/trade_filter_research_donors_2022_2026_causal/`.
- Measured donor entry overlap: 1,320 of 6,210 standalone donor trades share an
  entry timestamp with another strategy, so exact "release all passing
  strategies" needs multi-signal execution rather than the current one-row
  strategy contract.
- Added two-rule conjunctions, `--group-by`, `--include-catalog-features`, and
  `--ohlcv` to `backtester trade-filter-research`.
- Grouped filter searches now support per-strategy screens such as
  `--group-by selected_strategy`; the grouping column is excluded from rule
  features to avoid trivial constant rules.
- Catalog-style candle features are computed from OHLCV and joined at
  `entry_time` using backward-only alignment. Supported run `ohlcv.csv` files
  with `open_time`.
- Smoke-tested grouped filtering on `router_v2_3997501`: zero robust-forward
  passes. The routed artifact had train trades only for one donor, so the next
  valid research step is owner-run full-period donor backtests.
- Smoke-tested catalog-feature loading on the same artifact with a capped rule
  search: `catalog_bb_squeeze == 'False'` did not pass, but OHLCV feature
  attachment and progress output worked.
- Added the agent autonomy / short self-run policy to `AGENTS.md`: agents keep
  working until owner-run scope, interruption, unknown next step, or a real
  owner choice; short progress/ETA commands under roughly two minutes may be
  run by agents.
- Hardened `trade-filter-research`: portfolio-state fields are excluded by
  default, optional through `--include-portfolio-state-features`, and every
  candidate now reports validation/stress deltas versus baseline plus
  `robust_forward_pass` and `robust_forward_score`.
- Re-ranked `top_filters.csv` by robust forward score instead of raw validation
  score.
- Re-ran all six full-period router artifacts with default market-entry
  features: no top-50 single-rule filter passed robust-forward guards.
- Re-ran all six with portfolio-state features enabled as a risk-allocator
  diagnostic: only `router_v2_3213199` had one weak formal pass,
  `size >= 39.10903047699838`, improving validation return by +4.08pp and
  stress return by +2.46pp while leaving stress floor-month count unchanged.
- Added a backlog follow-up for compound filters / meta-labeling.
- Added ADR-0046: all trainable research entities default to train
  2022-2024, validation 2024-2025, stress 2025-latest.
- Added `docs/trade_filter_research.md` for entry-known `take`/`skip` filter
  research over existing `trades.csv` artifacts.
- Added `backtester trade-filter-research`, which generates single-rule
  numeric/categorical filters from train only, blocks outcome leakage fields,
  ranks train-discovered rules by validation score, and reports stress metrics.
- The command writes `baseline_by_split.csv`, `filter_candidates.csv`,
  `top_filters.csv`, and `report.md`, with a visible progress bar for rule
  evaluation.
- Smoke-tested on `router_v2_3997501` full-period exact trades: 282 candidate
  rules evaluated; best validation-ranked research rule was
  `size <= 316.00902786872854` with train +26.74%, validation +121.16%, stress
  +134.03% in CSV-deletion approximation.
- Deferred the execution-grade router oracle to P2 and moved active work to
  trade-filter research.
- Validation: targeted trade-filter tests, execution multi-signal tests,
  archive-progress tests, ruff, and mypy passed for the changed paths.
- ADRs touched: ADR-0046, ADR-0047.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`, `README.md`,
  `CHANGELOG.md`.

---

## 2026-06-25 — Promoted router external-backtester boundary fix

- Removed all nested backtests from `promoted_router`; the external backtester
  now remains the only portfolio simulator.
- Promoted routers privately consume persisted rolling-label/model state,
  build a causal selection timeline, prepare nested signal streams through a
  strategy-class registry, and return one composite strategy frame. The
  external backtester remains unaware of router files and internals.
- Missing persisted router state now fails immediately instead of triggering
  hours of hidden donor reconstruction.
- Restored the six archived strategy trade exports from the repository-root
  handoff and rebuilt the required PineScript-aware rolling-label state:
  1,341 rows, 37 router features, six strategies.
- Restored the selected `crypt_ensemble` candle progress display for
  interactive composite runs without reintroducing nested backtests.
- Added ADR-0044 and the shared incremental-router runtime contract.
- Replaced portfolio-member branching with a strategy-class adapter registry;
  one parameterized contract suite automatically covers every config in
  `strategy_paths`.
- Added generic shadow portfolios and parity tests against the unchanged
  external `ExecutionSim`; removed accidental shadow execution from the final
  selected-signal multiplex pass.
- Fixed promoted-router reproducibility: `validation_start=2024-01-01` is now
  frozen in the router config. Starting the hold/switch state machine at the
  first label row had changed the 2025 timeline from the archived
  +125.04%/359-trade replay to +103.18%/361 trades.
- Added one parameterized adapter-to-canonical parity test over every
  `strategy_paths` member; no portfolio strategy ids are hard-coded.
- Replaced mass router ranking with robust oracle-regret scoring and added
  oracle gap, capture ratio, hit-rate, p90, and worst-regret diagnostics.
- Added `router_shortlist.csv` and `router-validate-shortlist` for staged
  continuous shared-capital screening before exact composite OHLCV backtests.
- Added mandatory router-search progress bars with candidate counts, elapsed
  time, rate, and ETA; documented project-wide long-run progress requirements
  and owner-run PID invisibility across agent sandbox namespaces in `AGENTS.md`.
- Fixed `router-search-matrix` progress visibility: child stderr is inherited
  by the owner terminal and each algorithm receives a dedicated tqdm position;
  normal child output remains in `run.log`.
- Consumed the completed four-algorithm oracle-regret matrix: 4,000 shortlist
  rows collapsed to 813 unique train selection timelines, then frozen
  2024-2025 predictions were generated for routed holdout validation.
- Consumed routed 2025 validation for all 813 timelines: every candidate was
  `discard`; 69 respected the 10% monthly drawdown ceiling, and the existing
  `router_v2_2687609` still had the most +15% floor months among them (4/12).
- Froze five new risk/return-front router configs under
  `strategies/router_shortlist/` for final exact OHLCV composite verification,
  with `router_v2_2687609` retained as the control.
- Consumed exact OHLCV runs for all six finalists on 2025 and 2022-2026. The
  best 2025 candidate, `router_v2_3997501`, returned +157.93% with -6.22%
  mandate DD but passed only 4/12 monthly floors; every finalist is `discard`.
- Verified full-run/standalone parity: five routers have identical 2025 trade
  sequences, while `router_v2_3213199` has two additional first-day trades
  only when pre-2025 warm-up candles are available.
- Added ADR-0045.
- Corrected the promoted-router spec, archive notes, README, and active task.
- Validation: 37 focused promoted-router/router/execution tests passed and
  ruff clean. Targeted mypy is clean for the promoted runtime; the older
  router/CLI modules retain pre-existing strict typing findings.
- ADRs touched: ADR-0043, ADR-0044, ADR-0045.
- Files touched: `src/backtester/`, `tests/backtester/`, `strategies/archive/`,
  `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-24 — Router search algorithm matrix

- Added Router Catalog v2 backends: uniform `random`, balanced `island_qd`,
  successive-filtering `hyperband_qd`, and random-forest-surrogate `smac_qd`.
- Added deterministic `--seed` and `--proposal-multiplier` controls.
- Added `backtester router-search-matrix` to launch the four stochastic
  searches concurrently with isolated outputs and logs.
- Validation: 14 focused router/label tests passed, ruff clean, and all four
  algorithms completed a real-label matrix smoke.
- Consumed the owner-run 100k matrix and archived two distinct frontier
  routers: `router_v2_4252951` (+425.17% median, -6.11% worst offset DD) and
  `router_v2_3216811` (+310.56% median, +281.26% minimum, -3.80% worst DD).
- Added `backtester router-validate` for continuous shared-capital replay of
  archived trades with margin gates and drain-before-switch handoffs.
- Added ADR-0042: routers select exactly one strategy and never select cash or
  split capital.
- Added `promoted_router` and promoted `router_v2_2687609` as a normal strategy
  containing all six archived strategies.
- Extended the generic signal contract with per-signal TTL, trailing, exit
  geometry, and position-group drain controls so nested strategies retain
  their own execution settings under the standard `ExecutionSim`.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`, `README.md`,
  `strategies/backtester/`, `routers/archive/`, `CHANGELOG.md`.

---

## 2026-06-23 — Single-strategy router search MVP

- Added PineScript-derived `router_ps_*` market-state features to rolling
  regime labels, reusing native Python feature implementations from the local
  PineScript catalog.
- Added `backtester router-search` for single-strategy router candidates with
  offset-robust utility scoring; routers always choose one strategy and never
  split capital across strategies.
- Restored the regime router handoff artifact and rebuilt fresh
  PineScript-aware rolling labels under
  `results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/`.
- Optimized router search with NumPy return/feature matrices and vectorized
  non-overlap offset selection; a 20-config PineScript-aware smoke dropped from
  roughly 50 seconds to roughly 11 seconds.
- Completed the full 2000-config router search. Best selector:
  `router_001190` (`rolling_median`, 120d lookback, 3-point switch margin),
  median offset return +258.13%, minimum offset return +186.37%, worst DD
  -17.34%.
- Archived that selector as
  `rolling_median_120d_switch_margin_3` under `docs/archive/routers/` and
  `routers/archive/`; added `--config-offset` for owner-run continuation of the
  remaining 5040 catalog configs in bounded chunks.
- Consumed all remaining chunks and completed the 7040-config v1 catalog.
  Archived the best distinct risk-qualified family as
  `pinescript_same_state_mean_dd_120d_hold30_margin1` (+192.80% median offset
  return, -6.52% worst DD).
- Added Router Catalog v2 with 4,640,400 deterministic combinations covering
  expanded score families, PineScript state subsets, exact/similarity matching,
  weighted state profiles, EWM recency, sample gates, holds, and switch
  margins.
- Added memory-safe `--summary-only`, `--catalog-version`, `--top-predictions`,
  and `--count-only`; benchmarked 500 v2 configs at about 92 seconds / 303 MB.
- Validation: focused regime router/label tests passed; ruff clean on touched
  files.
- Files touched: `src/backtester/regime_router.py`,
  `src/backtester/regime_labels.py`,
  `src/backtester/strategy_discovery/features.py`, `src/backtester/__main__.py`,
  `tests/backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-23 — Archived matrix parallel jobs

- Added `--jobs N` to `backtester archived-performance-matrix` for
  process-level strategy parallelism (default serial).
- Matrix orchestration moved into `run_archived_performance_matrix`; partial
  checkpoint writes still happen after each completed strategy.
- Validation: focused regime matrix tests passed; ruff clean on touched files.
- Files touched: `src/backtester/regime_matrix.py`, `src/backtester/__main__.py`,
  `tests/backtester/test_regime_matrix.py`, `docs/regime_performance_matrix.md`,
  `README.md`, `docs/tasks/IN_PROGRESS.md`, `CHANGELOG.md`.

---

## 2026-06-23 — Full rolling router benchmark

- Consumed the completed
  `results/regime_matrix_archive_sol_2022_2025_trades/` archive matrix with six
  raw `strategy_trades/*.csv` files.
- Generated full daily 30-day rolling labels where every row has all six
  archived strategies available.
- Evaluated router baselines and KNN/lookback sensitivity; documented that
  oracle is very strong but current simple routers are not robust enough.
- Updated next work to utility-scored, offset-robust router evaluation.
- Files touched: `docs/`, `CHANGELOG.md`.

---

## 2026-06-23 — Archive matrix parameter guard

- Verified that archive matrix runs resolve strategy execution params from
  `strategies/archive/*.json` `backtest_args`.
- Added regression coverage for `backtest_args` precedence over legacy DSS flat
  params and for all current archived strategy effective matrix args.
- Validation: focused regime matrix/label/router tests passed; ruff clean on
  touched files.
- Files touched: `tests/backtester/test_regime_matrix.py`, `docs/`,
  `CHANGELOG.md`.

---

## 2026-06-23 — Rolling router baseline evaluator

- Added `backtester rolling-router-baseline` and
  `src/backtester/regime_router.py` for live-safe router scoring over rolling
  label CSVs.
- Router training now uses only completed prior label windows
  (`label_end <= asof`) and reports dense forward-label scores plus non-overlap
  portfolio-style scores.
- Fixed strategy-return column detection so `return_dispersion_pct` is not
  treated as a pseudo-strategy.
- Evaluated the partial exact-artifact rolling labels and documented why a
  full six-strategy raw-trade matrix rerun is the next label-grade step.
- Validation: focused regime router/label tests passed; ruff clean on touched
  files.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`, `README.md`,
  `CHANGELOG.md`.

---

## 2026-06-23 — Partial rolling labels from exact trade artifacts

- Added optional rolling-label coverage masking via `strategy_coverage.csv` so
  partial trade datasets do not treat missing strategy years as 0% return.
- Assembled
  `results/regime_matrix_archive_partial_existing_trades_2022_2025/` from
  existing exact-parameter raw trade artifacts and generated daily 30-day
  rolling labels.
- Result: 1341 rows; 977 rows have 4 available strategies, 335 rows have 3,
  and 29 boundary rows have 1.
- Validation: focused regime label/matrix tests passed; ruff clean on touched
  files.
- Files touched: `src/backtester/regime_labels.py`,
  `tests/backtester/test_regime_labels.py`, `docs/`, `CHANGELOG.md`.

---

## 2026-06-23 — Rolling regime label infrastructure

- `backtester archived-performance-matrix` now exports raw per-strategy trades
  under `strategy_trades/<strategy_id>.csv`.
- Added `backtester rolling-regime-labels` to build daily/hourly forward labels
  from raw trade exports with detector-safe OHLCV features at `T`.
- Documented the Plan B rerun commands and rolling label trade-inclusion rule.
- Validation: focused regime label/matrix tests passed; ruff clean on touched
  files.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`, `README.md`,
  `CHANGELOG.md`.

---

## 2026-06-23 — Monthly router baseline

- Evaluated first monthly portfolio routers over the archive-only oracle label
  dataset.
- Found `rolling_top2_mean_60_40` is the current simple benchmark to beat:
  +66.51% over 2024-2025 with -12.58% max drawdown.
- The OHLCV feature-KNN top-2 router reduced drawdown to -6.00% but returned
  only +42.09% and switched too often.
- Added `docs/regime_router_baseline.md` and updated next work to a
  risk-gated rolling top-2 router.
- Files touched: `docs/regime_router_baseline.md`, `docs/regime_detection.md`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-23 — Rolling label Plan B recorded

- Recorded that the current active path remains the monthly oracle-label
  dataset, while denser daily/hourly rolling labels are Plan B.
- Added the raw per-strategy trade export requirement for future
  `archived-performance-matrix` runs.
- Added a backlog item for `strategy_trades/<strategy_id>.csv` exports and
  rolling 7d/30d/90d label generation.
- Files touched: `docs/regime_label_analysis.md`,
  `docs/regime_performance_matrix.md`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-23 — Regime label analysis

- Analyzed the archive-only monthly oracle labels for feature separation,
  unstable low-margin labels, and walk-forward exact-strategy baselines.
- Found that exact single-strategy classification is not reliable yet: the best
  model ties rolling majority on 2024-2025 walk-forward exact accuracy.
- Added `docs/regime_label_analysis.md` and recorded the next step as a
  confidence-gated top-2 portfolio router, not a hard classifier.
- Files touched: `docs/regime_label_analysis.md`, `docs/regime_detection.md`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-23 — Oracle regime labels MVP

- Added `backtester oracle-regime-labels` to convert a completed archived
  performance matrix into monthly `best_strategy` oracle labels.
- Added detector-safe OHLCV features computed strictly before each bucket start.
- Generated the first label artifact under
  `results/regime_matrix_archive_sol_2022_2025/oracle_labels/`.
- Documented the command in README and the label contract in
  `docs/regime_detection.md`.
- Validation: focused regime label/matrix tests passed; ruff clean on touched
  files.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-22 — NR4 VWAP robust archived

- Archived NR4 VWAP robust as `nr4_vwap_robust` after the owner-run
  execution-only Optuna completed.
- Frozen best trial 412 execution params:
  `tp_move_pct=0.026`, `rrr=1.75`, `ttl=52`, `risk_percent=0.5`,
  `trail_activation_rrr=1.75`, `trail_distance_atr=0.25`.
- Updated the archive index and regime matrix notes so the next matrix can be
  archive-only instead of archive+active.
- Files touched: `strategies/archive/`, `docs/archive/candidates/`,
  `docs/regime_performance_matrix.md`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-22 — NR4 archive-before-final-matrix plan

- Documented that label-grade regime matrices should use archived strategy
  columns only; active `--strategy` inputs are exploratory until archived.
- Added the NR4 big Optuna → archive → second matrix sequence to
  `docs/tasks/IN_PROGRESS.md`.
- Clarified in the regime detection docs that archive provenance is required
  before using strategy columns for label training or router evaluation.
- Files touched: `docs/regime_detection.md`,
  `docs/regime_performance_matrix.md`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-22 — Regime matrix progress control

- Added `--strategy-progress/--no-strategy-progress` to
  `backtester archived-performance-matrix`.
- Matrix runs now announce each strategy before starting it and keep
  strategy-level progress bars enabled by default when supported.
- Validation: regime matrix tests passed; ruff clean on touched CLI/test files.
- Files touched: `src/backtester/__main__.py`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-22 — Regime matrix archive replay fixes

- Fixed stale execution params in archived NR7 and VWAP strategy JSONs so they
  match their archived `execution_params.json` files.
- Matrix runs now force strategy-level `progress=false` to avoid nested
  strategy progress bars.
- `backtester archived-performance-matrix` now rewrites partial matrix outputs
  after each completed strategy, so an interrupted run preserves completed
  rows.
- Validation: regime matrix tests passed; ruff clean on touched matrix files.
- Files touched: `src/backtester/__main__.py`, `strategies/archive/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-22 — Archived strategy performance matrix MVP

- Added `docs/regime_performance_matrix.md` as the contract for the first
  `time x strategy metrics` artifact used by regime discovery.
- Added `backtester archived-performance-matrix` to run archived and selected
  active strategies on one shared window and export bucket-level matrix CSVs.
- Added matrix aggregation utilities and tests for manifest, bucket metrics,
  pivots, and CLI help.
- Documented the owner-run SOL 2022-2025 archive+active matrix command in
  README.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-22 — Archived WR45 Optuna research seeds

- Archived `smac_003335_double_bottom_body_to_range` and
  `island_2023_021396_engulfing_bb_trend` as `research_seed` DSS candidates.
- Frozen each strategy under `strategies/archive/` with best Optuna execution
  parameters from the owner's completed runs.
- Added archive README, execution params, provenance, mandate snapshot, and
  monthly return CSVs for both candidates.
- Both entries explicitly keep `mandate_verdict=discard`; the archive value is
  regime/detector evidence, not production promotion.
- Files touched: `docs/archive/candidates/`, `strategies/archive/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-19 — Stage 1 WR gate uses only configured threshold

- Removed the hidden `tp_first > sl_first` requirement from DSS Stage 1
  `weak_barrier_win_rate` gating.
- `--stage1-min-wr` / `DSSConfig.min_barrier_win_rate` is now the only Stage 1
  win-rate gate; signal-count, TP-first-rate, and overtrading gates are
  unchanged.
- Updated the DSS v2 spec and added regression coverage for a WR45 candidate
  with fewer TP-first outcomes than SL-first outcomes.
- Validation: `tests/backtester/test_dss.py` passed; ruff clean on touched
  Stage 1/test files.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-19 — Stage 1 WR threshold CLI flag

- Added `--stage1-min-wr` to `backtester search-signals` and
  `backtester search-signals-matrix`.
- The flag feeds `DSSConfig.min_barrier_win_rate` without changing Stage 1
  signal-count, TP-first, or overtrading gates.
- Validation: DSS tests passed; ruff clean on the touched CLI/test files; both
  command help outputs show the new flag.
- Files touched: `src/backtester/__main__.py`, `README.md`, `docs/tasks/`,
  `CHANGELOG.md`.

---

## 2026-06-19 — Full PineScript SMC/ICT DSS catalog slice

- Completed the remaining PineScript-derived DSS catalog transfer from
  `pinescript/smc.pine`.
- Added native OHLCV-safe SMC features for internal/swing BOS/CHoCH, fair-value
  gaps, equal highs/lows, premium/discount zones, and active order-block zones.
- Added five SMC triggers: `pt_ps_smc_structure_break`, `pt_ps_smc_fvg`,
  `pt_ps_smc_equal_sweep`, `pt_ps_smc_premium_discount_reversal`, and
  `pt_ps_smc_order_block_retest`.
- Added five SMC filters: `pf_ps_smc_bias`, `pf_ps_smc_fvg_recent`,
  `pf_ps_smc_premium_discount`, `pf_ps_smc_equal_level_recent`, and
  `pf_ps_smc_order_block_active`.
- Updated `docs/discovery/pinescript_catalog_v1.md` and removed the completed
  SMC/ICT catalog backlog item.
- Validation: `tests/backtester/test_dss.py` passed; ruff clean and mypy clean
  on touched PineScript catalog/features/tests.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-19 — DSS matrix launch command

- Added `backtester search-signals-matrix` to launch `staged`, `catcma_qd`,
  `island_qd`, `hyperband_qd`, and `smac_qd` concurrently with one command.
- The wrapper creates per-algorithm output directories, writes child
  `run.log` files, uses the standard DSS seeds, and exits non-zero if any
  child search fails.
- Documented the command in README and added CLI tests for help and unknown
  algorithm validation.
- Files touched: `src/backtester/__main__.py`, `tests/backtester/`,
  `README.md`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-19 — Regime detection roadmap and archive policy

- Converted owner notes from `test.md` into `docs/regime_detection.md`.
- Added ADR-0041: regimes will be discovered from archived strategy behavior,
  with separate offline Labeler, online Detector, and Portfolio Router.
- Updated the candidate archive contract so useful non-mandate strategies can
  be kept as `regime_seed` or `research_seed` for future detector training.
- Added backlog tasks for the archived-strategy performance matrix, offline
  Regime Discovery/Labeler, rule-based online Detector, Portfolio Router
  utility scoring, and later non-OHLCV detector features.
- Updated README with the regime-aware routing research direction.
- Removed the temporary `test.md` handoff file after converting it.
- Files touched: `docs/regime_detection.md`, `docs/decisions/`,
  `docs/backtester/`, `docs/archive/candidates/`, `docs/tasks/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-19 — DSS manual replay uses flat execution params

- Fixed `backtester run` replay for DSS candidate JSONs that carry execution
  fields in flat `params` but no `backtest_args`; `risk_percent`, `rrr`,
  `trail_distance_atr`, and `position_ttl_bars` now become backtest defaults.
- Kept `backtest_args` as the highest-precedence strategy-file override.
- Added regression coverage for flat DSS params and `backtest_args` precedence.
- Validation: `tests/backtester/test_optimizer.py` passed; direct
  `build_backtest_args` check on the owner's WR46.85 JSON returns the expected
  Optuna execution values. Full ruff/mypy on the touched files still report
  pre-existing unrelated issues in those files.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/tasks/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-18 — Archived dssv2_013321 near-miss

- Archived `dssv2_013321_ps_macd_squeeze_recent` as a PineScript-derived
  near-miss after owner review.
- Added mandate snapshot, monthly mandate CSV, execution params, and
  provenance under `docs/archive/candidates/dssv2_013321_macd_squeeze_recent/`.
- Added frozen runnable strategy copy under
  `strategies/archive/dssv2_013321_ps_macd_squeeze_recent.json`.
- Files touched: `docs/archive/candidates/`, `strategies/archive/`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-18 — DSS Stage 1 ATR-scaled directional label

- Replaced DSS Stage 1 candidate-geometry labeling with a volatility-normalized
  directional label: next-open entry, closed-candle ATR14, SOL reference
  calibration of 0.7% favorable TP and 0.4% adverse SL, and conservative
  SL-first handling when both barriers touch in one candle.
- Stage 1 ATR is only a symbol volatility scale; candidate `rrr`, `risk_percent`,
  `atr_sl_mult`, structural stops, TTL, fees, sizing, and execution overlap are
  still excluded from Stage 1.
- Unresolved end-of-window tails are now reported as `unresolved_tail` and
  excluded from `barrier_win_rate`; the minimum signal gate uses resolved
  TP/SL outcomes.
- Added `stage1_tp_move_pct`, `stage1_sl_move_pct`, and
  `stage1_reference_atr_pct` config/state fields plus new CSV columns for
  `barrier_unresolved_tail_rate_*`, `barrier_median_mae_pct_*`, and
  `barrier_median_mfe_pct_*`.
- Removed Stage 1 advisory-score dependence on stop distance; CatCMA-QD now
  uses the shared Stage 1 advisory scorer.
- Validation: `tests/backtester/test_dss.py` 67/67 passed; ruff and mypy clean
  on touched DSS modules/tests.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-17 — Unified DSS Stage 1 contract

- Split DSS Stage 1 signal viability into `dss_stage1.py` and kept
  `dss_v2.py` as the staged runner/artifact surface.
- Added `Stage1Result.should_promote` and `advisory_score`; DSS backends now
  use the stage result as the single pass/fail contract before Stage 2.
- Made `--stage-mode stage1` apply to all `search-signals` algorithms:
  `staged`, `catcma_qd`, `island_qd`, `hyperband_qd`, and `smac_qd`.
- Added `stage1_near_misses.csv` so rejected/specialist candidates remain
  ranked and inspectable after long Stage 1 runs.
- Documented `discover-strategies` as legacy for this contract; new search
  work should add `search-signals` backends instead.
- Validation: `tests/backtester/test_dss.py` 64/64 passed; ruff clean and
  mypy clean on touched DSS modules/tests.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-16 — PineScript-derived DSS catalog v1

- Added a separate `pinescript_v1` DSS trigger/filter catalog derived from the
  local PineScript idea set under `pinescript/`.
- Added closed-candle discovery features for Supertrend, UT Bot-style ATR
  trail, squeeze release, WaveTrend, MACD, ADX/DI, Williams Vix Fix,
  pivot/volume breaks, simple trendline breaks, and killzone sessions.
- Added `backtester search-signals --catalog legacy|pinescript_v1|all`; default
  remains `legacy`, while the active next owner run uses only
  `--catalog pinescript_v1`.
- Added `--stage-mode stage1` for Stage 1-only catalog discovery: the run
  stops before backtests, writes `stage1_ranked.csv`, and exports research
  configs under `stage1_candidates/`.
- Added `--min-signals-per-week`; the PineScript handoff now uses 4 signals per
  week, so 20 signals/year no longer passes Stage 1 on full-year windows.
- Changed execution tuning so trailing activation is derived from the selected
  `rrr` whenever `trail_distance_atr > 0`; user-facing backtest/diagnostic
  CLIs no longer expose separate `--trail-activation-rrr*` flags.
- Enforced optimizer/backtest policy: `max_positions` is fixed to `0` across
  user-facing CLIs and internal best-run export, and optimizer targets are
  locked to `mandate_score`.
- Fixed strategy `backtest_args` compatibility: `position_ttl_bars` is now
  accepted as an alias for runner `ttl`, so DSS/Optuna candidate JSONs override
  the CLI `--ttl` default correctly.
- Fixed replay of trailing-stop candidates: `BacktestArgs` now derives
  `trail_activation_rrr` from the final merged `rrr` whenever
  `trail_distance_atr > 0`, so `backtester run` matches Optuna best-run
  trailing behavior.
- Extended `SignalComposer` so PineScript-derived candidate JSONs replay
  through the normal DSS strategy/backtest path.
- Persisted the selected catalog in DSS state and documented the new catalog
  contract in `docs/discovery/pinescript_catalog_v1.md`.
- Updated README and task state so the next validation run searches the new
  PineScript catalog instead of repeating the legacy space.
- Validation: `tests/backtester/test_dss.py` 58/58 passed;
  `tests/backtester/test_optimizer.py` and
  `tests/backtester/test_fixed_candidate_report.py` 21/21 passed; ruff and
  mypy clean on touched optimizer/grid/walk-forward files.
- Files touched: `src/backtester/strategy_discovery/`, `src/backtester/__main__.py`,
  `tests/backtester/`, `docs/discovery/`, `docs/tasks/`, `README.md`,
  `CHANGELOG.md`.

---

## 2026-06-16 — DSS WR55/10pd tail analysis

- Analyzed owner-supplied `dss_wr55_10pd_searches_20260616_142549_tar.gz`
  without committing the raw `results/` artifacts.
- Confirmed the WR55/10pd failure is a 2022/2023 regime conflict: 31,241
  candidates passed 2022 in the completed 1.2M-trial run, none passed 2023;
  38 candidates passed 2023 in the 2023-first snapshots, all failed 2022 due to
  too few signals.
- Added `docs/discovery/dss_wr55_10pd_tail_analysis.md` and updated the DSS v2
  spec with `balanced` vs `specialist:<window>` candidate classes.
- Implemented DSS Stage 1 specialist artifacts:
  `candidate_class`, `target_window`, `stage1_specialists.csv`, and
  `stage1_specialists.jsonl`; only balanced candidates remain eligible for
  Stage 2/export.
- Restored the fast default Stage 1 early-reject path; specialist diagnostics
  require explicit `--specialist-windows` so normal all-window searches do not
  accidentally multiply runtime.
- Updated `summary.md` output to include Stage 1 specialist counts and updated
  task state so the next step is owner-run real-data validation.
- Validation: `tests/backtester/test_dss.py` 51/51 passed; ruff clean on
  touched Python files; mypy clean on touched DSS module/test.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-16 — Cross-machine DSS WR55 search handoff

- Added a markdown handoff for gitignored `results/` artifacts so agents on
  other PCs can understand the WR55/10pd DSS search state without local CSVs.
- Recorded the 2026-06-16 09:53 MSK snapshot: completed `seed60616` reached
  1.2M trials with 0 Stage 1 survivors and 0 exported candidates; active
  `seed60617`, `seed60618`, `2023first_seed60619`, and
  `2023first_seed60620` were still running with 0 survivors.
- Captured the main finding: the current constructor finds many 2022 WR55
  specialists and rare 2023 WR55 specialists, but no robust 2022/2023
  intersection so far.
- Added a backlog item to analyze the 2023-first tail and design the next
  regime-aware DSS search step before launching more identical seed runs.
- Files touched: `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-12 — DSS Stage 1 path-aware barrier label

- Added Stage 1 barrier metrics for DSS candidates: `tp_first`, `sl_first`,
  `timeout`, MAE/MFE in ATR, and bars-to-TP over the candidate TTL.
- Changed the Stage 1 overtrading guard from the old approximate
  `800 signals/year` cap to `10 signals/day`.
- Stage 1 now rejects candidates below a low `min_barrier_tp_first_rate`
  threshold, with same-bar TP+SL counted conservatively as SL-first.
- Tightened the barrier gate so Stage 1 also requires
  `barrier_win_rate >= 55%` and `tp_first > sl_first` per checked window.
- Fixed the Stage 1 barrier label to use the same next-open entry and resolved
  `sl_rrr` exit levels as Stage 2 donor execution; the first implementation
  used the trigger reference price and could over-credit signals that Stage 2
  would enter differently or reject after a gap.
- Added `barrier_*` columns to `stage1_viability.csv`.
- Included barrier quality in CatCMA/Hyperband/Island Stage 1 cheap ranking.
- Updated DSS v2 docs and active handoff to distinguish pre-barrier and
  post-barrier search artifacts.
- Validation: `tests/backtester/test_dss.py` passed; ruff and mypy clean
  on touched modules/tests.
- Files touched: `src/backtester/strategy_discovery/`, `tests/backtester/`,
  `docs/discovery/`, `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-12 — SMAC-QD random-forest DSS backend

- Added `backtester search-signals --algorithm smac_qd`, a SMAC-style
  conditional surrogate backend using `sklearn.ensemble.RandomForestRegressor`.
- SMAC-QD bootstraps random evaluations, encodes conditional trigger/filter
  spaces into fixed RF features, scores proposal pools with predicted mean plus
  tree-dispersion uncertainty, and evaluates selected infill candidates through
  DSS Stage 1/2/3.
- Added `smac_qd_proposals.csv`, `smac_qd_observations.csv`, and
  `smac_qd_state.csv` artifacts.
- Updated the active handoff to five search algorithms: `staged`, `catcma_qd`,
  `island_qd`, `hyperband_qd`, and `smac_qd`.
- Added ADR-0040 and updated README, DSS v2 docs, task state, mypy overrides,
  and DSS tests.
- Validation: `tests/backtester/test_dss.py` 44/44 passed; ruff and mypy clean
  on touched modules/tests; `search-signals --help` shows `smac_qd`.
- ADRs touched: ADR-0040.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `pyproject.toml`, `CHANGELOG.md`.

---

## 2026-06-12 — Hyperband-QD DSS backend

- Added `backtester search-signals --algorithm hyperband_qd`, an experimental
  successive-halving quality-diversity backend.
- Hyperband-QD runs Stage 1 viability for all generated candidates, then
  promotes behavior-diverse top fractions through one-window proxy,
  multi-window proxy, and full all-window Stage 3 scoring.
- Added `hyperband_rungs.csv` and `hyperband_qd_state.csv` artifacts while
  preserving normal DSS archive, manifest, and candidate JSON outputs.
- Added ADR-0039 and updated README, DSS v2 docs, task state, and DSS tests.
- Validation: `tests/backtester/test_dss.py` 41/41 passed; ruff and mypy clean
  on touched modules/tests.
- ADRs touched: ADR-0039.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-12 — DSS optimizer handoff for next agent

- Added a next-agent implementation plan for `--algorithm hyperband_qd` in
  `IN_PROGRESS.md`.
- Added backlog tasks for Hyperband-QD and a later SMAC-like conditional
  surrogate backend.
- Added an optimizer research shortlist to `IDEAS.md` covering Hyperband,
  SMAC-style search, full CatCMAwM, FuRBO, constrained TPE, and LLM-SAEA.
- Files touched: `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-12 — Island-QD DSS backend for Railway search

- Added `backtester search-signals --algorithm island_qd`, an experimental
  window-specialist quality-diversity backend for Railway-scale exploration.
- Island-QD rotates batches across configured windows, scores Stage 2 only on
  the target window, writes `island_scores.csv`, and periodically performs
  robust all-window checks.
- Changed `railway.toml` start command from live `crypt` alerts to the
  Island-QD Railway search worker, writing artifacts under `data/results/`.
- Added an active three-machine search matrix to `IN_PROGRESS.md` so future
  agents inspect work-PC staged DSS, home-PC CatCMA-QD, and Railway Island-QD
  outputs together.
- Added ADR-0038 and updated DSS docs, README, and task handoff with a Railway
  start command.
- Validation: `tests/backtester/test_dss.py` 39/39 passed; ruff and mypy clean
  on touched modules/tests.
- ADRs touched: ADR-0038.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-11 — CatCMA-QD experimental DSS backend

- Added opt-in `backtester search-signals --algorithm catcma_qd` with `--seed`
  for a non-duplicative home search while the work machine runs default DSS v2.
- Implemented `catcma_qd.py`: CatCMA-inspired mixed-variable weighted sampler,
  elite updates from DSS stage scores, shared Stage 1/2/3/4 evaluation, and
  `catcma_qd_state.csv` export.
- Capped CatCMA-QD Stage 2 proxy backtests per population batch after the first
  owner run showed 435 proxy evaluations in the first 591 candidates and an ETA
  above six days.
- Added ADR-0037 and updated the DSS v2 spec, README, task handoff, backlog,
  and DSS tests.
- Validation: `tests/backtester/test_dss.py` 38/38 passed; ruff clean on
  touched code/docs; mypy clean on touched modules and DSS tests.
- ADRs touched: ADR-0037.
- Files touched: `src/backtester/`, `tests/backtester/`, `docs/`,
  `README.md`, `CHANGELOG.md`.

---

## 2026-06-11 — DSS v2 quiet progress output

- Changed `backtester search-signals` to suppress internal INFO/WARNING logs
  during DSS v2 loading and staged scoring, so owner-scale runs show only the
  progress bar unless an error occurs.
- Added progress callback support in the DSS v2 runner and wired it to
  `click.progressbar`.
- Added regression coverage that progress ticks once per generated candidate.
- Validation: `tests/backtester/test_dss.py` 34/34 passed; ruff and mypy clean
  on touched files; 1-trial smoke emitted only the progress label/bar.
- Files touched: `src/backtester/__main__.py`,
  `src/backtester/strategy_discovery/dss_v2.py`,
  `tests/backtester/test_dss.py`, `CHANGELOG.md`.

---

## 2026-06-11 — DSS v2 state serialization fix

- Fixed `search-signals` crash on startup: `DSSWindowSpec` uses slots, so
  `state.json` writer can no longer rely on `__dict__`.
- Added regression test for serializing slotted window specs into DSS v2
  `state.json`.
- Validation: `tests/backtester/test_dss.py` 33/33 passed; ruff and mypy clean
  on touched files.
- Files touched: `src/backtester/strategy_discovery/dss_v2.py`,
  `tests/backtester/test_dss.py`, `CHANGELOG.md`.

---

## 2026-06-11 — DSS v2 staged quality-diversity implementation

- Replaced the operator-facing `backtester search-signals` path with DSS v2
  staged quality-diversity search; the retired Optuna sampler path is no longer
  exposed as a mode.
- Added `DSSCandidate`, behavior descriptors, `DSSArchive`, and `dss_v2.py`
  staged runner for Stage 0 generation, Stage 1 viability, Stage 2 proxy
  scoring, Stage 3 full mandate scoring, and Stage 4 candidate export.
- `search-signals --help` no longer shows `--sampler`, `--resume`,
  `--max-filters`, or `--accept-min-score`; passing removed flags fails with a
  DSS v2 message.
- DSS v2 artifacts now include `stage1_viability.csv`,
  `stage1_rejections.csv`, `stage2_proxy.csv`, `stage3_full_scores.csv`,
  `archive.json`, `archive.md`, `score_history.csv`,
  `candidate_manifest.*`, and replayable `candidates/*.json`.
- Tests added for candidate serialization, archive diversity/replacement,
  robust score dispersion, staged rejections, v1 resume guard, exported JSON
  replay via `DSSStrategy`, and CLI removed-option behavior.
- Validation: `ruff check` clean on touched files; `mypy` clean on touched
  modules; `tests/backtester/test_dss.py` 32/32 passed.
- ADRs touched: ADR-0036.
- Files touched: `src/backtester/`, `tests/backtester/`, `README.md`,
  `docs/tasks/`, `CHANGELOG.md`.

---

## 2026-06-11 — DSS v2 staged search spec

- Diagnosed `results/dss_sol_run_5k/study.journal`: about 16.5k completed
  trials, best robust `min(score)` **-4626.74**, no trial above `-500`, and
  elite collapse into `pt_ema_cross + rrr=4.0`.
- Added ADR-0036: replace DSS v1 NSGA-II with staged quality-diversity search.
- Added `docs/discovery/direct_signal_search_v2.md` as the implementation
  contract for rewriting `backtester search-signals` in place.
- Marked ADR-0035 and DSS v1 spec superseded.
- Updated task handoff so the next agent implements DSS v2 instead of running
  or tuning the retired sampler path.
- ADRs touched: ADR-0035, ADR-0036.
- Files touched: `docs/decisions/`, `docs/discovery/`, `docs/tasks/`,
  `CHANGELOG.md`.

---

## 2026-06-10 — DSS backtest fixes (structural_sl_mode + OHLCV columns)

**Problem 1:** `search-signals` scored `-5000` on all signal-bearing trials —
`structural_sl_mode="none"` rejected by `exit_geometry.py`.

**Problem 2:** after fix #1, `ExecutionSim` failed with
`Missing required columns: open, high, low, close` — `signal_df_to_ohlcv_aligned`
returned only signal columns.

**Fix:** `structural_sl_mode="ignore"` in `dss_objective.py`; merge primary OHLCV
into aligned frame in `signal_composer.py`. Strengthened regression tests.

**Files:** `src/backtester/strategy_discovery/{dss_objective,signal_composer}.py`,
`tests/backtester/{test_dss,test_signal_composer}.py`.

---

## 2026-06-10 — Direct Signal Search (DSS) — full implementation

- Implemented all 5 phases of DSS: parameterized catalog (P1), SignalComposer (P2),
  DSSObjective + cache (P3), report + CLI + DSSStrategy (P4), tests (P5).
- 20 parameterized trigger factories + 16 parameterized filter factories with Optuna
  `param_space()` hooks; each returning a closure `TriggerFn` / `FilterFn`.
- `SignalComposer.build(TrialConfig)` → pure `GenerateFn`; `signal_df_to_ohlcv_aligned()`
  bridges event-list → OHLCV-aligned format expected by `Backtester`.
- `DSSSignalCache`: LRU cache keyed by `signal_cache_key + window_label`; hits/misses tracked.
- `DSSObjective`: Optuna objective; returns `(mandate_score_w1, …, mandate_score_wN)` tuple;
  `compute_mandate_score` formula identical to `optimizer.py` (ADR-0031).
- `write_dss_report`: `pareto_front.json`, `summary.md`, `candidates/*.json` (one per top-N trial).
- `DSSStrategy` registered as `"dss_strategy"` — enables `compare-fixed` / `walk-forward` replay.
- `backtester search-signals` CLI subcommand: NSGA-II / TPE / Random sampler, journal resume,
  multi-window, per-symbol, parallel jobs.
- Bugfix in `features.py`: `atr.replace(0, pd.NA)` → `atr.replace(0, np.nan)` (object-dtype crash).
- 32 tests pass (`test_signal_composer.py` + `test_dss.py`).
- Files: `src/backtester/strategy_discovery/{parameterized_triggers,parameterized_filters,
  dss_config,signal_composer,dss_cache,dss_objective,dss_report,__init__}.py`,
  `src/backtester/strategies/dss_strategy.py`, `src/backtester/{__main__,registry}.py`,
  `tests/backtester/{test_signal_composer,test_dss}.py`.

## 2026-06-10 — Direct Signal Search architecture and specifications

- New discovery architecture: multi-objective Optuna (NSGA-II) searching directly on
  `mandate_score` across multiple independent time windows, replacing beam search with
  a proxy win-rate metric.
- ADR-0035: `docs/decisions/0035-direct-signal-search.md` — full architecture decision
  (parameterized catalog, SignalComposer, DSSObjective, NSGA-II, signal caching, Pareto
  front reporting, `backtester search-signals` CLI).
- Full system spec: `docs/discovery/direct_signal_search.md` — all data types, catalogs,
  CLI reference, integration with compare-fixed/walk-forward, 5-phase implementation plan.
- SignalComposer contract: `docs/discovery/signal_composer.md` — generate_fn schema,
  ATR-based SL/TP derivation, error handling table, factory patterns, test checklist.
- `docs/tasks/BACKLOG.md` — P0 DSS implementation task added with phase breakdown.
- Files: `docs/decisions/0035-*`, `docs/discovery/direct_signal_search.md`,
  `docs/discovery/signal_composer.md`, `docs/tasks/`.

## 2026-06-10 — Walk-forward validation command

- New `backtester walk-forward` CLI command: rolling IS/OOS Optuna optimization and
  evaluation to distinguish genuine edge from regime-specific overfitting (ADR-0034).
- `src/backtester/walk_forward.py`: `generate_windows()`, `run_walk_forward()`,
  `write_walk_forward_report()`. Eval-only mode (`--trials 0`) for fast per-year audit.
- Output: `summary.md` (IS/OOS table + interpretation verdict) + `summary.json` +
  per-window `is_trials.csv` / `is_best_trial.json` / `oos_metrics.json`.
- 16 unit tests in `tests/backtester/test_walk_forward.py`.
- ADR: `docs/decisions/0034-walk-forward-validation.md`.
- Files: `src/backtester/walk_forward.py`, `src/backtester/__main__.py`,
  `tests/backtester/test_walk_forward.py`, `docs/decisions/0034-*`, `docs/tasks/`.

## 2026-06-09 — M4 live execution module + scheduler integration

- New `src/crypt/execution/` package: `ExecutionSettings`, `LivePosition` +
  atomic JSON state, `LiveRiskCalculator` (mirrors `BasicRiskModel` exactly),
  `LiveSignalRunner` (runs `crypt_ensemble.generate()` on live Parquet;
  CPU-bound call in thread pool via `run_in_executor`),
  `OKXTradingClient` (market entry + embedded SL/TP via ccxt), `LiveExecutionManager`.
- Default `dry_run=True` — no real orders placed until owner sets
  `EXECUTION_DRY_RUN=false`.
- New `H1Scheduler` in `src/crypt/runtime/scheduler.py` (fires at `*:02` UTC every hour).
- `src/crypt/__main__.py` updated: `H1Scheduler` + `LiveExecutionManager` wired;
  reconcile on startup; clean shutdown; `_maybe_build_execution_manager()` guard
  rejects `dry_run=false` without OKX credentials.
- `.env.example`: all `EXECUTION_*` vars documented with inline comments and safe defaults.
- 21 unit tests in `tests/execution/`; ruff + mypy strict — 0 errors.
- Owner override applied: proceeding without a promoted candidate (NR4 is archive).
- ADR: `docs/decisions/0033-m4-live-execution-architecture.md`.
- Spec: `docs/execution/live_execution.md`.
- Files: `src/crypt/execution/`, `src/crypt/__main__.py`,
  `src/crypt/runtime/scheduler.py`, `tests/execution/`, `.env.example`,
  `docs/execution/`, `docs/decisions/0033-*`, `docs/tasks/`.

## 2026-06-09 — Mandate-aware Optuna target

- Added `backtester optimize --target mandate_score` for ADR-0025-aligned trial
  ranking: capped monthly return minus penalties for monthly shortfall, DD
  breaches, excess below-floor months, and 3+ losing-month streaks.
- Optimizer trials now export mandate attrs (`mandate_score`, monthly floor
  counts, DD breach count, capped monthly summaries, verdict) into
  `trials.csv` / `best_trial.json`.
- ADR: `docs/decisions/0031-mandate-aware-optuna-target.md`.
- Files: `src/backtester/`, `tests/backtester/`, `docs/`, `README.md`.

## 2026-06-09 — NR4 continuous mandate re-baseline (ADR-0032)

- Owner-run continuous `compare-fixed` on mandate-score best params (tp=0.016,
  rrr=2.5, ttl=36, risk=1.5%):
  `results/nr4_mandate_score_best_compare/20260609_150212/`.
- Verdict **archive**: +185.06% capped sum, **9/12** months ≥15%, **1** DD breach
  (Mar −17.11%). Matches Optuna mandate_score proxy.
- Supersedes isolated-window results for promotion decisions.

## 2026-06-09 — Continuous mandate evaluation default (ADR-0032)

- `compare-fixed` now defaults to **continuous** mode (`--continuous` /
  `--isolated-windows`); positions carry through calendar months on one
  year-long backtest per symbol.
- Isolated per-month resets are diagnostic only; align mandate with
  `investment_mandate.md` and Optuna `mandate_score`.
- ADR: `docs/decisions/0032-continuous-mandate-evaluation.md`.

## 2026-06-09 — NR4 re-baseline (ADR-0029 + ADR-0030)

- Owner-run 12-month `compare-fixed` on frozen Optuna best (tp=0.016, rrr=2.5,
  ttl=48, risk=2%): `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/`.
- Verdict **discard** unchanged: +164.75% capped sum, 8/12 months ≥15%, 4 below
  floor. DD breaches **2** (Feb −11.4%, Mar −20.21%) under ADR-0030; was 3 under
  rolling-peak DD. ADR-0029 isolated mode had no numeric effect.
- Updated `docs/candidates/nr4_vwap_robust.md`, `IN_PROGRESS.md`, mandate §9.

## 2026-06-09 — Drawdown from window-start capital (closed trades only)

- Mandate and `ResultsAnalyzer` now define max DD as the worst realized
  equity below **window-start capital** (not rolling peak). Only **closed**
  trade exit points count; open positions are ignored until exit.
- Each mandate month / compare-fixed window uses its own `initial_capital`
  baseline (e.g. $10k per month).
- ADR: `docs/decisions/0030-drawdown-from-window-start.md`.

## 2026-06-09 — Isolated margin always on (ADR-0029)

- Removed `--is-isolated-futures` CLI flag; `ExecutionSim` always enforces
  OKX isolated-margin leverage consistency (`ISOLATED_FUTURES_ALWAYS`).
- Dropped `is_isolated_futures` from `BacktestArgs` / strategy overrides.
- NR4 and future runs need re-baseline — prior Optuna/mandate without flag
  used optimistic cross-margin semantics.

## 2026-06-09 — Candidate archive + NR4 active plan

- Archive layout spec: `docs/backtester/candidate_archive.md`.
- Shelved NR7 and VWAP reclaim: `docs/archive/candidates/` (mandate snapshots,
  `execution_params.json`, `provenance.json`); frozen JSON in `strategies/archive/`.
- Removed archived strategies from `strategies/backtester/`; NR4 remains active.
- NR4 near-miss plan: `docs/candidates/nr4_vwap_robust.md`.
- Updated `investment_mandate.md` §5.2/§9, README Status, `IN_PROGRESS.md`.

## 2026-06-09 — Fix v3 donor filters rejecting numpy pandas scalars

- `_int_or_none` / `_finite_float_or_none` in `crypt_ensemble.py` now accept
  `numpy.int64` / `numpy.float64` from discovery feature columns; previously
  `session_off_hours` and VWAP distance filters saw `missing_hour_utc` on every
  bar and produced zero trades.
- `temp.sh`: parse Optuna `position_ttl_bars` when `ttl` key absent.

## 2026-06-09 — v3 discovery candidates → donor crypt_ensemble

- Mapped robust v3 stacks to donor execution: `h1_vwap_reclaim` and
  `h1_nr4_breakout` triggers plus v3 filters (session off-hours, BB width rank,
  VWAP distance band, avoid doji).
- `convert.py` + `crypt_ensemble.py` filter/trigger parity with discovery
  features; checked-in strategies:
  `crypt_ensemble_h1_discovery_vwap_reclaim_robust.json`,
  `crypt_ensemble_h1_discovery_nr4_vwap_robust.json`.
- Spec `docs/strategy_discovery.md` §13 updated; convert tests added.

## 2026-06-08 — Strategy discovery catalog v3 (OHLCV expansion)

- Added `catalog_expansion.py`: **+30 triggers**, **+67 filters** (candle patterns,
  session/VWAP, compression/expansion, parameterized threshold bands).
- Extended `features.py` with session VWAP, wick ratios, gaps, NR4/14, Donchian,
  MACD proxy, consecutive candle counts, BB width rank, ATR ratio bands.
- Catalog totals: **44 triggers + 100 filters** (was 14 + 33). v3 blocks are
  discovery-only until mapped in `convert.py`.
- Spec: `docs/strategy_discovery.md` § v3; tests updated in
  `tests/backtester/test_strategy_discovery.py`.

## 2026-06-08 — Strategy execution context + NR7 tp_pct validation

- `StrategyExecutionContext` propagated into `strategy.generate()` via
  `StrategyData.metadata["execution_context"]` (ADR-0028).
- With `exit_geometry=tp_pct`, `crypt_ensemble` skips structural SL entry gate;
  discovery-mapped filters still apply; Optuna signal cache keys include
  execution-context dimensions.
- Fixed optimizer `best_run/` re-export: cached path now uses
  `backtest_run_kwargs()` so `exit_geometry` / `tp_move_pct` are not dropped.
- Owner-run Jan NR7 tp_pct (SOL H1): execution-context fix raised trades **7 → 11**
  (`results/nr7_tp_pct_jan_rerun_v2/`); Jan Optuna best **+6.30%**, PF 2.29
  at `tp=0.008`, `rrr=1.75`, `ttl=36`, `risk=1%`
  (`results/nr7_tp_pct_optuna_jan_v2/`). Still below mandate +15%/month floor.
- ADR-0028; spec `docs/backtester/exit_geometry.md` § execution context.
- Files: `src/backtester/execution_context.py`, `cli_runner.py`, `tester.py`,
  `optimizer.py`, `strategies/crypt_ensemble.py`, tests.

## 2026-06-08 — TP-first exit geometry (`tp_move_pct`)

- New execution mode `exit_geometry=tp_pct`: TP from target price move %,
  SL derived via `rrr`, structural `sl_price` capped by default (`cap`).
- Optuna: search `tp_move_pct` with `--tp-move-pct-low/high/step` (parallel
  with `rrr`, `ttl`).
- CLI: `--exit-geometry`, `--tp-move-pct` on `run`, `optimize`, `compare-fixed`.
- Spec: `docs/backtester/exit_geometry.md`; ADR-0027.

## 2026-06-08 — Continuous compare-fixed for ttl=0

- `compare-fixed --continuous`: one backtest per symbol across all windows;
  monthly rows derived from continuous trades (positions carry through month
  boundaries; no orphan/force-close at window end).
- `--ttl 0` auto-enables continuous mode; `ExecutionSim` already leaves open
  positions as `exit_reason=open` at end of data.
- Mandate export dedupes trades when multiple derived rows share one
  `continuous_run_dir`.
- Files: `src/backtester/fixed_candidate_report.py`, `src/backtester/__main__.py`,
  tests.

## 2026-06-08 — NR7 discovery donor execution validation

Owner-run SOL 2025 monthly `compare-fixed` on
`crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json`.

**Mandate verdict: discard** (0/12 months ≥15%, 3 consecutive losing months
Sep–Nov). **But:** sum capped **+25.6%**, 8/12 positive months, max DD **-6.47%**,
trade WR **54.2%** — best discovery→execution transfer so far vs momentum-burst
(-10.95% sum, 6 losing streak).

Artifact: `results/crypt_h1_discovery_nr7_bb_squeeze_sol_2025/20260608_124701/`

## 2026-06-08 — NR7 discovery candidate donor conversion

- Added `h1_nr7_breakout` raw trigger to `crypt_ensemble` (discovery-aligned NR7
  rule on closed H1 candles).
- Mapped discovery filters `bb_squeeze` → `max_bb_width_pct = 0.04` and
  `h4_context_aligned` → `require_h4_context_aligned = true`.
- Checked in
  `strategies/backtester/crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json` for
  v2 shortlist top candidate (58.6% label WR / 222 events).
- Next: owner-run SOL 2025 monthly `compare-fixed` (command in
  `docs/tasks/IN_PROGRESS.md`).

**Files touched:** `src/backtester/strategies/crypt_ensemble.py`,
`src/backtester/strategy_discovery/convert.py`, `strategies/backtester/`,
`tests/backtester/`, `docs/`.

## 2026-06-08 — Discovery catalog v2 (OHLCV-only)

- Expanded strategy discovery with **6 triggers** and **15 filters** using only
  OHLCV-derived features (EMA, RSI, Bollinger, candle anatomy, session hours,
  ROC, volume tiers).
- Extended `features.py` with shared v2 indicator columns; progress estimator
  now reads catalog size dynamically.
- v2 blocks are **discovery-only** until mapped in `convert-discovery-strategy`.
- Catalog size: **14 triggers + 33 filters** (was 8 + 18).

**ADRs:** none.

**Verification:** `pytest tests/backtester/test_strategy_discovery.py`; ruff;
mypy on `strategy_discovery/`.

**Files touched:** `src/backtester/strategy_discovery/`, `tests/backtester/`,
`docs/strategy_discovery.md`, `docs/tasks/IDEAS.md`, `CHANGELOG.md`.

## 2026-06-08 — Discovery candidate donor conversion

- Added `backtester convert-discovery-strategy` to map discovery-native
  `rank_*_strategy.json` files into donor `crypt_ensemble` configs.
- Extended `crypt_ensemble` with `h1_momentum_burst` raw trigger and
  discovery-aligned filters: `block_d1_h4_context_reversal`,
  `min_trend_strength_atr`, `min_volume_median_ratio`.
- Checked in reference config
  `strategies/backtester/crypt_ensemble_h1_discovery_momentum_burst_short.json`
  for
  `h1_momentum_burst__avoid_low_volume__block_context_reversal__side_short_only__trend_strength_min`.
- Updated handoff: next owner-run step is SOL 2025 monthly `compare-fixed` on
  the converted config.
- Owner-run result (20260608_114552): **mandate discard** — 0/12 months ≥15%,
  sum capped **-10.95%**, 6 consecutive losing months; label edge did not
  survive donor SL/RRR/TTL/fees.

**ADRs:** ADR-0025 applies; none added.

**Verification:** focused pytest on conversion, discovery filters, and momentum
burst trigger; ruff on changed backtester files.

**Files touched:** `src/backtester/`, `strategies/backtester/`, `tests/backtester/`,
`docs/strategy_discovery.md`, `docs/tasks/`, `CHANGELOG.md`, `README.md`.

## 2026-06-08 — Full-year discovery artifact review

- Reviewed owner-run full SOL 2025 monthly discovery artifact
  `results/discovery_sol_h1_2025_monthly/20260608_113331/`.
- Strict robust shortlist was empty: no candidate kept every month at or above
  `50%` label win rate.
- Selected the only practical full-year shortlist family for possible donor
  conversion:
  `h1_momentum_burst__avoid_low_volume__block_context_reversal__side_short_only__trend_strength_min`.
- Selected profile: `325` events, `180/143/2`, `55.73%` aggregate win rate,
  all 12 months above the event-count floor, 11 of 12 months at or above
  `50%`; July was the weak month at `42.31%`.
- Updated `IN_PROGRESS.md`: next work is to convert that discovery-native
  candidate into a donor-executable diagnostic strategy config or document why
  current `crypt_ensemble` cannot represent it.

**ADRs:** ADR-0025 applies; none added.

**Verification:** inspected full-year `config.json`, `top_win_rate_min_*`,
`robust_min_window_win_rate_50.csv`, `candidates.csv`, and
`candidate_windows.csv`.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-08 — Robust discovery artifact review

- Reviewed owner-run improved monthly discovery artifact
  `results/discovery_sol_h1_monthly/20260608_112946/`.
- `top_win_rate_min_50.csv` still led with
  `h1_order_block_retest__atr_distance_1_2`, but per-window metrics show
  February weakness (`6/8`, `42.86%`).
- `top_win_rate_min_100.csv` led with range-breakout `0..1 ATR` H4-aligned
  variants, but per-window metrics show March weakness (`19/25`, `43.18%`).
- `robust_min_window_win_rate_50.csv` surfaced two mild but stable Jan-Mar
  families: candle-confirm H4-aligned short volatility-normal variants and
  `h1_structure_break__side_short_only`.
- Fixed shortlist CSV exports so `top_*` and `robust_*` files include the same
  per-window robustness summary columns as `candidates.csv`.
- Updated `IN_PROGRESS.md`: next owner-run step is full SOL 2025 monthly
  discovery before any donor conversion.

**ADRs:** ADR-0025 applies; none added.

**Verification:** inspected `top_win_rate_min_*`, `robust_min_window_win_rate_50`,
`candidate_windows.csv`, and reran targeted discovery tests/lint/type checks.

**Files touched:** `src/backtester/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-08 — Discovery robustness shortlists

- Extended `backtester discover-strategies` report exports with
  `candidate_windows.csv` / `.md` containing per-candidate, per-window events,
  wins, losses, neutral count, and win rate.
- Added per-window robustness summary columns to `candidates.csv`.
- Added root shortlist CSV/Markdown exports and matching `best_candidates/`
  subdirectories for top score, top win rate at minimum sample thresholds
  (`50`, `100`, `200`, `500`), and robust candidates with every window at or
  above `50%` win rate.
- Kept legacy `best_candidates/rank_*` top-score artifacts for compatibility.
- Updated docs and active handoff so the next owner-run discovery pass starts
  from the new shortlist files instead of manually sorting `candidates.csv`.

**ADRs:** ADR-0025 applies; none added.

**Verification:** `pytest tests/backtester/test_strategy_discovery.py -q`;
`ruff check` / `ruff format --check` on discovery, CLI, and discovery tests;
`mypy` on discovery, CLI, and discovery tests.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`docs/tasks/`, `README.md`, `CHANGELOG.md`.

## 2026-06-08 — Monthly discovery artifact review

- Reviewed owner-run monthly discovery artifact
  `results/discovery_sol_h1_monthly/20260608_112021/`.
- Top score remained non-directional: `h1_candle_confirm`, `2157` events,
  `49.81%` win rate.
- High-win narrow candidates were not robust enough across months:
  `h1_order_block_retest__atr_distance_1_2` was `65.45%` aggregate but failed
  February; `h1_range_breakout__atr_distance_0_1__h4_context_aligned` was
  `57.97%` aggregate but failed March.
- The most stable checked profile was
  `h1_candle_confirm__h4_context_aligned__side_short_only__trend_strength_min__volatility_normal_only`
  at `286` events and `54.23%` aggregate win rate, with all three months
  mildly positive.
- Updated `IN_PROGRESS.md`: next work should improve discovery report exports
  with per-window W/L/N and robustness-ranked shortlists before converting any
  candidate into a donor execution config.

**ADRs:** ADR-0025 applies; none added.

**Verification:** inspected monthly `config.json`, `candidates.csv`, score
shortlist, and reconstructed per-window labels for selected candidates using
the discovery labeler.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-08 — Discovery artifact review

- Reviewed owner-run discovery artifact
  `results/discovery_sol_h1/20260608_111656/`.
- The top score candidate was dense but not directional:
  `h1_candle_confirm`, `2155` events, `49.77%` win rate.
- The best higher-sample candidates were only mild edges (`>=500` events:
  best `53.23%` win rate), while narrower candidates need stability checks
  (`h1_order_block_retest__atr_distance_1_2`: `55` events, `65.45%`;
  `h1_range_breakout__atr_distance_0_1__h4_context_aligned`: `141` events,
  `56.74%`).
- Updated `IN_PROGRESS.md` to request a monthly-window discovery rerun before
  converting any discovery-native candidate into a donor execution config.

**ADRs:** ADR-0025 applies; none added.

**Verification:** inspected `config.json`, `candidates.csv`, top
`best_candidates/` reports/events, and candidate aggregates with local pandas.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-08 — Discovery progress bar

- Added a Click progress bar to `backtester discover-strategies` so long
  trigger/filter discovery runs show visible progress through dataset
  preparation, trigger generation, labeling, beam evaluation, and export.
- Kept discovery logic unchanged; the progress total is an estimated upper
  bound and is completed when the search exits early.
- Added a focused test that `run_strategy_discovery` emits progress ticks.

**ADRs:** ADR-0025 applies; none added.

**Verification:** `pytest tests/backtester/test_strategy_discovery.py -q`;
`ruff check` / `ruff format --check` on discovery, CLI, and discovery tests;
`mypy` on discovery, CLI, and discovery tests; `backtester
discover-strategies --help`.

**Files touched:** `src/backtester/`, `tests/backtester/`, `CHANGELOG.md`.

## 2026-06-08 — Strategy discovery constructor MVP

- Implemented `backtester discover-strategies`, a self-contained trigger/filter
  discovery job for fixed ATR-barrier forward labels.
- Added the `src/backtester/strategy_discovery/` package with event contracts,
  feature building, eight H1 triggers, eighteen filters, labeler, scoring,
  staged/beam search, and report exports.
- The command writes `config.json`, `candidates.csv`, `candidates.md`,
  `search_trace.csv`, `rejected.csv`, and discovery-native
  `best_candidates/rank_*` artifacts under one timestamped output directory.
- Added focused discovery tests for trigger output, label outcomes, filters,
  no-lookahead H4/D1 context alignment, sample-size scoring, candidate
  de-duplication, and CLI artifact creation.
- Moved the completed P0 implementation task to `DONE.md`; `IN_PROGRESS.md`
  now points to the owner-run discovery command and `BACKLOG.md` tracks the
  follow-up conversion from discovery shortlist to donor strategy config.

**ADRs:** ADR-0025 applies; none added.

**Verification:** `pytest tests/backtester/test_strategy_discovery.py -q`;
`ruff check` / `ruff format --check` on discovery, CLI, and discovery tests;
`mypy` on discovery, CLI, and discovery tests; `backtester
discover-strategies --help`.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/tasks/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-08 — Strategy discovery constructor spec

- Added `docs/strategy_discovery.md`, the contract for a one-session P0
  implementation of `backtester discover-strategies`.
- Defined the trigger/filter model: one trigger plus zero or more filters,
  fixed ATR-barrier forward labels, staged/beam search, scoring, and report
  artifacts.
- Promoted the task to the top of `IN_PROGRESS.md` and `BACKLOG.md` so the
  next agent builds the whole MVP instead of continuing manual one-off H1
  backtest selection.
- Kept risk management, leverage, margin, SL/TP, RRR, TTL, and trailing-stop
  optimization explicitly out of the discovery MVP.

**ADRs:** ADR-0025 applies; none added.

**Verification:** documentation-only change; no tests run.

**Files touched:** `docs/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-08 — Open-position trade accounting

- Diagnosed the owner-run no-setup raw candle-confirm artifact at
  `results/crypt_h1_raw_candle_confirm_no_setup_r1_pos5/20260608_101504/`.
- Root cause of the strange trade count: `ExecutionSim` exported only closed
  positions, so open positions at window end occupied slots and margin but did
  not appear in `trades.csv` or `total_trades`.
- `ExecutionSim` now exports still-open positions as `exit_reason = open`
  without realized `exit_time`, `exit_price`, `pnl_abs`, or `capital_after`.
- `ResultsAnalyzer` now reports `total_trades`, `closed_trades`, and
  `open_trades`; realized PnL/return/win-rate/drawdown metrics use closed
  trades only, while margin/exposure diagnostics still include open rows.
- Fixed candidate, signal-quality, and mandate reports now preserve entry
  counts while keeping realized mandate PnL based on closed exits.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** targeted pytest for execution sim, results analyzer,
mandate report, and fixed candidate report; changed-file ruff check/format;
manual replay of SOL March existing `signals.csv` confirmed `17` closed trades
plus `5` open entries.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/tasks/`,
`CHANGELOG.md`.

## 2026-06-08 — H1 trigger-first discovery reset

- Recorded the owner-directed reset from filtered H1 branch tuning to raw
  trigger discovery.
- Added raw H1 one-trigger strategy configs for candle confirm, sweep reversal,
  structure break, and order-block retest.
- Closed the density review: baseline and age6/noOB remain sparse and far below
  mandate, so the next step is `rrr = 1.0` trigger-quality diagnostics before
  PnL optimization.
- Added diagnostic-only `setup_source = h1_raw` mode so raw H1 triggers can be
  tested without the H4 setup gate.
- Added `crypt_ensemble_h1_raw_candle_confirm_no_setup.json` for the first
  no-setup density check.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** `pytest tests/backtester/test_crypt_ensemble_strategy.py -q`;
`mypy src/backtester/strategies/crypt_ensemble.py`; `ruff check` on changed
strategy/test files; JSON validation for new strategy config. No backtests run
by agent.

**Files touched:** `src/backtester/`, `tests/backtester/`,
`strategies/backtester/`, `docs/`, `CHANGELOG.md`.

## 2026-06-08 — Owner-run backtest rule

- Added the owner-run backtest rule to `AGENTS.md` and
  `.cursor/rules/ai-first-workflow.mdc`.
- Future agents must provide exact backtest/optimizer commands and wait for
  the owner to return with artifacts, unless the owner explicitly asks the
  agent to run a specific command.

**ADRs:** none.

**Verification:** documentation-only change; no tests run.

**Files touched:** `AGENTS.md`, `.cursor/rules/`, `CHANGELOG.md`.

## 2026-06-07 — Visual verdict workflow and no-TTL falsification

- Documented the owner/agent visual verdict workflow for automatic
  `trade_chart.html` artifacts.
- Recorded the owner's verdict for
  `results/crypt_h1_visual_review/20260607_203324/`: too few trades, test
  without TTL.
- Ran the same three reviewed windows with `--ttl 0` at
  `results/crypt_h1_visual_review_no_ttl/20260607_204930/`.
- Decision: reject no-TTL for this H1 branch; all three reviewed windows
  worsened, TTL exits mostly became stop-loss exits, and sparse trade count
  remained the core issue.
- Next step: compare less sparse H1 configs with continuous charts before a
  new optimizer/grid branch.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed `backtester compare-fixed --ttl 0
--is-isolated-futures --jobs 3`; inspected `windows.csv`, `trades.csv`, and
generated HTML reports.

**Files touched:** `docs/`, `results/`, `CHANGELOG.md`.

## 2026-06-07 — Automatic TradingView trade chart frontend

- `ResultsAnalyzer.export_results(..., ohlcv_df=...)` now writes
  `ohlcv.csv` and `trade_chart.html` automatically.
- This covers `backtester run`, optimizer `best_run/`, `compare-fixed`,
  `compare-grid`, and `signal-quality` artifacts.
- Replaced the temporary Plotly report with TradingView Lightweight Charts.
- The chart uses the full continuous OHLCV frame, so candles are visible
  between trades.
- Kept `backtester trade-chart` only as a manual regeneration command for old
  artifacts or custom `--ohlcv` sources.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** `pytest tests/backtester/test_trade_chart_report.py
tests/backtester/test_results_analyzer.py -q`; `mypy
src/backtester/trade_chart_report.py`; changed-file `ruff check`; `uv lock`.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `pyproject.toml`, `uv.lock`, `results/`, `CHANGELOG.md`.

## 2026-06-07 — H1 distance-filter tiny execution grid

- Completed seven-window execution-only grid for
  `crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4.json`.
- Artifact:
  `results/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4_grid/20260607_192915/`.
- Best row: `rrr = 1.5`, `ttl = 36`, `max_positions = 1`, `+6.18%` total,
  `37` trades, worst DD `-2.26`.
- Decision: reject this branch for SOL 2025 mandate validation and broad
  Optuna; the best row is still far below the `+15%` monthly floor and depends
  heavily on TON February.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed owner-run `compare-grid --is-isolated-futures
--jobs 3`; inspected `grid.csv`; no `grid_errors.csv` was written.

**Files touched:** `results/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-07 — H1 trigger freshness and stop-distance diagnostics

- Added two H1 diagnostic strategy configs: age-6 freshness without
  `h1_order_block_retest`, and the same profile with a `2..4 ATR` signal
  stop-distance filter.
- Owner-ran the standard seven-window isolated `compare-fixed` reports.
- Result: age-6/no-OB alone was weaker than baseline (`+0.41%` vs `+1.32%`);
  age-6/no-OB with `2..4 ATR` improved to `+3.78%` but only across `39`
  trades and with no month near the `+15%` mandate floor.
- Decision: do not run broad Optuna or SOL 2025 mandate validation yet; next
  step is a tiny execution-only grid for the `2..4 ATR` diagnostic.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** `pytest tests/backtester/test_crypt_ensemble_strategy.py -q`;
completed owner-run `compare-fixed --is-isolated-futures --jobs 3` for both
diagnostic configs; inspected `windows.csv`, mandate summaries, `signals.csv`,
and `trades.csv`.

**Files touched:** `strategies/backtester/`, `results/`, `docs/tasks/`,
`CHANGELOG.md`.

## 2026-06-07 — H1 structural-trigger bounded validation

- Completed isolated seven-window bounded validation for the rewritten
  `crypt_ensemble_h1.json` structural-trigger baseline.
- Artifact:
  `results/crypt_ensemble_h1_structural_trigger_bounded_isolated/20260607_183249/`.
- Result: roughly `+1.32%` total across SOL Jan/Feb/Mar and TON
  Jan/Feb/Mar/Apr 2025; no month passed the `+15%` mandate floor.
- Mandate summary: SOL is only technically `full_optuna` over the short
  three-month diagnostic slice; TON is `discard` because 4/4 months are below
  the floor.
- Decision: do not run broad Optuna or SOL 2025 mandate validation on this
  baseline; next tune H1 trigger freshness/rule mix and the harmful
  `1_2_atr` stop-distance bucket.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed owner-run `backtester compare-fixed
--is-isolated-futures --jobs 3`; generated and inspected
`setup_attribution.csv`.

**Files touched:** `results/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-07 — H1 structural-trigger rewrite

- Rewired `crypt_ensemble` H1 `trigger_rules` so JSON configuration now affects
  entry logic.
- Added structural H1 trigger rules: sweep reversal, structure break, and
  order-block retest.
- Kept `h1_candle_confirm` only as an explicit legacy diagnostic rule.
- Updated H1 strategy JSON configs to use structural triggers by default.
- Added a future backlog task for standalone interactive HTML trade-chart
  reports; no report implementation was shipped in this session.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** targeted strategy pytest; targeted mypy; changed-file ruff
check/format; short SOL H1 smoke at
`/tmp/crypt_structural_h1_smoke/20260607_144558/`.

**Files touched:** `src/backtester/`, `tests/backtester/`,
`strategies/backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-07 — H1 pivot-only bounded validation

- Ran seven-window bounded `compare-fixed` for
  `crypt_ensemble_h1_filter_pivot_only.json`.
- Result: `-3.04%` total across SOL Jan/Feb/Mar and TON Jan/Feb/Mar/Apr 2025;
  SOL summed `+2.93%`, TON summed `-5.97%`.
- Mandate summary: SOL is weak/full-Optuna eligible over the 3-month diagnostic
  slice, while TON is `discard` because 4/4 months are below the 15% floor.
- Decision: discard `pivot_only` as a general filter for now; do not spend a
  tiny grid or SOL 2025 mandate run on it.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed `backtester compare-fixed --jobs 3`; inspected
`windows.csv`, `monthly_mandate.csv`, and `mandate_summary.csv`.

**Files touched:** `results/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-07 — H1 structural-stop quality filters

- Added default-off `allowed_sl_anchor_types`,
  `min_signal_sl_distance_atr`, and `max_signal_sl_distance_atr` filters to
  donor `crypt_ensemble`.
- Added pivot-only and anchor-distance/no-sweep H1 diagnostic strategy configs.
- Ran SOL March 2025 and TON February 2025 bounded `compare-fixed` reports.
- Decision: pivot-only improved both problem windows and should be validated
  across the standard bounded window set; the distance/no-sweep filter is
  TON-positive but SOL-negative.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** `pytest` for `test_crypt_ensemble_strategy.py`; source
`mypy`; changed-file `ruff check` and `ruff format --check`; two completed
`backtester compare-fixed` reports.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`strategies/backtester/`, `results/`, `CHANGELOG.md`.

## 2026-06-07 — H1 setup attribution report

- Added `setup_snapshot_time` to `crypt_ensemble` signal exports.
- Extended `backtester signal-quality` with `setup_attribution.csv` /
  `setup_attribution.md` for tradeable and rejected H1 setup rows.
- Ran SOL March 2025 and TON February 2025 attribution at
  `results/crypt_h1_setup_attribution/20260607_112717/`.
- Decision: next H1 signal-logic work should test structural-stop quality
  filters before broad Optuna or another SOL 2025 mandate run.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** targeted pytest for backtester reports and `crypt_ensemble`;
targeted mypy for changed source modules; changed-file ruff check and format
check.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `results/`, `CHANGELOG.md`.

## 2026-06-06 — Broader H1 setup diagnostics

- Ran bounded execution-only H1 optimizer diagnostics for SOL March 2025 and
  TON February 2025.
- Compared both windows against the fixed `rrr = 1.25`, `ttl = 36`,
  `max_positions = 1` baseline.
- Decision: next code/report work should target H1 trigger/setup-quality
  attribution, not side gating or broad Optuna.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed two `backtester optimize` runs and one
`backtester compare-fixed --jobs 2` baseline; inspected optimizer and
best-run diagnostics.

**Files touched:** `results/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-06 — OHLCV preflight task canceled

- Canceled the P1 OHLCV coverage preflight task by owner direction.
- Removed the task from active backlog and replaced the handoff with the P0
  H4/H1 setup-geometry diagnostic chain.
- Left prior SOL data-coverage incident notes intact as historical context.

**ADRs:** none.

**Verification:** documentation-only update.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-06 — Stop-loss limit task canceled

- Canceled the P1 stop-loss count limit task by owner direction.
- Removed the task from active backlog; subsequent handoff was redirected again
  after the owner also canceled OHLCV preflight work.
- Marked stop-loss count limits as canceled in the investment mandate so future
  agents do not treat them as approved current-search work.

**ADRs:** ADR-0025 updated in-place by owner direction; none added.

**Verification:** documentation-only update.

**Files touched:** `docs/`, `CHANGELOG.md`.

## 2026-06-06 — SOL 2025 mandate validation artifact

- Diagnosed the owner-run `compare-fixed` failure: local SOL OHLCV parquet
  ended in April 2025, leaving `sol_2025_05` and later H1 windows empty.
- Backfilled SOL OHLCV through `2026-01-01` and verified full 2025 H1/H4/D1
  coverage.
- Reran the 12-month SOL H1 short-only fixed candidate at
  `results/crypt_ensemble_h1_short_only_sol_2025_mandate/20260606_120001/`.
- Mandate verdict: **discard**; `0/12` months passed the `+15%` floor, capped
  yearly sum was `+6.82%`, worst monthly DD was `-5.41%`.
- Added a P1 backlog item for OHLCV coverage preflight before expensive window
  reports.

**ADRs:** ADR-0025 applies; none added.

**Verification:** completed `backtester compare-fixed --jobs 3`; inspected
`windows.csv`, `monthly_mandate.csv`, and `mandate_summary.csv`.

**Files touched:** `data/`, `results/`, `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-06 — Mandate reporting for fixed candidates

- Added `docs/mandate_reporting.md` and `src/backtester/mandate_report.py`.
- `backtester compare-fixed` now exports per-symbol `monthly_mandate.csv`,
  `mandate_summary.csv`, and `mandate_summary.md` from per-window `trades.csv`
  artifacts, preserving ADR-0025's separate portfolio assumption.
- Mandate report covers raw/capped monthly returns, excess return,
  intra-month max DD, stop-loss counts, losing-month streaks, and
  promote/archive/discard/full-Optuna verdicts.
- Moved the P0 mandate-metrics item to `DONE.md`; next handoff is real SOL
  2025 artifact validation or P1 stop-loss limits.

**ADRs:** ADR-0025 applies; none added.

**Verification:** `uv run pytest tests/backtester -q`; targeted
`uv run mypy src/backtester/mandate_report.py src/backtester/fixed_candidate_report.py`;
changed-file `ruff check --select E,F,I --ignore E501`; changed-file
`ruff format --check`.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-06 — Bounded trailing-stop evaluation

- Checked the owner-run trailing grid at
  `results/crypt_ensemble_h1_short_only_trailing_grid/20260606_104945/`; it
  failed all windows because trailing was enabled with `trail_distance_atr = 0`.
- Reran the seven-window short-only H1 bounded grid at
  `results/crypt_ensemble_h1_short_only_trailing_grid_rerun/20260606_110353/`.
- Fixed TP remained best: aggregate `+10.12%`; best trailing row
  (`trail_activation_rrr = 1.25`, `trail_distance_atr = 0.5`) reached only
  `+7.70%`.
- Decision: do not widen trailing to SOL 2025 for this candidate row; return
  to mandate reporting unless the owner chooses another signal-quality test.

**ADRs:** ADR-0025 and ADR-0026 apply; none added.

**Verification:** completed `backtester compare-grid` artifact with 140 rows
and no `grid_errors.csv`; Python aggregation of `grid.csv`.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-06 — Optional trailing-stop execution

- Added optional `trail_activation_rrr` / `trail_distance_atr` execution
  params across `ExecutionSim`, `Backtester.run`, CLI, optimizer, and bounded
  reports.
- `trail_activation_rrr = 0` preserves fixed TP; after activation fixed TP is
  disabled and exits export `exit_reason = trailing_stop` with taker fee.
- Reports now include trailing params and `exit_trailing_stop`; README and MTF
  docs show bounded search usage.
- Next: run a bounded trailing-stop grid for the current H1 short-only
  finite-position row.

**ADRs:** none.

**Verification:** targeted backtester pytest `48 passed`; changed-file
formatter check clean; changed-file `ruff check --select E,F,I --ignore E501`
clean; `backtester run/optimize/compare-grid --help` expose the new flags.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-05 — Post-margin-fix validation grids (owner-run)

- Owner completed bounded H1 short-only grids at `risk_percent = 1.0`, `0.5`,
  `0.25` after ADR-0026.
- Confirmed monotonic `peak_locked_margin_pct_initial` on all seven windows;
  aggregate return scales `+10.12%` → `+5.06%` → `+2.51%`; max peak margin
  `46.38%` → `23.19%` → `11.59%` (no `96.62%` plateau).
- Margin audit acceptance passed; candidate still not mandate-promotable.
- Next: P0 mandate-metrics CLI.

**ADRs:** ADR-0026 applies.

**Verification:** owner-run `compare-grid` artifacts; Python cross-check of
three `grid.csv` files.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — Isolated-margin leverage selection (ADR-0026)

- Audited donor margin geometry after the H1 `max_positions = 1` grid kept peak
  locked margin at `96.62%` when `risk_percent` was lowered.
- Added `margin_policy.py`; unified per-slot caps across `risk_model.py` and
  `execution_sim.py`; switched to max-leverage locked-margin selection when the
  position fits the cap.
- Added `tests/backtester/test_margin_policy.py`; updated execution-sim margin
  expectations.
- Next: re-run bounded H1 short-only grids, then P0 mandate-metrics CLI.

**ADRs:** ADR-0026 (new).

**Verification:** `uv run pytest tests/backtester -q` (all passed).

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`.

## 2026-06-05 — Owner investment mandate (ADR-0025)

- Documented auto-trading candidate gates in `docs/investment_mandate.md`:
  +15%/month ($1 500 on $10k), 2025 full-year SOL-first backtest, 10% intra-month
  max DD, capped positive outliers at 20%, archive/discard/full-Optuna funnel.
- Added ADR-0025; surfaced mandate in `README.md`, `AGENTS.md` session-start
  list, and `BACKLOG.md` header.
- Approved capped-profit policy from `IDEAS.md`; added backlog items for mandate
  metrics, trailing stop, stop-limit Optuna dims, and archive layout.

**ADRs:** ADR-0025 (new).

**Verification:** documentation only.

**Files touched:** `docs/`, `README.md`, `AGENTS.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 finite-position grid result

- Inspected the completed owner-started `max_positions` grid at
  `results/crypt_ensemble_h1_short_only_max_positions_grid/20260605_125237`.
- Best aggregate row: `rrr = 1.5`, `ttl = 42`, `max_positions = 1`,
  `risk_percent = 1.0`, totaling `+10.12%` across seven windows.
- Reran that bounded row at `risk_percent = 0.5` and `0.25`. Returns/drawdowns
  scaled down to `+5.06%` / `-4.45` and `+2.51%` / `-2.24`, but peak locked
  margin still reached `96.62%` of initial capital.
- Decision: not promoted; lower risk sizing alone does not fix the margin
  realism blocker. Added a P0 follow-up to audit finite-position margin sizing
  semantics before H1 promotion.

**ADRs:** ADR-0024 applies; none added.

**Verification:** owner-started artifact inspection plus two completed
`backtester compare-grid` lower-risk repeats; no tests run.

**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — `max_positions` search wiring

- Added optimizer search for `max_positions` via explicit
  `--max-positions-values`, with low/high/step range flags still available.
- Added `compare-grid --max-positions-values` so bounded execution grids can
  compare `rrr` / `ttl` / concurrent-position caps while reusing one signal
  frame per window.
- Exported `max_positions` in fixed/grid/signal-quality summaries and made
  optimizer `best_run/` respect the selected value.
- Updated README/MTF docs and task trackers for the finite-position-cap
  workflow required by ADR-0024.

**ADRs:** ADR-0024 applies; none added.

**Verification:** targeted optimizer/report pytest `11 passed`; changed-file
formatter check clean; changed-file `ruff check --select E,F,I --ignore E501`
clean; `optimize --help` and `compare-grid --help` show the new flags.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 margin-realism audit

- Added trade-level margin exports: `locked_margin`,
  `available_balance_before`, `open_positions_before`,
  `total_locked_margin_before`, and `total_locked_margin_after_entry`.
- Added report-level peak margin/concurrency columns to `compare-fixed` /
  execution-grid summaries and margin rows to `trade_diagnostics.csv`.
- Reran the seven-window short-only H1 audit at
  `results/crypt_ensemble_h1_short_only_margin_audit/20260605_122841`.
- Result: unconstrained short-only remains `+3.96%` overall but is not
  promotable; peak simultaneous positions reached 18 and peak locked margin
  reached `104.42%` of initial capital.
- Updated docs to make finite `max_positions` the next required P0 before
  owner-run promotion checks.

**ADRs:** ADR-0024 applies; none added.

**Verification:** targeted backtester pytest `49 passed`; changed-file
formatter check clean; changed-file `ruff check --select E,F,I --ignore E501`
clean. Full root ruff still fails on pre-existing donor style debt.

**Files touched:** `src/backtester/`, `tests/backtester/`, `docs/`,
`README.md`, `CHANGELOG.md`.

## 2026-06-05 — H1 short-only candidate validation

- Completed fixed-candidate validation for
  `strategies/backtester/crypt_ensemble_h1_filter_short_only.json` with
  `rrr = 1.25`, `position_ttl_bars = 36`, and `risk_percent = 1.0`.
- Seven-window result across SOL Jan/Feb/Mar 2025 and TON Jan/Feb/Mar/Apr
  2025: total `+3.96%`, 470 short-only trades, 3 positive windows, 3 negative
  windows, 1 flat no-trade window. Worst window was TON March at `-10.65%`,
  `profit_factor = 0.66`, max drawdown `-20.52`; TON April produced no trades.
- Conclusion: useful diagnostic, not promoted. ADR-0024 still blocks H1
  promotion until margin usage, concurrent positions, and finite
  `max_positions` behavior are auditable.
- Added a P2 backlog follow-up to align `compare-fixed` defaults/docs with the
  seven-window candidate-validation acceptance set.

**ADRs:** ADR-0024 applies; none added.
**Files touched:** `docs/tasks/`, `CHANGELOG.md`.

## 2026-06-05 — Margin-realistic H1 concurrency documented

- Recorded ADR-0024: H1 candidates cannot be promoted until concurrent
  position and margin usage are auditable.
- Documented that `capital_before` / `capital_after` are realized-equity
  fields, not free-margin fields.
- Added P0 follow-ups to export margin diagnostics and make `max_positions` a
  bounded Optuna/search dimension before promoting short-only.
- Added a P1 follow-up for explicit isolated-futures liquidation/effective-stop
  modeling before using maximum leverage as a candidate assumption.

**ADRs:** added ADR-0024.

**Verification:** documentation-only update; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

## 2026-06-04 — H1 filter comparison and ablations

- Ran full base-vs-filtered H1 signal-quality diagnostics across SOL
  Jan/Feb/Mar 2025 and TON Jan/Feb/Mar/Apr 2025.
- Added focused ablation configs for short-only, no-liquidity-sweep,
  max-72h-anchor-age, and short-plus-no-liquidity-sweep comparisons.
- Results: base `-12.72%`; full filter `+2.31%`; short-only `+3.96%`;
  no-liquidity-sweep `-8.29%`. The full filter is not promoted; the next
  bounded candidate should be short-only.
- Updated task trackers with the completed artifacts and the next validation
  handoff.

**ADRs:** none.

**Verification:** completed `backtester signal-quality` runs with
`UV_CACHE_DIR=/tmp/uv-cache` for base, full filter, short-only, and
no-liquidity-sweep reports.

**Files touched:** `strategies/`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — H1 signal-quality diagnostics and filters

- Added `backtester signal-quality` for report-only H1 diagnostics across
  SOL/TON windows, exporting `signals.csv` / `groups.csv`, Markdown copies,
  fail-soft `errors.csv`, and per-window donor artifacts.
- Added H1 diagnostic filters to `crypt_ensemble`: `allowed_sides`,
  `blocked_sl_anchor_types`, `max_anchor_age_hours`, and
  `block_context_reversal`, with `signal_filter_reason` exported on signals.
- Added `strategies/backtester/crypt_ensemble_h1_filtered.json` as a
  diagnostic profile for short-only, no-liquidity-sweep-anchor, max-72h-anchor
  age, and context-reversal checks.
- Updated `AGENTS.md` so task docs must include what/why/gain/acceptance and
  agents must explain selected task intent at session start and read the next
  step back at session end.
- Updated README, MTF spec, migration docs, and task trackers for the new
  diagnostic workflow.

**ADRs:** none.

**Verification:** `uv run pytest tests/backtester -q` -> 114 passed with 4
existing pandas timezone-to-period warnings; `uv run ruff check` on changed
backtester tests clean; `uv run backtester --help` and
`uv run backtester signal-quality --help` verified with `UV_CACHE_DIR=/tmp`;
short SOL base and filtered `signal-quality` smokes completed under `/tmp`.

**Files touched:** `AGENTS.md`, `README.md`, `src/backtester/`,
`tests/backtester/`, `strategies/`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — Document mise as optional

- Clarified that `uv` / `pyproject.toml` are the canonical dependency,
  script, and Python-tooling surface.
- Documented root `mise.toml` as an optional local convenience layer that
  wraps the same `uv` commands.

**ADRs:** none.

**Verification:** documentation-only update; no tests run.

**Files touched:** `README.md`, `docs/`, `CHANGELOG.md`.

## 2026-06-04 — Root-integrated backtester package

- Added ADR-0023 for the new layout: `backtester` now lives under
  `src/backtester/` inside the root `uv` project.
- Moved donor tests to `tests/backtester/` and strategy JSON configs to
  `strategies/backtester/`.
- Removed the old nested `backtester/` project boundary: donor
  `pyproject.toml`, donor `uv.lock`, Hatch/versioningit config, donor
  `mise.toml`, donor `.cursor` rules, local venv/cache/results, and unused
  donor dashboard/scripts/gui files.
- Added root `mise.toml` and root `backtester` console script.
- Merged donor runtime dependencies into root `pyproject.toml` and refreshed
  `uv.lock`.
- Retired and deleted the obsolete `src/crypt/backtest/` harness and
  `tests/backtest/` after usage search found no live imports outside stale
  docs/self-tests.
- Updated README, backfill/backtester docs, CI/pre-commit/mise commands, and
  task trackers for root-level backtester usage.

**ADRs:** added ADR-0023; updated ADR-0018 and ADR-0021 with supersession
notes.

**Verification:** `uv run pytest -q` -> 187 passed with 4 existing pandas
timezone-to-period warnings; `uv run pytest tests/backtester -q` -> 108
passed with the same warnings; `uv run mypy --strict src/crypt` clean; root
gated `ruff check` and `ruff format --check` clean; `uv run backtester --help`
works; `uv lock --check` clean.

**Files touched:** `src/backtester/`, `src/crypt/`, `tests/`,
`strategies/`, `docs/`, `.github/`, root tooling files.

## 2026-06-04 — Owner-run H1 artifacts and grid fail-soft

- Unpacked and inspected owner-provided `results.tar` from the unattended H1
  diagnostic commands.
- Reviewed full candidate A results: SOL full was only mildly positive
  (`+4.39%`, PF `1.09`) and TON full failed badly (`-54.65%`, PF `0.71`,
  max drawdown `-54.49`), so candidate A is rejected as calibration.
- Reconstructed the aborted monthly `compare-grid` from per-run artifacts:
  360 candidates across 10 completed windows, no robust `rrr`/`ttl` candidate,
  and no candidate with at least 7 positive windows.
- Changed `backtester compare-grid` to preserve completed summaries when some
  windows fail, writing `grid.csv` / `grid.md` plus `grid_errors.csv` /
  `grid_errors.md`.
- Added a focused regression test and updated README/task docs for the new
  fail-soft output and next diagnostic direction.

**ADRs:** none.

**Verification:** ruff check and format clean on changed report/test files via
root `uv --group dev`; targeted donor pytest `6 passed` with 4 existing
pandas timezone-to-period warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Precomputed execution-grid signals

- Inspected SOL March diagnostics for the best grid row and candidate A:
  failures are short-only, bearish-context, stop-loss dominated, and clustered
  around the March 11-14 rebound.
- Found order-block anchored shorts negative while pivot-anchored shorts were
  positive in both inspected SOL March rows.
- Changed `backtester compare-grid` to generate one `crypt_ensemble` signal
  frame per symbol/window and reuse it across `rrr` / `ttl` execution
  candidates.
- Kept deterministic grid report ordering and moved `--jobs` work units to
  independent windows after signal reuse.
- Added a focused test for one signal build across multiple execution
  candidates.
- Updated README and task docs for the new `compare-grid` signal-reuse path.

**ADRs:** none.

**Verification:** ruff check and format clean on changed report/test files;
targeted donor pytest `5 passed`; `compare-grid --help` verified; tiny SOL
smoke at `/tmp/crypt_compare_grid_precomputed_smoke/20260603_160558` completed
with one signal build, two candidate exports, and byte-identical `signals.csv`
files.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — SOL March execution grid

- Added `backtester compare-grid` for bounded execution-only `rrr` / `ttl`
  grid reports with `grid.csv`, `grid.md`, and per-candidate donor artifacts.
- Added `--jobs N` to `compare-grid` for process-level candidate/window
  parallelism.
- Backfilled missing local SOL OHLCV data via `crypt.backfill` so the SOL
  March 2025 H1 window can be reproduced locally.
- Ran the SOL March grid at
  `/tmp/crypt_execution_grid_sol_mar/20260603_153612`.
- Result: all 9 candidates remained negative; best was `rrr = 1.0`,
  `ttl = 30`, `total_return_pct = -6.15`, `profit_factor = 0.66`,
  max drawdown `-11.20`, 64 short-only trades.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/report/test
paths; targeted donor pytest `4 passed`; `compare-grid --help` verified; SOL
March grid completed and exported artifacts.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Parallel fixed-candidate windows

- Added `--jobs N` to `backtester compare-fixed` for process-level parallel
  execution of independent windows.
- Kept `--jobs 1` as the default serial path and preserved deterministic
  `windows.csv` / `windows.md` row order when workers finish out of order.
- Added duplicate window-label validation to prevent run artifact overwrites.
- Updated README fixed-candidate docs with the new `--jobs` option.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/report/test
paths; targeted donor pytest `3 passed`; `compare-fixed --help` shows
`--jobs`.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

## 2026-06-03 — Optimization acceleration planning

- Documented the safe path for speeding up donor H1 optimization: parallelize
  fixed-window/tiny-grid workloads first, then add precomputed signal reuse,
  then disk-backed signal caching, and only then guarded optimizer `--jobs`.
- Added P1 backlog items for `compare-fixed`/tiny-grid parallelization,
  disk-backed `crypt_ensemble` signal cache, guarded optimizer parallelism,
  and explicit precomputed-signal execution-only optimization.
- Recorded the key guardrail: broad full-history `--strategy-param-search`
  should not be parallelized before workers can share or reuse generated
  signal frames.

**ADRs:** none.

**Verification:** documentation-only update; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

## 2026-06-03 — Owner idea parking lot

- Added `docs/tasks/IDEAS.md` for owner ideas that should be remembered for
  later but not implemented without explicit approval.
- Recorded the first idea: cap oversized monthly backtest profits for
  calibration/report ranking while still preserving raw monthly returns in the
  report.
- Updated `AGENTS.md` so future agents read `IDEAS.md`, remind the owner about
  relevant ideas, and ask for approval before moving any idea into backlog,
  specs, or code.

**ADRs:** none.

**Verification:** documentation-only process update; no tests run.

**Files touched:** `AGENTS.md`, `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Fixed H1 candidate comparison

- Added `backtester compare-fixed`, a fixed-candidate comparison CLI that runs
  bounded H1 windows and exports `windows.csv`, `windows.md`, and donor
  per-window run artifacts.
- Added tests for window parsing and fixed-candidate summary aggregation.
- Ran candidate A (`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`) across SOL
  January/February/March 2025 and TON January/February 2025 at
  `/tmp/crypt_fixed_candidate_h1/20260603_134312`.
- Bounded result: positive on SOL January `+1.99%`, SOL February `+13.82%`,
  TON January `+1.19%`, and TON February `+2.76%`; failed SOL March at
  `-6.52%`.
- Recorded candidate A as worth a long owner-run diagnostic, not accepted
  calibration, and documented the full-history SOL/TON owner-run command.

**ADRs:** none.

**Verification:** ruff check and format clean on the changed CLI/report/test
paths; targeted donor pytest `2 passed`; bounded `compare-fixed` run completed
and exported artifacts.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-03 — Urgent profitability sprint handoff

- Recorded owner direction for the next 2-3 Codex sessions: prioritize a
  bounded profitable candidate and an owner-run long backtest command over
  broad architecture work.
- Added a top `IN_PROGRESS.md` handoff with the next-session order: fixed
  `rrr = 1.25` / `ttl = 36` comparisons, tiny execution-only grid only if
  needed, side-skew attribution, and a final unattended local run command.
- Added P0 backlog items for fixed-candidate H1 window comparison, candidate
  selection, minimal side-skew attribution, and owner-run long backtest
  preparation.
- Documented the 2026-06-03 full-history SOL H1 curiosity Optuna run as too
  expensive for remaining Codex time: trial 0 took about 1h48m and returned
  `total_return_pct = -9.47`, `max_drawdown = -24.75`, `total_trades = 482`.

**ADRs:** none.

**Verification:** documentation-only handoff; no code or tests changed.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Adjacent H1 optimizer diagnostics

- Inspected the SOL January H1 optimizer best-run artifacts and confirmed the
  `+2.46%` result is mixed-side and fragile: longs contributed `+304.88`,
  shorts `-58.48`.
- Ran the same bounded execution-only optimizer search on adjacent SOL
  February 2025 at
  `/tmp/crypt_donor_h1_mtf_optuna_sol_feb/20260603_104255`: best trial
  `rrr = 1.25`, `position_ttl_bars = 36`, `total_return_pct = 13.82`,
  `profit_factor = 5.40`, max drawdown `-1.90`, 53 short-only trades.
- Ran the same bounded search on TON January 2025 at
  `/tmp/crypt_donor_h1_mtf_optuna_ton_jan/20260603_104642`: best trial
  `rrr = 1.50`, `position_ttl_bars = 36`, `total_return_pct = 1.95`,
  `profit_factor = 1.12`, max drawdown `-5.51`, 86 short-only trades.
- Recorded that XPL was intentionally skipped for this pass because its H1
  history is shorter.
- Kept H1 setup geometry in diagnostic status; broader out-of-sample windows
  and fixed-candidate comparisons are required before strategy-param search.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor code/test paths;
targeted donor pytest `29 passed`; full donor pytest `102 passed` with 2
existing pandas warnings; SOL February and TON January bounded optimizer CLI
diagnostics completed and exported `best_run/` artifacts.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Operator-facing H1 optimizer CLI

- Added `backtester optimize`, a CLI wrapper around the existing donor
  `ParameterOptimizer` for bounded `crypt_ensemble` H1 tuning.
- The command loads bounded `crypt-parquet`, preserves strategy JSON params,
  exposes execution/risk search ranges, writes `trials.csv`,
  `best_trial.json`, the Optuna journal log, and donor `best_run/`
  diagnostics.
- Fixed fixed-risk handling in `ParameterOptimizer`; `risk_percent_range =
  None` now uses the configured fixed `risk_percent`.
- Added cached best-signal reuse for `best_run/` export so execution-only
  optimizer runs do not rerun `crypt_ensemble.generate()` after Optuna.
- Ran a bounded SOL H1 12-trial optimizer diagnostic at
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`: best tiny in-sample
  result was `rrr = 1.25`, `position_ttl_bars = 30`,
  `total_return_pct = 2.46`, `profit_factor = 1.14`, max drawdown `-5.7`,
  97 trades. This is diagnostic only, not accepted calibration.

**ADRs:** none.

**Verification:** ruff check and format clean on changed CLI/optimizer/test
files; targeted donor pytest `3 passed`; full donor pytest `102 passed` with 2
existing pandas warnings; bounded SOL H1 optimizer CLI diagnostic completed;
short cache smoke confirmed `best_run/` export does not show a second
`crypt_ensemble` progress build.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-03 — H1 optimizer speed path

- Extended the existing donor `ParameterOptimizer` instead of adding a second
  optimizer: baseline `strategy_params`, configurable `rrr` range/step,
  Optuna-controlled `position_ttl_bars`, preserved `risk_base_period`,
  optional daily/trading-window search, and optional strategy-param search.
- Added signal-frame caching inside `ParameterOptimizer`; execution-only
  `rrr`/`ttl` trials reuse the same generated `crypt_ensemble` signals.
- Added ADR-0022 and implemented H4 setup snapshots in H1 MTF mode. H4 setup
  verdicts are evaluated at the latest closed H4 setup time and reused across
  H1 trigger bars until the next H4 close.
- Added tests for setup snapshot invalidation and optimizer signal-cache reuse.
- Ran bounded SOL H1 Optuna speed check at
  `/tmp/crypt_donor_h1_mtf_optuna_speed_check`: first 745-bar signal build
  took about 226.9 seconds; the next two `rrr`/`ttl` trials completed in about
  0.05 seconds each from cache. Tiny diagnostic best was `rrr = 1.75`,
  `position_ttl_bars = 30`, `total_return_pct = 0.18`.

**ADRs:** 0022 (accepted).

**Verification:** ruff check and format clean on changed donor optimizer,
strategy, and tests; targeted donor pytest `28 passed`; full donor pytest
`101 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `CHANGELOG.md`.

---

## 2026-06-03 — Parity-safe H1 window cache

- Documented the `crypt_ensemble` performance optimization contract before
  code changes: reference path must remain available, and optimized paths must
  pass reference-vs-optimized parity before tuning.
- Added `optimized_windows` to donor `crypt_ensemble`. Default remains
  `false`; the H1 diagnostic strategy config opts in.
- Implemented a closed-window context cache for candle/extras selection only,
  preserving closed-candle and timestamp bounds without caching verdicts, SMC
  states, trigger decisions, or stops across bars.
- Added parity tests for cached context windows and H1 MTF strategy output
  across signal, stop, trigger, rationale, metadata, and strength columns.
- Reran bounded SOL H1 MTF smoke with optimized windows at
  `/tmp/crypt_donor_h1_mtf_smoke_optimized_windows/20260603_083245`: 745 H1
  bars, 98 trades, final capital 9947.0, `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`.
- Runtime improved from about 6 minutes 35 seconds to about 5 minutes
  3 seconds on the bounded January SOL slice. Further speedups remain behind a
  separate parity contract for verdict/SMC/event-age caching.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `25 passed`; full donor pytest `98 passed` with
3 existing pandas warnings; bounded optimized SOL H1 smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — H1 stop-distance cap diagnostic

- Added `max_sl_distance_atr` as an explicit donor `crypt_ensemble` strategy
  parameter with the existing `8 ATR` guard preserved as the default.
- Exposed `max_sl_distance_atr` through `suggest_params()` for future donor
  Optuna work.
- Set `max_sl_distance_atr = 4.0` in the H1 diagnostic strategy config.
- Added a focused unit test for neutralizing a structurally valid stop that is
  wider than an explicit cap.
- Updated README, MTF spec, and task tracking with the stop-distance cap
  contract.
- Reran bounded SOL H1 MTF smoke at
  `/tmp/crypt_donor_h1_mtf_smoke_h1_max4/20260602_195943`: 745 H1 signal rows,
  105 tradeable signals, 98 trades, final capital 9947.0,
  `total_return_pct = -0.53`, `profit_factor = 0.97`, max drawdown `-7.41`.
- Compared with the previous H1 stop-source smoke: TTL exits fell from 50.0%
  to 37.8%, and trade frequency fell from 6.27 to 3.89 trades/day. This is
  still a bounded SOL diagnostic, not full-history H1 acceptance.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `23 passed`; full donor pytest `96 passed` with
3 existing pandas warnings; bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — H1 structural stop-source selection

- Updated the MTF strategy spec with the H1-vs-H4 structural stop-source
  contract.
- Implemented H1 stop-source selection in donor `crypt_ensemble`: H4 remains
  the primary setup stop, while H1 execution mode can replace it with a valid,
  known, same-direction H1 structural stop only when it is closer by execution
  ATR distance.
- Added tests for using a closer H1 stop and keeping H4 when the H1 candidate
  is wider.
- Reran bounded SOL H1 MTF smoke at
  `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`: 745 H1
  signal rows, 159 tradeable signals, 153 tradeable signals with
  `sl_source_tf = 1h`, 158 trades, final capital 9058.19,
  `total_return_pct = -9.42`, `profit_factor = 0.66`, max drawdown `-10.44`.
- H1 stop-source diagnostics are now contract-visible, but the result is still
  diagnostic only: trade frequency rose to 6.27 trades/day and setup geometry
  plus performance remain open before full-history H1 acceptance.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `22 passed`; full donor pytest `95 passed` with
3 existing pandas warnings; bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — MTF no-lookahead entry timing

- Added donor `crypt_ensemble` tests for D1 forming-candle exclusion,
  future-known H4 structural stop-anchor rejection, and H1 signal timing
  through `ExecutionSim`.
- Fixed donor `crypt_ensemble` to leave `entry_price` empty so execution
  enters at the next execution-bar open after a closed signal candle, instead
  of using the signal candle close as a current-bar custom entry.
- Updated README, MTF spec, and task tracking with the next-open entry
  contract.
- Reran bounded SOL H1 MTF smoke after the fix at
  `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`: 745 H1
  signal rows, 35 short trades, final capital 9357.25 from 10000,
  `total_return_pct = -6.43`, `profit_factor = 0.04`, max drawdown `-6.27`.
- Sample trades confirm next-open execution: first `signal_time` is
  `2025-01-03 13:00:00+00:00`, first `entry_time` is
  `2025-01-03 14:00:00+00:00`.
- H1 stop-source acceptance remains open: all 35 trades still used H4
  order-block stops.

**ADRs:** none.

**Verification:** ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `20 passed`; full donor pytest `93 passed`; full
suite still has 3 existing pandas warnings. Bounded SOL H1 MTF smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt-parquet` bounded smoke range

- Added inclusive `--from` / `--to` options to the donor `backtester run` CLI
  for `crypt-parquet` data.
- `CryptParquetDataLoader` now parses date bounds as UTC, limits
  `StrategyData.primary`/output rows by the requested range, and preserves
  pre-start candle history in `StrategyData.candles` up to `--to` for H4/D1
  warmup.
- Added tests for CLI propagation, inclusive primary filtering, and context
  warmup retention.
- Updated README, MTF smoke spec, and task tracking with the bounded H1 smoke
  command.
- Reran bounded SOL H1 MTF smoke locally after owner restored Parquet data:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded/20260602_191541`.
- Smoke produced 745 H1 signal rows, 35 short trades, final capital 9340.69
  from 10000, `total_return_pct = -6.59`, `profit_factor = 0.05`, max drawdown
  `-6.45`, and full signal/trade diagnostics. This is diagnostic only; full
  H1 acceptance remains open behind no-lookahead expansion, H1 stop-source
  behavior, setup geometry, and performance profiling.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`26 passed`; full donor pytest `90 passed`; both with 3 existing pandas
warnings. Bounded SOL H1 smoke completed.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Vend `backtester/` into crypt monorepo (docs)

- Owner decision: fold the donor package into the `crypt` git repository
  instead of keeping a nested `backtester/.git` or submodule.
- Added ADR-0021 with one-time migration steps (`rm -rf backtester/.git`,
  root `git add backtester/`, gitlink cleanup).
- Updated `README.md` layout, `docs/backtest.md`, `docs/backtester_migration.md`,
  and ADR-0018 cross-references.
- Recorded follow-up: root CI does not yet run donor `pytest` (BACKLOG P2).

**ADRs:** 0021 (accepted).

**Verification:** docs-only; no tests run. Owner still removes `backtester/.git`
and commits the tree from the `crypt` root.

**Files touched:** `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — First MTF `crypt_ensemble` implementation slice

- Added donor `crypt-parquet` `primary_timeframe` support and CLI
  `--primary-timeframe`, preserving H4 as the default primary frame.
- Added timeframe-role config to `crypt_ensemble` (`context`, `setup`,
  `trigger`, `execution`) and a first H1 MTF path: D1 context filter, H4 setup
  verdict, H1 candle-confirm trigger/execution, and MTF diagnostics.
- Added `backtester/strategies/crypt_ensemble_h1.json` with H1 execution,
  `ttl = 24`, `rrr = 1.5`, and monthly risk base.
- Added tests for H1 primary loader semantics, CLI propagation, H1 execution
  index/diagnostics, H4 forming-candle exclusion, and D1 opposite-context
  blocking.
- Attempted the SOL H1 MTF smoke; it loaded 21517 H1 bars and started replay,
  but ended before export and produced no artifact. Full H1 smoke remains open
  behind a range limiter or performance pass.
- Updated README, migration docs, MTF spec, and task tracking.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`41 passed`; full donor pytest `88 passed`, both with 3 existing pandas
warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Unified MTF `crypt_ensemble` handoff

- Added `docs/crypt_ensemble_mtf.md` as the next implementation spec for a
  generic multi-timeframe strategy contract.
- Captured the owner-requested top-down model: D1 context, H4 setup, H1
  trigger/execution.
- Required extensibility for future 15m triggers through timeframe-role config
  (`context`, `setup`, `trigger`, `execution`) instead of special-case H1 code.
- Documented no-lookahead rules, data contract changes, first H1 slice,
  diagnostics, required tests, smoke command, and future 15m path.
- Updated task tracking so the next agent starts from the MTF spec.

**ADRs:** none.

**Verification:** docs-only; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor TTL exit diagnostics

- Added `trade_diagnostics.csv` export to donor `ResultsAnalyzer` for runs
  with trades: exit reasons, side/exit counts, PnL by side/reason, holding
  duration, trades per day, `sl_distance_atr` by exit reason, and anchor
  distance by stop type.
- Generated the diagnostic report for the existing structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827/trade_diagnostics.csv`.
- Diagnosed TTL-heavy exits as setup geometry rather than an execution bug:
  1496/1672 trades (`89.47%`) closed by `ttl_expired`; `ttl = 6` H4 bars is a
  24-hour window, while TTL-expired trades had median `sl_distance_atr = 3.985`,
  making the `rrr = 2` TP roughly 8 ATR away.
- Checked lower-timeframe feasibility: SOL and TON have long H1 Parquet
  history, but the strategy/engine contracts are H4-semantic and need a
  separate H1 spec/ADR before code changes.
- Updated README, migration docs, and task tracking with the new artifact and
  next steps.

**ADRs:** none.

**Verification:** ruff clean on changed analyzer/test files; targeted donor
pytest `6 passed`.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Structural SMC stop-loss for donor `crypt_ensemble`

- Replaced the donor `crypt_ensemble` default ATR-only stop with a structural
  SMC stop hierarchy: active order block, fresh liquidity sweep, confirmed
  pivot, then optional explicit ATR fallback.
- Added `sl_atr_buffer_mult` and `allow_atr_sl_fallback`; the default strategy
  JSON disables ATR fallback and neutralizes BUY/SELL verdicts without a valid
  structural stop.
- Added stop diagnostics to strategy output: `sl_anchor_type`,
  `sl_anchor_level`, `sl_anchor_known_at`, and `sl_distance_atr`.
- Added synthetic tests for long/short OB stops, sweep stops, pivot fallback,
  excessive-distance/no-anchor neutralization, and no-lookahead anchor timing.
- Reviewed owner-completed structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827`: 1672 trades,
  final capital 6683.68, `total_return_pct = -33.16`, `profit_factor = 0.84`,
  max drawdown `-35.38`. Structural SL removed 120 trades versus the previous
  no-structural smoke but did not improve aggregate metrics; long-side trades
  remain the main drag.
- Updated README, structural SL spec, migration docs, and task tracking. Next
  step is either focused order-block stop-quality analysis or minimal donor
  Optuna with out-of-sample caution.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`14 passed`; full donor pytest `82 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Structural SL handoff before donor optimizer

- Removed the newly added donor walk-forward optimizer code, CLI command, and
  tests; `folds` is not part of the first donor optimizer step.
- Restored donor `crypt_ensemble` optimizer surface to the existing
  `sl_atr_mult` and `min_confidence` suggestions; weight optimization remains
  a future task after structural stop-loss.
- Added `docs/crypt_ensemble_structural_sl.md`: structural stop-loss spec
  using SMC order blocks, liquidity sweeps, pivots, and ATR buffer.
- Added explicit donor safety rule: `backtester/` is high-risk source-of-truth
  code; prefer adapting `crypt_ensemble` over rewriting donor internals.
- Updated task tracking so structural SL is the next P0 before optimizer or
  backtest interpretation.

**ADRs:** none.

**Verification:** changed-file ruff clean. Targeted donor pytest should be
rerun after structural SL implementation.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — ADR-0020 removes donor default confidence gate

- Recorded the owner correction in ADR-0020: `ALERT_CONFIDENCE_THRESHOLD = 75`
  was arbitrary and must not be rationalized as a calibrated threshold.
- Removed default `min_confidence = 75` from donor `crypt_ensemble`; BUY/SELL
  verdicts are tradeable by default, while explicit `min_confidence` remains
  available for diagnostics or Optuna.
- Replaced the hard-coded `confidence_ge_75` signal diagnostic with confidence
  quantiles.
- Reviewed owner-provided SOL smoke at `/tmp/crypt_donor_smoke/20260602_132627`:
  1792 trades, final capital 6694.69, `total_return_pct = -33.05`,
  `profit_factor = 0.88`; long-side performance remains the main issue.
- Updated task handoff so the next step is donor Optuna, not further
  investigation of the number `75`.

**ADRs:** ADR-0020; ADR-0011 status updated.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`12 passed`; full donor pytest `75 passed` with 3 existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Threshold-correct donor smoke produced no live-threshold trades

- Added donor no-trade diagnostics: `signals.csv`, `signal_diagnostics.csv`,
  and non-empty `metrics.csv` now export even when no trades are opened.
- Reran SOL donor smoke with `min_confidence = 75` at
  `/tmp/crypt_donor_smoke/20260602_122510`.
- Confirmed 0 trades is expected under current confidence semantics:
  1798 directional verdicts existed, but max confidence was 52 and no row
  reached the live alert threshold of 75.
- Added follow-ups to audit confidence scale vs live threshold and add a cheap
  signal diagnostics report before Optuna.

**ADRs:** none.

**Verification:** ruff clean on changed donor files; full donor pytest
`74 passed` with 3 existing pandas warnings; SOL donor smoke completed in
about 15 minutes.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt_ensemble` confidence threshold

- Reviewed the owner-rerun monthly-risk SOL donor smoke at
  `/tmp/crypt_donor_smoke/20260602_104522`.
- Confirmed metadata export is present, but diagnosed the run as trading every
  directional verdict: all exported trades had `confidence <= 55`, below the
  live alert threshold of 75.
- Added `min_confidence` to `crypt_ensemble` params and Optuna suggestions.
  Default JSON value is `75`.
- Low-confidence BUY/SELL verdicts now preserve verdict metadata but emit
  donor `signal = 0`.

**ADRs:** none.

**Verification:** ruff clean on changed strategy/test files; targeted donor
pytest `6 passed` with one existing pandas warning.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor risk-base sizing and trade attribution export

- Reviewed the owner-completed SOL donor smoke and confirmed it was a plain
  `backtester run`, not an optimizer run.
- Recorded old-mode smoke metrics: 1792 trades, final capital 6548.74 from
  10000 initial capital, `total_return_pct = -34.51`, `profit_factor = 0.88`;
  long trades were materially negative while shorts were slightly positive.
- Fixed donor execution export so trade rows retain `crypt_ensemble`
  attribution metadata: `signal_time`, confidence, score, regime, decision,
  rationale, and per-engine strengths.
- Added `risk_base_period` sizing modes (`trade`, `weekly`, `monthly`,
  `backtest`) and exported `risk_base_capital` per trade.
- Set `crypt_ensemble` to monthly risk-base sizing for donor M2 smokes.

**ADRs:** ADR-0019.

**Verification:** ruff clean on changed donor files; targeted donor pytest
`39 passed`; full donor pytest `71 passed` with existing pandas warnings.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor `crypt_ensemble` engine wiring

- Wired donor `crypt_ensemble` to run the existing volatility, regime,
  directional engines, and aggregator over `StrategyData`.
- Added closed-candle H4 replay semantics in the donor strategy: each row is
  evaluated at `open_time + 4h`, with H4/H1/D1 contexts filtered to closed
  candles only.
- Added donor output metadata: `entry_price`, ATR-based `sl_price`,
  confidence, score, regime, decision, rationale, and per-engine strengths.
- Added per-bar progress for long `crypt_ensemble` runs and enabled it in the
  strategy JSON.
- Fixed project-Parquet `open_time` ambiguity when it is both index name and
  column label.
- Added donor tests for BUY/SELL/HOLD mapping, ATR stop output, missing
  optional frames, and `open_time`-named indexes.

**ADRs:** ADR-0018.

**Verification:** `PYTHONPATH=src:../src uv run --extra dev pytest tests -q`
in `backtester/` → 67 passed; ruff clean on changed donor files. SOL
`crypt-parquet` smoke loaded 5545 H4 bars and showed progress, but the full
run was stopped before completion due duration.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor backtester Parquet loaders and neutral ensemble skeleton

- Added donor `StrategyData` and adapted `Backtester`/CLI plumbing so old
  strategies still receive `pd.DataFrame` while richer strategies can receive
  project-aware data.
- Added donor `parquet` and `crypt-parquet` data sources, including support
  for project-style `open_time` + `o/h/l/c/volume` Parquet files.
- Registered `crypt_ensemble` with a neutral/no-trade skeleton and strategy
  JSON config.
- Added donor tests for loader modes, CLI data-source selection, and the
  neutral `crypt_ensemble` skeleton.
- Updated README and migration/task docs with the experimental donor command.

**ADRs:** ADR-0018.

**Verification:** `PYTHONPATH=src:../src uv run --extra dev pytest tests -q`
in `backtester/` → 65 passed; ruff clean on changed donor files; SOL
`parquet` and `crypt-parquet` smoke commands loaded 5545 H4 bars and wrote
no-trades reports.

**Files touched:** `backtester/`, `docs/`, `README.md`, `CHANGELOG.md`.

---

## 2026-06-02 — Donor backtester migration plan

Owner redirected M2 architecture toward the donor `backtester/` package:
minimal additive changes, keep Parquet, keep one symbol per run, register the
existing ensemble as a donor strategy, and defer deletion of
`src/crypt/backtest/` until a donor-backed smoke run works.

- Added ADR-0018 accepting donor backtester as the future canonical M2
  strategy/backtester architecture.
- Added `docs/backtester_migration.md` with the implementation handoff:
  `StrategyData`, `parquet`, `crypt-parquet`, `crypt_ensemble`, smoke test,
  and later Optuna phase.
- Updated task tracking with P0/P1 migration steps for the next agent.

**ADRs:** ADR-0018.

**Verification:** docs-only; no tests run.

**Files touched:** `docs/`, `CHANGELOG.md`.

---

## 2026-06-01 — M2 report reviewed; OHLCV calibration rejected

Owner reran the SOL/TON OHLCV-only backtest after the multi-symbol execution
fix. The replay completed, but the optimizer sanity guard fired on the first
two out-of-sample folds, so generated weights are not promoted.

- Added ADR-0014 documenting the rejected calibration result and the decision
  to keep alerts marked uncalibrated.
- Fixed `weights_to_yaml()` so candidate files containing numpy scalar weights
  are emitted as safe, portable YAML instead of Python object tags.
- Added a regression test for safe YAML serialization.
- Added follow-ups for guarded-report artifact semantics and weak long-side
  signals.

**ADRs:** ADR-0014.

**Verification:** `uv run pytest -q` passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`,
`reports/backtest_2026-06/`.

---

## 2026-06-01 — Hotfix: multi-symbol backtest execution uses symbol-local next bars

Owner backtest log showed impossible SL validation lines where prices from
different instruments were paired (for example SOL entry levels with TON stop
prices). Root cause: `ExecutionSim` used the next global row in a combined
multi-symbol DataFrame for next-open entries and TTL exits.

- `ExecutionSim.run()` now computes `next_open`, `next_time`, and bar number
  per symbol before the simulation loop.
- Backtest simulation frames now include explicit `entry_price = close` from
  the closed signal candle.
- Cleaned up pandas `pct_change(fill_method=None)` and timezone-aware UTC
  generation timestamps for warnings seen in the same run.
- Added a regression test for same-timestamp SOL/TON rows.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 124 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`.

---

## 2026-06-01 — Backtest optimizer recomputes candidate scores

- Fixed M2 calibration blocker: `BacktestRecorder` now persists
  `strength_<engine>` columns for scoring engines.
- Updated `optimizer._apply_weights` to recompute score/decision from replayed
  strengths under candidate weights instead of reusing the old final `score`.
- Added focused tests proving candidate weights change score, decision, and
  objective.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 119 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/backtest/`, `tests/backtest/`, `docs/`.

---

## 2026-06-01 — SMC liquidity engine

- Extended SMC core with `SMCLiquidityLevel`, `SMCLiquiditySweep`, ATR-scaled
  equal high/low detection, swing liquidity levels, wick-distance metadata,
  and same-candle ambiguity flags.
- Added `SMCLiquidityEngine`: reversal signal from fresh equal/swing high-low
  sweeps with rejection bonus and neutral missing-data/ambiguous paths.
- Wired `smc_liquidity` into live orchestration, replay, aggregator scoring,
  placeholder weights, optimizer engine lists, and backtest docs.
- Added tests for equal-level confirmation timing, sweep timing, ambiguous
  double sweeps, bullish/bearish liquidity output, and missing H4 data.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 116 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/runtime/`, `src/crypt/backtest/`, `src/crypt/aggregator/`,
`tests/`, `config/`, `docs/`.

---

## 2026-06-01 — SMC order-block engine

- Extended SMC core with `SMCOrderBlock`, order-block extraction from
  pivot-to-break structure windows, high-volatility candle parsing, and
  mitigation state.
- Added `SMCOrderBlocksEngine`: active zone retest signal with structure-bias
  confluence, rejection bonus, ATR width filter, and neutral missing-data path.
- Wired `smc_order_blocks` into live orchestration, replay, aggregator scoring,
  placeholder weights, and optimizer engine lists.
- Added tests for order-block creation, mitigation, retest signal, no retest
  before the closed candle, and missing H4 data.
- Added a P0 backlog item for optimizer score recomputation before trusting
  M2 calibration output.

**ADRs:** none.

**Verification:** `uv run pytest -q` → 109 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/runtime/`, `src/crypt/backtest/`, `src/crypt/aggregator/`,
`tests/`, `config/`, `docs/`.

---

## 2026-06-01 — ADR-0017: OHLCV-only M2 + first SMC structure engine

Owner direction: stop blocking M2 on paid/short derivatives history and first
prove value with free OKX candles.

- Added ADR-0017: primary M2 calibration is OHLCV-only; `derivatives` weight
  is `0` until deep OI/LS history is separately proven.
- Added SMC specs: `smc_core`, `smc_structure`, `smc_order_blocks`,
  `smc_liquidity`.
- Implemented first SMC core slice in `src/crypt/structure/smc.py`:
  confirmed pivots + BOS/CHoCH with explicit `known_at` timing.
- Added `SMCStructureEngine` and wired it into live orchestration and replay.
- Updated `config/weights.yaml`, aggregator scoring engines, backtest
  preconditions, README/backfill/backtest docs for OHLCV-only M2.
- Added no-lookahead tests for SMC pivot/event timing and engine output.

**ADRs:** 0017.

**Verification:** `uv run pytest` → 103 passed; `uv run ruff check src tests`
clean; `uv run mypy src` clean.

**Files touched:** `docs/`, `src/crypt/structure/`, `src/crypt/engines/`,
`src/crypt/aggregator/`, `src/crypt/backtest/`, `src/crypt/runtime/`,
`tests/`, `config/`, `README.md`.

---

## 2026-06-01 — Hotfix: OI endpoint parameter `instId` (not `ccy`)

OKX `/rubik/stat/contracts/open-interest-history` requires `instId`
(e.g. `SOL-USDT-SWAP`), not `ccy` (`SOL`). ADR-0016 had the wrong parameter.
Also switched stored field from `row[1]` (contracts) to `row[3]` (oiUsd) for
USD-denominated OI, consistent with the prior `openInterestValue` field.

- `src/crypt/exchange/okx.py` — `fetch_oi_history` and `fetch_oi_history_page`:
  `ccy=ccy` → `instId=symbol`, `row[1]` → `row[3]` (oiUsd).

Discovered on first live backfill run (error code `50014 instId can't be empty`).

---

## 2026-06-01 — ADR-0016 code implementation: drop funding, fix OI endpoint

Session 6. All code changes from ADR-0016 implemented; 97 tests pass,
mypy 0 errors, ruff clean.

### Code changes

- `src/crypt/exchange/okx.py` — `fetch_oi_history` and `fetch_oi_history_page`
  replaced `ccxt`'s `fetch_open_interest_history` (9-day history) with direct
  call to `publicGetRubikStatContractsOpenInterestHistory` (data to Feb 2024).
- `src/crypt/engines/derivatives.py` — `_funding_signal` removed; weights
  rebalanced to OI 0.67 / LS 0.33; graceful degradation reworked.
- `src/crypt/models.py` — `EvaluationContext.funding` field removed.
- `src/crypt/data/context.py` — `_FUNDING_LIMIT`, `_df_to_funding`, funding
  loading removed.
- `src/crypt/data/store.py` — `save_funding`, `load_funding`, `_funding_path`,
  `_FUNDING_COLS` removed.
- `src/crypt/data/ingestor.py` — `_ingest_funding` removed.
- `src/crypt/backfill/__main__.py` — `_backfill_funding`, `funding` data-type
  removed; default `--data-types` changed to `ohlcv,oi,ls_ratio`.
- `src/crypt/backtest/replay.py` — `load_funding`, `_FUNDING_LIMIT` removed;
  `ReplayContextBuilder` updated.
- `src/crypt/backtest/__main__.py` — funding precondition check removed;
  `_build_funding_model` simplified to always return `ZeroFundingModel`;
  `_FUNDING_WARMUP_DAYS` constant removed.
- `tests/engines/test_derivatives.py` — rewritten without funding fixtures;
  6 OI+LS-only tests.
- `tests/backtest/test_no_lookahead.py` — funding fixture and
  `test_funding_boundary_excluded` removed; OI guard test retained.
- `tests/decision/test_filters.py`, `tests/conftest.py` — `funding` arg
  removed from `make_ctx`; `FundingSnapshot` import removed.
- `.env.example` — Coinglass env vars replaced with tombstone comment.

### Docs (unchanged from session 5 — already updated by prior agent)

`docs/backfill.md`, `docs/engines/derivatives.md`, `docs/decisions/0016-*`.

---

## 2026-06-01 — Drop funding; fix OI endpoint; retire Coinglass plan (ADR-0016)

**Decisions made in owner-agent design session.**

### Funding sub-signal dropped from `DerivativesEngine`

OKX perpetual swap contracts run on 1 h / 2 h / 4 h / 8 h funding settlement
cycles (e.g. TON-USDT-SWAP moved to 4 h in April 2025). The engine's
`_FUNDING_LIMIT = 200` window assumed a fixed 8 h cycle; a 4 h contract
silently halves the effective z-score window, producing miscalibrated weights
with no error signal. OKX also retains only ~3 months of funding history —
insufficient for M2. The sub-signal is removed; `DerivativesEngine` now runs
on OI momentum (0.67) + L/S ratio (0.33).

### OI endpoint corrected

`ccxt`'s `fetch_open_interest_history` calls
`/rubik/stat/contracts/open-interest-volume` (only ~9 days of history).
The correct endpoint is `/rubik/stat/contracts/open-interest-history`, which
OKX retains to February 2024. `OKXClient.fetch_oi_history_page` must be
updated to call `publicGetRubikStatContractsOpenInterestHistory` directly.

### Coinglass plan retired (ADR-0015 superseded)

With funding dropped and OI/LS both available from OKX native deep endpoints,
no remaining data gap requires a third-party vendor. `CoinglassClient` was
never implemented; no rollback needed.

### Product vision clarified

Session discussion captured in `BACKLOG.md`:
- Output goal: BUY/SELL + entry price + SL (ATR-based) + TP (2:1 R:R fixed).
- New engine categories planned: structural (S/R, VWAP, Fibonacci), volume
  (CVD, OBV), price action (Order Blocks, FVG, BOS/ChoCH).
- Engine = "alpha factor / signal generator", not a complete strategy.

**ADRs:** 0016 (new). 0015 (superseded).

**Docs updated:**

- `docs/decisions/0016-drop-funding-fix-oi-endpoint.md` — new ADR (accepted).
- `docs/decisions/0015-coinglass-historical-backfill.md` — status → superseded.
- `docs/engines/derivatives.md` — spec updated (no-funding design, new weights).
- `docs/backfill.md` — Coinglass section removed; OI endpoint table updated.
- `docs/tasks/IN_PROGRESS.md` — next steps rewritten for OI fix + engine cleanup.
- `docs/tasks/BACKLOG.md` — Coinglass items removed; product vision + new engine
  categories added.

**Code not yet written.** Next agent implements changes in `IN_PROGRESS.md`.

---

## 2026-05-29 — Coinglass backfill: spec + ADR (implementation pending)

Owner approved Coinglass as a read-only backfill source for deep
derivatives history (funding, OI, LS ratio, taker volume) where OKX
Rubik endpoints retain only ~9–90 days.

**Docs added/updated:**

- `docs/backfill.md` — full backfill contract (OKX + Coinglass sources,
  CLI `--source`, endpoint mapping, tier limits, M2 workflow).
- `docs/decisions/0015-coinglass-historical-backfill.md` — ADR (accepted).
- `docs/backtest.md` §14, §16 — cross-refs and provenance note.
- `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — implementation
  checklist.

**Code not yet written.** Next agent implements `CoinglassClient` and
`--source coinglass|auto` per `docs/backfill.md` §8.

**ADRs:** 0015.

---

## 2026-05-29 — Backfill: fix OKX history-wall performance bug

**Problem:** Running `python -m crypt.backfill --from 2024-01-01` for
ls_ratio / taker_vol / OI triggered OKX error `50030 "Illegal time range"`
for every historical window (OKX Rubik endpoints keep only ~30 days of
ls_ratio/taker_vol, ~9 days of OI, ~90 days of funding). Each failed window
was retried 5× with exponential backoff (~27 s/window), making the full
ls_ratio pass take an estimated ~150 hours for a 2-year range.

**Fixes:**

- `src/crypt/utils/retry.py` — added `no_retry_on` predicate parameter.
  When the predicate returns True the exception is re-raised immediately
  (no sleep). Permanent errors like `50030` should never consume backoff.
- `src/crypt/exchange/okx.py` — added `_is_okx_history_limit` predicate
  (matches `50030` in error string); wired into `fetch_oi_history_page`,
  `fetch_ls_ratio_range`, `fetch_taker_volume_range`.
- `src/crypt/backfill/__main__.py` — `_backfill_oi` and `_backfill_rubik`
  now track consecutive zero-data windows. After `_MAX_CONSECUTIVE_EMPTY=3`
  consecutive empties the cursor jumps forward `_HISTORY_SKIP_MS=90 days`,
  quickly landing on the edge of available OKX history instead of grinding
  through the full date range.

**Note on data availability:** OHLCV goes back 2+ years on OKX. All other
endpoints have hard limits imposed by OKX; no amount of retrying will
recover older data. What can be backfilled today per endpoint:
- funding: ~90 days
- ls_ratio / taker_vol: ~31 days
- OI: ~9 days

**Re-run guidance:** re-running is idempotent (ParquetStore upserts). To
skip already-fetched types use `--data-types oi,ls_ratio` etc.

---

## 2026-05-29 — M2 backtest harness: full pipeline steps 4–11

Completed the M2 backtest harness. All pipeline components are implemented,
typed, tested (97 tests, 0 mypy errors, ruff clean).

### New modules

- `src/crypt/backtest/labels.py` — forward-label loader (§6). Computes
  `return_h4/h24/h96`, `mae`, `mfe`, `hit_h4/h24/h96` for each verdict.
  Uses pandas Series reindex with UTC-aware DatetimeIndex.
- `src/crypt/backtest/metrics.py` — metrics engine adapted from
  `backtester/src/backtester/results_analyzer.py` with all §18.4 fixes:
  - `build_equity_curve`: removed `drop_duplicates(subset="exit_time")`; sorted by
    `(exit_time, entry_time)` to handle multi-symbol same-tick exits.
  - `compute_sharpe_ratio`: warning emitted when n_monthly_samples < 6;
    trade-level Sharpe added as complement.
  - `compute_bootstrap_ci`: 95% CI for any scalar metric (1000 resamples).
  - `compute_buy_and_hold`, `compute_random_direction_baseline`: baselines (§11).
  - `generate_metrics`: full metrics dict including hit rates and bootstrap CI.
- `src/crypt/backtest/walkforward.py` — expanding-window walk-forward CV (§8).
  `FoldSpec`, `generate_folds`, `slice_verdicts`, `slice_trades`. Hard guarantee:
  no test-slice timestamp ever in the train slice.
- `src/crypt/backtest/optimizer.py` — weight optimiser (§9). Grid search over
  weight triples × threshold grid (all regimes). Coordinate descent refinement.
  Objective: `mean(pnl_net) - 0.5*std(pnl_net)`. Sanity guards (§9.4).
  `aggregate_weights_across_folds`: median weights + max thresholds (§13).
- `src/crypt/backtest/report.py` — static HTML report generator (§12). Embeds
  matplotlib equity curves, monthly-return bar charts, metrics tables, exit
  distribution, long/short breakdown, baselines, weights YAML. No server needed.
- `src/crypt/backtest/__main__.py` — full CLI entry point (§3, §5). Implements:
  data precondition checks (§4), H4 replay loop with `ReplayContextBuilder`,
  forward labels, `ExecutionSim` wiring with per-symbol `ParquetFundingModel`,
  walk-forward folds, weight optimisation, HTML report generation.

### Tests

- `tests/backtest/test_labels.py` — 8 tests: label computation, monotone-up
  price hit rate, HOLD→NaN hits, drop-tail behaviour, incomplete-window drop,
  MAE/MFE direction.
- `tests/backtest/test_walkforward.py` — 8 tests: fold count, no-overlap
  guarantee, expanding train window, regression test on synthetic 1-year dataset.
- `tests/backtest/test_metrics.py` — 12 tests: basic metrics, equity-curve
  §18.4 fix (duplicate exit_time), Sharpe warning, bootstrap CI, buy-and-hold,
  generate_metrics integration.

### Dependencies

- `matplotlib>=3.8` added to runtime deps (for HTML report charts).

Stats: 97 tests (was 67); mypy 0 errors (12 backtest files); ruff clean.

ADRs introduced: none (implementation follows previously-decided contracts).

---

## 2026-05-29 — M2 backtest harness: backfill CLI + replay core (steps 1–3)

Implemented the first three steps of the M2 backtest harness spec
(`docs/backtest.md`). All new code passes mypy strict (43 files, 0 errors),
ruff clean, and 67/67 tests.

### New modules

- `src/crypt/backfill/__init__.py`, `__main__.py` — OKX backfill CLI.
  Supports OHLCV, funding, OI, LS ratio, taker volume. Paginated, resume-safe,
  rate-limited, tqdm progress. Usage:
  `uv run python -m crypt.backfill --symbol SOL-USDT-SWAP --from 2023-01-01 --to 2026-05-01`
- `src/crypt/backtest/replay.py` — `ReplayParquetStore` (time-fence at
  `tick_time`) and `ReplayContextBuilder` (drop-in for live `ContextBuilder`).
- `src/crypt/backtest/fee_model.py` — ported `FeeModel` / `StaticPercentFeeModel`
  (maker/taker asymmetry: TP exits use maker fee, SL/TTL use taker fee).
- `src/crypt/backtest/risk_model.py` — ported `RiskModel` / `BasicRiskModel`
  (ATR-distance position sizer).
- `src/crypt/backtest/execution_sim.py` — ported `ExecutionSim` with all §18.4 fixes:
  - 🔴 `FundingRateModel` interface + `ZeroFundingModel` + `ParquetFundingModel`
    (charges `position_value * rate * 0.5` per H4 bar).
  - 🔴 Multi-symbol capital pool: single sim instance, `symbol` column in df,
    positions per symbol, shared capital.
  - 🟡 SL gap-adjusted fill: `exit_price = min/max(sl_price, bar_open)` for gaps;
    `--sl-pessimism-pct` flag.
  - 🟡 `exit_time` off-by-one fixed: TP/SL use `bar_time`, TTL uses `next_time`.
- `src/crypt/backtest/recorder.py` — `BacktestRecorder` (verdict → Parquet sink).
- `src/crypt/backtest/__init__.py` — module-level exports.

### Modified

- `src/crypt/exchange/okx.py` — pagination methods: `fetch_ohlcv_page`,
  `fetch_funding_history_page`, `fetch_oi_history_page`, `fetch_ls_ratio_range`,
  `fetch_taker_volume_range`; `fetch_ohlcv` gains optional `since_ms` param.
- `pyproject.toml` — `tqdm>=4.66` runtime dep; `tqdm.*` mypy override.

### Tests

- `tests/backtest/__init__.py` — new package init.
- `tests/backtest/test_no_lookahead.py` — 8 tests for look-ahead guard
  (guard excludes future data; naïve builder leaks it — proof test is valid).

Stats: 67 tests (was 59); mypy 0 errors (43 files); ruff clean.

ADRs introduced: none.

---

## 2026-05-29 — Post-M1 run: P0 quality gates, post-mortem, stdlib name fix

M1 14-day run completed successfully (255 verdicts, 0 errors, 0 alerts). All P0
post-run work shipped in this session.

### Post-mortem

- `docs/post_mortems/2026-05-29-m1-run-summary.md` — full 14-day run analysis:
  tick completeness, decision distribution, regime breakdown, key observations
  (zero alerts, TON BUY streak at conf 50%, XPL bootstrapping behaviour).

### P0 quality gates (all 5 shipped)

- **GitHub Actions CI** — `.github/workflows/ci.yml`: ruff lint, ruff format,
  mypy strict, pytest, uv lock check, gitleaks secret scan.
- **Pre-commit hooks** — `.pre-commit-config.yaml`: ruff (with auto-fix) +
  mypy. README "Developer setup" section added.
- **`[UNCALIBRATED]` marker** — `Settings.uncalibrated: bool = True` added to
  `config.py`; `TelegramSink._format_message` now appends `⚠️ [UNCALIBRATED]`
  to the alert title when flag is True; wired through `Orchestrator._build_sinks`.
  Unit tests in `tests/sinks/test_telegram.py` (8 tests).
- **Closed-candle invariant** — `OKXClient.fetch_ohlcv` now uses time-based
  `closed` determination (bar_close + 5s safety buffer). `Ingestor._ingest_ohlcv`
  pre-filters to closed candles before `save_candles`. `ParquetStore.save_candles`
  raises `ValueError` on any non-closed candle. Tests in
  `tests/data/test_store_closed_invariant.py` (4 tests).
- **Critical-inputs guard refactor** — `Signal.critical_missing: list[str]`
  field added. `BaseEngine.critical_inputs: ClassVar[list[str]] = []` declared;
  TrendEngine, MeanRevEngine, VolatilityEngine, RegimeEngine declare
  `critical_inputs = ["candles[H4]"]`; DerivativesEngine keeps `[]`.
  `DecisionFilter._has_critical_missing` now reads `sig.critical_missing`
  instead of substring-matching `"candles[H4]"` in `inputs_missing`. New tests
  in `tests/decision/test_filters.py` (+5 tests).

### `crypt` stdlib name conflict fix (ADR-0013)

- `pyproject.toml` — `[tool.pytest.ini_options]` gets `pythonpath = ["src"]`;
  `uv run pytest` now works out of the box without `PYTHONPATH=src`.
- `docs/decisions/0013-crypt-stdlib-name-conflict.md` — ADR documenting root
  cause, fixes applied, agent instructions, what was deliberately NOT done.
- `docs/deploy/railway.md` — troubleshooting table updated with ADR-0013 link.

### Stats

- Tests: 59 passed (was 42); mypy 0 errors (36 files); ruff clean.
- New files: 8 (`ci.yml`, `.pre-commit-config.yaml`, post-mortem, ADR-0013,
  `test_telegram.py`, `test_store_closed_invariant.py`, `tests/sinks/__init__.py`,
  `tests/data/__init__.py`).
- Modified files: `config.py`, `sinks/telegram.py`, `runtime/orchestrator.py`,
  `exchange/okx.py`, `data/store.py`, `data/ingestor.py`, `models.py`,
  `engines/base.py`, `engines/trend.py`, `engines/meanrev.py`,
  `engines/volatility.py`, `engines/regime.py`, `decision/filters.py`,
  `pyproject.toml`, `README.md`, `docs/deploy/railway.md`,
  `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md`, `docs/tasks/DONE.md`.

ADRs introduced: 0013.

---

## 2026-05-29 — Fix Railway data export docs (`railway run` vs `railway ssh`)

`railway run` runs commands locally with injected env vars; `/app/data` exists only
inside the deployed container where the volume is mounted. Step 7 in the deploy guide
incorrectly used `railway run`, causing `find: '/app/data': No such file or directory`.

- `docs/deploy/railway.md` — Step 7 now uses `railway ssh`; added prerequisites,
  extract commands, and troubleshooting rows.
- `docs/operator.md`, `docs/decisions/0010-railway-deployment.md` — aligned references.

---

## 2026-05-15 — Planning session: post-M1 docs / specs / backlog refresh

Pure documentation session. **No code changes.** The M1 14-day Railway
run is in progress; pushes to `master` would trigger a redeploy and
downtime (ADR-0010), so all work landed under `docs/` only.

Owner asked the agent to brainstorm and document what else can land
during and after the 14-day window, with extra detail so future agents
can implement without re-deriving the design.

### New documents

- `docs/backtest.md` — full M2 harness spec (CLI, data preconditions,
  no-look-ahead guard, walk-forward CV, weight optimiser with sanity
  guards, bootstrap CI, baseline comparisons, HTML report, backfill
  CLI, tests).
- `docs/paper_trading.md` — full M3 spec (ledger schema, entry / exit
  logic, SL/TP via ATR, restart recovery, P&L attribution, calibration
  curve, owner ledger via Telegram commands, tests).
- `docs/operator.md` — owner-facing runbook (anatomy of an alert,
  red / green flags, post-calibration recipe, escalation).
- `docs/operations/telegram_commands.md` — `/status`, `/last`,
  `/explain`, `/health`, `/threshold`, `/pause`, `/trade`, etc.
- `docs/operations/observability.md` — per-tick metrics jsonl,
  error-to-Telegram webhook, engine telemetry log lines, OKX
  instrumentation, heartbeat enrichment.
- `docs/operations/ci.md` — GitHub Actions workflow, branch
  protection, pre-commit hooks.
- `docs/post_mortems/_template.md` — incident post-mortem template.
- `docs/post_m1_code_fixes.md` — 8 latent issues to address after the
  run (closed-flag invariant, critical-inputs guard, anti-flip-flop,
  produced_at semantics, confidence-scale mismatch, XPL warm-up,
  multiplier cap, `InputKey` enum).

### New engine specs (no code yet — implement post-M2)

- `docs/engines/sentiment.md` — CryptoPanic-backed (background polling,
  graceful degrade, vote-weight calibration in M2).
- `docs/engines/liquidations.md` — three implementation paths; default
  Path B (Coinglass).
- `docs/engines/btc_context.md` — BTC-as-leader alignment multiplier +
  crisis filter; not part of weighted-sum score.
- `docs/engines/calendar.md` — `config/events.yaml` manual schedule;
  pre- and post-event confidence suppression curve.
- `docs/engines/cross_symbol_confluence.md` — meta-engine, runs in
  aggregator layer.

### New ADRs

- `0011-thresholds-rationale-and-uncalibrated-marker.md` — explains why
  the current threshold values are placeholders and mandates an
  `[UNCALIBRATED]` tag on Telegram alerts until M2 calibration.
- `0012-liquidations-roadmap.md` — complements (does not supersede)
  ADR-0006; promotes liquidation engine to BACKLOG P1 post-M2 with
  three implementation paths. ADR-0006 status line updated to point
  here.

### Task tracking

- `docs/tasks/BACKLOG.md` — full rewrite with P0/P1/P2 sections
  cross-referencing all new specs. M2 (backtest) decomposed from 3
  bullets into 12; M3 decomposed; new engines sequenced; operability
  and observability tracks added.
- `docs/tasks/IN_PROGRESS.md` — explicit next-steps block for the agent
  picking up after the 14-day run, ordered: extract data → write
  post-mortem → P0 quality gates → M2 starting with the no-look-ahead
  test.

ADRs introduced: 0011, 0012. ADR-0006 annotated.

Files touched (directory level): `docs/`, `docs/engines/`,
`docs/decisions/`, `docs/operations/`, `docs/post_mortems/`,
`docs/tasks/`.

No `src/` or `tests/` changes. No `pyproject.toml` / `uv.lock` changes.

---

## 2026-05-15 — Fix: all log levels tagged `[err]` in Railway

**Root cause:** Loguru writes all levels to `sys.stderr` by default. Railway
labels every byte from stderr as `[err]`, regardless of log level.

**Fix:** Split the console sink in `_configure_logging`:
- `DEBUG` / `INFO` → `sys.stdout` (Railway: `[inf]`)
- `WARNING` and above → `sys.stderr` (Railway: `[err]`, correct)

File log (`crypt.log`) unchanged — still receives all levels.

Files touched: `src/crypt/__main__.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: aiogram 3.7.0 broke `Bot` initializer (`parse_mode` removed)

**Root cause:** aiogram 3.7.0 removed `parse_mode`, `disable_web_page_preview`,
and `protect_content` from the `Bot.__init__` signature. Passing `parse_mode`
directly raised `TypeError` on every startup, crashing the process in a
Railway crash-loop.

**Fix:** Replaced `Bot(token=..., parse_mode=ParseMode.HTML)` with
`Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`
as required by aiogram ≥ 3.7.0.

Files touched: `src/crypt/sinks/telegram.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `SettingsError` on Railway when `SYMBOLS` env var is empty

**Root cause:** pydantic-settings v2 tries `json.loads()` on every `list[str]`
field before calling `field_validator`. `SYMBOLS=` (empty string) → empty
`json.loads("")` → `JSONDecodeError` → process crash.

**Fix:**
- Added `enable_decoding=False` to `SettingsConfigDict`: pydantic-settings now
  passes the raw string to the `field_validator` instead of trying JSON first.
- Updated `_parse_symbols` validator to fall back to `_DEFAULT_SYMBOLS` when
  the env var is empty/blank.
- Added troubleshooting row to `docs/deploy/railway.md`.

Files touched: `src/crypt/config.py`, `docs/deploy/railway.md`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `ModuleNotFoundError: No module named 'crypt.data'` on Railway

**Root cause:** `.gitignore` contained `data/` (no leading slash), which matched any
directory named `data` anywhere in the tree — including `src/crypt/data/`.
Railway builds from the git repo, so the entire Python package `crypt.data`
(context, ingestor, store) was absent from the container.

**Fix:** Changed `data/` → `/data/` and `logs/` → `/logs/` in `.gitignore`
(leading slash limits the rule to the repository root only).
Added `src/crypt/data/__init__.py`, `context.py`, `ingestor.py`, `store.py`
to git tracking.

Files touched: `.gitignore`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: slow shutdown (SIGINT did not interrupt in-flight awaits)

### What broke
SIGINT only set `stop_event`, but long-running coroutines (`run_health_check`,
`bootstrap`, `tick`) were awaited directly with no cancellation path.
Shutdown took up to ~30 s because those operations ran to completion before
`stop_event.wait()` was ever reached.

### Fix
Signal handler now also calls `main_task.cancel()` on the main asyncio task.
`CancelledError` is raised at the current `await` point and propagates up
through `asyncio.gather` chains; `except asyncio.CancelledError: pass` in
`_main()` ensures the `finally` cleanup block still runs.

Files touched: `src/crypt/__main__.py`.

---

## 2026-05-15 — Fix: root cause of silent zero-exit (stdlib crypt.py name collision)

Package name `crypt` collides with the deprecated Python 3.12 stdlib module
`crypt.py`. In Python's module resolution order, stdlib comes before
site-packages and the editable-install `src/` path. So `python -m crypt`
silently executed the stdlib module (no `__main__` block → exit 0, no output).

Fix: prefix the start command with `PYTHONPATH=/app/src` (railway.toml).
This puts `src/` at the front of `sys.path` before stdlib, so our package
is found first. Same fix required locally: `PYTHONPATH=src` in `.env`.

Files:
- `railway.toml`
- `.env.example`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: pandas-ta 0.4.x numba/LLVM hang on Railway

pandas-ta>=0.4 (only version available for Python 3.12+) added numba as a
hard dependency. numba initialises LLVM via llvmlite at Python import time —
before logging is even configured — causing a complete silent hang in
CPU-constrained Railway containers.

Fix: `NUMBA_DISABLE_JIT=1` is now documented as a required Railway Variable
(and added to `.env.example`). With JIT disabled numba functions fall back to
plain Python; indicators remain correct, just slightly slower.

The `<0.4` constraint was tried but is not available for Python 3.12+ on PyPI.

Files:
- `pyproject.toml` (reverted <0.4 constraint, added explanatory comment)
- `.env.example` (NUMBA_DISABLE_JIT=1 added)
- `docs/deploy/railway.md` (moved to Required variables table)
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: silent container on Railway deploy (output buffering + health check hang)

Three issues caused the process to appear dead after bytecode compilation:
1. `python -u` not set → Python buffered stderr in non-TTY container, log lines never flushed.
2. Health check created `ccxt.okx` without `"timeout": 30_000` → `load_markets()` could hang indefinitely.
3. Railpack auto-detects start command without `--no-dev` → dev packages (mypy/ruff) installed on every start, adding ~30-60 s delay before Python even booted.

Fixes: `railway.toml` start command changed to `uv run --no-dev python -u -m crypt`; `health.py` ccxt instance gets explicit 30 s timeout; `railway.md` updated with `PYTHONUNBUFFERED=1` recommendation and expanded troubleshooting table.

Files:
- `railway.toml`
- `src/crypt/runtime/health.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Railway: `uv run --no-dev` + immediate stderr logs

`uv run` includes the `dev` group by default, so every deploy was reinstalling
mypy/ruff before the app started. Start command now passes `--no-dev`. Stderr
logging uses colorize/enqueue only when stderr is a TTY so Railway log streams
see lines immediately.

Files:
- `railway.toml`
- `src/crypt/__main__.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix Railway `railway.toml` parse error

Removed invalid TOML line `$schema = ...` (that key belongs in `railway.json` only;
bare TOML keys cannot start with `$`). Railway deploy config now parses.

Files:
- `railway.toml`
- `CHANGELOG.md`

---

## 2026-05-14 — AGENTS: incident / "fix this" workflow

Clarified AI-first behaviour when the owner starts a session with errors or
CI logs instead of "continue": chat overrides stale assumptions, reproduce
before refactor, minimal fix + tests, and which task/changelog docs to touch.

Files:
- `AGENTS.md`
- `.cursor/rules/ai-first-workflow.mdc`

---

## 2026-05-14 — Session 6: Railway deployment

Railway deployment config for the M1 14-day continuous run.

Files created/modified:
- `railway.toml` — Railpack builder, production install, start command, restart policy.
- `.python-version` — pins Python 3.12.
- `src/crypt/config.py` — added `log_dir` field (env: `LOG_DIR`, default `logs/`).
- `src/crypt/__main__.py` — `_configure_logging` now accepts `log_dir` from settings.
- `.env.example` — documented `LOG_DIR`.
- `docs/decisions/0010-railway-deployment.md` — ADR (accepted).
- `docs/deploy/railway.md` — 8-step owner deployment guide with file extraction commands.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

ADRs introduced: 0010.

---

## 2026-05-14 — Session 5: reliability hardening

All P0/P1/P2 reliability items from BACKLOG completed. System is now ready
for the 14-day continuous run.

### What was done

- **`src/crypt/utils/retry.py`** (new) — `retry_with_backoff` coroutine helper
  with full-jitter exponential backoff (`uniform(0, min(max_delay, base*2^n))`).
- **`src/crypt/exchange/okx.py`** — all 5 fetch methods wrapped with
  `retry_with_backoff`; `"timeout": 30_000` added to ccxt config.
- **`src/crypt/data/ingestor.py`** — `ingest_all` and `_ingest_symbol`
  now log `BaseException` items from `asyncio.gather(return_exceptions=True)`.
- **`src/crypt/runtime/orchestrator.py`** — `tick()` logs exceptions from
  gather; sink exceptions logged by name; `_evaluate_symbol` returns
  `"ok"/"partial"/"failed"` status; tick summary log line at end.
  `Timeframe` added to imports.
- **`src/crypt/runtime/health.py`** — `_check_disk_space` added (logs WARNING
  if < 1 GB free on `data_dir` filesystem).
- **`src/crypt/__main__.py`** — log rotation changed to `rotation="00:00"` +
  `compression="gz"`; `_heartbeat_loop` background task (30-min liveness log +
  6h OKX health re-check); heartbeat task cancelled cleanly on shutdown.
- **`src/crypt/sinks/telegram.py`** — backoff jitter: `random.uniform(0.5, 1.5)`
  multiplier on retry wait.
- **`src/crypt/config.py`** — `okx_max_retries`, `okx_retry_base_delay`,
  `okx_retry_max_delay` settings exposed.
- **`.env.example`** — retry/backoff params documented (commented out).
- **`deploy/crypt.service`** (new) — systemd unit with `Restart=always`,
  `RestartSec=10`, `EnvironmentFile`, `WorkingDirectory`.
- **`README.md`** — "Running as a service" section added.

Results: mypy 0 errors / 36 files. ruff clean. 42/42 tests pass.

ADRs introduced: none.

---

## 2026-05-14 — Session 3: M1 validation

All M1 P0/P1 items resolved. System runs against live OKX without errors.

Files changed:

- `pyproject.toml` — added `pandas.*`, `pyarrow.*` to mypy overrides.
- `src/crypt/exchange/okx.py` — fixed `fetch_ls_ratio` and `fetch_taker_volume`: OKX rubik stat endpoints require `ccy` (base currency), not `instId`.
- `src/crypt/runtime/health.py` — **new**: startup health-check (OKX ping, symbol existence via market `id`, optional Telegram bot ping).
- `src/crypt/runtime/scheduler.py` — `stop()` guarded with `running` check.
- `src/crypt/__main__.py` — import `run_health_check`; call it before bootstrap; create `logs/` directory before file sink.
- `src/crypt/data/store.py` — typed lambda list; pyarrow `type: ignore`.
- `src/crypt/engines/derivatives.py` — `Direction` annotation; typed `_ls_signal` param; added imports.
- `src/crypt/engines/trend.py` — `Direction` annotation; `Direction` import.
- `src/crypt/engines/meanrev.py` — `Direction` annotation; `std=2.0`; `type: ignore[arg-type]`.
- `src/crypt/engines/volatility.py` — `npt.NDArray[Any]` for `_rank_pct`.
- `src/crypt/config.py` — `return list(v)` to silence mypy `no-any-return`.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

Results: mypy 0 errors / 34 files. ruff clean. 42/42 tests pass.
Smoke test: `uv run python -m crypt --once` exits 0, verdicts for all 3 symbols.
Symbol check: SOL-USDT-SWAP ✓, TON-USDT-SWAP ✓, XPL-USDT-SWAP ✓.

ADRs introduced: none.

---

## 2026-05-14 — Session 2: M1 implementation

Full M1 code layer implemented. Context7 was unavailable; proceeded with
in-context library knowledge.

Files created:

- `src/crypt/config.py`, `models.py`, `__main__.py`
- `src/crypt/exchange/__init__.py`, `base.py`, `okx.py`
- `src/crypt/data/__init__.py`, `store.py`, `ingestor.py`, `context.py`
- `src/crypt/engines/__init__.py`, `base.py`, `trend.py`, `meanrev.py`,
  `derivatives.py`, `volatility.py`, `regime.py`
- `src/crypt/aggregator/__init__.py`, `weights.py`, `ensemble.py`
- `src/crypt/decision/__init__.py`, `filters.py`
- `src/crypt/sinks/__init__.py`, `base.py`, `telegram.py`, `jsonlog.py`,
  `console.py`, `execution_stub.py`
- `src/crypt/runtime/__init__.py`, `scheduler.py`, `orchestrator.py`
- `src/crypt/backtest/__init__.py`
- `config/weights.yaml`
- `tests/conftest.py`, `tests/engines/test_{trend,meanrev,derivatives,
  volatility,regime}.py`, `tests/aggregator/test_ensemble.py`,
  `tests/decision/test_filters.py`

Also updated: `pyproject.toml` (`requires-python` bump to `>=3.12`),
`uv.lock` generated.

All 42 tests pass; `ruff` clean.

Next: live smoke test, `XPL-USDT-SWAP` existence check, mypy pass.

ADRs introduced: none.

---

## 2026-05-13 — Session 1: project bootstrap

Owner pinned down the high-level requirements: Python, OKX-only, 4h intraday,
3 starting symbols (`SOL-USDT-SWAP`, `TON-USDT-SWAP`, `XPL-USDT-SWAP`),
Telegram alerts, 0$ data budget, local execution, weighted-sum aggregator,
confidence threshold 75%, AI-first development.

Created the project scaffold:

- `README.md`, `AGENTS.md`, this `CHANGELOG.md`, `.gitignore`, `.env.example`
- `.cursor/rules/` — `project-context.mdc`, `ai-first-workflow.mdc`,
  `coding-standards.mdc`
- `docs/architecture.md`
- `docs/decisions/` — ADRs 0001–0008
- `docs/tasks/` — `ROADMAP.md`, `BACKLOG.md`, `IN_PROGRESS.md`, `DONE.md`
- `docs/engines/` — specs for `trend`, `meanrev`, `derivatives`, `volatility`,
  `regime`, `aggregator`, `decision`
- `pyproject.toml`, `src/crypt/__init__.py`, `tests/`

OKX API capabilities verified via Context7 (`/websites/okx_docs-v5_en` and
`/ccxt/ccxt`):

- OHLCV, funding rate (current + history), open interest history, long/short
  account ratio, taker volume — all available via public REST.
- Liquidations — only via WebSocket; deferred (ADR 0006).

No code yet. Next session: implement data layer + signal contracts (see
`docs/tasks/IN_PROGRESS.md`).

ADRs introduced: 0001..0008.
