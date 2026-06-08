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

Current active work is **M2 donor backtester migration and calibration**.
`backtester` is now a root-integrated package under `src/backtester` per
ADR-0023.
The donor `crypt_ensemble` strategy can replay the existing ensemble over
project Parquet data and the first multi-timeframe H1 execution slice exists,
but full H1 smoke acceptance remains open behind H1 setup-geometry retuning
and a performance pass.

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
    --target total_return_pct \
    --rrr-low 1.0 --rrr-high 2.0 --rrr-step 0.25 \
    --ttl-low 18 --ttl-high 42 --ttl-step 6 \
    --trail-activation-rrr-values 0,0.5,0.75,1.0,1.25 \
    --trail-distance-atr-low 0.5 --trail-distance-atr-high 2.0 --trail-distance-atr-step 0.5 \
    --max-positions-values 1,2,3,5 \
    --risk-percent 1.0 \
    --no-strategy-param-search \
    --no-daily-limit-search \
    --no-trading-window-search \
    --export-best-run
```

The optimizer writes `trials.csv`, `best_trial.json`, the Optuna journal log,
and donor `best_run/` diagnostics under a timestamped output directory.

For cheaper fixed-candidate checks across several bounded windows, use
`compare-fixed`. With no `--window` options it compares SOL January/February/
March 2025 and TON January/February 2025 using the fixed execution candidate
(`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`) and writes `windows.csv`,
`windows.md`, `monthly_mandate.csv`, `mandate_summary.csv`,
`mandate_summary.md`, and per-window donor run artifacts under `runs/<label>/`.
The mandate files apply ADR-0025 gates: raw/capped monthly returns, intra-month
max drawdown, stop-loss counts, and the promote/archive/discard/full-Optuna
verdict, evaluated per symbol because each symbol has its own mandate portfolio.
Use `--jobs N` to run independent windows in parallel; this does not parallelize
Optuna strategy-parameter search.

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
    --max-positions-values 1,2,3,5 \
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
`signals.csv`, and `signal_diagnostics.csv` when the run completes.
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

## Deploying to Railway (recommended for 14-day run)

Follow the step-by-step checklist in `docs/deploy/railway.md`.

Short version:
1. Connect GitHub repo to Railway → branch `master`.
2. Add environment variables (see checklist for full list).
3. Attach a persistent volume at `/app/data`; set `LOG_DIR=data/logs`.
4. Confirm build succeeds and Telegram alert arrives.

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
