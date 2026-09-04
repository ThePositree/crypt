# Product Surface Model

Status: ready for owner approval
Revision: 1
Approval: pending owner decision (Product Surface Approval)

This document is the canonical frontend source of truth for the `crypt docs` documentation portal. It defines the product boundaries, audience jobs, route and page model, interaction affordances, risk classifications, states, source map, and approval gates.

---

## Canonical Product Source

- **Source paths:**
  - `README.md` — Core repository framing, stack, setup, and short CLI runbook.
  - `AGENTS.md` — Agent operating rules, core invariants, parity contracts, and language policy.
  - `docs/state/current.yml` — Current active strategy configuration, deployment state, and production reconciliation status.
  - `docs/architecture.md` — High-level system architecture, engine boundaries, and module map.
  - `docs/strategy_benchmark.md` — Quantitative strategy target, money benchmarks, and risk evaluation rules.
  - `docs/execution/live_execution.md` — Live execution runtime spec, parity contract, OKX integration, and risk-base continuity.
  - `docs/cli.md` — Owner-facing CLI runbook and parameter defaults.
  - `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md` — D3 P01 Task Contract and Owner Onboarding Answers.
  - `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md` — D3 P02 Factual Research and Section Source Map.
- **Source status:** current and verified.
- **Frontend reads there for:** Domain concepts, algorithm flows, data pipelines, CLI commands, execution safety invariants, and configuration parameters.
- **Frontend-specific delta kept here:** Route and page tree, interactive UI affordances (search, command palette, tabs, expandable diagrams, copyable snippets), visual navigation structure (breadcrumbs, sidebar, desktop TOC, "what to read next"), maturity badges, risk callouts, user journeys, responsive viewports, and page states.
- **Conflicts or stale claims:** None. The historical signal-only Telegram alert MVP is strictly classified as archived historical context, not active product framing.

---

## Product Surface

- **Product name:** `crypt docs`
- **Product type:** Large framework documentation portal.
- **Tech stack:** Next.js + Tailwind CSS.
- **Language policy:** Russian for all user-visible UI copy, navigation, explanations, and guides; English for code identifiers, CLI flags, configuration keys, and repository documentation artifacts.
- **Target audience:** Developer-crypto-traders (разработчики-криптотрейдеры) — engineers and quantitative traders who want to understand, backtest, research, or operate automated perpetual strategies on OKX.
- **Primary job:** Explain comprehensively how the `crypt` codebase works as a crypto-trading framework and live execution engine without guessing or digging through thousands of lines of code.
- **Secondary jobs:**
  - Guide new developers to their first working smoke backtest within 5 minutes.
  - Provide an instant, copyable reference for CLI commands, flags, and configuration variables.
  - Explain the pure decision pipeline and strict parity between backtester and live execution.
  - Document the DSS v3 strategy discovery engine, Optuna exit-geometry optimization, and donor portfolio construction.
  - Provide operational runbooks for live OKX execution, monthly risk-base anchors, and incident response.
  - Enable instant full-content search via header search and `Cmd/Ctrl+K` command palette.

- **In scope:**
  - Next.js + Tailwind CSS static/SSG documentation portal.
  - Russian language interface and documentation content.
  - 10 core sections: Overview, Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.
  - Full-content search engine accessible via header input and `Cmd/Ctrl+K` modal palette.
  - Dual navigation model: subsystem/architecture-first left sidebar and guided learning tracks.
  - Page-level chrome: breadcrumbs, hierarchical sidebar, sticky desktop on-page Table of Contents (TOC), and "Что читать дальше" (What to read next) transition cards at the bottom of every page.
  - Interactive affordances:
    - Expandable SVG / interactive flow diagrams (e.g. dataflow, decision pipeline, live order lifecycle).
    - Code and configuration tabs (e.g. CLI vs Python API; .env vs JSON).
    - Filterable catalogs for strategies, glossary terms, and CLI commands.
    - Copyable command buttons with visual confirmation ("Скопировано!").
  - Dark and Light themes with seamless toggle (dark theme default).
  - Playful lo-fi visual identity with abstract geometric mascots (representing pure decision logic, risk shield, and candle observer).
  - Prominent risk callout badges: Live Money, OKX Execution, Configuration Safety, No Look-Ahead Bias.
  - Maturity badges: Stable, Research, Operational, Archived.

- **Out of scope (strict non-goals):**
  - Displaying live account balances, active positions, real-time equity, or live PnL.
  - Triggering live trades, modifying positions, or mutating external exchange state from the web UI.
  - A database-backed or headless Content Management System (CMS) — all content is statically authored in repository source files.
  - Raw source-code dumping as the primary teaching method — the portal provides framework-style conceptual explanations, interface contracts, and copyable CLI snippets rather than pasting entire Python files.
  - Public user authentication or multi-tenant user accounts.

