# Product Surface Model

Status: approved
Revision: 2
Approval: approved by owner
Date: 2026-09-03
Portal Name: crypt docs
Portal Language: Russian (content and interface)
Technology Stack: Next.js + Tailwind CSS

This file is the canonical frontend source of truth for what product the `crypt docs` documentation portal is building. It prevents later agents from reconstructing product requirements from chat, fragmented decisions, or visual drafts.

---

## Canonical Product Source

- **Source path**:
  - Primary backend repository source: `README.md` (lines 1–123), `docs/state/current.yml` (lines 1–54), and `AGENTS.md` (lines 1–96).
  - Independent factual research artifact: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md` (lines 1–525).
- **Source status**:
  - Current for the backend research workbench and OKX live execution engine.
  - First canonical definition for the new frontend documentation portal (`crypt docs`).
- **Frontend reads there for**:
  - Ground-truth subsystem architecture: Research Workbench (`src/backtester/`) vs Production Runtime (`src/crypt/`).
  - Active production strategy: `filtered_donor_portfolio` v6 (`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`) on `SOL-USDT-SWAP`.
  - Strict parity principles: Identical mathematical formulations for sizing, margin, stop loss, take profit, time-to-live (TTL), native trailing stops (`move_order_stop`), and aggregate average entry accounting (`avgPx`).
  - Strict invariants: Only closed candles (`closed=True`) used for signals/features (no look-ahead bias); isolated margin always on; OKX exchange state is source of truth for money, fills, and positions.
  - Active vs retired vs proposed capabilities: Deletion of `crypt.backtest` (ADR-0023); removal of Coinglass (ADR-0016); status of proposed Telegram commands and JSONL telemetry.
- **Frontend-specific delta kept here**:
  - Product positioning, target persona, and job-to-be-done framing for `crypt docs` as a comprehensive framework documentation portal in Russian.
  - Dual navigation model: Architecture Route (system decomposition) and Learning Route (sequential workflow tutorial).
  - Comprehensive page and screen inventory across all 10 required sections.
  - User journeys, interaction specifications, component behaviors, and state definitions.
  - Framework documentation UX conventions (breadcrumbs, sticky sidebar navigation, on-page table of contents with scrollspy, what-to-read-next contextual footers, Cmd/Ctrl+K command palette).
  - Visual identity direction (playful lo-fi pastel aesthetic with abstract mascots, light/dark themes, file-backed content architecture).
  - Strict negative boundaries: Total ban on live account balances, active positions, PnL metrics, and raw source code quotations.
- **Conflicts or stale claims**:
  - `docs/architecture.md` (lines 83, 115–118) still lists retired `src/crypt/backtest/` in its directory tree. Resolved: That package was permanently removed on 2026-06-04 by ADR-0023; all backtesting resides in `src/backtester/`.
  - `docs/architecture.md` (lines 18–20) mentions Bybit/Binance fallback clients. Resolved: The repository only integrates OKX perpetual swaps; multi-exchange support is out of scope.
  - `docs/architecture.md` (lines 170–180) describes a 4h-aligned APScheduler loop. Resolved: Active production execution operates on an hourly (H1) cadence triggered primarily by OKX business WebSocket at `HH:59:30 UTC` (ADR-0051), with REST polling at `*:02 UTC` as fallback.
  - `docs/operations/telegram_commands.md` and `docs/operations/observability.md` describe interactive chat commands and engine-level JSONL telemetry. Resolved: Both are unbuilt proposals; active production uses one-way Russian Telegram notifications and standard Loguru text logging.

---

## Product Surface

### Product Name & Identity
- **Product Name**: `crypt docs`
- **Product Framing**: A comprehensive, modern documentation portal for the `crypt` quantitative crypto trading framework. The portal is presented like official framework documentation (e.g., Next.js, Django, or PyTorch docs), framing `crypt` as an advanced, production-grade quantitative framework for crypto perpetual strategy discovery, exact backtesting, and live execution.
- **Content Language**: Russian (`ru`) for all copy, guides, diagrams, references, tooltips, and navigation labels. Technical terms, identifiers, flags, and code snippets retain their exact English naming with Russian explanatory context.
- **Visual & UI Theme**: Playful lo-fi pastel aesthetic with abstract mascots, clean typography, generous whitespace, and balanced contrast. Full support for Light and Dark themes with seamless switching.
- **Content Storage Architecture**: 100% file-backed directly in frontend repository source files (MDX / TypeScript data structures). No external CMS, database, or network dependency.

### Target Audience
- **Primary Persona**: `developer-crypto-trader`
  - A technical practitioner who combines quantitative trading interests with software engineering discipline.
  - Understands trading concepts (perpetual futures, leverage, isolated margin, funding, slippage, order types, drawdown, Sharpe/Sortino).
  - Understands software concepts (APIs, WebSockets, Python, asyncio, CLI, Docker/containers, CI/CD, Git, state machines).
  - Desires deep architectural clarity and operational transparency without being forced to reverse-engineer thousands of lines of raw Python source code.
  - Values honesty about risk, statistical limits, and operational realities over marketing hype or ungrounded profit promises.

### Jobs to Be Done (JTBD)
- **Primary Job**:
  - "When I explore or operate `crypt`, I want a clear, comprehensive, framework-style Russian documentation portal that explains how every subsystem, invariant, and workflow operates, so that I can confidently understand, research, validate, and execute quantitative strategies without reading raw source code."
- **Secondary Jobs**:
  - *Guided Onboarding*: Step-by-step walkthrough of the entire quantitative lifecycle from historical data ingestion to backtesting, DSS v3 discovery, Optuna optimization, and live execution.
  - *Architectural Clarity*: Clear mental model of the two-domain separation (`src/backtester/` vs `src/crypt/`), data contracts, and execution clock topologies.
  - *Parity Verification*: Detailed explanation of why and how backtest simulations achieve exact behavioral parity with OKX live trading (isolated margin, fees, native trailing stops, aggregate average entry, monthly risk base).
  - *CLI & Command Execution*: Instant access to accurate, copyable CLI command snippets, environment parameters, and arguments for daily research and operations.
  - *Risk & Safety Auditing*: Transparent understanding of critical invariants (closed-candle evaluation, no look-ahead bias, isolated margin rules, circuit breakers, and owner override principles).
  - *Fast Information Discovery*: Rapid keyboard-driven search (Cmd/Ctrl+K) across all curated documentation pages.
  - *Terminology Harmonization*: Clear definitions of project-specific vocabulary via an integrated glossary.

### In Scope
1. **Full Russian-Language Portal Content**:
   - Complete skeleton and deep, substantial curated documentation across all 10 required sections (no placeholder "Lorem Ipsum" or shallow stubs).
2. **Ten Required Content Sections**:
   - `01. Обзор (Overview)`: Project mission, framework framing, historical MVP context, core architectural principles, technology stack.
   - `02. Архитектура (Architecture)`: Two-domain split (`src/backtester/` research vs `src/crypt/` runtime), data contracts, closed-candle invariant, retired module history.
   - `03. Бэктестер (Backtester)`: `ExecutionSim` discrete-event engine, monthly risk-base capital model, isolated margin policy, dynamic safe leverage, fee/slippage models, exit geometry, native OKX trailing parity, aggregate average entry (`avgPx`), instrument precision, canonical regression suite (Full Replay, Phase C).
   - `04. Стратегии (Strategies)`: Strategy registry, active production strategy (`filtered_donor_portfolio` v6 on `SOL-USDT-SWAP`), DSS v3 multi-timeframe search, directional barrier labeling, quality-diversity search backends, Optuna geometry optimization, strategy benchmark targets, owner override principle.
   - `05. Исполнение / Live-трейдинг (Live Execution)`: Hourly WebSocket trigger (`HH:59:30 UTC`) with REST fallback, fast-append latest-bar signal runner cache, atomic order lifecycle (`entry_intent` -> `protected`), market entry with attached algo stops (`attachAlgoOrds`), native OKX `move_order_stop` trailing stops, durable monthly risk-base checkpoints, exchange reconciliation (`ExchangeSync`), safety circuit breakers, blocked-signal auditing (`MISSED SIGNAL`), fill drift alerting, position TTL expiry.
   - `06. Пайплайн данных (Data Pipeline)`: Partitioned Parquet file store under `data/<SYMBOL>/`, strict closed-candle persistence rule (`closed=True`), historical backfill CLI (`python -m crypt.backfill`), deploy preflight checks and corrupt file cleanup (`deploy_preflight.py`), historical data scope (OKX native; Coinglass dropped).
   - `07. Справочник CLI (CLI Reference)`: Runnable syntax, arguments, environment flags, and copyable snippets for `backtester run`, `backtester optimize`, `backtester search-signals`, `backtester search-signals-matrix`, `python -m crypt`, and `python -m crypt.backfill` (strictly displaying commands and arguments only; mock or captured terminal execution output and runtime stdout/stderr logs are excluded).
   - `08. Конфигурация (Configuration)`: Configuration hierarchy (Environment variables via `pydantic-settings`, Strategy JSON configs as source of truth for money parameters, startup pre-trade validation against `backtest_args`, uncalibrated legacy YAML weights).
   - `09. Эксплуатация (Operations)`: Railway container deployment runbook, persistent volume (`/app/data`), logging via Loguru, background health checks, operator Telegram notification contracts (8 event types), CI/CD quality checks.
   - `10. Глоссарий (Glossary)`: Definitive definitions for domain terms (Core v4/v6, DSS v3, QD, ExecutionSim, Monthly Risk Base, Isolated Margin, Native OKX Trailing, Instrument Precision Policy, Aggregate Average Entry, Fill Drift, H1 WebSocket Trigger, Sinks, Regime, etc.).
3. **Dual Navigation Routes**:
   - *Architecture Route*: Structural decomposition designed for quantitative developers and systems architects exploring components, modules, and boundaries.
   - *Learning Route*: Step-by-step guided reading journey designed for practitioners wanting an end-to-end tutorial through the framework.
4. **Rich Framework Documentation Features**:
   - Breadcrumb navigation path on all documentation pages.
   - Sticky hierarchical sidebar navigation with section grouping and maturity badges.
   - Desktop on-page table of contents (TOC) with scrollspy highlighting.
   - What-to-read-next contextual navigation cards at the bottom of every page.
   - Full-text search with header input field and global Cmd/Ctrl+K command palette modal.
   - Interactive components: data/decision flow diagrams, tabbed comparative views, expandable deep-dive accordions, filterable tables, copyable code blocks.
   - Explicit section maturity badges: `stable`, `research`, `operational`, `archived`.
   - Prominent risk callout boxes for high-stakes topics: Live Money, OKX Execution, Configuration, No Look-Ahead Bias.
   - Dedicated 404 / Not Found error page (`/not-found`) with playful lo-fi lost-mascot illustration, Russian error copy, quick recovery navigation links (Home, Overview), and integrated search trigger.
   - Light and Dark theme toggle.

### Out of Scope (Explicit Prohibitions)
1. **NO LIVE ACCOUNT METRICS OR RESULTS**:
   - The portal must **never** connect to live exchange accounts, query live balances, or display active positions, live equity curves, open orders, real-time PnL, or live performance metrics.
   - Live Execution content is strictly limited to explaining architecture, lifecycle state machines, order safety mechanisms, and operational guarantees.
2. **NO RAW SOURCE CODE QUOTATIONS**:
   - The portal does not replicate or quote blocks of Python source code from the repository. It explains principles, logic, algorithms, and architectures using clear framework-level prose, structured diagrams, parameter tables, and CLI snippets.
3. **NO EXTERNAL CMS OR DATABASE**:
   - No Strapi, Sanity, Contentful, PostgreSQL, or Redis. Content is entirely managed in source files (MDX / TypeScript / JSON) checked into git.
4. **NO TRADING OR BACKTEST EXECUTION FROM THE PORTAL**:
   - The portal is a static/jamstack informational documentation site. It cannot trigger live trades, launch backtest processes, run Optuna, or dispatch API requests to Railway or OKX.
5. **NO MULTI-EXCHANGE CLAIMS**:
   - The portal must not claim support for Binance, Bybit, Coinbase, or decentralized exchanges. It documents OKX perpetual swap integration exclusively.
6. **NO FALSE PRESENTATION OF PROPOSED FEATURES**:
   - Interactive Telegram bot commands (`/status`, `/trade`, `/pnl`) and per-engine microsecond JSONL telemetry must not be presented as active production capabilities. They are documented strictly as proposed or absent where relevant.
7. **NO CLAIMS OF AUTOMATIC STRATEGY PROMOTION**:
   - Direct Signal Search v3 must be accurately described as an automated research discovery tool, not an autonomous production trading engine. Strategy promotion is strictly human-in-the-loop.
8. **NO CLAIMS OF BENCHMARK COMPLIANCE FOR PRODUCTION STRATEGY**:
   - The documentation must explicitly state that the active production portfolio v6 operates via explicit owner override despite failing benchmark floors.
9. **NO TERMINAL EXECUTION OUTPUT OR MOCKED CLI RESULTS**:
   - Terminal & CLI snippets must contain only runnable command syntax, flags, and arguments. Displaying mocked, simulated, or captured stdout/stderr terminal execution output/results is strictly prohibited across all components and documentation pages to prevent stale, misleading, or ungrounded claims.

---

## Required Pages and Screens

| Page Route | Title (Russian) | Section | Purpose & Content Scope | Maturity Badge |
|---|---|---|---|---|
| `/` | `crypt docs: Главная` | Portal Root | Project introduction, framework identity, high-level architecture diagram, guided entrypoints (Architecture Route vs Learning Route), key principles, search entrypoint. | `stable` |
| `/overview` | `Обзор платформы` | Overview | Quantitative workbench + OKX execution framing, historical MVP context (retired H4 ensemble), design principles, tech stack (`uv`, Python 3.12, OKX, Pandas, PyArrow, Optuna). | `stable` |
| `/learning` | `Обучающий маршрут` | Learning | Guided tutorial index: end-to-end walkthrough from historical data backfill to live trading execution. | `stable` |
| `/learning/01-data-ingestion` | `1. Сбор и подготовка данных` | Learning | Tutorial step 1: running backfill, understanding Parquet storage, closed-candle invariant, preflight checks. | `stable` |
| `/learning/02-backtesting` | `2. Историческое моделирование` | Learning | Tutorial step 2: running `backtester run`, analyzing metrics, isolated margin, fees, native trailing parity. | `stable` |
| `/learning/03-signal-discovery` | `3. Поиск сигналов (DSS v3)` | Learning | Tutorial step 3: multi-timeframe search, directional barrier labeling, QD archives, candidate selection. | `research` |
| `/learning/04-optimization` | `4. Оптимизация геометрии (Optuna)` | Learning | Tutorial step 4: running `backtester optimize`, resolving RRR, TTL, risk %, trailing ATR, TP move. | `stable` |
| `/learning/05-live-deployment` | `5. Запуск в продакшене` | Learning | Tutorial step 5: Railway container deployment, `.env` configuration, dry-run smoke, Telegram monitoring. | `operational` |
| `/architecture` | `Системная архитектура` | Architecture | Two-domain system map (`src/backtester/` vs `src/crypt/`), data boundaries, memory & execution topologies, retired components. | `stable` |
| `/architecture/domains` | `Домены: Исследования и Исполнение`| Architecture | Detailed boundary between the pure research workbench and the continuous live execution runtime. | `stable` |
| `/architecture/invariants` | `Инварианты и гарантии` | Architecture | Fundamental system invariants: closed candles only, no look-ahead bias, isolated margin, exchange authority. | `stable` |
| `/backtester` | `Архитектура бэктестера` | Backtester | Overview of `ExecutionSim`, discrete-event simulation, parity objectives, candle vs minute execution models. | `stable` |
| `/backtester/parity-mechanics` | `Механика паритета с биржей` | Backtester | Detailed breakdown: isolated margin policy, fee timing, native trailing stop parity (`move_order_stop`), aggregate average entry (`avgPx`). | `stable` |
| `/backtester/risk-model` | `Модель капитала и риска` | Backtester | Monthly risk-base capital model (ADR-0019/ADR-0059), position sizing via `BasicRiskModel`, leverage calculation. | `stable` |
| `/backtester/regression` | `Регрессионные чекпоинты` | Backtester | Canonical test suites: Full Replay (1564 trades, 2021–2026), Strict Phase C checkpoint (warmup vs accounting split). | `stable` |
| `/strategies` | `Реестр и архитектура стратегий`| Strategies | Overview of `src/backtester/registry.py`, strategy contracts, signal generation interfaces. | `stable` |
| `/strategies/production-portfolio`| `Активная стратегия (Core v6)` | Strategies | Filtered donor portfolio architecture, donor components, tail-control filtering (`drop_negative_v5`), risk parameters. | `operational` |
| `/strategies/dss-v3` | `Direct Signal Search v3` | Strategies | Multi-timeframe search engine, directional barrier labeling, frequency classes (`sparse` to `frequent`), QD backends. | `research` |
| `/strategies/optuna-optimizer` | `Оптимизация параметров (Optuna)`| Strategies | Downstream geometry search, trial budgets, parameter spaces (RRR, TTL, risk %, trailing ATR, TP move). | `stable` |
| `/strategies/benchmark` | `Бенчмарк и правила допуска` | Strategies | Target metrics ($10k capital, +15% monthly floor, max -10% drawdown) and the owner override principle. | `stable` |
| `/execution` | `Live-исполнение на OKX` | Live Execution | Orchestrator architecture (`LiveExecutionManager`), dual clock triggers (WebSocket + REST fallback), runtime safety. | `operational` |
| `/execution/order-lifecycle` | `Жизненный цикл ордеров` | Live Execution | State machine: `entry_intent` -> `entry_submitted` -> `entry_filled` -> `protected` -> `closing` -> `closed`. | `operational` |
| `/execution/native-trailing` | `Нативный трейлинг OKX` | Live Execution | `move_order_stop` algorithmic order integration, entry activation price, ATR-derived callback spread. | `operational` |
| `/execution/safety-and-sync` | `Защитные барьеры и синхронизация`| Live Execution | `ExchangeSync` reconciliation, durable state persistence (`live_positions.json`), blocked-signal audit, fill drift policy. | `operational` |
| `/data-pipeline` | `Пайплайн и хранилище данных` | Data Pipeline | Storage topology under `data/<SYMBOL>/`, Parquet file partitioning, schema versioning, closed-candle invariant. | `stable` |
| `/data-pipeline/backfill` | `Утилита бэкфилла` | Data Pipeline | `python -m crypt.backfill` architecture, supported data types (OHLCV, 1m, OI, L/S ratio, taker volume), idempotency. | `stable` |
| `/data-pipeline/preflight` | `Deploy Preflight Check` | Data Pipeline | Integrity verification, 0-byte file cleanup, coverage staleness thresholds, auto-backfill triggers. | `operational` |
| `/cli` | `Справочник команд CLI` | CLI | Central CLI hub, global environment flags (`PYTHONPATH=src`, `UV_CACHE_DIR`), argument conventions; snippets display executable commands only with zero captured output. | `stable` |
| `/cli/backtester` | `Команды бэктестера` | CLI | Detailed syntax and copyable snippets for `backtester run`, `optimize`, `search-signals`, `search-signals-matrix` (runnable command syntax only; execution outputs/results omitted). | `stable` |
| `/cli/runtime` | `Команды рантайма и бэкфилла` | CLI | Detailed syntax and copyable snippets for `python -m crypt` and `python -m crypt.backfill` (runnable command syntax only; stdout/stderr execution output omitted). | `stable` |
| `/configuration` | `Конфигурация системы` | Configuration | Hierarchical settings model: `.env` (`Settings`, `ExecutionSettings`), Strategy JSON source of truth, YAML weights. | `stable` |
| `/configuration/startup-validation`| `Pre-trade валидация параметров`| Configuration | Startup check comparing `.env` fallback settings with Strategy JSON `backtest_args` to prevent configuration drift. | `operational` |
| `/operations` | `Эксплуатация и развертывание` | Operations | Deployment on Railway, persistent volume mounts, Loguru logging, health-check heartbeats, CI/CD pipelines. | `operational` |
| `/operations/telegram-alerts` | `Уведомления Telegram` | Operations | Presentation contracts for 8 Russian operator event types, delivery resilience, blocked-signal reporting. | `operational` |
| `/glossary` | `Глоссарий терминов` | Glossary | Comprehensive A–Z searchable dictionary of quantitative, architectural, and operational terms. | `stable` |
| `/not-found` | `404: Страница не найдена` | Global Error | Friendly 404 screen with lo-fi lost-mascot illustration, explanation in Russian, quick links to Home and Overview, and search trigger. | `stable` |
| `[Modal]` | `Поиск по документации (Cmd+K)` | Global Overlay | Full-text search palette over curated page content with maturity badges, section breadcrumbs, and keyboard navigation. | `stable` |

---

## Required Journeys

### Journey 1: Developer-Trader Guided Onboarding (Learning Route)
- **Actor**: Developer-crypto-trader exploring `crypt` for the first time.
- **Entry**: Lands on `/` (Home), reads framework overview, clicks "Начать обучение" (Start Learning Route).
- **Steps**:
  1. Arrives at `/learning` and views the 5-step curriculum progress bar.
  2. Proceeds to `/learning/01-data-ingestion`: learns how Parquet files store closed candles, runs sample `crypt.backfill` command, reads preflight sanity checks.
  3. Advances via "Что читать дальше" (What to Read Next) to `/learning/02-backtesting`: understands `ExecutionSim`, executes a historical replay command, inspects win rate, profit factor, and drawdown.
  4. Advances to `/learning/03-signal-discovery`: learns how DSS v3 searches triggers and filters via directional barrier labeling without look-ahead bias.
  5. Advances to `/learning/04-optimization`: learns how Optuna tunes money geometry (RRR, TTL, trailing stop distance).
  6. Concludes at `/learning/05-live-deployment`: understands dry-run smoke testing, Railway container startup, and Telegram alert monitoring.
- **Outcome**: The user gains a coherent, end-to-end understanding of how raw data turns into validated live execution without seeing fragmented source code.

### Journey 2: Systems Architect Subsystem Deep-Dive (Architecture Route)
- **Actor**: Experienced Python backend engineer or quant developer evaluating system design and reliability.
- **Entry**: Clicks "Архитектура" in header navigation.
- **Steps**:
  1. Views interactive two-domain system diagram (`src/backtester/` vs `src/crypt/`) on `/architecture`.
  2. Dives into `/architecture/invariants` to examine the closed-candle rule, zero-byte file protection, and isolated margin enforcement.
  3. Navigates to `/backtester/parity-mechanics` to audit how `ExecutionSim` achieves parity with OKX live trading (isolated margin tiers, taker fees on limit TPs, native `move_order_stop` trailing stops, aggregate average entry `avgPx`).
  4. Follows cross-link to `/execution/order-lifecycle` to examine the atomic state machine and `data/live_positions.json` persistence.
  5. Reviews `/execution/safety-and-sync` to inspect `ExchangeSync` reconciliation rules and blocked-signal auditing (`MISSED SIGNAL`).
- **Outcome**: The architect thoroughly verifies that the system has institutional-grade parity, robust circuit breakers, and zero look-ahead bias.

### Journey 3: CLI & Runbook Operator (Reference Route)
- **Actor**: Operator or developer running backtests, optimizer runs, or data backfills from the terminal.
- **Entry**: Presses `Cmd+K` from any screen, types "optimize" or "backfill", and presses Enter.
- **Steps**:
  1. Lands directly on `/cli/backtester` at the `#backtester-optimize` anchor.
  2. Reads parameter table: `--strategy`, `--output`, `--n-trials`, default values, and environment prerequisites (`PYTHONPATH=src`, `UV_CACHE_DIR=/tmp/uv-cache`).
  3. Clicks "Копировать команду" (Copy Command) on a copyable snippet.
  4. Clicks an inline cross-link to `/strategies/optuna-optimizer` to check search parameter ranges.
