# Product Research: crypt Architecture, Runtime, and Subsystem Ground Truth

- **Date**: 2026-09-03
- **Audience**: Engineering and authoring team for the Russian documentation portal targeting developer-crypto-traders.
- **Repository**: `/home/n-tretyakov/projects/crypt`
- **Current Operational Target**: Automated strategy discovery, exact historical backtesting, and live single-symbol perpetual execution on OKX.

---

## 1. Factual System Map

The `crypt` repository is a unified research workbench and production execution system for cryptocurrency perpetual futures strategies, implemented in Python 3.12+ and managed with `uv`.

```
                                  ┌──────────────────────────────────────────────┐
                                  │                  OKX APIs                    │
                                  │  REST (Public/Private) & WebSocket (Business)│
                                  └───────────────┬──────────────────────────────┘
                                                  │
                                                  │ OHLCV / Market Data / Orders
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Data Pipeline                                            │
│  - Storage: Parquet partitioned store under data/<SYMBOL>/ (closed candles only)               │
│  - Ingest / Backfill: python -m crypt.backfill (OHLCV, execution_1m, last/mark, OI, ratios)   │
│  - Preflight: python -m crypt.runtime.deploy_preflight (integrity check, zero-byte cleanup)   │
└───────────────────────┬────────────────────────────────────────────────┬───────────────────────┘
                        │                                                │
                        ▼ Historical Parquet Loading                     ▼ Live Append & Context
┌──────────────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
│               Research Workbench                 │   │             Live Execution              │
│                 (src/backtester/)                │   │           (src/crypt/execution/)        │
│                                                  │   │                                         │
│  1. Signal Discovery: DSS v3                     │   │  1. Ingestion Clock:                    │
│     - CLI: backtester search-signals[-matrix]    │   │     - Primary: H1 WebSocket            │
│     - Timeframes: 15m, 1h, 4h, 1d (MTF)         │   │       (wss://ws.okx.com:8443)           │
│     - Engines: CatCMA-QD, Hyperband-QD,          │   │     - Fallback: REST polling at *:02 UTC│
│       SMAC-QD, Island-QD, Directional            │   │  2. Live Signal Runner:                 │
│     - Evaluation: Directional barrier labeling   │   │     - FilteredDonorPortfolio (Core v4)  │
│                                                  │   │     - Fast append cached latest bar     │
│  2. Geometry Optimization: Optuna                │   │  3. Sizing & Risk Continuity:           │
│     - CLI: backtester optimize                   │   │     - Monthly risk-base checkpoint pair │
│     - Searches: RRR, TTL, risk %, trail ATR, TP  │   │       (data/risk_base_checkpoints/)     │
│                                                  │   │     - Shared BasicRiskModel sizing      │
│  3. Historical Simulation: ExecutionSim          │   │  4. Order & Protection Management:      │
│     - CLI: backtester run                        │   │     - Side-specific isolated margin     │
│     - Parity: Exact margin, fees, precision,     │   │     - Market entry + attachAlgoOrds SL  │
│       aggregate avg entry, native trailing       │   │     - Native OKX move_order_stop trail  │
│                                                  │   │  5. Exchange Sync & Recovery:           │
│                                                  │   │     - Full snapshot reconciliation      │
│                                                  │   │     - State in data/live_positions.json │
└──────────────────────────────────────────────────┘   └────────────────────┬────────────────────┘
                                                                            │ Notifications & Alerts
                                                                            ▼
                                                       ┌─────────────────────────────────────────┐
                                                       │        Operator Telegram Layer          │
                                                       │  - Russian localized event alerts       │
                                                       │  - Daily sync health report             │
                                                       │  - Blocked / missed signal auditing     │
                                                       └─────────────────────────────────────────┘
```

The system is split into two primary functional domains:
1. **Research Workbench (`src/backtester/`)**: An integrated donor package providing multi-timeframe directional signal discovery (Direct Signal Search v3), parameter/geometry optimization (Optuna), and an event-driven backtesting simulator (`ExecutionSim`) implementing realistic margin, fees, liquidations, and trade geometry.
2. **Production Runtime (`src/crypt/`)**: A continuous execution service deployed on Railway or run locally via `python -m crypt --execution-only`, executing owner-selected strategies on OKX perpetual swap instruments (active production: `SOL-USDT-SWAP`).

---

## 2. Subsystem Breakdown

### 2.1 Overview
- **Core Identity**: A specialized quantitative research and execution engine for automated crypto perpetual strategies.
- **Historical Heritage**: Began as a signal-only Telegram alert system based on an H4 ensemble (trend, mean reversion, derivatives, volatility, regime). That MVP is complete and is now retained solely as historical context (`AGENTS.md`, lines 7–8; `README.md`, lines 24–25).
- **Core Principle**: Strict parity between backtest simulation and live money execution. Sizing, stop loss (SL), take profit (TP), time-to-live (TTL), margin calculations, and trailing geometry share identical mathematical implementations (`docs/execution/live_execution.md`, lines 22–38).
- **Technology Stack**:
  - Python >= 3.12 (`pyproject.toml`, line 6).
  - Package Manager: `uv` (`README.md`, line 34).
  - Exchange Connectivity: `ccxt` (v4.4+) and direct OKX REST/WebSocket clients (`pyproject.toml`, line 15; `src/crypt/runtime/h1_websocket.py`, lines 10–15).
  - Data Processing: `pandas` (v2.2+), `pyarrow` (v17+), `pydantic` (v2.7+), `pydantic-settings` (`pyproject.toml`, lines 16–20).
  - Numerical & Optimization: `numpy`, `scipy`, `scikit-learn`, `optuna` (v4.0+), `cmaes` (`pyproject.toml`, lines 17, 29, 31, 34).
  - Scheduling & Async: `APScheduler`, `aiogram` (v3.10+), `aiohttp`, `httpx` (`pyproject.toml`, lines 14, 21, 22, 24).
  - Observability & Testing: `loguru`, `pytest`, `ruff`, `mypy` (`pyproject.toml`, lines 23, 42–47).