---

## Route & Page Model (10 Core Sections, 38 Key Pages)

```text
/ (redirects to /docs or renders landing)
/docs/
├── overview/                      # Раздел 1: Обзор платформы
│   ├── manifesto                  # Философия, паритет, чистота решений, non-goals
│   ├── quickstart                 # Установка (uv), .env, первый смоук SOL-USDT-SWAP
│   ├── learning-routes            # Треки: "Для разработчика" vs "Для квант-трейдера"
│   └── boundaries                 # Границы системы, безопасность, статический контент
│
├── architecture/                  # Раздел 2: Архитектура
│   ├── system-overview            # Высокоуровневая топология и граф подсистем
│   ├── decision-pipeline          # Пайплайн решений: EvaluationContext -> Signal -> Order
│   ├── module-map                 # Карта модулей (src/crypt vs src/backtester)
│   └── adrs                       # Реестр архитектурных решений (ADR-0010 — ADR-0062)
│
├── backtester/                    # Раздел 3: Бэктестер
│   ├── engine                     # Механика симулятора, исполнение, комиссии, проскальзывание
│   ├── regression                 # Регрессионные чекпоинты (Phase A/B/C Parity)
│   ├── optimization               # Optuna: exit geometry (sl_rrr, trailing, tp_pct)
│   └── metrics                    # Бенчмарк +15%/мес, просадка от старта, capped return
│
├── strategies/                    # Раздел 4: Стратегии
│   ├── anatomy                    # Базовый интерфейс Strategy, generate(), чистые функции
│   ├── dss-v3                     # Direct Signal Search v3, каталог триггеров и фильтров
│   ├── portfolios                 # Донорные портфели, контроль хвостов (v6 SOL)
│   ├── regimes                    # Детекция рыночных фаз и роутеры режимов
│   └── lifecycle                  # Жизненный цикл кандидатов, вердикты и архив
│
├── execution/                     # Раздел 5: Боевое исполнение
│   ├── architecture               # Архитектура live-модуля и контракт паритета
│   ├── okx-client                 # Интеграция с OKX: REST, WebSocket H1, типы ордеров
│   ├── reconciliation             # Синхронизация стейта, списание частей позиции, live_positions.json
│   ├── risk-base                  # Непрерывность риск-базы (ADR-0059), фиксация эквити месяца
│   └── notifications              # Telegram-оповещения, события и алерты оператору
│
├── data-pipeline/                 # Раздел 6: Пайплайн данных
│   ├── ingestion                  # Загрузка свечей, REST polling, бэкфилл данных
│   ├── models                     # Типизированные модели (Candle, FundingSnapshot, OISnapshot)
│   ├── storage                    # Хранилище Parquet, партиционирование, pyarrow-кэш
│   └── timeframes                 # Мультитаймфреймы и строгий запрет Look-Ahead Bias
│
├── cli/                           # Раздел 7: Справочник CLI
│   ├── overview                   # Общие соглашения, флаги, дефолты и переменные окружения
│   ├── backtester                 # Команды backtester run и backtester optimize
│   ├── discovery                  # Команды backtester search-signals и search-signals-matrix
│   └── live-and-backfill          # Команды python -m crypt и python -m crypt.backfill
│
├── configuration/                 # Раздел 8: Конфигурация
│   ├── env-vars                   # Справочник переменных .env (EXECUTION_*, OKX_*, TELEGRAM_*)
│   ├── strategy-json              # Спецификация и JSON-схема файлов стратегий
│   ├── risk-params                # Параметры риск-менеджмента, плечо, капитал
│   └── safety-guards              # Защитные фильтры: spread guard, stale candle, аварийные стопы
│
├── operations/                    # Раздел 9: Эксплуатация и DevOps
│   ├── railway                    # Деплой на Railway, персистентные тома, переменные
│   ├── monitoring                 # Health-чеки, структурированные логи (Loguru), метрики
│   ├── runbook                    # Ранбук оператора: десинк, сбои API OKX, аварийное закрытие
│   └── reconciliation-audits      # Исторический аудит реконсиляции (Live vs Backtest)
│
└── glossary/                      # Раздел 10: Глоссарий
    ├── trading                    # Трейдинг: RRR, TTL, ATR, Funding, Open Interest, Slippage
    ├── architecture               # Архитектура: EvaluationContext, Parity Contract, Risk Base
    └── strategies                 # Стратегии: SMC, Order Block, FVG, Regime Router
```

---

## Required User Journeys

1. **Journey 1: Первый смоук-бэктест за 5 минут (Onboarding Journey)**
   - *User:* Разработчик, только что клонировавший репозиторий.
   - *Flow:* Главная страница (`/docs`) -> Клик по кнопке «Быстрый старт» -> Чтение `/docs/overview/quickstart` -> Копирование команд `uv sync` и `uv run backtester run` -> Запуск в терминале -> Проверка вывода консоли -> Переход по ссылке «Что читать дальше: Системная архитектура».
   - *Success Criteria:* Пользователь без ошибок запустил локальный бэктест и понимает структуру артефактов в `results/`.

