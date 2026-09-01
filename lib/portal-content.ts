import {
  Archive,
  BookOpen,
  Bot,
  Boxes,
  Cable,
  ChartCandlestick,
  ClipboardList,
  Compass,
  FileWarning,
  FlaskConical,
  GitBranch,
  HeartPulse,
  LucideIcon,
  Map,
  NotebookTabs,
  PlaySquare,
  Route,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";

export type PortalSection = {
  title: string;
  body: string;
  bullets?: string[];
};

export type PortalPage = {
  slug: string;
  title: string;
  navLabel: string;
  summary: string;
  accent: "mint" | "sky" | "lavender" | "rose" | "lemon";
  icon: LucideIcon;
  sections: PortalSection[];
  related: string[];
};

export type PipelineStep = {
  id: string;
  title: string;
  summary: string;
  detail: string;
  pageSlug: string;
};

export type ArchitectureNode = {
  id: string;
  title: string;
  summary: string;
  pageSlug: string;
  tone: PortalPage["accent"];
};

export const portalPages: PortalPage[] = [
  {
    slug: "overview",
    title: "Overview",
    navLabel: "Overview",
    summary:
      "The shortest explanation of crypt: a strategy research bench first, with an optional live execution runtime.",
    accent: "mint",
    icon: Compass,
    sections: [
      {
        title: "What crypt is",
        body:
          "crypt is a curated engineering workspace for automated crypto perpetual strategy research. It helps developers turn market ideas into repeatable strategy candidates, run exact historical simulations, preserve useful research branches, and operate one owner-selected strategy through the same decision path when live execution is enabled.",
      },
      {
        title: "What the portal explains",
        body:
          "This portal explains the code as a product system: how ideas enter the bench, how candles become signals, how the backtester evaluates decisions, how candidates are archived, and where the optional OKX execution module fits.",
        bullets: [
          "No profit promises or performance claims are shown here.",
          "No exchange account data is displayed.",
          "Every page is manually curated rather than rendered from markdown.",
        ],
      },
      {
        title: "Main operating idea",
        body:
          "Research and live behavior should share pure decision code wherever practical. That keeps investigation, replay, and production operation pointed at the same underlying strategy logic instead of drifting into separate products.",
      },
    ],
    related: ["architecture", "pipeline", "research"],
  },
  {
    slug: "architecture",
    title: "Architecture",
    navLabel: "Architecture",
    summary:
      "A clickable system map for research, backtesting, archives, risk controls, runbooks, and optional execution.",
    accent: "sky",
    icon: Map,
    sections: [
      {
        title: "System shape",
        body:
          "The architecture is organized around a research loop and a runtime loop. Research creates and validates candidates. Runtime operation loads the owner-selected strategy configuration and treats the exchange as the source of truth for money, positions, fills, and fees.",
      },
      {
        title: "Boundary that matters",
        body:
          "The optional execution module is deliberately downstream of research. It should not redefine the strategy. It should load the selected strategy, evaluate closed-candle decisions, synchronize exchange state, and emit operator-visible feedback.",
      },
      {
        title: "Why this is a portal page",
        body:
          "Developers need a mental map before diving into individual modules. The map below gives each subsystem a job, a trust boundary, and a route deeper into the portal.",
      },
    ],
    related: ["pipeline", "live-execution", "risk-controls"],
  },
  {
    slug: "pipeline",
    title: "Pipeline",
    navLabel: "Pipeline",
    summary:
      "A stepper view of how research ideas move through data, strategy logic, simulation, archive, and optional runtime.",
    accent: "lemon",
    icon: Route,
    sections: [
      {
        title: "From idea to operated strategy",
        body:
          "The pipeline starts with a hypothesis and ends with either a rejected branch, an archived candidate, or a runtime-selected strategy. The important invariant is that forward progress comes from reproducible code and documented evidence, not from chat memory.",
      },
      {
        title: "Closed-candle discipline",
        body:
          "Indicators and features use closed candles only. That rule protects the research loop from look-ahead bias and keeps live decisions aligned with what the backtester could actually have known.",
      },
      {
        title: "Neutral degradation",
        body:
          "Missing market data or unavailable external state should not be guessed. The system should produce neutral signals, blocked entries, or explicit operator errors depending on the boundary involved.",
      },
    ],
    related: ["research", "backtester", "operator-runbooks"],
  },
  {
    slug: "research",
    title: "Strategy Research",
    navLabel: "Research",
    summary:
      "How developers explore candidate strategies without turning every experiment into production code.",
    accent: "lavender",
    icon: FlaskConical,
    sections: [
      {
        title: "Research is the default mode",
        body:
          "The project is primarily a research workbench. It exists to search, compare, document, and discard strategy ideas quickly while preserving the trails that proved useful enough to revisit.",
      },
      {
        title: "Candidate discipline",
        body:
          "A candidate becomes useful when its logic, data assumptions, validation path, and known risks are inspectable. The portal treats strategy research as an engineering workflow rather than a list of trading tips.",
      },
      {
        title: "Benchmark role",
        body:
          "The benchmark is a reporting and comparison target. It is not a gate that prevents the owner from promoting a strategy. When evidence and owner direction differ, the evidence is documented and the runtime source of truth stays explicit.",
      },
    ],
    related: ["backtester", "strategies", "candidate-archive"],
  },
  {
    slug: "backtester",
    title: "Backtester",
    navLabel: "Backtester",
    summary:
      "The historical execution engine that tests strategy decisions against available candle data.",
    accent: "rose",
    icon: ChartCandlestick,
    sections: [
      {
        title: "Purpose",
        body:
          "The backtester evaluates candidate decisions against historical data with execution assumptions made explicit. It is the main tool for comparing strategy variants before any runtime consideration.",
      },
      {
        title: "Regression checkpoints",
        body:
          "Backtester integrity depends on known checkpoints. The project keeps a dedicated regression document for parity and replay checks so agents do not reconstruct critical expectations from memory.",
      },
      {
        title: "What this portal omits",
        body:
          "This docs portal does not display result tables or equity curves. It explains the engine and its contracts, leaving quantitative reports to the research artifacts that generated them.",
      },
    ],
    related: ["pipeline", "research", "risks"],
  },
  {
    slug: "strategies",
    title: "Strategies",
    navLabel: "Strategies",
    summary:
      "How selected strategy configurations are treated as explicit runtime inputs and research artifacts.",
    accent: "mint",
    icon: GitBranch,
    sections: [
      {
        title: "Strategy as configuration",
        body:
          "Strategies are represented by inspectable configuration and decision code. The live runtime loads the selected configuration from the environment, so prose summaries never outrank active runtime config.",
      },
      {
        title: "Shared decision path",
        body:
          "The project prefers one pure decision path for both backtests and live operation. Shared logic reduces accidental divergence and makes a live behavior easier to replay and audit.",
      },
      {
        title: "Owner selection",
        body:
          "The owner controls which strategy is promoted. Agents document evidence, risks, and current truth, then implement against the selected runtime source.",
      },
    ],
    related: ["live-execution", "risk-controls", "research"],
  },
  {
    slug: "candidate-archive",
    title: "Candidate Archive",
    navLabel: "Archive",
    summary:
      "The memory system for frozen research branches, strategy candidates, and router experiments.",
    accent: "sky",
    icon: Archive,
    sections: [
      {
        title: "Why the archive exists",
        body:
          "Research creates many branches. The archive keeps useful candidates and router experiments available without leaving every investigation active in the main workflow.",
      },
      {
        title: "What belongs there",
        body:
          "Frozen candidates, rejected-but-informative experiments, router variants, and handoff notes belong in archive space once they are no longer active work.",
      },
      {
        title: "How to read it",
        body:
          "Treat archived material as evidence with date and context. An archived candidate can inspire new work, but active runtime configuration and current task documents remain the source of truth for current operation.",
      },
    ],
    related: ["research", "strategies", "operator-runbooks"],
  },
  {
    slug: "live-execution",
    title: "Live Execution",
    navLabel: "Live",
    summary:
      "The optional OKX runtime module for the owner-selected strategy, explained without exposing account state.",
    accent: "lavender",
    icon: Bot,
    sections: [
      {
        title: "Optional runtime module",
        body:
          "Live execution is not the whole product. It is an optional module that runs the owner-selected strategy through an OKX execution path when the environment enables it.",
      },
      {
        title: "Runtime truth",
        body:
          "Loaded environment and strategy configuration define live behavior. OKX defines money truth for fills, fees, positions, orders, and account equity. Documentation helps operators reason, but it does not override runtime state.",
      },
      {
        title: "Operator feedback",
        body:
          "The runtime should surface explicit state through logs, health checks, Telegram reporting, and reconciliation notes. Production paths must not ask interactive yes/no questions.",
      },
    ],
    related: ["risk-controls", "operator-runbooks", "strategies"],
  },
  {
    slug: "risk-controls",
    title: "Risk Controls",
    navLabel: "Risks",
    summary:
      "Where the system blocks guesses, records uncertainty, and keeps high-impact actions explicit.",
    accent: "rose",
    icon: ShieldCheck,
    sections: [
      {
        title: "Risk as code and process",
        body:
          "Risk controls are not only thresholds. They include explicit runtime sources of truth, neutral handling for missing data, regression checks, operator-visible failures, and documentation of known evidence.",
      },
      {
        title: "No hidden assumptions",
        body:
          "Exchange availability, candle availability, account state, and fills must not be assumed. When state is absent, the system should block, degrade neutrally, or emit a clear operator error.",
      },
      {
        title: "Money-path caution",
        body:
          "Any UI or runtime action that can move money, alter account state, or mutate production settings needs an explicit action contract before implementation.",
      },
    ],
    related: ["live-execution", "backtester", "operator-runbooks"],
  },
  {
    slug: "operator-runbooks",
    title: "Operator Runbooks",
    navLabel: "Runbooks",
    summary:
      "Practical paths for local setup, dry-run checks, Railway operation, Telegram reporting, and incident response.",
    accent: "lemon",
    icon: ClipboardList,
    sections: [
      {
        title: "Runbooks keep operation boring",
        body:
          "The portal explains where an operator should start, what source of truth applies, and which checks protect against acting on stale assumptions.",
      },
      {
        title: "Local first",
        body:
          "Development starts locally with explicit environment settings and targeted validation. Long-running research jobs should expose progress and avoid silent multi-minute waits.",
      },
      {
        title: "Incident response",
        body:
          "Failures should be reproduced when possible, isolated to a root cause, fixed narrowly, covered by regression tests where practical, and recorded so the next agent is not blind.",
      },
    ],
    related: ["live-execution", "risks", "overview"],
  },
  {
    slug: "risks",
    title: "Known Risks",
    navLabel: "Known Risks",
    summary:
      "The limitations a developer should understand before changing research, execution, or docs surfaces.",
    accent: "lavender",
    icon: FileWarning,
    sections: [
      {
        title: "Backtest and live drift",
        body:
          "The largest engineering risk is accidental divergence between historical simulation and live decision behavior. Shared pure decision code and regression checkpoints reduce that risk.",
      },
      {
        title: "Data gaps",
        body:
          "Market data and exchange state can be unavailable, partial, or stale. The system must not fabricate state to keep a workflow looking smooth.",
      },
      {
        title: "Documentation drift",
        body:
          "A curated portal can become stale if durable decisions are not recorded. Product pages should stay aligned with canonical docs, runtime truth, and changelog entries.",
      },
    ],
    related: ["risk-controls", "backtester", "operator-runbooks"],
  },
];

export const pipelineSteps: PipelineStep[] = [
  {
    id: "hypothesis",
    title: "Research hypothesis",
    summary: "A market behavior idea is framed as inspectable strategy logic.",
    detail:
      "The first job is to state what the candidate is trying to detect and what data assumptions it needs.",
    pageSlug: "research",
  },
  {
    id: "candles",
    title: "Closed candles",
    summary: "Indicators consume completed candles rather than future or forming data.",
    detail:
      "Closed-candle discipline protects against look-ahead bias and helps live behavior match replayable history.",
    pageSlug: "pipeline",
  },
  {
    id: "decision",
    title: "Pure decision path",
    summary: "Strategy code emits decisions without depending on presentation or operator UI.",
    detail:
      "The same decision path should be reusable by backtests and optional live runtime paths wherever practical.",
    pageSlug: "strategies",
  },
  {
    id: "backtest",
    title: "Historical execution",
    summary: "The backtester evaluates decisions against historical execution assumptions.",
    detail:
      "Regression checkpoints protect accounting, replay boundaries, and candidate comparison from silent drift.",
    pageSlug: "backtester",
  },
  {
    id: "archive",
    title: "Archive or promote",
    summary: "Useful branches are frozen with context; owner-selected configs can become runtime inputs.",
    detail:
      "The archive keeps research memory durable while active runtime config remains the source of operational truth.",
    pageSlug: "candidate-archive",
  },
  {
    id: "runtime",
    title: "Optional execution",
    summary: "The OKX module can operate the selected strategy when explicitly enabled.",
    detail:
      "Exchange state is the money truth. Missing state must become a blocked path or operator-visible error.",
    pageSlug: "live-execution",
  },
];

export const architectureNodes: ArchitectureNode[] = [
  {
    id: "research",
    title: "Research Bench",
    summary: "Strategy discovery, candidate iteration, and benchmark-oriented comparison.",
    pageSlug: "research",
    tone: "lavender",
  },
  {
    id: "backtester",
    title: "Backtester",
    summary: "Historical execution, replay boundaries, and regression checkpoints.",
    pageSlug: "backtester",
    tone: "rose",
  },
  {
    id: "archive",
    title: "Candidate Archive",
    summary: "Frozen research lines, router experiments, and reusable evidence.",
    pageSlug: "candidate-archive",
    tone: "sky",
  },
  {
    id: "strategy",
    title: "Strategy Config",
    summary: "Owner-selected strategy configuration and shared decision logic.",
    pageSlug: "strategies",
    tone: "mint",
  },
  {
    id: "runtime",
    title: "Optional OKX Runtime",
    summary: "Exchange sync, orders, fills, health, and Telegram operator reporting.",
    pageSlug: "live-execution",
    tone: "lavender",
  },
  {
    id: "risk",
    title: "Risk Controls",
    summary: "Blocked assumptions, neutral degradation, and money-path caution.",
    pageSlug: "risk-controls",
    tone: "rose",
  },
  {
    id: "runbooks",
    title: "Runbooks",
    summary: "Local setup, dry-runs, incident response, and deployment operating notes.",
    pageSlug: "operator-runbooks",
    tone: "lemon",
  },
];

export const moduleTabs = [
  {
    id: "research",
    label: "Research loop",
    icon: FlaskConical,
    body:
      "Start with candidate logic, closed-candle features, exact historical checks, and durable evidence. Most project work belongs here.",
    bullets: ["candidate search", "backtester comparison", "archive notes"],
  },
  {
    id: "runtime",
    label: "Runtime loop",
    icon: HeartPulse,
    body:
      "Load the owner-selected strategy only when execution is enabled. Runtime code treats OKX and loaded env as the source of truth.",
    bullets: ["exchange sync", "operator notifications", "health checks"],
  },
  {
    id: "docs",
    label: "Docs loop",
    icon: NotebookTabs,
    body:
      "Keep durable decisions in canonical docs so future agents and developers do not reconstruct product state from chat.",
    bullets: ["context routes", "task hygiene", "changelog trail"],
  },
];

export const quickLinks = [
  { label: "Architecture map", href: "/docs/architecture", icon: Boxes },
  { label: "Pipeline stepper", href: "/docs/pipeline", icon: PlaySquare },
  { label: "Runbooks", href: "/docs/operator-runbooks", icon: TerminalSquare },
  { label: "Search the portal", href: "#search", icon: BookOpen },
  { label: "Optional live module", href: "/docs/live-execution", icon: Cable },
];

export function getPortalPage(slug: string): PortalPage | undefined {
  return portalPages.find((page) => page.slug === slug);
}

export function getRelatedPages(page: PortalPage): PortalPage[] {
  return page.related
    .map((slug) => getPortalPage(slug))
    .filter((related): related is PortalPage => Boolean(related));
}

export function getSearchIndex() {
  return portalPages.map((page) => ({
    slug: page.slug,
    title: page.title,
    summary: page.summary,
    content: [page.title, page.summary, ...page.sections.flatMap((section) => [section.title, section.body, ...(section.bullets ?? [])])]
      .join(" ")
      .toLowerCase(),
  }));
}
