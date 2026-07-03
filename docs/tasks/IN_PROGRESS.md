# In progress

## Core4 v3 OKX aggregate-average rerun (2026-07-03)

**What:** rerun the canonical minute last/mark backtest after ADR-0058 corrected
same-side OKX position accounting. Logical entries still own their SL, TP,
native trailing, and TTL, but realized PnL, locked margin, and liquidation now
use the exchange side's aggregate average entry. Partial closes preserve that
average.

**Why now:** the 2026-07-02 `$25,100.59` artifact used constituent entry prices
for realized PnL and rebuilt the remaining average after partial closes. OKX
does neither. In the artifact, 1,918 of 3,422 entries added to an existing side
and 1,916 closes occurred with multiple same-side constituents, so the defect
is material.

**Expected gain:** obtain the first cash path that combines minute last/mark
execution with actual OKX same-side average-price semantics. This determines
whether the strategy remains near `$25k`, improves materially, or fails for a
different reason.

**Acceptance:**

1. `trades.csv` exports both logical `entry_price` and
   `aggregate_entry_price`.
2. Cash reconciles from `$10,000` through closed PnL and open entry fees.
3. Signal, signal-diagnostic, and H1 OHLCV hashes match artifact
   `20260702_102019`.
4. Report final account dollars, both drawdowns, 2025 mandate months,
   liquidation count, and exit distribution.

**Owner-run command:**

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --data-source crypt-parquet \
  --data-dir data \
  --primary-timeframe 1h \
  --symbol SOL-USDT-SWAP \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_causal_v3_core4.json \
  --capital 10000 \
  --output results/core4_v3_okx_aggregate_average_20260703
