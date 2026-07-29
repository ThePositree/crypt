# In progress

## Distant TP review for current v6 portfolio (2026-07-29)

**What:** classify distant/improbable TP trades by donor strategy using a
continuous full-history v6 backtest, with fixed 5% and top-decile cohorts,
historical TP-price recency, exit reason, duration, and realized PnL.

**Why now:** live SOL entries included targets well outside the recent price
range. The owner wants evidence before lowering TP geometry while preserving
the strategies themselves.

**Expected gain:** identify whether a target cap or a lower per-strategy TP
improves dollars and drawdown without removing useful donors.

**Implementation status:** the causal policy is now implemented in
`backtester.tp_policy` and is applied by both `ExecutionSim` and the Railway
executor. It is disabled by default. Each event/trade records original and
effective RRR, adjustment reason, TP distance, and target recency; live state
keeps the same audit values in `signal_event` and the entry notification
explains a change in plain Russian. The canonical flexible-sandbox mount is
`params.components.distant_tp`; `strategies` overrides can enable/disable it
per donor, and the older `params.tp_policy` key remains an alias.

**Next steps:** the component remains globally default-off, while the
canonical production portfolio now mounts the approved rule only on
`freq_r03`. The selected candidate passed the first untouched forward check,
but that sample is only 15 days and 24 portfolio trades; keep monitoring the
live result and run a longer forward comparison before widening the mount to
other donors. Any future threshold change must beat the unchanged baseline in
dollars and drawdown without an unacceptable frequency change.

**Baseline evidence:** the 2025 owner run is
`results/strategy_review/v6_tp_2025/20260729_060548/`. It has 350 trades and
`+$55,945.85` PnL. The top 10% by TP distance (35 trades, threshold 9.3566%)
has `-$2,522.05`, 20% win rate, zero TP exits, 28 stop losses, four TTL exits,
and three trailing exits. A simple `TP >= 5%` cohort is profitable, so the
next comparison is an `rrr` cap at 4.0 versus 3.0 rather than deleting every
wide-target trade.

**Cap comparison:** global cap 4.0 produced `+$48,124.58` (352 trades,
peak-to-trough DD `-20.27%`); cap 3.0 produced `+$33,593.61` (368 trades,
peak-to-trough DD `-21.35%`). Both reduce PnL versus baseline `+$55,945.85`
and neither is suitable as a global production rule. The next candidate is a
targeted/dynamic rule based on TP distance or historical level recency, tested
on an untouched range rather than selected from 2025 in-sample results.

**Component comparisons:** portfolio-wide mount with `7%/720-bars -> RRR 3.0`
produced 371 trades and `+$41,734.46` on 2025; targeted mount on
`freq_r03`, `freq_r11`, `sparse_r06`, and `sparse_r12` produced 362 trades and
`+$48,270.88`. Both were below the unchanged 2025 baseline. On the first
continuous 2026 window (`2026-01-01` through `2026-06-29`, because local 1m
data has a full-day gap on June 30), baseline produced 224 trades and
`+$7,298.16`; targeted mount produced 228 trades and `+$8,040.15`. The
cross-period sign reversal is not robust enough for production.

**Full-period validation:** after the June 30 minute-data repair, both
configurations were replayed over the complete locally available history,
`2022-01-01` through `2026-06-30` (39,398 hourly bars). The unchanged v6
baseline artifact is `results/strategy_review/v6_2022_2026_baseline_full/20260729_083245/`:
1,508 trades, final capital `$956,449.50`, PnL `+$946,449.50`, win rate
`34.00%`, PF `1.47`, peak-to-trough DD `-39.23%`. The targeted dynamic-TP
artifact is `results/strategy_review/v6_2022_2026_targeted_full/20260729_082753/`:
1,568 trades, final capital `$735,712.38`, PnL `+$725,712.38`, win rate
`35.63%`, PF `1.47`, peak-to-trough DD `-33.27%`; it adjusted 455 entries.
Therefore the filter added 60 trades and reduced drawdown by 5.96 percentage
points, but destroyed `$220,737.12` of cumulative PnL (23.32% below the
baseline PnL). It stays default-off and is not a production promotion.