### 2.2 Architecture
- **Package Separation**:
  - `src/crypt/`: Houses live execution orchestration, data ingestion, store, runtime scheduling, preflight, exchange integration, and sinks (`docs/architecture.md`, lines 74–122).
  - `src/backtester/`: Houses the simulation engine, feature extractors, strategy discovery (DSS v3), fee models, margin models, and strategy registry (`src/backtester/registry.py`, lines 1–43; `docs/backtest.md`, lines 5–10).
- **Retired Components**:
  - The legacy `src/crypt/backtest/` harness was permanently retired on 2026-06-04 by ADR-0023 (`docs/backtest.md`, lines 3–15). All backtesting logic resides in `src/backtester/`.
- **Pure Decision Separation**: Strategies generate signals from closed candles only. Sizing and execution simulation are decoupled from signal generation, allowing identical strategy logic to feed either simulated fills (`ExecutionSim`) or live OKX order placement (`LiveExecutionManager`).
- **Data Boundaries**: Immutable dataclasses and typed dataframes enforce contracts between the data store, signal runners, and risk engines (`src/crypt/models.py`, lines 128–168; `src/backtester/data_contracts.py`).

### 2.3 Backtester
- **Simulation Engine (`ExecutionSim`)**:
  - Located in `src/backtester/execution_sim.py`.
  - Replays historical candles chronologically. For DSS v3 candidates, candle timeframe is automatically derived from the strategy trigger timeframe (`docs/cli.md`, lines 70–73).
  - Supports both standard candle execution (e.g. H1) and minute execution models (`minute_last` and `minute_mark` per ADR-0056) for exact intrabar stop and liquidation evaluation (`tests/backtester/test_minute_execution.py`).
- **Capital & Sizing Model**:
  - Sizing is driven by `BasicRiskModel` (`src/backtester/risk_model.py`).
  - Implements a monthly risk-base period: sizing equity is fixed at the start of each calendar month, preventing compounding feedback loops and intra-month equity volatility from distorting position size (`docs/decisions/0019-monthly-risk-base-for-donor-m2.md`; `docs/decisions/0059-durable-monthly-risk-base-checkpoints.md`).
- **Margin & Leverage (`margin_policy.py`)**:
  - Isolated margin is strictly enforced for all positions (`docs/decisions/0029-isolated-margin-always-on.md`).
  - Dynamic leverage selection calculates safe leverage below exchange liquidation risk based on maintenance margin tiers and liquidation buffers (`docs/decisions/0026-isolated-margin-leverage-selection.md`; `docs/decisions/0049-liquidation-safe-leverage-parity.md`).
- **Fee & Slippage Model (`fee_model.py`)**:
  - `StaticPercentFeeModel` applies maker (0.02%) and taker (0.05%) fees.
  - Entry fees are deducted immediately from available cash to match OKX accounting timing (`docs/decisions/0053-versioned-instrument-precision-and-entry-fee-timing.md`).
  - Limit TP orders are conservatively charged as taker fees in backtests because they may fill immediately on touch (`docs/execution/live_execution.md`, lines 266–268).
- **Trade Geometry & Exit Policies (`exit_geometry.py`, `trailing_policy.py`)**:
  - Supports multiple exit families: `sl_rrr`, `sl_rrr_trailing`, `tp_pct` (`docs/cli.md`, lines 79–83).
  - Native trailing stop parity: models OKX `move_order_stop` order mechanics with entry-known activation price and callback spread derived from closed-candle ATR14 (`docs/execution/native_okx_trailing.md`, lines 1–45).
  - Intrabar evaluation policy enforces worst-case extreme ordering unless explicitly configured otherwise (`docs/execution/native_okx_trailing.md`, lines 58–70).
- **Aggregate Average Entry Accounting**:
  - Implements ADR-0058: When multiple logical strategy constituents share a single position side on OKX, the exchange blends them into an aggregate average entry price (`avgPx`). The backtester tracks this aggregate price for portfolio equity and liquidation calculations while retaining individual constituent entry prices for performance attribution (`docs/decisions/0058-okx-aggregate-average-entry-accounting.md`).
- **Instrument Precision Policy**:
  - Strict contract size, amount step, and price tick quantization (`src/backtester/instrument_precision.py`). For `okx_sol_usdt_swap_2026_07_01`, contract size is 1 SOL, amount step is 0.01 contracts, min size is 0.01 contracts, tick size is 0.01 USDT (`docs/execution/live_execution.md`, lines 222–226).
- **Canonical Regression Suite**:
  - Documented in `docs/backtester_regression.md`.
  - Canonical Full Replay (2021-12-18 to 2026-06-29): exactly 1564 trades, 35.32% win rate, 1.43 profit factor, -4.14% drawdown below start, -33.26% peak-to-trough drawdown (`docs/backtester_regression.md`, lines 34–44).
  - Strict Live Checkpoint Phase C (2026-07-29T12:00Z to 2026-08-10T22:00Z): 20 trades, requires separate warmup (`--load-from 2026-07-13T00:00:00Z`) from accounting (`--from 2026-07-29T12:00:00Z`) (`docs/backtester_regression.md`, lines 86–118).

### 2.4 Strategies
- **Strategy Registry (`src/backtester/registry.py`)**:
  - Canonical mapping of strategy identifiers: `filtered_donor_portfolio`, `dss_strategy`, `promoted_router`, `crypt_ensemble`, `dual_ma`, `liq_hunter`, `som`, `forest`, `fvg_imbalance`, `fractal_rejection`, `rejection`, `fractal_rb`, `phase_routed`, `meta` (`src/backtester/registry.py`, lines 27–42).
- **Active Production Strategy**:
  - Config: `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json` (`docs/state/current.yml`, line 13; `docs/backtester_regression.md`, lines 10–12).
  - Architecture: Multi-signal donor portfolio combining vetted DSS candidates. Applies tail-control filters to prune underperforming or adverse-regime donors (`drop_negative_v5`).
  - Execution Sizing: Individual donor events carry their own risk percentage, RRR, TTL bars, and trailing parameters that override global defaults (`docs/execution/live_execution.md`, lines 183–188).