2. **Journey 2: Исследование и оптимизация стратегии (Quant Research Journey)**
   - *User:* Квант-трейдер, исследующий новые торговые идеи.
   - *Flow:* Меню навигации -> Раздел «Стратегии» (`/docs/strategies/dss-v3`) -> Изучение алгоритма поиска сигналов DSS v3 -> Переход в `/docs/backtester/optimization` для понимания подбора геометрии выхода через Optuna -> Ознакомление с требованиями бенчмарка в `/docs/backtester/metrics` -> Просмотр кейса v6 SOL в `/docs/strategies/portfolios`.
   - *Success Criteria:* Исследователь понимает, как из триггера создать валидный JSON-кандидат с оптимальными RRR/TTL и протестировать его на соответствие бенчмарку +15%/мес.

3. **Journey 3: Эксплуатация боевого модуля и реагирование на сбои (Live Ops Journey)**
   - *User:* DevOps / Оператор системы перед запуском реальной торговли на OKX.
   - *Flow:* Раздел «Боевое исполнение» (`/docs/execution/architecture`) -> Проверка таблицы паритета -> Изучение механизма фиксации риск-базы (`/docs/execution/risk-base`) -> Настройка переменных в `/docs/configuration/env-vars` -> Инструкция по деплою в `/docs/operations/railway` -> Изучение ранбука оператора в `/docs/operations/runbook`.
   - *Success Criteria:* Оператор безопасно разворачивает систему с корректно смонтированным томом для чекпоинтов риск-базы и знает протокол действий при получении алерта о десинхронизации.

4. **Journey 4: Мгновенный поиск через Command Palette (Search Journey)**
   - *User:* Опытный пользователь, которому нужен быстрый синтаксис флага или переменной.
   - *Flow:* Нажатие горячих клавиш `Cmd+K` (или `Ctrl+K`) на любой странице -> Ввод запроса (например, «risk_base» или «optuna») -> Моментальный вывод сгруппированных результатов со сниппетами -> Перемещение стрелками клавиатуры -> Нажатие `Enter` для перехода прямо к нужному якорю.
   - *Success Criteria:* Переход к искомой информации занимает менее 3 секунд.

---

## Required States & Affordances

| State / Component | Описание поведения и визуальные требования |
|---|---|
| **Default Content State** | Аккуратная верстка документации с высокой читаемостью, боковой навигацией слева, оглавлением справа, хлебными крошками вверху. |
| **Search Palette (`Cmd/Ctrl+K`)** | Модальное окно по центру экрана: поле ввода с фокусом, группировка результатов по 10 разделам, подсветка совпадений, навигация стрелками (`Up`/`Down`/`Enter`/`Esc`), пустое состояние с подсказками. |
| **Header Search Input** | Компактный инпут в шапке с горячей клавишей `⌘K` / `Ctrl+K`, открывающий полноценную палитру при клике или фокусе. |
| **Interactive Diagrams** | Интерактивные схемы подсистем и пайплайнов с возможностью разворачивания на полный экран, зума и переключения деталей этапов. |
| **Code & Config Tabs** | Вкладки над блоками кода (например, «CLI (Terminal)» vs «Python API», «.env» vs «YAML») с сохранением активного выбора. |
| **Copyable Snippets** | Кнопка «Копировать» в правом верхнем углу каждого блока команд/кода с анимацией подтверждения («Скопировано!») на 2 секунды. |
| **Maturity Filter** | Фильтрация каталогов (стратегии, компоненты) по бейджам: `stable`, `research`, `operational`, `archived`. |
| **Risk Callout Badges** | Яркие маркированные блоки предостережений: `[КРИТИЧЕСКИЙ РИСК: РЕАЛЬНЫЕ ДЕНЬГИ]`, `[ИСПОЛНЕНИЕ OKX / ВНЕШНЕЕ API]`, `[КОНФИГУРАЦИЯ И СЕКРЕТЫ]`, `[ЖЕСТКОЕ ПРАВИЛО: БЕЗ LOOK-AHEAD BIAS]`. |
| **Theme Toggle** | Переключатель Dark/Light в шапке без мерцания при загрузке (Dark mode по умолчанию). |
| **Mobile Navigation Drawer** | Выдвижное меню для мобильных экранов с полным деревом навигации, переключателем тем и поиском. |
| **"What to read next" Card** | Карточка в подвале каждой страницы с двумя ссылками: следующая логическая страница текущего трека и альтернативный углубленный раздел. |

---

## Source-of-Truth & Factual Mapping

