# crypt

Modular ensemble decision system for crypto perpetual futures markets.

> Continuously monitors a small basket of OKX perpetual contracts, runs several
> independent "trader views" (trend, mean-reversion, derivatives positioning,
> volatility regime, ...), aggregates them into a single weighted verdict
> (`BUY` / `SELL` / `HOLD` + confidence + rationale) and pushes alerts to
> Telegram.
>
> Goal of v1: signal generation for the owner to trade manually.
> Goal of vN: **automated execution** once a strategy candidate passes the
> owner investment mandate.

This is **not** a trading bot yet. It is a research-and-alerting system moving
toward auto-trading after backtest gates are met.

## Owner targets (candidate gates)

Full spec: **`docs/investment_mandate.md`** (ADR-0025). Summary:

- **+$1 500/month** minimum (**+15%** on a **$10k** portfolio) after fees.
- **2025** full-year continuous backtest; **SOL first**, then **TON**.
- Max **10% drawdown inside any month**; month above that → archive.
- Up to **3** months below 15% allowed; **3** consecutive losing months → discard.
- Auto-trading code only **after** a candidate **promotes** under the mandate.

## Status

**M1 complete.**
All signal-only MVP components are implemented and the live manual-alerting
surface has already been completed. Engines, aggregator, decision layer, sinks,
runtime, retry/backoff, heartbeat, log rotation, service config, and Railway
deployment docs are in place.

Current active work is **M2 donor backtester migration and candidate search**.
`backtester` is a root-integrated package under `src/backtester` (ADR-0023).
`discover-strategies` ranks H1 trigger+filter stacks; converted candidates run
through donor `crypt_ensemble` + mandate `compare-fixed` / Optuna.
The longer-term research direction is regime-aware routing: keep searching and
archiving useful strategy families, then infer market regimes from the archived
strategy performance matrix and train an online detector/router
(`docs/regime_detection.md`, ADR-0041).

Current archived regime seeds include NR4 VWAP robust, NR7 BB squeeze, VWAP
reclaim, MACD squeeze, double-bottom body-to-range, and engulfing BB trend.
NR4 is now archived under `docs/archive/candidates/nr4_vwap_robust/` after a
2022-2024 execution-only Optuna best-run; it remains a `discard`/research seed,
not a production candidate.

See `docs/tasks/ROADMAP.md` for milestones.

## Stack