- **Outcome**: The operator executes accurate terminal commands without guessing parameter names or reviewing source code.

### Journey 4: Parity & Safety Auditor (Parity & Risk Deep-Dive)
- **Actor**: Risk auditor or trader checking whether live money execution deviates from historical backtests.
- **Entry**: Navigates from `/overview` via a prominent "Границы безопасности и риски" (Safety & Risk Callout).
- **Steps**:
  1. Inspects risk callout boxes on `/architecture/invariants`.
  2. Reads `/backtester/parity-mechanics` regarding entry fee timing, isolated margin liquidation buffers, and worst-case intrabar trailing stop evaluation.
  3. Navigates to `/execution/safety-and-sync` to read about fill drift alerting (`Цена входа отличается от плана`, ADR-0054) and monthly risk-base checkpoint continuity (`YYYY-MM.json`, ADR-0059).
  4. Reviews `/strategies/benchmark` to confirm that the active production strategy operates via explicit owner override despite failing benchmark floors.
- **Outcome**: The auditor confirms that all live execution risks, drifts, and margin policies are documented transparently and protected by fail-safe circuit breakers.

---

## Required States

### 1. Global Visual Theme States
- **Light Theme**: Soft pastel background (pale ivory/cream), dark charcoal typography, pastel accent highlights (soft lavender, mint, warm peach), high-contrast code snippets.
- **Dark Theme**: Deep slate/charcoal background, crisp off-white typography, glowing pastel neon accents, dark code snippet backgrounds with syntax highlighting.
- **System Preference**: Default state automatically detects `prefers-color-scheme`, allows explicit user toggle stored in `localStorage`.

