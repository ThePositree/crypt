# Crypt Docs Portal P02 Source Map And Product Research

- Artifact path: `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`
- Artifact type: D3 P02 factual product research and source-to-surface mapping artifact
- Revision: 1
- Date: 2026-09-04
- Authoring context: D3 frontend phase main (`term_b095c115-2e3c-45ce-bc58-3ab5a82b338b`)
- Status: prepared for Product Surface Approval
- Target product: `crypt docs` (Russian Next.js + Tailwind documentation portal for developer-crypto-traders)

## 1. Research Context & Purpose

`crypt docs` is a documentation portal that teaches and documents the `crypt` repository as a quantitative crypto-trading framework and live execution engine.
Per owner onboarding decisions in `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`:
- Language: Russian UI and copy (with technical English terms preserved where standard).
- Stack: Next.js + Tailwind CSS.
- Mode: Purely source-grounded documentation; no CMS; no display of live balances, open positions, or real-time metrics.
- Format: Framework-style teaching (explain concepts, data structures, invariants, and copyable CLI snippets rather than quoting raw source files).
- Required sections: Overview, Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.

This document establishes the source-to-page grounding for each section, verifying that every promised portal page maps directly to verified repository implementations, architecture specifications, and configuration schemas.

---

## 2. Source-to-Route Mapping & Maturity / Risk Classification

### Section 1: Обзор платформы (Overview)
- Route prefix: `/docs/overview` (and root `/docs`)
- Audience Job: Quickly understand what `crypt` is, why it was built, its core invariants, and how to run a first smoke backtest within 5 minutes.
- Pages:
  1. `/docs` or `/docs/overview/manifesto` — **Манифест и философия фреймворка**
     - Canonical sources: `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/state/current.yml`.
     - Maturity: `stable`
     - Risk markers: `[ЖЕСТКОЕ ПРАВИЛО: БЕЗ LOOK-AHEAD BIAS]`, `[ПАРИТЕТ БЭКТЕСТА И LIVE]`
     - Key topics: Research workbench vs live OKX executor, pure decision code parity, closed candle invariant, why signal-only MVP was archived.
  2. `/docs/overview/quickstart` — **Быстрый старт и первый смоук-бэктест**
     - Canonical sources: `README.md`, `docs/cli.md`, `src/backtester/cli_runner.py`.
     - Maturity: `stable`
     - Risk markers: `[КОНФИГУРАЦИЯ И ОКРУЖЕНИЕ]`
     - Key topics: Python 3.11+, `uv sync`, `.env` setup, running a bounded smoke backtest on `SOL-USDT-SWAP` with `uv run backtester run`, analyzing console outputs and output artifacts.
  3. `/docs/overview/learning-routes` — **Маршруты изучения (Learning Tracks)**
     - Canonical sources: `docs/agent/context_routes.yml`, `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Guided path for Developers (Architecture -> Pipeline -> Engine -> Live) vs Guided path for Quant Traders (Benchmark -> Backtester -> DSS v3 -> Exit Geometry -> Risk Base).
  4. `/docs/overview/boundaries` — **Границы системы и Non-Goals**
     - Canonical sources: `AGENTS.md`, `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
     - Maturity: `stable`
     - Risk markers: `[БЕЗОПАСНОСТЬ ДЕНЕГ]`
     - Key topics: Why the portal is static and read-only, strict exclusion of live balance displays, no CMS, no interactive execution triggers from the browser.

---