- Python 3.11+
- [`ccxt`](https://github.com/ccxt/ccxt) — OKX market data (REST)
- `pandas` + `pandas-ta` — indicators
- `pydantic` v2 + `pydantic-settings` — typed config
- `APScheduler` — periodic 4h-aligned loop
- `aiogram` — Telegram alerts
- `loguru` — logging
- `pytest` — tests
- `ruff` + `mypy` — lint / type check
- `uv` — package manager
- `mise` — optional local tool/task runner

No database, no Redis, no Docker in MVP.

## How it is developed

This repository is built **AI-first**. The owner sets global goals in chat;
agents own implementation planning, scaffolding and documentation.

Anyone (human or agent) contributing should first read:

1. `AGENTS.md`
2. `docs/investment_mandate.md`
3. `.cursor/rules/ai-first-workflow.mdc`
4. `docs/tasks/IN_PROGRESS.md`
5. `docs/tasks/ROADMAP.md`
6. The most recent entries in `CHANGELOG.md`

## Quick start

```bash
uv sync --all-extras
cp .env.example .env   # fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# One-shot tick (bootstrap + evaluate once, no scheduler):
uv run python -m crypt --once

# Live loop (runs every 4h):
uv run python -m crypt

# Custom symbols:
uv run python -m crypt --symbols SOL-USDT-SWAP,TON-USDT-SWAP
```

## Historical backfill (M2 data)

Primary M2 calibration is OHLCV-only (ADR-0017): no paid derivatives,
liquidations, or sentiment data until the candle-only system demonstrates
value. See `docs/backfill.md` and `docs/backtester_migration.md`.

```bash
# M2 primary backfill (OHLCV-only per ADR-0017)
PYTHONPATH=src uv run python -m crypt.backfill \
    --symbol SOL-USDT-SWAP \
    --from 2024-02-01 --to 2026-06-01 \
    --data-types ohlcv

# Then run donor-backed backtests from the repository root.
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/backtester/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

Data lands in `data/<SYMBOL>/` (Parquet). Re-running is idempotent.

Execution-grade H1 replay additionally uses monthly-partitioned OKX 1m
last-trade and mark-price candles. The signal remains H1; minute data only
orders stop, TP, native-trailing, and liquidation events inside each hour.
Use the parallel `last_1m` / `mark_1m` commands in `docs/backfill.md`.

Live Telegram execution notifications are Russian and operator-oriented: they
separate a real opened trade, an alert-only price drift, and a safety-paused
entry. The durable monthly risk-base checkpoint and its Railway migration are
documented in `docs/execution/live_execution.md` and `docs/deploy/railway.md`.

## Backtester (M2)

ADR-0018 moves future M2 work toward the donor `backtester/` package.
ADR-0023 integrates it into the root `uv` project as `src/backtester`; it is
not a nested repository and no longer has its own `pyproject.toml`, `uv.lock`,
Hatch config, or subdirectory `mise` file. The donor package is treated as a
high-risk source-of-truth dependency: avoid rewriting its internals and prefer
adapting `crypt_ensemble` to its existing strategy API.

The current `crypt_ensemble` donor strategy runs the existing engines and
aggregator over project Parquet data and emits donor-compatible `signal`,
structural SMC `sl_price`, and verdict metadata. It leaves `entry_price` empty
so donor execution enters at the next execution-bar open after a closed signal
candle. Stop-losses are anchored to active order blocks, fresh liquidity
sweeps, or confirmed pivots with an ATR buffer; if no structural anchor exists,
the donor signal is neutralized by default instead of falling back to
mechanical ATR-only stops.
Default-off H1 diagnostics can filter selected signals by side, structural
anchor type allow/block lists, anchor age, context reversal, and selected
stop-distance ATR range.
Donor execution exports `signal_time`, `risk_base_capital`, confidence, score,
regime, rationale, stop diagnostics, margin diagnostics, and per-engine
strengths into `trades.csv` for audit. Margin diagnostics include
`locked_margin`, `available_balance_before`, `open_positions_before`, and
total locked margin before/after entry. It also writes
`trade_diagnostics.csv`, a compact report for exit reason, side, PnL,
structural stop distance, and peak margin/concurrency analysis. Per ADR-0019,
`crypt_ensemble` sizes risk from the capital at the beginning of each calendar
month (`risk_base_period = monthly`) instead of compounding every trade from
current capital. Per ADR-0020, the live Telegram alert threshold of `75` is an
arbitrary placeholder and is not the default donor entry gate; BUY/SELL
verdicts are tradeable by default when a valid structural stop exists, while
`min_confidence` remains available as an explicit diagnostic parameter. Full
SOL smoke backtests are currently slow because each bar replays the whole
ensemble; H1 MTF runs are especially expensive until the donor route gets a
range limiter or parity-safe cache.

The filtered donor portfolio also supports an opt-in causal distant-TP
component. Mount it at `params.components.distant_tp` to lower effective RRR
for wide or historically stale targets while preserving the signal, structural
SL, and risk sizing; per-donor overrides can mount or unmount it independently.
It is disabled by default; see `docs/backtester/tp_reachability_diagnostics.md`
for fields, audit columns, and validation requirements.

`backtester run` supports optional profit sweep modes for
withdrawal-style diagnostics:

```bash
uv run backtester run ... --capital 10000 --capital-sweep monthly_profit
uv run backtester run ... --capital 10000 --capital-sweep trade_profit
```

`monthly_profit` removes realized trading capital above the initial capital at
month boundaries and counts it as banked profit. `trade_profit` applies the
same rule immediately after each profitable closed trade. If the trading
account is below the initial capital, nothing is added and the reduced account
continues. Reports keep `Final Capital` as the remaining trading account and
add `Banked Profit` plus `Total Account` when money was swept. The monthly
console table also includes `Withdrawn ($)`, the amount withdrawn for that
specific month; months without a withdrawal show `0`.

```bash
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/backtester/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

Experimental H1 MTF mode keeps D1/H4 as context/setup but uses H1 as the
primary execution frame. H1 entries now require explicit structural trigger
rules (`h1_sweep_reversal`, `h1_structure_break`, or
`h1_order_block_retest`) instead of the earlier legacy candle-colour
confirmation. The current diagnostic H1 config uses
`max_sl_distance_atr = 4.0` to reject structural stops wider than 4 execution
ATR; this is an explicit setup-geometry tuning knob, not a calibrated final
parameter. The H1 diagnostic config also enables `optimized_windows`, a
reference-vs-optimized parity-tested cache for closed candle/extras window
selection; set it to `false` in the strategy params to force the original
per-bar reference path. Per ADR-0022, H1 MTF mode also treats the H4 setup
verdict as a snapshot at the latest closed H4 setup time and reuses it across
H1 trigger bars until the next H4 close. The donor optimizer can now cache
generated `crypt_ensemble` signal frames, so repeated execution-only
`rrr`/`ttl` trials avoid rerunning the full ensemble. The optimizer CLI also
reuses the cached best signal frame when exporting `best_run/`, so
execution-only runs should pay for only one signal build per strategy-param
set.

Every donor run export now writes an operator-facing chart frontend next to
the CSV artifacts:

- `ohlcv.csv` — the continuous candle frame used by the run.
- `trade_chart.html` — a TradingView Lightweight Charts report with candles,
  signal markers, entry/exit markers, and entry/TP/SL/trailing-stop level
  overlays.

The report is generated automatically for `backtester run`, optimizer
`best_run/`, `compare-fixed` window runs, `compare-grid` candidate runs, and
`signal-quality` window runs whenever OHLCV is available. To regenerate an old
artifact manually:

```bash
uv run backtester trade-chart \
    --run-dir results/crypt_ensemble_sol_h1/20260607_183249/runs/sol_2025_01
```

Manual regeneration reads `trades.csv`, optional diagnostics CSVs, and
`ohlcv.csv` by default; pass `--ohlcv` for a full external CSV/Parquet candle
source. Legacy `trade_candles/` slices are only a fallback for old artifacts and
do not provide a continuous between-trade chart.

```bash
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_sol_h1
```

Use `discover-strategies` before more manual H1 trigger/filter backtests. It
ranks one-trigger plus filter-stack candidates by fixed ATR-barrier forward
labels and exports a shortlist for later donor execution validation.

Convert a discovery-native candidate into a donor strategy config:

```bash
uv run backtester convert-discovery-strategy \
    --input results/discovery_sol_h1_2025_monthly/20260608_113331/best_candidates/rank_001_strategy.json \
    --output strategies/backtester/my_candidate.json
```

The current full-year shortlist reference config is
`strategies/backtester/crypt_ensemble_h1_discovery_momentum_burst_short.json`.
See `docs/strategy_discovery.md` §13 for conversion semantics.

Direct Signal Search v2 searches trigger/filter/execution parameters with a
staged quality-diversity pipeline instead of the retired Optuna NSGA-II sampler
path. The command writes viability, proxy, full-score, archive, and candidate
manifest artifacts directly under the chosen output directory. Removed v1 flags
such as `--sampler`, `--resume`, `--max-filters`, and `--accept-min-score` are
not part of the operator interface.
By default DSS searches the legacy trigger/filter catalog. Use
`--catalog pinescript_v1` to search only the PineScript-derived catalog built
from the local TradingView idea set, or `--catalog all` for later comparison
after the pure catalog has been inspected.
The PineScript catalog now includes both the first indicator slice and the
SMC/ICT slice from `smc.pine`: BOS/CHoCH, FVG, equal highs/lows,
premium/discount, and order-block retest primitives.
The default backend is `--algorithm staged`. For non-duplicative exploratory
runs, `--algorithm catcma_qd` enables the experimental CatCMA-inspired
quality-diversity backend from ADR-0037. `--algorithm island_qd` enables the
window-specialist island backend from ADR-0038 for Railway-scale runs where
each island optimizes one training window before occasional robust checks.
`--algorithm hyperband_qd` enables the ADR-0039 successive-halving backend:
large batches pay cheap Stage 1 first, then only behavior-diverse top fractions
advance to progressively more expensive proxy/full scoring. `--algorithm
smac_qd` enables the ADR-0040 random-forest surrogate backend: bootstrap random
design first, then score large proposal pools with RF mean + tree-dispersion
uncertainty before evaluating selected infill candidates. CatCMA-QD, Island-QD,
Hyperband-QD, and SMAC-QD cap expensive Stage 2+ backtests per candidate batch;
most generated candidates only pay the cheap Stage 1 signal-viability check.
Stage 1 is a volatility-normalized directional label: next-open entry,
ATR-scaled favorable/adverse barriers calibrated from the SOL reference
`0.7% / 0.4%`, same-bar TP+SL counted as SL, and unresolved end-of-window tails
excluded from the Stage 1 win-rate denominator. Candidate `rrr`, risk percent,
ATR stop distance, TTL, fees, sizing, and execution overlap are searched or
scored only in later stages.
DSS strategy JSON replay treats flat `params` execution fields
(`rrr`, `risk_percent`, `trail_distance_atr`, `position_ttl_bars`) as
backtest defaults when `backtest_args` is absent, so manual `backtester run`
matches the execution settings printed for optimizer/manual candidates.
Archived DSS configs may also use two entry-only replay controls:
`allowed_signal=-1` or `1` keeps only shorts or longs, and
`entry_skip_rules` can skip signals using features known at the next-bar entry,
currently `entry_dayofweek` and `stop_distance_pct`. These controls are
intended for exact replay of validated trade-filter research, not for deleting
trades from CSV after the fact.

```bash
uv run backtester search-signals \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --windows 2022,2023,2024,2025H1 \
    --n-trials 50000 \
    --n-jobs 4 \
    --output results/dss_sol_v2
```

```bash
uv run backtester search-signals \
    --catalog pinescript_v1 \
    --stage-mode stage1 \
    --min-signals-per-week 4 \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --windows 2023 \
    --n-trials 50000 \
    --n-jobs 4 \
    --seed 73023 \
    --output results/dss_sol_pinescript_v1_2023_seed73023
```

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

```bash
uv run backtester search-signals \
    --algorithm island_qd \
    --seed 2026 \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --windows 2022,2023,2024,2025H1 \
    --n-trials 120000 \
    --output data/results/dss_sol_island_qd_railway_seed2026
```

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

To launch the full five-algorithm DSS matrix at once, use
`search-signals-matrix`. It starts one child `search-signals` process per
algorithm and writes each process log under its output directory:

```bash
uv run backtester search-signals-matrix \
    --data-dir data \
    --symbol SOL-USDT-SWAP \
    --windows 2023 \
    --catalog all \
    --stage-mode stage1 \
    --min-signals-per-week 4 \
    --stage1-min-wr 0.45 \
    --n-trials 50000 \
    --n-jobs-per-algorithm 1 \
    --output-root results/dss_stage1_matrix_all_2023
```

Default algorithms are `staged`, `catcma_qd`, `island_qd`, `hyperband_qd`, and
`smac_qd` with the standard seeds used in DSS handoffs. Total requested workers
are `algorithm_count * n_jobs_per_algorithm`. `--stage1-min-wr` controls only
the Stage 1 barrier win-rate gate; signal-count and overtrading gates still
apply unchanged.

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

Inspect `summary.md`, `archive.md`, `stage1_viability.csv`,
`stage1_ranked.csv`, `stage1_near_misses.csv`, `stage1_specialists.csv`,
`stage2_proxy.csv`, `stage3_full_scores.csv`, and `candidate_manifest.md` first. In
`--stage-mode stage1`, DSS stops before backtests, writes a Stage 1-only
shortlist to `stage1_ranked.csv`, and exports research configs under
`stage1_candidates/`. `stage1_specialists.*` preserves target-window
specialists for later routing analysis; those rows are not promotion-ready
exports and are only produced when `--specialist-windows` is set. Leave
`--specialist-windows` empty for the fast all-window early-reject path.
Exported full-mode `candidates/*.json` files are replayable via
`compare-fixed` and `walk-forward`.

Regime research starts by building a comparable matrix from archived
strategies. The command below runs every `strategies/archive/*.json` strategy
on the same SOL window and writes bucket-level CSVs plus raw per-strategy
trades:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester archived-performance-matrix \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2022-01-01 \
    --to 2025-12-31 \
    --bucket month \
    --include-archive \
    --jobs 3 \
    --output results/regime_matrix_archive_sol_2022_2025
```

Outputs are `strategy_manifest.csv`, `bucket_metrics.csv`,
`matrix_return_pct.csv`, `matrix_trade_count.csv`, `summary.md`, and
`strategy_trades/<strategy_id>.csv`.

The first offline oracle-label dataset is built from the archive-only matrix
and detector-safe OHLCV features:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester oracle-regime-labels \
    --matrix-dir results/regime_matrix_archive_sol_2022_2025 \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2021-12-18 \
    --to 2025-12-31 \
    --bucket month \
    --output results/regime_matrix_archive_sol_2022_2025/oracle_labels
```

Outputs are `oracle_labels.csv` and `summary.md`. Labels select the best
archived strategy per bucket; OHLCV features are computed strictly before the
bucket start.

For denser detector training, generate rolling daily labels from raw trades:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester rolling-regime-labels \
    --matrix-dir results/regime_matrix_archive_sol_2022_2025 \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2022-01-01 \
    --to 2025-12-31 \
    --step day \
    --horizon-days 30 \
    --min-history-days 90 \
    --output results/regime_matrix_archive_sol_2022_2025/rolling_labels_day_30d
```

Rolling labels use features available before each `T` and select the best
archived strategy over the future window `[T, T + horizon)`. New rolling-label
artifacts also include `router_ps_*` market-state features derived from the
local PineScript idea set through native Python implementations: Supertrend,
ADX/DI, squeeze momentum, WaveTrend, MACD, Vix Fix, trendlines, killzones, and
SMC state.

Evaluate simple live-safe routers over those rolling labels:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester rolling-router-baseline \
    --labels results/regime_matrix_archive_sol_2022_2025/rolling_labels_day_30d/rolling_labels.csv \
    --validation-start 2024-01-01 \
    --min-available-strategies 3 \
    --lookback-days 365 \
    --output results/regime_matrix_archive_sol_2022_2025/rolling_labels_day_30d/router_baseline
```

The router baseline is an offline diagnostic. It uses only completed prior
label windows (`label_end <= asof`) when selecting weights.

Search single-strategy routers with a larger catalog:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester router-search \
    --labels results/regime_matrix_archive_sol_2022_2025/rolling_labels_day_30d/rolling_labels.csv \
    --validation-start 2024-01-01 \
    --min-available-strategies 6 \
    --max-configs 2000 \
    --output results/regime_matrix_archive_sol_2022_2025/rolling_labels_day_30d/router_search
```

`router-search` never splits capital between strategies and never chooses
`cash`. Each candidate selects exactly one archived strategy, then scores offset
robustness, drawdown, negative periods, and switching cost. See
`docs/regime_router_search.md`.

For large Router Catalog v2 runs, use `--catalog-version v2 --summary-only`.
The v2 catalog contains more than 4.6 million deterministic combinations;
summary-only mode retains full predictions and offset detail only for the top
shortlist.

V2 also supports `grid`, `random`, `island_qd`, `hyperband_qd`, and `smac_qd`
search backends. Launch the four stochastic backends together with:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester router-search-matrix \
    --labels results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/rolling_labels.csv \
    --validation-start 2024-01-01 \
    --validation-end 2025-01-01 \
    --max-configs 25000 \
    --output-root results/router_search_matrix_v2_25k
```

Replay an archived router through one shared-capital portfolio:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester router-validate \
    --predictions results/router_search_matrix_v2_25k/random_seed1101/router_search_predictions.csv \
    --router router_v2_3216811 \
    --matrix-dir results/regime_matrix_archive_sol_2022_2025_trades \
    --from 2025-01-01 \
    --to 2026-01-01 \
    --capital 10000 \
    --max-allowed-margin 1.0 \
    --output results/router_validation_v2_3216811_2025
```

The validator uses one active strategy, no cash state, shared capital/margin,
and drain-before-switch execution. See `docs/routed_execution_validation.md`.

Mass router search now ranks candidates by robust regret to the
single-strategy oracle and writes `router_shortlist.csv`. Replay the complete
shortlist before exact composite validation with:

```bash
uv run backtester router-validate-shortlist \
    --predictions <search-output>/router_search_predictions.csv \
    --shortlist <search-output>/router_shortlist.csv \
    --matrix-dir results/regime_matrix_archive_sol_2022_2025_trades \
    --from 2025-01-01 \
    --to 2026-01-01 \
    --output <search-output>/routed_shortlist
```

Promoted routers are implemented as normal strategies. `router_v2_2687609`
uses all six archived strategies internally and runs through the standard
backtester:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2022-12-18 \
    --to 2026-06-10 \
    --strategy strategies/archive/router_v2_2687609.json \
    --capital 10000 \
    --output results/router_v2_2687609_full
```

The strategy consumes persisted completed rolling labels, selects one nested
strategy causally, and emits its signals through the normal external
backtester. It never launches nested backtests. The labels artifact referenced
by the strategy config must exist locally before this command is run.
See `docs/strategies/promoted_router.md`.

Trade-filter research inspects existing `trades.csv` artifacts and searches
entry-known `take`/`skip` rules under the default anti-overfit split:
train `2022-01-01` → `2024-01-01`, validation `2024-01-01` → `2025-01-01`,
stress `2025-01-01` → latest available trade.

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester trade-filter-research \
    --trades results/router_exact_shortlist_2022_2026/router_v2_3997501/20260625_162258 \
    --output results/trade_filter_research/router_v2_3997501 \
    --capital 10000
```

The command writes `baseline_by_split.csv`, `filter_candidates.csv`,
`top_filters.csv`, and `report.md`. It is a research screen only: promising
filters must still be implemented inside the strategy/router and re-run
through the normal backtester. Portfolio-state fields such as `size`,
capital, margin, and open-position counts are excluded by default; pass
`--include-portfolio-state-features` only for separate risk-allocator research.

To search separate filters per strategy inside a router or composite artifact:

```bash
uv run backtester trade-filter-research \
    --trades results/router_exact_shortlist_2022_2026/router_v2_3997501/20260625_162258 \
    --group-by selected_strategy \
    --output results/trade_filter_research_by_strategy/router_v2_3997501 \
    --capital 10000
```

To add discovery/catalog-style closed-candle features at entry time, also pass
the completed run OHLCV file:

```bash
uv run backtester trade-filter-research \
    --trades results/router_exact_shortlist_2022_2026/router_v2_3997501/20260625_162258 \
    --ohlcv results/router_exact_shortlist_2022_2026/router_v2_3997501/20260625_162258/ohlcv.csv \
    --include-catalog-features \
    --group-by selected_strategy \
    --output results/trade_filter_research_by_strategy_catalog/router_v2_3997501 \
    --capital 10000
```

Exact-test the filtered donor portfolio with shared capital and multi-signal
same-candle entries:

```bash
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2022-12-18 \
    --to 2026-06-10 \
    --strategy strategies/archive/filtered_donor_portfolio_causal_v1.json \
    --capital 10000 \
    --output results/filtered_donor_portfolio_causal_v1_full
```

This strategy uses `signal_events` so several filtered donor signals can be
processed on the same OHLCV bar through the same shared capital/margin engine.

```bash
uv run backtester discover-strategies \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-04-01 \
    --output results/discovery_sol_h1 \
    --label-horizon-bars 24 \
    --label-atr-mult 1.0 \
    --beam-width 20 \
    --max-filter-depth 4 \
    --min-trades-total 50 \
    --min-trades-per-window 10
```

Artifacts land in `results/discovery_sol_h1/<timestamp>/`. Inspect
`top_win_rate_min_50.csv`, `top_win_rate_min_100.csv`, and
`robust_min_window_win_rate_50.csv` first, then use `candidate_windows.csv` to
check per-window wins/losses before opening the matching
`best_candidates/<shortlist>/rank_001_report.md` and events CSV.

Bounded H1 setup tuning can use the donor optimizer directly:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester optimize \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_sol_h1_optuna \
    --trials 25 \
    --rrr-low 1.0 --rrr-high 2.0 --rrr-step 0.25 \
    --ttl-low 18 --ttl-high 42 --ttl-step 6 \
    --trail-distance-atr-low 0.0 --trail-distance-atr-high 2.0 --trail-distance-atr-step 0.5 \
    --risk-percent 1.0 \
    --no-strategy-param-search \
    --no-daily-limit-search \
    --no-trading-window-search \
    --export-best-run
```

Optimizer tuning always uses `mandate_score`: capped monthly return after
strong penalties for months below the 15% floor, monthly DD breaches, and
consecutive losing months. Scalar targets such as `total_return_pct` are not
available through the optimizer CLI. The optimizer writes `trials.csv`,
`best_trial.json`, the Optuna journal log, and donor `best_run/` diagnostics
under a timestamped output directory. `max_positions` is fixed to `0` across
backtest/diagnostic CLIs.

Use `--trail-distance-atr-low/high/step` for trailing-stop search. In Optuna
mode, trailing activation is not a separate parameter: if `trail_distance_atr`
is positive, the trailing stop activates at the selected `rrr`; if
`trail_distance_atr` is `0`, trailing is disabled.

For mandate candidate checks across calendar months, use `compare-fixed`
(**continuous by default**, ADR-0032): one backtest per symbol spans all
`--window` entries; monthly mandate rows are derived from that run so open
positions are not reset at month boundaries. With no `--window` options it
compares SOL January/February/March 2025 and TON January/February 2025 using
the fixed execution candidate (`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`)
and writes `windows.csv`, `windows.md`, `monthly_mandate.csv`,
`mandate_summary.csv`, `mandate_summary.md`, and run artifacts under
`runs/<symbol>_continuous/`. Use `--isolated-windows` only for diagnostics
(legacy per-month capital reset). Use `--jobs N` only in isolated mode.

**TP-first exit geometry** (`--exit-geometry tp_pct --tp-move-pct 0.015`):
fixed gross TP move from entry; SL = TP distance / `rrr`, structural SL used
as cap. With `tp_pct`, `crypt_ensemble` skips the structural SL **entry gate**
(ADR-0028); discovery-mapped filters still apply. Optuna search:

```bash
--exit-geometry tp_pct \
--tp-move-pct-low 0.008 --tp-move-pct-high 0.020 --tp-move-pct-step 0.002 \
--rrr-low 1.25 --rrr-high 2.25 --rrr-step 0.25 \
--ttl-low 12 --ttl-high 48 --ttl-step 12 \
--risk-percent-low 1.0 --risk-percent-high 2.0 --risk-percent-step 0.25
```

See `docs/backtester/exit_geometry.md`.

```bash
uv run backtester compare-fixed \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_fixed \
    --rrr 1.25 \
    --ttl 36 \
    --risk-percent 1.0 \
    --jobs 3
```

For a tiny execution-only `rrr` / `ttl` / `max_positions` grid around a
problematic window, use `compare-grid`. It writes `grid.csv`, `grid.md`, and
per-candidate donor artifacts under
`runs/<label>/rrr_<value>__ttl_<bars>__maxpos_<value>/`. For each
symbol/window, `compare-grid` now builds the `crypt_ensemble` signal frame
once and reuses it across execution candidates, so execution-parameter checks
do not pay repeated signal-generation cost for the same fixed strategy config.
`--jobs N` parallelizes independent windows; candidates inside one window are
run serially so they can share the precomputed signal frame.
If one or more windows fail to load or execute, completed windows still write
`grid.csv` / `grid.md`, and failed windows are listed in `grid_errors.csv` /
`grid_errors.md`.

```bash
uv run backtester compare-grid \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_grid_sol_mar \
    --window sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01 \
    --rrr-values 1.0,1.25,1.5 \
    --ttl-values 30,36,42 \
    --risk-percent 1.0 \
    --jobs 3
```

Before running more execution grids, use `signal-quality` to attribute H1
PnL and trade counts by side, setup month, confidence bucket, anchor type,
anchor freshness, context/setup alignment, trigger type, stale-anchor marker,
and reversal marker. It also writes setup/trigger attribution for tradeable and
rejected setup rows by setup snapshot time, trigger type, context bias, anchor
type, stop-distance bucket, and realized outcome. With no `--window` options
it checks SOL Jan/Feb/Mar 2025 and TON Jan/Feb/Mar/Apr 2025. It writes
`signals.csv`, `signals.md`, `groups.csv`, `groups.md`,
`setup_attribution.csv`, `setup_attribution.md`, per-window donor artifacts
under `runs/<label>/`, and `errors.csv` / `errors.md` when some windows fail.

```bash
uv run backtester signal-quality \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_signal_quality \
    --rrr 1.25 \
    --ttl 36 \
    --risk-percent 1.0 \
    --jobs 3
```

For a bounded diagnostic of the first H1 setup/anchor filters, run the same
report with `strategies/backtester/crypt_ensemble_h1_filtered.json`. That
config keeps the same H1 geometry but enables `allowed_sides = ["short"]`,
blocks liquidity-sweep stop anchors, rejects anchors older than 72 hours, and
blocks explicit context reversals. It is a diagnostic profile, not accepted
calibration.

Use `--from` / `--to` for bounded donor `crypt-parquet` smokes before running
full-history H1 MTF. The bounds limit the primary/output timeframe while
preserving earlier candle history for H4/D1 warmup up to `--to`. Expected
current result: data loads, `crypt_ensemble` shows per-bar progress, and donor
execution writes `trades.csv`, `trade_diagnostics.csv`, `metrics.csv`,
`signals.csv`, `signal_events.csv` (for portfolio event inputs), and
`signal_diagnostics.csv` when the run completes.
`equity_curve.csv` is written only when trades exist.

## Developer setup

```bash
uv sync --all-extras
uv tool install pre-commit
pre-commit install
```

`uv` and `pyproject.toml` are the source of truth for dependencies, scripts,
and Python tool configuration. `mise` is optional: it pins local tool versions
and provides short wrappers around the same `uv` commands.

```bash
# Optional convenience layer:
mise run sync
mise run test
mise run test-backtester
mise run backtester-help
```

Pre-commit runs `ruff` (with auto-fix) and `mypy --strict` on every commit.
CI runs the same checks plus `pytest` and `uv lock --check` on every push.

## Deploying Live Execution to Railway

Follow the step-by-step checklist in `docs/deploy/railway.md`.

Short version:
1. Connect the GitHub repo to Railway → branch `main`.
2. Add environment variables (see checklist for full list).
3. Attach a persistent volume at `/app/data`.
4. Keep `railway.toml` start command as `sh scripts/railway_live_start.sh`.
5. Confirm preflight completes, then `Starting crypt [execution-only]` appears.

The Railway entrypoint always runs `crypt.runtime.deploy_preflight` before the
live process. It removes zero-byte parquet files, checks H1/H4/D1 live OHLCV
coverage, and runs OKX backfill when data is missing, stale, or gapped. A fresh
volume can therefore spend a long time backfilling before any order logic starts.
The entrypoint defaults to the archived post-ADR-0058 live strategy unless
`EXECUTION_STRATEGY_CONFIG` is explicitly overridden. Preflight and backfill use
the same `LOG_LEVEL` and stdout/stderr routing as the live process: INFO and
progress output go to stdout, while only WARNING/ERROR go to stderr.

## Live Execution

Live execution is off by default. Start with dry-run only:

```bash
PYTHONPATH=src \
MPLCONFIGDIR=/tmp/matplotlib \
EXECUTION_ENABLED=true \
EXECUTION_DRY_RUN=true \
EXECUTION_DRY_RUN_CAPITAL=10000 \
EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
EXECUTION_SYMBOLS=SOL-USDT-SWAP \
uv run python -m crypt --once --execution-only
```

The live runner loads the strategy through the same backtester registry as
`backtester run`, processes portfolio `signal_events` in order, and blocks new
entries unless OKX balance/positions/orders are synced with
`data/live_positions.json`. OKX must be in long/short position mode; net/one-way
mode is blocked because the portfolio can hold independent long and short entries.
Entry/close lifecycle is persisted before exchange writes. After restart the
runner adopts actual fills and protection by deterministic client ID; partial
reduce-only closes retain `closing` state and retry only the remaining
contracts.
Use `--execution-only` for trading dry-runs and trading service processes; it
skips the legacy H4 alert monitor that prints `HOLD/conf/regime` verdicts and
uses `EXECUTION_SYMBOLS` for startup health checks.
When Telegram is configured, live execution sends one full sync report per UTC
day, an `ENTRY ATTEMPT` followed by `ENTRY` or `ENTRY REJECTED` / `EXECUTION
ERROR` for every actionable donor event, and one message for every recorded
exit. New exchange-sync blockers and execution-cycle failures are reported
immediately. A sync blocker is reported again on every H1 execution cycle while
it remains active. Attempts and rejections, including the complete rejection
reason, are also written to the console and `logs/crypt.log`.

The normal H1 trigger connects to the OKX business WebSocket at `HH:59:30 UTC`
and starts processing as soon as OKX confirms the closing H1 candle and
publishes the new hour's open. H4 and UTC-day confirmations are also required
at their boundaries. The former `*:02 UTC` REST cycle remains only as a
duplicate-guarded fallback if WebSocket confirmation fails.
The filtered donor portfolio live runner then uses a validated donor-frame cache: exact
full-history features are retained, while only the latest donor tail is
replayed and checked against cached overlap. Current measured hourly signal
latency is about 6.8 seconds instead of 31.8 seconds; any mismatch forces a
complete rebuild.
Keep
`EXECUTION_MAX_POSITIONS=0` for the current portfolio. On startup, live execution refuses to
run if the money-impacting `EXECUTION_*` defaults diverge from the strategy
JSON `backtest_args`, including maker/taker fees and
`EXECUTION_INSTRUMENT_PRECISION_POLICY`. `EXECUTION_DRY_RUN_CAPITAL` lets a dry-run size entries
as if the account had `$10k` while still syncing the real OKX account; it is
ignored for live money. Switch `EXECUTION_DRY_RUN=false` only after real H1
dry-run logs show clean sync and sane SL/TP/size output.

The live executor selects liquidation-safe leverage with a buffer beyond every
structural stop. For SOL live execution, `maintenance_margin_tier_schedule`
tracks OKX isolated SWAP position tiers so larger aggregate same-side positions
use the higher MMR and lower maximum leverage tier. Trailing donors use native
OKX `move_order_stop` orders; the backtester uses the same fixed entry-time
activation price and callback spread. The conservative H1 model does not let a
newly tightened trailing stop consume the earlier adverse extreme of the same
candle, applies adverse opening gaps, and treats a nearer structural stop as
crossed before a deeper last-price liquidation.
Same-side logical entries share one OKX aggregate average entry for realized
PnL, margin, and liquidation. Adding exposure updates that average; partial
closes preserve it. Trade exports retain both the logical `entry_price` and
`aggregate_entry_price` used for cash accounting. `pnl_abs` remains account PnL
from the aggregate entry; `constituent_pnl_abs` and `constituent_pnl_rel` are
diagnostic donor-level PnL from the logical entry's own price.
Missing protection or an unsafe exchange liquidation level blocks new entries
and is reported to Telegram every H1 cycle. If closing one same-side
constituent removes the required liquidation buffer from a remaining logical
position, live fail-safe closes it reduce-only on synchronization; the
backtester mirrors that action at the next H1 open.

## Running as a service (local VPS / Linux)

The `deploy/crypt.service` systemd unit runs the process under your user account
with automatic restart on crash.

```bash
# Install (adjust User/WorkingDirectory paths inside the file first if needed)
sudo cp deploy/crypt.service /etc/systemd/system/crypt.service
sudo systemctl daemon-reload
sudo systemctl enable --now crypt

# Check status / live logs
systemctl status crypt
journalctl -u crypt -f
```

The unit sets `Restart=always` with a 10-second cool-down, so a Python crash or
OOM kill will automatically restart the process within 10 seconds.

## Layout

```
crypt/
├── AGENTS.md                # agent operating manual
├── CHANGELOG.md             # session-by-session log
├── README.md                # this file
├── .cursor/rules/           # always-on rules for AI agents
├── docs/
│   ├── architecture.md      # high-level design
│   ├── backfill.md          # backfill CLI contract (OKX OHLCV + optional Rubik data)
│   ├── backtest.md          # retired root-native harness note
│   ├── backtester_migration.md
│   ├── decisions/           # ADRs (one decision per file)
│   ├── engines/             # per-engine specs (signal contracts, logic, thresholds)
│   └── tasks/               # ROADMAP / BACKLOG / IN_PROGRESS / DONE
├── mise.toml                # optional tool versions and common tasks
├── src/backtester/          # canonical M2 donor backtester package
├── src/crypt/               # live ensemble
├── strategies/backtester/   # donor strategy JSON configs
└── tests/                   # pytest suites for crypt and backtester
```

Backtester tests now run from the repository root:

```bash
uv run pytest tests/backtester -q
```

## License

Private. No license granted.