```

Expected artifact:
`results/core4_v3_okx_aggregate_average_20260703/<timestamp>/` with
`metrics.csv`, `trades.csv`, `equity_curve.csv`, `signals.csv`,
`signal_diagnostics.csv`, `trade_diagnostics.csv`, `ohlcv.csv`, and
`trade_chart.html`.

**Links:** ADR-0058, `docs/execution/liquidation_safe_leverage.md`,
`docs/execution/minute_intrabar_execution.md`.

---

## Core4 v3 live takeover and exact trade verification (2026-06-29)

**What:** start the liquidation-safe/native-trailing v3 executor and verify the
first new native-trailing trade. The legacy Island position was closed through
the production client on 2026-06-29 and its fill/state/sync path is complete.

**Why now:** the first live trade proved that 25x liquidation (`71.2843`) was
above its structural stop (`70.9484`). The audit also found missing live
trailing, candle gaps, order retry duplication risk, incomplete protection
identity, and OKX same-side aggregation differences.

**Expected gain:** future entries cannot silently liquidate before their stop;
every entry/exit/error reaches Telegram; v3 live orders and the canonical
backtester share leverage, aggregate liquidation, fixed entry-time native
trailing geometry, fees, fill identity, TTL precedence, and minute-resolved
historical execution.

**Acceptance:**

1. Superseded: precision/fee artifact
   `results/core4_v3_precision_fee_parity_20260701/20260701_091336/` predates
   conservative intrabar execution and is no longer canonical.
2. Startup repairs any future H1/H4 gaps and then reports continuity clean.
3. The next service restart logs WebSocket preparation at `HH:59:30`, an OKX
   confirmed boundary near `HH:00`, and `source=websocket`; `*:02` logs a
   skipped REST fallback for the already-completed boundary.
4. Completed: owner reran through `2026-06-29 14:00 UTC`; all seven exported
   CSV artifacts are byte-identical to canonical `20260629_160832`.
5. The next v3 trailing entry has a persisted `move_order_stop`, safe aggregate
   OKX liquidation, and clean sync.
6. Replay that completed entry with `matched=true`.

**Completed live-close evidence:** position `1166b4b0` closed reduce-only via
order `3699121635279626240` at `73.43`, fees and PnL reconciled exactly, and the
post-close snapshot contained zero positions/orders with clean sync.

**2026-07-02 v2 result:** owner artifact
`results/core4_v3_recovery_conservative_intrabar_v2_20260702/20260702_052419/`
is cash-consistent at `$32,956.20`, `+229.56%`, `-10.33%` drawdown, four
`unsafe_liquidation_buffer` exits, and zero liquidations. It validates the
conservative H1 model but is superseded as the final acceptance artifact by
the owner's decision to add minute execution.

**Minute data completed:** owner backfilled SOL last-trade and mark-price
history for `2021-12-18` through `2026-06-30`. Both series contain 2,383,200
continuous rows. All H1 high/low/close aggregates match. Eight OKX H1 opens
differ from the first 1m open by at most `$0.06`; both opens remain inside the
same exact hourly range, so H1 remains the modeled entry and 1m starts the
subsequent path.

**Canonical minute result:** owner artifact
`results/core4_v3_minute_last_mark_20260702/20260702_102019/` is execution-
reconciled at `$25,100.59`, `+151.01%`, `-9.20%` below-start drawdown,
`-42.54%` peak-to-trough drawdown, 3,422 entries, eight mark-price
liquidations, two liquidation-buffer fail-safe exits, and exact cash
reconciliation. Signals and H1 OHLCV remain byte-identical to H1 v2.

**Risk verdict:** the strategy fails the owner mandate. The 2025 slice is
`discard`: five monthly drawdown breaches, worst monthly below-start drawdown
`-19.68%`, and only five of twelve months pass the 15% floor. Across the full
artifact the worst monthly below-start drawdown is `-49.53%`.

**Next action:** owner decision is required: either knowingly continue a
supervised small-balance live experiment despite the failed mandate and
`-42.54%` historical peak loss, or keep live stopped and return to strategy
risk reduction. Historical 1m data remains backtest/replay-only; live uses
continuous native OKX protection and real-time mark-price liquidation.

**Links:** ADR-0049, ADR-0050, ADR-0051,
ADR-0052, ADR-0053, ADR-0055, ADR-0056,
`docs/execution/live_backtest_parity_audit_2026-06-30.md`,
`docs/execution/liquidation_safe_leverage.md`,
`docs/execution/native_okx_trailing.md`,
`docs/execution/live_trade_replay.md`,
`docs/execution/h1_websocket_trigger.md`,
`docs/execution/live_signal_cache.md`.

---

## Core4 live execution dry-run validation (2026-06-27)

**What:** run the updated Core v4 live executor in `EXECUTION_DRY_RUN=true`
against the real OKX account and inspect 1-2 real H1 ticks before any live
money switch.

**Why now:** the code migration is complete locally, but only the real OKX
account can prove credentials, balance/position/order snapshot shape, pending
algo order visibility, and live logs.

**Expected gain:** catch exchange/API/account-shape problems while no orders are
being placed.

**Acceptance:**
1. Start with `EXECUTION_ENABLED=true EXECUTION_DRY_RUN=true`.
2. Logs show clean full exchange sync: balance, no orphan positions/orders, and
   no `last_exchange_sync_errors`.
3. Exchange sync confirms OKX is in long/short position mode; one-way/net mode
   is a blocker before live money.
4. Telegram receives one daily full-sync report when configured, reports every
   execution-cycle failure, and repeats an active sync blocker every H1 cycle.
5. On an H1 tick, the executor either skips because no Core v4 event exists or
   sends `ENTRY ATTEMPT` followed by `ENTRY`, `ENTRY REJECTED`, or `EXECUTION
   ERROR`; successful dry-run details include sane entry, SL, TP, contracts,
   donor id, and risk base.
6. Only after owner review may `EXECUTION_DRY_RUN=false` be considered.

**Command:**
```bash
PYTHONPATH=src \
MPLCONFIGDIR=/tmp/matplotlib \
EXECUTION_ENABLED=true \
EXECUTION_DRY_RUN=true \
EXECUTION_DRY_RUN_CAPITAL=10000 \
EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85.json \
EXECUTION_SYMBOLS=SOL-USDT-SWAP \
uv run python -m crypt --once --execution-only
```

Use `--execution-only` for this check. The legacy H4 alert monitor is not part
of Core4 trading validation and should not print `HOLD/conf/regime` verdicts
during the dry-run.

**Links:** `docs/execution/live_execution.md`, ADR-0048,
`src/crypt/execution/`.

---

## Superseded Core4 v4 drawdown branch — not active (2026-06-26)

**Status:** superseded by the owner's 2026-06-29 decision that causal v3 is the
active portfolio. The figures below are historical and invalid after the
liquidation/native-trailing execution changes.

**What:** previously continued from
`strategies/archive/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85.json`,
the current best post-fix core4 balance.

**Why now:** after fixing multi-signal trailing parity, core4 became the
strongest money source. Raw v3 made +$656,185 on $10k but had -22.42%
recalculated drawdown. The selected v4 removes Island longs and scales nested
risk to 85%, making +$206,978 on $10k with -14.91% drawdown and 12.69
trades/week.

**Expected gain:** push drawdown toward 10-12% while preserving a materially
larger money result than standalone Island/SMAC.

**Acceptance:** exact `backtester run` artifact with recalculated drawdown from
`equity_curve.csv`, not the console DD line; report final dollars, trades/week,
worst month, negative month count, and per-strategy PnL.

**Next steps:**

1. Re-run the selected v4 with `--capital-sweep monthly_profit` to measure
   banked dollars, remaining trading capital, and total account value without
   assuming all profits stay reinvested.
2. Stress v4 by fixed windows: 2024-2025 validation and 2025-latest stress,
   then inspect whether the -14.91% drawdown is concentrated in one period.
3. Try smaller targeted reductions only on the drawdown-causing components
   instead of globally reducing risk again.
4. Do not use pre-2026-06-26 multi-signal artifacts for conclusions; rerun
   them after the trailing parity fix.

**Links:** `results/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85_full/20260626_182156/`,
`results/core4_fine_frontier_after_fix/`,
`results/core4_combo_variants_after_fix/`,
`results/core4_risk_scale_after_fix/`.

**Update (2026-06-27):** monthly-profit sweep exact tests were run on the
current v4 baseline and several distribution variants for SOL 2022-12-18 →
2026-06-10 with $10k initial capital. The baseline remains the strongest
money result among checked variants: total account $43,271, +$33,271 PnL,
-14.57% drawdown, 36 positive months and 7 negative months. The best drawdown
reduction branch was DSS half-risk: total account $38,459 and -11.64%
drawdown, but it gave up roughly $4,812 vs baseline. DSS risk x0.65 was a
middle branch: total account $41,013 and -13.19% drawdown. Daily loss 3R kept
money close to baseline ($42,663) but did not improve drawdown (-14.57%).
DSS bar-range cap improved profit factor to 1.42 and DD to -14.06%, but cut
total account to $41,483. Adding low-risk NR7 was rejected: total account
$43,007 but drawdown worsened to -18.75% and negative months increased.
`max_positions` is not an allowed research/control lever per owner direction;
discard the diagnostic max-position artifacts and do not use them for
conclusions.

**Current conclusion:** no checked variant dominates v4 on all owner criteria.
If prioritizing money, keep v4 or daily-loss-3 as the nearest branches. If
prioritizing smoother drawdown, DSS risk x0.65 is the least painful reduction,
while DSS half-risk is the cleanest DD cut but sacrifices too much profit.

**Sparse donor scan (2026-06-27):** owner suggested adding many rare high-WR
strategies to v4. Local scan was redirected away from exact `trades.csv` and
toward strategy-search artifacts. The relevant Stage 1 gate fix landed on
2026-06-19: the hidden `tp_first > sl_first` requirement was removed, leaving
the configured WR threshold as the actual Stage 1 WR gate. Local post-fix
search artifacts are thin: only
`results/dss_sol_v2_barrier_wr55_10pd_2023first_seed60619/` and
`...seed60620/` were found. They exported no balanced candidates, but they
contain useful 2023 specialists rejected for too few 2022 signals. Top traces:

- `dssv2_017163`: `pt_compression_breakout` with
  `pf_bar_range_min+pf_side_long_only`, 21 signals in 2023, 71.43% barrier WR,
  only 3 signals in 2022.
- `dssv2_061351`: `pt_nr4_breakout` with
  `pf_bb_width+pf_body_to_range_min+pf_volume_ratio`, 24 signals in 2023,
  62.50% barrier WR, only 4 signals in 2022.
- `dssv2_023651`: `pt_nr4_breakout` with `pf_rsi_zone+pf_side_short_only`,
  21 signals in 2023, 61.90% barrier WR, only 4 signals in 2022.

Older pre-fix v3 discovery artifacts under `results/20260608_193549/` contain
promising sparse seeds, but they must be rerun under the post-2026-06-19 DSS
gate before use. Best-looking seed families include:
`h1_vwap_reclaim` off-hours quiet-volume low-BB-width (30 events, 72.41% label
WR across 11 monthly windows), `h1_hammer` low-BB-width close-near-high (39
events, 74.36% label WR), `h1_tweezer_top` Asia short-side trend-strength
(78 events, 74.03% label WR), and `h1_bb_rejection` low-BB-width EMA50-side
(48 events, 72.92% label WR). These are not exact candidates yet.

Owner smoke-ran
`search-signals-matrix --windows bad_2023_09,bad_2024_05,bad_2025_01,bad_2026_04 --catalog all --stage-mode stage1 --min-trades 3 --min-signals-per-week 0 --stage1-min-wr 0.62 --n-trials 100`
into `results/sparse_donor_stage1_bad_months_matrix_v1/`. Runtime was about
3 minutes for 5 algorithms x 100 trials. All five algorithms finished cleanly,
but exported zero Stage 1 candidates and zero specialists. The strongest
near-misses mostly passed only one bad-month slice with too few or weak signals
elsewhere, so the 4-window smoke is too strict for the intended "basket of rare
specialists" idea. Next sparse donor searches should be single bad-month
specialist runs first, then merge the best specialists into a candidate basket.

Owner then redirected away from bad-month-specific search and back to the
ADR-0046 anti-overfit chronology. Active owner-run search:
`results/sparse_donor_stage1_train_2022_2023_v2/`, command uses
`--windows train_2022_2023:2022-01-01:2024-01-01 --catalog all --stage-mode stage1 --min-trades 15 --min-signals-per-week 0 --stage1-min-wr 0.62 --n-trials 2000`.
Early partial read while the run was still active showed roughly 380-397
candidates processed per algorithm and one `staged` Stage 1 survivor:
`dssv2_000099`, `pt_vwap_reclaim` with
`pf_bar_range_min+pf_ps_smc_equal_level_recent`, 17 train signals and 64.7%
Stage 1 barrier WR. Wait for `summary.md` / `stage1_ranked.csv` before making
any portfolio conclusion.

Final read: the 10,000-candidate matrix exported only two Stage 1 candidates:
`staged_seed73023/stage1_candidates/stage1_001_dssv2_000099_pt_vwap_reclaim.json`
(17 train signals, 64.7% Stage 1 barrier WR, mixed side with 29% longs) and
`smac_qd_seed5151/stage1_candidates/stage1_001_smac_000961_pt_ps_smc_premium_discount_reversal.json`
(16 train signals, 62.5% Stage 1 barrier WR, short-only). CatCMA-QD,
Hyperband-QD, and Island-QD exported no Stage 1 candidates. Rejection shape:
roughly 1,095-1,254 candidates per algorithm had too few signals, 718-871 had
weak barrier WR, and 25-33 were overtrading. This confirms the rare-donor path
can find usable sparse candidates, but the current gates are too strict to
produce a large basket from 2,000 trials/algorithm. Next step is exact
validation of the two exports on 2024 and 2025-latest, then either relax to
`--stage1-min-wr 0.60` or lower `--min-trades` to 10 for a broader basket.

Owner reported the two strict Stage 1 exports were exact-validation failures.
Before launching another search, the weak-barrier near-miss layer was mined.
Generated 15 replayable candidate JSONs under
`results/sparse_donor_stage1_train_2022_2023_v2/weak_barrier_shortlist/`
plus `shortlist.csv` and `README.md`. These candidates have 17-45 train
signals, Stage 1 barrier WR from 48.9% to 61.1%, and several use high RRR
settings where exact execution can still make money despite missing the 62%
barrier-WR gate. Next step: exact-run this shortlist on 2024 validation before
starting another Stage 1 matrix.

---

## Island short-only branch: next risk reduction pass (2026-06-26)

**What:** continue improving the Island short-only branch after the first exact
weekend wide-stop filter. Current best money variant:
`strategies/archive/island_short_r1p42_rrr0p75_ttl32_weekend_stop_filter_v1.json`.

**Why now:** the six-donor portfolio failed, while Island has a real standalone
short-side edge. The filtered Island branch improved $10k → $82,602
(+$72,602), kept 3.40 trades/week, and beat the original Island's +$50,599
with lower recalculated drawdown (-16.35% vs -23.91%). It still does not meet
the strict mandate because drawdown remains above 10% and 2025 monthly floor
coverage is weak.

**Expected gain:** reduce drawdown without dropping below the owner's frequency
floor of 2-3 trades/week. The immediate target is a variant that stays near
or above +$1,500/month average while moving drawdown below ~15%; the harder
mandate target remains below 10%.

**Acceptance:** exact backtester artifacts for the chosen variant, a comparison
against the current baseline in dollars, trades/week, negative months, worst
month, and recalculated equity drawdown.

**Next steps:**

1. Search only entry-known Island filters, not CSV deletion: weekend filter
   threshold sweep, session/hour filters, stop-distance bands, volatility bands,
   and short-only crisis/off-switch candidates.
2. Recalculate drawdown from `equity_curve.csv`; do not trust the printed
   `Max Drawdown` line alone because recent runs showed a misleading -1.6%
   print while equity-curve drawdown was -16.35%.
3. If no single rule gets drawdown under ~15% while preserving at least
   2-3 trades/week, test symbol portability before investing more effort in
   Island-only polishing.

**Links:** `results/island_short_weekend_stop_filter_v1_full/20260626_172556/`,
`results/island_short_weekend_stop_filter_risk_grid/`,
`docs/archive/candidates/island_2023_021396_engulfing_bb_trend/README.md`.

---

## Per-strategy donor filter research needs owner-run donor backtests (2026-06-26)

**What:** run full-period exact backtests for each donor strategy in the
router/composite portfolio, then search entry-known `take`/`skip` filters
per donor strategy using `backtester trade-filter-research`.

**Why now:** grouped filtering on a routed artifact is not enough. In
`router_v2_3997501`, the 2022-2024 train split had 718 trades for
`crypt_ensemble_h1_discovery_nr4_vwap_robust` but zero train trades for three
other selected strategies. A routed output only shows what the old router chose;
it cannot train personal filters for strategies the router did not use in the
train window.

**Expected gain:** find strategy-specific bad-trade filters before changing the
router. If a donor's own 2024 validation and 2025+ stress both improve, the
filter can later be embedded into that strategy and the combined portfolio can
be exact-tested through the normal backtester.

**Acceptance:** each donor has a full-period exact `trades.csv`, then a
filter-research report with train 2022-2024, validation 2024-2025, and stress
2025-latest. Any candidate must improve validation and stress returns, not
worsen stress floor-month count, and not worsen stress monthly drawdown before
it is considered for exact implementation.

**Status (2026-06-26):** the code supports single rules, two-rule conjunctions,
`--group-by selected_strategy`, and optional closed-candle catalog features via
`--include-catalog-features --ohlcv <path>`. Smoke tests on
`router_v2_3997501` produced zero robust passes; this is expected because the
routed artifact lacks train data for most donors.

**Update (2026-06-26):** owner completed parallel full-period donor backtests
under `results/donor_exact_2022_2026/`. Causal donor-level filter research was
run under `results/trade_filter_research_donors_2022_2026_causal/` after fixing
catalog feature joins to use strictly previous candles on exact `open_time`.
All six donors have at least one robust-forward CSV filter:

- `crypt_ensemble_h1_discovery_nr4_vwap_robust`: +$60 validation, +$3,722
  stress on $10k.
- `crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4`: +$1,473 validation, +$3,936
  stress on $10k.
- `crypt_ensemble_h1_discovery_vwap_reclaim_robust`: +$9,378 validation,
  +$1,470 stress on $10k.
- `dssv2_013321_ps_macd_squeeze_recent`: +$4,463 validation, +$17,298 stress
  on $10k.
- `island_2023_021396_engulfing_bb_trend`: +$282 validation, +$5,508 stress on
  $10k.
- `smac_003335_double_bottom_body_to_range`: +$2,174 validation, +$2,832 stress
  on $10k.

These are CSV-deletion research numbers, not final portfolio results.
Standalone donor trades overlap materially: 1,320 of 6,210 trades occur on
timestamps where 2-3 strategies want to enter. The current strategy/backtester
contract has one signal row per bar, so exact "release all passing strategies"
requires a multi-signal execution path instead of selecting one row or
duplicating OHLCV bars.

**Status (multi-signal implementation):** `ExecutionSim` now accepts optional
`signal_events` lists per OHLCV bar. The old scalar `signal` / `sl_price`
contract remains valid. `Backtester` passes `signal_events` strategies through
without requiring scalar signal columns. The new
`filtered_donor_portfolio_causal_v1` strategy builds all six donor signal
streams, applies the causal donor filters, and emits every accepted signal into
one shared-capital execution path.

**Correction (2026-06-26):** owner exact-tested `causal_v1` and got +$9,377 on
$10k (+93.78%) with -7.57% drawdown, but that run is invalid as a portfolio
verdict. The fast portfolio path did not expose `confidence` and
`strength_smc_structure`, so two donor filters silently rejected all NR4 and
NR7 events. The code now fails early when a filter references unavailable
features. A new `filtered_donor_portfolio_causal_v2_deployable` config uses
only fast-path deployable fields known at entry time: `entry_hour`,
`entry_dayofweek`, and previous-closed-candle `catalog_*` features. A diagnostic
signal-only pass produced 3,787 events across all six donors:

- NR4 VWAP: 828 events.
- NR7 BB squeeze: 669 events.
- VWAP reclaim: 305 events.
- DSS MACD squeeze: 384 events.
- Island engulfing: 1,060 events.
- SMAC double bottom: 541 events.

**Exact result (2026-06-26):** owner exact-tested
`filtered_donor_portfolio_causal_v2_deployable` under
`results/filtered_donor_portfolio_causal_v2_deployable_full/20260626_163108`.
The result is not investable: $10,000 became $6,557 (-$3,442 / -34.43%) with a
-76.05% maximum drawdown. Longs lost -$8,288 while shorts made +$4,846. By
strategy, VWAP reclaim lost -$5,913 and NR7 lost -$5,714; DSS made +$5,237 and
NR4 made +$3,008.

**Negative-oracle update (2026-06-26):** `backtester negative-oracle-research`
was added and run on the bad v2 artifact:
`results/negative_oracle_filtered_donor_portfolio_causal_v2/`. It tested 1,066
entry-known skip rules. The best robust simple/pair rule saved only +$315 in
validation and +$1,487 in stress, so there is no obvious simple "mine" rule
that rescues this portfolio.

**Next decision:** stop trying to rescue the six-donor SOL-only portfolio with
simple filters. The next useful branch is either symbol expansion or a
portfolio-level crisis/off-switch research pass.

**Filter command template after donor backtests exist:**

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester trade-filter-research \
  --trades results/donor_exact_2022_2026/<strategy_id>/<timestamp> \
  --ohlcv results/donor_exact_2022_2026/<strategy_id>/<timestamp>/ohlcv.csv \
  --include-catalog-features \
  --output results/trade_filter_research_donors_2022_2026/<strategy_id> \
  --capital 10000 \
  --min-train-trades 20 \
  --top-n 50
```