### 2. Navigation States
- **Desktop Sidebar Navigation**:
  - *Section Expanded/Collapsed*: Accordion toggles for each of the 10 sections.
  - *Active Route Highlighting*: Distinct pastel pill background and accent bar for the currently viewed page.
  - *Maturity Badge*: Visible next to each page link (`stable`, `research`, `operational`, `archived`).
- **Desktop On-Page Table of Contents (TOC)**:
  - *Scrollspy Active Heading*: Dynamically updates as the user scrolls through page sections.
  - *Nested Hierarchy*: Subheadings (`h2`, `h3`) indented with smooth scroll on click.
- **Mobile Navigation Drawer**:
  - *Closed State*: Discreet hamburger icon in header.
  - *Open State*: Full-screen slide-over drawer with dual-route switch (Architecture vs Learning), section tree, and theme toggle.

### 3. Search Palette States (`Cmd/Ctrl+K`)
- **Closed State**: Triggered by header search bar click or `Cmd+K` / `Ctrl+K` shortcut.
- **Open Initial State**: Search modal overlays content with backdrop blur; displays recent searches and popular section shortcuts (Overview, CLI, Backtester).
- **Query Typing / Debounced Search**: Fast in-memory search over curated page headers, content paragraphs, and glossary terms.
- **Results Populated**: Results grouped by section with breadcrumb path, title, matching snippet highlight, and section maturity badge.
- **Empty Results State**: Friendly lo-fi mascot illustration with "Ничего не найдено" (Nothing found) message and suggested query alternatives.
- **Keyboard Navigation State**: Active result highlighted via arrow up/down keys; Enter key navigates; Escape closes modal.

