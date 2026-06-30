# Done

Reverse-chronological archive of completed work. Newest on top.

---

## 2026-06-30 — Validated latest-bar Core4 signal cache

**What:** added a live-only donor-frame cache and latest-row generation path
without replacing the full external backtester strategy contract.

**Why now:** WebSocket triggering removed two minutes of fixed delay, but full
Core4 generation still took about 32 seconds and could miss entries during a
fast move.

**Result:** live rebuilds exact full-history discovery features, recalculates
donors on a 512-bar tail, validates 128 cached overlap bars exactly, and
automatically performs a cold rebuild after any history or frame mismatch.
Backtester `generate()` remains the full-history path.

**Acceptance:** on 39,734 real SOL H1 bars, full generation took `31.8s`, cold
live cache generation `13.2s`, and the next append `6.8s`. The complete latest
event dictionary matched the full result exactly. Cache append/invalidation
unit tests, focused execution/backtester tests, ruff, and strict mypy pass.
Owner-run artifact
`results/core4_v3_cache_parity_20260630/20260630_151804/` was compared with
canonical `results/core4_v3_liqsafe_native_trailing_tiered_20260629/20260629_160832/`;
`trades.csv`, metrics, diagnostics, signals, equity, and OHLCV are all
byte-identical.

**Links:** ADR-0052, `docs/execution/live_signal_cache.md`,
`src/backtester/strategies/filtered_donor_portfolio.py`.

## 2026-06-30 — WebSocket-confirmed H1 live trigger and rejection logs

**What:** replaced the fixed two-minute primary execution delay with an OKX
business WebSocket boundary listener and made entry attempts/rejections visible
in normal logs as well as Telegram.

**Why now:** live detected the 2026-06-30 SMAC long but started at `14:02 UTC`;
price had moved from the backtest open `$72.84` to `$73.52`, so the `0.1%`
drift guard rejected a trade the backtester would have entered.

**Result:** the service subscribes at `HH:59:30 UTC`, waits for confirmed
H1/H4/UTC-day candles plus the new H1 open, persists those candles, and starts
the Core4 cycle immediately. Text ping, reconnect/resubscribe, duplicate
prevention, error notification, and the `*:02` REST fallback follow the
resilience pattern reviewed in the owner's `goex` project.

**Acceptance:** real OKX business WebSocket smoke subscription returned
`candle1H` data and an acknowledgement; focused execution/runtime tests pass;
ruff, strict mypy, and offline lock validation pass.

**Links:** ADR-0051, `docs/execution/h1_websocket_trigger.md`,
`src/crypt/runtime/h1_websocket.py`.

## 2026-06-29 — OKX SOL maintenance-margin tiers in liquidation model

**What:** added the fixed OKX SOL-USDT isolated SWAP tier schedule
`okx_sol_usdt_swap_2026_06_29` to the shared liquidation model, strategy
config, live settings, persisted positions, and trade exports.

**Why now:** the first liquidation fix still used `maintenance_margin_rate=0.004`
for every size. OKX applies that only up to `5000` SOL contracts; larger
aggregate same-side positions get higher MMR and lower maximum leverage.

**Result:** both backtester and live execution resolve maintenance margin rate
and maximum leverage from position size, and aggregate liquidation uses total
same-side size. v3 nested donor replay receives the same liquidation/tier
defaults as the outer portfolio run. Leverage is side-scoped: an open same-side
position reuses its current leverage and never calls OKX leverage-change before
adding to that side; an empty side chooses fresh leverage from the current tier.
Old single-rate configs remain backward-compatible.

**Validation:** focused liquidation/simulation/live-risk/replay tests pass,
strict `src/crypt/execution` mypy passes, and focused ruff `E,F,I` passes.

**Links:** `src/backtester/margin_policy.py`,
`strategies/archive/filtered_donor_portfolio_causal_v3_core4.json`,
`docs/execution/liquidation_safe_leverage.md`.

---

## 2026-06-29 — Real reduce-only close integration test

**What:** used ephemeral Python importing production functions to bind and
cancel the legacy Island trade's exact TP/SL, submit an idempotent reduce-only
market close, confirm its fill, persist fees/PnL, notify Telegram, reconcile
OKX, and replay the result.

**Result:** order `3699121635279626240` filled `0.41` SOL contracts at `73.43`.
Entry fee was `$0.01515155`, exit fee `$0.01505315`, and realized PnL
`-$0.2270047`. OKX ended with zero positions, regular orders, and algo orders;
cash and equity both read `$104.7729953`; sync was clean.

**Finding:** canceling the attached TP automatically canceled its linked SL as
OCO. OKX then returned `51400` for the redundant SL cancellation. Protection
cleanup now treats terminal/not-found cancellation as idempotent success.

**Links:** `src/crypt/execution/okx_order_client.py`,
`tests/execution/test_okx_order_client.py`,
`docs/execution/live_execution.md`.

---

## 2026-06-29 — Liquidation-safe v3 and native OKX trailing parity

**What:** corrected the canonical backtester and live Core4 v3 executor for
real OKX liquidation, same-side aggregation, native trailing, candle
continuity, idempotent orders, confirmed fills/fees, per-position protection,
and exact trade replay.

**Why now:** the first live SOL long opened at 25x with liquidation `71.2843`
above structural stop `70.9484`; live also lacked the trailing behavior scored
by the v3 backtest.

**Result:** new entries select the highest safe whole leverage (20x for the
observed geometry), enforce a 0.5% price buffer, model worst-case liquidation,
place an OKX `move_order_stop` with fixed entry ATR spread, and block on any
missing/unsafe protection. Telegram reports every attempt, terminal result,
runtime error, and repeated sync blocker.

**Acceptance:** the complete unit suite passes when excluding one test that
prints `PASSED` but hangs during pytest shutdown; focused ruff and strict
`src/crypt/execution` mypy pass. Live read-only reconciliation binds the
existing SL/TP correctly and reports only its genuine unsafe liquidation.

**Links:** ADR-0049, ADR-0050, `docs/execution/`,
`src/backtester/trailing_policy.py`, `src/crypt/execution/`.

---

## 2026-06-29 — Complete Telegram visibility for live entry attempts and failures

**What:** extended Core4 execution notifications from completed entries/exits
to every actionable entry attempt, deterministic rejection, and runtime error.

**Why now:** the owner cannot continuously inspect service logs and needs to
know when a donor tries to enter, whether OKX accepted the path, and why an
entry did not happen.

**Result:** every donor event now emits `ENTRY ATTEMPT` before sizing or OKX
calls, followed by `ENTRY`, `ENTRY REJECTED`, or `EXECUTION ERROR`. Telegram
also receives candle refresh, signal generation, leverage, order placement,
TTL close, startup/runtime, and exchange-sync blocker errors.
Persistent sync blockers are reported on every H1 execution cycle.

**Acceptance:** 57 terminating execution tests plus 3 shared multi-signal
tests pass; notification, rejection, success, leverage-error, and repeated
sync-blocker coverage is included. `ruff check` and strict `mypy` pass.
One pre-existing H1 thread-pool test passes its assertions but hangs during
pytest shutdown and is tracked separately in `BACKLOG.md`.

**Links:** `src/crypt/execution/notifications.py`,
`src/crypt/execution/executor.py`, `docs/execution/live_execution.md`.

---

## 2026-06-28 — Core4 execution-only dry-run cleanup

**What:** separated Core4 live execution dry-runs from the legacy H4 alert
monitor and fixed OKX pending algo-order sync.

**Why now:** the first owner dry-run printed unrelated `HOLD/conf/regime`
verdicts for TON/XPL/SOL and OKX rejected pending algo-order sync because the
raw endpoint was called without `ordType`.

**Result:** `python -m crypt --once --execution-only` now runs only the H1
Core4 execution path, uses `EXECUTION_SYMBOLS` for startup symbol checks, and
does not instantiate the legacy H4 monitor. The startup log now prints only the
execution symbols in this mode. Pending algo orders are queried by the required
OKX algo order types, so the sync should no longer produce `Parameter ordType
error`. The dry-run freshness check also accepts timezone-aware Parquet
`open_time` values, fixing the pandas `tzinfo with the tz parameter` failure.
Standard-library logs are now routed into loguru, so execution INFO messages
are visible in the operator console and `logs/crypt.log`. The execution-only
heartbeat now keeps checking `EXECUTION_SYMBOLS`, not the legacy monitor
symbol basket. Dry-run sizing can also use `EXECUTION_DRY_RUN_CAPITAL` so a
small real OKX balance does not prevent testing the same `$10k`/`$30k` sizing
profile used in backtests. OKX swap sizing now rounds down to exchange lot
size / ccxt amount precision instead of whole contracts, so SOL sizes like
`0.48` contracts are valid when OKX reports `lotSz=0.01`.

**Acceptance:** `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
(57 tests), `ruff check src/crypt/__main__.py src/crypt/execution
tests/execution`, and `mypy src/crypt/__main__.py src/crypt/execution`
passed.

**Links:** `src/crypt/__main__.py`,
`src/crypt/execution/okx_order_client.py`,
`docs/execution/live_execution.md`.

---

## 2026-06-28 — Live execution Telegram reporting

**What:** added Telegram reporting for live Core4 execution: daily full sync,
every entry, and every exit.

**Why now:** before real money, the owner needs operator-visible proof of
account state and every trade lifecycle event, not only logs/state files.

**Result:** when Telegram is configured, live execution sends one full sync
report per UTC day with balance, positions, orders, algo orders, sync status,
and blocker reasons. Entry notifications are sent after local state records a
position. Exit notifications are sent after OKX fill classification, startup
reconciliation, or TTL market close. The last daily sync report date is
persisted to avoid restart spam.

The follow-up parity audit added startup validation against strategy
`backtest_args`, `drain_on_group_change` handling for `signal_events`, and
stronger live-vs-`ExecutionSim` assertions for leverage and locked margin.

**Acceptance:** `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
(53 tests), `ruff check src/crypt/execution tests/execution`, and
`mypy src/crypt/execution` passed.

**Links:** `src/crypt/execution/notifications.py`,
`src/crypt/execution/executor.py`, `docs/execution/live_execution.md`.

---

## 2026-06-28 — OKX live order parameter audit against signal_executor

**What:** compared the Core4 live ccxt order path with the cloned
`signal_executor` direct OKX REST implementation and tightened the live order
parameters.

**Why now:** before live money, the owner wanted confirmation that the ccxt
wrapper sends the same critical OKX fields as the known direct executor:
isolated margin, side-specific position mode, attached SL/TP, reduce-only
closes, and algo-order cancellation support.

**Result:** live execution now sets isolated leverage for both long and short
sides, sends entry orders with isolated margin and explicit position side, uses
a market stop and limit take-profit attached to the entry, sends reduce-only
market closes with the original position side, and blocks new entries unless
OKX reports long/short position mode.

**Acceptance:** `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
(46 tests), `ruff check src/crypt/execution tests/execution`, and
`mypy src/crypt/execution` passed.

**Links:** `signal_executor/internal/secondary/exchange/okx/okx.go`,
`src/crypt/execution/okx_order_client.py`,
`docs/execution/live_execution.md`.

---

## 2026-06-27 — Investor Core4 report and live close accounting

**What:** added a plain-language HTML report for a non-technical investor and
extended live state accounting for positions that disappear from OKX.

**Why now:** the owner wants to show Core4 to a friend/investor without trader
or programmer jargon, and live execution state needs to explain closed
positions in dollars rather than only `status=closed`.

**Result:** `reports/core4_investor_report.html` summarizes the work in plain
Russian, compares three practical modes, shows $1k/$10k/$30k scaling, and
includes yearly/monthly tables for the banked-profit and calmer variants.

Live execution now classifies missing exchange positions from recent fills and
persists exit time, exit price, exit reason, estimated realized PnL, and exit
fee when a matching fill is available.

**Acceptance:** `pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
(40 tests), `ruff check src/crypt/execution tests/execution`, and
`mypy src/crypt/execution` passed.

**Links:** `reports/core4_investor_report.html`,
`src/crypt/execution/fill_classifier.py`, `tests/execution/test_fill_classifier.py`.

---

## 2026-06-27 — Core4 live execution parity migration

**What:** migrated M4 live execution from the old scalar `crypt_ensemble` path
to Core v4 registry strategy execution with multi-event `signal_events`.

**Why now:** the owner wants to present Core v4 and start real-time trading, but
live execution had to match the exact backtested strategy before any investor
or live-money discussion. The old live path would have traded a different
strategy shape.

**Result:** live execution now loads the selected Core v4 JSON through the
backtester registry, waits for closed H1 candles, uses the current forming H1
open as the backtester-equivalent next-open entry, processes every same-bar
event in order, applies event-level risk/RRR/TTL/exit overrides, and keeps the
owner rule `max_positions = 0`.

Full OKX sync was added before startup reconciliation, before every H1 entry
decision, and after order placement. The state schema is v2 with donor/event
metadata, trailing fields, and last exchange sync status. New entries are
blocked on orphan positions/orders, missing exchange positions, or invalid
balance.

**Acceptance:** local validation passed:
`pytest tests/execution tests/backtester/test_backtester_multi_signal.py -q`
(36 tests), `ruff check src/crypt/execution tests/execution`, and
`mypy src/crypt/execution`. Synthetic parity now checks that live entry
decisions match `ExecutionSim.run()` for the same `signal_events`.

**Links:** `docs/execution/live_execution.md`, ADR-0048,
`src/crypt/execution/`, `tests/execution/`,
`tests/backtester/test_backtester_multi_signal.py`.

---

## 2026-06-26 — Monthly profit sweep mode added to backtester

**What:** added an explicit `--capital-sweep monthly_profit` mode to
`backtester run`.

**Why now:** the owner wanted to evaluate a withdrawal-style account: each
month starts from the configured trading capital when there is profit to sweep,
while losing months are not topped up.

**Result:** at month boundaries, realized trading capital above the initial
capital is removed from the trading account and tracked as banked profit. If
the account is below initial capital, nothing is withdrawn and the reduced
account continues. Reports now show `Banked Profit` and `Total Account` when
the mode withdraws money. The monthly console table also shows `Withdrawn ($)`
for the dollars withdrawn in each specific month.

**Acceptance:** targeted execution and results tests passed. `trades.csv`
contains `capital_sweep_amount`, `banked_profit_after`, and
`trading_capital_after_sweep` for audit.

**Links:** `src/backtester/execution_sim.py`,
`src/backtester/results_analyzer.py`, `README.md`.

---

## 2026-06-26 — Multi-signal trailing parity fixed

**What:** fixed the multi-signal execution path so `signal_events` strategies
request ATR/trailing support the same way scalar-signal strategies do.

**Why now:** the first `Island short + SMAC long` portfolio result was
nonsensical: it emitted the right number of trades after nested replay controls
were fixed, but no trade exited by `trailing_stop`, so the portfolio made only
+$8,350 while standalone Island alone made +$72,602.

**Result:** `ExecutionSim.run()` now detects `trail_activation_rrr` inside
`signal_events` and enriches the frame with closed ATR before simulation. A
regression test proves a multi-signal event can exit by `trailing_stop`.
Single-strategy portfolio parity was checked for both selected Island and
selected SMAC: trades, PnL, exits, and recalculated drawdown match standalone
runs exactly.

**Acceptance:** after the fix, `island_short_smac_long_portfolio_v1` made
+$158,657 on $10k with 1,087 trades and -16.98% recalculated drawdown. Targeted
pytest, ruff, and mypy checks passed.

**Follow-up rerun:** all archived `filtered_donor_portfolio` configs were
rerun under `results/multisignal_rerun_after_trailing_fix/`. Pre-fix
multi-signal money results are invalid. `causal_v1` now fails closed because it
references unavailable fields; `causal_v2_deployable` is +$138,222 with
-55.61% drawdown; `causal_v3_core4` is +$656,185 with -22.42% drawdown; the
selected Island+SMAC branch is +$158,657 with -16.98% drawdown.

**Core4 frontier:** selected
`filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85` as the
current best balance after a risk/composition grid. It made +$206,978 on $10k,
kept 2,298 trades / 12.69 trades per week, and reduced recalculated drawdown to
-14.91%.

**Links:** `src/backtester/execution_sim.py`,
`results/island_short_smac_long_portfolio_v1_trailing_fixed_full/20260626_180002/`,
`results/portfolio_parity_check/`,
`results/multisignal_rerun_after_trailing_fix/`,
`results/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85_full/20260626_182156/`.

---

## 2026-06-26 — SMAC long-only branch tested

**What:** split archived SMAC into long-only/short-only branches, searched a
small risk/RRR/TTL grid around the long side, and tested it as a possible
complement to the selected Island short-only branch.

**Why now:** archived donor evidence showed SMAC had the best long-side money
among current donor strategies: +$9,910 long PnL in the archived full-period
run. The owner asked to start improving SMAC after fixing Island.

**Result:** selected `smac_long_r0p95_rrr1p25_ttl64_v1` as the current SMAC
long branch. It made +$10,377 on $10k, kept 2.61 trades/week, and had -14.59%
recalculated drawdown. This is not strong enough as a standalone production
candidate, but it is the cleanest current long-only SMAC branch.

**Acceptance:** exact artifacts exist under
`results/smac_long_selected_full/20260626_174726/`. The rejected
wide-stop filters are under `results/smac_long_stop_filter/`. The experimental
`Island short + SMAC long` portfolio was exact-tested after fixing nested
replay controls and should not be promoted: it made only +$8,350 with -28.27%
recalculated drawdown.

**Links:** `strategies/archive/smac_long_r0p95_rrr1p25_ttl64_v1.json`,
`strategies/archive/island_short_smac_long_portfolio_v1.json`,
`docs/archive/candidates/smac_003335_double_bottom_body_to_range/README.md`.

---

## 2026-06-26 — Island short-only branch improved and exact-tested

**What:** added exact DSS replay controls for side filtering and entry-known
skip rules, then optimized the archived Island engulfing/BB/EMA strategy around
its short-side edge.

**Why now:** the six-donor filtered portfolio failed badly, while standalone
Island remained one of the few current families with clear positive money. The
owner asked to keep trade frequency at least 2-3 trades/week and improve Island
instead of searching unrelated strategies.

**Result:** the original full-period Island run made +$50,599 on $10k with
7.32 trades/week and -23.91% recalculated drawdown. The current best
short-only filtered branch,
`island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1`, made +$72,602 on
$10k, kept 3.40 trades/week, and recalculated drawdown was -16.35%. A lower
risk variant, `island_short_r1p35_rrr0p75_ttl32_weekend_stop_filter_v1`, made
+$65,227 with 3.40 trades/week and -15.62% drawdown.

**Acceptance:** exact `backtester run` artifacts exist under
`results/island_short_weekend_stop_filter_v1_full/20260626_172556/` and
`results/island_short_weekend_stop_filter_risk_grid/`. Targeted pytest, ruff,
and mypy pass for the DSS replay changes.

**Links:** `strategies/archive/island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1.json`,
`src/backtester/strategies/dss_strategy.py`,
`docs/archive/candidates/island_2023_021396_engulfing_bb_trend/README.md`.

---

## 2026-06-26 — Negative oracle research command

**What:** added `backtester negative-oracle-research`, a report that searches
entry-known skip rules for repeatable losing trade clusters.

**Why now:** the deployable filtered donor portfolio exact result lost
$3,442 on a $10k account with -76.05% drawdown. The owner chose the "negative
oracle" idea: find mines to avoid rather than winners to take.

**Result:** the command writes `negative_rules.csv`, `top_negative_rules.csv`,
and `report.md`, with progress bars for single and two-rule searches. On
`filtered_donor_portfolio_causal_v2_deployable`, 1,066 rules were tested; the
best robust rule saved only +$315 validation and +$1,487 stress, so this
portfolio has no strong simple entry-known mine filter.

**Acceptance:** targeted tests, ruff, and mypy pass.

**Links:** `src/backtester/negative_oracle_research.py`,
`results/negative_oracle_filtered_donor_portfolio_causal_v2/`.

---

## 2026-06-26 — Filtered donor portfolio v1 invalidated and deployable v2 prepared

**What:** diagnosed the poor `filtered_donor_portfolio_causal_v1` exact result
and found that two donor filters referenced fields unavailable in the fast
portfolio signal path.

**Why now:** the owner exact-tested v1 and got only +$9,377 on $10k (+93.78%)
with -7.57% drawdown. The result was suspicious because the research filters
had looked much stronger per donor.

**Result:** v1 now fails early instead of silently dropping donors when a filter
requires missing features. Added previous-closed-candle catalog features to the
portfolio path and created
`strategies/archive/filtered_donor_portfolio_causal_v2_deployable.json`, which
uses only deployable entry-time fields.

**Acceptance:** signal-only diagnostics show all six donors emitting events in
v2: 3,787 total events before execution. Targeted tests, ruff, and mypy pass.
Owner-scale exact validation remains the next owner-run step.

**Links:** `strategies/archive/filtered_donor_portfolio_causal_v2_deployable.json`,
`src/backtester/strategies/filtered_donor_portfolio.py`.

---

## 2026-06-26 — Multi-signal shared-capital execution MVP

**What:** added a backward-compatible `signal_events` execution contract so one
OHLCV bar can carry multiple independent entry requests. Added
`filtered_donor_portfolio_causal_v1`, which runs all six archived donor signal
streams, applies the causal donor filters, and releases every accepted signal
into the shared capital/margin simulator.

**Why now:** donor-level filter research showed robust-forward CSV improvements
for all six donors, and standalone donor trades materially overlap on the same
entry timestamps. The owner wants all passing strategies to trade from the same
available capital instead of forcing one active strategy or pre-splitting
capital.

**Result:** `ExecutionSim` still supports legacy scalar `signal`/`sl_price`
rows, but can now process `signal_events` lists by updating active positions
once per OHLCV bar and then evaluating all same-bar entries in order.
`Backtester` accepts strategies that emit `signal_events` without scalar signal
columns.

**Acceptance:** targeted execution/backtester tests pass; targeted ruff and
mypy are clean for the new strategy path. Owner-scale exact validation remains
owner-run.

**Links:** ADR-0047, `docs/multi_signal_execution.md`,
`strategies/archive/filtered_donor_portfolio_causal_v1.json`.

---

## 2026-06-26 — Donor backtest archive materialized