- **Direct Signal Search v3 (DSS v3)**:
  - Documented in `docs/discovery/direct_signal_search_v3.md` and ADR-0062.
  - Multi-Timeframe Search Engine: Allows triggers and filters to operate on distinct timeframes (`15m`, `1h`, `4h`, `1d`) (`docs/discovery/direct_signal_search_v3.md`, lines 38–56).
  - Directional Labeling Only: Search evaluation relies strictly on barrier labeling (reaching favorable barrier before adverse barrier on closed candles), without running full backtests or geometry optimization (`docs/discovery/direct_signal_search_v3.md`, lines 147–159).
  - Frequency Classes: Archives candidates across distinct frequency buckets: `sparse` (20–59/yr), `medium` (60–179/yr), `frequent` (180–520/yr), `overactive` (>520/yr) (`docs/discovery/direct_signal_search_v3.md`, lines 205–213).
  - Search Backends: `catcma_qd` (powered by `cmaes.CatCMAwM`), `hyperband_qd`, `smac_qd`, `island_qd`, and `directional` (`docs/discovery/direct_signal_search_v3.md`, lines 240–254).
  - Resumable Endless Mode: Runs indefinitely by default, persisting candidate journals, quality-diversity archive cells, and backend state (`docs/discovery/direct_signal_search_v3.md`, lines 297–335).
- **Optuna Parameter & Geometry Search**:
  - Implemented in `src/backtester/optimizer.py` and invoked via `backtester optimize`.
  - Searches exit families (`sl_rrr`, `sl_rrr_trailing`, `tp_pct`), RRR (1.0–10.0), TTL minutes (60–10080), risk % (0.25–3.0), trailing distance ATR (0.5–10.0), and TP move % (0.004–0.14) (`docs/cli.md`, lines 79–96).
  - Objective: Evaluates candidates against money-target criteria and drawdown constraints (`docs/decisions/0031-mandate-aware-optuna-target.md`).
- **Benchmark Target**:
  - Documented in `docs/strategy_benchmark.md`.
  - Floor Criteria: $10,000 capital, +15% raw monthly return floor, $1,500 monthly profit, max 20% positive monthly cap for ranking, maximum -10% monthly drawdown below start (`docs/strategy_benchmark.md`, lines 30–54).
  - Owner Override Principle: The benchmark is a research target, not an operational gate. The owner may promote any strategy to production, including benchmark-failing configurations (`AGENTS.md`, lines 30–33; `docs/strategy_benchmark.md`, lines 96–105).

### 2.5 Live Execution
- **Core Orchestrator**:
  - Implemented in `LiveExecutionManager` (`src/crypt/execution/executor.py`).
  - Controlled by settings in `src/crypt/execution/settings.py` (`ExecutionSettings`).
- **Dual Trigger System**:
  - Primary Clock: `H1WebSocketScheduler` (`src/crypt/runtime/h1_websocket.py`). Subscribes to OKX business WebSocket (`wss://ws.okx.com:8443/ws/v5/business`) at `HH:59:30 UTC` for `candle1H`, `candle4H`, `candle1Dutc`. Triggers execution upon receiving confirmed candles (`confirm=1`) and the new forming H1 candle open (`confirm=0`), which provides the canonical `next_open` price (`docs/execution/h1_websocket_trigger.md`, lines 10–33).
  - Fallback Clock: APScheduler cron trigger polling OKX REST at `*:02 UTC` if WebSocket delivery fails or times out (`docs/execution/h1_websocket_trigger.md`, lines 52–56).
- **Signal Generation & Cache Optimization**:
  - `LiveSignalRunner` (`src/crypt/execution/signal_runner.py`) loads the strategy JSON via the backtester registry and runs signal generation.
  - Core v4 uses the fast-append latest-bar cache (`generate_latest()` in `FilteredDonorPortfolioStrategy`), reducing hourly evaluation time on 39k bars from 31.8s to 6.8s (`docs/execution/live_signal_cache.md`, lines 1–45).
- **Order Placement (`OKXTradingClient`)**:
  - Located in `src/crypt/execution/okx_order_client.py`.
  - Sets isolated margin mode and side-specific leverage, strictly avoiding modifying the opposite side (`docs/execution/live_execution.md`, lines 207–215).
  - Places market entry orders with attached algorithmic orders (`attachAlgoOrds`) for market SL and optional limit TP (`docs/execution/live_execution.md`, lines 230–252).
  - Uses strictly OKX `last` price triggers to preserve parity with OHLCV backtest data (`docs/execution/live_execution.md`, lines 252–256).
  - For trailing-enabled events, submits an independent reduce-only `move_order_stop` algo order after entry fill confirmation, utilizing pre-planned ATR-derived geometry from the H1 open (`docs/execution/native_okx_trailing.md`, lines 24–45).
- **Durable Order Lifecycle**:
  - Progresses through explicit persisted stages: `entry_intent -> entry_submitted -> entry_filled -> protected` and `open -> closing -> closed` (`docs/execution/live_execution.md`, lines 277–294).
  - State file: `data/live_positions.json` with schema versioning, checksum validation, and atomic write replacement (`live_positions.previous.json`) (`docs/execution/live_execution.md`, lines 476–532).
- **Durable Monthly Risk-Base Continuity**:
  - Implemented in `src/crypt/execution/risk_base_continuity.py` per ADR-0059.
  - Sizing is anchored to an immutable, checksummed pair of checkpoint files: `<checkpoint_dir>/YYYY-MM.json` and `YYYY-MM.backup.json` (`docs/execution/live_execution.md`, lines 442–470).
  - Transitions occur only on the first actionable post-sync H1 batch of a new UTC month. Missing or conflicting checkpoints pause new entries while allowing existing positions to manage stops and closes (`docs/execution/live_execution.md`, lines 453–457).
- **Exchange Synchronization & Safety Circuit Breakers**:
  - `ExchangeSync` (`src/crypt/execution/exchange_sync.py`) verifies local state against full OKX account snapshots (balances, positions, regular orders, algo orders, position mode: long/short mode required) (`docs/execution/live_execution.md`, lines 315–345).
  - Any unexplained position or order mismatch halts new entries.
  - Blocked-Signal Audit: When exchange sync or risk-base continuity blocks entry, signals are still computed, logged with key `MISSED SIGNAL`, and notified via Telegram with persistent cumulative event counters (`docs/execution/live_execution.md`, lines 147–164).
  - Entry Fill Drift: Differences between expected H1 open and actual fill price are logged and notified as `Цена входа отличается от плана` under an alert-only policy (ADR-0054); drift does not abort filled orders (`docs/execution/live_execution.md`, lines 391–402).
  - Position TTL Expiry: Positions exceeding their TTL duration are closed via market order with `reduceOnly=True` after cancelling attached algo orders (`docs/execution/live_execution.md`, lines 415–437).