**Positive candidate search:** a threshold sweep then tested distance-only
mounts on `freq_4pw_r03_catcma_011465` with `adjusted_rrr=3.0`. The best tested
point was `min_tp_distance_pct=0.06` with `min_last_touch_bars=null` (recency
disabled), leaving every other donor unchanged. Full-history artifact:
`results/strategy_review/v6_tp_search_r03_d6_only_rrr3/20260729_105954/`.
It produced 1,560 trades and `+$1,175,598.82` PnL from `$10,000`, versus the
unchanged baseline's `+$946,449.50`: `+$229,149.32` / `+24.21%`; win rate
rose from `34.00%` to `35.56%`, and peak-to-trough DD improved from `-39.23%`
to `-33.26%`. Nearby tested thresholds were 5% (`+$1,145,957.30`), 7%
(`+$1,152,472.44`), 8% (`+$1,122,994.02`), 9% (`+$1,108,539.25`), and 10%
(`+$1,098,484.92`). The candidate then passed the first untouched
forward/holdout validation; only the approved `freq_r03` mount is enabled in
the canonical production JSON.

**Per-donor follow-up:** the same distance-only idea was tested separately on
three other donors. `sparse_r06` at 10%/RRR 3.0 was PnL-neutral
(`+$946,449.50`); `sparse_r12` at 10%/RRR 3.0 reduced PnL to
`+$852,043.63`; and `freq_r11` at 7%/RRR 3.0 reduced it to
`+$847,897.70`. Therefore there are not multiple positive TP-adjustment
components to combine: the evidence currently supports mounting only the
`freq_r03` candidate and leaving the other donors untouched.

**Holdout / forward validation:** the candidate was replayed against the
unchanged baseline on the continuous live-audit window `2026-07-13 00:00 UTC`
through `2026-07-27 23:00 UTC`, which was not used by the full-history search.
Both runs used the same 1m data, `$10,000` start, and 24 portfolio entries.
Baseline finished at `$10,307.89` (`+$307.89` PnL, 39.13% win rate, PF 1.23,
peak-to-trough DD `-9.50%`). The candidate finished at `$10,481.48`
(`+$481.48`, 43.48% win rate, PF 1.38, peak-to-trough DD `-8.71%`). That is
`+$173.59` / `+56.4%` more holdout PnL and 0.79 percentage points less
peak-to-trough drawdown with no trade-count loss. Three `freq_r03` entries
were adjusted; one changed from a baseline stop (`-$82.13`) to a target exit
(`+$97.27`), while the other two had the same realized exit. Artifacts:
`results/strategy_review/v6_holdout_baseline_20260713_27/20260729_114311/` and
`results/strategy_review/v6_holdout_candidate_r03_d6_rrr3_20260713_27/20260729_114324/`.

Artifacts: `results/strategy_review/v6_tp_dynamic_policy/20260729_080904/`,
`results/strategy_review/v6_tp_dynamic_targeted/20260729_081033/`,
`results/strategy_review/v6_2026_baseline_to_jun29/20260729_081320/`, and
`results/strategy_review/v6_2026_targeted_to_jun29/20260729_081404/`.

**Data limitation:** the attempted 2026-01-01 → 2026-07-28 run was rejected
because 1m execution coverage is incomplete from `2026-06-30 00:00 UTC`
(780 missing minutes). Its empty artifact is not a zero-trade result.
An agent-side repair attempt for `2026-06-30` hit repeated network failures at
OKX `public/instruments?instType=SPOT` before any bars were written, so the
owner must run the short one-day repair from an environment with OKX access.