**Links:** `docs/trade_filter_research.md`, ADR-0046,
`results/router_exact_shortlist_2022_2026/`.

---

## Active DSS search matrix — inspect all five (2026-06-12)

**Context for next agent:** the owner is intentionally running five different
DSS search algorithms before the next agent session. The next session should
start only after all artifacts have been gathered on one PC. Do not implement a
sixth algorithm before inspecting these five result sets.

**Important version note (2026-06-12 late):** DSS Stage 1 now includes a cheap
path-aware barrier label (`tp_first` vs `sl_first` vs `timeout`) and writes
`barrier_*` columns in `stage1_viability.csv`. Searches already running before
that change are still useful as pre-barrier diagnostics, but do not compare
their Stage 1 survivor rates directly with fresh runs started after this code.
The first barrier implementation used trigger reference price; the fixed
version uses the same next-open entry and resolved `sl_rrr` levels as Stage 2.
Restart any barrier run that began before this note if Stage 1/Stage 2
alignment matters for analysis.

**Superseded version note (2026-06-18):** fresh DSS Stage 1 runs no longer use
candidate `rrr`, `risk_percent`, `atr_sl_mult`, structural stops, TTL, or
`sl_rrr` levels. The active Stage 1 label is next-open entry, closed-candle
ATR14 as symbol volatility scale, SOL reference calibration of 0.7% favorable
TP and 0.4% adverse SL, same-bar TP+SL counted as SL, and unresolved
end-of-window tails excluded from `barrier_win_rate`. Compare results only
against artifacts produced after this note when evaluating the current Stage 1
policy.