### Section 2: Архитектура (Architecture)
- Route prefix: `/docs/architecture`
- Audience Job: Master the internal topology, module boundaries, dataflow contracts, and key architectural trade-offs.
- Pages:
  1. `/docs/architecture/system-overview` — **Системный обзор и граф подсистем**
     - Canonical sources: `docs/architecture.md`, `src/crypt/__init__.py`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Top-level architecture: Config -> Ingestor/Store -> EvaluationContext -> Engines/Regimes -> Aggregator -> Decision Layer -> Sinks/Executor. Interactive zoomable topology diagram.
  2. `/docs/architecture/decision-pipeline` — **Пайплайн принятия решений (Decision Pipeline)**
     - Canonical sources: `docs/architecture.md`, `src/crypt/data/context.py`, `src/crypt/models.py`.
     - Maturity: `stable`
     - Risk markers: `[ЖЕСТКОЕ ПРАВИЛО: БЕЗ LOOK-AHEAD BIAS]`, `[ПАРИТЕТ БЭКТЕСТА И LIVE]`
     - Key topics: Immutable per-tick EvaluationContext, lifecycle of a signal: Candle -> Indicators -> Signal -> Regime Filtering -> Portfolio Aggregator -> Risk Model -> Execution Order.
  3. `/docs/architecture/module-map` — **Карта модулей (`src/crypt` и `src/backtester`)**
     - Canonical sources: `src/crypt/`, `src/backtester/`, `docs/architecture.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Module responsibilities, separation between research sandbox (`src/backtester/`) and production runtime (`src/crypt/runtime/`, `src/crypt/execution/`), shared typed models (`src/crypt/models.py`).
  4. `/docs/architecture/adrs` — **Каталог архитектурных решений (ADRs)**
     - Canonical sources: `docs/decisions/` (ADR-0010, ADR-0025, ADR-0033, ADR-0058, ADR-0059, ADR-0060, ADR-0061, ADR-0062).
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Index of pivotal architectural decisions, rationale, trade-offs, and why append-only records prevent regression loops.

---

### Section 3: Бэктестер (Backtester)
- Route prefix: `/docs/backtester`
- Audience Job: Understand bar-by-bar execution simulation, fee and slippage models, Optuna parameter search, and rigorous regression checks.
- Pages:
  1. `/docs/backtester/engine` — **Механика симулятора и исполнение ордеров**
     - Canonical sources: `src/backtester/execution_sim.py`, `src/backtester/fee_model.py`, `src/backtester/exit_geometry.py`.
     - Maturity: `stable`
     - Risk markers: `[ТОЧНОСТЬ И ПАРИТЕТ]`
     - Key topics: Intrabar simulation, high/low order execution sequence, stop-loss / take-profit / time-to-live triggers, `StaticPercentFeeModel`, slippage assumptions.
  2. `/docs/backtester/regression` — **Регрессионные чекпоинты (Phase A/B/C Parity)**
     - Canonical sources: `docs/backtester_regression.md`, `docs/execution/live_backtest_reconciliation_2026-07-28.md`.
     - Maturity: `operational`
     - Risk markers: `[ПРОВЕРКА РЕГРЕССИЙ]`
     - Key topics: Historical parity checkpoints: Phase A (baseline), Phase B (accounting parity), Phase C (strict replay with warmup split `--load-from` and `--from`). How to verify the backtester is not broken.
  3. `/docs/backtester/optimization` — **Оптимизация геометрии выхода через Optuna**
     - Canonical sources: `src/backtester/optimizer.py`, `docs/cli.md`, `docs/decisions/0031-mandate-aware-optuna-target.md`.
     - Maturity: `stable`
     - Risk markers: `[РИСК ПЕРЕОБУЧЕНИЯ]`
     - Key topics: Exit geometry families (`sl_rrr`, `sl_rrr_trailing`, `tp_pct`), RRR, TTL, risk %, trailing ATR distance, generation of `best_geometry_summary.txt`.
  4. `/docs/backtester/metrics` — **Метрики эффективности и целевой бенчмарк**
     - Canonical sources: `docs/strategy_benchmark.md`, `src/backtester/mandate_report.py`, `docs/decisions/0057-distinguish-below-start-and-peak-drawdown.md`.
     - Maturity: `stable`
     - Risk markers: `[МЕТРИКИ РИСКА]`
     - Key topics: Monthly return target (+15%), profit target ($1,500/mo on $10k), positive outlier cap (`min(raw, 20)`), below-start monthly drawdown vs peak-to-trough drawdown, benchmark verdicts (Promote / Archive / Discard).

---

### Section 4: Стратегии (Strategies)
- Route prefix: `/docs/strategies`
- Audience Job: Learn how quantitative strategies are discovered, constructed into donor portfolios, filtered against regimes, and archived.
- Pages:
  1. `/docs/strategies/anatomy` — **Анатомия стратегии и базовый интерфейс**
     - Canonical sources: `src/backtester/strategy.py`, `src/backtester/registry.py`, `src/crypt/models.py`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Base `Strategy` interface, `generate(strategy_data)` method, pure function contract, registry pattern.
  2. `/docs/strategies/dss-v3` — **Direct Signal Search (DSS v3) и генерация сигналов**
     - Canonical sources: `docs/discovery/direct_signal_search_v3.md`, `docs/decisions/0062-dss-v3-persistent-multi-timeframe-search.md`, `src/backtester/strategy_discovery/`.
     - Maturity: `research`
     - Risk markers: `[ИССЛЕДОВАТЕЛЬСКИЙ МОДУЛЬ]`
     - Key topics: Multi-timeframe signal discovery, PineScript indicator catalog, triggers and parameterized filters, Quality Diversity algorithms (QD, Hyperband, SMAC, CMA), persistent feature cache.
  3. `/docs/strategies/portfolios` — **Донорные портфели и контроль хвостов (v6 SOL)**
     - Canonical sources: `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`, `docs/decisions/0058-okx-aggregate-average-entry-accounting.md`, `src/backtester/strategies/filtered_donor_portfolio.py`.
     - Maturity: `operational`
     - Risk markers: `[ДЕЙСТВУЮЩАЯ СТРАТЕГИЯ]`
     - Key topics: Architecture of donor portfolios, constituent weighting, tail control filters, negative filter research, production v6 SOL portfolio case study.
  4. `/docs/strategies/regimes` — **Детекция рыночных фаз и роутеры режимов**
     - Canonical sources: `docs/regime_detection.md`, `src/backtester/regime_router.py`, `src/backtester/indicators/market_phase.py`.
     - Maturity: `research`
     - Risk markers: None
     - Key topics: Market regime classification (Trend, Range, High Volatility), conditional weight adjustments, regime-aware routing.
  5. `/docs/strategies/lifecycle` — **Жизненный цикл кандидатов и архив**
     - Canonical sources: `docs/backtester/candidate_archive.md`, `docs/archive/candidates/`, `docs/strategy_benchmark.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Candidate lifecycle from discovery to benchmark evaluation to promotion or archival; archive directory structure and reproduction commands.