### 4. Interactive Component States
- **Tabbed Panels** (e.g. CLI examples, comparative architecture flows):
  - *Default Tab Active*: First tab highlighted with active indicator.
  - *Tab Switch*: Instant content transition without page jump.
- **Expandable Deep-Dive Accordions**:
  - *Collapsed State*: Clean header with preview summary and chevron indicator.
  - *Expanded State*: Smooth expansion revealing technical operational details, mathematical formulas, or edge cases.
- **Filterable Lists** (e.g. CLI argument matrices, Glossary, Strategy Registry):
  - *Unfiltered State*: Complete alphabetical or categorical list.
  - *Filtered State*: Real-time filtering by search term or category badge; "Сбросить фильтры" (Reset filters) button when zero matches occur.
- **Code Snippet Blocks**:
  - *Command-Only Constraint*: Terminal & CLI snippets must contain only runnable command syntax, flags, and arguments; displaying mocked, captured, or simulated stdout/stderr terminal execution output/results is strictly prohibited across all components and documentation pages.
  - *Default State*: Monospace font, syntax highlighting, clear distinction of command vs parameters.
  - *Hover State*: Copy icon button appears in top-right corner.
  - *Copied State*: Temporary checkmark icon and "Скопировано!" (Copied!) feedback tooltip for 2 seconds.