**What:** copied full-period donor exact backtest artifacts and causal filter
research outputs into `results/research_archive/` as physical file copies.

**Why now:** the owner requested that donor trades and all backtest diagnostics
be preserved so future agents do not need to repeat owner-scale donor
backtests if working directories are cleaned or moved.

**Result:** archive manifest confirms six donor runs, 6,210 total trades, and
physical copies rather than hardlinks.

**Acceptance:** `results/research_archive/donor_exact_2022_2026_manifest.json`
records copied runs and verifies `copied_not_hardlinked=True` for each donor
`trades.csv`.

**Links:** `results/research_archive/donor_exact_2022_2026/`,
`results/research_archive/trade_filter_research_donors_2022_2026_causal/`.

---

## 2026-06-26 — Per-strategy and catalog-feature trade filter research

**What:** extended `backtester trade-filter-research` from single global
filters to two-rule conjunctions, optional grouped searches, and optional
closed-candle catalog/discovery features joined at entry time.

**Why now:** the owner wants to filter bad trades per strategy, then later let
all surviving strategies trade through the normal shared-capital backtester
instead of forcing the router to pick exactly one active strategy.

**Result:** the command now supports `--group-by selected_strategy`,
`--include-catalog-features`, and `--ohlcv <path>`. Grouped searches remove the
grouping column from candidate features to avoid trivial constant rules. Catalog
features are computed from OHLCV and joined with backward-only time alignment,
so no trade can see candles after entry.

**Acceptance:** targeted tests, ruff, and mypy pass. A real smoke on
`router_v2_3997501` confirmed grouped progress bars and showed zero robust
passes; a catalog-feature smoke confirmed `ohlcv.csv` with `open_time` loads and
joins successfully.

**Links:** `docs/trade_filter_research.md`,
`src/backtester/trade_filter_research.py`,
`results/trade_filter_research_by_strategy_2022_2026/router_v2_3997501/`.

---

## 2026-06-26 — Anti-overfit trade filter research MVP

**What:** added a fixed train/validation/stress split policy and a
`backtester trade-filter-research` command that searches entry-known
single-rule `take`/`skip` filters over existing `trades.csv` artifacts.

**Why now:** exact OHLCV validation showed that the current router shortlist
does not meet the mandate. The owner redirected work away from more router
search and toward inspecting existing bad trades and removing them without
look-ahead.

**Result:** the command reads one or more `trades.csv` files, generates
threshold/equality rules from the train split only, blocks post-entry leakage
fields, ranks the train-discovered rules by validation score, and reports
stress metrics separately. It writes `baseline_by_split.csv`,
`filter_candidates.csv`, `top_filters.csv`, and `report.md`.

**Acceptance:** synthetic leakage/split tests pass; targeted `ruff` and `mypy`
are clean; a full-period router smoke generated 282 candidate rules with a
visible progress bar.

**Links:** ADR-0046, `docs/trade_filter_research.md`,
`src/backtester/trade_filter_research.py`.

---

## 2026-06-25 — Oracle-regret router search and exact shortlist completed

**What:** searched 100,000 Router Catalog v2 proposals across four algorithms,
deduplicated them by train selection timeline, validated every unique timeline
through archived continuous execution, and exact-backtested the risk/return
front through the normal composite OHLCV strategy contract.

**Result:** 4,000 retained configurations collapsed to 813 unique timelines.
All 813 routed candidates received `discard`; only 69 respected the 10%
monthly drawdown ceiling. Exact 2025 results for the six finalists were:

| Router | Return | Floor months | Worst mandate DD | Verdict |
| --- | ---: | ---: | ---: | --- |
| `router_v2_3997501` | +157.93% | 4/12 | -6.22% | discard |
| `router_v2_2687609` | +123.64% | 4/12 | -9.76% | discard |
| `router_v2_4332664` | +118.01% | 3/12 | -9.74% | discard |
| `router_v2_4329131` | +115.86% | 3/12 | -4.80% | discard |
| `router_v2_2687604` | +101.88% | 2/12 | -1.97% | discard |
| `router_v2_3213199` | +97.54% | 3/12 | -6.70% | discard |

The full-history 2022-2026 diagnostics produced +425.78% to +664.60%, but do
not change the 2025 decision. After normalizing full-run 2025 PnL to capital
at 2025-01-01, results match the standalone runs. Five candidates had identical
2025 trade sequences; `router_v2_3213199` gained two boundary-hour trades only
when prior candles were present.

**Decision:** the oracle-regret proxy is adequate as a cheap screening tool
but does not produce a mandate-qualified router over the current six-strategy
universe. Do not promote or tune these router configurations further.

**Acceptance:** exact artifacts exist under
`results/router_exact_shortlist_2025/` and
`results/router_exact_shortlist_2022_2026/`.

**Links:** ADR-0045, `docs/regime_router_search.md`.

---

## 2026-06-24 — Router 2687609 promoted into normal strategy contract

**Correction (2026-06-25):** this completion claim was invalid. The first
implementation launched nested backtests inside the strategy and violated the
owner-required external-backtester boundary. The item is active again in
`IN_PROGRESS.md`; the corrected strategy consumes persisted causal router
state and never reconstructs it through nested backtests.

**What:** implemented `router_v2_2687609` as registry strategy
`promoted_router`, containing all six archived strategies and the frozen router
configuration.

**Original result (superseded):** the strategy reconstructed completed donor
labels internally and emitted only the selected nested strategy's signals.
That reconstruction violated the external-backtester boundary. Generic
per-signal TTL, trailing, exit geometry, and position-group drain support
remain valid.

**Acceptance:** registry/config loading succeeds; 55 focused composition,
execution, router, and label tests pass. Full-period validation is owner-run.

**Links:** `docs/strategies/promoted_router.md`,
`strategies/archive/router_v2_2687609.json`.

---

## 2026-06-24 — Router v2 matrix consumed and execution validator built

**What:** consumed the completed four-algorithm matrix, merged 100,000
evaluations, archived the high-return and robustness frontier routers, and
implemented continuous shared-capital trade replay.

**Result:** `router_v2_4252951` reached +425.17% median offset return with
-6.11% worst DD. `router_v2_3216811` reached +310.56% median, +281.26% minimum,
and -3.80% worst DD. The new `router-validate` command enforces one strategy,
no cash, shared margin, and drain-before-switch semantics.

**Acceptance:** archive snapshots are complete; routed execution synthetic
tests and CLI help pass. Real 2025 replay remains owner-run.

**Links:** `docs/regime_router_search.md`,
`docs/routed_execution_validation.md`, ADR-0042.

---

## 2026-06-24 — Router search algorithm matrix implemented

**What:** added `random`, `island_qd`, `hyperband_qd`, and `smac_qd` candidate
selection backends for Router Catalog v2 plus `router-search-matrix` for
concurrent owner runs.

**Result:** every backend uses the same full offset-robust final evaluator while
exploring the 4.64M catalog through a different proposal policy. Seeds and
proposal-pool size are explicit and reproducible.

**Acceptance:** 14 focused tests pass, ruff is clean, and a four-process smoke
run completed successfully on real rolling labels.

---

## 2026-06-23 — Router Catalog v2 constructor implemented

**What:** expanded the router constructor to a 4,640,400-config deterministic
catalog with new scoring, state-subset, similarity, recency, hold, sample, and
switch dimensions.

**Result:** added memory-safe `--summary-only`, `--catalog-version v2`,
`--top-predictions`, and `--count-only`. A 500-config benchmark took about 92
seconds with roughly 303 MB peak RSS, supporting a 100k approximately five-hour
owner run.

**Acceptance:** focused router tests pass; ruff is clean; exact owner command is
documented in `docs/regime_router_search.md`.

---

## 2026-06-23 — Complete v1 router catalog evaluated

**What:** consumed owner-run router-search chunks at offsets 2000, 4000, and
6000, completing all 7040 deterministic v1 configs.

**Result:** no later chunk beat the archived rolling-median router on raw
utility. The best distinct risk-qualified family was `router_005807`:
PineScript same-state mean-minus-DD, 120d lookback, 30d hold, switch margin 1,
median offset return +192.80%, minimum +141.63%, worst DD -6.52%.

**Decision:** archived it as
`pinescript_same_state_mean_dd_120d_hold30_margin1`; moved active work to
Router Catalog v2 rather than tuning either v1 seed.

**Links:** `docs/archive/routers/`,
`docs/regime_router_search.md`.

---

## 2026-06-23 — First router research seed archived

**What:** archived search row `router_001190` under the descriptive id
`rolling_median_120d_switch_margin_3`.

**Why now:** the owner rejected further local optimization of this candidate
and directed the project to preserve it as a benchmark while continuing the
broader router search.

**Result:** frozen config is under `routers/archive/`; verdict, utility,
offset snapshot, and provenance are under `docs/archive/routers/`.

**Links:** `docs/archive/routers/rolling_median_120d_switch_margin_3/`,
`routers/archive/rolling_median_120d_switch_margin_3.json`.

---

## 2026-06-23 — Full PineScript-aware router search completed

**What:** optimized `router-search` enough to run the full 2000-config
PineScript-aware single-strategy router catalog.

**Why now:** the first constructor MVP was correct but too slow for the full
catalog. The owner wanted the session used to push through to a real result,
not stop at implementation.

**Expected gain:** get the first utility-ranked router shortlist over all
archived strategies and PineScript-derived market-state features.

**Result:** full run completed at
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/`.
Best router is `router_001190`: rolling median score, 120d lookback, no feature
set, 3-point switch margin, median offset return +258.13%, minimum offset return
+186.37%, worst DD -17.34%, median switches 2. PineScript same-state routers
reached the top-20 but did not beat the rolling selector.

**Acceptance:** full artifacts exist (`router_utility_scores.csv`,
`router_search_report.md`, predictions, dense scores, offset sensitivity);
focused tests pass and ruff is clean. Follow-up DD attribution moved to
`IN_PROGRESS.md`.

**Links:** `docs/regime_router_search.md`,
`src/backtester/regime_router.py`.

---

## 2026-06-23 — Single-strategy router constructor MVP

**What:** implemented `backtester router-search`, a router constructor that
scores single-strategy selectors over rolling labels. It never splits capital
across multiple active strategies and never chooses `cash`.

**Why now:** the owner clarified that routing should search combinations the
same way DSS searches strategies, but the active universe must remain the full
archive and the output must be exactly one strategy.

**Expected gain:** move regime routing from a few hand-written baselines to a
searchable catalog with offset-robust utility scoring.

**Result:** rolling labels now export `router_ps_*` PineScript-derived market
features; `router-search` exports predictions, dense diagnostics, offset
sensitivity, utility scores, and a markdown report. A rolling-only smoke run
completed at
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/router_search_smoke_fixed/`.
Fresh PineScript-aware labels were built at
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/`.

**Acceptance:** focused router/label tests pass and ruff is clean. Full
PineScript-KNN catalog execution remains in `IN_PROGRESS.md` because the
current KNN path is too slow for a large run.

**Links:** `docs/regime_router_search.md`,
`src/backtester/regime_router.py`,
`src/backtester/regime_labels.py`,
`src/backtester/strategy_discovery/features.py`.

---

## 2026-06-23 — Full rolling labels and router baseline evaluated

**What:** consumed the completed archive-only matrix with raw trades, built
daily 30-day rolling labels, and evaluated live-safe router baselines.

**Why now:** the partial existing-trades artifact had mixed coverage and could
not support label-grade router conclusions.

**Expected gain:** establish the first clean six-strategy rolling-label
benchmark for regime routing.

**Result:** `results/regime_matrix_archive_sol_2022_2025_trades/` contains six
raw strategy trade files, 1341 daily rolling labels all with six available
strategies, and router baseline artifacts. Oracle non-overlap return is
+1812.32%, while the default simple routers are far lower. A sensitivity pass
found `feature_knn_top2_60_40` with `lookback=180d`, `k=3` can reach +142.75%
on one start offset, but offset robustness favors `rolling_top2_mean_60_40`
median behavior.

**Acceptance:** docs updated with full results and next work moved to robust
router utility scoring.

**Links:** `docs/regime_rolling_router_baseline.md`,
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d/`.

---

## 2026-06-23 — Archive matrix params regression-checked

**What:** verified that the full archive matrix command resolves execution
params from `strategies/archive/*.json` `backtest_args`, not from stale CLI
defaults or legacy DSS `params`.

**Why now:** archive matrix reruns are expensive, and stale execution params
have caused wrong strategy replays before.

**Expected gain:** prevent another long run with wrong `risk_percent`, `rrr`,
TTL, trailing, `tp_pct`, or structural stop mode.

**Result:** effective args for all six archived strategies match the intended
archive execution params. Regression tests now lock both precedence and current
archive-file values.

**Acceptance:** focused regime tests pass and ruff is clean.

**Links:** `tests/backtester/test_regime_matrix.py`.

---

## 2026-06-23 — Partial rolling router baseline evaluated

**What:** added a reproducible `rolling-router-baseline` evaluator and scored
simple live-safe routers over the partial daily 30-day rolling labels.

**Why now:** the project needed to know whether the partial labels are enough to
continue detector/router work without another long matrix rerun.

**Expected gain:** avoid spending compute blindly, while still testing the
Plan B router mechanics.

**Result:** the partial artifact is useful for pipeline validation but not
enough for router selection. Overall `equal_weight_available` beats the rolling
and KNN routers, while the 2024-only subset favors KNN and the 2025-only subset
favors simpler allocation. The inconsistent strategy universe is now the main
limitation.

**Acceptance:** report written to `docs/regime_rolling_router_baseline.md`;
artifacts written under
`results/regime_matrix_archive_partial_existing_trades_2022_2025/rolling_labels_day_30d/router_baseline_min3/`;
focused tests and ruff pass.

**Links:** `src/backtester/regime_router.py`,
`docs/regime_rolling_router_baseline.md`.

---

## 2026-06-23 — Partial rolling label artifact from existing exact runs

**What:** assembled a partial `strategy_trades/` dataset from existing raw
trade artifacts whose execution params match the archive/Optuna best params,
then generated daily 30-day rolling labels from it.

**Why now:** the owner wanted to avoid another 9-hour matrix rerun if existing
trade artifacts were enough to test Plan B.

**Expected gain:** validate the rolling-label/router pipeline immediately while
preserving compute for only the reruns that prove necessary.

**Result:** created
`results/regime_matrix_archive_partial_existing_trades_2022_2025/` with copied
strategy trade CSVs, `source_trades_manifest.csv`, `strategy_coverage.csv`, and
`rolling_labels_day_30d/rolling_labels.csv`.

**Acceptance:** rolling labels built successfully with 1341 rows; focused
regime label/matrix tests pass; ruff is clean on touched files.

**Links:** `docs/regime_label_analysis.md`,
`docs/regime_performance_matrix.md`.

---

## 2026-06-23 — Plan B rolling label infrastructure

**What:** implemented the raw trade export and rolling label builder needed for
Plan B.

**Why now:** monthly labels were too coarse for a useful detector, and the
owner approved moving to the denser `features at T -> best strategy over
T..T+horizon` labeling path.

**Expected gain:** after one new archive-only matrix rerun, the project can
build daily 30-day rolling labels without additional strategy backtests.

**Result:** `archived-performance-matrix` now writes
`strategy_trades/<strategy_id>.csv`, and `backtester rolling-regime-labels`
builds daily/hourly forward labels from those trade exports.

**Acceptance:** focused regime matrix/label tests pass; ruff is clean for the
touched files. Owner-run commands are documented in `IN_PROGRESS.md`.

**Links:** `src/backtester/regime_labels.py`,
`docs/regime_performance_matrix.md`.

---

## 2026-06-23 — Monthly router baseline evaluated

**What:** evaluated the first monthly portfolio-router baselines over the
archive-only oracle label dataset.

**Why now:** after exact strategy classification failed, the next question was
whether a confidence-gated top-2 router could improve portfolio utility using
the existing monthly data.

**Expected gain:** identify a practical benchmark and avoid building a complex
detector before a simple router baseline is beaten.

**Result:** the feature-KNN top-2 router returned +42.09% with -6.00% max DD
over 2024-2025, but did not beat the simpler `rolling_top2_mean_60_40`
benchmark, which returned +66.51% with -12.58% max DD.

**Acceptance:** report compares oracle, equal-weight, rolling single best,
rolling top-2, and feature-KNN top-2 by return, drawdown, losing months, and
switching count.

**Links:** `docs/regime_router_baseline.md`,
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/router_baseline_report.md`.

---

## 2026-06-23 — Regime label analysis completed

**What:** analyzed the generated oracle label dataset for feature separation,
label stability, and simple live-safe detector baselines.

**Why now:** after the archive-only matrix and oracle labels were generated,
the project needed to know whether OHLCV features can already select the best
monthly strategy.

**Expected gain:** avoid prematurely building a hard strategy classifier if the
current labels/features do not support it.

**Result:** wrote `docs/regime_label_analysis.md` and local analysis artifacts
under `results/regime_matrix_archive_sol_2022_2025/oracle_labels/`. The best
walk-forward model only tied rolling-majority exact accuracy, so the next MVP
should be a confidence-gated top-2 portfolio router.

**Acceptance:** report ranks feature separation, flags 12 ambiguous buckets
with margin below 2%, and proposes the first detector/router baseline.

**Links:** `docs/regime_label_analysis.md`,
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/analysis_report.md`.

---

## 2026-06-23 — Oracle regime label dataset MVP

**What:** added the first offline oracle-label dataset builder for completed
archive performance matrices.

**Why now:** both regime matrices finished, and the clean archive-only matrix is
the source of truth for training labels. The next step was to convert monthly
strategy returns into `best_strategy` labels and attach detector-safe OHLCV
features.

**Expected gain:** future offline Regime Discovery, online Detector, and Router
work can consume a single reproducible CSV instead of recomputing oracle labels
by hand.

**Result:** added `backtester oracle-regime-labels`, generated
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/oracle_labels.csv`,
and wrote the feature/label contract into `docs/regime_detection.md`.

**Acceptance:** output has 48 monthly rows and 34 columns; summary shows all six
archived strategies are selected at least once and zero losing oracle buckets.
Focused pytest and ruff checks pass.

**Links:** `src/backtester/regime_labels.py`,
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/`.

---

## 2026-06-22 — NR4 VWAP robust archived for regime matrix

**What:** archived the NR4 VWAP robust candidate after the owner-run
execution-only Optuna completed.

**Why now:** the regime matrix should use frozen archived strategy columns
instead of mixing archived candidates with an active `--strategy` input.

**Expected gain:** the next archive-only matrix can be used as the cleaner
source of truth for regime discovery and labeler work.

**Result:** added
`strategies/archive/crypt_ensemble_h1_discovery_nr4_vwap_robust.json` and
`docs/archive/candidates/nr4_vwap_robust/` with execution params, provenance,
mandate snapshot, and monthly diagnostics from the 2022-2024 Optuna best-run.

**Acceptance:** archive JSON and docs are present; JSON files parse; the next
owner action is the archive-only matrix command in `IN_PROGRESS.md`.

**Links:** `results/optuna_nr4_vwap_robust_big_2022_2025/20260622_153157/`.

---

## 2026-06-22 — Regime matrix progress control

**What:** added explicit progress control for
`backtester archived-performance-matrix`.

**Why now:** after archive replay fixes, the owner restarted the matrix and saw
no progress bar for several minutes because strategy-level progress had been
disabled inside matrix runs.

**Expected gain:** long `crypt_ensemble` matrix runs again show bar-level
progress, while operators can still opt out with `--no-strategy-progress`.

**Result:** added `--strategy-progress/--no-strategy-progress`, defaulting to
enabled, and print `Matrix strategy starting: ...` before each strategy.

**Acceptance:** command help shows the new flag; regime matrix tests pass; ruff
is clean.

**Links:** `src/backtester/__main__.py`.

---

## 2026-06-22 — Regime matrix archive replay fixes

**What:** fixed archived strategy replay behavior for the performance matrix.

**Why now:** the owner started the first matrix run and saw stale execution
params (`rrr=1.25`, `ttl=36`) plus nested progress bars from archived
`crypt_ensemble` configs.

**Expected gain:** matrix rows now reflect frozen archive execution params, and
interrupted matrix runs retain completed strategy outputs.

**Result:** synchronized old NR7/VWAP archive strategy JSONs with their
`execution_params.json`, disabled strategy-level progress inside matrix runs,
and made the matrix command write partial CSVs after each completed strategy.

**Acceptance:** archive JSONs parse and load to the expected execution params;
regime matrix tests pass; ruff is clean.

**Links:** `strategies/archive/`,
`src/backtester/__main__.py`.

---

## 2026-06-22 — Archived strategy performance matrix MVP

**What:** added the first archived/active strategy performance matrix builder.

**Why now:** the owner asked whether the regime matrix from
`docs/regime_detection.md` was real and then approved building it. The archive
now has enough research seeds to start infrastructure, even if it is not enough
for trustworthy regime labels yet.

**Expected gain:** future regime discovery can consume comparable
bucket-by-strategy behavior instead of hand-reading individual backtest
summaries.

**Result:** added `backtester archived-performance-matrix`, a spec under
`docs/regime_performance_matrix.md`, matrix CSV exports, and focused tests.

**Acceptance:** command help is covered; bucket aggregation/manifest/pivot tests
cover the matrix core. Owner-run command is documented in README.

**Links:** `docs/regime_performance_matrix.md`,
`src/backtester/regime_matrix.py`, `README.md`.

---

## 2026-06-22 — Archived WR45 Optuna research seeds

**What:** archived `smac_003335_double_bottom_body_to_range` and
`island_2023_021396_engulfing_bb_trend` after owner-run big Optuna completed.

**Why now:** the owner asked to move both tuned strategies into the archive and
freeze the execution parameters from each `best_trial.json`.

**Expected gain:** future regime discovery and detector training can use these
profitable but mandate-discarded signal families as labeled research evidence.

**Result:** added strategy JSON copies under `strategies/archive/` and archive
notes under `docs/archive/candidates/`, including execution params,
provenance, mandate snapshots, and monthly return CSVs.

**Acceptance:** both archive entries point to the local Optuna/best-run
artifacts and explicitly state `archive_reason=research_seed` with
`mandate_verdict=discard`.

**Links:** `docs/archive/candidates/smac_003335_double_bottom_body_to_range/`,
`docs/archive/candidates/island_2023_021396_engulfing_bb_trend/`.