**Retrospective bad-trade label:** among 124 trades with geometric `rrr >= 4`,
77 finished with negative realized PnL, totaling `-$23,443.86`. This is an
analysis label only; runtime cannot use future PnL. The negative rows are
exported in `high_rrr_negative_trades.csv` and grouped in
`high_rrr_negative_summary.csv`. The largest groups are `freq_r03` (64 rows,
`-$10,365`), `freq_r11` (5, `-$6,535`), and `sparse_r06` (6, `-$5,864`).

---

## Live execution vs backtest reconciliation audit (2026-07-28)

**What:** build an evidence-backed reconciliation of the Railway live SOL
portfolio from its first real entry on 2026-07-13 through the current live
period. Join Railway volume logs and persisted state, Telegram notifications,
OKX fills/orders/ledger, deployment/version boundaries, and an exact bounded
replay of the effective live strategy.

**Why now:** the owner wants live trade count, entry/exit set, and dollar PnL
to be compared with the backtester. The period contains known candle repairs,
WebSocket/REST callback failures, a restart catch-up entry, partial-close
recovery defects, and an exchange-sync block, so a naive fresh replay would
mislabel operational defects as strategy disagreement.

**Expected gain:** a cash-meaningful audit: every difference is classified as
normal fill/slippage, a known missed signal/downtime, an extra stale/catch-up
entry, an accounting/protection recovery event, a changed historical candle,
or an unresolved data gap. This will establish a reliable live baseline for a
$100-scale account before interpreting future strategy PnL.

**Acceptance:**

1. An immutable or reproducibly exported OKX fill/order/ledger table covers
   2026-07-13 onward and reconciles to the account cash path.
2. A UTC event ledger links every live entry/exit/blocked callback to Railway
   logs and Telegram evidence, with normal same-side OKX aggregation kept
   separate from logical constituents.
3. All confirmed outage/sync-block windows and delayed/extra entries are
   listed explicitly before comparison.
4. One owner-run exact replay command is frozen against the identified v6
   strategy/data window; its artifacts are compared trade-by-trade rather
   than only by aggregate PnL.
5. A report gives entry count, closed/open trade count, gross and net dollars,
   fees, entry/exit drift, matched/unmatched rows, and a final discrepancy
   verdict.

**Evidence already captured:** owner-run v6 replay artifacts are
`results/live_reconciliation/v6_capital_104_77/20260728_162345` and
`results/live_reconciliation/v6_capital_102_34/20260728_162357`. Phase B
matches all 16 real post-rollout entries and proves one missed short at
2026-07-23 12:00 UTC, worth `+$4.99897320` in the deterministic replay.
Phase A remains historically non-deterministic after H1 repair; its first
three entries retain the stored strict replay (`-1.685379` backtest versus
`-1.689069` OKX account PnL). Current Railway deployment `a7362c9` is
post-fix; earlier source version must be inferred from live event payloads and
logs rather than only deployment metadata.

**Links:** `docs/execution/live_backtest_reconciliation_2026-07-28.md`,
`docs/archive/candidates/post_adr0058_tail_control_portfolio/live_replay_20260714.md`,
`docs/execution/live_backtest_parity_audit_2026-06-30.md`, ADR-0048 through
ADR-0058, `/app/data/live_positions.json`, `/app/data/logs/crypt.log*`.

**Next steps:** after `2026-07-29T00:00:00Z`, the owner must run the one-day
backfill and continuous phase-B extension recorded in
`docs/execution/live_backtest_reconciliation_2026-07-28.md`. This appends the
five 28 July short entries/exits while preserving the 27 July open-position
path. Then join its artifacts to the final OKX ledger snapshot, classify the
remaining 28 July events, reconcile the cash bridge including type-8 balance
changes, and issue the complete-period verdict.

## Fresh post-ADR-0058 strategy search and portfolio rebuild (2026-07-08)

**What:** restart strategy discovery under the corrected minute execution and
OKX aggregate-average accounting stack, then optimize only the strongest fresh
families and assemble a new shared-capital portfolio from the survivors.