### 5. Content Risk & Warning Callouts
- **Risk Callout (Критический риск)**: Red/coral pastel callout box with warning icon for live money risks, OKX API execution, and configuration discrepancies.
- **Invariant Callout (Строгий инвариант)**: Purple/lavender callout box for no look-ahead bias and closed-candle requirements.
- **Notice Callout (Важное примечание)**: Mint/blue callout box for architectural nuances, owner overrides, and operational tips.
- **Archived / Retired Callout (Устаревший компонент)**: Gray/amber callout box explicitly marking retired subsystems (e.g. `src/crypt/backtest/`, Coinglass integration) to prevent confusion.

### 6. Error & Fallback States
- **404 / Not Found State (`/not-found`)**: Dedicated route and catch-all error boundary with playful lo-fi lost-mascot illustration, clear Russian explanation, search palette trigger, and direct navigation links back to Home (`/`) and Overview (`/overview`).
- **System Error Boundary State**: Client-side component error boundary rendering a recoverable fallback card with a "Попробовать снова" (Retry) action without full page reload.

---

## Source-of-Truth Boundaries

1. **Portal Content Source of Truth**:
   - The documentation content authored in the frontend repository (MDX / TypeScript / JSON files) is the canonical source of truth for the public presentation, structure, user guides, and tutorials of `crypt docs`.
   - Content must strictly conform to verified facts established in `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`.