| Machine | Algorithm | Output | Status / next check |
| --- | --- | --- | --- |
| Work PC | default `staged` DSS v2 | `results/dss_sol_v2` | Owner started 120k trials. When owner returns, inspect `summary.md`, `archive.md`, `stage2_proxy.csv`, `stage3_full_scores.csv`, `candidate_manifest.md`, and `candidates/*.json`. |
| Home PC | `catcma_qd` | `results/dss_sol_catcma_seed777_fast` | Run was observed at 23,698 generated / 2,464 Stage 2 rows with no Stage 3 and no proxy score above `-5000`; likely negative unless it later resumes and improves. Inspect before deciding. |
| Railway | `island_qd` | `data/results/dss_sol_island_qd_railway_seed2026` | `railway.toml` start command now launches this search. Inspect via `railway ssh`; key file is `island_scores.csv` plus any exported `candidates/*.json`. |
| Extra local/remote | `hyperband_qd` | `results/dss_sol_hyperband_seed4242` | Owner started or can start this fourth algorithm. Inspect `hyperband_rungs.csv`, `stage2_proxy.csv`, `stage3_full_scores.csv`, archive, manifest, and candidates. |
| Extra local/remote | `smac_qd` | `results/dss_sol_smac_seed5151` | Owner should start this fifth algorithm after pulling this session. Inspect `smac_qd_proposals.csv`, `smac_qd_observations.csv`, `smac_qd_state.csv`, normal DSS stage CSVs, archive, manifest, and candidates. |