---

### Section 5: Боевое исполнение (Live Execution)
- Route prefix: `/docs/execution`
- Audience Job: Deeply understand how strategy signals are transformed into live OKX orders, exchange sync, risk anchoring, and fail-safe operation.
- Pages:
  1. `/docs/execution/architecture` — **Архитектура боевого модуля и контракт паритета**
     - Canonical sources: `docs/execution/live_execution.md`, `docs/decisions/0033-m4-live-execution-architecture.md`, `src/crypt/execution/`.
     - Maturity: `operational`
     - Risk markers: `[КРИТИЧЕСКИЙ РИСК: РЕАЛЬНЫЕ ДЕНЬГИ]`, `[ПАРИТЕТ БЭКТЕСТА И LIVE]`
     - Key topics: Component layout: LiveSignalRunner, LiveRiskCalculator, OKXTradingClient, LiveExecutionManager. Strict parity contract table between backtest and live modules.
  2. `/docs/execution/okx-client` — **Интеграция с OKX: REST, WebSocket и ордера**
     - Canonical sources: `src/crypt/execution/okx_order_client.py`, `src/crypt/runtime/h1_websocket.py`, `docs/execution/h1_websocket_trigger.md`.
     - Maturity: `operational`
     - Risk markers: `[ИСПОЛНЕНИЕ OKX / ВНЕШНЕЕ API]`
     - Key topics: Perpetual swap market orders, algo orders (SL / TP), H1 WebSocket candle trigger, fill classification, rate limits, retry policy.
  3. `/docs/execution/reconciliation` — **Синхронизация с биржей и реконсиляция стейта**
     - Canonical sources: `src/crypt/execution/exchange_sync.py`, `src/crypt/execution/position_state.py`, `docs/execution/live_execution.md`.
     - Maturity: `operational`
     - Risk markers: `[СИНХРОНИЗАЦИЯ ПОЗИЦИЙ]`
     - Key topics: OKX exchange as source of truth for money, local `live_positions.json` state, handling constituent reduction attribution when multiple logical positions share one side, orphan and phantom position handling.
  4. `/docs/execution/risk-base` — **Непрерывность риск-базы (Risk Base Continuity)**
     - Canonical sources: `src/crypt/execution/risk_base_continuity.py`, `docs/decisions/0059-durable-monthly-risk-base-checkpoints.md`.
     - Maturity: `operational`
     - Risk markers: `[ЗАЩИТА ДЕПОЗИТА]`
     - Key topics: Month-start equity latching, immutable risk base checkpoints (`risk_base_checkpoints/`), prevention of compounding drawdown, disaster recovery after mid-month restarts.
  5. `/docs/execution/notifications` — **Система оповещений и Telegram-бот**
     - Canonical sources: `docs/execution/telegram_notifications.md`, `src/crypt/execution/notifications.py`, `src/crypt/sinks/telegram.py`.
     - Maturity: `operational`
     - Risk markers: None
     - Key topics: Event types: trade entry, exit (SL / TP / TTL), exchange desync warning, monthly risk anchor established, heartbeat; message formatting and diagnostic details.