2. **Backend Engine Source of Truth**:
   - For strategy logic, simulation math, margin models, and backtest results, the source of truth is the Python codebase (`src/backtester/`, `src/crypt/`), canonical regression suite (`docs/backtester_regression.md`), and strategy JSON files (`strategies/`).
   - The documentation portal explains these mechanics faithfully but does not define or alter them.
3. **Live Money & Runtime Source of Truth**:
   - For live production trading, the sole sources of truth are:
     - Runtime environment configuration: `EXECUTION_STRATEGY_CONFIG` and loaded `.env` variables (`src/crypt/execution/settings.py`).
     - Exchange state: OKX fills, orders, fees, positions, and account equity.
     - Persistent runtime files: `data/live_positions.json` and `risk_base_checkpoints/YYYY-MM.json`.
   - The documentation portal never participates in live trading execution, never overrides runtime config, and never reports live financial state.

---

## Risk and Safety Boundaries

1. **Absolute Live Data Prohibition**:
   - The portal must never display live account balances, active positions, PnL curves, live trade executions, or exchange credentials.
   - Any live execution page must clearly state: "Этот раздел описывает архитектурные гарантии и алгоритмы исполнения. Портал документации не отображает текущие позиции, балансы или результаты реального счета."
2. **Strict Look-Ahead Bias Invariant**:
   - Every discussion of feature extraction, indicators, DSS v3 signal generation, and strategy evaluation must emphasize that calculations use strictly closed candles (`closed=True`).
   - The portal must clearly explain that the forming candle open is used solely as the execution `next_open` reference price.