### 2.6 Data Pipeline
- **Parquet Storage Architecture**:
  - Stored under `data/<SYMBOL>/` without relational databases or external cache layers (ADR-0005).
  - Subdivided by timeframe (`15m`, `1h`, `4h`, `1d`) and partitioned dates for 1m execution candles (`tests/data/test_store_minute_partitions.py`).
  - Invariant: Only strictly closed candles (`closed=True`) are persisted to prevent look-ahead bias (`src/crypt/models.py`, lines 136–137; `tests/data/test_store_closed_invariant.py`).
- **Backfill CLI (`python -m crypt.backfill`)**:
  - Located in `src/crypt/backfill/__main__.py`.
  - Fetches historical data directly from OKX REST endpoints.
  - Supported data types: `ohlcv`, `execution_1m`, `last_1m`, `mark_1m`, `oi`, `ls_ratio`, `taker_vol` (`src/crypt/backfill/__main__.py`, lines 499–507).
  - Idempotent upsert logic handles deduplication (`src/crypt/data/store.py`).
  - Coinglass endpoints were permanently removed by ADR-0016; OKX native endpoints provide all required historical data (`docs/decisions/0016-drop-funding-fix-oi-endpoint.md`).
- **Deploy Preflight Check (`src/crypt/runtime/deploy_preflight.py`)**:
  - Executes before live trading launches (`scripts/railway_live_start.sh`, line 19).
  - Detects and purges 0-byte corrupt parquet files (`src/crypt/runtime/deploy_preflight.py`, lines 100–108).
  - Evaluates live coverage for H1, H4, and D1 candles against staleness thresholds (H1 max 3h, H4 max 12h, D1 max 3d).
  - Automatically launches targeted OKX backfills if required historical data is missing or gapped (`src/crypt/runtime/deploy_preflight.py`, lines 24–40, 140–180).

### 2.7 CLI
- **Owner-Facing Console Surface (`docs/cli.md`)**:
  1. `backtester run`:
     - Executes strategy replay over historical data (`docs/cli.md`, lines 46–65).
     - Defaults: data directory `data`, symbol `SOL-USDT-SWAP`, full available history, capital `$10,000`.
     - Supports `--strategy`, `--from`, `--to`, `--load-from` (warmup split), `--output`, `--capital`, `--risk-percent`, `--rrr`, `--ttl-minutes`.
  2. `backtester optimize`:
     - Executes post-DSS Optuna parameter and geometry optimization (`docs/cli.md`, lines 69–100).
     - Defaults: 50,000 trials, searches exit family, RRR, TTL minutes, risk %, trailing ATR, TP move %.
  3. `backtester search-signals`:
     - Runs DSS v3 signal discovery for a single backend (`docs/cli.md`, lines 115–123).
     - Runs in endless resumable mode when `--n-trials` is omitted (`docs/discovery/direct_signal_search_v3.md`, lines 297–303).
  4. `backtester search-signals-matrix`:
     - Runs DSS v3 matrix search across all algorithms (`catcma_qd`, `hyperband_qd`, `smac_qd`, `island_qd`, `directional`) (`docs/cli.md`, lines 105–114).
  5. `python -m crypt`:
     - Runtime execution and monitoring entrypoint (`src/crypt/__main__.py`, lines 25–54).
     - Flags: `--execution-only` (runs live execution path, bypassing legacy H4 monitor), `--once` (single evaluation tick), `--symbols`, `--no-bootstrap`.
  6. `python -m crypt.backfill`:
     - Explicit historical data fetcher (`docs/cli.md`, lines 126–134).
     - Flags: `--symbol`, `--from`, `--to`, `--data-types`, `--page-size`, `--max-rps`, `--data-dir`.
- **Environment Policy for CLI**:
  - Standard user commands need only `PYTHONPATH=src` to prevent Python 3.12 stdlib `crypt` collision (ADR-0013; `docs/cli.md`, lines 9–10).
  - Sandboxed execution must set `UV_CACHE_DIR=/tmp/uv-cache` and `MPLCONFIGDIR=/tmp/matplotlib-cache` (`AGENTS.md`, line 46; `docs/cli.md`, lines 14–17).

### 2.8 Configuration
- **Configuration Hierarchy**:
  1. Environment Variables & `.env` (`pydantic-settings`):
     - `Settings` (`src/crypt/config.py`, lines 15–74): Telegram tokens, OKX API credentials, log level, default symbols (`SOL-USDT-SWAP`, `TON-USDT-SWAP`, `XPL-USDT-SWAP`), alert confidence threshold, data/log paths.
     - `ExecutionSettings` (`src/crypt/execution/settings.py`, lines 16–125): Prefixed with `EXECUTION_`. Master switches (`EXECUTION_ENABLED`, `EXECUTION_DRY_RUN`, `EXECUTION_DRY_RUN_CAPITAL`), strategy path (`EXECUTION_STRATEGY_CONFIG`), risk-base checkpoint paths, circuit breakers, fallback money geometry.
  2. Strategy JSON (`strategies/`):
     - The loaded strategy configuration is the primary source of truth for runtime money parameters (`docs/state/current.yml`, line 10).
     - Startup Pre-trade Validation: Live execution validates `.env` fallback execution settings against the strategy JSON's `backtest_args`. Any discrepancy in fees, precision policy, or money parameters halts startup with an exception before any order can be submitted (`docs/execution/live_execution.md`, lines 190–196).
  3. Legacy YAML Configuration:
     - `config/weights.yaml`: Contains regime-conditional engine weights for the legacy H4 ensemble. Explicitly marked as uncalibrated placeholder weights (`src/crypt/config.py`, lines 53–55; ADR-0011; ADR-0020).