**What the next agent should do first when results are available:**
1. For each output directory, count rows in `stage0_candidates.jsonl`,
   `stage1_viability.csv`, `stage2_proxy.csv`, and `stage3_full_scores.csv`.
2. Also inspect algorithm-specific artifacts:
   `island_scores.csv`, `hyperband_rungs.csv`, `smac_qd_observations.csv`, and
   `smac_qd_state.csv` when present.
3. Report best `robust_score`, best `score_min`, and whether any candidate JSONs
   exported across all five runs.
4. Note whether `stage1_viability.csv` has `barrier_*` columns; missing columns
   mean the artifact came from the pre-barrier Stage 1 policy.
5. If any `candidates/*.json` exist, prepare owner-run `compare-fixed` commands
   for SOL 2025 continuous validation. Do not run owner-scale validations unless
   explicitly asked.

**SMAC-QD command for the fifth run:**
```bash
uv run backtester search-signals \
  --algorithm smac_qd \
  --seed 5151 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_smac_seed5151
```

**Hyperband-QD command for the fourth run if it is not already running:**
```bash
uv run backtester search-signals \
  --algorithm hyperband_qd \
  --seed 4242 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_hyperband_seed4242
```

---

## Island-QD Railway search — next owner action (2026-06-12)

**What remains:** owner can run a separate Railway service/job with the new
`island_qd` DSS backend. This should run independently from the local
CatCMA-QD run and the work-machine default DSS v2 run.