**Why now:** the corrected Core4 v3 rerun is economically weaker than the prior
canonical artifact and still fails the owner mandate. Old strategy and
portfolio artifacts were produced under execution/accounting assumptions that
are now known to be materially wrong, so they are research seeds, not promotion
evidence.

**Expected gain:** find candidates whose edge survives the current execution
model before spending time on live execution or polishing a failed portfolio.
The target remains the owner mandate: at least nine 2025 months above `$1,500`
on `$10,000`, no monthly drawdown breach above 10%, and no three consecutive
losing months.

**Acceptance:**

1. A fresh DSS/search artifact exists under the corrected code/data stack and
   exports a shortlist with trigger/filter/execution params.
2. Shortlist candidates pass a quick exact replay screen before any expensive
   Optuna budget is spent.
3. Big Optuna is run only for candidates that are not immediate discards on the
   quick exact screen.
4. Optimized winners are frozen as archive strategy JSONs with artifact links.
5. A new `filtered_donor_portfolio` config combines the top non-duplicative
   winners through the normal multi-signal shared-capital execution path.
6. Final portfolio backtest reports dollars, 2025 mandate rows, both drawdown
   metrics, liquidation count, exit mix, per-strategy PnL, and a promote /
   archive / discard verdict.

**Owner-run phase 1 command (fresh broad search):**

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester search-signals-matrix \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --catalog all \
  --stage-mode full \
  --min-trades 15 \
  --min-signals-per-week 0 \
  --stage1-min-wr 0.55 \
  --n-trials 50000 \
  --n-jobs-per-algorithm 1 \
  --output-root results/post_adr0058_dss_matrix_sol_20260708