3. **Transparent Operational Risks**:
   - The portal must openly document that production portfolio v6 failed the benchmark target during Phase C testing (-13% return vs +15% target) and runs in production strictly via explicit owner override.
   - Execution risks such as fill drift (`Цена входа отличается от плана`), liquidation buffers, and WebSocket fallback behaviors must be clearly articulated.
4. **No Unimplemented Features Presented as Active**:
   - Interactive Telegram bot commands (`/status`, `/trade`) and per-engine microsecond JSONL telemetry must be explicitly labeled as proposed or absent, preventing operators from attempting to use unbuilt features.

---

## Open Owner Decisions

1. **Decision 1: Next.js Content Structure**:
   - *Option A (Recommended)*: Next.js App Router with `@next/mdx` or local MDX components, structured by route folders (`app/(docs)/overview/page.mdx`), providing native React component embedding and fast static compilation.
   - *Option B*: Next.js App Router with unified local Content Collections / Velite / Contentlayer-style typed content definitions, separating raw markdown files into a `content/` folder.
2. **Decision 2: Client-Side Full-Text Search Engine**:
   - *Option A (Recommended)*: Client-side Minisearch or FlexSearch indexing pre-built JSON search manifests generated at build time, enabling zero-network, sub-10ms Cmd+K search without external binaries.
   - *Option B*: Pagefind static search engine executed during build time, serving static search indexes.
3. **Decision 3: Playful Lo-Fi Pastel Visual Design Tokens**:
   - Finalizing the precise pastel palette (soft lavender `#E8E5F6`, mint `#E3F5E9`, pastel coral `#FCECE9`, pale cream `#FAF9F5`, deep charcoal `#1E2024`) and selecting the style for abstract mascot illustrations (e.g. geometric crypto-critters guiding the user through sections).
4. **Decision 4: Diagram Rendering Approach**:
   - *Option A (Recommended)*: Bespoke React SVG diagram components styled with Tailwind CSS utility classes and design tokens, ensuring zero external client runtime, instant render, and seamless light/dark theme switching.
   - *Option B*: Build-time or client-rendered Mermaid.js diagrams embedded via MDX plugins.

---

## Artifact Sources

- **Owner Onboarding Answers**:
  - Source: Task brief and owner specifications (2026-09-03).
  - Scope confirmed: Russian documentation portal (`crypt docs`), Next.js + Tailwind, developer-crypto-trader audience, architecture + learning routes, framework docs format without raw code quotes, full search (Cmd+K), 10 required sections, interactive diagrams/tabs, copyable CLI snippets without outputs, architectural guarantees without live balances/positions, light/dark themes, playful lo-fi pastel style with abstract mascots, risk callouts, maturity statuses, full first release skeleton.
