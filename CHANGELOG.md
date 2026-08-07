# Changelog

Recent project history. Older entries live in `CHANGELOG_ARCHIVE.md`.

Format: newest on top, date in `YYYY-MM-DD`.

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