### 2.9 Operations
- **Railway Container Deployment**:
  - Documented in `docs/deploy/railway.md` and configured via `railway.toml`.
  - Process: Runs as a persistent (non-serverless) container via `scripts/railway_live_start.sh`.
  - Volume: Single persistent volume mounted at `/app/data` holding Parquet data, `live_positions.json`, `risk_base_checkpoints/`, and daily rotated logs `/app/data/logs/crypt.log` (`docs/deploy/railway.md`, lines 16–35).
  - Start Command: Executes `deploy_preflight` first, followed by `python -m crypt --execution-only` (`scripts/railway_live_start.sh`, lines 19–20).
- **Observability & Logging**:
  - Structured logging via Loguru to stdout and daily rotated log files (`docs/deploy/railway.md`, lines 194–198).
  - Background Heartbeat: Emits an info line every 30 minutes and triggers a full OKX connectivity and credentials health check every 6 hours (`src/crypt/__main__.py`, lines 65–87).
  - Disk Space Protection: Warns on startup if available disk space is under 1 GB (`docs/operations/observability.md`, line 24).
- **Telegram Notifications (`src/crypt/execution/notifications.py`)**:
  - Implements the presentation contract defined in `docs/execution/telegram_notifications.md`.
  - Language: Concise, localized Russian copy oriented towards non-technical operators while retaining technical trace IDs.
  - Active Message Types:
    - `Проверка бота`: Daily reconciliation report summarizing account balance, local vs exchange positions, and entry permission status.
    - `Найден сигнал`: Dispatched immediately when an actionable donor event is detected on a closed candle.
    - `Сделка открыта`: Confirms trade entry, side, actual fill price, SL/TP levels, contract count, margin, and monthly risk base.
    - `Вход пропущен`: Explains deterministic rejections (risk sizing, margin limits, group caps, minimum exposure).
    - `Цена входа отличается от плана`: Fill drift alert comparing H1 expected price vs actual fill without canceling the trade.
    - `Нужна проверка`: Warnings or execution exceptions (e.g. API connectivity, exchange sync failures).
    - `Сделка закрыта`: Reports trade exit, realized PnL, paid fees, and exit rationale (SL, TP, TTL expiry).
    - `Сигнал пропущен из-за защиты`: Alerts when safety guards (exchange sync or risk-base continuity) prevent an otherwise actionable entry (`MISSED SIGNAL`).
  - Resilience: Best-effort delivery with exponential backoff; failures never cancel trade orders or database writes (`docs/execution/telegram_notifications.md`, lines 30–33).
- **Continuous Integration (CI)**:
  - Workflow defined in `.github/workflows/ci.yml`.
  - Automated Checks: `ruff check` (excluding `tests/backtester`), `ruff format --check`, `mypy --strict src/crypt`, `pytest -q`, `uv lock --check`, and `gitleaks` secret scanning (`.github/workflows/ci.yml`, lines 28–55; `docs/operations/ci.md`, lines 34–50).

### 2.10 Glossary
- **Core v4 / v6 (`filtered_donor_portfolio`)**: The active production multi-signal portfolio strategy combining vetted donor strategy instances with tail-risk and negative-regime pruning (`docs/state/current.yml`, line 13; `docs/backtester_regression.md`, lines 10–12).
- **Direct Signal Search v3 (DSS v3)**: Automated strategy discovery framework searching multi-timeframe trigger and filter instances evaluated exclusively via directional barrier labeling (`docs/discovery/direct_signal_search_v3.md`).
- **Directional Labeling**: Research evaluation method determining whether closed-candle price action hits a fixed favorable price barrier before an adverse barrier within a forward window (`docs/discovery/direct_signal_search_v3.md`, lines 147–165).
- **Quality Diversity (QD)**: Evolutionary optimization paradigm (CatCMA-QD, Hyperband-QD, SMAC-QD, Island-QD) that maintains archives of high-performing strategies across diverse behavioral and frequency niches (`docs/discovery/direct_signal_search_v3.md`, lines 200–260).
- **ExecutionSim**: The root-integrated discrete-event backtesting simulator in `src/backtester/` executing candle-by-candle trade replay (`src/backtester/execution_sim.py`).
- **Monthly Risk Base**: Capital sizing reference anchored to the account equity at the beginning of each UTC month, ensuring sizing independence from intra-month equity swings (`docs/decisions/0019-monthly-risk-base-for-donor-m2.md`; ADR-0059).
- **Isolated Margin**: Exchange margin mode where collateral is strictly dedicated to an individual position, preventing cross-margin account liquidations (`docs/decisions/0029-isolated-margin-always-on.md`).
- **Native OKX Trailing (`move_order_stop`)**: An algorithmic order type executed natively on OKX infrastructure with activation price and callback spread fixed at entry (`docs/execution/native_okx_trailing.md`).
- **Instrument Precision Policy**: A versioned specification (e.g. `okx_sol_usdt_swap_2026_07_01`) defining exact exchange contract units, minimum lot sizes, amount steps, and price tick quantization (`src/backtester/instrument_precision.py`; ADR-0053).
- **Aggregate Average Entry (`avgPx`)**: The blended entry price assigned by OKX when multiple positions or fills exist on the same instrument side (`docs/decisions/0058-okx-aggregate-average-entry-accounting.md`).
- **Fill Drift**: The percentage variance between the expected H1 candle next-open price and the realized exchange market fill price (`docs/decisions/0054-entry-drift-is-observability-not-rejection.md`).
- **H1 WebSocket Trigger**: Real-time scheduling component subscribing to OKX public business channels at `HH:59:30 UTC` to trigger execution immediately on candle confirmation (`docs/execution/h1_websocket_trigger.md`).
- **Sinks**: Dispatcher classes (`TelegramSink`, `JsonLogSink`, `ConsoleSink`) that export trading verdicts and alerts (`src/crypt/sinks/`).
- **Regime**: Market categorization (e.g. `TRENDING`, `RANGING`, `HIGH_VOL`) utilized for weighting and routing (`src/crypt/models.py`, lines 142–146).

---

## 3. Real Runtime/User Paths and Topology

### 3.1 Operator Paths