**Why now:** local CatCMA-QD reached about 23.7k generated candidates without a
single proxy candidate above `-5000` robust/min score. The best candidates were
often only useful on one window, especially `2025H1`, while `2022` killed the
robust score. Island-QD directly tests whether per-window specialist families
exist before trying to find robust intersections.

**Expected gain:** produce `island_scores.csv` showing best candidate families
per window and possibly export replayable candidate JSONs that default robust
search would reject too early.

**Railway start command for a dedicated search service:**
```bash
PYTHONPATH=/app/src uv run --no-dev backtester search-signals \
  --algorithm island_qd \
  --seed 2026 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output data/results/dss_sol_island_qd_railway_seed2026
```

**Config-as-code:** `railway.toml` currently uses this search command as
`deploy.startCommand`. Revert it to `PYTHONPATH=/app/src uv run --no-dev python
-u -m crypt` before using the same Railway service for live alerts again.

**Expected artifacts:** `data/results/dss_sol_island_qd_railway_seed2026/summary.md`,
`island_scores.csv`, `archive.md`, `archive.json`,
`island_qd_state_<window>.csv`, `stage1_viability.csv`, `stage2_proxy.csv`,
`stage3_full_scores.csv` if robust checks run, `candidate_manifest.md`, and
`candidates/*.json` if archive elites export.