---

## 2026-06-19 — Stage 1 WR gate made threshold-only

**What:** removed the hidden `tp_first > sl_first` requirement from the Stage 1
`weak_barrier_win_rate` gate.

**Why now:** after exposing `--stage1-min-wr`, the owner found that WR45 still
rejected candidates such as `island_2022_000210` because TP-first count was
below SL-first count. That made the CLI threshold partly ineffective below
50% WR.

**Expected gain:** research runs can intentionally use WR45 or any other
configured threshold without an implicit second WR filter.

**Result:** `DSSConfig.min_barrier_win_rate` is now the only Stage 1 win-rate
gate. Signal-count, TP-first-rate, and overtrading gates are unchanged.

**Acceptance:** added a regression test where WR is above 0.45 while
`tp_first < sl_first`; the candidate passes Stage 1. DSS tests and ruff pass.

**Links:** `src/backtester/strategy_discovery/dss_stage1.py`,
`docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-19 — Stage 1 WR threshold exposed in CLI

**What:** added `--stage1-min-wr` to `backtester search-signals` and
`backtester search-signals-matrix`.

**Why now:** the owner wants to rerun the all-catalog matrix with a softer WR45
Stage 1 gate while keeping the existing signal-count and overtrading filters
unchanged.

**Expected gain:** operator runs can explore lower-WR candidates without code
edits, while the Stage 1 promotion contract remains centralized in
`DSSConfig`.

**Result:** the flag sets `DSSConfig.min_barrier_win_rate` for direct searches
and is passed through to every child process launched by the matrix command.

**Acceptance:** DSS tests pass, ruff is clean for the touched CLI/tests, and
both command help outputs show `--stage1-min-wr`.

**Links:** `src/backtester/__main__.py`, `README.md`.

---

## 2026-06-19 — Full PineScript SMC/ICT DSS catalog slice

**What:** completed the remaining PineScript-derived catalog transfer from
`smc.pine` into native DSS primitives.

**Why now:** the first PineScript slice intentionally skipped the large
SMC/ICT surface. The owner asked to continue and finish the catalog transfer in
this session so future `pinescript_v1` / `all` searches include the full
TradingView idea set.

**Expected gain:** DSS can now search BOS/CHoCH, fair-value gaps, equal
highs/lows, premium/discount zones, and order-block retests in the same staged
Stage 1 pipeline as the earlier Supertrend, UT Bot, Squeeze, WaveTrend, MACD,
ADX/DI, VixFix, pivot-volume, trendline, and killzone primitives.

**Result:** added SMC feature columns, five SMC triggers, and five SMC filters
to `pinescript_v1`. Updated the PineScript catalog spec and removed the
completed backlog item.

**Acceptance:** DSS tests pass, ruff is clean, and mypy reports no issues on
the touched PineScript catalog/features/tests.

**Links:** `docs/discovery/pinescript_catalog_v1.md`,
`src/backtester/strategy_discovery/features.py`,
`src/backtester/strategy_discovery/pinescript_catalog.py`.

---

## 2026-06-19 — DSS matrix launch command

**What:** added `backtester search-signals-matrix`, an operator command that
launches the standard DSS algorithm set in parallel.

**Why now:** the owner was repeatedly starting five separate commands for
`staged`, `catcma_qd`, `island_qd`, `hyperband_qd`, and `smac_qd` when testing
the same catalog/window setup.

**Expected gain:** one command can start all search backends, distribute them
across OS-scheduled cores, keep per-algorithm output directories, and collect
child logs.

**Result:** the wrapper starts one `search-signals` subprocess per algorithm,
uses the standard seeds, writes `run.log` in each output directory, waits for
all children, and fails if any child exits non-zero.

**Acceptance:** CLI help and invalid-algorithm tests cover the new command.

**Links:** `src/backtester/__main__.py`, `README.md`.

---

## 2026-06-19 — Regime detection roadmap documented

**What:** converted the owner-provided `test.md` notes into project
documentation and removed the temporary source file.

**Why now:** the owner defined the next strategic direction: continue running
strategy searches while building regime infrastructure, archive useful
non-mandate strategies, and later use that archive to train a regime detector
and portfolio router.

**Expected gain:** future agents can work from durable specs and backlog items
instead of reconstructing the plan from chat or a temporary note.

**Result:** added `docs/regime_detection.md`, ADR-0041, and backlog tasks for
the archived-strategy performance matrix, Regime Discovery/Labeler, online
Detector, Portfolio Router scoring, and future non-OHLCV detector features.
Updated candidate archive policy to allow `regime_seed` and `research_seed`
entries.

**Acceptance:** `test.md` was removed; README, archive docs, backlog, ADR, and
changelog all point to the regime-aware routing direction.

**Links:** `docs/regime_detection.md`,
`docs/decisions/0041-regime-discovery-from-strategy-behavior.md`,
`docs/backtester/candidate_archive.md`.

---

## 2026-06-19 — DSS manual replay execution defaults

**What:** fixed `backtester run` replay for DSS manual/optimizer candidate JSONs
that store execution values directly in flat `params`.

**Why now:** the owner replayed
`dssv2_013321_macd_squeeze_wr4685_cli_exec.json` and saw the strategy log print
`risk_percent=0.5`, `rrr=6.0`, `trail_distance_atr=0.25`, and
`position_ttl_bars=92`, while the actual backtest engine still used CLI
defaults (`risk_percent=1.0`, `rrr=2.0`, no trailing, no TTL).

**Expected gain:** manual DSS replays now match the execution parameters carried
by the candidate file, making Optuna best-run comparisons reproducible without
extra flags when `backtest_args` is absent.

**Result:** `build_backtest_args` now treats DSS flat execution params as
strategy-file defaults and still lets explicit `backtest_args` take precedence.

**Acceptance:** `tests/backtester/test_optimizer.py` passes; a direct
`build_backtest_args` check on the owner's WR46.85 JSON now returns
`risk_percent=0.5`, `rrr=6.0`, `trail_distance_atr=0.25`,
`trail_activation_rrr=6.0`, and `ttl=92`.

**Links:** `src/backtester/cli_runner.py`,
`results/dss_stage1_staged_pinescript_2023_atr_seed73023/manual_candidates/dssv2_013321_macd_squeeze_wr4685_cli_exec.json`.

---

## 2026-06-18 — Archived dssv2_013321 MACD/squeeze near-miss

**What:** shelved the manual PineScript candidate
`dssv2_013321_ps_macd_squeeze_recent` under the git-tracked candidate archive
and froze its best execution parameters.

**Why now:** the owner reviewed the 2023 Optuna best-run and decided to stop
active work on this candidate after the mandate snapshot showed 5 months below
the 15% floor and 2 monthly DD breaches despite strong single-year return.

**Expected gain:** future agents can inspect or revive the candidate without
reconstructing the PineScript Stage 1 run, Optuna artifact, or exact trailing
ATR execution settings.

**Result:** added `docs/archive/candidates/dssv2_013321_macd_squeeze_recent/`
with README, mandate snapshot, monthly mandate CSV, execution params, and
provenance; added frozen strategy JSON under `strategies/archive/`.

**Acceptance:** archive index links to the candidate; provenance points to the
discovery, Optuna, and best-run artifacts.

**Links:** `docs/backtester/candidate_archive.md`;
`results/dssv2_013321_big_optuna_2023_trail_atr/20260617_132218/best_trial.json`.

---

## 2026-06-18 — DSS Stage 1 ATR-scaled directional label

**What:** replaced DSS Stage 1 candidate-geometry evaluation with an
ATR-scaled directional label. Stage 1 now enters at next candle open, uses
closed-candle ATR14 as the symbol volatility scale, preserves the SOL reference
calibration of 0.7% favorable TP and 0.4% adverse SL, counts same-bar TP+SL
conservatively as SL, and reports unresolved end-of-window tails separately
from resolved TP/SL outcomes.

**Why now:** the owner clarified that fixed 0.7%/0.4% barriers are acceptable
for SOL but too strict for more volatile symbols such as TON. Stage 1 should
test whether a candidate predicts direction under comparable volatility, not
whether it already has a tuned execution geometry. Candidate RRR, risk percent,
TTL, `atr_sl_mult`, structural stops, fees, sizing, and trailing behavior
belong in later stages.

**Expected gain:** search algorithms can keep exploring different trigger and
filter spaces while Stage 1 uses one clean pass/fail contract. Good candidates
near the end of a window are no longer miscounted as losses just because their
future path is truncated.

**Result:** added `stage1_tp_move_pct`, `stage1_sl_move_pct`, and
`stage1_reference_atr_pct`; Stage 1 artifacts now include unresolved-tail and
percent MAE/MFE columns while keeping legacy column aliases for compatibility.
CatCMA-QD uses the shared Stage 1 advisory score instead of a local
stop-distance copy.

**Acceptance:** `tests/backtester/test_dss.py` 67/67 passed; ruff and mypy
clean on touched DSS modules/tests.

**Links:** `src/backtester/strategy_discovery/dss_stage1.py`,
`docs/discovery/direct_signal_search_v2.md`, `README.md`.

---

## 2026-06-17 — Unified DSS Stage 1 promotion contract

**What:** split DSS Stage 1 signal-viability evaluation into a shared
`dss_stage1` module and made every `search-signals` backend use the same
`Stage1Result.should_promote` contract before moving candidates to Stage 2.
`discover-strategies` remains legacy and outside this contract.

**Why now:** the owner wanted the search algorithms to own only candidate-space
exploration while Stage 1 owns pass/fail and diagnostic scoring. The old code
already shared most Stage 1 logic, but alternative backends did not all honor
`--stage-mode stage1` and the promotion condition was duplicated as
`passed + behavior`.

**Expected gain:** `staged`, `catcma_qd`, `island_qd`, `hyperband_qd`, and
`smac_qd` now search in different ways but feed candidates through one Stage 1
gate and artifact surface. Stage 1-only runs can compare catalogs/backend
proposal behavior without paying proxy/full backtest cost.

**Result:** added `stage1_near_misses.csv` so ranked rejected/specialist rows
remain visible after long runs; `stage1_ranked.csv` still contains only
promoted Stage 1 candidates. All DSS backends now stop before Stage 2/3 when
`--stage-mode stage1` is set.

**Acceptance:** `tests/backtester/test_dss.py` 64/64 passed; ruff clean and
mypy clean on touched DSS modules/tests.

**Links:** `src/backtester/strategy_discovery/dss_stage1.py`,
`docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-17 — Optuna trailing ATR search cleanup

**What:** removed trailing activation from the Optuna search space and kept
only trailing ATR distance as the tunable trailing-stop parameter. Also locked
execution tuning to the project policy: `max_positions = 0` and optimizer
target `mandate_score`.

**Why now:** the owner-run Optuna trial selected `rrr=2.75` with
`trail_activation_rrr=3.0`, which exposed that activation should not be an
independent parameter. In this model the activation point is the selected
`rrr`; the only question is how far the ATR trailing stop should sit after
activation.

**Expected gain:** reduce optimizer degrees of freedom and prevent misleading
trials caused by searching both the target level and a separate activation
level.

**Result:** user-facing backtest/diagnostic CLIs no longer expose
`--trail-activation-rrr*` options. `ParameterOptimizer` derives
`trail_activation_rrr = rrr` whenever `trail_distance_atr > 0`; if
`trail_distance_atr` is `0`, trailing is disabled. Best-run export uses the
same derivation.

`max_positions` is now normalized to `0` in `BacktestArgs` and
`FixedCandidateParams`, removed from user-facing CLI flags, ignored in
best-run params, and no longer searched by `ParameterOptimizer`. Optimizer
CLI/walk-forward no longer expose `--target`; they use `mandate_score`.

**Acceptance:** `tests/backtester/test_optimizer.py` and
`tests/backtester/test_fixed_candidate_report.py` 21/21 passed; ruff passed on
touched optimizer/CLI/grid/walk-forward files except pre-existing
`cli_runner.py` path-style lint debt; mypy passed on touched optimizer/grid and
walk-forward files; CLI help for `run`, `optimize`, `compare-fixed`,
`compare-grid`, and `signal-quality` shows only trail ATR controls.

**Links:** `src/backtester/optimizer.py`, `src/backtester/__main__.py`,
`README.md`.

---

## 2026-06-16 — PineScript-derived DSS catalog v1

**What:** added a separate `pinescript_v1` DSS trigger/filter catalog derived
from the PineScript files supplied under `pinescript/`.

**Why now:** the legacy DSS catalog has been heavily explored and the latest
WR55/10pd analysis showed it keeps collapsing into regime conflict rather than
finding robust 2022/2023 intersections. The owner asked to stop walking the old
space and try a fresh set of TradingView/PineScript-derived primitives.

**Expected gain:** give DSS a materially different vocabulary: Supertrend, UT
Bot-style ATR trail, squeeze release, WaveTrend, MACD phase, ADX/DI, Williams
Vix Fix, pivot/volume breaks, simple trendline breaks, and killzone/session
filters.

**Result:** `backtester search-signals` now accepts
`--catalog legacy|pinescript_v1|all`; default remains `legacy` for backwards
compatibility, while the active handoff instructs the owner to run
`--catalog pinescript_v1` only. `--stage-mode stage1` now stops before
backtests and exports `stage1_ranked.csv` plus `stage1_candidates/*.json`.
`--min-signals-per-week 4` makes the effective Stage 1 frequency gate about
209 signals on a full-year window. New closed-candle feature columns are
computed in the discovery dataset, the catalog is exported from
`backtester.strategy_discovery`, `SignalComposer` can replay PineScript
candidate JSONs, and `dss_state.json` records the selected catalog/mode.

**Acceptance:** `tests/backtester/test_dss.py` 58/58 passed; ruff clean and
mypy clean on touched DSS feature/catalog/CLI/test files.

**Links:** `docs/discovery/pinescript_catalog_v1.md`,
`src/backtester/strategy_discovery/pinescript_catalog.py`.

---

## 2026-06-16 — DSS regime-specialist Stage 1 artifacts

**What:** implemented DSS Stage 1 classification for `balanced` vs
`specialist:<window>` candidates.

**Why now:** WR55/10pd tail analysis showed the all-window Stage 1 gate was
discarding sparse regime-specific edge before Stage 2. The project needed the
artifact surface to preserve those specialists without pretending they are
mandate-ready.

**Expected gain:** future DSS runs can separate all-window robust candidates
from target-window specialists and decide later whether a routing/composition
layer is worth building.

**Result:** `stage1_viability.csv` now includes `candidate_class` and
`target_window`; specialists are written to `stage1_specialists.csv` and
`stage1_specialists.jsonl` only when explicit specialist capture is requested;
only balanced candidates remain `passed=True` and continue toward Stage
2/export. `summary.md` reports Stage 1 specialist count. The default all-window
path keeps the old early-reject behavior so owner-scale runs stay practical.

**Acceptance:** `tests/backtester/test_dss.py` 52/52 passed; ruff clean on
touched files; mypy clean on touched DSS CLI/config/module/test files.

**Links:** `src/backtester/strategy_discovery/dss_v2.py`,
`docs/discovery/direct_signal_search_v2.md` §7.1.

---

## 2026-06-16 — DSS WR55/10pd tail analysis

**What:** analyzed the owner-supplied
`dss_wr55_10pd_searches_20260616_142549_tar.gz` archive containing five
WR55/10pd DSS Stage 1 searches.

**Why now:** `results/` artifacts are gitignored and the previous handoff only
had a markdown snapshot. The project needed a concrete decision before running
more identical DSS seeds.

**Expected gain:** identify whether the current failure was an implementation
bug, a compute-budget issue, or a real 2022/2023 regime conflict.

**Result:** documented that the completed 1.2M-trial 2022-first run produced
31,241 2022-pass candidates and none that also passed 2023; the 2023-first
snapshots produced 38 2023-pass candidates, all rejected by
`too_few_signals:2022`. The next implementation choice is a DSS
regime-specialist Stage 1/archive path, not a sixth optimizer backend.

**Acceptance:** analysis recorded in
`docs/discovery/dss_wr55_10pd_tail_analysis.md`; DSS v2 spec updated with
`balanced` vs `specialist:<window>` candidate classes; backlog now points at
the implementation task.