```
                                  [Developer / Trader]
                                            │
           ┌────────────────────────────────┼────────────────────────────────┐
           │ Research Workflows             │ Optimization Workflows         │ Production Workflows
           ▼                                ▼                                ▼
  backtester search-signals-matrix  backtester optimize            Railway Live Container
           │                                │                      (scripts/railway_live_start.sh)
           ▼                                ▼                                │
  DSS v3 Candidate JSONs           Winning Money Geometry                    ▼
  (directional_candidates/)        (best_geometry_summary.txt)     deploy_preflight
           │                                │                                │
           └────────────────┬───────────────┘                                ▼
                            ▼                                      python -m crypt --execution-only
                   backtester run                                            │
                   (Full Replay / Regression)                                ▼
                            │                                      OKX Orders & Fills
                            ▼                                                │
                   Donor Portfolio Assembly                                  ▼
                   (strategies/archive/*.json)                     Telegram Notifications
```

1. **Strategy Discovery & Research**:
   - The operator launches endless multi-timeframe search:
     `PYTHONPATH=src uv run backtester search-signals-matrix --output-root results/dss_v3_sol_all_endless`
   - Evaluates multi-timeframe triggers and filters using directional labeling.
   - Outputs ranked candidate JSONs to `results/.../directional_candidates/`.
2. **Downstream Optimization**:
   - The operator takes a DSS candidate and optimizes money geometry:
     `PYTHONPATH=src uv run backtester optimize --strategy path/to/candidate.json --output results/optuna_candidate`
   - Resolves RRR, TTL minutes, risk %, trailing distance ATR, and TP move %.
3. **Historical Validation & Regression Verification**:
   - Replays candidates or assembled portfolios against full history:
     `PYTHONPATH=src uv run backtester run --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json --output results/v6_sol_full`
   - Validates results against canonical checkpoints in `docs/backtester_regression.md`.
4. **Live Execution Dry-Run Smoke**:
   - Tests live integration without risking capital:
     `PYTHONPATH=src EXECUTION_ENABLED=true EXECUTION_DRY_RUN=true EXECUTION_DRY_RUN_CAPITAL=10000 EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json EXECUTION_SYMBOLS=SOL-USDT-SWAP uv run python -m crypt --once --execution-only`
5. **Continuous Production Deployment**:
   - Runs persistently on Railway via `scripts/railway_live_start.sh`.
   - Executes preflight backfill check, attaches persistent volume at `/app/data`, and launches `python -u -m crypt --execution-only`.

### 3.2 Runtime Execution Loop Topology

```
[HH:59:30 UTC] H1 WebSocket connects to wss://ws.okx.com:8443/ws/v5/business
      │
      ▼
Receive candle1H confirm=1 (closed bar) and confirm=0 (new open)
      │
      ├──> [Fail / Timeout] ──> Fallback to REST polling at *:02 UTC
      │
      ▼
Signal Runner updates local Parquet store with confirmed candle
      │
      ▼
FilteredDonorPortfolioStrategy.generate_latest() (Fast-append cache)
      │
      ▼
Actionable Signal Batch emitted (e.g. donor events for SOL-USDT-SWAP)
      │
      ├──> Telegram: "Найден сигнал"
      │
      ▼
Exchange Snapshot Reconciled (Balance, Positions, Orders, Mode)
      │
      ├──> Mismatch Detected ──> Block Entries, Log MISSED SIGNAL, Alert Telegram
      │
      ▼
Durable Monthly Risk-Base Verified (<checkpoint_dir>/YYYY-MM.json)
      │
      ├──> Missing / Inconsistent ──> Block Entries, Alert Telegram
      │
      ▼
LiveRiskCalculator.calculate() (Shared BasicRiskModel sizing)
      │
      ├──> Sizing / Margin Guard Fails ──> Telegram: "Вход пропущен"
      │
      ▼
Durable State Written: status = "entry_intent" (live_positions.json)
      │
      ▼
OKX Client sets side-specific isolated leverage
      │
      ▼
OKX Client places market order with attachAlgoOrds (Last-price market SL, limit TP)
      │
      ▼
Order Fills Confirmed on OKX
      │
      ├──> Fill Drift Detected ──> Telegram: "Цена входа отличается от плана"
      │
      ▼
Trailing-enabled event?
      ├──> Yes: Place native move_order_stop algo order
      │
      ▼
Durable State Updated: status = "open", protected = true
      │
      ▼
Telegram: "Сделка открыта"
```

---

## 4. Active vs Historical, Deferred, and Absent Capabilities