| Раздел портала | Реализация в коде (`src/`) | Документация в репозитории (`docs/`) | Конфигурация / Артефакты |
|---|---|---|---|
| **Overview** | `src/crypt/__init__.py` | `README.md`, `AGENTS.md`, `docs/state/current.yml` | `pyproject.toml` |
| **Architecture** | `src/crypt/data/context.py`, `src/crypt/models.py`, `src/crypt/engines/` | `docs/architecture.md`, `docs/decisions/` | `docs/agent/context_routes.yml` |
| **Backtester** | `src/backtester/execution_sim.py`, `src/backtester/optimizer.py`, `src/backtester/fee_model.py` | `docs/backtester_regression.md`, `docs/strategy_benchmark.md` | `results/` |
| **Strategies** | `src/backtester/strategy.py`, `src/backtester/strategy_discovery/`, `src/backtester/strategies/` | `docs/discovery/direct_signal_search_v3.md`, `docs/regime_detection.md` | `strategies/archive/*.json` |
| **Live Execution** | `src/crypt/execution/` (`executor.py`, `okx_order_client.py`, `exchange_sync.py`, `risk_base_continuity.py`) | `docs/execution/live_execution.md`, `docs/execution/telegram_notifications.md` | `data/live_positions.json`, `data/risk_base_checkpoints/` |
| **Data Pipeline** | `src/crypt/data/`, `src/crypt/models.py`, `src/backtester/data_loader.py`, `src/crypt/backfill/__main__.py` | `docs/backfill.md`, `docs/agent/operating_rules.md` | `data/<symbol>/*.parquet` |
| **CLI** | `src/backtester/cli_runner.py`, `src/crypt/__main__.py`, `src/crypt/backfill/__main__.py` | `docs/cli.md`, `README.md` | CLI entrypoints in `pyproject.toml` |
| **Configuration** | `src/crypt/config.py`, `src/crypt/execution/settings.py` | `docs/execution/live_execution.md` | `.env.example` |
| **Operations** | `src/crypt/runtime/health.py`, `src/crypt/runtime/logging.py` | `docs/deploy/railway.md`, `docs/operator.md`, `docs/operations/observability.md` | `railway.toml`, `scripts/railway_live_start.sh`, `deploy/crypt.service` |
| **Glossary** | `src/crypt/models.py`, `src/crypt/structure/` | `docs/strategy_benchmark.md`, `docs/architecture.md` | `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md` |

---

## Risk & Safety Boundaries

1. **Изоляция боевых данных (Live Money Boundary):**
   Портал является чисто статическим информационным ресурсом. В исходном коде фронтенда категорически запрещено наличие API-роутов, делающих запросы к OKX API за текущим балансом, открытыми позициями или историей сделок аккаунта.
2. **Паритет логики (Parity Boundary):**
   Все формулы и концепции, описанные в документации, должны в точности соответствовать коду `src/backtester` и `src/crypt/execution`. При расхождении между старыми текстовыми документами и исполняемым кодом рантайма приоритет всегда имеет актуальный рантайм-код.
3. **Защита секретов (Secrets Boundary):**
   Все примеры конфигурации используют фиктивные плейсхолдеры (`your_okx_key_here`, `your_telegram_bot_token`). Никакие реальные ключи, токены или переменные окружения не коммитятся и не включаются в бандл портала.
4. **Строгий запрет заглядывания в будущее (No Look-Ahead Boundary):**
   Вся документация по расчету фичей, индикаторов и бэктестов акцентирует внимание на использовании исключительно закрытых свечей (`candle.is_closed == True`).

---

## Artifact Sources & Traceability

- **Owner Onboarding Answers:** Вопросы 1–30 из `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`.
- **Factual Research Artifact:** `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`.
- **Authoring Context:** D3 frontend phase main (`term_b095c115-2e3c-45ce-bc58-3ab5a82b338b`), dispatched worker session.
- **Contract Reviewer Context:** independent Orca reviewer
  (`task_9c7fffbeb164`, `term_bfd0f0f6-37fe-4588-ae8b-6a7ea6bb1650`);
  review artifact:
  `docs/frontend/reviews/2026-09-04-crypt-docs-p02-product-surface-review.md`.
- **Accepted Factual Map:** 10 разделов, 38 ключевых страниц, 4 категории рисков, 4 статуса зрелости.
- **Rejected / Unresolved Facts:** none. Advisory note: production copy must
  explain that `data/risk_base_checkpoints/` is runtime-generated, not a static
  repository directory.

---

## Approval Record

- **Revision:** 1
- **Decision:** pending owner decision (Product Surface Approval)
- **Owner message or waiver:** pending
- **Date:** 2026-09-04
- **Next phase unlocked upon approval:** P03 (Messaging Identity, Source-Grounded Content, Text Inventory, Independent Copy Review)