- **Independent Factual Research Artifact**:
  - Source path: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md` (lines 1–525).
  - Content accepted: Complete system map, 10-subsystem breakdown, real runtime paths, active vs retired vs proposed capabilities, source-of-truth references, code contradictions, negative boundary rules.
- **Supporting Canonical Sources**:
  - `README.md` (lines 1–123): Repository framing and quick-smoke CLI examples.
  - `docs/state/current.yml` (lines 1–54): Compact current state, production strategy path, Phase C boundary.
  - `AGENTS.md` (lines 1–96): Operating rules, closed-candle invariant, owner override authority.
  - `docs/architecture.md` (lines 1–213): System architecture and domain separation.
  - `docs/execution/live_execution.md` (lines 1–604): Complete live execution, order lifecycle, and safety specification.
  - `docs/backtester_regression.md` (lines 1–163): Canonical regression replay benchmarks.
  - `docs/discovery/direct_signal_search_v3.md` (lines 1–385): Direct Signal Search v3 specification.
  - `docs/cli.md` (lines 1–137): Owner-facing CLI runbook.
  - `docs/deploy/railway.md` (lines 1–225): Railway container deployment runbook.
  - `docs/strategy_benchmark.md` (lines 1–113): Mandate benchmark criteria.
- **Independent Contract Review Artifact**:
  - Source path: `docs/frontend/reviews/product-surface-contract-review-2026-09-03.md` (lines 1–171).
  - Reviewer: Independent Frontend Lead Contract Reviewer (`task_da7dc5b490a7`, dispatch `ctx_9e5ccc970aaf`, terminal `term_668cc1a5-f3f0-4d62-8ef9-b5912e10075b`).
  - Verdict: `pass-with-fixes` (1 blocking, 3 non-blocking findings resolved in Revision 2).
- **Product Surface Author Context**:
  - Revision 1: `task_fba2e2cb878b`, dispatch `ctx_e25333e8f4b0`, terminal `term_07a19ef4-dd73-45bb-a04b-3ceb3091d9d0`.
  - Revision 2: `task_ccaf1ad3d3a0`, dispatch `ctx_b15052bf0745`, terminal `term_ef39ff94-44b0-4bdb-8d15-57b427e693a1`.
- **Product Surface Contract Reviewer Context**:
  - Independent Frontend Lead Contract Reviewer (`task_da7dc5b490a7`, dispatch `ctx_9e5ccc970aaf`, terminal `term_668cc1a5-f3f0-4d62-8ef9-b5912e10075b`).
- **Accepted Factual Map & Line Index**:
  - Subsystems and architecture: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, lines 10–269.
  - Real runtime/user paths: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, lines 270–378.
  - Capability status table: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, lines 379–423.
  - Negative documentation boundaries: `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, lines 495–525.
- **Rejected or Unresolved Facts**:
  - `src/crypt/backtest/` harness: rejected (deleted via ADR-0023).
  - Coinglass data provider: rejected (dropped via ADR-0016).
  - Interactive Telegram bot commands: rejected as active; treated as proposed/absent.
  - Microsecond engine JSONL telemetry: rejected as active; treated as proposed/absent.
  - Paper trading ledger sink: rejected as active; treated as proposed/absent.
  - Forming candle look-ahead: rejected; strictly closed candles enforced.
  - Live account metrics: strictly excluded from frontend scope.
- **Related Decisions**:
  - ADR-0005: Parquet partitioned local storage without relational DBs.
  - ADR-0008: Exclusion of order book / tape data.
  - ADR-0013: Avoidance of Python 3.12 stdlib `crypt` collision via `PYTHONPATH=src`.
  - ADR-0016: Elimination of Coinglass endpoints in favor of OKX native.
  - ADR-0019 / ADR-0059: Durable monthly risk-base checkpoints (`YYYY-MM.json`).
  - ADR-0023: Permanent retirement of legacy `src/crypt/backtest/`.
  - ADR-0026 / ADR-0029 / ADR-0049: Isolated margin always on and dynamic safe leverage calculation.
  - ADR-0050: Native OKX trailing stop (`move_order_stop`) parity.
  - ADR-0051: H1 WebSocket candle trigger (`HH:59:30 UTC`) with REST fallback.
  - ADR-0052: Fast-append latest-bar signal runner cache.
  - ADR-0053: Versioned instrument precision policies and entry fee timing.
  - ADR-0054: Fill drift treated as observability alert, not order abort.
  - ADR-0058: OKX aggregate average entry (`avgPx`) accounting for blended positions.
  - ADR-0062: Direct Signal Search v3 multi-timeframe directional barrier labeling.

---

## Approval Record

### Revision 1 (2026-09-03)
- **Status**: reviewed (verdict: pass-with-fixes)
- **Review Artifact**: `docs/frontend/reviews/product-surface-contract-review-2026-09-03.md`
- **Findings Addressed**: 1 blocking finding (Polars dependency contradiction), 3 non-blocking findings (missing 404 route, CLI snippet output suppression rule, diagram rendering technology decision).

### Revision 2 (2026-09-03)
- **Status**: approved
- **Decision**: approved
- **Owner message or waiver**: Owner approved in chat with message `апрув` after Revision 2 passed independent re-review.
- **Date**: 2026-09-03
- **Next phase unlocked**: Messaging, Design Identity, Design System, flows, wireframes, and screen contracts for the approved `crypt docs` product surface.