**Railway note:** `railway run` executes locally with Railway env vars. To run
on Railway compute, set the service Start Command or deploy a dedicated service.
The output path intentionally starts with `data/` so artifacts land on the
Railway volume mounted at `/app/data`. To inspect files in the container
volume, use `railway ssh`.

---

## CatCMA-QD SOL search — next owner action (2026-06-11)

**What remains:** owner can run the experimental CatCMA-inspired DSS backend at
home while the work machine continues the default staged DSS v2 run.

**Why now:** running another default staged search with the same code/seed would
mostly duplicate the work-machine candidate sequence. ADR-0037 adds a different
mixed-variable learning pressure over triggers, filters, and execution params.
The first local CatCMA-QD attempt reached 592/120000 with ETA ~6d because Stage
2 proxy scoring was too permissive; it was stopped and the backend now caps
Stage 2 to the top cheap-scored slice per batch.

**Expected gain:** increase search diversity and give the project a second,
non-identical archive to compare against the work-machine DSS v2 artifact.

**Command:**
```bash
uv run backtester search-signals \
  --algorithm catcma_qd \
  --seed 777 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --output results/dss_sol_catcma_seed777_fast
```

**Expected artifacts:** `results/dss_sol_catcma_seed777_fast/summary.md`,
`archive.json`, `archive.md`, `catcma_qd_state.csv`, `stage1_viability.csv`,
`stage2_proxy.csv`, `stage3_full_scores.csv`, `score_history.csv`,
`candidate_manifest.md`, and `candidates/*.json` if any archive elite exports.