```

Use higher `--n-trials` only after the first matrix shows exported candidates
or useful near-miss families. Inspect `summary.md`, `stage1_ranked.csv`,
`stage2_proxy.csv`, `stage3_full_scores.csv`, `candidate_manifest.md`, and
`candidates/*.json` before launching Optuna.

**2026-07-10 result:** owner completed
`results/post_adr0058_dss_matrix_sol_20260708/`. All five algorithms finished
cleanly with 50,000 generated candidates each, but exported zero candidates:
Stage 1 survivors `0`, Stage 2 survivors `0`, Stage 3 evaluations `0`, archive
cells `0`. This does not support launching big Optuna yet. The run was an
all-window robust search, so it rejected nearly everything on the first failing
window. Rejection shape was dominated by 2022: roughly 27k-31k candidates per
algorithm had too few 2022 signals, 18k-22k had weak 2022 barrier WR, and about
0.6k-0.7k overtraded 2022.

**Interesting near-miss families:** the best traces were not portfolio-ready,
but they show useful seed families for specialist search:

- `pt_ps_macd_signal_cross + pf_ps_smc_bias + pf_session`: 18 signals in 2022
  with 66.7% WR, 24 in 2023 with 62.5% WR, then failed 2024 badly at 28.6%.
- `pt_double_bottom_sweep + anchor_age/rsi/short_only/trend_strength`: 55.2%
  in 2022 and 68.2% in 2023, then failed 2024 at 30.4%.
- `pt_ps_ut_trail_cross + pf_ps_macd_hist_state + pf_ps_pivot_volume`: passed
  2022/2023 style checks but had only 12 signals in 2024.
- `pt_momentum_burst` with session/trend filters and
  `pt_ps_wavetrend_cross` with trendline/MACD-state filters repeatedly appear
  near the top but do not survive all years.

**Next owner-run phase:** switch from robust all-window search to
single-window specialist discovery so the project can build a basket of many
strategies. Run Stage 1-only matrices per target window; these should export
`stage1_candidates/*.json` for exact replay screening before Optuna:

```bash
MPLCONFIGDIR=/tmp/matplotlib UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester search-signals-matrix \
  --data-dir data --symbol SOL-USDT-SWAP \
  --windows 2022 \
  --catalog all --stage-mode stage1 \
  --min-trades 15 --min-signals-per-week 0 --stage1-min-wr 0.55 \
  --n-trials 30000 --n-jobs-per-algorithm 1 \
  --output-root results/post_adr0058_specialists_sol_2022_20260710
```

Repeat the same command with `--windows 2023`, `--windows 2024`, and
`--windows 2025H1`, changing only `--output-root`. If CPU/RAM is available,
these four independent matrices can run in parallel; otherwise run them one at
a time. After they finish, exact-test the exported `stage1_candidates/*.json`
before any big Optuna.

**Links:** ADR-0058, ADR-0056, ADR-0057, ADR-0047,
`docs/discovery/direct_signal_search_v2.md`,
`docs/multi_signal_execution.md`.

**2026-07-12 Optuna seed prep:** exported the current Stage 1 near-miss tops
from the owner's WR45 sparse and 4-per-week frequent searches as replayable
`dss_strategy` JSONs under
`results/post_adr0058_top_for_optuna_20260712/`.

- `sparse_0pw/strategies/`: 12 stronger sparse seeds; these are the preferred
  first Optuna budget because they show multi-year shape despite failing one
  barrier.
- `freq_4pw/strategies/`: 12 frequent seeds; treat as a separate, lower-trust
  batch because several rows scored well on only 4-7 trades before failing the
  4-per-week gate.
- `manifest.csv`: combined rank/source/trigger/filter/window metrics for both
  batches.

Next owner-run step: run execution-parameter Optuna on these exported JSONs,
preferably training on 2022-2024 and validating winners out of sample on 2025
before any portfolio assembly. Keep sparse and frequent outputs separate.
Use
`results/post_adr0058_top_for_optuna_20260712/run_split_rrr_optuna_progress.py`
for the owner-run Optuna batch; it shows total trial progress, active jobs,
ETA, output paths, and per-job log links while keeping parallel Optuna logs
separate.

**2026-07-12 Optuna result:** owner completed the split-RRR Optuna batch at
`results/post_adr0058_optuna_top_train_big_split_rrr_20260712/`. A summary was
written to `summary.md` and `optuna_summary.csv`. All best trials still have
mandate verdict `discard` on the 2022-2024 train window. Best train shapes:

- `sparse_0pw/rank_06_hyperband_001552`: `+374.37%`, 79 trades, 16 passing
  months, 20 below-floor months, six DD breach months, worst monthly DD
  `-26.56%`.
- `sparse_0pw/rank_12_hyperband_017877`: `+247.77%`, 102 trades, 11 passing
  months, 25 below-floor months, five DD breach months, worst monthly DD
  `-22.98%`.
- `freq_4pw/rank_09_hyperband_010009`: `+112.66%`, only 15 trades, seven
  passing months, 29 below-floor months, one DD breach month.

Next useful step: do not promote a single strategy from this batch. Either add
stronger post-entry/month-regime filters to the top sparse winners, or assemble
a low-risk exploratory portfolio from non-overlapping top sparse components
and validate on 2025 before any promotion decision.

**2026-07-13 all-24 portfolio prep:** built an exploratory shared-capital
portfolio combining all 24 split-RRR Optuna best trials:
`results/post_adr0058_portfolio_all24_split_rrr_20260713/filtered_donor_portfolio_all24_split_rrr.json`.
Each donor was frozen with its best-trial execution parameters under
`frozen_strategies/`, and `portfolio_manifest.csv` links each donor to its
source Optuna trial. Config load validation passed with 24 nested strategies,
`intrabar_execution_timeframe=1m`, and `risk_base_period=monthly`. Owner-run
full-period backtest is required next.

**2026-07-13 all-24 full backtest result:** owner ran the full-period v1 source
artifact at
`results/post_adr0058_portfolio_all24_split_rrr_20260713/backtest_full/20260712_223913/`.
It made `$10,000 -> $172,325.77` (`+1623.26%`) but is not promotable: profit
factor `1.01`, peak-to-trough DD `-90.72%`, 27 liquidations plus one unsafe
liquidation-buffer exit, and severe bad months including `2025-12 -55.72%`,
`2026-04 -48.06%`, and `2026-05 -41.32%`. Strategy attribution files were
written into that artifact:
`strategy_contribution.csv`, `strategy_monthly_pnl.csv`,
`worst_month_strategy_contributors.csv`, and `bad_month_strategy_score.csv`.

Archived:

- v1 exact all-24:
  `strategies/archive/filtered_donor_portfolio_post_adr0058_all24_v1.json`
- v2 reduced risk-capped first cut:
  `strategies/archive/filtered_donor_portfolio_post_adr0058_reduced_v2_risk1.json`

v2 keeps seven donors (`freq_4pw_r03_catcma_011465`,
`freq_4pw_r02_hyperband_004678`, `freq_4pw_r09_hyperband_010009`,
`sparse_0pw_r06_hyperband_001552`, `sparse_0pw_r11_island_2024_021423`,
`sparse_0pw_r07_hyperband_019621`, `sparse_0pw_r09_catcma_013114`) and caps
their risk to at most `1.0` for the first DD-control test. Config validation
passed: v1 has 24 donors; v2 has 7 donors with risk `0.5-1.0`.

**2026-07-13 v2 result and v3 return-first prep:** owner ran v2 at
`results/post_adr0058_portfolio_reduced_v2_risk1_full_20260713/20260712_225328/`.
It reduced the outcome to `$10,000 -> $62,074.13` (`+520.74%`), PF `1.10`,
drawdown below start `-2.49%`, peak-to-trough DD `-39.28%`, 19 liquidations
plus four unsafe liquidation-buffer exits. Owner redirected the research order:
first maximize peak/final return, then reduce drawdowns. Created v3 as a
return-first archive:
`strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v3.json`.
v3 keeps the 12 v1 donors with positive all-period PnL, preserves original
Optuna risk (`0.5-3.0`), and removes only net-negative v1 donors. Manifest:
`strategies/archive/post_adr0058_return_first_v3_manifest.csv`.

**2026-07-13 v3 result and v4 prep:** owner ran v3 at
`results/post_adr0058_portfolio_return_first_v3_full_20260713/20260712_230512/`.
It reached `$10,000 -> $883,881.46` (`+8738.81%`), PF `1.09`, drawdown below
start `-1.36%`, peak-to-trough DD `-62.81%`, 19 liquidations plus three unsafe
liquidation-buffer exits. Strategy attribution files were written into the v3
artifact. Created v4 as a minimal return-preserving cleanup:
`strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v4_positive_v3.json`.
v4 removes only the four v3 net-negative donors
(`sparse_0pw_r09_catcma_013114`, `sparse_0pw_r06_hyperband_001552`,
`freq_4pw_r05_island_2023_001587`, `sparse_0pw_r10_island_2022_000031`) and
keeps original Optuna risk for the remaining eight donors. Manifest:
`strategies/archive/post_adr0058_return_first_v4_manifest.csv`.

**2026-07-13 v4 result and v5 tail-control prep:** owner ran v4 at
`results/post_adr0058_portfolio_return_first_v4_positive_v3_full_20260713/20260712_231303/`.
v4 made `$10,000 -> $340,047.49` (`+3300.47%`), PF `1.09`, drawdown below
start `-1.36%`, peak-to-trough DD `-58.44%`, 18 liquidations plus four unsafe
liquidation-buffer exits. This was a poor trade-off versus v3 because final
capital fell by roughly `$543k` while peak-to-trough DD improved only about
4.37 percentage points. Owner chose to continue from v3 and reduce drawdowns
with minimal return loss. Created v5:
`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v5_filtered_v3.json`.
v5 keeps all 12 v3 donors and original Optuna risk, but adds one entry-known
`catalog_*` filter per donor based on v3 bad-month attribution. This is a
research artifact; filters are derived from the full-period v3 run and require
validation after the full-period check.

**2026-07-13 v5 result:** owner ran v5 at
`results/post_adr0058_portfolio_tail_control_v5_filtered_v3_full_20260713/20260712_232331/`.
This is the best research artifact so far: `$10,000 -> $1,360,197.25`
(`+13501.97%`), PF `1.39`, drawdown below start `-6.79%`,
peak-to-trough DD `-39.14%`, nine liquidations, and no unsafe
liquidation-buffer exits. This improves both v3 return (`+8738.81%`) and v3
peak-to-trough DD (`-62.81%`). Remaining weak spots are still `2026-04
-17.33%`, `2025-12 -8.03%`, and early 2022 drawdowns. v5 attribution files
were written in the artifact; current net-negative donors after filtering are
`sparse_0pw_r01_smac_018790` (`-$101,229.69`) and
`freq_4pw_r05_island_2023_001587` (`-$55,313.64`).

**2026-07-13 v6 prep:** created
`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`.
v6 removes only the two v5 net-negative donors
(`sparse_0pw_r01_smac_018790`, `freq_4pw_r05_island_2023_001587`) and keeps
the other ten v5 donors with their filters and original Optuna risk. Expected
trade density from v5 trades remains acceptable: 1494 trades over 237 weeks,
6.3/week average, seven weeks below two trades, and 50 weeks below four trades;
for `2025+`, 550 trades, 7.05/week average, zero weeks below two trades, six
weeks below four trades. Manifest:
`strategies/archive/post_adr0058_tail_control_v6_manifest.csv`.

**2026-07-13 v6 result:** owner ran v6 at
`results/post_adr0058_portfolio_tail_control_v6_drop_negative_v5_full_20260713/20260713_100653/`.
Result: `$10,000 -> $1,098,402.88` (`+10884.03%`), PF `1.48`, drawdown below
start `-17.75%`, peak-to-trough DD `-39.23%`, nine liquidations, zero unsafe
liquidation-buffer exits, 1515 trades. Weekly density remains acceptable: 6.39
trades/week average, median six, seven weeks below two trades, 48 weeks below
four trades. All ten remaining donors are net-positive after attribution.
Worst residual trade-PnL months are `2026-04 -$156,980`, `2025-12 -$35,037`,
and `2024-11 -$12,272`; next improvement should focus on `2026-04` without
damaging the high-return donors.

**2026-07-13 v7 prep:** created
`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v7_apr2026.json`.
v7 starts from v6 and adds one extra AND filter to the four main `2026-04`
loss contributors while preserving all ten donors and original Optuna risk:
`sparse_0pw_r07_hyperband_019621` requires `catalog_bb_width_pct <=
0.03957995`; `sparse_0pw_r11_island_2024_021423` requires
`catalog_trend_strength_atr >= 0.22770487`; `freq_4pw_r03_catcma_011465`
requires `catalog_rsi14 <= 52.60144416`; `freq_4pw_r02_hyperband_004678`
requires `catalog_trend_strength_atr >= 0.72252106`. Manifest:
`strategies/archive/post_adr0058_tail_control_v7_manifest.csv`. Config load
validation passed with 10 donors and 14 total filter rules.

**2026-07-13 v7 result:** owner ran v7 at
`results/post_adr0058_portfolio_tail_control_v7_apr2026_full_20260713/20260713_102023/`.
Result: `$10,000 -> $866,481.95` (`+8564.82%`), PF `1.90`, drawdown below
start `-6.85%`, peak-to-trough DD `-32.33%`, five liquidations, zero unsafe
liquidation-buffer exits, 935 trades. It strongly improves v6 risk quality and
nearly fixes `2026-04` (`-2.41%` monthly return), but trade density is now near
the lower operator bound: 3.95 trades/week average, median four, 31 weeks below
two trades, and 114 weeks below four trades. For `2025+`, 359 trades over 78
weeks, 4.6/week average, five weeks below two trades, 28 below four. All donors
except `sparse_0pw_r06_hyperband_001552` are net-positive after attribution.
Current branch decision: v6 is the higher-return/high-density base; v7 is the
lower-DD/cleaner base. A likely v8 should relax only the harshest v7 filters
that caused the trade-density drop, not revert all v7 changes.

**2026-07-13 archive package:** preserved the full v1-v7 research lineage at
`docs/archive/candidates/post_adr0058_tail_control_portfolio/`. The archive
contains version summaries, donor composition and filters, exact owner-run
commands, portfolio JSON snapshots, compact backtest snapshots, complete
copied full backtests, source Optuna research artifacts, strategy attribution,
and monthly strategy PnL. Use this package before rerunning any v1-v7
full-period backtest.

---

## Core4 v3 OKX aggregate-average rerun review (2026-07-08)

**What:** owner completed the canonical minute last/mark rerun after ADR-0058.
The accepted artifact for this local session is
`results/core4_v3_okx_aggregate_average_2026070/20260708_054313/` (note the
output directory typo: `2026070`, not `20260703`). The earlier failed empty
artifact `20260708_050411/` is invalid and must not be used.

**Why now:** this replaces the superseded 2026-07-02 `$25,100.59` minute
artifact, which still used constituent entry prices instead of OKX aggregate
average-entry accounting.

**Result:** `$10,000` became `$24,195.85` (`+141.96%`) with 3,425 entries,
3,423 closed trades, two open trades, profit factor `1.05`, drawdown below
start `-9.20%`, peak-to-trough drawdown `-42.84%`, and nine liquidations.
Cash reconciles exactly:
`$10,000 + $14,204.343855912753 closed PnL - $8.4947749 open entry fees =
$24,195.849081012755`.

**2025 mandate verdict:** `discard`. Only four months pass the `$1,500` / 15%
floor: April, May, July, and September. Eight months are below the floor;
five months breach the 10% monthly below-start drawdown limit. Worst monthly
drawdown is `-19.42%` in March. Sum capped monthly return is `+77.97%`.

**Validation completed locally:**

1. `trades.csv` exports `aggregate_entry_price`.
2. H1 OHLCV export has 39,711 rows, spans `2021-12-18 00:00 UTC` →
   `2026-06-29 14:00 UTC`, has zero duplicates, and zero hourly gaps.
3. Artifact includes `metrics.csv`, `trades.csv`, `equity_curve.csv`,
   `signals.csv`, `signal_diagnostics.csv`, `trade_diagnostics.csv`,
   `ohlcv.csv`, and `trade_chart.html`.
4. Hashes for the new artifact:
   - `signals.csv`:
     `9afa6db1fcd013edec80dd20a389fc9e4c0f004dda8f28589a77f7a0f1072041`
   - `signal_diagnostics.csv`:
     `57a618f70ce6ae970a2036c50e1f04b2f823ac6a4a988c55e9f1a07dfb1c8716`
   - `ohlcv.csv`:
     `493dd2adf167268a08b6572c7d5cab699dfe3e9d1841e949d9d6d9eeaed157e6`

**Remaining next step:** compare those hashes to the superseded local/owner
artifact `results/core4_v3_minute_last_mark_20260702/20260702_102019/` if it
is available on another machine. That artifact is not present in this local
workspace, so byte-identical signal/OHLCV parity against the previous canon
could not be verified here. The money verdict does not depend on that compare:
the aggregate-average rerun still fails the owner mandate.

**Links:** ADR-0058, `docs/execution/liquidation_safe_leverage.md`,
`docs/execution/minute_intrabar_execution.md`.

---

## Core4 v3 OKX aggregate-average rerun command (2026-07-03)

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