---

### Section 6: Пайплайн данных (Data Pipeline)
- Route prefix: `/docs/data-pipeline`
- Audience Job: Master candle ingestion, schema normalization, local Parquet storage, and strict look-ahead bias prevention.
- Pages:
  1. `/docs/data-pipeline/ingestion` — **Инжест свечей и бэкфилл данных**
     - Canonical sources: `src/crypt/data/`, `src/crypt/backfill/__main__.py`, `docs/backfill.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Historical candle downloading from OKX REST, pagination, gap detection, incremental backfilling.
  2. `/docs/data-pipeline/models` — **Типизированные модели данных и нормализация**
     - Canonical sources: `src/crypt/models.py`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Pydantic & dataclass schemas: `Candle`, `FundingSnapshot`, `OISnapshot`, `RatioSnapshot`, timestamp conventions (UTC, milliseconds vs ISO).
  3. `/docs/data-pipeline/storage` — **Локальное хранилище Parquet и кэширование**
     - Canonical sources: `src/backtester/data_loader.py`, `src/crypt/data/`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Directory structure `data/<symbol>/...`, column schemas, snappy compression, fast reading with `pyarrow`, in-memory feature caches.
  4. `/docs/data-pipeline/timeframes` — **Мультитаймфреймы и запрет Look-Ahead Bias**
     - Canonical sources: `AGENTS.md`, `src/backtester/data_contracts.py`.
     - Maturity: `stable`
     - Risk markers: `[ЖЕСТКОЕ ПРАВИЛО: БЕЗ LOOK-AHEAD BIAS]`
     - Key topics: Closed candles only rule! Alignment of multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d) without peeking into future data; timestamp boundaries for feature calculation.

---

### Section 7: Справочник CLI (CLI Reference)
- Route prefix: `/docs/cli`
- Audience Job: Instant access to copyable command recipes, flags, defaults, and common CLI workflows.
- Pages:
  1. `/docs/cli/overview` — **Общие соглашения и переменные окружения CLI**
     - Canonical sources: `docs/cli.md`, `README.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Defaults (`data/`, `SOL-USDT-SWAP`, full history, $10k capital), `PYTHONPATH=src`, sandbox variables (`UV_CACHE_DIR=/tmp/uv-cache`, `MPLCONFIGDIR=/tmp/matplotlib-cache`).
  2. `/docs/cli/backtester` — **Команды бэктестера: run и optimize**
     - Canonical sources: `docs/cli.md`, `src/backtester/cli_runner.py`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: `backtester run` (full vs bounded `--from`/`--to`), `backtester optimize` (Optuna 50k trials), flag reference (`--strategy`, `--output`, `--capital`, `--risk-percent`, `--rrr`, `--ttl-minutes`).
  3. `/docs/cli/discovery` — **Команды поиска сигналов: search-signals**
     - Canonical sources: `docs/cli.md`, `src/backtester/strategy_discovery/search.py`.
     - Maturity: `research`
     - Risk markers: None
     - Key topics: `backtester search-signals`, `backtester search-signals-matrix`, parallel execution parameters, feature caches.
  4. `/docs/cli/live-and-backfill` — **Команды боевого модуля и утилиты данных**
     - Canonical sources: `README.md`, `docs/execution/live_execution.md`, `src/crypt/__main__.py`, `src/crypt/backfill/__main__.py`.
     - Maturity: `operational`
     - Risk markers: `[КРИТИЧЕСКИЙ РИСК: РЕАЛЬНЫЕ ДЕНЬГИ]`
     - Key topics: `python -m crypt --once --execution-only`, dry-run mode flags, `python -m crypt.backfill` date ranges and symbol flags.

---