**Links:** `docs/discovery/dss_wr55_10pd_tail_analysis.md`,
`docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-12 — DSS Stage 1 path-aware barrier label

**What:** added a cheap path-aware TP/SL/TTL barrier label to DSS Stage 1.
Stage 1 now measures whether a signal reaches its favorable ATR barrier before
the adverse ATR barrier, records MAE/MFE and bars-to-TP metrics, and rejects
candidates below configurable `min_barrier_tp_first_rate` and
`min_barrier_win_rate` floors.

**Why now:** the owner challenged the earlier directional-label design. A pure
"price eventually moved N ATR in the predicted direction" label can rank
signals that would have hit a realistic stop before the favorable move.

**Expected gain:** keep the fast directional-search idea while making it
tradeability-aware before expensive donor backtests. CatCMA/Hyperband/Island
cheap ranking now also rewards higher TP-first rates and penalizes SL-first,
timeouts, and large adverse excursion.

**Result:** `stage1_viability.csv` gains `barrier_*` columns; same-bar TP+SL is
counted conservatively as `sl_first`; the barrier label now uses the same
next-open entry and resolved `sl_rrr` levels as Stage 2 donor execution; Stage
1 requires `barrier_win_rate >= 55%` and `tp_first > sl_first`; DSS tests cover
TP-first pass-through, same-bar SL-first rejection, low win-rate rejection, and
gap cases where Stage 2 would reject the trade.

**Acceptance:** `tests/backtester/test_dss.py` 48/48 passed; ruff and mypy clean
on touched DSS modules/tests.

**Links:** `docs/discovery/direct_signal_search_v2.md`, `src/backtester/strategy_discovery/dss_v2.py`.

---

## 2026-06-12 — SMAC-QD random-forest DSS backend

**What:** added `backtester search-signals --algorithm smac_qd`, a SMAC-style
conditional surrogate backend using `sklearn.ensemble.RandomForestRegressor`.

**Why now:** the owner wants five materially different DSS search algorithms to
run before the next result-inspection session. After staged DSS, CatCMA-QD,
Island-QD, and Hyperband-QD, a random-forest surrogate is the next distinct
search pressure.

**Expected gain:** learn promising conditional trigger/filter/execution regions
from observed scores, then evaluate RF-selected infill candidates instead of
only random, weighted, islanded, or rung-based candidates.

**Result:**
- Added ADR-0040.
- Added `smac_qd.py`: fixed conditional candidate encoder,
  `RandomForestRegressor` surrogate, tree-dispersion uncertainty, acquisition
  scoring, random bootstrap, proposal selection, and DSS Stage 1/2/3 reuse.
- Added `smac_qd_proposals.csv`, `smac_qd_observations.csv`, and
  `smac_qd_state.csv` artifacts.
- Added CLI option value `--algorithm smac_qd`.
- Updated README, DSS spec, `IN_PROGRESS.md`, `BACKLOG.md`, and `IDEAS.md` so
  the next agent inspects five algorithm outputs rather than continuing
  optimizer implementation.

**Acceptance:** `tests/backtester/test_dss.py` 44/44 passed; ruff and mypy
clean on touched modules/tests.

**Links:** ADR-0040, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-12 — Hyperband-QD DSS backend

**What:** added `backtester search-signals --algorithm hyperband_qd`, a
successive-halving quality-diversity backend.

**Why now:** staged DSS v2, CatCMA-QD, and Island-QD were already available for
parallel owner runs. The next distinct backend needed formal budget allocation
instead of another sampler variant.

**Expected gain:** weak candidates pay only cheap Stage 1 viability, while
behavior-diverse top fractions advance through one-window proxy,
multi-window proxy, and full all-window scoring.

**Result:**
- Added ADR-0039.
- Added `hyperband_qd.py` with Stage 1 for all generated candidates, capped
  rung promotions, `hyperband_rungs.csv`, `hyperband_qd_state.csv`, and normal
  DSS archive/manifest/candidate artifacts.
- Added CLI option value `--algorithm hyperband_qd`.
- Updated README and DSS v2 docs with the command and artifact contract.
- Removed the Hyperband implementation task from `IN_PROGRESS.md` and
  `BACKLOG.md`.

**Acceptance:** `tests/backtester/test_dss.py` 41/41 passed; ruff and mypy
clean on touched modules/tests.

**Links:** ADR-0039, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-12 — DSS optimizer handoff for next agent

**What:** documented the next algorithm sequence after the current staged /
CatCMA-QD / Island-QD runs.

**Why now:** the owner plans to launch additional parallel searches on idle
machines, but wants each launch to use a meaningfully different algorithm.

**Expected gain:** the next agent can start implementing Hyperband-QD without
reconstructing the research discussion from chat.

**Result:**
- Added an `IN_PROGRESS.md` handoff for `--algorithm hyperband_qd`.
- Added `BACKLOG.md` tasks for Hyperband-QD and later SMAC-like surrogate QD.
- Added `IDEAS.md` shortlist of remaining research algorithms and recommended
  order.

**Acceptance:** next-agent docs state that Hyperband-QD is first, SMAC-like is
second, and full CatCMAwM should wait for promising families.

---

## 2026-06-12 — Island-QD DSS backend for Railway search

**What:** added an opt-in `--algorithm island_qd` backend for
`backtester search-signals`.

**Why now:** local CatCMA-QD showed a regime/window conflict: after about 23.7k
generated candidates, no proxy candidate had robust or min score above `-5000`.
Best candidates could be passable on one window while failing `2022`.

**Expected gain:** Railway can now run a materially different search that
discovers per-window specialists before occasional all-window robust checks.

**Result:**
- Added ADR-0038.
- Added `island_qd.py`: per-window models, rotating target windows, target-only
  Stage 2 scoring, periodic robust Stage 3 checks, `island_scores.csv`, and
  per-window state CSVs.
- Added CLI option value `--algorithm island_qd`.
- Changed `railway.toml` to start the Island-QD search worker and write
  artifacts under `data/results/`.
- Added a three-machine active search matrix to `IN_PROGRESS.md`.
- Updated README, DSS spec, and task handoff with Railway start command.

**Acceptance:** `tests/backtester/test_dss.py` 39/39 passed; ruff and mypy
clean on touched modules/tests.

**Links:** ADR-0038, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-11 — CatCMA-QD experimental DSS backend

**What:** added an opt-in `--algorithm catcma_qd` backend for
`backtester search-signals`, plus `--seed` for non-duplicative parallel search
runs.

**Why now:** the owner started a 120k default DSS v2 run on the work machine.
Running the same deterministic staged generator at home would mostly duplicate
that candidate sequence, so the project needed a materially different search
pressure for the same three-day window.

**Expected gain:** CatCMA-QD explores mixed trigger/filter/execution spaces with
an adaptive probability model while preserving DSS artifacts and replayable
candidate JSONs for `compare-fixed`.

**Result:**
- Added ADR-0037 accepting the experimental CatCMA-inspired backend.
- Added `catcma_qd.py`: weighted mixed-variable population sampler, elite-based
  updates, DSS Stage 1/2/3/4 reuse, and `catcma_qd_state.csv`.
- Added CLI options `--algorithm staged|catcma_qd` and `--seed`.
- Capped expensive Stage 2 proxy backtests per CatCMA-QD batch after the first
  owner run showed 435 proxy evaluations in the first 591 candidates and an ETA
  above six days.
- Updated README, DSS v2 spec, task handoff, and candidate-validation backlog.

**Acceptance:** `tests/backtester/test_dss.py` 38/38 passed; ruff clean on
code/docs touched; mypy clean on touched modules and DSS tests.

**Links:** ADR-0037, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-11 — DSS v2 staged quality-diversity implementation

**What:** replaced the operator-facing `backtester search-signals` path with
DSS v2 staged quality-diversity search. The old Optuna sampler mode is retired
from CLI usage; removed v1-only options fail with a DSS v2 message.

**Why now:** the owner-run DSS v1 journal showed structural search failure:
about 16.5k complete trials, best robust `min(score)` **-4626.74**, zero trials
above `-500`, and elite collapse into `pt_ema_cross + rrr=4.0 + wide ATR stop`.

**Expected gain:** expensive full backtests are spent only after cheap signal
viability and proxy stages, while a quality-diversity archive preserves
different trigger/behavior families for later 2025 holdout validation.

**Result:**
- Added `DSSCandidate` and behavior descriptors.
- Added `DSSArchive` with per-cell robust / average / low-drawdown elites.
- Added `dss_v2.py` staged runner: Stage 0 candidates, Stage 1 viability,
  Stage 2 proxy scores, Stage 3 full mandate scores, Stage 4 candidate export.
- `search-signals --help` no longer exposes `--sampler`, `--resume`,
  `--max-filters`, or `--accept-min-score`.
- Stage artifacts include `stage1_viability.csv`, `stage1_rejections.csv`,
  `stage2_proxy.csv`, `stage3_full_scores.csv`, `archive.json`, `archive.md`,
  `score_history.csv`, `candidate_manifest.*`, and `candidates/*.json`.

**Acceptance:** ruff clean; mypy clean on touched modules; 32 DSS tests pass,
including archive diversity, robust replacement, stage rejections, v1 resume
guard, exported JSON replay through `DSSStrategy`, and CLI hidden-option checks.

**Links:** ADR-0036, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-11 — DSS v1 diagnosis and DSS v2 rewrite spec

**What:** inspected the live DSS journal and documented the replacement design
for `backtester search-signals`.

**Why now:** the owner observed that the long DSS run looked stuck in a local
search zone. Journal analysis confirmed the concern: about 16.5k completed
trials in `results/dss_sol_run_5k/study.journal`, best robust `min(score)`
only **-4626.74**, zero trials with `min_score > -500`, and top candidates
collapsed into `pt_ema_cross + rrr=4.0 + wide ATR stop`.

**Expected gain:** the next implementation session can replace the command
directly instead of spending another session researching sampler options.

**Result:**
- ADR-0036 accepts replacing DSS v1 with staged quality-diversity search.
- `docs/discovery/direct_signal_search_v2.md` defines the full implementation
  contract: staged viability/proxy/full scoring, quality-diversity archive,
  robust scalar fitness, resume behavior, reports, tests, and next-agent plan.
- ADR-0035 and the v1 DSS spec are marked superseded.
- `IN_PROGRESS.md` now points the next agent at the DSS v2 rewrite.
- `BACKLOG.md` no longer asks the owner to run the retired NSGA-II DSS path.

**Acceptance:** docs now clearly say to rewrite `search-signals` in place,
remove the v1 sampler path from operator usage, and implement DSS v2 from the
new spec.

**Links:** ADR-0036, `docs/discovery/direct_signal_search_v2.md`.

---

## 2026-06-10 — Direct Signal Search (DSS) — full implementation

**What:** implemented all five phases of the DSS system (`backtester search-signals` command):
multi-objective Optuna (NSGA-II) directly optimizing `mandate_score` across multiple
independent time windows, replacing beam search with proxy win-rate metric.

**Why now:** walk-forward (ADR-0034) showed NR4 is regime-specific. DSS is the redesign
that fixes both root causes: objective (proxy → mandate_score) and constants (hardcoded
→ parameterized Optuna search space).

**Components:**
- `src/backtester/strategy_discovery/parameterized_triggers.py` — 20 trigger factories with `param_space()`
- `src/backtester/strategy_discovery/parameterized_filters.py` — 16 filter factories with `param_space()`
- `src/backtester/strategy_discovery/dss_config.py` — `TrialConfig`, `DSSWindowSpec`, `DSSSearchSpace`, `DSSConfig`, param types
- `src/backtester/strategy_discovery/signal_composer.py` — `SignalComposer.build()` → `GenerateFn`, `signal_df_to_ohlcv_aligned()`
- `src/backtester/strategy_discovery/dss_cache.py` — `DSSSignalCache` (LRU, keyed by `signal_cache_key + window_label`)
- `src/backtester/strategy_discovery/dss_objective.py` — `DSSObjective`, `compute_mandate_score()`, `run_dss_backtest()`
- `src/backtester/strategy_discovery/dss_report.py` — `write_dss_report()`, Pareto front, `pareto_front.json`, `summary.md`, `candidates/*.json`
- `src/backtester/strategies/dss_strategy.py` — `DSSStrategy` (registered, replays `TrialConfig` via `compare-fixed`, `walk-forward`)
- `src/backtester/__main__.py` — `search-signals` CLI subcommand wired
- `src/backtester/registry.py` — `DSSStrategy` registered
- `src/backtester/strategy_discovery/__init__.py` — all DSS exports
- `src/backtester/strategy_discovery/features.py` — bugfix: `pd.NA` → `np.nan` in float division
- `tests/backtester/test_signal_composer.py` — 11 unit tests (build, schema, SL/TP consistency, ATR-zero)
- `tests/backtester/test_dss.py` — 21 unit/integration tests (TrialConfig, WindowSpec, cache, catalogs, mandate_score, Pareto, 5-trial smoke)

**Acceptance:** 32/32 tests pass; `ruff check` clean; `backtester search-signals --help` works.

**Links:** ADR-0035, `docs/discovery/direct_signal_search.md`, `docs/discovery/signal_composer.md`.

---

## 2026-06-10 — Walk-forward validation command

**What:** implemented `backtester walk-forward` CLI command for IS/OOS rolling-window
validation of strategy candidates.

**Why now:** owner discovered NR4 returns ~0 or small negative on 3-year SOL/TON backtest
despite strong 2024-2025 performance. Walk-forward is the principled way to distinguish
genuine edge (generalizes out-of-sample) from overfitting to training regime.

**Components:**
- `src/backtester/walk_forward.py`: `generate_windows()` (rolling anchor-point), `run_walk_forward()`
  (per-window Optuna + OOS eval), `write_walk_forward_report()` (summary.md + summary.json).
- `src/backtester/__main__.py`: `walk-forward` CLI command wired.
- `tests/backtester/test_walk_forward.py`: 16 unit tests covering window generation,
  boundary conditions, degradation ratio, report building. All passing.
- `docs/decisions/0034-walk-forward-validation.md`: ADR recording methodology.

**Acceptance:** `uv run backtester walk-forward --help` shows the command;
`tests/backtester/test_walk_forward.py` 16/16 passed; ruff + mypy clean.

---

## 2026-06-09 — M4 live execution module + H1 scheduler integration

**What:** implemented the full M4 live execution module that mirrors `ExecutionSim`
exactly for real OKX order placement, and wired it into the H1 scheduler in `__main__.py`.

**Why now:** owner explicit mandate override — proceeding with NR4 (archive verdict)
before a promoted candidate is found.

**Components:**
- `settings.py` — `ExecutionSettings` (pydantic-settings, all keys EXECUTION_*)
- `position_state.py` — `LivePosition` + atomic JSON persistence
- `risk_calculator.py` — `LiveRiskCalculator` wrapping `BasicRiskModel` with identical
  logic to `ExecutionSim._try_open_position()`
- `signal_runner.py` — `LiveSignalRunner` running `crypt_ensemble.generate()` on live
  Parquet data for guaranteed signal parity; CPU-bound call runs in thread pool via
  `run_in_executor` to avoid blocking asyncio
- `okx_order_client.py` — `OKXTradingClient` placing market + embedded SL/TP orders
  via ccxt; dry_run=True default
- `executor.py` — `LiveExecutionManager` orchestrating H1 ticks: candle refresh →
  TTL/fill detection → signal check → entry
- `src/crypt/runtime/scheduler.py` — `H1Scheduler` added (fires at `*:02 UTC` every hour)
- `src/crypt/__main__.py` — `H1Scheduler` + `LiveExecutionManager` wired; reconcile on startup;
  safe shutdown (close() called in finally block)
- `.env.example` — all EXECUTION_* variables documented with inline comments
- 21 unit tests in `tests/execution/`, all passing; ruff + mypy strict clean

**ADRs:** ADR-0033 (`docs/decisions/0033-m4-live-execution-architecture.md`)
**Spec:** `docs/execution/live_execution.md`

**Acceptance:** 21/21 tests pass, ruff clean, module installable.

**Remaining before live activation:** wire into H1 scheduler in `__main__.py`;
integration test with dry_run=True; owner sign-off before dry_run=False.

---

## 2026-06-09 — Mandate-aware Optuna target

**What:** added `backtester optimize --target mandate_score`, a composite
objective aligned with ADR-0025 monthly return and DD gates.

**Result:** each trial now exports mandate user attrs (`mandate_score`,
monthly floor counts, DD breach count, capped monthly return summary, verdict).
`mandate_score` ranks capped monthly return after penalties for monthly
shortfall below 15%, DD excess beyond 10%, excess below-floor months, and 3+
consecutive losing months. Legacy targets remain available for diagnostics.

**Acceptance:** `tests/backtester/test_optimizer.py` covers mandate score on
synthetic monthly trades; ADR-0031 documents the formula and trade-off.

---

## 2026-06-09 — NR4 re-baseline after ADR-0029 + ADR-0030 (owner-run)

**What:** 12-month `compare-fixed` on NR4 frozen Optuna best params after
simulator policy changes.

**Result:** `results/nr4_optuna_best_dd0030_rebaseline/20260609_124449/` —
**discard** unchanged. Sum capped **+164.75%**, **8/12** months ≥15%, **2** DD
breaches (Feb −11.4%, Mar −20.21%; was 3 under rolling-peak DD). ADR-0029 had
no effect (identical to v3 overnight — entries already at 25×).

**Acceptance:** mandate truth recorded in `docs/candidates/nr4_vwap_robust.md`,
`IN_PROGRESS.md`, `investment_mandate.md` §9.

---

## 2026-06-09 — Drawdown from window-start capital (ADR-0030)

**What:** mandate and `ResultsAnalyzer` max DD now measure worst drop below
**window-start capital** on closed trades only; open positions ignored.

**Result:** ADR-0030; `mandate_report.py`, `results_analyzer.py`, tests in
`test_drawdown_from_window_start.py`, `test_mandate_report.py`; spec updates in
`docs/mandate_reporting.md`, `docs/investment_mandate.md` §3.1.

**Acceptance:** `uv run pytest tests/backtester/test_drawdown_from_window_start.py tests/backtester/test_mandate_report.py -q` green.

---

## 2026-06-09 — Isolated margin always on (ADR-0029)

**What:** removed `--is-isolated-futures` CLI flag; `ExecutionSim` always
enforces OKX isolated-margin leverage consistency (`ISOLATED_FUTURES_ALWAYS`).

**Result:** ADR-0029; `margin_policy.py`, `execution_sim.py`, CLI/runner cleanup;
tests updated. Prior runs without the flag used optimistic cross-margin semantics.

**Acceptance:** flag gone from `backtester run` / `optimize` / `compare-fixed` help.

---

## 2026-06-09 — Candidate archive layout + NR7/VWAP shelved

**What:** git-tracked archive for superseded discovery candidates; NR4 remains
active with near-miss plan.

**Result:** `docs/backtester/candidate_archive.md`; entries under
`docs/archive/candidates/` for NR7 and VWAP reclaim (mandate snapshots,
execution params, provenance); frozen JSON in `strategies/archive/`.
NR4 plan in `docs/candidates/nr4_vwap_robust.md`.

**Acceptance:** `investment_mandate.md` §5.2 references archive paths; README
Status points to NR4; archived strategies removed from `strategies/backtester/`.

---

## 2026-06-08 — Strategy discovery catalog v3 (OHLCV expansion)

**What:** expanded discovery catalog with ~97 new OHLCV-native blocks: candle
patterns, session/VWAP, volatility compression/expansion, candle sequences,
parameterized RSI/BB/volume thresholds.

**Why now:** full-year baseline discovery (label 1.0/24) showed limited trigger
diversity; owner requested +70–90 blocks to widen beam-search space beyond
`h1_candle_confirm` monopoly.

**Result:** `catalog_expansion.py` (+30 triggers, +67 filters), extended
`features.py`, merged into `triggers.py` / `filters.py`. Total **44 + 100**.
All v3 blocks discovery-only (no `convert.py` mapping yet).

**Acceptance:** `uv run pytest tests/backtester/test_strategy_discovery.py` green;
spec `docs/strategy_discovery.md` § v3 updated.

**Next:** owner-run discovery with v3 catalog (expect longer runtime than ~15 min
baseline); consider `--label-atr-mult 1.5 --label-horizon-bars 36` experiment.

---

## 2026-06-08 — Strategy execution context (ADR-0028)

Wired CLI execution flags into `strategy.generate()` so tp_pct runs do not
require structural stop anchors at the signal layer.

What was done:

- Added `StrategyExecutionContext` and metadata propagation from `Backtester`,
  `ParameterOptimizer`, and CLI runners.
- `crypt_ensemble` skips structural SL entry gate when `exit_geometry=tp_pct`;
  discovery-mapped filters unchanged.
- Optuna signal cache keys include execution-context fields that affect signals.
- Fixed optimizer `best_run/` cached re-export omitting `exit_geometry` /
  `tp_move_pct`.
- Spec: `docs/backtester/exit_geometry.md`; ADR-0028.

Owner validation (Jan SOL H1, NR7 candidate):

- Rerun v2: **11 trades**, **+3.36%** (`nr7_tp_pct_jan_rerun_v2/`).
- Jan Optuna v2 best: **+6.30%**, PF 2.29, `tp=0.008`, `rrr=1.75`, `ttl=36`
  (`nr7_tp_pct_optuna_jan_v2/`).

---

## 2026-06-08 — TP-first exit geometry (ADR-0027)

Added `exit_geometry=tp_pct`: fixed gross TP move from entry, SL derived via
`rrr`, structural SL policy at exit layer (`cap` / `ignore` / `reject`).

What was done:

- `exit_geometry.py`, `risk_model.py`, `ExecutionSim` integration.
- CLI flags on `run`, `optimize`, `compare-fixed`; Optuna `--tp-move-pct-low/high/step`.
- Spec `docs/backtester/exit_geometry.md`; ADR-0027.

---

## 2026-06-08 — NR7 v2 shortlist donor conversion (code)

Prepared donor execution path for v2 discovery top candidate
`h1_nr7_breakout__bb_squeeze__h4_context_aligned`.

- `h1_nr7_breakout` trigger + `bb_squeeze` / `h4_context_aligned` filter mapping
  in `crypt_ensemble` and `convert.py`.
- Checked-in config
  `strategies/backtester/crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json`.
- Owner-run SL-first `compare-fixed`: mandate discard but +25.6% capped sum
  (`results/crypt_h1_discovery_nr7_bb_squeeze_sol_2025/20260608_124701/`).
- tp_pct tuning tracked in `DONE.md` 2026-06-08 execution-context entry.

---

## 2026-06-08 — Discovery catalog v2 (OHLCV-only)

Expanded `discover-strategies` with OHLCV-only triggers and filters from
`IDEAS.md` (owner-approved slice).

What was done:

- **+6 triggers:** `h1_ema_cross`, `h1_rsi_reversal`, `h1_bb_rejection`,
  `h1_engulfing`, `h1_inside_bar_breakout`, `h1_nr7_breakout`.
- **+15 filters:** EMA stack, SMA20/RSI/ROC alignment, volatility low/high,
  BB squeeze/wide, candle anatomy, London/NY session, volume above median,
  trend strength max.
- Extended `features.py` (EMA, RSI, Bollinger, bar anatomy, ROC, hour UTC).
- Progress estimator uses dynamic catalog size.
- Spec updated in `docs/strategy_discovery.md` §7–8.

Acceptance: 14 triggers + 33 filters; focused pytest; ruff; mypy strict on
`strategy_discovery/`. v2 blocks discovery-only (no donor conversion yet).

---

## 2026-06-08 — Discovery shortlist donor conversion

Converted the selected full-year discovery candidate into a donor-executable
`crypt_ensemble` diagnostic config.

What was done:

- Added `backtester convert-discovery-strategy` and
  `src/backtester/strategy_discovery/convert.py`.
- Extended `crypt_ensemble` with `h1_momentum_burst` and discovery-aligned
  filters (`block_d1_h4_context_reversal`, `min_trend_strength_atr`,
  `min_volume_median_ratio`).
- Checked in
  `strategies/backtester/crypt_ensemble_h1_discovery_momentum_burst_short.json`
  for
  `h1_momentum_burst__avoid_low_volume__block_context_reversal__side_short_only__trend_strength_min`.
- Documented conversion semantics in `docs/strategy_discovery.md` §13 and left
  the owner-run SOL 2025 monthly `compare-fixed` handoff in
  `docs/tasks/IN_PROGRESS.md`.

Acceptance:

- conversion command + checked-in strategy config + focused tests;
- owner-run execution validation completed 2026-06-08 → **mandate discard**
  (`results/crypt_h1_discovery_momentum_burst_sol_2025/20260608_114552/`).

## 2026-06-08 — Strategy discovery constructor MVP

Completed the P0 implementation of the strategy discovery constructor.

What was done:

- Added `src/backtester/strategy_discovery/` with discovery event contracts,
  primary/context features, eight initial H1 triggers, eighteen initial
  filters, fixed ATR-barrier forward labeling, Wilson-based scoring, staged
  beam search, and artifact export.
- Wired `backtester discover-strategies` into the root CLI.
- Supported both contiguous `--symbol --from --to` mode and repeated
  `--window label:SYMBOL:YYYY-MM-DD:YYYY-MM-DD` mode.
- Exported `config.json`, `candidates.csv`, `candidates.md`,
  `search_trace.csv`, `rejected.csv`, and discovery-native
  `best_candidates/rank_*` strategy/event/report files.
- Added focused tests for trigger output, labeler outcomes, filter
  pass/reject reasons, no-lookahead H4/D1 context alignment, sample-size
  scoring, beam de-duplication through the exported candidate IDs, and CLI
  artifact creation.

Why now:

- Manual H1 trigger/filter search was stuck in one-off JSON branches and
  repeated owner-run commands. This command gives the owner one unattended job
  that can produce a ranked shortlist before execution backtests and Optuna.

Expected gain:

- Future sessions can inspect one discovery report instead of asking the owner
  to run another intermediate trigger/filter backtest.

Acceptance:

- The owner can run `uv run backtester discover-strategies ...` and receive a
  timestamped artifact directory with ranked candidates and best-candidate
  event files.

Verification:

- `uv run pytest tests/backtester/test_strategy_discovery.py -q`
- `uv run ruff check src/backtester/strategy_discovery src/backtester/__main__.py tests/backtester/test_strategy_discovery.py`
- `uv run mypy src/backtester/strategy_discovery src/backtester/__main__.py tests/backtester/test_strategy_discovery.py`
- `uv run ruff format --check src/backtester/strategy_discovery src/backtester/__main__.py tests/backtester/test_strategy_discovery.py`
- `uv run backtester discover-strategies --help`

## 2026-06-08 — H1 density review and trigger-first reset

Completed the sparse-branch density review and reset the next search protocol
to trigger-first discovery.

What was done:

- Compared the structural H1 baseline against `age6/noOB` without the
  `2..4 ATR` distance filter on the same three visual-review windows.
- Added raw one-trigger H1 diagnostic strategy configs for candle confirm,
  sweep reversal, structure break, and order-block retest.
- Documented the trigger-first reset in `docs/crypt_ensemble_mtf.md`.

Artifacts:

- Baseline density:
  `results/crypt_h1_visual_review_baseline_density/20260607_210508/`.
- Age6/noOB density:
  `results/crypt_h1_visual_review_age6_no_ob_density/20260607_211115/`.

Result:

- Baseline remained sparse and weak: TON Feb `+3.15%` on 10 trades, SOL Jan
  `-3.74%` on 10 trades, SOL Mar `-0.05%` on 7 trades.
- Age6/noOB did not solve density or quality: TON Feb `+3.17%` on 13 trades,
  SOL Jan `-4.16%` on 8 trades, SOL Mar `-0.05%` on 7 trades.
- Decision: stop optimizing this filtered H1 branch. Search raw triggers at
  `rrr = 1.0`, rank by trade count and win rate before PnL, then add filters
  one at a time only after a measurable trigger exists.

Verification:

- Inspected owner-run `windows.csv`, `mandate_summary.csv`, `trades.csv`,
  `trade_diagnostics.csv`, and generated `trade_chart.html` artifacts.

## 2026-06-07 — Visual verdict workflow and no-TTL falsification

Completed the first owner/agent verdict pass using the automatic HTML reports.

What was done:

- Recorded the visual-verdict workflow in `docs/backtester_migration.md`.
- Treated the owner's chart verdict as strategy-search evidence:
  too few trades, and TTL should be tested off.
- Ran the same reviewed windows with `--ttl 0` for
  `strategies/backtester/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4.json`.
- Updated `IN_PROGRESS.md` with the combined verdict and the next concrete
  density-review commands.

Artifacts:

- TTL-36 visual review:
  `results/crypt_h1_visual_review/20260607_203324/`.
- No-TTL falsification:
  `results/crypt_h1_visual_review_no_ttl/20260607_204930/`.

Result:

- Sparse execution is confirmed: only `5-8` trades per reviewed month, with no
  month near the `+15%` mandate floor.
- No-TTL is rejected for this branch. Window returns worsened from
  TON Feb `+6.07%` to `+4.30%`, SOL Jan `-2.70%` to `-3.69%`, and SOL Mar
  `-0.48%` to `-2.62%`.
- TTL exits mostly turned into stop-loss exits, so TTL is currently acting as a
  damage-control rule rather than the cause of sparse entries.

Decision:

- Keep `ttl = 36` for the current H1 branch.
- Next work should compare less sparse trigger/filter configs with continuous
  charts before another broad search.

Verification:

- Completed `backtester compare-fixed --ttl 0 --is-isolated-futures --jobs 3`
  on the three reviewed windows.
- Inspected `windows.csv`, `trades.csv`, and generated `trade_chart.html`
  artifacts.

## 2026-06-07 — Automatic TradingView trade chart frontend

Completed the P1 operator-facing chart frontend for donor backtest artifacts.

What was done:

- `ResultsAnalyzer.export_results(..., ohlcv_df=...)` now writes
  `ohlcv.csv` and `trade_chart.html` automatically for every normal donor
  artifact.
- Because all CLI flows export through `ResultsAnalyzer`, the chart is now
  produced by `backtester run`, optimizer `best_run/`, `compare-fixed`,
  `compare-grid`, and `signal-quality` whenever OHLCV is available.
- Reworked `src/backtester/trade_chart_report.py` to use TradingView
  Lightweight Charts instead of Plotly.
- The chart uses the continuous full OHLCV frame, not stitched
  `trade_candles/`, so candle history between trades is visible.
- The frontend shows candlesticks, tradeable signal markers, entry/exit
  markers, and entry/TP/SL/trailing-stop level segments.
- Kept `backtester trade-chart` only as a manual regeneration command for old
  artifacts or custom `--ohlcv` sources.
- Removed the temporary Plotly dependency from the root project lock.
- Documented the automatic frontend in `README.md` and
  `docs/backtester_migration.md`.

Why now:

- The latest H1 grid branch is economically rejected, and the next search
  direction should be visually falsified before spending compute on another
  signal/grid premise.

Expected gain:

- Faster owner/agent review of whether entries chase late candles, stops sit
  behind meaningful invalidation, and exits make structural sense on the chart.

Acceptance:

- Every backtester artifact exported with OHLCV gets `ohlcv.csv` and
  `trade_chart.html` without an extra command.
- Manual `uv run backtester trade-chart --run-dir <run_dir>` regenerates the
  same frontend from `ohlcv.csv`, or from an external full CSV/Parquet candle
  source passed with `--ohlcv`.

Verification:

- `uv run pytest tests/backtester/test_trade_chart_report.py tests/backtester/test_results_analyzer.py -q`
- `uv run mypy src/backtester/trade_chart_report.py`
- `uv run ruff check src/backtester/trade_chart_report.py tests/backtester/test_trade_chart_report.py tests/backtester/test_results_analyzer.py`

## 2026-06-07 — H1 distance-filter tiny execution grid

Completed the tiny execution-only grid for the best H1 trigger/stop-distance
diagnostic profile.

What was done:

- Ran `backtester compare-grid` for
  `strategies/backtester/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4.json`.
- Windows: SOL January/February/March 2025 and TON
  January/February/March/April 2025.
- Grid: `rrr = 1.0, 1.25, 1.5`; `ttl = 24, 30, 36, 42`;
  `max_positions = 1`; `risk_percent = 1.0`; monthly risk base; isolated
  futures.

Artifact:

- `results/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4_grid/20260607_192915/`.

Result:

- Best row: `rrr = 1.5`, `ttl = 36`, `max_positions = 1`.
- Best seven-window total return: `+6.18%` across `37` trades, worst DD
  `-2.26`.
- Window returns for the best row: SOL Jan `-2.70%`, SOL Feb `+3.31%`,
  SOL Mar `-0.48%`, TON Jan `+0.04%`, TON Feb `+6.07%`, TON Mar `+0.96%`,
  TON Apr `-1.02%`.
- The improvement is not robust: it depends heavily on TON February, and no
  month is near the `+15%` mandate floor.

Decision:

- Reject this H1 distance-filter diagnostic branch for SOL 2025 mandate
  validation and broad strategy-param Optuna.
- If the owner wants another search attempt, start from a new signal premise
  or a different backlog item rather than widening this branch.

Verification:

- Completed owner-run `backtester compare-grid --is-isolated-futures --jobs 3`.
- Inspected `grid.csv`; no `grid_errors.csv` was written.

## 2026-06-07 — H1 trigger freshness and stop-distance diagnostics

Completed the P0 diagnostic pass for H1 structural-trigger freshness/rule mix.

What was done:

- Added `strategies/backtester/crypt_ensemble_h1_trigger_age6_no_ob.json`.
- Added
  `strategies/backtester/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4.json`.
- Ran the standard seven-window isolated `compare-fixed` diagnostic for both
  configs.
- Compared both artifacts against the structural-trigger baseline
  `results/crypt_ensemble_h1_structural_trigger_bounded_isolated/20260607_183249/`.

Artifacts:

- `results/crypt_ensemble_h1_trigger_age6_no_ob_bounded/20260607_185632/`.
- `results/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4_bounded/20260607_191049/`.

Result:

- Removing `h1_order_block_retest` and widening trigger freshness to 6 H1 bars
  was weaker than baseline: `+0.41%` total, `52` trades, worst DD `-3.44`.
- Adding a `2..4 ATR` signal stop-distance filter improved the bounded total
  to `+3.78%`, reduced worst DD to `-2.23`, and reduced trade count to `39`.
- The improved diagnostic removed the harmful `1_2_atr` bucket and left only
  `2_3_atr` (`20` trades / `+10.19` PnL) and `3_4_atr` (`19` trades /
  `+367.12` PnL).
- No month passed the `+15%` mandate floor. SOL is only technically
  `full_optuna` over the three-month diagnostic slice; TON remains `discard`
  over four months.

Decision:

- Do not run broad strategy-param Optuna or SOL 2025 mandate validation on
  either diagnostic config yet.
- The only justified next compute step is a tiny execution-only grid for
  `crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4.json` to check whether
  fixed `rrr = 1.25` / `ttl = 36` is suppressing a still-usable narrow signal.

Verification:

- `uv run pytest tests/backtester/test_crypt_ensemble_strategy.py -q`
- Completed owner-run `backtester compare-fixed --is-isolated-futures --jobs 3`
  for both diagnostic configs.
- Inspected `windows.csv`, `mandate_summary.md`, per-window `signals.csv`, and
  per-window `trades.csv`.

## 2026-06-07 — H1 structural-trigger bounded validation

Completed the bounded validation for the rewritten H1 structural-trigger
strategy.

What was done:

- Ran the standard seven-window `compare-fixed` diagnostic for
  `strategies/backtester/crypt_ensemble_h1.json`.
- Windows: SOL January/February/March 2025 and TON
  January/February/March/April 2025.
- Execution: `rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`,
  `max_positions = 1`, monthly risk base, isolated futures.
- Generated `setup_attribution.csv` / `setup_attribution.md` from the saved
  per-window `signals.csv` and `trades.csv`.

Artifacts:

- Final isolated acceptance artifact:
  `results/crypt_ensemble_h1_structural_trigger_bounded_isolated/20260607_183249/`.
- Earlier non-isolated diagnostic artifact:
  `results/crypt_ensemble_h1_structural_trigger_bounded/20260607_181623/`.

Result:

- Seven-window total return was roughly `+1.32%` across `57` trades.
- SOL Jan/Feb/Mar summed `-0.69%`; no SOL month passed the `+15%` floor.
- TON Jan/Feb/Mar/Apr summed `+2.01%`; TON mandate verdict was `discard`
  because all four months were below the `+15%` floor.
- Mandate summary: SOL was `full_optuna` only in the narrow three-month
  technical sense; this is not a promote or archive candidate.
- Structural trigger flow was sparse: `227` tradeable signals and `57`
  executed trades out of `2685` active setup rows.
- Trigger attribution: `h1_structure_break` had `37` trades / `+56.27` PnL;
  `h1_sweep_reversal` had `7` trades / `+88.50` PnL;
  `h1_order_block_retest` had `13` trades / `-13.98` PnL.
- Stop-distance attribution found a major bad bucket: `1_2_atr` had `11`
  trades / `-711.48` PnL, while `0_1_atr`, `2_3_atr`, and `3_4_atr` were
  positive in this slice.

Decision:

- Do not run broad Optuna or SOL 2025 mandate validation on this baseline.
- Next work should tune H1 trigger freshness/rule composition and the
  stop-distance diagnostic issue first, then rerun the same seven-window
  isolated report.

Verification:

- Completed owner-run `backtester compare-fixed --is-isolated-futures --jobs 3`.
- Inspected `windows.csv`, `monthly_mandate.csv`, `mandate_summary.csv`,
  `signals.csv`, `signal_diagnostics.csv`, and generated
  `setup_attribution.csv`.

## 2026-06-07 — H1 structural-trigger strategy rewrite

Completed the owner-directed rewrite of the H1 `crypt_ensemble` entry
contract.

What changed:

- Replaced the old implicit H1 candle-colour entry path with explicit
  `trigger_rules` wiring.
- Added default H1 structural trigger rules:
  `h1_sweep_reversal`, `h1_structure_break`, and `h1_order_block_retest`.
- Kept `h1_candle_confirm` available only as an explicit legacy diagnostic
  rule.
- Updated all `crypt_ensemble_h1*.json` strategy configs to use the new
  structural trigger rules.
- Updated `docs/crypt_ensemble_mtf.md` and README to document the new
  contract.
- Added a backlog task for a future standalone interactive HTML trade chart
  report; no report implementation or Plotly dependency was added in this
  session.

Why:

- Strategy review found that the previous H1 path reused the H4 ensemble
  verdict and entered on simple H1 candle colour. That made H1 a weak timing
  filter rather than a real trigger layer.
- Recent anchor/stop-distance filters were unstable across SOL March and TON
  February, indicating that stop-anchor filtering was being used to compensate
  for poor entry semantics.

Verification:

- `uv run pytest tests/backtester/test_crypt_ensemble_strategy.py -q`
- `uv run mypy src/backtester/strategies/crypt_ensemble.py`
- `uv run ruff check --select E,F,I --ignore E501 ...`
- `uv run ruff format --check ...`
- Short SOL H1 smoke:
  `/tmp/crypt_structural_h1_smoke/20260607_144558/` (`2025-01-01` →
  `2025-01-03`, 49 rows, no trades).

Next:

- Run bounded structural-trigger diagnostics over the standard SOL/TON window
  set before any strategy-param Optuna or SOL 2025 mandate run.

## 2026-06-07 — H1 pivot-only bounded validation

Completed the P0 bounded validation for the `pivot_only` structural-stop
filter.

What was done:

- Ran `backtester compare-fixed` for
  `strategies/backtester/crypt_ensemble_h1_filter_pivot_only.json`.
- Windows: SOL January/February/March 2025 and TON
  January/February/March/April 2025.
- Execution: `rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`,
  `max_positions = 1`, monthly risk base, isolated futures.

Artifacts:

- `results/crypt_h1_pivot_only_bounded/20260607_120751/`.

Result:

- Seven-window total return was `-3.04%` across 62 trades.
- SOL Jan/Feb/Mar summed `+2.93%`; no month passed the `+15%` mandate floor.
- TON Jan/Feb/Mar/Apr summed `-5.97%`; mandate verdict was `discard` because
  4/4 months were below the floor.
- Exit mix: 28 take-profits, 32 stop-losses, 2 TTL exits.
- Worst window DD was `-5.74`; worst monthly mandate DD was `-6.69`.

Decision:

- Discard `pivot_only` as a general candidate filter for now. It improved SOL
  March and TON February, but the wider bounded set shows over-pruning and new
  losses in TON March/April.
- Do not run a `pivot_only` `rrr/ttl` grid or SOL 2025 mandate report unless a
  later signal-logic change revives the idea.

Verification:

- Completed `backtester compare-fixed --jobs 3`.
- Inspected `windows.csv`, `monthly_mandate.csv`, and
  `mandate_summary.csv`.

Next: implement minimal donor Optuna support for selected `crypt_ensemble`
strategy parameters, because hand-authored structural filters are not yielding
a robust bounded candidate.

## 2026-06-07 — H1 structural-stop quality filter experiment

Completed the P0 structural-stop quality filter test before broad Optuna.

What changed:

- Documented default-off structural-stop allow-list and stop-distance filters
  in `docs/crypt_ensemble_mtf.md`.
- Added `allowed_sl_anchor_types`, `min_signal_sl_distance_atr`, and
  `max_signal_sl_distance_atr` to `crypt_ensemble` signal filters.
- Added diagnostic strategy configs:
  `crypt_ensemble_h1_filter_pivot_only.json` and
  `crypt_ensemble_h1_filter_anchor_distance_2_4_no_sweep.json`.
- Added focused tests for anchor allow-list and stop-distance filtering.

Artifacts:

- Pivot-only:
  `results/crypt_h1_structural_filter_pivot_only/20260607_114802/`.
- Anchor-distance/no-sweep:
  `results/crypt_h1_structural_filter_anchor_distance_2_4_no_sweep/20260607_115259/`.

Result:

- `pivot_only` improved both problem windows: SOL March `+0.56%` baseline →
  `+2.03%`, max DD `-2.29` → `-1.11`; TON February `+0.07%` baseline →
  `+2.33%`, max DD `-7.47` → `-2.31`.
- `anchor_distance_2_4_no_sweep` improved TON February to `+3.29%`, but hurt
  SOL March to `-2.22%`; treat it as symbol-specific evidence, not a general
  next candidate.

Verification:

- `uv run pytest tests/backtester/test_crypt_ensemble_strategy.py -q`
- `uv run mypy src/backtester/strategies/crypt_ensemble.py`
- `uv run ruff check --select E,F,I --ignore E501 ...`
- `uv run ruff format --check ...`
- Two completed `backtester compare-fixed` bounded reports.

Next: validate `pivot_only` across the standard bounded SOL/TON window set
before any SOL 2025 mandate rerun or broad strategy-param Optuna.

## 2026-06-07 — H1 trigger/setup-quality attribution report

Completed the P0 attribution report before changing H1 signal logic.

What was done:

- Added `setup_snapshot_time` to `crypt_ensemble` signal exports so H1 rows can
  be attributed back to the H4 setup snapshot that produced the verdict.
- Extended `backtester signal-quality` with `setup_attribution.csv` /
  `setup_attribution.md`.
- The new attribution groups tradeable and rejected setup rows by setup
  snapshot time, trigger type, context bias, context/setup alignment, anchor
  type, anchor source timeframe, stop-distance bucket, anchor freshness,
  realized outcome, and signal filter reason.
- Ran the report on SOL March 2025 and TON February 2025 with the fixed
  finite-position baseline (`rrr = 1.25`, `ttl = 36`, `max_positions = 1`).

Artifacts:

- `results/crypt_h1_setup_attribution/20260607_112717/`.

Result:

- SOL March: fixed baseline `+0.56%`, max DD `-2.29`, 18 trades; 385 SELL
  setup rows produced 67 short signals, with 150 context-opposite and 112
  trigger-rejected rows.
- TON February: fixed baseline `+0.07%`, max DD `-7.47`, 20 trades; 425 SELL
  setup rows produced 105 short signals, with 212 trigger-rejected rows.
- The next useful lever is structural-stop quality, not side gating or broad
  strategy-param Optuna: SOL pivot anchors were positive while order-block
  anchors were negative; TON liquidity-sweep anchors were negative while
  order-block and pivot anchors were positive.

Verification:

- `uv run pytest tests/backtester/test_fixed_candidate_report.py tests/backtester/test_crypt_ensemble_strategy.py -q`
- `uv run mypy src/backtester/fixed_candidate_report.py src/backtester/strategies/crypt_ensemble.py`
- `uv run ruff check --select E,F,I --ignore E501 ...` on changed source/test
  files.
- `uv run ruff format --check ...` on changed source/test files.

Next: test a default-off structural-stop quality filter using the attribution
artifact before any broad Optuna or SOL 2025 mandate rerun.

## 2026-06-06 — Broader H1 setup-geometry diagnostics

Completed the next P0 diagnostic pass before broad Optuna.

What was done:

- Ran execution-only `backtester optimize` for SOL March 2025 with
  strategy-param, daily-limit, and trading-window search disabled.
- Ran the same bounded optimizer for TON February 2025.
- Ran a fixed finite-position baseline on the same windows with
  `rrr = 1.25`, `ttl = 36`, `max_positions = 1`.
- Compared best trials, fixed baselines, side counts, trigger counts, stop
  anchors, exit mix, drawdown, and mandate relevance.

Artifacts:

- `results/crypt_donor_h1_mtf_optuna_sol_mar/20260606_180826/`.
- `results/crypt_donor_h1_mtf_optuna_ton_feb/20260606_181333/`.
- `results/crypt_donor_h1_mtf_fixed_sol_mar_ton_feb/20260606_181827/`.

Result:

- SOL March best: `+1.29%`, max DD `-2.01`, `rrr = 1.25`, `ttl = 24`,
  `max_positions = 1`; fixed baseline was `+0.56%`.
- TON February best: `+18.45%`, but max DD `-15.97`, `rrr = 2.0`,
  `ttl = 36`, `max_positions = 5`; fixed baseline was `+0.07%`.
- Both windows are already short-only at the tradeable-signal layer, so side
  gating is not the next useful lever.
- Decision: target H1 trigger/setup-quality attribution before changing signal
  logic or running broad Optuna.

Verification:

- Completed both `backtester optimize` runs.
- Completed `backtester compare-fixed --jobs 2` baseline.
- Inspected `best_trial.json`, `trials.csv`, `windows.csv`,
  `metrics.csv`, `signal_diagnostics.csv`, and `trade_diagnostics.csv`.

Next: add or extend a cheap H1 trigger/setup-quality attribution report and
run it on SOL March and TON February.

## 2026-06-06 — SOL 2025 mandate validation completed

Completed the real SOL 2025 fixed-candidate mandate report for the current H1
short-only row.

What was done:

- Diagnosed the owner-run crash: local SOL OHLCV parquet ended in April 2025
  (`ohlcv_1h` max `2025-04-05 23:00 UTC`), so `sol_2025_05` and later windows
  had empty H1 primary candles.
- Backfilled SOL OHLCV through the project backfill CLI for
  `2025-04-01` to `2026-01-01`, then verified full 2025 H1/H4/D1 monthly
  coverage.
- Reran the exact 12-month `backtester compare-fixed` command with
  `rrr = 1.5`, `ttl = 42`, `risk_percent = 1.0`, `max_positions = 1`, and
  isolated futures.

Artifacts:

- Completed run:
  `results/crypt_ensemble_h1_short_only_sol_2025_mandate/20260606_120001/`.
- The owner-started partial run remains at
  `results/crypt_ensemble_h1_short_only_sol_2025_mandate/20260606_113638/`
  and contains only `sol_2025_01` through `sol_2025_04`.

Result:

- Mandate verdict: **discard**.
- `0/12` months passed the `+15%` monthly return floor.
- `12/12` months were below floor; mandate allows at most `3`.
- Sum capped monthly return was only `+6.82%`; average capped monthly return
  was `+0.57%`.
- Worst monthly drawdown was `-5.41%`; no month breached the `10%` DD limit.

Acceptance:

- `windows.csv`, `monthly_mandate.csv`, `mandate_summary.csv`, and
  `mandate_summary.md` were written in the completed artifact.
- `mandate_summary.csv` records `verdict = discard` with rationale
  `12 months are below the 15% floor; mandate allows at most 3.`

Next: do not rerun this same SOL 2025 row unless signal logic changes. Move to
the P1 stop-loss count limits or another owner-approved signal-quality
experiment.

## 2026-06-06 — Mandate evaluation metrics for fixed candidates

Implemented automated ADR-0025 mandate reporting for donor fixed-candidate
runs.

What changed:

- Added `docs/mandate_reporting.md` as the report contract.
- Added `src/backtester/mandate_report.py` for monthly raw/capped returns,
  excess return, intra-month drawdown, stop-loss counts, losing-month streaks,
  and promote/archive/discard/full-Optuna verdicts.
- `backtester compare-fixed` now exports `monthly_mandate.csv`,
  `mandate_summary.csv`, and `mandate_summary.md` beside `windows.csv`,
  evaluated per symbol so SOL and TON portfolios are not mixed.
- README documents the new artifacts.

Why: ADR-0025 made the economic gates explicit, but agents still lacked an
automated report surface for candidate decisions.

Acceptance:

- Unit tests cover capped-return math, floor gates, drawdown archive logic,
  promote/discard verdicts, and `compare-fixed` mandate CSV export.
- `uv run pytest tests/backtester -q` passed.
- Targeted `uv run mypy src/backtester/mandate_report.py
  src/backtester/fixed_candidate_report.py` passed.
- Changed-file `ruff check --select E,F,I --ignore E501` passed.

Next: run a real SOL 2025 artifact-level validation and inspect
`mandate_summary.csv`, or move to the P1 stop-loss limit dimensions if the
owner does not want to spend a long run on the current weak row.

## 2026-06-06 — Bounded trailing-stop evaluation

Evaluated the newly implemented trailing-stop execution parameters on the
current short-only H1 finite-position row.

What was tested:

- Strategy: `strategies/backtester/crypt_ensemble_h1_filter_short_only.json`.
- Windows: SOL January/February/March 2025 and TON
  January/February/March/April 2025.
- Fixed row: `rrr = 1.5`, `ttl = 42`, `max_positions = 1`,
  `risk_percent = 1.0`, monthly risk base, isolated futures, `25x` max
  leverage.
- Trailing grid: `trail_activation_rrr = 0, 0.5, 0.75, 1.0, 1.25` and
  `trail_distance_atr = 0.5, 1.0, 1.5, 2.0`.

Artifacts:

- Failed first owner-run artifact:
  `results/crypt_ensemble_h1_short_only_trailing_grid/20260606_104945/`
  (`trail_distance_atr` was left at `0` while trailing was enabled).
- Completed rerun:
  `results/crypt_ensemble_h1_short_only_trailing_grid_rerun/20260606_110353/`.

Result:

- Fixed TP baseline remained best: aggregate `+10.12%`, worst window DD
  `-8.72`, 86 trades, exits `33` TP / `37` SL / `16` TTL.
- Best trailing row was `trail_activation_rrr = 1.25`,
  `trail_distance_atr = 0.5`: aggregate `+7.70`, worst window DD `-8.54`,
  96 trades, exits `41` trailing / `40` SL / `15` TTL.
- All other trailing rows were weaker; several turned the bounded profile
  negative or pushed worst drawdown beyond `10%`.
- Decision: trailing stop is **not worth a wider SOL 2025 run** for this
  candidate row; keep fixed TP as the current bounded winner.

Next: return to the P0 mandate-metrics CLI unless the owner chooses a new
signal-quality experiment.

## 2026-06-06 — Optional trailing-stop execution

Implemented bounded-search trailing stop support for donor execution.

What changed:

- Added `trail_activation_rrr` and `trail_distance_atr` to `ExecutionSim`,
  `Backtester.run`, CLI args, optimizer args, fixed-window reports, and
  execution-grid reports.
- `trail_activation_rrr = 0` preserves the existing fixed-TP path.
- After activation, fixed TP is disabled and exits use
  `exit_reason = trailing_stop` with taker-fee semantics.
- Trailing distance uses a strategy-provided `trail_atr` column when present,
  otherwise execution ATR14 computed from closed candles.
- Reports now export `exit_trailing_stop` plus trailing params.

Why: the owner chose to skip mandate-metrics automation for now and asked for
the narrower feature that may improve capture without changing signal logic.

Verification:

- `uv run pytest tests/backtester/test_execution_sim_run.py tests/backtester/test_optimizer.py tests/backtester/test_fixed_candidate_report.py -q`
- changed-file `ruff format --check`
- changed-file `ruff check --select E,F,I --ignore E501`
- `uv run backtester run --help`
- `uv run backtester optimize --help`
- `uv run backtester compare-grid --help`

Next: run bounded trailing-stop comparison for the current short-only H1 row.

## 2026-06-05 — Post-ADR-0026 margin validation grids (owner-run)

Owner reran the bounded H1 short-only row (`rrr=1.5`, `ttl=42`,
`max_positions=1`) across seven windows at `risk_percent = 1.0`, `0.5`, and
`0.25` after ADR-0026.

Artifacts:

- `results/crypt_ensemble_h1_short_only_post_margin_fix/20260605_152526/`
- `results/crypt_ensemble_h1_short_only_post_margin_fix_rp05/20260605_154035/`
- `results/crypt_ensemble_h1_short_only_post_margin_fix_rp025/20260605_154905/`

Result:

- Aggregate return scales linearly: `+10.12%` → `+5.06%` → `+2.51%`.
- Peak locked margin scales monotonically on **every** window (e.g. TON Jan
  `46.38%` → `23.19%` → `11.59%`; SOL Jan `2.89%` → `1.44%` → `0.72%`).
- Max aggregate peak margin: `46.38%` / `23.19%` / `11.59%` — no more `96.62%`
  plateau when lowering `risk_percent`.
- Trade counts unchanged except TON Feb (`19` → `18` at `rp=0.25`, likely
  `min_net_exposure` edge).
- Economics profile unchanged vs pre-fix grids at `rp=1.0`; candidate remains
  **not promotable** under mandate (+15%/month on independent windows).

Acceptance for margin audit: **passed**. Next work: P0 mandate-metrics CLI.

## 2026-06-05 — Isolated-margin leverage selection (ADR-0026)

Audited and fixed finite-position margin sizing in the donor execution path.

What changed:

- Added `src/backtester/margin_policy.py` with shared per-slot margin caps and
  max-leverage locked-margin selection.
- `BasicRiskModel` and `ExecutionSim._can_open_position` now use the same
  `effective_margin_fraction` / `per_entry_margin_cap` semantics.
- `EntryContext` carries `open_positions` so remaining-slot sharing is explicit.
- Replaced minimum-integer-leverage sizing (which maximized locked margin) with
  maximum-allowed-leverage sizing when the position fits the per-entry cap.

Why: the bounded H1 short-only row at `max_positions = 1` kept
`peak_locked_margin_pct_initial = 96.62%` even when `risk_percent` was lowered
to `0.5` and `0.25`, blocking mandate promotion checks.

Result: synthetic tight-stop profile now scales `16% → 8% → 4%` locked margin
for `risk_percent = 1.0 / 0.5 / 0.25` at `25x` leverage. Bounded H1 grids must
be re-run before promotion decisions.

Verification:

- `uv run pytest tests/backtester/test_margin_policy.py tests/backtester/test_risk_fee_models.py tests/backtester/test_execution_sim_run.py -q`
- full `uv run pytest tests/backtester -q`

Artifacts: code only; post-fix grid rerun tracked in `IN_PROGRESS.md`.

## 2026-06-05 — H1 short-only finite `max_positions` grid

Ran the bounded short-only execution grid after exposing `max_positions` as a
search parameter, then validated the best bounded row at lower risk sizing.

What was tested:

- Strategy: `strategies/backtester/crypt_ensemble_h1_filter_short_only.json`.
- Windows: SOL January/February/March 2025 and TON
  January/February/March/April 2025.
- Position-cap grid: `rrr = 1.0, 1.25, 1.5`; `ttl = 30, 36, 42`;
  `max_positions = 1, 2, 3, 5`; `risk_percent = 1.0`.
- Lower-risk repeats for the bounded winner: `risk_percent = 0.5` and
  `risk_percent = 0.25` with `rrr = 1.5`, `ttl = 42`,
  `max_positions = 1`.

Result: the best aggregate row was `rrr = 1.5`, `ttl = 42`,
`max_positions = 1`, totaling `+10.12%` across the seven-window acceptance set
with 86 trades, 4 positive windows, 2 negative windows, and TON April flat with
no trades. Window returns for that row: SOL Jan `+2.56%`, SOL Feb `+5.35%`,
SOL Mar `-2.07%`, TON Jan `+4.71%`, TON Feb `+3.10%`, TON Mar `-3.53%`, TON
Apr `0.00%`.

Lower-risk result: returns and drawdowns scaled down, but peak locked margin
did not become promotable. Aggregate totals for the same seven windows:
`risk_percent = 0.5` returned `+5.06%` with 86 trades, worst window `-1.77%`,
worst drawdown `-4.45`, and peak locked margin still `96.62%` of initial
capital. `risk_percent = 0.25` returned `+2.51%` with 85 trades, worst window
`-0.88%`, worst drawdown `-2.24`, and peak locked margin still `96.62%` of
initial capital.

Interpretation: finite position caps improved the short-only candidate profile,
and `max_positions = 1` is the current bounded winner by return, but it is not
promoted. Lowering `risk_percent` reduces PnL volatility without fixing the
margin realism blocker; the next required work is to audit and constrain the
position-sizing / margin-limit semantics before an owner-run long validation.

Artifacts:

- `results/crypt_ensemble_h1_short_only_max_positions_grid/20260605_125237`
- `grid.csv` / `grid.md` contain 252 completed rows; no error artifact was
  produced.
- `results/crypt_ensemble_h1_short_only_low_risk_grid_rp05/20260605_130507`
- `results/crypt_ensemble_h1_short_only_low_risk_grid_rp025/20260605_131347`

## 2026-06-05 — `max_positions` optimizer and grid search

Exposed finite concurrent-position caps as an execution-search parameter after
the H1 margin-realism audit showed that unconstrained short-only diagnostics
could reach 18 simultaneous positions and about 104% initial capital locked as
margin.

What changed:

- `backtester optimize` now supports explicit finite `max_positions` choices
  with `--max-positions-values`; range flags remain available for contiguous
  bounded sweeps.
- `ParameterOptimizer` passes the selected `max_positions` into `Backtester`
  and records it in trial user attributes.
- Optimizer `best_run/` export now respects the selected `max_positions`
  instead of falling back to the base CLI/config value.
- `backtester compare-grid` now supports `--max-positions-values` so bounded
  reports can compare `rrr` x `ttl` x finite position caps while reusing the
  same precomputed signal frame per window.
- Fixed/grid/signal-quality summaries include `max_positions` next to `rrr`,
  `ttl`, return, drawdown, trade count, and margin diagnostics.

Expected gain: the next H1 candidate check can compare finite caps such as
`1`, `2`, `3`, and `5` without guessing manually, while preserving
`max_positions = 0` only as an unconstrained diagnostic baseline per ADR-0024.

Verification:

- `uv run pytest tests/backtester/test_optimizer.py tests/backtester/test_fixed_candidate_report.py -q`
  -> `11 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check` on changed Python
  files -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check ... --select E,F,I --ignore E501`
  on changed Python files -> clean.
- `UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/matplotlib uv run backtester optimize --help`
  and `compare-grid --help` show the new flags.

## 2026-06-05 — H1 margin-realism audit

Added margin/concurrency diagnostics to donor execution and fixed-candidate
reports, then reran the short-only H1 candidate over SOL January/February/March
2025 and TON January/February/March/April 2025.

What changed:

- `trades.csv` now exports `locked_margin`, `available_balance_before`,
  `open_positions_before`, `total_locked_margin_before`, and
  `total_locked_margin_after_entry`.
- `windows.csv` and `trade_diagnostics.csv` now expose peak open positions,
  peak locked margin, peak locked-margin percentage, and minimum available
  balance before entry.
- The audit run confirmed the old `capital_before` semantics were intentional
  realized-equity fields, not free-margin fields.

Result: short-only remains a useful diagnostic but is not promotable with
unconstrained `max_positions = 0`. Seven-window return remains `+3.96%`, but
peak simultaneous positions reached 18, peak locked margin reached `104.42%`
of initial capital, and several windows left almost no available margin before
new entries.

Artifacts:

- `results/crypt_ensemble_h1_short_only_margin_audit/20260605_122841`
- Per-window `trades.csv`, `trade_diagnostics.csv`, `metrics.csv`, and
  `signals.csv` under `runs/<label>/`.

Verification: targeted simulator/report/analyzer pytest passed (`49 passed`);
changed-file formatter check passed; changed-file `ruff check --select E,F,I
--ignore E501` passed; full root ruff remains blocked by pre-existing donor
style debt tracked in `BACKLOG.md`.

## 2026-06-05 — H1 short-only candidate validation

Validated `strategies/backtester/crypt_ensemble_h1_filter_short_only.json` with
fixed execution parameters `rrr = 1.25`, `position_ttl_bars = 36`, and
`risk_percent = 1.0` across SOL January/February/March 2025 and TON
January/February/March/April 2025.

The seven-window acceptance set totals `+3.96%` across 470 short-only trades:
3 positive windows, 3 negative windows, and 1 flat no-trade window. Window
returns: SOL Jan `-0.90%`, SOL Feb `+13.82%`, SOL Mar `-6.22%`, TON Jan
`+5.15%`, TON Feb `+2.76%`, TON Mar `-10.65%`, TON Apr `0.00%`.
Worst window was TON March with `profit_factor = 0.66`, max drawdown
`-20.52`, and 99 short trades. TON April emitted no tradeable short signals.

Conclusion: short-only remains useful as a signal-quality diagnostic, but is
not promoted. Results are blocked by ADR-0024 until margin usage, concurrent
positions, and finite `max_positions` behavior are auditable.

Artifacts:

- Primary `compare-fixed` report for SOL Jan/Feb/Mar and TON Jan/Feb:
  `results/crypt_ensemble_h1_short_only_candidate/20260605_113757`
- Duplicate primary run, byte-identical `windows.csv`:
  `results/crypt_ensemble_h1_short_only_candidate/20260605_113701`
- TON March supplemental report:
  `/tmp/crypt_missing_ton_debug/20260605_114825`
- TON April supplemental report:
  `results/crypt_ensemble_h1_short_only_candidate_ton_apr/20260605_115125`

Verification: `compare-fixed` completed for all seven acceptance windows.
The two primary duplicate runs had identical `windows.csv`; the duplicate was
operator error during output interpretation, not a separate result.

## 2026-06-04 — Base-vs-filtered H1 signal-quality comparison

- Ran `backtester signal-quality` across the default H1 diagnostic windows:
  SOL January/February/March 2025 and TON January/February/March/April 2025.
- Compared base `crypt_ensemble_h1.json`, full filtered
  `crypt_ensemble_h1_filtered.json`, and two focused ablations:
  `crypt_ensemble_h1_filter_short_only.json` and
  `crypt_ensemble_h1_filter_no_liquidity_sweep.json`.
- What changed in evidence: base total was `-12.72%` across 557 trades; full
  filtered total was `+2.31%` across 418 short-only trades; short-only alone
  was stronger at `+3.96%` across 470 trades; no-liquidity-sweep alone stayed
  negative at `-8.29%` because it kept the harmful 87 long trades.
- Why it matters: the current full filter should not be promoted. Its gain
  mostly comes from deleting longs, while extra anchor filtering reduces useful
  short flow and worsens SOL January versus short-only.
- Expected gain for the next task: validate a narrow short-only candidate
  before spending more time on compound filters.

Artifacts:

- base: `results/crypt_ensemble_h1_signal_quality_base/20260604_141103`
- full filter: `results/crypt_ensemble_h1_signal_quality_filtered/20260604_142009`
- short-only:
  `results/crypt_ensemble_h1_signal_quality_filter_short_only/20260604_143218`
- no-liquidity-sweep:
  `results/crypt_ensemble_h1_signal_quality_filter_no_liquidity_sweep/20260604_144227`

Verification: all four reports completed with `UV_CACHE_DIR=/tmp/uv-cache`;
the no-liquidity-sweep run exported 7 windows and 126 groups.

## 2026-06-04 — H1 signal-quality diagnostics and first filter slice

- Added `backtester signal-quality`, a report-only H1 diagnostic command.
- What it does: builds `crypt_ensemble` signals once per window, runs one
  fixed execution profile for realized PnL attribution, and writes
  `signals.csv` / `signals.md`, `groups.csv` / `groups.md`, optional
  `errors.csv` / `errors.md`, and per-window donor artifacts.
- Why it was needed: candidate A was rejected after SOL full `+4.39%` but TON
  full `-54.65%`, and the monthly execution grid did not reveal a robust
  `rrr`/`ttl` geometry. More execution search was low leverage without knowing
  which signal classes were harmful.
- Expected gain: future agents can compare PnL/trade counts by side, setup
  month, confidence bucket, anchor type, anchor age/freshness, context/setup
  alignment, trigger type, stale-anchor marker, and reversal marker before
  changing strategy logic.
- Added default-off H1 setup/anchor filters to `crypt_ensemble`:
  `allowed_sides`, `blocked_sl_anchor_types`, `max_anchor_age_hours`, and
  `block_context_reversal`.
- Added `strategies/backtester/crypt_ensemble_h1_filtered.json`, a diagnostic
  profile that keeps the current H1 geometry but enables short-only,
  no-liquidity-sweep-anchor, max-72h-anchor-age, and context-reversal filters.
- Updated `AGENTS.md` so future task docs include what/why/gain/acceptance
  links, agents explain task intent at session start, and final replies read
  the next step back to the owner.

Verification: `uv run pytest tests/backtester -q` passed (`114 passed`, 4
existing pandas timezone-to-period warnings); short base and filtered
`signal-quality` SOL smokes completed and exported reports under `/tmp`.

## 2026-06-04 — Root-integrated backtester package

- Added ADR-0023: `backtester` is now a root-integrated package under
  `src/backtester/`, not a nested Python project under `backtester/`.
- Moved donor tests to `tests/backtester/`.
- Moved donor strategy JSON files to `strategies/backtester/`.
- Removed donor-only Hatch/versioningit project files, donor `uv.lock`,
  donor `mise.toml`, donor `.cursor` rules, local caches/venv, generated
  donor results, and unused donor dashboard/scripts/gui files.
- Added root `mise.toml` with common `uv` tasks.
- Added root `backtester` CLI entrypoint in `pyproject.toml` and merged donor
  runtime dependencies into the root dependency set.
- Retired the obsolete root-native `crypt.backtest` harness and removed its
  tests after usage search found no imports outside its own tests and stale
  docs.
- Updated README and migration docs to use root commands such as
  `uv run backtester run ... --strategy strategies/backtester/...`.

Verification: see the 2026-06-04 changelog entry for exact commands.

## 2026-06-04 — Owner-run H1 artifacts reviewed and grid fail-soft fixed

- Unpacked and inspected owner-provided `results.tar`.
- Reviewed full candidate A SOL/TON run:
  - SOL full: `+4.39%`, PF `1.09`, max drawdown `-12.68`, 255 trades.
  - TON full: `-54.65%`, PF `0.71`, max drawdown `-54.49`, 1258 trades.
- Rejected candidate A as a calibration candidate; it remains only a
  diagnostic baseline.
- Reconstructed the aborted extended monthly grid from per-run artifacts:
  360 completed candidates across 10 windows, no robust `rrr`/`ttl` candidate,
  no candidate with at least 7 positive windows.
- Changed `backtester compare-grid` so failed windows no longer discard
  completed summaries. Completed windows write `grid.csv` / `grid.md`; failed
  windows write `grid_errors.csv` / `grid_errors.md`.
- Added a regression test for partial summary export and updated README.

Verification: ruff check and format clean on changed report/test files via
root `uv --group dev`; targeted donor pytest `6 passed` with 4 existing
timezone-to-period warnings.

## 2026-06-03 — Precomputed execution-grid signal reuse

- Inspected SOL March grid diagnostics for the best row (`rrr = 1.0`,
  `ttl = 30`) and candidate A (`rrr = 1.25`, `ttl = 36`).
- Found that executed SOL March trades were all bearish-context,
  H4-setup-SELL, TRENDING-regime shorts; losses cluster around the March 11-14
  reversal and are stop-loss dominated rather than TTL dominated.
- Identified stop-anchor quality as the next useful investigation: order-block
  anchored shorts were negative while pivot-anchored shorts were positive in
  both inspected rows.
- Changed `backtester compare-grid` so each symbol/window builds the fixed
  `crypt_ensemble` signal frame once and reuses it across `rrr` / `ttl`
  execution candidates.
- Kept deterministic grid row ordering and shifted process-level `--jobs`
  parallelism to independent windows after signal reuse.
- Added a focused test proving two execution candidates in one window call
  `strategy.generate()` exactly once.
- Updated README `compare-grid` docs to describe signal reuse.

Verification: ruff check and format clean on changed report/test files;
targeted donor pytest `5 passed`; `compare-grid --help` verified; tiny SOL
smoke exported two candidate runs from one signal build and byte-identical
`signals.csv` files.

## 2026-06-03 — SOL March execution grid completed

- Added `backtester compare-grid`, an execution-only `rrr` / `ttl` grid
  report command for bounded H1 windows.
- The command exports `grid.csv`, `grid.md`, and per-candidate donor artifacts
  under `runs/<label>/rrr_<value>__ttl_<bars>/`.
- Added `--jobs N` for process-level parallel candidate/window execution.
- Backfilled missing local SOL OHLCV data through the project backfill CLI so
  SOL March 2025 is reproducible locally.
- Ran the SOL March grid at
  `/tmp/crypt_execution_grid_sol_mar/20260603_153612`.
- Result: all 9 `rrr = 1.0/1.25/1.5` and `ttl = 30/36/42` candidates were
  negative. Best row was `rrr = 1.0`, `ttl = 30`, `total_return_pct = -6.15`,
  `profit_factor = 0.66`, max drawdown `-11.20`, 64 short-only trades.

Verification: ruff check and format clean on changed CLI/report/test files;
targeted donor pytest `4 passed`; `compare-grid --help` verified; SOL March
grid completed and exported artifacts.

## 2026-06-03 — `compare-fixed --jobs` shipped

- Added `--jobs N` to `backtester compare-fixed`.
- Parallel execution uses independent process workers per window and writes
  per-window artifacts under `runs/<label>/`.
- Main-process report aggregation preserves CLI window order even when workers
  finish out of order.
- Added duplicate window-label validation so parallel workers cannot overwrite
  the same run artifact directory.
- Updated the README fixed-candidate command to show `--jobs 3`.

Verification: ruff check and format clean on changed CLI/report/test files;
targeted donor pytest `3 passed`.

## 2026-06-03 — Optimization acceleration plan documented

- Investigated the current donor optimizer shape: `ParameterOptimizer` uses
  Optuna `JournalStorage` with `n_jobs = 1` and an in-memory signal cache.
- Recorded that raw parallel Optuna is not the first safe speedup because
  multi-process workers would miss the in-memory `crypt_ensemble` signal
  cache and rebuild expensive signal frames.
- Added backlog items for fixed-window/tiny-grid parallelization, disk-backed
  signal caching, guarded optimizer `--jobs`, and explicit precomputed-signal
  execution-only optimization.
- Added an `IN_PROGRESS.md` handoff with the recommended implementation order
  and guardrails.

Verification: documentation-only update; no tests run.

## 2026-06-03 — Fixed H1 candidate A comparison

- Added `backtester compare-fixed`, a bounded fixed-candidate comparison CLI
  that runs one fixed execution profile across default SOL/TON H1 diagnostic
  windows and exports `windows.csv`, `windows.md`, and donor per-window run
  artifacts.
- Ran candidate A (`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`, current H1
  diagnostic strategy config) across SOL January/February/March 2025 and TON
  January/February 2025 at
  `/tmp/crypt_fixed_candidate_h1/20260603_134312`.
- Result: candidate A is positive on 4/5 bounded windows but fails SOL March
  2025. It is worth a long owner-run diagnostic, not accepted calibration.
- Prepared the owner-run full-history SOL/TON `compare-fixed` command in
  `IN_PROGRESS.md`.

Verification: targeted donor pytest `2 passed`; ruff check and format clean on
the new compare/report command files; bounded fixed-candidate CLI completed.

## 2026-06-03 — Urgent profitability sprint handoff

- Captured the owner's remaining-limit constraint: roughly 2-3 Codex sessions
  before limits reset, so the next sessions should prioritize a bounded
  profitable candidate and a long owner-run local backtest command.
- Added a top `IN_PROGRESS.md` handoff with next-session priorities:
  fixed-candidate H1 comparisons, tiny execution-only grid only if needed,
  side-skew attribution, and owner-run long-run preparation.
- Added P0 backlog items for the same sprint and documented why broad
  full-history SOL H1 `--strategy-param-search` Optuna is too expensive during
  Codex time.

Verification: documentation-only update; `git diff --check` passed.

## 2026-06-03 — First adjacent H1 optimizer diagnostics

- Inspected the SOL January optimizer best-run artifacts from
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`. The best trial
  (`rrr = 1.25`, `ttl = 30`) was only mildly positive: `total_return_pct =
  2.46`, `profit_factor = 1.14`, max drawdown `-5.7`, 97 trades; longs
  contributed `+304.88` while shorts contributed `-58.48`.
- Ran the same bounded execution-only optimizer search on adjacent SOL
  February 2025:
  `/tmp/crypt_donor_h1_mtf_optuna_sol_feb/20260603_104255`. Best trial:
  `rrr = 1.25`, `ttl = 36`, `total_return_pct = 13.82`, `profit_factor =
  5.40`, max drawdown `-1.90`, 53 trades, short-only.
- Ran the same bounded execution-only optimizer search on TON January 2025:
  `/tmp/crypt_donor_h1_mtf_optuna_ton_jan/20260603_104642`. Best trial:
  `rrr = 1.50`, `ttl = 36`, `total_return_pct = 1.95`, `profit_factor =
  1.12`, max drawdown `-5.51`, 86 trades, short-only.
- Skipped XPL for this pass because its H1 history is shorter and less useful
  for adjacent-window diagnostics.
- Result: the first adjacent/non-SOL pass is complete, but calibration is not
  accepted. The profile shifts from mixed long/short in SOL January to
  short-only in SOL February and TON January.

Verification: donor ruff check and format clean on changed optimizer/strategy
paths; targeted donor pytest `29 passed`; full donor pytest `102 passed` with
2 existing pandas warnings; SOL February and TON January bounded optimizer
diagnostics completed and exported `best_run/` artifacts.

## 2026-06-03 — Operator-facing H1 optimizer CLI

- Added `backtester optimize`, an operator-facing CLI around the existing donor
  `ParameterOptimizer`.
- The command supports bounded `crypt-parquet` input, preserves strategy JSON
  params, exposes `rrr`, `position_ttl_bars`, fixed/ranged `risk_percent`,
  daily-limit, trading-window, and strategy-param search controls, and exports
  `trials.csv`, `best_trial.json`, the Optuna journal log, and donor
  `best_run/` diagnostics.
- Fixed fixed-risk handling in `ParameterOptimizer` so
  `risk_percent_range = None` uses the configured fixed `risk_percent`.
- Added a cached-signal accessor and made `best_run/` export reuse the cached
  best signal frame for execution-only searches instead of rerunning
  `crypt_ensemble.generate()`.
- Ran a bounded SOL H1 12-trial optimizer diagnostic at
  `/tmp/crypt_donor_h1_mtf_optuna_cli/20260603_102446`: first 745-bar signal
  build took about 3 minutes 59 seconds; cached trials took about 0.05 seconds
  each; best tiny in-sample result was `rrr = 1.25`,
  `position_ttl_bars = 30`, `total_return_pct = 2.46`, `profit_factor = 1.14`,
  max drawdown `-5.7`, 97 trades.
- Ran a short cache smoke at
  `/tmp/crypt_donor_h1_mtf_optuna_cli_cache_smoke/20260603_103348` confirming
  `best_run/` export no longer shows a second `crypt_ensemble` progress build.

Verification: ruff check and format clean on changed CLI/optimizer/test files;
targeted donor pytest `3 passed`; full donor pytest `102 passed` with 2
existing pandas warnings; bounded SOL H1 optimizer CLI diagnostics completed.

## 2026-06-03 — Existing optimizer made usable for H1 setup tuning

- Switched the next H1 setup-geometry step from manual grid thinking to the
  existing donor `ParameterOptimizer`.
- Extended `ParameterOptimizer` additively so it can tune execution parameters
  needed by `crypt_ensemble`: configurable `rrr` range/step,
  `position_ttl_bars` search, preserved `risk_base_period`, baseline
  `strategy_params`, optional disabling of daily/trading-window knobs, and an
  `optimize_strategy_params` switch.
- Added signal-frame caching inside `ParameterOptimizer`, keyed by strategy
  params. Pure `rrr`/`ttl` trials now reuse the generated
  `crypt_ensemble` signal frame instead of rerunning the ensemble every trial.
- Added ADR-0022 and updated `docs/crypt_ensemble_mtf.md`: in H1 MTF mode, H4
  setup verdicts are snapshots at the latest closed H4 setup time and are
  reused across H1 trigger bars until the next H4 close.
- Added tests for H4 setup snapshot reuse/invalidation and optimizer signal
  cache reuse.
- Ran a bounded SOL H1 Optuna speed check at
  `/tmp/crypt_donor_h1_mtf_optuna_speed_check`: first 745-bar signal build
  took about 226.9 seconds; the next two `rrr`/`ttl` trials reused cached
  signals and completed in about 0.05 seconds each. Best tiny diagnostic trial
  was `rrr = 1.75`, `position_ttl_bars = 30`, `total_return_pct = 0.18`.

Verification: ruff check and format clean on changed donor optimizer/strategy
files and tests; targeted donor pytest `28 passed`; full donor pytest
`101 passed` with 3 existing pandas warnings.

## 2026-06-03 — Parity-safe `crypt_ensemble` window cache

- Added a reference-vs-optimized parity contract to
  `docs/crypt_ensemble_mtf.md` before changing strategy code.
- Added `optimized_windows` as an explicit donor `crypt_ensemble` parameter.
  The default remains `false`, preserving the original per-bar reference path
  unless a strategy config opts in.
- Implemented `_ContextWindowCache` for closed candle and timestamp-bounded
  extras window selection only. It preserves `open_time + timeframe <=
  tick_time` for candles and `ts < tick_time` for extras.
- Added reference-vs-optimized parity tests covering context-window equality
  and H1 MTF `generate()` output across signal, stop, trigger, rationale,
  metadata, and per-engine strength columns.
- Enabled `optimized_windows = true` in
  `strategies/backtester/crypt_ensemble_h1.json` for the H1 diagnostic config.
- Reran bounded SOL H1 MTF smoke with optimized windows:
  `/tmp/crypt_donor_h1_mtf_smoke_optimized_windows/20260603_083245`.
- Smoke produced the same key diagnostic result as the prior max-4 run:
  745 H1 signal rows, 98 trades, final capital 9947.0,
  `total_return_pct = -0.53`, `profit_factor = 0.97`, max drawdown `-7.41`,
  exit distribution 37 `ttl_expired`, 35 `stop_loss`, 26 `take_profit`.
  Runtime improved from about 6 minutes 35 seconds to about 5 minutes
  3 seconds on the bounded January SOL slice.

Verification: ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `25 passed`; full donor pytest `98 passed` with
3 existing pandas warnings; bounded SOL H1 optimized-window smoke completed.

---

## 2026-06-02 — H1 setup stop-distance cap diagnostic

- Added `max_sl_distance_atr` as an explicit donor `crypt_ensemble` strategy
  parameter, preserving the existing `8 ATR` default when omitted.
- Added the parameter to the donor Optuna suggestion surface and covered the
  explicit cap with a focused structural-stop unit test.
- Set `max_sl_distance_atr = 4.0` in
  `strategies/backtester/crypt_ensemble_h1.json` for bounded H1 diagnostics.
- Updated the MTF spec and README to document the H1 stop-distance cap as a
  diagnostic setup-geometry knob, not final calibration.
- Reran bounded SOL H1 MTF smoke:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_max4/20260602_195943`.
- Smoke produced 745 H1 signal rows, 105 tradeable signals, 98 trades,
  all executed trades using `sl_source_tf = 1h`, final capital 9947.0,
  `total_return_pct = -0.53`, `profit_factor = 0.97`, and max drawdown
  `-7.41`. TTL exits fell from 50.0% in the previous H1 stop-source smoke to
  37.8%; trade frequency fell from 6.27 to 3.89 trades/day.

Verification: ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `23 passed`; full donor pytest `96 passed` with
3 existing pandas warnings; bounded SOL H1 smoke completed in about 6 minutes
35 seconds.

---

## 2026-06-02 — H1 structural stop-source selection for MTF donor strategy

- Updated `docs/crypt_ensemble_mtf.md` to make the H1-vs-H4 structural stop
  selection contract explicit.
- Added H1 stop-source selection to donor `crypt_ensemble`: H4 remains the
  primary setup stop, while H1 execution mode may replace it with a valid,
  known, same-direction H1 structural stop only when it is closer by
  execution-timeframe ATR distance.
- Preserved H4 default behaviour and existing H4 `_structural_stop_state(ctx)`
  compatibility for tests and callers.
- Added focused tests showing H1 structure replaces a wider H4 stop, and that
  a wider H1 stop does not override H4.
- Reran bounded SOL H1 MTF smoke:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`.
- Smoke produced 745 H1 signal rows, 159 tradeable signals, 158 trades,
  153 tradeable signals with `sl_source_tf = 1h`, final capital 9058.19,
  `total_return_pct = -9.42`, `profit_factor = 0.66`, max drawdown `-10.44`.
  The result is diagnostic only; setup geometry and performance remain open.

Verification: ruff check and format clean on changed donor strategy/test
files; targeted donor pytest `22 passed`; full donor pytest `95 passed` with
3 existing pandas warnings; bounded SOL H1 smoke completed in about 6 minutes
35 seconds.

---

## 2026-06-02 — MTF no-lookahead tests and next-open entry

- Added focused donor `crypt_ensemble` tests for D1 forming-candle exclusion,
  future-known H4 structural stop anchors, and H1 signal timing through
  `ExecutionSim`.
- Fixed `crypt_ensemble` signal rows to leave `entry_price` empty so donor
  execution enters at the next execution-bar open after the closed signal
  candle, instead of using the signal candle close as a current-bar custom
  entry.
- Updated MTF docs and README to describe the donor next-open entry contract.
- Recorded that the previous bounded SOL H1 smoke predates this entry-timing
  fix and must be rerun before comparing H1 metrics.
- Reran bounded SOL H1 MTF smoke after the fix:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`.
- Updated H1 diagnostic result: 745 H1 signal rows, 35 short trades, final
  capital 9357.25 from 10000, `total_return_pct = -6.43`,
  `profit_factor = 0.04`, max drawdown `-6.27`; sample trades confirm
  entry on the next H1 open after the signal timestamp.

Verification: targeted donor pytest `20 passed`; full donor pytest
`93 passed`; ruff check and format clean on changed donor strategy/test files.
All donor pytest runs still show 3 existing pandas warnings in the full suite.
Bounded SOL H1 smoke completed.

---

## 2026-06-02 — Donor `crypt-parquet` smoke range limiter

- Added inclusive `--from` / `--to` CLI bounds for donor
  `crypt-parquet` runs.
- `CryptParquetDataLoader` now parses timezone-naive bounds as UTC and filters
  primary/output rows by their `DatetimeIndex`.
- Preserved pre-start candle history in `StrategyData.candles` up to `--to`
  so bounded smokes still have H4/D1 warmup for engines.
- Added loader and CLI tests for date-range propagation and inclusive
  primary filtering plus context warmup retention.
- Reran bounded SOL H1 MTF smoke after owner restored local Parquet data:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded/20260602_191541`.
- Smoke produced 745 H1 signal rows, 35 short trades, final capital 9340.69
  from 10000, `total_return_pct = -6.59`, `profit_factor = 0.05`, and full
  exports including `trades.csv`, `trade_diagnostics.csv`, `signals.csv`, and
  `signal_diagnostics.csv`.

Verification: ruff clean on changed donor files; targeted donor pytest
`26 passed`; full donor pytest `90 passed`; both with 3 existing pandas
warnings.

---

## 2026-06-02 — `backtester/` vendored into crypt monorepo (docs)

- Owner directed folding `backtester/` into the `crypt` repository (no nested
  `.git`, no submodule).
- Added `docs/decisions/0021-backtester-vendored-in-crypt-monorepo.md` with
  one-time git migration steps and consequences.
- Updated `README.md`, `docs/backtest.md`, `docs/backtester_migration.md`, and
  ADR-0018 cross-references.
- Current working-tree check confirms `backtester/.git` is absent and
  `backtester/` files are tracked from the `crypt` root repository.

---

## 2026-06-02 — First additive MTF `crypt_ensemble` code slice (session 24)

- Added `primary_timeframe` support to donor `crypt-parquet` data loading and
  CLI propagation while preserving H4 as the default primary timeframe.
- Added timeframe-role parsing to `CryptEnsembleStrategy`:
  `context`, `setup`, `trigger`, and `execution`.
- Preserved the existing H4 default mode and added an H1 MTF mode with D1
  context filtering, H4 setup verdict, H1 candle-confirm trigger, H1 execution
  tick index, and MTF diagnostics.
- Added `strategies/backtester/crypt_ensemble_h1.json` for the first H1
  experiment (`ttl = 24`, `rrr = 1.5`, monthly risk base).
- Added focused donor tests for H1 primary loader semantics, CLI propagation,
  H1 execution diagnostics, H4 forming-candle exclusion, and D1
  opposite-context blocking.
- Attempted the full SOL H1 smoke; it loaded 21517 H1 bars and began replay,
  but ended before export and produced no artifact. Full smoke remains open
  behind a run-time limiter or performance pass.

Verification: ruff clean on changed donor files; targeted donor pytest
`41 passed`; full donor pytest `88 passed`, both with 3 existing pandas
warnings.

---

## 2026-06-02 — Unified MTF `crypt_ensemble` handoff spec (session 23)

- Added `docs/crypt_ensemble_mtf.md` for the next implementation pass.
- Captured the owner-requested model: D1 context, H4 setup, H1
  trigger/execution.
- Required the design to be generic enough for future 15m trigger support via
  timeframe-role config rather than a strategy rewrite.
- Documented current gaps: the existing strategy is H4-primary, H1 has no
  distinct trigger layer, and SMC age/TTL/ATR semantics are H4-oriented.
- Documented implementation steps, required diagnostics, no-lookahead rules,
  tests, first H1 smoke command, and future 15m path.

Verification: docs-only; no tests run.

---

## 2026-06-02 — Donor TTL exit diagnostics for structural SOL smoke (session 22)

- Added `trade_diagnostics.csv` export to donor `ResultsAnalyzer` for runs
  with trades.
- The diagnostic report summarizes exit reasons, side/exit counts, side and
  exit-reason PnL, holding duration, trades per day, `sl_distance_atr` by exit
  reason, and stop-anchor distance by anchor type.
- Generated the report for
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827`.
- Diagnosed the TTL-heavy exits: 1496/1672 trades (`89.47%`) closed by
  `ttl_expired`; with `ttl = 6` H4 bars, the holding window is only 24 hours.
- TTL-expired trades had median `sl_distance_atr = 3.985`; with `rrr = 2`,
  their TP is roughly 8 ATR away. The immediate issue is setup geometry
  (wide structural stops plus distant TP inside a short TTL), not a donor
  execution bug.
- Checked local timeframe data availability: SOL and TON have long H1 history;
  XPL has only a short H1 window.

Verification: ruff clean on changed analyzer/test files; targeted donor pytest
`6 passed`.

---

## 2026-06-02 — Structural SMC stop-loss for donor `crypt_ensemble` (session 21)

- Replaced the default mechanical ATR-only donor stop with a structural SMC
  stop hierarchy inside `crypt_ensemble`; donor `ExecutionSim` remains
  unchanged.
- Stop anchors are selected in order: active order block, fresh liquidity
  sweep, confirmed pivot, then optional explicit ATR fallback.
- Default strategy JSON disables ATR fallback, so BUY/SELL verdicts without a
  valid structural stop are neutralized to donor `signal = 0` while keeping
  verdict metadata for audit.
- Added stop diagnostics: `sl_anchor_type`, `sl_anchor_level`,
  `sl_anchor_known_at`, and `sl_distance_atr`.
- Added synthetic tests for long/short order-block stops, sweep fallback,
  pivot fallback, excessive-distance neutralization, no-anchor
  neutralization, and no-lookahead `known_at <= tick_time`.
- Reviewed structural SOL smoke at
  `/tmp/crypt_donor_structural_sl_smoke/20260602_143827`: 1672 trades,
  final capital 6683.68, `total_return_pct = -33.16`, `profit_factor = 0.84`,
  max drawdown `-35.38`.
- Compared against the prior no-structural run
  `/tmp/crypt_donor_smoke/20260602_132627`: structural SL removed 120 trades
  but did not improve aggregate return or profit factor; long-side trades
  remain materially negative.

Verification: ruff clean on changed donor strategy/test files; targeted donor
pytest `14 passed`; full donor pytest `82 passed` with 3 existing pandas
warnings.

---

## 2026-06-02 — ADR-0020 and donor confidence gate rollback (session 19)

- ADR-0020 added: the live alert threshold `75` is an arbitrary placeholder,
  not a calibrated confidence threshold and not the default donor entry gate.
- ADR-0011 status updated so only its `75` rationale is superseded; the
  `[UNCALIBRATED]` marker policy remains accepted.
- `strategies/backtester/crypt_ensemble.json` no longer sets
  `min_confidence = 75`; donor `crypt_ensemble` trades BUY/SELL verdicts by
  default.
- `min_confidence` remains available as an explicit optional diagnostic/Optuna
  parameter.
- `signal_diagnostics.csv` now reports confidence quantiles instead of a
  hard-coded `confidence_ge_75` metric.
- Reviewed owner-provided SOL smoke at
  `/tmp/crypt_donor_smoke/20260602_132627`: 1792 trades, final capital 6694.69
  from 10000, `total_return_pct = -33.05`, `profit_factor = 0.88`, max
  drawdown `-36.96`; longs remain the main drag while shorts are slightly
  profitable.

Verification: ruff clean on changed donor files; targeted donor pytest
`12 passed`; full donor pytest `75 passed` with 3 existing pandas warnings.

---

## 2026-06-02 — Threshold-correct donor SOL smoke diagnostics (session 18)

- Added no-trade export diagnostics to the donor analyzer: `signals.csv`,
  `signal_diagnostics.csv`, and non-empty `metrics.csv` are now written even
  when execution opens zero trades.
- Reran SOL donor smoke with `min_confidence = 75` at
  `/tmp/crypt_donor_smoke/20260602_122510`.
- Confirmed the no-trade result is expected under the live threshold:
  5545 signal rows, 772 BUY verdicts, 1026 SELL verdicts, 3747 HOLD verdicts,
  max confidence 52, and 0 rows with `confidence >= 75`.
- Recorded that the full straightforward replay took about 15 minutes, so
  Optuna should wait for confidence-scale review and replay profiling/parity
  work.

Verification: ruff clean on changed donor files; full donor pytest
`74 passed` with 3 existing pandas warnings.

---

## 2026-06-02 — Donor `crypt_ensemble` confidence threshold (session 17)

- Reviewed monthly-risk SOL donor smoke at
  `/tmp/crypt_donor_smoke/20260602_104522`: 1792 trades, final capital 6694.69
  from 10000 initial capital, `total_return_pct = -33.05`,
  `profit_factor = 0.88`, max drawdown `-36.96`.
- Confirmed the trade export now carries `signal_time`, `risk_base_capital`,
  confidence, score, regime, decision, rationale, and `strength_<engine>`
  columns.
- Diagnosed the smoke as trading internal low-confidence verdicts: all trades
  had `confidence <= 55`, below the live alert threshold of 75.
- Added `min_confidence` to donor `crypt_ensemble` params and Optuna
  suggestions; default strategy JSON value is `75`.
- Low-confidence BUY/SELL verdicts now keep their metadata but emit donor
  `signal = 0`.

Verification: ruff clean on changed strategy/test files; targeted donor
pytest `6 passed` with one existing pandas warning.

---

## 2026-06-02 — Donor trade metadata and monthly risk-base sizing (session 16)

- Reviewed owner-completed SOL donor smoke at
  `/tmp/crypt_donor_smoke/20260602_101119`: 1792 trades, final capital
  6548.74 from 10000 initial capital, `total_return_pct = -34.51`,
  `profit_factor = 0.88`; long trades were the main drag while short trades
  were slightly positive.
- Confirmed the run was a plain `backtester run`, not an optimizer run.
- Fixed donor execution export so trade rows preserve `crypt_ensemble`
  attribution metadata: `signal_time`, confidence, score, regime, decision,
  rationale, and `strength_<engine>` columns.
- Added `risk_base_period` to donor execution sizing with `trade`, `weekly`,
  `monthly`, and `backtest` modes. The old per-trade current-capital behaviour
  remains available as `trade`.
- Set `strategies/backtester/crypt_ensemble.json` to monthly risk-base sizing
  for M2 donor smokes, per ADR-0019.
- Exported `risk_base_capital` on each trade row for audit.

Verification: ruff clean on changed donor files; targeted donor pytest
`39 passed`; full donor pytest `71 passed` with existing pandas warnings.

## 2026-06-02 — Donor `crypt_ensemble` engine wiring (session 15)

- `src/backtester/strategies/crypt_ensemble.py` — wired the donor
  strategy to run the existing `crypt` volatility/regime/directional engines
  and aggregator over `StrategyData`.
- Donor output now includes `signal`, `entry_price`, ATR-based `sl_price`,
  `confidence`, `score`, `regime`, `decision`, `rationale`, and
  `strength_<engine>` columns.
- Closed-candle replay semantics are preserved by evaluating each H4 row at
  `open_time + 4h` and filtering H4/H1/D1 contexts to candles closed at or
  before that tick.
- Added visible per-bar progress for long `crypt_ensemble` runs and enabled it
  in `strategies/backtester/crypt_ensemble.json`.
- Fixed the project-Parquet `open_time` ambiguity where the timestamp was both
  index name and column label.
- Tests added/updated for signal mapping, ATR stop output, missing optional
  frames, and `open_time`-named indexes.

Verification: donor `pytest` → 67 passed; ruff clean on changed donor files.
SOL `crypt-parquet` smoke loaded 5545 H4 bars and started replay with progress,
but the full run was stopped before completion due duration.

---

## 2026-06-02 — Donor backtester Parquet loader and neutral strategy slice (session 14)

- `src/backtester/data_contracts.py` — added `StrategyData` for
  richer strategy input while keeping the old DataFrame strategy path.
- `src/backtester/data_loader.py`, `cli_runner.py`,
  `__main__.py` — added `parquet` and `crypt-parquet` CLI data sources.
- `src/backtester/strategies/crypt_ensemble.py` and
  `strategies/backtester/crypt_ensemble.json` — registered a neutral
  `crypt_ensemble` skeleton.
- Tests added for single-file Parquet loading, project-style Parquet columns,
  `crypt-parquet` loader plumbing, CLI source selection, and the neutral
  strategy skeleton.
- Smoke: SOL `parquet` and `crypt-parquet` commands loaded 5545 H4 bars and
  wrote no-trades reports.

Verification: donor `pytest` → 65 passed; ruff clean on changed donor files.

---

## 2026-06-02 — Donor backtester migration decision (docs only — session 13)

- `docs/decisions/0018-donor-backtester-canonical-m2.md` — accepted ADR:
  future M2 work moves toward the donor `backtester/` package as the canonical
  strategy/backtester architecture.
- `docs/backtester_migration.md` — handoff spec for additive donor changes:
  `StrategyData`, `parquet`, `crypt-parquet`, `crypt_ensemble`, one-symbol
  smoke run, and later Optuna.
- `docs/tasks/IN_PROGRESS.md` — next-agent implementation sequence recorded.
- `docs/tasks/BACKLOG.md` — P0/P1 migration tasks added.

Verification: docs-only; no tests run.

---

## 2026-06-01 — M2 OHLCV backtest report review (session 12)

- `reports/backtest_2026-06/` reviewed after the owner reran the SOL/TON
  OHLCV-only backtest.
- ADR-0014 written: generated weights are rejected; keep `config/weights.yaml`
  unpromoted and keep live alerts marked uncalibrated.
- `src/crypt/backtest/optimizer.py` — `weights_to_yaml()` now writes safe YAML
  primitives when optimizer weights contain numpy scalar values.
- `reports/backtest_2026-06/weights.candidate.yaml` — rewritten with the safe
  serializer; weights unchanged.
- Tests added: `tests/backtest/test_optimizer.py` verifies candidate weights
  with numpy scalars can be loaded with `yaml.safe_load`.

Verification: `pytest -q` passed; `ruff check src tests` clean; `mypy src`
clean.

---

## 2026-06-01 — Multi-symbol execution simulator fix (session 11)

- `src/crypt/backtest/execution_sim.py` — next-open entries, TTL exits, and
  `holding_bars` now use per-symbol bar order instead of the next global row
  in a combined multi-symbol DataFrame.
- `src/crypt/backtest/__main__.py` — simulation input now carries
  `entry_price = close` from the closed signal candle.
- `src/crypt/backtest/metrics.py`, `src/crypt/backtest/report.py`,
  `src/crypt/backtest/__main__.py` — removed pandas `pct_change` and UTC
  datetime deprecation warnings seen in the owner backtest log.
- Tests added: `tests/backtest/test_execution_sim.py` reproduces same-timestamp
  SOL/TON rows and asserts SOL uses SOL's next open, not TON's price.

Verification: `124 passed`; `ruff check src tests` clean; `mypy src` clean.

---

## 2026-06-01 — Optimizer score recomputation fix (session 10)

- `docs/backtest.md` — replay verdict contract now requires
  `strength_<engine>` columns for all scoring engines.
- `src/crypt/backtest/recorder.py` — `BacktestRecorder` persists per-engine
  strengths from `Verdict.breakdown` alongside the final verdict score.
- `src/crypt/backtest/optimizer.py` — `_apply_weights` recomputes candidate
  scores from replayed strengths, renormalising across active engines before
  deriving decision/objective.
- Tests added: `tests/backtest/test_optimizer.py` proves candidate weight
  changes alter replayed score, decision, and objective.

Verification: `119 passed`; `ruff check src tests` clean; `mypy src` clean.

---

## 2026-06-01 — SMC liquidity engine (session 9)

- `src/crypt/structure/smc.py` — added equal high/low liquidity levels,
  swing liquidity levels, liquidity sweeps, ATR-scaled tolerance, wick-distance
  metadata, and same-candle ambiguity flags with explicit `known_at` timing.
- `src/crypt/engines/smc_liquidity.py` — added reversal engine for equal/swing
  high/low sweeps with neutral handling for missing H4 data and ambiguous
  same-candle double sweeps.
- `src/crypt/runtime/orchestrator.py`, `src/crypt/backtest/__main__.py` —
  wired `smc_liquidity` into live and replay evaluation.
- `src/crypt/aggregator/weights.py`, `src/crypt/backtest/optimizer.py`,
  `config/weights.yaml` — added `smc_liquidity` to M2 scoring and placeholder
  calibration weights.
- Tests added: `tests/engines/test_smc_liquidity.py`; SMC core tests now cover
  equal-level confirmation, sweep timing, and ambiguous double sweeps.

Verification: `116 passed`; `ruff check src tests` clean; `mypy src` clean.

---

## 2026-06-01 — SMC order-block engine (session 8)

- `src/crypt/structure/smc.py` — added `SMCOrderBlock`, order-block creation
  from BOS/CHoCH pivot-to-break windows, high-volatility candle parsing, and
  mitigation state.
- `src/crypt/engines/smc_order_blocks.py` — added active order-block retest
  engine with bias confluence, zone rejection bonus, ATR width filter, and
  neutral degradation on missing H4 data.
- `src/crypt/runtime/orchestrator.py`, `src/crypt/backtest/__main__.py` —
  wired the engine into live and replay evaluation.
- `src/crypt/aggregator/weights.py`, `config/weights.yaml`,
  `src/crypt/backtest/optimizer.py` — added `smc_order_blocks` to primary M2
  scoring and placeholder calibration search.
- Tests added: `tests/engines/test_smc_order_blocks.py`; SMC core tests now
  cover order-block creation and mitigation.

Verification: `109 passed`; `ruff check src tests` clean; `mypy src` clean.

---

## 2026-06-01 — ADR-0017 + first OHLCV-only SMC structure slice (session 7)

- `docs/decisions/0017-ohlcv-only-m2-smc.md` — M2 primary calibration moved
  to free OKX OHLCV data; derivatives weight set to 0 until proven.
- `docs/engines/smc_core.md`, `smc_structure.md`, `smc_order_blocks.md`,
  `smc_liquidity.md` — SMC contracts written before code.
- `src/crypt/structure/smc.py` — first SMC analyser slice: confirmed pivots
  and BOS/CHoCH with explicit `known_at` timing.
- `src/crypt/engines/smc_structure.py` — candle-only directional engine.
- `src/crypt/runtime/orchestrator.py`, `src/crypt/backtest/__main__.py` —
  `smc_structure` wired into live and replay signals.
- `config/weights.yaml`, `src/crypt/aggregator/weights.py` — scoring set and
  placeholder weights updated for ADR-0017.
- Tests added: `tests/structure/test_smc.py`,
  `tests/engines/test_smc_structure.py`.

Verification: `103 passed`; `ruff check src tests` clean; `mypy src` clean.

---

## 2026-06-01 — ADR-0016 code implementation: drop funding, fix OI endpoint (session 6)

All code changes from ADR-0016 implemented and verified (97 tests, mypy 0, ruff clean).

- `src/crypt/exchange/okx.py` — OI endpoint fixed to `publicGetRubikStatContractsOpenInterestHistory`.
- `src/crypt/engines/derivatives.py` — funding removed; OI 0.67 / LS 0.33.
- `src/crypt/models.py`, `data/context.py`, `data/store.py`, `data/ingestor.py` — funding paths removed.
- `src/crypt/backfill/__main__.py` — `funding` data-type removed.
- `src/crypt/backtest/replay.py`, `backtest/__main__.py` — funding references removed.
- Tests updated: `test_derivatives.py`, `test_no_lookahead.py`, `test_filters.py`, `conftest.py`.
- `.env.example` — Coinglass env vars replaced with tombstone comment.

---

## 2026-06-01 — ADR-0016: drop funding, fix OI endpoint, retire Coinglass (docs only — session 5)

- `docs/decisions/0016-drop-funding-fix-oi-endpoint.md` — new ADR (accepted).
- `docs/decisions/0015-coinglass-historical-backfill.md` — status updated to
  superseded.
- `docs/engines/derivatives.md` — spec rewritten: funding removed, weights
  rebalanced to OI 0.67 / LS 0.33.
- `docs/backfill.md` — Coinglass section removed; OI/LS from OKX native.
- `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md`, `CHANGELOG.md` — updated.

---

## 2026-05-29 — Coinglass backfill: spec + ADR (docs only)

- `docs/backfill.md` — backfill contract: OKX + Coinglass sources, CLI
  `--source`, endpoint mapping, tier limits, M2 operator workflow.
- `docs/decisions/0015-coinglass-historical-backfill.md` — accepted ADR.
- Cross-refs in `docs/backtest.md` §14/§16, `docs/decisions/0012`,
  `.env.example`, `README.md`, task tracking files.
- Implementation (`CoinglassClient`, CLI) deferred — see `IN_PROGRESS.md`.

---

## 2026-05-29 — M2 backtest harness: full pipeline — steps 4–11 (labels, metrics, walk-forward, optimizer, report, CLI)

- `src/crypt/backtest/labels.py` — forward-label loader (§6): return_h4/h24/h96, MAE, MFE, hit_* columns.
- `src/crypt/backtest/metrics.py` — port of ResultsAnalyzer with §18.4 fixes (equity-curve
  duplicate-exit fix, Sharpe warning < 6 months, trade-level Sharpe); bootstrap CI; hit-rate
  metrics; buy-and-hold / random-direction baselines.
- `src/crypt/backtest/walkforward.py` — expanding-window walk-forward CV; `FoldSpec`, `generate_folds`,
  `slice_verdicts`, `slice_trades`; hard no-overlap guarantee tested.
- `src/crypt/backtest/optimizer.py` — grid search + coordinate descent weight optimiser (§9);
  objective = `mean(pnl) - 0.5*std(pnl)`; sanity guards; `aggregate_weights_across_folds` (§13 median rule).
- `src/crypt/backtest/report.py` — static HTML report generator with embedded matplotlib charts (§12).
- `src/crypt/backtest/__main__.py` — full CLI entry point: precondition checks (§4), replay loop (§5),
  forward labels, ExecutionSim wiring, walk-forward, optimization, baseline comparison, HTML report.
- `tests/backtest/test_labels.py` — 8 tests for label computation, hit rates, drop-tail behaviour.
- `tests/backtest/test_walkforward.py` — 8 tests incl. regression: no test-slice timestamp in train.
- `tests/backtest/test_metrics.py` — 12 tests: basic metrics, equity-curve §18.4 fix, Sharpe warning,
  bootstrap CI, buy-and-hold, generate_metrics integration.
- `matplotlib>=3.8` added to runtime dependencies.

Stats: 97 tests (was 67); mypy 0 errors (12 backtest files); ruff clean.

---

## 2026-05-29 — M2 backtest harness: backfill CLI + replay infrastructure (steps 1–3)

- `src/crypt/backfill/__init__.py`, `__main__.py` — paginated backfill CLI for OKX
  OHLCV/funding/OI/LS-ratio/taker-vol; resume-safe; tqdm progress; `--from`, `--to`,
  `--data-types`, `--page-size`, `--max-rps`.
- `src/crypt/exchange/okx.py` — pagination methods added: `fetch_ohlcv_page`,
  `fetch_funding_history_page`, `fetch_oi_history_page`, `fetch_ls_ratio_range`,
  `fetch_taker_volume_range`. `fetch_ohlcv` gains optional `since_ms` param.
- `src/crypt/backtest/replay.py` — `ReplayParquetStore` (time-fence look-ahead guard)
  and `ReplayContextBuilder` (drop-in for `ContextBuilder` in replay loop).
- `tests/backtest/test_no_lookahead.py` — 8 tests: guard filters future data,
  naïve builder leaks it (proof the test would catch a real regression).
- `src/crypt/backtest/fee_model.py` — port of `StaticPercentFeeModel` with
  maker/taker asymmetry.
- `src/crypt/backtest/risk_model.py` — port of `BasicRiskModel` (ATR-distance sizer).
- `src/crypt/backtest/execution_sim.py` — port of `ExecutionSim` with all §18.4 fixes:
  `FundingRateModel` + `ZeroFundingModel` + `ParquetFundingModel` (🔴);
  multi-symbol capital pool via `symbol` column (🔴); SL gap-adjusted fill (🟡);
  `exit_time` off-by-one fixed (🟡).
- `src/crypt/backtest/recorder.py` — `BacktestRecorder` (verdict sink → Parquet).
- `src/crypt/backtest/__init__.py` — module exports.
- `pyproject.toml` — `tqdm>=4.66` added; `tqdm.*` added to mypy overrides.

Stats: 67 tests pass (was 59); mypy 0 errors (43 files); ruff clean.

---

## 2026-05-29 — Post-M1 P0 quality gates + post-mortem + ADR-0013

- `docs/post_mortems/2026-05-29-m1-run-summary.md` — M1 14-day run summary
  (255 verdicts, 0 crashes, 0 alerts, key observations).
- `.github/workflows/ci.yml` — GitHub Actions CI (ruff, mypy, pytest, uv lock,
  gitleaks).
- `.pre-commit-config.yaml` — pre-commit hooks (ruff + mypy).
- `[UNCALIBRATED]` Telegram marker — `Settings.uncalibrated`, `TelegramSink`,
  8 unit tests.
- Closed-candle invariant — time-based `closed` in OKXClient, ingestor filter,
  `save_candles` assertion, 4 unit tests.
- Critical-inputs guard refactor — `Signal.critical_missing`,
  `BaseEngine.critical_inputs`, per-engine declarations, filter updated, 5 new
  tests.
- ADR-0013 (`crypt` stdlib name conflict) — `pythonpath = ["src"]` in
  `pyproject.toml`; `uv run pytest` now works without `PYTHONPATH=src`.

---

## 2026-05-14 — Session 6: Railway deployment config

Railway deployment for the M1 14-day continuous run.

- Researched Railpack (Railway's build system), Railway Volumes, log retention, billing,
  GitHub auto-deploy, and file extraction methods.
- Created `docs/decisions/0010-railway-deployment.md` (ADR; status: accepted).
- Created `railway.toml` — Railpack builder, `uv sync --all-extras --no-dev` build command,
  `uv run --no-dev python -m crypt` start command (avoids default `dev` group on `uv run`),
  `ON_FAILURE` restart policy.
- Created `.python-version` — pins Python 3.12 for Railpack.
- Added `log_dir: Path` field to `Settings` (`config.py`); updated `__main__.py` to accept
  it in `_configure_logging`. On Railway: `LOG_DIR=data/logs` puts log files on the
  persistent volume alongside parquet files. Stderr Loguru uses `isatty()` so colorize and
  `enqueue` apply only in a real terminal (immediate logs on Railway).
- Updated `.env.example` with `LOG_DIR` documentation.
- Created `docs/deploy/railway.md` — step-by-step owner checklist (8 steps, including
  volume setup, env vars, monitoring, and exact file-extraction commands).

---

## 2026-05-14 — Session 5: reliability hardening

All P0/P1/P2 reliability BACKLOG items completed.

- `src/crypt/utils/retry.py` — `retry_with_backoff` helper (full-jitter exponential backoff).
- `src/crypt/exchange/okx.py` — retry applied to all 5 fetch methods; `timeout: 30s`.
- `src/crypt/data/ingestor.py` — exceptions from `asyncio.gather` logged at ERROR.
- `src/crypt/runtime/orchestrator.py` — gather exceptions logged; tick summary line;
  `_evaluate_symbol` returns status; sink exceptions logged.
- `src/crypt/runtime/health.py` — disk-space guard (`< 1 GB` → WARNING).
- `src/crypt/__main__.py` — daily log rotation + gz; heartbeat task (30 min liveness
  + 6 h OKX health check); clean shutdown of heartbeat task.
- `src/crypt/sinks/telegram.py` — jitter in backoff retry.
- `src/crypt/config.py` — `OKX_MAX_RETRIES`, `OKX_RETRY_BASE_DELAY`, `OKX_RETRY_MAX_DELAY`.
- `.env.example` — retry/backoff params documented.
- `deploy/crypt.service` — systemd unit with `Restart=always`, `RestartSec=10`.
- `README.md` — "Running as a service" section.

mypy 0 errors / 36 files. ruff clean. 42/42 tests pass.

---

## 2026-05-14 — Session 3: M1 validation (smoke test + mypy + health check)

### What was done

- **mypy clean pass** — fixed 12 type errors across 8 files:
  - Added `pandas.*` and `pyarrow.*` to `[[tool.mypy.overrides]]` in `pyproject.toml`.
  - `store.py`: typed lambda list as `list[Callable[[], Path]]`; added `type: ignore[no-untyped-call]` for pyarrow bundled-stub gap.
  - `engines/derivatives.py`: explicit `Direction` annotation on `direction` variable; typed `_ls_signal` arg to `list[LongShortRatioSnapshot]`; added `Direction` import.
  - `engines/trend.py`, `engines/meanrev.py`: explicit `Direction` annotation on direction variables.
  - `engines/meanrev.py`: `std=2.0` (float) + `type: ignore[arg-type]` for pandas-ta bundled-stub gap.
  - `engines/volatility.py`: `npt.NDArray[Any]` for `_rank_pct` signature.
  - `config.py`: `return list(v)` to avoid `Returning Any`.
- **OKX rubik stat API fix** — `/rubik/stat/contracts/long-short-account-ratio` and `/rubik/stat/taker-volume` require `ccy` (base currency), not `instId`. Fixed both methods in `okx.py`.
- **Scheduler stop guard** — `H4Scheduler.stop()` now checks `self._scheduler.running` before calling `shutdown()` to avoid `SchedulerNotRunningError` when `--once` is used.
- **Logging**: `logs/` directory is created at startup before the loguru file sink is added.
- **Health-check helper** (`src/crypt/runtime/health.py`) — on startup checks OKX API reachability, verifies each configured symbol exists in OKX market list (by raw `instId`), and optionally pings the Telegram bot.
- **Symbol verification** — all three configured symbols confirmed live on OKX: `SOL-USDT-SWAP` ✓, `TON-USDT-SWAP` ✓, `XPL-USDT-SWAP` ✓.
- **Smoke test** — `uv run python -m crypt --once` completes cleanly (exit 0, no unclosed connectors). Verdicts produced for all 3 symbols.

ADRs introduced: none.

---

## 2026-05-14 — M1 code layer

Implemented the full M1 pipeline. All 42 synthetic-data unit tests pass;
`ruff` reports no errors.

### What was built

- **`pyproject.toml`** — `requires-python` updated to `>=3.12` (pandas-ta
  constraint); `uv sync` run; `uv.lock` generated.
- **`src/crypt/config.py`** — `pydantic-settings` `Settings` class + YAML
  weights loader.
- **`src/crypt/models.py`** — all typed contracts: `Timeframe`, `Regime`,
  `Candle`, `FundingSnapshot`, `OISnapshot`, `LongShortRatioSnapshot`,
  `TakerVolumeSnapshot`, `Signal`, `Verdict`, `EvaluationContext`.
- **`src/crypt/exchange/`** — `ExchangeClient` Protocol + `OKXClient` backed
  by `ccxt.async_support.okx`. Covers OHLCV, funding history, OI history,
  L/S ratio, taker volume (including OKX-specific `rubik/stat` endpoints).
- **`src/crypt/data/`** — `ParquetStore` (Parquet read/write, upsert, trim),
  `Ingestor` (parallel async pulls for all symbols), `ContextBuilder`
  (assembles `EvaluationContext` from store).
- **`src/crypt/engines/`** — `BaseEngine` ABC + five engines:
  `TrendEngine`, `MeanRevEngine`, `DerivativesEngine`, `VolatilityEngine`,
  `RegimeEngine`. Bug fixed: `_rank_pct` returns 0 on zero-variance series.
- **`src/crypt/aggregator/`** — `WeightsConfig` (YAML loader with hard-coded
  fallback) + `ensemble.aggregate()` (regime-conditional weighted sum → Verdict).
- **`src/crypt/decision/filters.py`** — `DecisionFilter` (confidence
  threshold, cooldown, inputs-missing guard).
- **`src/crypt/sinks/`** — `BaseSink`, `TelegramSink` (aiogram, retry),
  `JsonLogSink` (JSONL append), `ConsoleSink`, `ExecutionStub`.
- **`src/crypt/runtime/`** — `H4Scheduler` (APScheduler 4h-aligned cron) +
  `Orchestrator` (wires all components, drives tick loop).
- **`src/crypt/__main__.py`** — CLI entry point with `--once`, `--symbols`,
  `--no-bootstrap` flags; graceful `SIGTERM`/`SIGINT` shutdown.
- **`config/weights.yaml`** — placeholder regime-conditional weights.
- **`tests/`** — 42 synthetic-data unit tests covering all engines,
  aggregator, and decision filter.

ADRs introduced: none (all decisions covered by ADRs 0001–0008).

---

## 2026-05-13 — M0 scaffold

- Decided language (Python), exchange (OKX-only), horizon (4h), storage
  (Parquet), data layer (REST), aggregator (regime-conditional weighted
  sum), scope (no order flow, no liquidations in MVP).
- ADRs 0001–0008 written.
- Architecture document `docs/architecture.md` written.
- Engine specs scaffolded under `docs/engines/`.
- Task tracking initialised: `ROADMAP.md`, `BACKLOG.md`, `IN_PROGRESS.md`,
  this file.
- Cursor rules created under `.cursor/rules/`.
- Root files created: `README.md`, `AGENTS.md`, `CHANGELOG.md`,
  `.gitignore`, `.env.example`.
- Verified via Context7 that OKX exposes everything needed for MVP through
  public REST (OHLCV, funding, OI, long/short ratio, taker volume).
  Liquidations are WS-only and deferred (ADR-0006).