**Do not resume:** `results/dss_sol_catcma_seed777/` was produced with the old
uncapped Stage 2 policy and is diagnostic only.

---

## DSS v2 first SOL search — next owner action (2026-06-11)

**Status:** already started on the work machine with 120k trials per owner chat.
Leave it running and inspect the artifact when the owner returns.

**What remains:** owner needs to return with `summary.md` / `archive.md` from
the work-machine run. Agents should not run this owner-scale search unless
explicitly asked.

**Why now:** DSS v1 collapsed into `pt_ema_cross + rrr=4.0 + wide ATR stop`.
DSS v2 now stages cheap viability/proxy checks before full mandate scoring and
keeps a quality-diversity archive, so the next useful evidence is a real SOL
archive artifact.

**Expected gain:** determine whether the v2 search can produce diverse exported
candidate JSONs worth 2025 `compare-fixed` validation.

**Command:**
```bash
uv run backtester search-signals \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 120000 \
  --n-jobs 4 \
  --output results/dss_sol_v2
```

**Expected artifacts:** `results/dss_sol_v2/summary.md`, `archive.json`,
`archive.md`, `stage1_viability.csv`, `stage2_proxy.csv`,
`stage3_full_scores.csv`, `score_history.csv`, `candidate_manifest.md`, and
`candidates/*.json` if any archive elite exports.

---

## Walk-forward validation — next steps (2026-06-10)

**What remains:** owner needs to run the walk-forward command on real data.

**Command (full optimization, 6 windows, SOL):**
```bash
uv run backtester walk-forward \
  --data-dir data --symbol SOL-USDT-SWAP \
  --from 2022-01-01 --to 2025-12-31 \
  --is-months 12 --oos-months 6 \
  --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \
  --trials 50 \
  --ttl-low 24 --ttl-high 60 \
  --risk-percent-low 1.0 --risk-percent-high 3.0 \
  --output results/walk_forward_nr4_sol
```

**Quick eval (no optimization, just per-year audit):**
```bash
uv run backtester walk-forward \
  --data-dir data --symbol SOL-USDT-SWAP \
  --from 2022-01-01 --to 2025-12-31 \
  --is-months 12 --oos-months 12 \
  --strategy strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json \
  --trials 0 \
  --output results/walk_forward_nr4_sol_eval
```

**Expected artifact:** `results/walk_forward_nr4_sol/<timestamp>/summary.md` — table of IS vs OOS returns per window + interpretation verdict.

**Why this matters:** answers whether NR4 has genuine edge or is overfit to 2024-2025.

---

## Active candidate: NR4 vwap band (2026-06-09)

**Strategy:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`  
**Plan:** `docs/candidates/nr4_vwap_robust.md`

### Mandate truth (ADR-0032 continuous, canonical)

**Active params:** tp=0.016, rrr=2.5, ttl=36, risk=1.5% (mandate-score Optuna best)

| Metric | Value |
| ------ | ----- |
| Verdict | **archive** |
| Sum capped | **+185.06%** |
| Months ≥ 15% | **9 / 12** |
| Below floor | **3** (Jan 11.83%, Feb 0.69%, Mar −1.28%) |
| DD breach | **1** (Mar −17.11%) |
| Full-year return | +284.65% (continuous run) |

Artifact: `results/nr4_mandate_score_best_compare/20260609_150212/`

Optuna continuous proxy and compare-fixed **match** (9/12, +185.06%, archive).
ADR-0032 alignment confirmed.

**Why archive, not promote:** Mar intra-month DD −17.11% > 10% limit → archive
per mandate §3.1 (no deep dive required). Also 3 months below 15% floor (within
allowed 3, but DD gate dominates).

### Historical (pre-ADR-0032 isolated mode — do not use for decisions)

| Params | Verdict | Sum capped | Months ≥15% |
| ------ | ------- | ---------- | ----------- |
| Legacy risk=2%, ttl=48 isolated | discard | +164.75% | 8/12 |
| Mandate-score isolated | discard | +131.31% | 3/12 |

### Next steps

1. **Owner-run legacy continuous** (tp=0.016, rrr=2.5, ttl=48, risk=2%) — compare
   vs current best under ADR-0032; command in `docs/candidates/nr4_vwap_robust.md`.
2. **Mar attribution** — `.../150212/runs/sol_continuous/trade_chart.html` + Mar
   SL cluster (DD breach month).
3. Filter/signal tweak or archive NR4 as near-miss if Mar DD cannot be fixed.

**Archived (2026-06-09):** NR7 and VWAP reclaim → `docs/archive/candidates/`.
