# crypt

Modular ensemble decision system for crypto perpetual futures markets.

> Continuously monitors a small basket of OKX perpetual contracts, runs several
> independent "trader views" (trend, mean-reversion, derivatives positioning,
> volatility regime, ...), aggregates them into a single weighted verdict
> (`BUY` / `SELL` / `HOLD` + confidence + rationale) and pushes alerts to
> Telegram.
>
> Goal of v1: signal generation for the owner to trade manually.
> Goal of vN: automated execution once the signal track-record is proven.

This is **not** a trading bot. It is a research-and-alerting system.

## Status

**M1 complete.**
All signal-only MVP components are implemented and the live manual-alerting
surface has already been completed. Engines, aggregator, decision layer, sinks,
runtime, retry/backoff, heartbeat, log rotation, service config, and Railway
deployment docs are in place.

Current active work is **M2 donor backtester migration and calibration**.
`backtester/` is now vendored as ordinary source in this monorepo per ADR-0021.
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

No database, no Redis, no Docker in MVP.

## How it is developed

This repository is built **AI-first**. The owner sets global goals in chat;
agents own implementation planning, scaffolding and documentation.

Anyone (human or agent) contributing should first read:

1. `AGENTS.md`
2. `.cursor/rules/ai-first-workflow.mdc`
3. `docs/tasks/IN_PROGRESS.md`
4. `docs/tasks/ROADMAP.md`
5. The most recent entries in `CHANGELOG.md`

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

## Historical backfill (M2 backtest)

Primary M2 calibration is OHLCV-only (ADR-0017): no paid derivatives,
liquidations, or sentiment data until the candle-only system demonstrates
value. See `docs/backfill.md` and `docs/backtest.md`.

```bash
# M2 primary backfill (OHLCV-only per ADR-0017)
PYTHONPATH=src uv run python -m crypt.backfill \
    --symbol SOL-USDT-SWAP \
    --from 2024-02-01 --to 2026-06-01 \
    --data-types ohlcv

# Then run backtest — see docs/backtest.md
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

Data lands in `data/<SYMBOL>/` (Parquet). Re-running is idempotent.

## Donor backtester migration (experimental)

ADR-0018 moves future M2 work toward the donor `backtester/` package.
ADR-0021 tracks `backtester/` in this monorepo (same git history as
`src/crypt/`; not a nested repository). The donor package is treated as a
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
Donor execution exports `signal_time`, `risk_base_capital`, confidence, score,
regime, rationale, stop diagnostics, and per-engine strengths into `trades.csv`
for audit. It also writes `trade_diagnostics.csv`, a compact report for exit
reason, side, PnL, and structural stop distance analysis. Per ADR-0019,
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
cd backtester

PYTHONPATH=src:../src uv run --extra dev backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

Experimental H1 MTF mode keeps D1/H4 as context/setup but uses H1 as the
primary execution frame. The current diagnostic H1 config uses
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

```bash
PYTHONPATH=src:../src uv run --extra dev backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_sol_h1
```

Bounded H1 setup tuning can use the donor optimizer directly:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
PYTHONPATH=src:../src UV_CACHE_DIR=/tmp/uv-cache \
uv run --extra dev backtester optimize \
    --data-source crypt-parquet \
    --data-dir ../data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_sol_h1_optuna \
    --trials 25 \
    --target total_return_pct \
    --rrr-low 1.0 --rrr-high 2.0 --rrr-step 0.25 \
    --ttl-low 18 --ttl-high 42 --ttl-step 6 \
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
`windows.md`, and per-window donor run artifacts under `runs/<label>/`.
Use `--jobs N` to run independent windows in parallel; this does not parallelize
Optuna strategy-parameter search.

```bash
PYTHONPATH=src:../src uv run --extra dev backtester compare-fixed \
    --data-dir ../data \
    --primary-timeframe 1h \
    --strategy strategies/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_fixed \
    --rrr 1.25 \
    --ttl 36 \
    --risk-percent 1.0 \
    --jobs 3
```

For a tiny execution-only `rrr` / `ttl` grid around a problematic window, use
`compare-grid`. It writes `grid.csv`, `grid.md`, and per-candidate donor
artifacts under `runs/<label>/rrr_<value>__ttl_<bars>/`. For each
symbol/window, `compare-grid` now builds the `crypt_ensemble` signal frame
once and reuses it across execution candidates, so `rrr` / `ttl` checks do not
pay repeated signal-generation cost for the same fixed strategy config.
`--jobs N` parallelizes independent windows; candidates inside one window are
run serially so they can share the precomputed signal frame.

```bash
PYTHONPATH=src:../src uv run --extra dev backtester compare-grid \
    --data-dir ../data \
    --primary-timeframe 1h \
    --strategy strategies/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_h1_grid_sol_mar \
    --window sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01 \
    --rrr-values 1.0,1.25,1.5 \
    --ttl-values 30,36,42 \
    --risk-percent 1.0 \
    --jobs 3
```

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
├── backtester/              # donor M2 package (ADR-0018, ADR-0021; own pyproject.toml)
├── .cursor/rules/           # always-on rules for AI agents
├── docs/
│   ├── architecture.md      # high-level design
│   ├── backfill.md          # backfill CLI contract (OKX OHLCV + optional Rubik data)
│   ├── backtest.md          # M2 backtest harness contract
│   ├── backtester_migration.md
│   ├── decisions/           # ADRs (one decision per file)
│   ├── engines/             # per-engine specs (signal contracts, logic, thresholds)
│   └── tasks/               # ROADMAP / BACKLOG / IN_PROGRESS / DONE
├── src/crypt/               # live ensemble + legacy backtest harness
└── tests/                   # pytest (crypt package)
```

Donor tests run from `backtester/` (`uv run pytest` with
`PYTHONPATH=src:../src`); they are not yet part of root CI.

## License

Private. No license granted.