### Section 8: Конфигурация (Configuration)
- Route prefix: `/docs/configuration`
- Audience Job: Full reference of all environment variables, JSON strategy specifications, and safety guards.
- Pages:
  1. `/docs/configuration/env-vars` — **Переменные окружения (`.env`)**
     - Canonical sources: `.env.example`, `src/crypt/config.py`, `src/crypt/execution/settings.py`.
     - Maturity: `stable`
     - Risk markers: `[КОНФИГУРАЦИЯ И СЕКРЕТЫ]`
     - Key topics: `EXECUTION_ENABLED`, `EXECUTION_DRY_RUN`, `EXECUTION_STRATEGY_CONFIG`, `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
  2. `/docs/configuration/strategy-json` — **Формат и схема JSON-файлов стратегий**
     - Canonical sources: `strategies/archive/*.json`, `src/backtester/strategies/filtered_donor_portfolio.py`, `src/backtester/strategy_discovery/dss_config.py`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Specification of trigger definitions, filter dictionaries, exit geometry parameters, portfolio weights, and metadata fields.
  3. `/docs/configuration/risk-params` — **Параметры риска, плеча и капитала**
     - Canonical sources: `src/crypt/execution/risk_calculator.py`, `src/backtester/margin_policy.py`.
     - Maturity: `stable`
     - Risk markers: `[КОНТРОЛЬ РИСКА]`
     - Key topics: Position sizing formula, risk percent per trade (default 1.0%), max liquidation-safe leverage, monthly risk base floor.
  4. `/docs/configuration/safety-guards` — **Защитные фильтры и аварийные пороги**
     - Canonical sources: `src/crypt/execution/settings.py`, `docs/architecture.md`.
     - Maturity: `operational`
     - Risk markers: `[АВАРИЙНЫЕ СТОПЫ]`
     - Key topics: Spread guard, stale candle cooldown, max concurrent constituents, circuit breakers, emergency execution disablement.

---

### Section 9: Эксплуатация и DevOps (Operations)
- Route prefix: `/docs/operations`
- Audience Job: Deploy the engine to Railway, monitor health, triage incident alerts, and run historical reconciliation audits.
- Pages:
  1. `/docs/operations/railway` — **Развертывание на Railway и рантайм**
     - Canonical sources: `docs/deploy/railway.md`, `docs/decisions/0010-railway-deployment.md`.
     - Maturity: `operational`
     - Risk markers: `[БОЕВОЙ ДЕПЛОЙ]`
     - Key topics: Railway environment setup, persistent volume mount for `data/` and `risk_base_checkpoints/`, cron/worker triggers, environment variable overrides.
  2. `/docs/operations/monitoring` — **Мониторинг, логирование и health-чеки**
     - Canonical sources: `src/crypt/runtime/health.py`, `src/crypt/runtime/logging.py`, `docs/operations/observability.md`.
     - Maturity: `operational`
     - Risk markers: None
     - Key topics: Structured JSON logs with Loguru, health check endpoints, Telegram heartbeat reporting, memory & disk usage tracking.
  3. `/docs/operations/runbook` — **Ранбук оператора и реагирование на инциденты**
     - Canonical sources: `docs/operator.md`, `AGENTS.md`.
     - Maturity: `operational`
     - Risk markers: `[ИНЦИДЕНТЫ И РЕАГИРОВАНИЕ]`
     - Key topics: Step-by-step triage for: exchange desync alert, missing candle gap, OKX API 5xx outage, manual emergency trade closure, state file corruption recovery.
  4. `/docs/operations/reconciliation-audits` — **Аудит реконсиляции (Live vs Backtest)**
     - Canonical sources: `docs/execution/live_backtest_reconciliation_2026-07-28.md`, `src/crypt/execution/trade_replay.py`.
     - Maturity: `operational`
     - Risk markers: `[ФИНАНСОВЫЙ АУДИТ]`
     - Key topics: How to run trade-by-trade audit comparing OKX fills against backtester simulated trades; identifying slippage variance, fee discrepancies, and timing drift.

---

### Section 10: Глоссарий (Glossary)
- Route prefix: `/docs/glossary`
- Audience Job: Instant cross-reference and definitions for domain concepts spanning trading, quant metrics, and platform architecture.
- Pages:
  1. `/docs/glossary/trading` — **Трейдинг и бессрочные деривативы**
     - Canonical sources: `src/crypt/models.py`, `docs/strategy_benchmark.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: Funding rate (ставка финансирования), Open Interest (открытый интерес), Long/Short ratio, Mark vs Index price, RRR (Reward-to-Risk Ratio), TTL (Time-to-Live), ATR.
  2. `/docs/glossary/architecture` — **Архитектурные термины платформы**
     - Canonical sources: `docs/architecture.md`, `AGENTS.md`, `docs/execution/live_execution.md`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: EvaluationContext, Pure Decision Code, Parity Contract, Look-Ahead Bias, Risk Base Anchor, Constituent, Donor Portfolio, DSS v3.
  3. `/docs/glossary/strategies` — **Стратегии и паттерны технического анализа**
     - Canonical sources: `src/crypt/engines/`, `src/backtester/strategies/`.
     - Maturity: `stable`
     - Risk markers: None
     - Key topics: SMC (Smart Money Concepts), Order Block (OB), FVG (Fair Value Gap), Liquidity Sweep, Market Phase, Regime Router.

---

## 3. Risk Boundaries & Visual Markers

The documentation portal explicitly identifies 4 critical risk categories. Every relevant page and code snippet will prominently display the corresponding visual callout:

1. `[КРИТИЧЕСКИЙ РИСК: РЕАЛЬНЫЕ ДЕНЬГИ]` (Live Money Risk):
   - Highlighted in sections covering live order execution, live sizing, risk base continuity, and production deployment.
   - Purpose: Remind operators that wrong parameters cause real monetary loss on OKX.
2. `[ИСПОЛНЕНИЕ OKX / ВНЕШНЕЕ API]` (Exchange API Risk):
   - Highlighted in sections detailing OKX REST calls, order types, WebSocket subscriptions, rate limits, and network errors.
   - Purpose: Document exchange failure modes, desync, and fail-safe recovery rules.
3. `[КОНФИГУРАЦИЯ И СЕКРЕТЫ]` (Config Safety Risk):
   - Highlighted in `.env` references, API keys, and parameter overrides.
   - Purpose: Prevent accidental leak of API keys or deploying with dry-run disabled by mistake.
4. `[ЖЕСТКОЕ ПРАВИЛО: БЕЗ LOOK-AHEAD BIAS]` (No Look-Ahead Rule):
   - Highlighted in data pipeline, feature calculations, indicators, and backtester candle indexing.
   - Purpose: Ensure only closed candles are used, strictly preserving historical simulation integrity.

---

## 4. Maturity Classification System

Every page, strategy, and subsystem in `crypt docs` is tagged with one of four explicit maturity statuses:

- `stable` (Стабильно): Core framework components, verified contracts, proven CLI commands, well-tested data models.
- `research` (Исследование): Experimental discovery modules, DSS v3 genetic/QD search, regime detection algorithms under active exploration.
- `operational` (Боевое): Production execution components, live OKX client, risk-base continuity checkpoints, Railway runbook.
- `archived` (Архив): Historical reference implementations, older candidate portfolios, superseded research lines.

---

## 5. UI Surface Affordances & User Journeys

### User Journey 1: "The 5-Minute Developer Onboarding"
- Entry: Homepage (`/docs`) -> reads Framework Manifesto and Architecture diagram -> clicks Quickstart (`/docs/overview/quickstart`) -> runs `uv sync` and smoke backtest -> inspects console and output files -> follows "What to read next" to Architecture Overview.

### User Journey 2: "The Quant Strategy Researcher"
- Entry: Strategies section (`/docs/strategies`) -> explores DSS v3 signal discovery -> reviews Benchmark criteria (`/docs/backtester/metrics`) -> learns how to optimize exit geometry with Optuna (`/docs/backtester/optimization`) -> studies production v6 SOL portfolio (`/docs/strategies/portfolios`).

### User Journey 3: "The Live System Operator"
- Entry: Live Execution section (`/docs/execution`) -> inspects Parity Contract (`/docs/execution/architecture`) -> reviews Risk Base Continuity (`/docs/execution/risk-base`) -> configures `.env` (`/docs/configuration/env-vars`) -> references Railway runbook (`/docs/operations/railway`) -> reviews Incident triage (`/docs/operations/runbook`).

### User Journey 4: "Instant Command & Term Lookup"
- Entry: Any page -> presses `Cmd/Ctrl+K` -> types "optuna" or "risk_base" -> instantly sees categorized search results with snippet previews -> navigates with keyboard arrows -> hits Enter to jump directly to the section anchor.

---

## 6. Review & Approval Status

- Research grounding: Complete after coordinator correction of missing source paths, verified against active codebase and docs.
- Independence: Authored in fresh D3 phase main session.
- Approval status: Ready for Product Surface Approval after independent P02 review pass.