| Capability Domain | Sub-feature | Status | Ground Truth Reference |
|---|---|---|---|
| **Strategy Discovery** | DSS v3 Multi-Timeframe Search | **Active** | `docs/discovery/direct_signal_search_v3.md`; `src/backtester/strategy_discovery/` |
| | Directional Barrier Labeling | **Active** | Evaluates favorable vs adverse barrier on closed candles |
| | Resumable Endless Search | **Active** | Default mode when `--n-trials` is omitted |
| | DSS v2 Full Backtest Search | **Retired** | Superseded by DSS v3; backtest pipeline removed from search (ADR-0062) |
| **Optimization** | Optuna Geometry Optimization | **Active** | `backtester optimize`; searches RRR, TTL, risk %, trail ATR, TP move |
| **Backtesting** | Integrated `ExecutionSim` | **Active** | `src/backtester/execution_sim.py`; parity with live sizing, margin, fees |
| | Monthly Risk Base | **Active** | Sizing capital anchored at monthly boundaries (ADR-0019, ADR-0059) |
| | Native OKX Trailing Parity | **Active** | Pre-submit activation and callback spread modeling (ADR-0050) |
| | Aggregate Avg Entry (`avgPx`) | **Active** | Implements OKX side blending for realized PnL and equity (ADR-0058) |
| | Minute Execution Evaluation | **Active** | `minute_last` and `minute_mark` data types supported (ADR-0056) |
| | Root `crypt.backtest` Package | **Retired** | Permanently retired on 2026-06-04 by ADR-0023 (`docs/backtest.md`) |
| **Live Execution** | Production Strategy | **Active** | `filtered_donor_portfolio` v6 on `SOL-USDT-SWAP` (`docs/state/current.yml`) |
| | H1 WebSocket Trigger | **Active** | Subscribes at `HH:59:30 UTC` with REST fallback at `*:02` (ADR-0051) |
| | Latest-Bar Signal Cache | **Active** | Fast append slice for Core v4 portfolio (ADR-0052) |
| | Isolated Margin Mode | **Active** | Side-specific isolated leverage strictly enforced (ADR-0026, ADR-0029) |
| | Last-Price Stop Triggers | **Active** | OKX market SL triggered by `last` price matching OHLCV data |
| | Durable State Persistence | **Active** | Atomic fsync replacement of `live_positions.json` with backup snapshot |
| | Monthly Risk Checkpoints | **Active** | Dual checksummed files (`YYYY-MM.json`, `YYYY-MM.backup.json`) (ADR-0059) |
| | Blocked-Signal Audit | **Active** | Logs `MISSED SIGNAL` and notifies cumulative count on safety block |
| | Fill Drift Alerting | **Active** | Alert-only notification; does not abort executed entries (ADR-0054) |
| | Multi-Symbol Live Execution | **Deferred** | Config accepts list, but production is strictly single-symbol `SOL-USDT-SWAP` |
| **Data Ingestion** | OKX REST Historical Backfill | **Active** | `python -m crypt.backfill` for OHLCV, 1m, OI, L/S ratio, taker volume |
| | Deploy Preflight Cleanup | **Active** | Detects zero-byte files, verifies coverage, triggers auto-backfill |
| | Coinglass Historical Data | **Retired** | Permanently dropped by ADR-0016; OKX native endpoints used |
| **Operations** | Railway Container Runbook | **Active** | `scripts/railway_live_start.sh` with persistent volume at `/app/data` |
| | Operator Telegram Alerts | **Active** | One-way Russian notifications for 8 distinct lifecycle events |
| | Interactive Telegram Commands | **Proposed / Absent** | `/status`, `/trade`, `/pnl` in `docs/operations/telegram_commands.md` are unbuilt |
| | Advanced Observability Metrics | **Proposed / Absent** | `tick_metrics.jsonl`, engine telemetry, error webhook in `docs/operations/observability.md` are unbuilt |
| | Paper Trading Ledger | **Proposed / Absent** | `PaperLedgerSink` in `docs/paper_trading.md` is unbuilt |
| | Continuous Integration | **Active** | `.github/workflows/ci.yml` runs ruff, mypy strict, pytest, gitleaks |
| **Historical MVP** | 5-Engine H4 Ensemble | **Historical** | Signal-only Telegram alert system; bypassed by `--execution-only` |
| **Non-Goals / Scope** | Web UI / Dashboard | **Absent** | Explicitly out of scope (`docs/architecture.md`, line 213) |
| | Database (Postgres, Redis) | **Absent** | Explicitly out of scope; Parquet only (ADR-0005; `docs/architecture.md`) |
| | OrderFlow / Tape Engine | **Absent** | Explicitly excluded by ADR-0008 |
| | Liquidation Analytics Engine | **Deferred** | Explicitly deferred by ADR-0006 and ADR-0012 |
| | Sentiment Analysis Engine | **Deferred** | Deferred to Backlog P2 (`docs/architecture.md`, line 210) |
| | ML Meta-Aggregator | **Deferred** | Deferred to Backlog P2 (`docs/architecture.md`, line 212) |

---

## 5. Source-of-Truth References

| Fact / Subsystem | Canonical File Path | Line Reference / Anchor |
|---|---|---|
| Project framing & rules | `AGENTS.md` | lines 1–96 |
| Repository overview & smoke runs | `README.md` | lines 1–123 |
| Compact state snapshot | `docs/state/current.yml` | lines 1–54 |
| Deterministic context routing | `docs/agent/context_routes.yml` | lines 1–180 |
| High-level system architecture | `docs/architecture.md` | lines 1–213 |
| Retired backtester harness | `docs/backtest.md` | lines 1–15 |
| Canonical CLI runbook | `docs/cli.md` | lines 1–137 |
| Canonical backtest regression runbook | `docs/backtester_regression.md` | lines 1–163 |
| Strategy benchmark targets & rules | `docs/strategy_benchmark.md` | lines 1–113 |
| Live execution specification | `docs/execution/live_execution.md` | lines 1–604 |
| Railway deployment runbook | `docs/deploy/railway.md` | lines 1–225 |
| Strategy config conventions | `strategies/README.md` | lines 1–15 |
| Direct Signal Search v3 specification | `docs/discovery/direct_signal_search_v3.md` | lines 1–385 |
| H1 WebSocket trigger specification | `docs/execution/h1_websocket_trigger.md` | lines 1–72 |
| Native OKX trailing-stop parity | `docs/execution/native_okx_trailing.md` | lines 1–84 |
| Live latest-bar signal cache | `docs/execution/live_signal_cache.md` | lines 1–61 |
| Operator Telegram notifications | `docs/execution/telegram_notifications.md` | lines 1–75 |
| Proposed observability specifications | `docs/operations/observability.md` | lines 1–192 |
| Proposed Telegram bot commands | `docs/operations/telegram_commands.md` | lines 1–204 |
| CI specifications & local commands | `docs/operations/ci.md` | lines 1–240 |
| Active CI workflow definition | `.github/workflows/ci.yml` | lines 1–55 |
| Dependencies & tooling settings | `pyproject.toml` | lines 1–115 |
| Environment configuration model | `src/crypt/config.py` | lines 1–96 |
| Live execution settings model | `src/crypt/execution/settings.py` | lines 1–180 |
| Strategy registry single source of truth | `src/backtester/registry.py` | lines 1–43 |
| Backtester CLI entrypoint | `src/backtester/__main__.py` | lines 140–1500 |
| Runtime service entrypoint | `src/crypt/__main__.py` | lines 1–180 |
| Historical backfill CLI | `src/crypt/backfill/__main__.py` | lines 1–525 |
| Deploy preflight script | `src/crypt/runtime/deploy_preflight.py` | lines 1–200 |
| Railway container startup script | `scripts/railway_live_start.sh` | lines 1–21 |

---

## 6. Contradictions and Unresolved Questions

