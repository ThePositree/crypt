import {
  Archive,
  Bell,
  BookOpen,
  Boxes,
  Database,
  FlaskConical,
  GitBranch,
  Map,
  PlugZap,
  Radar,
  Route,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type SectionId =
  | "overview"
  | "architecture"
  | "data"
  | "strategies"
  | "backtesting"
  | "live-execution"
  | "operations"
  | "glossary"
  | "signal-journey";

export type PortalSection = {
  id: SectionId;
  title: string;
  shortTitle: string;
  href: string;
  icon: LucideIcon;
  color: string;
  character: string;
  summary: string;
};

export type Recipe = {
  title: string;
  summary: string;
  steps: string[];
};

export type DocPage = {
  id: SectionId;
  title: string;
  eyebrow: string;
  summary: string;
  character: string;
  characterRole: string;
  mentalModel: string;
  movingParts: string[];
  contracts: string[];
  deepDive: string[];
  recipes: Recipe[];
  failureModes: string[];
  related: SectionId[];
  glossaryTerms: string[];
  sources: string[];
};

export type GlossaryTerm = {
  term: string;
  definition: string;
  section: SectionId;
  related: string[];
};

export type SystemNode = {
  id: SectionId;
  title: string;
  label: string;
  summary: string;
  connections: SectionId[];
};

export type JourneyStep = {
  id: string;
  title: string;
  summary: string;
  section: SectionId;
  state: string;
  contract: string;
};

export const sections: PortalSection[] = [
  {
    id: "overview",
    title: "Обзор",
    shortTitle: "Обзор",
    href: "/overview",
    icon: Map,
    color: "rose",
    character: "Библиотекарь системы",
    summary: "Карта проекта, роли подсистем и маршруты изучения.",
  },
  {
    id: "architecture",
    title: "Архитектура",
    shortTitle: "Архитектура",
    href: "/architecture",
    icon: Boxes,
    color: "blue",
    character: "Архитектор комнат",
    summary: "Границы между данными, стратегиями, бэктестером и live-кодом.",
  },
  {
    id: "data",
    title: "Данные",
    shortTitle: "Данные",
    href: "/data",
    icon: Database,
    color: "mint",
    character: "Хранитель источников",
    summary: "Свечи, контекст, загрузчики, хранилище и missing-data правила.",
  },
  {
    id: "strategies",
    title: "Стратегии",
    shortTitle: "Стратегии",
    href: "/strategies",
    icon: SlidersHorizontal,
    color: "apricot",
    character: "Логик стратегий",
    summary: "Правила сигналов, фильтры, маршрутизаторы и архив кандидатов.",
  },
  {
    id: "backtesting",
    title: "Бэктестер",
    shortTitle: "Бэктестер",
    href: "/backtesting",
    icon: FlaskConical,
    color: "lilac",
    character: "Инспектор симуляций",
    summary: "Как проверяются решения, комиссии, warmup/accounting и parity.",
  },
  {
    id: "live-execution",
    title: "Live Execution",
    shortTitle: "Live",
    href: "/live-execution",
    icon: PlugZap,
    color: "teal",
    character: "Оператор исполнения",
    summary: "Архитектура OKX исполнения без секретов и runtime значений.",
  },
  {
    id: "operations",
    title: "Операции",
    shortTitle: "Операции",
    href: "/operations",
    icon: Wrench,
    color: "amber",
    character: "Дежурный инженер",
    summary: "Dry-run, preflight, Railway, Telegram, observability и incidents.",
  },
  {
    id: "glossary",
    title: "Глоссарий",
    shortTitle: "Глоссарий",
    href: "/glossary",
    icon: BookOpen,
    color: "sage",
    character: "Справочник терминов",
    summary: "Термины проекта и связи между разделами.",
  },
  {
    id: "signal-journey",
    title: "Путь сигнала",
    shortTitle: "Сигнал",
    href: "/signal-journey",
    icon: Route,
    color: "coral",
    character: "Курьер сигнала",
    summary: "Как данные превращаются в решение и возможное исполнение.",
  },
];

const recipe = (title: string, summary: string, steps: string[]): Recipe => ({
  title,
  summary,
  steps,
});

export const pages: DocPage[] = [
  {
    id: "overview",
    title: "Как читать crypt",
    eyebrow: "Стартовая модель",
    summary:
      "crypt устроен как исследовательский workbench с отдельным live OKX модулем. Портал объясняет роли частей и границы между ними.",
    character: "Библиотекарь системы",
    characterRole: "держит карту комнат и показывает безопасный маршрут чтения",
    mentalModel:
      "Представь систему как контрольную комнату: данные входят через одну дверь, стратегии принимают решения в другой, бэктестер проверяет поведение на истории, а live execution применяет выбранную стратегию через отдельную операционную границу.",
    movingParts: [
      "Research path ищет, сравнивает и архивирует стратегии.",
      "Backtester path воспроизводит историческое исполнение и проверяет accounting.",
      "Decision path стремится оставаться общей чистой логикой для backtest и live.",
      "Live path читает runtime config и работает с OKX как источником денежной правды.",
    ],
    contracts: [
      "Документация объясняет устройство кода, но не отображает результаты запусков.",
      "Старый Telegram signal-only MVP является историческим контекстом.",
      "Benchmark помогает сравнивать стратегии, но владелец выбирает production стратегию.",
      "Если prose и runtime config расходятся, runtime config важнее для live behavior.",
    ],
    deepDive: [
      "Главная ось проекта: данные -> стратегия -> решение -> проверка -> optional live execution.",
      "Архитектура полезна только тогда, когда она сохраняет границы ответственности: исследование не должно неявно мутировать live состояние, а live путь не должен зависеть от приблизительных отчётов.",
      "Портал намеренно продуктовый: он называет человеческие роли подсистем, но внутри страниц даёт инженерные контракты, failure modes и recipes.",
    ],
    recipes: [
      recipe("Выбрать маршрут чтения", "Начни с данных, затем переходи к стратегиям, бэктестеру и live execution.", [
        "Открой карту системы на главной.",
        "Выбери подсистему, которая отвечает на текущий вопрос.",
        "Перейди в deep-dive и проверь contracts/failure modes.",
      ]),
    ],
    failureModes: [
      "Считать портал runtime truth для live money path.",
      "Путать research evidence с production selection.",
      "Читать отдельный модуль без data-flow и signal journey контекста.",
    ],
    related: ["architecture", "data", "strategies", "signal-journey"],
    glossaryTerms: ["runtime truth", "signal", "strategy", "benchmark"],
    sources: ["README.md", "docs/state/current.yml", "AGENTS.md"],
  },
  {
    id: "architecture",
    title: "Архитектура как набор комнат",
    eyebrow: "Границы системы",
    summary:
      "Раздел объясняет, где заканчиваются данные, где начинается decision logic, и почему exchange/runtime эффекты держатся отдельно.",
    character: "Архитектор комнат",
    characterRole: "следит, чтобы каждая подсистема имела свою дверь и контракт",
    mentalModel:
      "Архитектура crypt строится вокруг явных границ: data слой поставляет закрытые свечи и контекст, engines/strategies формируют сигналы, backtester симулирует исполнение, runtime и execution работают с внешними эффектами.",
    movingParts: [
      "Data modules отвечают за ingestion, store и контекст.",
      "Engines описывают reusable рыночные признаки и сигнальные идеи.",
      "Aggregator и decision filters собирают решения и ограничения.",
      "Backtester применяет стратегию к истории с отдельным accounting.",
      "Execution и exchange modules синхронизируют позиции, ордера и уведомления.",
      "Sinks выводят события в консоль, JSON logs, Telegram или execution stub.",
    ],
    contracts: [
      "Pure decision code должен переиспользоваться между backtest и live там, где это возможно.",
      "Внешние эффекты остаются на runtime/execution/exchange границе.",
      "OKX является источником правды для fills, fees, positions и equity.",
      "Missing data должно приводить к neutral signal, blocked entry или явной ошибке оператора.",
    ],
    deepDive: [
      "Архитектурный слой не пытается спрятать сложность за одним объектом. Он делает важные переходы явными: подготовка данных, оценка стратегии, риск, simulation или live order path.",
      "Backtester и live execution не должны расходиться в том, как понимают стратегическое решение. Различаются источники фактов: история в backtest, exchange/runtime state в live.",
      "Система расширяется через новые стратегии, engines, sinks или data sources, но каждое расширение должно сохранить no-look-ahead и понятную деградацию при отсутствии данных.",
    ],
    recipes: [
      recipe("Добавить новый subsystem page", "Новая страница должна объяснить роль, границы, contracts и related links.", [
        "Определи, какую ответственность подсистема забирает у соседних модулей.",
        "Запиши входы, выходы, failure modes и links на glossary.",
        "Добавь страницу в curated content и поисковый corpus.",
      ]),
    ],
    failureModes: [
      "Смешать research scripts и live execution side effects.",
      "Сделать стратегию зависимой от непроверенного runtime state.",
      "Добавить abstraction без уменьшения реальной сложности.",
    ],
    related: ["data", "strategies", "backtesting", "live-execution"],
    glossaryTerms: ["engine", "sink", "runtime truth", "exchange sync"],
    sources: ["docs/architecture.md", "docs/agent/context_routes.yml", "src/crypt"],
  },
  {
    id: "data",
    title: "Данные и свечные границы",
    eyebrow: "Market data room",
    summary:
      "Данные в crypt должны быть явными, проверяемыми и закрытыми по времени. Это защита от look-ahead и тихих runtime допущений.",
    character: "Хранитель источников",
    characterRole: "проверяет, что каждая свеча пришла вовремя и не смотрит в будущее",
    mentalModel:
      "Data слой отвечает не за торговую идею, а за честный материал для неё: загрузить, сохранить, дать контекст и явно сообщить, если чего-то не хватает.",
    movingParts: [
      "Ingestor получает рыночные данные.",
      "Store хранит свечи и отдаёт их потребителям.",
      "Context собирает данные для стратегий и исполнения.",
      "Backtester data loader читает исторические окна.",
      "Timeframe handling определяет, какие свечи доступны конкретной стратегии.",
    ],
    contracts: [
      "Индикаторы и features используют только closed candles.",
      "Недоступность данных не должна превращаться в уверенный сигнал.",
      "Backtest warmup может отличаться от accounting window.",
      "Нельзя предполагать доступность exchange/data без проверки.",
    ],
    deepDive: [
      "Закрытая свеча означает, что вся информация внутри неё уже была известна на момент принятия решения. Это главное правило против look-ahead bias.",
      "Отсутствие данных является состоянием системы, а не просто пустым списком. Стратегия может получить neutral behavior, blocked entry или operator-visible error.",
      "Для candidate JSON стратегий execution timeframe может следовать из trigger timeframe, поэтому портал объясняет принцип, а не заставляет читателя держать в голове CLI детали.",
    ],
    recipes: [
      recipe("Добавить источник данных", "Источник должен сохранять временные границы и failure behavior.", [
        "Определи, какие свечи и timeframe он поставляет.",
        "Опиши missing/partial data state.",
        "Добавь проверку, что downstream логика не видит будущие свечи.",
      ]),
    ],
    failureModes: [
      "Использовать текущую незакрытую свечу как исторический факт.",
      "Молчаливо заполнить отсутствующие данные optimistic значением.",
      "Смешать warmup данные и период accounting в отчёте.",
    ],
    related: ["strategies", "backtesting", "signal-journey"],
    glossaryTerms: ["candle", "closed candle", "warmup", "partial data"],
    sources: ["src/crypt/data", "src/backtester/data_loader.py", "docs/backtester_regression.md"],
  },
  {
    id: "strategies",
    title: "Стратегии, фильтры и маршруты",
    eyebrow: "Decision room",
    summary:
      "Стратегии описывают правила входа, выхода и фильтрации. Архивы и benchmark дают evidence, но production выбор остаётся решением владельца.",
    character: "Логик стратегий",
    characterRole: "превращает гипотезы в проверяемые правила",
    mentalModel:
      "Стратегия в crypt - это не чёрный ящик. Это набор условий, параметров, фильтров и runtime metadata, которые должны одинаково читаться исследовательским и live путём там, где это возможно.",
    movingParts: [
      "Engines выделяют reusable рыночные свойства: trend, volatility, derivatives, SMC и другие.",
      "Decision filters блокируют или пропускают entries по условиям.",
      "Strategy discovery генерирует и оценивает кандидатов.",
      "Routers и portfolios комбинируют donor strategies.",
      "Archives фиксируют полезные исследовательские ветки.",
    ],
    contracts: [
      "Benchmark является reporting target, а не production gate.",
      "Owner может выбрать production стратегию даже при слабом benchmark evidence.",
      "Known evidence and risks document once, active runtime config continues.",
      "Strategy code must avoid look-ahead through closed-candle inputs.",
    ],
    deepDive: [
      "Strategy discovery полезен как фабрика кандидатов, но портал объясняет не результаты поиска, а форму pipeline: признаки, triggers, filters, scoring, архивирование.",
      "Routing strategy выбирает не одну магическую формулу, а состав правил с разными режимами и ограничениями.",
      "Новые стратегии должны быть объяснимыми через входные данные, сигнал, риск и ожидаемую validation команду.",
    ],
    recipes: [
      recipe("Добавить стратегию", "Новая стратегия должна иметь понятный signal contract и backtest path.", [
        "Опиши trigger и timeframe.",
        "Проверь, что входы используют closed candles.",
        "Добавь или переиспользуй validation route в backtester.",
      ]),
      recipe("Добавить фильтр", "Фильтр должен явно говорить, когда он блокирует entry.", [
        "Определи входные признаки.",
        "Верни neutral/block behavior для missing data.",
        "Покрой regression case.",
      ]),
    ],
    failureModes: [
      "Считать archive candidate production truth.",
      "Сделать фильтр, который silently пропускает missing data.",
      "Оптимизировать только PnL без проверки tail risk и parity.",
    ],
    related: ["data", "backtesting", "signal-journey"],
    glossaryTerms: ["strategy", "filter", "router", "benchmark", "donor"],
    sources: ["src/backtester/strategies", "src/crypt/decision", "docs/strategy_benchmark.md"],
  },
  {
    id: "backtesting",
    title: "Бэктестер и regression checkpoints",
    eyebrow: "Simulation room",
    summary:
      "Бэктестер проверяет поведение стратегии на истории, отделяя warmup от accounting и сохраняя parity discipline с live path.",
    character: "Инспектор симуляций",
    characterRole: "сверяет исторический сценарий с контрактами исполнения",
    mentalModel:
      "Backtest - это контролируемая симуляция принятия решений и исполнения. Его цель не показать красивый результат в портале, а объяснить, как evidence создаётся и где оно может сломаться.",
    movingParts: [
      "CLI runner собирает параметры запуска.",
      "Tester проходит по свечам и вызывает strategy logic.",
      "Execution simulation применяет комиссии, sizing, margin, TP/SL behavior.",
      "Regression docs фиксируют phase checkpoints.",
      "Reports and analyzers существуют как artifacts, но портал не показывает результаты.",
    ],
    contracts: [
      "`--load-from` может задавать warmup раньше, чем `--from` accounting boundary.",
      "Use `docs/backtester_regression.md` for backtester-broken checks.",
      "No look-ahead applies to every feature and indicator.",
      "Full validation should be scoped when long commands exceed practical ETA.",
    ],
    deepDive: [
      "Warmup даёт стратегии исторический контекст, но не должен засчитываться как trading/accounting период, если задача требует отдельной boundary.",
      "Phase checkpoints нужны не для реконструкции истории из чата, а как стабильный regression target.",
      "Backtester может быть корректным как decision simulator и всё равно отличаться от OKX fills; эти различия относятся к reconciliation.",
    ],
    recipes: [
      recipe("Проверить parity", "Используй documented checkpoint вместо ad hoc историй.", [
        "Открой regression document.",
        "Выбери checkpoint и expected boundary.",
        "Сравни decision path отдельно от exchange money truth.",
      ]),
    ],
    failureModes: [
      "Стартовать history точно с accounting boundary и потерять warmup context.",
      "Считать exchange slippage ошибкой decision code без reconciliation.",
      "Показывать PnL в документационном портале как продуктовую поверхность.",
    ],
    related: ["strategies", "live-execution", "operations"],
    glossaryTerms: ["backtester", "warmup", "accounting window", "parity"],
    sources: ["src/backtester", "docs/backtester_regression.md"],
  },
  {
    id: "live-execution",
    title: "Live Execution без раскрытия runtime",
    eyebrow: "Execution room",
    summary:
      "Live path объясняется как архитектура: runtime config, risk, position state, OKX sync, order client and notifications. Секреты и значения счёта не показываются.",
    character: "Оператор исполнения",
    characterRole: "проверяет границу между публичным объяснением и live money truth",
    mentalModel:
      "Live execution - это не продолжение docs и не dashboard. Это runtime, который читает конфигурацию, синхронизируется с exchange, принимает decisions и отправляет orders only when enabled.",
    movingParts: [
      "Signal runner получает strategy decision.",
      "Executor применяет execution settings and risk calculation.",
      "Position state tracks local knowledge while exchange sync verifies truth.",
      "OKX order client handles external order interactions.",
      "Notifications explain operator-visible events.",
    ],
    contracts: [
      "Production runtime must never ask interactive y/n questions.",
      "OKX is truth for fills, fees, positions, orders and account equity.",
      "Loaded env/config beats prose summaries.",
      "Public portal never shows live account values or secrets.",
    ],
    deepDive: [
      "Live behavior starts from loaded runtime config. Even accurate docs cannot override `EXECUTION_STRATEGY_CONFIG` or exchange state.",
      "Exchange sync reduces drift between local state and OKX facts. It should classify fills and positions clearly enough for operator understanding.",
      "Notifications are part of observability, not the source of money truth.",
    ],
    recipes: [
      recipe("Trace a live decision", "Follow the architecture without exposing private runtime.", [
        "Start at signal runner.",
        "Check execution settings and risk boundaries conceptually.",
        "Follow exchange sync and notification responsibilities.",
      ]),
    ],
    failureModes: [
      "Treating local state as final when OKX differs.",
      "Documenting a prose strategy as if it were active runtime config.",
      "Adding public UI for private money/account state.",
    ],
    related: ["operations", "signal-journey", "backtesting"],
    glossaryTerms: ["OKX", "runtime truth", "exchange sync", "dry-run"],
    sources: ["src/crypt/execution", "src/crypt/exchange", "docs/execution/live_execution.md"],
  },
  {
    id: "operations",
    title: "Операционные сценарии",
    eyebrow: "Runbook room",
    summary:
      "Операции объясняют dry-run, preflight, Railway, Telegram notifications, observability and incident response как сценарии поведения кода.",
    character: "Дежурный инженер",
    characterRole: "показывает preconditions, recovery и границы действия",
    mentalModel:
      "Operational docs отвечают на вопрос: что делает система в конкретном сценарии и как оператор понимает состояние, не мутируя ничего из публичного портала.",
    movingParts: [
      "Dry-run checks decision and execution wiring without real money.",
      "Deploy preflight validates readiness before live runtime.",
      "Railway hosts production process outside the portal.",
      "Telegram reports operator-visible events.",
      "Observability and incident response explain recovery paths.",
    ],
    contracts: [
      "Portal does not deploy, push, mutate exchange, or change external state.",
      "Long-running commands must expose progress and ETA.",
      "Incident handling starts with reproduction or a clear reason why not.",
      "Operator docs must preserve private env and credential boundaries.",
    ],
    deepDive: [
      "Operations pages are scenario-driven: starting condition, checks, what code path does, expected feedback, failure/recovery.",
      "Railway and Telegram are explained as system integration surfaces, not as live data widgets.",
      "Incident response protects the codebase from reflexive refactors: reproduce, isolate root cause, apply smallest fix, add regression coverage, record durable knowledge.",
    ],
    recipes: [
      recipe("Run a dry-run mentally", "Understand the operator path before touching live state.", [
        "Confirm execution is dry-run conceptually.",
        "Trace signal runner and executor boundaries.",
        "Read notification and failure-state expectations.",
      ]),
      recipe("Handle an incident", "Use the repo's incident sequence.", [
        "Reproduce or state why impossible.",
        "Isolate root cause before refactoring.",
        "Patch smallest cause and update tests/docs.",
      ]),
    ],
    failureModes: [
      "Turning docs into a control plane.",
      "Hiding missing credentials behind generic errors.",
      "Skipping changelog/task updates after operational changes.",
    ],
    related: ["live-execution", "architecture", "glossary"],
    glossaryTerms: ["dry-run", "preflight", "Telegram sink", "incident response"],
    sources: ["docs/operations", "docs/deploy/railway.md", "AGENTS.md"],
  },
  {
    id: "glossary",
    title: "Глоссарий проекта",
    eyebrow: "Reference room",
    summary:
      "Глоссарий объясняет локальный язык crypt и связывает термины с разделами, где они реально используются.",
    character: "Справочник терминов",
    characterRole: "собирает понятия и показывает связи между комнатами",
    mentalModel:
      "Термин полезен только тогда, когда он помогает перейти от слова к поведению системы. Поэтому записи глоссария связаны с разделами и соседними понятиями.",
    movingParts: [
      "Alphabet browsing helps when the reader knows the term.",
      "Filters help by subsystem.",
      "Related terms show conceptual neighbors.",
      "Backlinks take the reader to the page where behavior is explained.",
    ],
    contracts: [
      "Definitions are project-specific, not generic crypto encyclopedia entries.",
      "Every major page should expose related terms.",
      "Search includes glossary content.",
      "Zero-result states should route back to learning paths.",
    ],
    deepDive: [
      "Glossary terms should reduce friction inside dense docs pages. If a term needs a full explanation, the glossary links back to a section instead of duplicating a page.",
      "Filtering by section lets a reader see, for example, only execution concepts or only strategy concepts.",
    ],
    recipes: [
      recipe("Добавить термин", "Термин должен иметь definition, section and related links.", [
        "Напиши project-specific meaning.",
        "Свяжи термин с основным разделом.",
        "Добавь related terms and search tags.",
      ]),
    ],
    failureModes: [
      "Определение слишком общее и не помогает читать этот код.",
      "Термин есть в тексте, но не находится поиском.",
      "Глоссарий становится тупиком без related links.",
    ],
    related: ["overview", "architecture", "signal-journey"],
    glossaryTerms: ["signal", "candle", "strategy", "OKX", "sink"],
    sources: ["docs/frontend/product-surface-model.md", "README.md"],
  },
  {
    id: "signal-journey",
    title: "Путь сигнала",
    eyebrow: "From data to action",
    summary:
      "Путь сигнала показывает, как данные превращаются в decision, затем в backtest simulation или optional live execution behavior.",
    character: "Курьер сигнала",
    characterRole: "несёт событие через комнаты и показывает, где оно меняет форму",
    mentalModel:
      "Signal journey - это учебная нить через весь проект. Она соединяет data availability, strategy rules, risk checks, simulation/live branch, notifications and reconciliation.",
    movingParts: [
      "Data is loaded and normalized.",
      "Features and indicators are calculated on closed candles.",
      "Strategy evaluates triggers and filters.",
      "Risk layer sizes or blocks the entry.",
      "Backtester simulates; live execution may route orders when enabled.",
      "Logs, notifications and reconciliation explain what happened.",
    ],
    contracts: [
      "A missing or partial input cannot become a confident entry.",
      "Backtest and live should share decision code where possible.",
      "Live branch trusts runtime config and OKX facts.",
      "The portal shows behavior path, not realized trading outcomes.",
    ],
    deepDive: [
      "The same conceptual signal changes representation as it moves: market data, feature state, strategy decision, risk decision, simulated trade or live order intent, then audit trail.",
      "The branch point between backtest and live is important. Backtest controls historical data and accounting; live must respect exchange facts, position sync and operator-visible errors.",
      "Signal journey is the best debugging map because it shows where a failure belongs: data availability, decision logic, risk policy, execution client, or reconciliation.",
    ],
    recipes: [
      recipe("Debug a blocked signal", "Classify the stop point instead of guessing.", [
        "Check whether source candles are available and closed.",
        "Inspect strategy/filter conditions conceptually.",
        "Determine whether risk or exchange sync blocked the entry.",
      ]),
    ],
    failureModes: [
      "Debugging live behavior from a backtest result alone.",
      "Skipping data availability and looking only at strategy rules.",
      "Treating notifications as final money truth.",
    ],
    related: ["data", "strategies", "backtesting", "live-execution"],
    glossaryTerms: ["signal", "filter", "risk", "execution", "reconciliation"],
    sources: ["src/crypt/execution/signal_runner.py", "src/backtester", "docs/execution/live_backtest_reconciliation_2026-07-28.md"],
  },
];

export const systemNodes: SystemNode[] = sections.map((section) => ({
  id: section.id,
  title: section.title,
  label: section.shortTitle,
  summary: section.summary,
  connections:
    section.id === "overview"
      ? ["architecture", "data", "signal-journey"]
      : section.id === "data"
        ? ["strategies", "backtesting"]
        : section.id === "strategies"
          ? ["backtesting", "signal-journey"]
          : section.id === "backtesting"
            ? ["live-execution", "operations"]
            : section.id === "live-execution"
              ? ["operations", "signal-journey"]
              : ["overview", "glossary"],
}));

export const journeySteps: JourneyStep[] = [
  {
    id: "capture",
    title: "Данные получены",
    summary: "Система получает свечи и рыночный контекст из доступных источников.",
    section: "data",
    state: "сырой market context",
    contract: "Нельзя считать данные доступными без проверки.",
  },
  {
    id: "normalize",
    title: "Границы закрыты",
    summary: "Свечи и признаки приводятся к timeframe, который может видеть стратегия.",
    section: "data",
    state: "closed-candle window",
    contract: "No look-ahead: незакрытая свеча не является фактом.",
  },
  {
    id: "evaluate",
    title: "Стратегия думает",
    summary: "Rules, engines and filters превращают состояние рынка в signal decision.",
    section: "strategies",
    state: "candidate decision",
    contract: "Missing data приводит к neutral или blocked behavior.",
  },
  {
    id: "risk",
    title: "Риск проверяет",
    summary: "Risk policies решают, можно ли входить и каким размером.",
    section: "live-execution",
    state: "sized or blocked intent",
    contract: "Риск должен быть явным и проверяемым.",
  },
  {
    id: "simulate",
    title: "Бэктест ветвится",
    summary: "Исторический путь симулирует execution, fees and accounting.",
    section: "backtesting",
    state: "simulated trade path",
    contract: "Warmup and accounting windows can differ.",
  },
  {
    id: "execute",
    title: "Live ветвится",
    summary: "Live path uses runtime config, exchange sync and OKX order boundaries.",
    section: "live-execution",
    state: "order intent or block",
    contract: "OKX remains money truth.",
  },
  {
    id: "observe",
    title: "След остаётся",
    summary: "Logs, Telegram and reconciliation explain what the system believes happened.",
    section: "operations",
    state: "operator-visible audit trail",
    contract: "Notifications are evidence, not exchange truth.",
  },
];

export const glossaryTerms: GlossaryTerm[] = [
  { term: "signal", definition: "Стратегическое событие или решение, которое может привести к входу, выходу или блокировке действия.", section: "signal-journey", related: ["strategy", "filter", "risk"] },
  { term: "candle", definition: "Свечной интервал рынка. Для принятия решений в crypt важны только закрытые свечи.", section: "data", related: ["closed candle", "timeframe"] },
  { term: "closed candle", definition: "Свеча, чьи данные уже завершены во времени и не добавляют look-ahead bias.", section: "data", related: ["candle", "no look-ahead"] },
  { term: "strategy", definition: "Набор правил, параметров и фильтров, формирующий decision из рыночного состояния.", section: "strategies", related: ["signal", "filter", "router"] },
  { term: "filter", definition: "Условие, которое пропускает, блокирует или ослабляет entry decision.", section: "strategies", related: ["strategy", "missing data"] },
  { term: "router", definition: "Композиция или выбор между стратегиями, donor-компонентами и режимами.", section: "strategies", related: ["portfolio", "donor", "benchmark"] },
  { term: "benchmark", definition: "Денежная цель сравнения стратегий; не является жёстким production gate.", section: "strategies", related: ["strategy", "owner override"] },
  { term: "backtester", definition: "Исторический симулятор strategy and execution behavior с accounting и regression checkpoints.", section: "backtesting", related: ["warmup", "parity"] },
  { term: "warmup", definition: "Исторический контекст до accounting boundary, нужный для корректных features и signals.", section: "backtesting", related: ["accounting window", "candle"] },
  { term: "accounting window", definition: "Период, чьи сделки и деньги засчитываются в конкретной проверке.", section: "backtesting", related: ["warmup", "parity"] },
  { term: "parity", definition: "Дисциплина сравнения backtest and live decision behavior без смешивания с exchange money truth.", section: "backtesting", related: ["reconciliation", "OKX"] },
  { term: "OKX", definition: "Биржевая система, которая является источником правды для fills, fees, positions, orders and equity.", section: "live-execution", related: ["exchange sync", "runtime truth"] },
  { term: "runtime truth", definition: "Loaded env/config and external exchange state, которые важнее prose summaries для live behavior.", section: "live-execution", related: ["OKX", "EXECUTION_STRATEGY_CONFIG"] },
  { term: "exchange sync", definition: "Граница синхронизации локального состояния с биржевыми фактами.", section: "live-execution", related: ["OKX", "position state"] },
  { term: "sink", definition: "Выходной адаптер для событий: console, JSON log, Telegram или execution stub.", section: "architecture", related: ["notification", "operations"] },
  { term: "dry-run", definition: "Режим проверки execution path без реального денежного исполнения.", section: "operations", related: ["preflight", "live execution"] },
  { term: "preflight", definition: "Проверка готовности runtime и конфигурации перед live execution.", section: "operations", related: ["dry-run", "runtime truth"] },
  { term: "Telegram sink", definition: "Канал operator-visible уведомлений, который помогает наблюдать события, но не заменяет OKX truth.", section: "operations", related: ["sink", "notification"] },
  { term: "reconciliation", definition: "Сверка live facts, logs, fills and replay evidence для объяснения расхождений.", section: "operations", related: ["parity", "OKX"] },
  { term: "partial data", definition: "Состояние, когда данных достаточно для части интерфейса или проверки, но не для уверенного действия.", section: "data", related: ["missing data", "blocked entry"] },
  { term: "blocked entry", definition: "Decision path остановил потенциальный вход из-за риска, missing data, sync или другого явного условия.", section: "signal-journey", related: ["filter", "risk"] },
  { term: "incident response", definition: "Последовательность fix-work: reproduce, isolate root cause, smallest fix, regression test, docs update.", section: "operations", related: ["preflight", "observability"] },
];

export const learningRoutes = [
  { title: "Сначала понять данные", href: "/data", summary: "Закрытые свечи, store, context и missing-data поведение." },
  { title: "Потом стратегии", href: "/strategies", summary: "Rules, filters, routing и жизненный цикл кандидатов." },
  { title: "Затем бэктестер", href: "/backtesting", summary: "Simulation, accounting boundaries и regression checkpoints." },
  { title: "После этого live", href: "/live-execution", summary: "Runtime config, OKX sync и execution boundaries." },
];

export function getPage(id: SectionId) {
  return pages.find((page) => page.id === id);
}

export function getSection(id: SectionId) {
  return sections.find((section) => section.id === id);
}

export type SearchDocument = {
  id: string;
  type: "page" | "glossary" | "recipe" | "journey";
  title: string;
  section: string;
  href: string;
  body: string;
  tags: string[];
};

export function buildSearchDocuments(): SearchDocument[] {
  const pageDocs = pages.map((page) => ({
    id: `page:${page.id}`,
    type: "page" as const,
    title: page.title,
    section: getSection(page.id)?.title ?? page.id,
    href: `/${page.id === "overview" ? "overview" : page.id}`,
    body: [
      page.summary,
      page.mentalModel,
      ...page.movingParts,
      ...page.contracts,
      ...page.deepDive,
      ...page.failureModes,
      ...page.glossaryTerms,
    ].join(" "),
    tags: [page.id, ...page.glossaryTerms],
  }));

  const glossaryDocs = glossaryTerms.map((term) => ({
    id: `glossary:${term.term}`,
    type: "glossary" as const,
    title: term.term,
    section: getSection(term.section)?.title ?? term.section,
    href: `/glossary?term=${encodeURIComponent(term.term)}`,
    body: [term.definition, ...term.related].join(" "),
    tags: [term.section, ...term.related],
  }));

  const recipeDocs = pages.flatMap((page) =>
    page.recipes.map((item) => ({
      id: `recipe:${page.id}:${item.title}`,
      type: "recipe" as const,
      title: item.title,
      section: getSection(page.id)?.title ?? page.id,
      href: `/${page.id}#recipes`,
      body: [item.summary, ...item.steps].join(" "),
      tags: [page.id, "recipe"],
    })),
  );

  const journeyDocs = journeySteps.map((step) => ({
    id: `journey:${step.id}`,
    type: "journey" as const,
    title: step.title,
    section: "Путь сигнала",
    href: `/signal-journey#${step.id}`,
    body: [step.summary, step.state, step.contract].join(" "),
    tags: [step.section, "signal", "journey"],
  }));

  return [...pageDocs, ...glossaryDocs, ...recipeDocs, ...journeyDocs];
}

export function searchDocuments(query: string, sectionFilter = "all") {
  const normalized = query.trim().toLowerCase();
  const docs = buildSearchDocuments();

  if (!normalized) {
    return docs.slice(0, 8).map((doc) => ({ ...doc, score: 0, snippet: doc.body.slice(0, 180) }));
  }

  const terms = normalized.split(/\s+/).filter(Boolean);

  return docs
    .filter((doc) => sectionFilter === "all" || doc.section === sectionFilter || doc.tags.includes(sectionFilter))
    .map((doc) => {
      const haystack = `${doc.title} ${doc.section} ${doc.body} ${doc.tags.join(" ")}`.toLowerCase();
      const title = doc.title.toLowerCase();
      const score = terms.reduce((total, term) => {
        const exactTitle = title.includes(term) ? 12 : 0;
        const occurrences = haystack.split(term).length - 1;
        return total + exactTitle + occurrences;
      }, 0);
      return { ...doc, score, snippet: makeSnippet(doc.body, terms) };
    })
    .filter((doc) => doc.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title, "ru"))
    .slice(0, 24);
}

function makeSnippet(body: string, terms: string[]) {
  const lower = body.toLowerCase();
  const first = terms
    .map((term) => lower.indexOf(term))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b)[0];

  if (first === undefined) {
    return body.slice(0, 180);
  }

  const start = Math.max(0, first - 70);
  const end = Math.min(body.length, first + 150);
  return `${start > 0 ? "..." : ""}${body.slice(start, end)}${end < body.length ? "..." : ""}`;
}

export const utilityIcons = {
  archive: Archive,
  bell: Bell,
  git: GitBranch,
  radar: Radar,
  search: Search,
  shield: ShieldCheck,
  zap: Zap,
};
