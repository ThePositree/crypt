# Messaging: crypt docs

Status: proposed (Revision 2)
Revision: 2
Approval source: pending owner approval after re-review
Date: 2026-09-03
Downstream Mandatory Gates: O10 (Five raster Visual Direction Boards), O11 (Visual Direction Approval), O18–O20 (Page-level Wireframes, Persistent HTML Wireframe Artifacts, and Wireframe Approval), O21 (Screen Contracts for all 35+ portal routes), O25 (Final Implementation Approval), O33 (Independent Frontend QA Gate), O34 (Independent QA Brief)
Portal Name: crypt docs
Portal Language: Russian (content and interface)
Target Audience: developer-crypto-trader
Technology Stack: Next.js + Tailwind CSS
Source Surface: `docs/frontend/product-surface-model.md` (Revision 2, Approved)
Research Artifact: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`
Independent Contract Review: `docs/frontend/reviews/messaging-design-contract-review-2026-09-03.md` (Revision 1 Review, pass-with-fixes)

Use this file as the durable canonical contract for public product voice, page-level text contracts, message trajectories, proof systems, objection handling, microcopy standards, text inventory patterns, and anti-slop copy rules for the `crypt docs` documentation portal.

---

## 1. Messaging Identity

Messaging Identity establishes how `crypt docs` speaks to developer-crypto-traders. It translates internal repository mechanics, owner decisions, and mathematical invariants into authoritative, accessible, and disciplined Russian framework documentation.

### 1.1 Voice and Core Identity Attributes

- **Directness**: Very high. Zero introductory fluff, zero marketing hype. The text states system facts, mathematical relationships, trade-offs, and operational risks immediately. Every section answers what the subsystem does, how it works, and how to operate it.
- **Formality**: Semi-formal technical dialogue. Reads like modern engineering framework documentation (comparable to Next.js, PyTorch, Django, or Stripe docs) written natively in Russian. Respectful, objective, and intellectually rigorous.
- **Technical Depth**: High and uncompromising. The copy assumes the reader understands both software engineering (APIs, WebSockets, asyncio, Docker, CI/CD, Parquet storage, state machines) and quantitative trading (perpetual futures, leverage, isolated margin, funding rates, slippage, order types, drawdown, Sharpe/Sortino ratios). Concepts are explained via exact mechanics rather than analogies.
- **Claim Confidence**: Strictly calibrated to code and empirical evidence. High confidence on proven mathematical parity (isolated margin, fees, trailing stops, closed-candle invariant). Strictly humble and candid about strategy performance: benchmark failures, market risks, and owner overrides are presented openly without justification or whitewashing.
- **Emotional Intensity**: Calm, sober, analytical. The copy never excites the user with dreams of trading wealth, nor does it panic them with fear. Trading perpetual futures is treated as an engineering domain with high capital risk.
- **Humor**: Playful but strictly compartmentalized. Whimsical, lo-fi geometric mascot illustrations and mild self-aware quips appear solely on non-critical, low-stakes surfaces: 404 error page (`/not-found`), empty search results, and friendly tip banners. Humor is strictly forbidden inside risk callouts, live execution rules, margin mechanics, and financial warnings.
- **Relationship to the User**: Peer-to-peer technical partnership with fellow systems engineers and algorithmic traders. Addressed primarily impersonally ("Система гарантирует...", "Для запуска выполните...") or with professional second-person plural ("Вы можете настроить...", "Обратите внимание...").

### 1.2 Vocabulary and Phrase Registers

#### Approved Natural Russian Technical Phrases
- `закрытые свечи` (strictly closed candles; historical invariant)
- `отсутствие заглядывания вперед` (no look-ahead bias)
- `математический паритет симулятора и биржи` (simulation-to-exchange parity)
- `дискретно-событийный симулятор` (discrete-event simulator; `ExecutionSim`)
- `изолированная маржа` (isolated margin; strictly enforced)
- `нативный трейлинг-стоп OKX` (`move_order_stop` algorithmic order)
- `агрегированная средняя цена входа` (`avgPx` position accounting)
- `дрейф цены входа` (fill drift; difference between expected open and fill)
- `ежемесячный базис риска` (monthly risk base; capital checkpointing)
- `направленная разметка барьеров` (directional barrier labeling; DSS v3)
- `архивы качества и разнообразия` (quality-diversity archives; QD search)
- `контур синхронизации с биржей` (`ExchangeSync` reconciliation engine)
- `аудит пропущенных сигналов` (`MISSED SIGNAL` auditing)
- `прямое решение владельца` (owner override principle)

#### Strictly Prohibited / Foreign Phrases (Crypto & Marketing Slop)
- ❌ `революционный торговый робот / бот нового поколения` (pretentious marketing slop)
- ❌ `гарантированная доходность / пассивный заработок / финансовая свобода` (unethical, ungrounded financial claims)
- ❌ `100% винрейт / безупречные сигналы / Грааль` (mathematically absurd claims)
- ❌ `интуитивно понятный интерфейс / инновационная платформа` (empty corporate boilerplate)
- ❌ `уникальный искусственный интеллект / квантовая магия` (false claims about deterministic algorithms)
- ❌ `кликните сюда / жми здесь` (lazy, non-descriptive call-to-action copy)
- ❌ Any claim of multi-exchange support (Binance, Bybit) or live balance dashboards.

### 1.3 Owner Preference Signals and Translation

1. **Owner Directive**: "Framework-docs tone, direct, precise, playful but technically serious."
   - *Translation*: Structure all pages like canonical framework documentation (Overview, Architecture, Invariants, Reference, Tutorials). Use crisp section headings that state technical arguments. Confine playful mascot art to lo-fi illustrations without diluting engineering rigor.
2. **Owner Directive**: "Portal explains code architecture and workflows without quoting raw source."
   - *Translation*: Instead of embedding 50-line Python snippets of `src/backtester/execution_sim.py`, provide structured ASCII/SVG lifecycle flowcharts, state-transition tables, mathematical parameter breakdowns, and runnable CLI commands.
3. **Owner Directive**: "No live balances/positions/PnL/current runtime metrics; live execution is architecture/guarantees only."
   - *Translation*: Frame Live Execution strictly as an operational architecture guide. Add persistent notice callouts making clear that `crypt docs` is a static documentation portal that neither connects to live trading accounts nor exposes private keys or live balances.
4. **Owner Directive**: "Snippets command-only; zero simulated terminal outputs."
   - *Translation*: Every code block contains strictly executable bash/CLI commands with valid flags and arguments. Never append fake terminal progress bars, simulated logs, or mocked stdout/stderr results.

### 1.4 Translation of Private / Internal Jargon to Public Framework Copy

| Internal / Private Jargon | Public Framework Documentation Copy | Rationale |
|---|---|---|
| `донорский портфель v6` | `Мультисигнальный портфель стратегий-доноров (Core v6)` | Adds architectural clarity for external readers. |
| `drop_negative_v5` | `Фильтр контроля хвостовых рисков и неблагоприятных режимов` | Explains the statistical purpose of the filter. |
| `Phase C фейл` | `Результаты верификации Phase C (-13% доходности) и принцип ручного допуска владельцем` | Truthful, formal disclosure of benchmark non-compliance without slang. |
| `грязный воркфлоу / костыль` | `Архитектурный компромисс / временное проектное решение` | Professional engineering framing. |
| `kill switch / паника` | `Защитный контур автоматической блокировки входов` | Precise functional description. |

---

## 2. Messaging Contract

The Messaging Contract establishes the purpose, audience, mental states, key claims, required proof, and generic-copy risks for all portal surfaces.

### 2.1 Global Portal Contract (Universal Shell)

- **Page or screen**: Global application layout, top header, sidebar navigation, footer, meta tags.
- **Why it exists**: Provides an immediate mental model of `crypt docs` as the authoritative, comprehensive framework documentation for the `crypt` quantitative system.
- **Audience**: Developer-crypto-traders seeking deep architectural insight and operational guides.
- **Starting user state**: The user expects either another superficial crypto-bot landing page or a raw code dump. They may doubt the technical seriousness of the framework.
- **Intended leaving state**: The user recognizes a production-grade, disciplined quantitative framework with transparent documentation, rigorous invariants, and zero marketing hype.
- **Main idea**: `crypt` — это открытый квант-фреймворк для поиска, строгого бэктестинга и live-исполнения бессрочных фьючерсных стратегий на OKX с математическим паритетом симуляции и биржи.
- **First messages**: Framework identity badge (`v1.0`), search trigger (`Cmd+K`), navigation split into Architecture Route and Learning Route, status badges (`stable`, `research`, `operational`).
- **Later messages**: Footers with source repo link, changelog references, and explicit non-financial advice disclaimers.
- **Objections to answer**: "Это очередной телеграм-сигнальщик?" -> No, the old H4 ensemble MVP is retired historical context; this is a full research workbench and live OKX execution engine.
- **Required proof**: Two-domain architecture map (`src/backtester/` vs `src/crypt/`), canonical regression suite stats (1564 trades replay), and explicit invariant definitions.
- **Natural action**: Open the Learning Route for a guided walkthrough or use `Cmd+K` to search CLI commands.
- **Generic-copy risks**: Slipping into generic SaaS documentation boilerplate ("Добро пожаловать в нашу документацию").

### 2.2 Home Page (`/`)

- **Page or screen**: Portal root (`/`).
- **Why it exists**: Orients the developer-trader, presents core value propositions, provides high-level system architecture, and splits users into their preferred journey (Architecture vs Learning).
- **Audience**: First-time visitors and returning operators.
- **Starting user state**: Wants to know what `crypt` is, whether it's worth reading, how it works, and how to get started.
- **Intended leaving state**: Clear mental model of the two-domain architecture, understanding of core invariants (no look-ahead, exact parity), and an explicit choice of reading route.
- **Main idea**: Полная инженерная прозрачность алгоритмической торговли: от направленного поиска сигналов на закрытых свечах до атомарного исполнения на OKX.
- **First messages**:
  - Hero Headline: "Документация квант-фреймворка crypt"
  - Subheadline: "Поиск бессрочных фьючерсных стратегий, историческое моделирование с биржевым паритетом и надежное live-исполнение на OKX."
  - Primary CTAs: "Начать обучение" (Start Learning Route) and "Изучить архитектуру" (Architecture Route).
- **Later messages**: 4 Core Principles (Математический паритет, Нулевое заглядывание вперед, Автономия и контроль риска, Полная воспроизводимость), High-level System Topology diagram, Section Navigator grid.
- **Objections to answer**:
  - "Где реальный баланс и статистика?" -> The portal documents architecture and safety guarantees; live financial metrics are explicitly excluded to maintain security and prevent ungrounded claims.
  - "Бэктесты не сходятся с реалкой" -> `ExecutionSim` natively models OKX isolated margin tiers, instant fee deductions, native `move_order_stop` trailing stops, and aggregate average entry prices (`avgPx`).
- **Required proof**: Citations of ADR-0029, ADR-0050, ADR-0058, Full Replay statistics (1564 trades, 2021–2026), and clear domain boundaries.
- **Natural action**: Click "Начать обучение" or navigate to `/overview`.
- **Generic-copy risks**: Empty buzzwords like "мощный инструмент для трейдинга".

### 2.3 Guided Learning Route (`/learning/*`)

- **Page or screen**: `/learning` and 5 sequential steps (`01-data-ingestion`, `02-backtesting`, `03-signal-discovery`, `04-optimization`, `05-live-deployment`).
- **Why it exists**: Guides the developer-trader step-by-step through the quantitative lifecycle without forcing them to reverse-engineer source code.
- **Audience**: Technical practitioners wanting a hands-on tutorial workflow.
- **Starting user state**: Knows trading and Python basics, but unfamiliar with the repository's data pipeline, CLI commands, and execution flow.
- **Intended leaving state**: Confident understanding of how historical data flows into DSS v3, how Optuna optimizes geometry, how backtests validate hypotheses, and how Railway hosts live execution.
- **Main idea**: От сырых свечей до контролируемого исполнения на бирже: пятишаговый воспроизводимый цикл количественной разработки.
- **First messages**: Step indicator (1 to 5), estimated reading time, prerequisite environment variables (`PYTHONPATH=src`, `UV_CACHE_DIR=/tmp/uv-cache`).
- **Later messages**: Step-by-step CLI commands, parameter explanations, common failure modes, and "Что читать дальше" (What to Read Next) footer cards.
- **Objections to answer**: "С чего начать?" -> Step 1: historical backfill and preflight integrity checks.
- **Required proof**: Runnable CLI commands with real configuration paths (`strategies/archive/...`).
- **Natural action**: Copy CLI command, run locally, proceed to the next tutorial step.
- **Generic-copy risks**: Skipping prerequisites or assuming magical background processes.

### 2.4 Overview & Architecture Pages (`/overview`, `/architecture/*`)

- **Page or screen**: `/overview`, `/architecture`, `/architecture/domains`, `/architecture/invariants`.
- **Why it exists**: Establishes the foundational engineering contracts, domain boundaries, and inviolable safety invariants.
- **Audience**: Systems architects, quant engineers, and code auditors.
- **Starting user state**: Skeptical about edge cases: look-ahead bias in indicators, margin calls, exchange desync, code coupling.
- **Intended leaving state**: Certainty that the system strictly separates research from continuous execution, enforces closed-candle inputs, and isolates margin risk.
- **Main idea**: Разделение двух миров: детерминированная исследовательская лаборатория (`src/backtester/`) и отказоустойчивый контур исполнения (`src/crypt/`).
- **First messages**: Two-domain diagram, invariant callout box (`Строгий инвариант: только закрытые свечи`), retired modules notice (ADR-0023 retirement of `crypt.backtest`).
- **Later messages**: Memory models, WebSocket vs REST triggers, Parquet schema stability, explicit negative boundaries.
- **Objections to answer**: "Как гарантируется отсутствие заглядывания вперед?" -> Features and signals use closed candles only (`closed=True`); forming candle open is used strictly as the execution `next_open` reference price.
- **Required proof**: Citations of `src/crypt/models.py`, `tests/data/test_store_closed_invariant.py`, ADR-0023, and ADR-0029.
- **Natural action**: Explore `/backtester/parity-mechanics` or `/execution/safety-and-sync`.
- **Generic-copy risks**: Abstract architecture diagrams without concrete package and file path mappings.

### 2.5 Backtester Engine & Parity Pages (`/backtester/*`)

- **Page or screen**: `/backtester`, `/backtester/parity-mechanics`, `/backtester/risk-model`, `/backtester/regression`.
- **Why it exists**: Documents how `ExecutionSim` achieves fidelity with OKX perpetual trading mechanics.
- **Audience**: Quant developers verifying simulation integrity and reviewing benchmark checkpoints.
- **Starting user state**: Believes backtest results are overfit or idealized (zero slippage, ignored fees, naive stop-loss triggers).
- **Intended leaving state**: Understands that `ExecutionSim` models real exchange friction: isolated margin maintenance tiers, instant entry fee deduction, worst-case intrabar trailing stops, and aggregate average entry prices.
- **Main idea**: Бэктестер, созданный не для красивых отчетов, а для точного отражения биржевой физики OKX.
- **First messages**: `ExecutionSim` discrete-event architecture, comparison table between naive backtests and `crypt` parity simulation.
- **Later messages**: Mathematical formulations for `BasicRiskModel`, monthly risk-base capital anchoring (ADR-0019/0059), Canonical Full Replay (1564 trades) and Phase C checkpoint specifications.
- **Objections to answer**: "Почему доходность бэктеста ниже, чем у наивных симуляторов?" -> Because `crypt` accounts for taker fees on limit TPs, liquidation buffers, amount step quantization, and realistic intrabar stop order fills.
- **Required proof**: Canonical regression statistics from `docs/backtester_regression.md`, exact instrument precision constants (`okx_sol_usdt_swap_2026_07_01`).
- **Natural action**: Run `backtester run` with regression flags to verify local output matches canonical checkpoints.
- **Generic-copy risks**: Claiming "zero error" instead of explaining exact modeled mechanisms and known limitations.

### 2.6 Strategy Discovery & Optimization Pages (`/strategies/*`)

- **Page or screen**: `/strategies`, `/strategies/production-portfolio`, `/strategies/dss-v3`, `/strategies/optuna-optimizer`, `/strategies/benchmark`.
- **Why it exists**: Explains how strategies are systematically discovered (DSS v3), optimized (Optuna), registered, and evaluated against the mandate benchmark.
- **Audience**: Quant researchers and portfolio operators.
- **Starting user state**: Wonders if strategies are hardcoded heuristic rules or curve-fitted parameters.
- **Intended leaving state**: Understands DSS v3 multi-timeframe directional barrier labeling, Quality-Diversity archiving, downstream geometry tuning, and the owner override principle.
- **Main idea**: Разделение поиска сигналов и оптимизации геометрии: генетический поиск структуры без подгонки кривой и контролируемый допуск в продакшен.
- **First messages**: Strategy Registry (`src/backtester/registry.py`), active production strategy (`filtered_donor_portfolio` Core v6 on `SOL-USDT-SWAP`), benchmark target definition.
- **Later messages**: Multi-timeframe search topology (15m, 1h, 4h, 1d), barrier labeling math, QD archive backends (CatCMA, SMAC, Island), Optuna parameter spaces (RRR, TTL, risk %, trail ATR), and owner override documentation.
- **Objections to answer**: "Продакшен-стратегия соответствует бенчмарку?" -> No, Core v6 failed Phase C benchmark floors (-13% vs +15% target) and runs under explicit owner override.
- **Required proof**: Phase C benchmark table, `docs/discovery/direct_signal_search_v3.md`, `docs/strategy_benchmark.md`.
- **Natural action**: Review DSS v3 search parameters and run `backtester search-signals`.
- **Generic-copy risks**: Hiding the benchmark failure or hyping DSS v3 as an autonomous AI money machine.

### 2.7 Live Execution & Safety Pages (`/execution/*`)

- **Page or screen**: `/execution`, `/execution/order-lifecycle`, `/execution/native-trailing`, `/execution/safety-and-sync`.
- **Why it exists**: Documents the runtime execution loop, order state machines, safety circuit breakers, and reconciliation logic on OKX.
- **Audience**: Reliability engineers, devops operators, and live money auditors.
- **Starting user state**: Concerned about exchange API failures, WebSocket disconnects, slippage, double fills, or orphaned positions.
- **Intended leaving state**: Complete confidence in the atomic order lifecycle (`entry_intent` -> `protected`), persistent state files, `ExchangeSync` reconciliation, and blocked-signal auditing.
- **Main idea**: Отказоустойчивое исполнение на OKX: атомарные состояния, нативные биржевые стопы и полная синхронизация перед каждой операцией.
- **First messages**: Notice callout (no live balances/trading from docs), dual trigger diagram (H1 WebSocket `HH:59:30 UTC` + REST fallback at `*:02 UTC`).
- **Later messages**: Atomic lifecycle flowchart, native `move_order_stop` pre-submit geometry, durable `live_positions.json` with backup snapshots, `ExchangeSync` rules, `MISSED SIGNAL` auditing, alert-only fill drift policy.
- **Objections to answer**: "Что происходит при сбое сети во время отправки ордера?" -> Local state records `entry_intent`; on recovery, `ExchangeSync` reconciles open orders and positions before any new action is permitted.
- **Required proof**: ADR-0050, ADR-0051, ADR-0054, ADR-0059, code citations to `src/crypt/execution/`.
- **Natural action**: Review Telegram notification contracts in `/operations/telegram-alerts`.
- **Generic-copy risks**: Making promises of "100% uptime" or claiming real-time tick-level orderbook execution.

### 2.8 Data Pipeline & Storage Pages (`/data-pipeline/*`)

- **Page or screen**: `/data-pipeline`, `/data-pipeline/backfill`, `/data-pipeline/preflight`.
- **Why it exists**: Details historical data storage, supported data types, idempotent backfill CLI, and preflight integrity checks.
- **Audience**: Data engineers and operators managing historical data partitions.
- **Starting user state**: Assumes the project requires Postgres, TimescaleDB, or Redis.
- **Intended leaving state**: Understands the local Parquet partitioned store under `data/<SYMBOL>/`, the strict closed-candle persistence rule, and automated preflight repair.
- **Main idea**: Локальное файловое хранилище на Parquet: нулевые сетевые накладные расходы, строгая партиционированность и автоматическая проверка целостности.
- **First messages**: Storage topology map, closed-candle invariant badge, list of supported data types (OHLCV, 1m, OI, L/S ratio, taker volume).
- **Later messages**: `python -m crypt.backfill` syntax, preflight 0-byte corrupt file purge, staleness thresholds (H1 max 3h, H4 max 12h, D1 max 3d), retirement of Coinglass (ADR-0016).
- **Objections to answer**: "Почему Parquet, а не база данных?" -> Parquet provides zero-overhead columnar scans, reproducible git/filesystem snapshots, and zero external service dependencies (ADR-0005).
- **Required proof**: `src/crypt/runtime/deploy_preflight.py`, ADR-0005, ADR-0016.
- **Natural action**: Run `deploy_preflight.py` or execute a backfill test.
- **Generic-copy risks**: Vague descriptions of data storage without exact folder schemas and partitioning keys.

### 2.9 CLI Reference Pages (`/cli/*`)

- **Page or screen**: `/cli`, `/cli/backtester`, `/cli/runtime`.
- **Why it exists**: Comprehensive, copyable, exact command syntax reference for daily research and operations.
- **Audience**: Terminal-driven operators, quant researchers, and automated runbooks.
- **Starting user state**: Needs the exact command syntax, flag names, and environment variables without reading Python argparse code.
- **Intended leaving state**: Can instantly copy runnable commands with correct arguments, knowing exactly what each flag controls.
- **Main idea**: Точный консольный справочник: исполняемые команды, параметры по умолчанию и окружение без лишнего вывода.
- **First messages**: Global environment rules (`PYTHONPATH=src`, `UV_CACHE_DIR=/tmp/uv-cache`), command selector tabs.
- **Later messages**: Parameter tables (flag, type, default, required, description), copyable command snippets with syntax highlighting.
- **Objections to answer**: "Где примеры вывода терминала?" -> Output is deliberately omitted; snippets contain only executable commands to prevent stale or misleading results.
- **Required proof**: Verified argument lists from `src/backtester/__main__.py` and `src/crypt/__main__.py`.
- **Natural action**: Click "Копировать команду" and execute in local terminal.
- **Generic-copy risks**: Including fake/mocked terminal progress bars, imaginary dates, or unverified flags.

### 2.10 Configuration & Operations Pages (`/configuration/*`, `/operations/*`)

- **Page or screen**: `/configuration`, `/configuration/startup-validation`, `/operations`, `/operations/telegram-alerts`.
- **Why it exists**: Documents environment variables, Strategy JSON source-of-truth rules, pre-trade startup validation, Railway deployment, and Russian operator Telegram alerts.
- **Audience**: DevOps engineers and live system operators.
- **Starting user state**: Needs to know where configuration lives and what happens if `.env` settings clash with strategy JSON files.
- **Intended leaving state**: Understands the configuration hierarchy (Strategy JSON overrides `.env` for money parameters), pre-trade crash-on-mismatch validation, Railway volume mounting, and the 8 Telegram alert types.
- **Main idea**: Иерархическая конфигурация и предсказуемая эксплуатация: защита от дрейфа параметров и прозрачные Telegram-уведомления.
- **First messages**: Configuration priority hierarchy diagram, startup validation warning (`Pre-trade защита`).
- **Later messages**: Environment variables reference table, Railway deployment runbook, Loguru log rotation, Telegram presentation contracts for 8 event types.
- **Objections to answer**: "Может ли бот торговать с неверными настройками маржи?" -> No, startup validation compares `.env` with Strategy JSON `backtest_args` and halts execution if any parameter differs.
- **Required proof**: `src/crypt/execution/settings.py`, `scripts/railway_live_start.sh`, `docs/execution/telegram_notifications.md`.
- **Natural action**: Inspect `.env.example` and verify Railway volume configuration.
- **Generic-copy risks**: Omitting the pre-trade mismatch crash rule or treating Telegram bot as interactive.

### 2.11 Glossary & Command Palette (`/glossary`, `[Modal] Cmd+K`)

- **Page or screen**: `/glossary` and global search palette modal.
- **Why it exists**: Provides instant, keyboard-driven access to every concept, acronym, subsystem, and command in the documentation.
- **Audience**: All users seeking rapid lookup.
- **Starting user state**: Encounters unfamiliar terms (DSS v3, QD, ExecutionSim, Monthly Risk Base, `move_order_stop`, `avgPx`) or searches for specific CLI commands.
- **Intended leaving state**: Quickly finds precise definitions, source-of-truth citations, and direct navigation links to relevant deep-dive pages.
- **Main idea**: Мгновенный доступ ко всем терминам, концепциям и командам фреймворка.
- **First messages**: Search input field, alphabetical index pills (А–Я, A–Z), category filters (Архитектура, Бэктестер, Исполнение, Риск).
- **Later messages**: Concise definitions with formula/parameter callouts, links to canonical ADRs and documentation pages.
- **Objections to answer**: "Слишком много внутренних терминов" -> Every term has a formal definition and architectural context.
- **Required proof**: Definitions mapped directly to repository models and ADRs.
- **Natural action**: Select a search result or glossary link and jump directly to the target section.
- **Generic-copy risks**: Dictionary definitions copied from generic Wikipedia articles instead of repository-grounded mechanics.

### 2.12 Risk Callouts Contract

- **Page or screen**: Reusable content blocks embedded across all documentation pages.
- **Why it exists**: Highlights non-negotiable boundaries, financial risks, mathematical invariants, and retired modules to prevent operator errors.
- **Audience**: All readers, especially operators preparing live execution or backtest runs.
- **Starting user state**: Scanning content quickly, prone to missing critical nuances or safety constraints.
- **Intended leaving state**: Fully aware of specific hazards, invariants, or deprecated paths before taking action.
- **Main idea**: Явные визуальные и текстовые границы: безопасность капитала, строгость математики и честность статусов.
- **First messages**: Visual badge/icon and category header: `Критический риск`, `Строгий инвариант`, `Важное примечание`, `Устаревший компонент`.
- **Later messages**: Exact hazard explanation, mathematical or operational consequence, and mandatory operator action.
- **Objections to answer**: "Зачем мне это читать?" -> Violating this invariant causes look-ahead bias, capital loss, or runtime crash.
- **Required proof**: References to specific ADRs, closed-candle invariant tests, or OKX liquidation rules.
- **Natural action**: Heed the warning, verify local configuration, or avoid using retired commands.
- **Generic-copy risks**: Using generic "Warning!" banners without stating the exact operational mechanism.

### 2.13 404 Error Page (`/not-found`) Contract

- **Page or screen**: Global error page (`/not-found`).
- **Why it exists**: Handles broken URLs gracefully, re-orients the lost user, and provides immediate recovery paths back to documentation.
- **Audience**: Any user following a broken link, mistyped URL, or stale bookmark.
- **Starting user state**: Frustrated or confused by a missing resource.
- **Intended leaving state**: Amused by the friendly lo-fi mascot illustration, immediately aware of what happened, and easily navigates back to Home, Overview, or opens Search.
- **Main idea**: Страница не найдена, но навигация под контролем: быстрый возврат к документации и поиск нужного раздела.
- **First messages**: Lo-fi lost-mascot illustration, clear Russian headline: "404: Страница потерялась в блоках".
- **Later messages**: Explanatory text: "Запрошенный маршрут документации не существует или был перемещен при рефакторинге." Action buttons: "На главную", "Обзор платформы", "Открыть поиск (Cmd+K)".
- **Objections to answer**: "Сайт сломался?" -> No, only this specific URL is missing; the full framework documentation is operational.
- **Required proof**: Functional navigation links and keyboard shortcut trigger.
- **Natural action**: Click "На главную" or press `Cmd+K`.
- **Generic-copy risks**: Default browser "404 Not Found" blank page or aggressive technical error traces.

---

## 3. Message Trajectory

Message Trajectory defines the structured psychological progression a user experiences while reading key portal surfaces. It ensures every page transforms user hesitation into understanding and confident action.

### 3.1 Portal Home Page (`/`) Trajectory

```text
[1. Starting User State]
User arrives asking: "Что такое crypt? Очередной сомнительный торговый бот или серьезная инженерная система?"
       │
       ▼
[2. Problem / Tension]
Большинство решений для алготрейдинга либо показывают фантастические результаты на переоптимизированных бэктестах,
которые рушатся на реальной бирже, либо представляют собой закрытые «черные ящики» без понятной архитектуры и гарантий безопасности.
       │
       ▼
[3. Product Explanation]
crypt — это прозрачный исследовательский веркбенч и модуль исполнения на OKX.
Мы разделяем систему на два независимых домена: строгую математическую лабораторию (src/backtester/)
и автономный контур живой торговли (src/crypt/).
       │
       ▼
[4. Mechanism]
- Нулевое заглядывание вперед: расчет индикаторов и сигналов строго на закрытых свечах (closed=True).
- Полный биржевой паритет: ExecutionSim учитывает изолированную маржу, комиссии тейкера, нативный трейлинг move_order_stop и среднюю цену avgPx.
- Защита капитала: атомарные состояния ордеров, ежемесячный базис риска и полная сверка с биржей ExchangeSync перед каждым действием.
       │
       ▼
[5. Proof]
Регрессионный чекпоинт на 1564 сделках (2021–2026), канонический набор тестов Phase C,
архитектурные решения ADR-0001 — ADR-0062 и открытые формулы расчета риска.
       │
       ▼
[6. Objection Handling]
- "Где текущий PnL и позиции?" -> Портал документирует архитектуру; live-метрики исключены из соображений безопасности.
- "Продакшен-стратегия гарантирует прибыль?" -> Нет. Активный портфель Core v6 работает по прямому решению владельца,
  несмотря на несдачу бенчмарка (-13% на Phase C). Мы не обещаем Граалей и говорим об этом честно.
       │
       ▼
[7. Action]
Выберите удобный маршрут:
- [Начать обучение]: пошаговый путь от сбора данных до деплоя.
- [Изучить архитектуру]: детальный разбор подсистем, доменов и инвариантов.
- [Нажать Cmd+K]: быстрый поиск нужной команды или параметра.
```

### 3.2 Guided Learning Route (`/learning/*`) Trajectory

```text
[1. Starting User State]
User arrives at /learning: "Я хочу запустить процесс исследования и торговли, но не знаю последовательность шагов и CLI команд."
       │
       ▼
[2. Problem / Tension]
Фреймворк содержит десятки CLI флагов, алгоритмов оптимизации и конфигурационных файлов.
Без единой дорожной карты легко допустить ошибку в окружении или запустить оптимизацию не на тех данных.
       │
       ▼
[3. Product Explanation]
Обучающий маршрут crypt docs — это 5 последовательных шагов, воспроизводящих полный производственный цикл
количественного исследователя: от загрузки сырых данных с OKX до безопасного мониторинга на Railway.
       │
       ▼
[4. Mechanism]
Шаг 1: Сбор закрытых свечей в Parquet через crypt.backfill и префлайт-чеки.
Шаг 2: Запуск ExecutionSim через backtester run с проверкой изолированной маржи и комиссий.
Шаг 3: Поиск сигналов в DSS v3 через направленную разметку барьеров на нескольких таймфреймах.
Шаг 4: Оптимизация геометрии сделок (RRR, TTL, трейлинг) в Optuna.
Шаг 5: Развертывание контейнера на Railway с проверкой переменных и Telegram-оповещениями.
       │
       ▼
[5. Proof]
Каждый шаг содержит точные исполняемые команды с проверенными путями к стратегиям из strategies/archive/
и проверяемые условия перехода к следующему этапу.
       │
       ▼
[6. Objection Handling]
"Что если команда упадет из-за нехватки памяти или конфликта версий?" ->
На каждом шаге зафиксированы обязательные переменные (PYTHONPATH=src, UV_CACHE_DIR=/tmp/uv-cache) и лимиты ресурсов.
       │
       ▼
[7. Action]
Перейти к Шагу 1: "1. Сбор и подготовка данных" -> Запустить первую команду бекфилла.
```

### 3.3 Subsystem Deep-Dive & Parity Mechanics Trajectory

```text
[1. Starting User State]
User lands on /backtester/parity-mechanics or /execution/order-lifecycle: "Действительно ли этот симулятор сходится с биржей OKX?"
       │
       ▼
[2. Problem / Tension]
Большинство алгоритмов показывают прибыль в бэктестах, но сливают на бирже из-за скрытых ликвидаций на изолированной марже,
проскальзываний на стопах, комиссий за вход и несовпадения логики трейлинга.
       │
       ▼
[3. Product Explanation]
ExecutionSim спроектирован как точный цифровой двойник торгового ядра OKX для бессрочных свопов SOL-USDT-SWAP.
Он воспроизводит правила биржи до цента и до шага тика.
       │
       ▼
[4. Mechanism]
- Изолированная маржа: динамический расчет безопасного плеча с запасом ликвидации (ADR-0026, ADR-0049).
- Тайминг комиссий: комиссия за вход списывается мгновенно в момент открытия, уменьшая свободную маржу (ADR-0053).
- Трейлинг OKX: моделирование move_order_stop с активационной ценой и спредом отката по ATR14 закрытой свечи (ADR-0050).
- Агрегированный вход: учет объединения позиций биржей по средней цене avgPx с раздельным учетом сигналов (ADR-0058).
       │
       ▼
[5. Proof]
Полная регрессионная каноническая выборка (Full Replay): ровно 1564 сделки, 35.32% win rate, 1.43 profit factor.
Тесты test_minute_execution.py и test_native_okx_trailing.py подтверждают совпадение долей тика.
       │
       ▼
[6. Objection Handling]
"А что с дрейфом цены исполнения?" -> При расхождении цены входа H1 и биржевого маркет-ордера отправляется
алерт "Цена входа отличается от плана", но сделка сопровождается дальше по биржевым защитным ордерам (ADR-0054).
       │
       ▼
[7. Action]
Изучить параметры инструмента okx_sol_usdt_swap_2026_07_01 или перейти к спецификации жизненного цикла ордеров.
```

---

## 4. Text Hierarchy

Text Hierarchy establishes strict formatting and semantic rules across 5 textual levels to guarantee that scanning readers instantly capture arguments and critical nuances.

### Level 1: Main Promise (Заголовок страницы / Hero)
- **Role**: States the central premise, value, or capability of the page. Must be fully understandable in isolation without reading supporting text.
- **Tone**: Authoritative, concise, mathematically grounded.
- **Pattern**: `[Субсистема или Концепция]: [Ключевая инженерная гарантия или задача]`
- **Examples**:
  - Home: `crypt docs: Инженерная документация квант-фреймворка`
  - Backtester Parity: `Механика паритета: точное воспроизведение торгового ядра OKX`
  - DSS v3: `Direct Signal Search v3: генетический поиск сигналов без подгонки под историю`
  - Invariants: `Инварианты системы: нулевое заглядывание вперед и изолированная маржа`

### Level 2: Section Arguments (Заголовки разделов h2 / h3)
- **Role**: Headings must function as progressive technical arguments rather than passive nouns. A reader scanning only Level 1 and Level 2 headings must understand the complete logical progression of the page.
- **Tone**: Assertive, mechanism-oriented, active.
- **Examples**:
  - Instead of `## Описание маржи` -> `## Изолированная маржа всегда включена для предотвращения кросс-ликвидации аккаунта`
  - Instead of `## Свечи` -> `## Расчет сигналов ведется строго по закрытым свечам с нулевым заглядыванием вперед`
  - Instead of `## Трейлинг` -> `## Нативный трейлинг OKX move_order_stop фиксирует геометрию в момент входа`
  - Instead of `## Сбои` -> `## Контур ExchangeSync останавливает новые входы при любом рассинхроне с биржей`

### Level 3: Supporting Copy (Основной текст, формулы, пояснения)
- **Role**: Explains mechanisms, trade-offs, configuration parameters, mathematical models, empirical limitations, and edge-case behaviors.
- **Tone**: Analytical, structured, dense with information.
- **Rules**:
  - Lead with the operational consequence before detailing configuration keys.
  - Always pair an architectural choice with its rationale and canonical ADR reference.
  - Break complex conditions into bulleted lists or comparison tables rather than dense prose walls.

### Level 4: Action Copy (Кнопки, ссылки, действия)
- **Role**: Concrete, unambiguous, verb-first callouts indicating exactly what will occur upon user action.
- **Tone**: Decisive, explicit, unambiguous.
- **Rules**:
  - Ban vague labels ("Далее", "Подробнее", "Кликните", "Сюда").
  - Use exact target descriptions: `Скопировать команду бэктеста`, `Перейти к шагу 2: Историческое моделирование`, `Открыть спецификацию ADR-0050`, `Сбросить фильтры поиска`.

### Level 5: Microcopy (Бейджи, подсказки, хлебные крошки, ошибки, поля ввода)
- **Role**: Resolves immediate user friction at the point of interaction.
- **Tone**: Compact, helpful, context-sensitive.
- **Rules**:
  - Breadcrumbs display exact hierarchy: `Главная / Бэктестер / Механика паритета`.
  - Maturity Badges: `stable` (зеленый пастельный), `operational` (синий пастельный), `research` (лавандовый пастельный), `archived` (серый/янтарный).
  - Code Copy Feedback: `Скопировано!` (rendered with fixed container/button width `min-w-[140px]` or tooltip to prevent layout shift of adjacent elements; persists for 2 seconds).
  - Search Input: `Поиск по документации... (Cmd+K)`.

---

## 5. Proof System

The Proof System enforces that every strong technical claim in `crypt docs` is anchored directly to repository evidence, code implementations, regression checkpoints, or empirical test results. Unsubstantiated claims are strictly forbidden.

| # | Major Framework Claim | Required Proof | Available Repository Evidence | Missing / Deferred Proof | Decision & Copy Rule |
|---|---|---|---|---|---|
| **1** | **Математический паритет симулятора с биржей OKX** | Доказательство совпадения маржи, комиссий, шага тика, нативного трейлинга и объединения входов. | 1. Изолированная маржа и динамическое плечо (`src/backtester/margin_policy.py`, ADR-0026, ADR-0049).<br>2. Мгновенное списание комиссии входа (`src/backtester/fee_model.py`, ADR-0053).<br>3. Трейлинг `move_order_stop` (`tests/execution/test_native_okx_trailing.py`, ADR-0050).<br>4. Агрегированная средняя цена `avgPx` (ADR-0058).<br>5. Канонический регресс Full Replay: 1564 сделки (`docs/backtester_regression.md`). | Тиковые данные стакана (OrderBook tape) исключены по ADR-0008. | **ADD PROOF**: Утверждать паритет на уровне свечей и минутных баров (`minute_last`/`minute_mark`), явно указывая на исключение тикового стакана. |
| **2** | **Строгое отсутствие заглядывания вперед (No Look-Ahead Bias)** | Доказательство того, что ни один индикатор, фича или фильтр не видит будущее в момент генерации сигнала. | 1. Валидация модели данных: свойство `closed=True` обязательно для всех сохраняемых свечей (`src/crypt/models.py`, `tests/data/test_store_closed_invariant.py`).<br>2. Цена входа — строго `next_open` формирующейся свечи (`src/backtester/execution_sim.py`).<br>3. Разделение периода прогрева (warmup) и периода учета в регрессионных тестах Phase C (`docs/backtester_regression.md`). | Нет. Полнота доказательств подтверждена тестами. | **ADD PROOF**: Описать инвариант как фундамент фреймворка; в каждом описании сигналов повторять, что используются только закрытые бары. |
| **3** | **DSS v3 находит робастные сигналы без оверфиттинга через бэктест** | Доказательство разделения фазы поиска сигналов и фазы оптимизации мани-менеджмента. | 1. Оценка кандидатов ведется исключительно по направленной разметке барьеров (Directional Barrier Labeling) на закрытых свечах (`docs/discovery/direct_signal_search_v3.md`, ADR-0062).<br>2. Разделение по частотным корзинам (`sparse`, `medium`, `frequent`).<br>3. Архивы Quality-Diversity (CatCMA, SMAC, Island).<br>4. Оптимизация SL/TP/TTL вынесена в отдельный шаг Optuna. | Влияние 1m свечей на матричный поиск остается открытым вопросом в документации. | **ADD PROOF**: Четко объяснять, что DSS v3 оценивает только направленное движение цены до барьеров, а не финансовую эквити-кривую. |
| **4** | **Безопасность капитала и отказоустойчивость live-рантайма** | Доказательство того, что сбои сети, рассинхрон или перезапуски не приводят к неконтролируемым ордерам. | 1. Атомарный жизненный цикл ордеров (`entry_intent` -> `protected`) с записью в `data/live_positions.json` и ротацией бэкапов (`docs/execution/live_execution.md`).<br>2. Контур `ExchangeSync`: сверка балансов, позиций и стопов перед каждым действием.<br>3. Ежемесячные чекпоинты базиса риска `YYYY-MM.json` с контрольными суммами (ADR-0059).<br>4. Аудит блокировок: логирование `MISSED SIGNAL` и Telegram-алерты. | Интерактивные команды Telegram (`/pause`, `/trade`) не реализованы. | **ADD PROOF & WEAKEN CLAIM**: Подтверждать безопасность локальных контуров и атомарных состояний, но явно указывать, что интерактивное управление через Telegram отсутствует (только push-уведомления). |
| **5** | **Статус активной продакшен-стратегии и принцип ручного допуска** | Доказательство статуса стратегии v6 и оснований ее работы на реальном счете. | 1. Конфиг: `filtered_donor_portfolio` v6 на `SOL-USDT-SWAP` (`docs/state/current.yml`).<br>2. Результат Phase C: -13.11% доходности при бенчмарке +15% (`docs/strategy_benchmark.md`).<br>3. Полномочия владельца: бенчмарк является исследовательским ориентиром, владелец имеет право допускать любую стратегию (`AGENTS.md`, `docs/strategy_benchmark.md`). | Нет. Статус прозрачно зафиксирован в репозитории. | **ADD PROOF & MAINTAIN HONESTY**: Открыто публиковать несдачу бенчмарка активной стратегией и объяснять принцип ручного допуска владельцем (Owner Override). Запретить любые попытки скрыть просадку. |

---

## 6. Objection Map

The Objection Map anticipates real technical and operational doubts a developer-crypto-trader will have, placing concrete, source-backed responses exactly where the objection arises.

### Objection 1: "Очередной 'прибыльный' бот из Телеграма с рисованными доходностями"
- **Where it arises**: Hero section of Home (`/`) and Overview (`/overview`).
- **Trigger**: The reader has seen hundreds of fraudulent crypto-bot sites promising passive income.
- **Verbatim Response**:
  > «crypt не продает подписки, не обещает доходности и не является "волшебным ботом". Это открытый исследовательский фреймворк и модульная среда исполнения, созданная по стандартам системного программирования: строгая типизация, изоляция маржи, полное воспроизведение комиссий и открытый исходный код без заглядывания вперед. Исторический Telegram-MVP 2026 года завершен и оставлен лишь как контекст; текущий фокус — чистая количественная архитектура.»
- **Placement**: Primary text block immediately beneath the Home Hero and in the "История и контекст MVP" section on `/overview`.
- **Evidence**: `README.md`, `AGENTS.md`, ADR-0023.

### Objection 2: "Бэктесты всегда врут: на истории плюс, на реальном счете — ликвидация"
- **Where it arises**: Navigation to `/backtester` and `/backtester/parity-mechanics`.
- **Trigger**: The trader has experienced execution slippage, liquidation on isolated margin, or unrealistic fills on limit orders in other simulators.
- **Verbatim Response**:
  > «ExecutionSim создавался для устранения разрыва между бэктестом и биржей. Симулятор принудительно рассчитывает уровни ликвидации по формулам OKX, списывает комиссии за вход в нулевую секунду, консервативно считает limit-тейк-профиты как taker-сделки и эмулирует алгоритмические трейлинг-стопы move_order_stop по худшей внутрисвечной цене. Если бэктест показывает убыток из-за биржевых трений, вы увидите его до отправки реальных денег.»
- **Placement**: Lead callout card on `/backtester/parity-mechanics` and comparison table on `/backtester`.
- **Evidence**: ADR-0026, ADR-0049, ADR-0050, ADR-0053, ADR-0058.

### Objection 3: "Где графики баланса реального счета и открытые позиции? Вы их прячете?"
- **Where it arises**: `/overview`, `/execution`, and footer links.
- **Trigger**: The visitor expects a SaaS analytics dashboard with live PnL widgets and wallet balances.
- **Verbatim Response**:
  > «crypt docs — это портал документации архитектуры и кода, а не дашборд торгового счета. Из соображений безопасности, защиты приватных ключей и предотвращения спекулятивных манипуляций портал принципиально не подключается к API биржи в реальном времени и не отображает текущий баланс или активные позиции. Вся информация об исполнении посвящена архитектурным гарантиям, стейт-машине ордеров и защитным контурам.»
- **Placement**: Persistent Notice Callout on `/execution` and Section 1 of `/overview`.
- **Evidence**: Product Surface Model (Negative Boundaries), `docs/architecture.md`.

### Objection 4: "Фреймворк выглядит слишком сложным: десятки флагов, формул и файлов. С чего мне начать?"
- **Where it arises**: First interaction with the navigation sidebar or `/architecture`.
- **Trigger**: Cognitive overload from extensive quant and systems terminology.
- **Verbatim Response**:
  > «Вам не нужно изучать всю кодовую базу одновременно. Перейдите в Обучающий маршрут (/learning): он разбит на 5 понятных практических шагов. Вы последовательно выполните бэкфилл данных, запустите воспроизводимый бэктест одной командой, разберете поиск сигналов в DSS v3 и поймете, как работает боевой контейнер на Railway. Для быстрого поиска конкретной команды всегда доступна палитра Cmd+K.»
- **Placement**: Quick-start banner on Home (`/`), header link "Обучающий маршрут", and empty search states.
- **Evidence**: Journey 1 from `docs/frontend/product-surface-model.md`.

### Objection 5: "Что произойдет, если сервер перезагрузится прямо во время открытой сделки?"
- **Where it arises**: `/execution/order-lifecycle` and `/execution/safety-and-sync`.
- **Trigger**: Fear of orphaned positions, unbounded losses, or double-entry bugs after system crashes.
- **Verbatim Response**:
  > «Каждый вход в позицию на OKX отправляется как рыночный ордер с прикрепленными биржевыми стоп-ордерами (attachAlgoOrds), а для трейлинга выставляется нативный move_order_stop на инфраструктуре OKX. Даже при полном падении сервера позиция защищена на стороне биржи. При перезапуске контур ExchangeSync считывает состояние аккаунта OKX через приватный REST API, сопоставляет его с data/live_positions.json и блокирует любые новые действия до полного подтверждения синхронизации.»
- **Placement**: "Отказоустойчивость и аварийное восстановление" accordion on `/execution/safety-and-sync`.
- **Evidence**: `docs/execution/live_execution.md` (lines 315–370), ADR-0050.

### Objection 6: "Почему в документации нет исходного кода функций, а только команды и схемы?"
- **Where it arises**: `/architecture` and `/cli/*`.
- **Trigger**: The engineer expects raw copy-pasted Python snippets.
- **Verbatim Response**:
  > «crypt docs объясняет архитектурные контракты, математические формулы, потоки данных и интерфейсы управления, а не дублирует репозиторий. Код развивается и оптимизируется; документация фиксирует устойчивые инварианты, форматы конфигураций и готовые к запуску CLI команды. Полный исходный код с тестами доступен непосредственно в репозитории проекта.»
- **Placement**: Documentation philosophy callout on `/overview` and in the CLI overview header.
- **Evidence**: Product Surface Model (Explicit Prohibitions), `docs/agent/frontend_design_subsystem.md`.

---

## 7. Microcopy Rules

Microcopy governs all small, high-frequency user-facing labels, buttons, tooltips, placeholders, and status badges. It ensures every micro-interaction is clear, consistent, and friction-free.

### 7.1 Navigation and Header Microcopy
- **Brand Title**: `crypt docs`
- **Sub-brand Tag**: `Квант-фреймворк`
- **Primary Route Switcher**:
  - Architecture Route: `Архитектура` (Tooltip: `Системная декомпозиция, домены и инварианты`)
  - Learning Route: `Обучение` (Tooltip: `Пошаговое руководство от данных до запуска`)
- **Breadcrumb Separator**: `/` (styled in muted pastel slate)
- **Home Breadcrumb**: `Главная`
- **Sidebar Group Headers**: All caps with leading section number:
  - `01. ОБЗОР`, `02. АРХИТЕКТУРА`, `03. БЭКТЕСТЕР`, `04. СТРАТЕГИИ`, `05. ИСПОЛНЕНИЕ`, `06. ДАННЫЕ`, `07. СПРАВОЧНИК CLI`, `08. КОНФИГУРАЦИЯ`, `09. ЭКСПЛУАТАЦИЯ`, `10. ГЛОССАРИЙ`.
- **Table of Contents (On-Page TOC) Header**: `На этой странице`
- **Scrollspy Indicator**: Active heading receives soft lavender background pill and 2px left border accent.

### 7.2 Search and Command Palette Modal (`Cmd/Ctrl+K`)
- **Header Search Bar Placeholder**: `Поиск по документации... (Cmd+K)`
- **Modal Input Placeholder**: `Введите команду, концепцию или раздел документации...`
- **Keyboard Shortcut Badges**: `Cmd K` (macOS) / `Ctrl K` (Linux/Windows), `Esc` (Закрыть), `↑↓` (Навигация), `↵` (Перейти).
- **Recent Searches Header**: `Недавние запросы`
- **Popular Sections Header**: `Популярные разделы`
- **Search Result Count**: `Найдено результатов: {count}`
- **Empty Search Results State**:
  - Title: `Ничего не найдено по запросу «{query}»`
  - Body: `Попробуйте изменить формулировку, проверить раскладку клавиатуры или выбрать один из ключевых разделов ниже.`
  - Suggested Query Pills: `backtester run`, `dss-v3`, `изолированная маржа`, `deploy_preflight`, `live_positions.json`.
  - Action Button: `Очистить строку поиска`

### 7.3 Tabs and Comparative Views
- **CLI Snippet Tabs**: `Команда (bash)`, `Параметры и флаги`, `Переменные окружения`.
- **Architecture Comparative Tabs**: `Исследования (Backtester)`, `Исполнение (Runtime OKX)`.
- **Execution Clock Tabs**: `H1 WebSocket (Основной)`, `REST Polling (Резервный)`.
- **Active Tab Styling**: High-contrast pastel tab with bottom active indicator; inactive tabs stay muted slate.

### 7.4 Expandable Deep-Dive Accordions
- **Default State Label Pattern**: `Развернуть технические подробности: {Тема}`
- **Expanded State Label Pattern**: `Свернуть подробности`
- **Summary Preview**: One crisp sentence summarizing the underlying mechanism before expanding.

### 7.5 Code and CLI Snippets
- **Command-Only Restriction**: Strictly commands only; no mocked execution logs or simulated stdout.
- **Copy Button (Default)**: `Копировать команду` (Copy icon, fixed container/button width `min-w-[140px]` to eliminate layout jump upon text change)
- **Copy Button (Active / Copied Feedback)**: `Скопировано!` (Checkmark icon, persists for 2000ms with stable container geometry)
- **Prerequisite Flag Helper**: `Обязательно: PYTHONPATH=src`

### 7.6 Empty, Error, and Loading States
- **Page Loading State**: `Загрузка раздела документации...`
- **Component Error Boundary**:
  - Title: `Не удалось отобразить интерактивный компонент`
  - Body: `Произошла ошибка рендеринга блока. Документация доступна в текстовом режиме.`
  - Action: `Попробовать снова` (Retry button)
- **404 Not Found Page**:
  - Code: `404`
  - Title: `Страница потерялась в блоках`
  - Description: `Запрошенный адрес документации не существует, был переименован или перемещен при обновлении структуры фреймворка.`
  - Recovery Actions: `На главную`, `Обзор платформы`, `Открыть поиск (Cmd+K)`.

### 7.7 Maturity Badges
- `stable`: Зеленый пастельный фон, темный текст (`Стабильный компонент / ядро фреймворка`)
- `operational`: Синий пастельный фон, темный текст (`Эксплуатационный / продакшен рантайм`)
- `research`: Лавандовый пастельный фон, темный текст (`Исследовательский модуль / DSS v3`)
- `archived`: Серый/янтарный фон, темный текст (`Устаревший / выведенный из эксплуатации`)

### 7.8 Content Risk and Notice Callouts
- **Критический риск (Critical Risk)**:
  - Header: `Критический риск: реальный счет и капитал`
  - Styling: Pastel red/coral border and background, alert triangle icon.
- **Строгий инвариант (Strict Invariant)**:
  - Header: `Строгий инвариант: нулевое заглядывание вперед`
  - Styling: Pastel purple/lavender border and background, lock/shield icon.
- **Важное примечание (Important Notice)**:
  - Header: `Важное примечание по архитектуре`
  - Styling: Pastel mint/blue border and background, info circle icon.
- **Устаревший компонент (Retired / Archived Component)**:
  - Header: `Архивный компонент: выведено из эксплуатации`
  - Styling: Pastel gray/amber border and background, archive box icon.

---

## 8. Text Inventory Patterns

The Text Inventory Pattern defines concrete, reusable copy schemas for all required page types and repeated components across `crypt docs`. It standardizes the semantic job, text patterns, and copy rules across the portal.

### 8.1 Pattern 1: Page Header and Hero Block
- **Component**: `PageHero` / `DocHeader`
- **Locations**: All 35+ portal routes (`/`, `/overview`, `/architecture/*`, etc.)
- **Category**: Structural Level 1 & Level 2 Text
- **Semantic Job**: Instantly establishes page title, breadcrumb context, architectural maturity, and the primary technical promise.
- **Exact Text Patterns**:
  - Breadcrumb: `Главная / {SectionName} / {PageTitle}`
  - Badge: `{MaturityBadge: stable | operational | research | archived}`
  - Title (`h1`): `{PageTitle}`
  - Lead Paragraph: `2–3 емких предложения, объясняющих назначение подсистемы, ее место в двухдоменной архитектуре и практическую пользу для разработчика.`
- **Starting User State**: Unsure if this page contains the required information.
- **Leaving User State**: Confident in the page scope, knowing what mechanism will be explained.
- **Proof Nearby**: Invariant badge and links to canonical ADRs.
- **Anti-Drift Rule**: Never use generic greetings ("В этом разделе мы поговорим о..."). State the system role directly.

### 8.2 Pattern 2: Two-Domain System Diagram Header & Legends
- **Component**: `ArchitectureMapBlock`
- **Locations**: `/`, `/overview`, `/architecture`, `/architecture/domains`
- **Category**: Level 2 & Level 3 Informational
- **Semantic Job**: Explains the strict separation between the Research Workbench (`src/backtester/`) and Production Runtime (`src/crypt/`).
- **Exact Text Patterns**:
  - Section Heading: `Два изолированных домена: Исследования и Исполнение`
  - Subtitle: `Единый математический базис решений при полной изоляции рантаймов.`
  - Box 1 Header: `Исследовательский веркбенч (src/backtester/)`
  - Box 1 Items: `DSS v3 Поиск сигналов`, `Optuna Оптимизация геометрии`, `ExecutionSim Дискретный симулятор`
  - Box 2 Header: `Боевой рантайм OKX (src/crypt/)`
  - Box 2 Items: `H1 WebSocket Триггер`, `ExchangeSync Сверка стейта`, `Atomic Order Lifecycle`, `Telegram Оповещения`
  - Shared Center Banner: `Единые контракты: модели маржи, формулы риска и правила закрытых свечей`
- **Starting User State**: Confused about where backtesting ends and live trading begins.
- **Leaving User State**: Clear architectural boundary; knows code does not mix simulation with production execution.
- **Proof Nearby**: File path references (`src/backtester/` vs `src/crypt/`).

### 8.3 Pattern 3: Runnable CLI Command Block (Command-Only)
- **Component**: `CliSnippetBlock`
- **Locations**: `/cli/*`, `/learning/*`, `/data-pipeline/backfill`
- **Category**: Level 4 Action Copy & Code
- **Semantic Job**: Provides an instantly copyable, fully runnable bash command with zero ambiguity.
- **Exact Text Patterns**:
  - Block Header: `{CommandName} — {ShortJobDescription}`
  - Pre-command Environment Badge: `Обязательно: PYTHONPATH=src`
  - Runnable Snippet:
    ```bash
    PYTHONPATH=src uv run backtester run \
      --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
      --output results/v6_sol_full
    ```
  - Copy Button: `Копировать команду` -> `Скопировано!` (enforced `min-w-[140px]` fixed button width to avoid layout jump during copy feedback)
  - Argument Description Table: Columns `Параметр`, `Тип`, `По умолчанию`, `Описание действия`.
- **Negative Boundary Constraint**: Displaying mocked, simulated, or captured stdout/stderr terminal output is STRICTLY PROHIBITED. Only executable syntax and argument tables are permitted.
- **Starting User State**: Needs to run a backtest or optimizer without syntax errors.
- **Leaving User State**: Successfully copies command and understands all passed flags.

### 8.4 Pattern 4: Strict Invariant Callout Block
- **Component**: `InvariantCallout`
- **Locations**: `/architecture/invariants`, `/overview`, `/data-pipeline`, `/backtester`
- **Category**: Level 3 & Level 5 Safety Text
- **Semantic Job**: Prevents look-ahead bias and methodological errors by cementing fundamental system rules.
- **Exact Text Patterns**:
  - Badge: `Строгий инвариант`
  - Title: `Нулевое заглядывание вперед: только закрытые свечи (closed=True)`
  - Body: `Все индикаторы, извлечение признаков, правила фильтрации и генерация сигналов рассчитываются исключительно по сформированным закрытым свечам. Формирующаяся свеча используется только как эталон цены следующего открытия (next_open) для моделирования входа.`
  - Reference Link: `Спецификация модели данных: src/crypt/models.py`
- **Starting User State**: Tempted to use forming candles for earlier entries.
- **Leaving User State**: Understands that using unclosed candles destroys simulation validity.

### 8.5 Pattern 5: Critical Live Money Risk Callout Block
- **Component**: `RiskCallout`
- **Locations**: `/execution/*`, `/configuration/startup-validation`, `/strategies/production-portfolio`
- **Category**: Level 3 & Level 5 Safety Text
- **Semantic Job**: Informs operators of capital risk, isolated margin rules, and benchmark status.
- **Exact Text Patterns**:
  - Badge: `Критический риск`
  - Title: `Live-исполнение и статус продакшен-стратегии`
  - Body: `Активный портфель Core v6 работает на реальном счете SOL-USDT-SWAP по прямому решению владельца, несмотря на отклонение от бенчмарка в Phase C (-13.11% против целевых +15%). Торговля фьючерсами сопряжена с риском полной потери маржи. Портал crypt docs не гарантирует доходность и не отображает текущий баланс счета.`
  - Reference Link: `Правила допуска стратегий: docs/strategy_benchmark.md`
- **Starting User State**: Assumes the live strategy is guaranteed to be profitable.
- **Leaving User State**: Fully sober about market risks, historical drawdown, and human-in-the-loop overrides.

### 8.6 Pattern 6: What-to-Read-Next Footer Cards
- **Component**: `ReadNextGrid`
- **Locations**: Bottom of every documentation page
- **Category**: Level 4 Action Navigation
- **Semantic Job**: Preserves reading momentum and guides the user to logical next steps.
- **Exact Text Patterns**:
  - Section Title: `Что читать дальше`
  - Left Card (Sequential / Tutorial): `Следующий шаг: {NextPageTitle}` (Subtitle: `{NextPageSummary}`)
  - Right Card (Architectural Deep-Dive): `Углубленный анализ: {DeepDivePageTitle}` (Subtitle: `{DeepDiveSummary}`)
- **Starting User State**: Finished reading the current page; wondering where to go next.
- **Leaving User State**: Immediately sees two clear, relevant pathways forward.

### 8.7 Pattern 7: Search and Command Palette Modal Item
- **Component**: `CommandPaletteItem`
- **Locations**: Global search overlay (`Cmd+K`)
- **Category**: Level 5 Microcopy & Navigation
- **Semantic Job**: Provides high-density, scannable search hit information.
- **Exact Text Patterns**:
  - Breadcrumb Path: `{SectionName} > {PageTitle}`
  - Match Title: `{MatchedHeadingOrTitle}`
  - Context Highlight: `...совпадение фразы в тексте документации с подсветкой...`
  - Maturity Tag: `{stable | operational | research | archived}`
  - Action Hint: `Нажмите Enter для перехода`
- **Starting User State**: Searching for a specific keyword in a hurry.
- **Leaving User State**: Identifies the exact relevant section within 2 keystrokes.

---

## 9. Anti-Slop Copy Rules

Anti-slop rules protect `crypt docs` from degrading into interchangeable tech-marketing copy, bloated documentation stubs, or vague financial promises.

### 9.1 The Six Universal Anti-Slop Tests
Every paragraph in `crypt docs` must pass these six tests before publication:

1. **The Product Specificity Test**: Could this sentence appear on a competitor's trading bot site, a generic SaaS landing page, or a crypto marketing brochure?
   - *If YES*: Reject and rewrite. Add specific subsystem names (`ExecutionSim`, `DSS v3`, `ExchangeSync`), exact file paths, or mathematical parameters.
2. **The Mechanism Test**: Does the sentence state *how* something happens, rather than just asserting that it is "fast", "powerful", or "reliable"?
   - *Example Bad*: "Наша система быстро исполняет ордера и защищает от сбоев."
   - *Example Good*: "H1 WebSocket триггер подключается к OKX в HH:59:30 UTC, получает подтвержденную свечу confirm=1 и отправляет лимитные стоп-ордера через attachAlgoOrds."
3. **The Proof Near Claim Test**: Is every claim of accuracy or parity backed by a test suite, ADR, or mathematical invariant within the same section?
   - *Rule*: Never claim "биржевой паритет" without naming isolated margin tiers, fee timing, or native trailing stop mechanics.
4. **The Negative Boundary Test**: Does the page respect the strict prohibitions established in the Product Surface Model?
   - *Rule*: Never mention live balances, current open PnL, active wallet equity, multi-exchange support, or quote blocks of raw Python source code.
5. **The Command-Only Snippet Test**: Does every CLI snippet display strictly runnable syntax without simulated terminal progress bars or stdout logs?
   - *Rule*: Never fabricate imaginary terminal execution outputs.
6. **The Calm Tone Test**: Is the text free from hyperbole, exclamation marks, urgent FOMO triggers, and get-rich-quick crypto clichés?
   - *Rule*: Maintain calm, dignified engineering authority at all times.

### 9.2 Concrete Anti-Slop Rewriting Table

| Flawed / Slop Draft | Approved Framework Documentation Copy | Reason for Revision |
|---|---|---|
| "crypt — это революционная платформа для автоматического заработка на крипте с помощью передового ИИ." | "crypt — открытый квант-фреймворк для поиска бессрочных фьючерсных стратегий, исторического моделирования и исполнения на OKX." | Eliminates marketing lies; states exact domain and framework shape. |
| "Наш уникальный бэктестер гарантирует 100% точность и отсутствие ошибок при симуляции." | "ExecutionSim обеспечивает математический паритет с биржей OKX, воспроизводя изолированную маржу, комиссии тейкера и нативный трейлинг." | Replaces impossible perfection claims with concrete modeled mechanisms. |
| "Бот успешно торгует на бирже по лучшей в мире стратегии." | "В продакшене активен мультисигнальный портфель Core v6 на SOL-USDT-SWAP, запущенный по прямому решению владельца." | States actual strategy identity and discloses owner override truthfully. |
| "Кликните сюда, чтобы посмотреть все доступные команды терминала." | "Ознакомьтесь с параметрами команд в Справочнике CLI (/cli/backtester)." | Replaces lazy link text with descriptive, accessible action copy. |
| "В случае сетевой ошибки ничего страшного не произойдет, все под контролем." | "При сетевом сбое ExchangeSync блокирует новые входы, сохраняя открытые позиции под защитой нативных биржевых стоп-ордеров." | Explains the exact failure mode and circuit breaker response. |

---

## 10. Copy Review & Audit Preparation

This section defines the criteria, checklist, and gating progression for independent contract review of `docs/frontend/messaging.md`.

### 10.1 Readiness Declaration
- **Artifact Path**: `docs/frontend/messaging.md`
- **Revision**: 2
- **Status**: proposed (Revision 2)
- **Approval Source**: pending owner approval after re-review
- **Review Reference**: `docs/frontend/reviews/messaging-design-contract-review-2026-09-03.md` (remediated all findings: negative tracking ban, complete downstream gate enumeration, and token alignment)
- **Readiness**: The document is complete, fully source-grounded, covers all required surfaces from `docs/frontend/product-surface-model.md` Revision 2, and is ready for independent contract re-review and progression to downstream visual gates.

### 10.2 Downstream Mandatory Gates
This messaging contract is a foundational architectural specification and does not authorize immediate code implementation. Production frontend implementation is strictly gated by the following sequential pipeline under `docs/agent/frontend_design_subsystem.md`:
1. **Gate O10 (Five raster Visual Direction Boards)**: Exploration and rendering of exactly five raster visual direction boards reflecting the approved playful lo-fi pastel aesthetic with abstract mascots.
2. **Gate O11 (Visual Direction Approval)**: Explicit owner review and sign-off on the selected visual direction board.
3. **Gates O18–O20 (Page-Level Wireframes, HTML Wireframe Artifacts & Wireframe Approval)**: Structural wireframe definition across all pages (O18), generation of persistent interactive HTML wireframe prototypes (O19), and formal wireframe approval sign-off (O20).
4. **Gate O21 (Screen Contracts)**: Comprehensive screen-level contracts specifying components, inputs, outputs, error states, and interaction inventory across all 35+ portal routes.
5. **Gate O25 (Final Implementation Approval)**: Formal owner approval of the complete design-to-code package prior to writing production frontend code in a separate session.
6. **Gate O33 (Independent Frontend QA Gate) & Gate O34 (Independent QA Brief)**: Independent quality assurance audit verifying multi-viewport fidelity across six canonical viewport classes, accessibility, typography, and functional links.

### 10.3 Review Rubric
An independent reviewer must verify:
1. **Source Grounding**: All technical claims match `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md` and repository reality.
2. **Negative Boundaries**: Zero live balances, zero PnL metrics, zero raw code dumps, zero mocked CLI execution outputs, zero multi-exchange claims.
3. **Language Policy**: English metadata, structural contracts, and rules governing authentic, idiomatic Russian content and UI microcopy.
4. **Surface Coverage**: Explicit contracts for Global Shell, Home, Learning, Overview, Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, Glossary, Search, Risk Callouts, and 404 Page.
5. **Anti-Slop Strength**: Concrete criteria and examples eliminating generic crypto and SaaS boilerplate.
6. **Downstream Gate Alignment**: Explicit enumeration and cross-referencing of Gates O10, O11, O18–O20, O21, O25, O33, and O34.