### 6.1 Documentation vs Code Contradictions
1. **Module Map in `docs/architecture.md` vs Reality**:
   - `docs/architecture.md` (lines 83, 115–118) still lists `src/crypt/backtest/` (`replay.py`, `report.py`) in its directory tree.
   - *Resolution*: This module was completely removed on 2026-06-04 by ADR-0023. `docs/backtest.md` explicitly warns that `crypt.backtest` is retired and that all backtesting resides in `src/backtester/`.
2. **Exchange Client Support in `docs/architecture.md`**:
   - `docs/architecture.md` (lines 18–20) mentions "Optional fallback clients (Bybit/Binance, future)".
   - *Resolution*: No Bybit or Binance implementations exist in the repository. The only exchange client implemented is OKX (`src/crypt/exchange/okx.py`).
3. **Execution Loop Framing in `docs/architecture.md`**:
   - `docs/architecture.md` (lines 170–180) describes the system as a 4h-aligned loop driven by APScheduler.
   - *Resolution*: The active live execution system runs on an hourly (H1) cadence driven primarily by the OKX business WebSocket at `HH:59:30 UTC` (`docs/execution/h1_websocket_trigger.md`), with REST polling at `*:02 UTC` serving only as a fallback.
4. **Timeframe Enumeration**:
   - `docs/architecture.md` (line 133) defines `Timeframe` as `M15, H1, H4, D1`.
   - *Resolution*: `src/crypt/models.py` (lines 38–43) and `src/crypt/backfill/__main__.py` (lines 35–41) include `M1` (`1m`) to support minute execution and replay data.
5. **Interactive Telegram Commands Status**:
   - `docs/operations/telegram_commands.md` documents commands (`/status`, `/last`, `/explain`, `/health`, `/threshold`, `/pause`, `/trade`, `/pnl`) as an existing specification.
   - *Resolution*: The document header marks this as "Status: proposed, post-M1 run". The codebase implements only one-way notifications (`TelegramSink`, `ExecutionTelegramNotifier`); no inbound command dispatcher or polling loop exists.
6. **Observability Telemetry Status**:
   - `docs/operations/observability.md` outlines `tick_metrics.jsonl`, engine telemetry lines, and an error webhook.
   - *Resolution*: This document is marked "Status: proposed, post-M1 run". The active codebase writes standard Loguru text logs to `data/logs/crypt.log` without per-engine microsecond JSONL logging.

### 6.2 Unresolved Architectural Questions
1. **DSS v3 1m Timeframe Activation**:
   - `docs/discovery/direct_signal_search_v3.md` (lines 80–91, 381) leaves open whether `1m` candles should be permanently enabled in large matrix searches or gated behind an aggressive-search flag due to data volume and memory footprint.
2. **DSS v3 Filter Complexity Limits**:
   - Whether `max_filters` should remain an explicit user-configurable flag or be replaced by an internal algorithmic complexity budget (`docs/discovery/direct_signal_search_v3.md`, lines 383–384).
3. **Sparse vs Frequent Win Rate Thresholds**:
   - Whether sparse candidate gates should mandate higher barrier win rates than frequent candidates to compensate for smaller statistical sample sizes (`docs/discovery/direct_signal_search_v3.md`, lines 385–387).
4. **Uncalibrated Weights in Legacy Code**:
   - The original ensemble weights in `config/weights.yaml` remain marked `uncalibrated: true` (ADR-0011, ADR-0020). Since product development shifted to DSS and donor portfolios, formal calibration of the legacy ensemble was abandoned.

---

## 7. Facts the Documentation Portal Must Not Claim

To maintain strict truthfulness and avoid misleading developer-crypto-traders, the documentation portal must adhere to the following negative boundaries:

1. **Must NOT claim `crypt` is a general multi-exchange trading bot**:
   - It supports OKX perpetual swaps only. There is no support for Binance, Bybit, Coinbase, or decentralized exchanges.
2. **Must NOT claim the system includes a Web UI or Dashboard**:
   - There is no React frontend, Vue dashboard, REST API server, or GUI interface. All interactions are CLI commands, file inspections, and Telegram notifications.
3. **Must NOT claim relational databases or Redis are utilized**:
   - The data layer relies strictly on local Parquet files, JSON state files, and filesystem directories.
4. **Must NOT claim DSS automatically promotes or executes strategies**:
   - Direct Signal Search v3 is purely a research tool generating candidate configurations. Strategy promotion to production requires deliberate manual selection by the human owner.
5. **Must NOT claim the active production strategy passes the benchmark floor**:
   - Production portfolio v6 failed the benchmark target during Phase C testing (-13% return vs +15% target). It runs in production solely by explicit owner override, as documented in `docs/state/current.yml` and `docs/strategy_benchmark.md`.
6. **Must NOT claim Telegram supports interactive chat commands**:
   - The bot does not process commands like `/status` or `/trade`. It is an outbound, push-only notification system.
7. **Must NOT claim look-ahead bias is solved by evaluating forming candles**:
   - All features, indicators, and strategy signals are evaluated exclusively on closed candles. The forming candle open price is used strictly as the execution `next_open` reference.
8. **Must NOT claim real-time order book / orderflow / tick data is utilized**:
   - Order book tape and orderflow analysis are explicitly out of scope (ADR-0008). Historical analysis and live execution rely on discrete candle boundaries (OHLCV).
9. **Must NOT claim `crypt.backtest` is the active backtesting engine**:
   - The `crypt.backtest` package was deleted in June 2026. All backtesting is performed by `src/backtester/` via `backtester run`.
10. **Must NOT claim DSS v3 optimizes stop-loss, take-profit, or TTL**:
    - DSS v3 performs directional barrier labeling only. Trade geometry (RRR, TTL, trailing stops, risk %) is optimized downstream using Optuna (`backtester optimize`).
11. **Must NOT claim stop-loss triggers use OKX Mark Price**:
    - Stop-loss orders in live execution strictly use OKX `last` price triggers to preserve exact behavioral parity with backtest candle data. Mark price is used exclusively for liquidation risk modeling.
12. **Must NOT claim paper trading ledger functionality is active**:
    - Paper trading ledgers and simulated accounting sinks are unimplemented proposals. Live execution supports either `--dry-run` simulation (logging orders) or live money execution.
