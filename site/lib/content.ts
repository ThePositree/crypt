import {
  BarChart3,
  BookOpen,
  Boxes,
  Braces,
  Compass,
  Database,
  GitBranch,
  LifeBuoy,
  LucideIcon,
  Map,
  PlayCircle,
  RadioTower,
  Scale,
  Search,
  ShieldCheck,
  TerminalSquare
} from "lucide-react";

export type DocSection = {
  heading: string;
  body: string[];
  bullets?: string[];
};

export type GuideStep = {
  title: string;
  command: string;
  output: string[];
  explanation: string;
};

export type DocPage = {
  slug: string;
  title: string;
  eyebrow: string;
  description: string;
  type: "Guide" | "Concept" | "Reference" | "Risk" | "Overview";
  version: string;
  audience: Array<"Developers" | "Crypto Traders">;
  tags: string[];
  sourceRefs: string[];
  sections: DocSection[];
  guideSteps?: GuideStep[];
  related: string[];
};

export type MapNode = {
  id: string;
  title: string;
  short: string;
  slug: string;
  tone: "data" | "engine" | "strategy" | "backtest" | "execution" | "results" | "risk";
  position: { left: string; top: string };
  icon: LucideIcon;
};

export const versions = ["v0.1.0", "v0.0.3", "v0.0.2", "v0.0.1"];
export const currentVersion = versions[0];

export const mapNodes: MapNode[] = [
  {
    id: "data",
    title: "Data Station",
    short: "Loads candles and normalizes market context.",
    slug: "architecture",
    tone: "data",
    position: { left: "8%", top: "12%" },
    icon: Database
  },
  {
    id: "engine",
    title: "Engine Workshop",
    short: "Turns closed candles into features and signals.",
    slug: "strategy-lifecycle",
    tone: "engine",
    position: { left: "38%", top: "10%" },
    icon: Boxes
  },
  {
    id: "strategy",
    title: "Strategy Studio",
    short: "Composes rules, filters, exits, and portfolios.",
    slug: "strategy-lifecycle",
    tone: "strategy",
    position: { left: "69%", top: "16%" },
    icon: GitBranch
  },
  {
    id: "backtest",
    title: "Backtest Lab",
    short: "Replays strategies with costs and exact windows.",
    slug: "backtester",
    tone: "backtest",
    position: { left: "15%", top: "52%" },
    icon: PlayCircle
  },
  {
    id: "execution",
    title: "Execution Boundary Bridge",
    short: "Separates research decisions from live connectors.",
    slug: "live-execution",
    tone: "execution",
    position: { left: "40%", top: "47%" },
    icon: RadioTower
  },
  {
    id: "results",
    title: "Report Library",
    short: "Explains metrics, archives, and comparison artifacts.",
    slug: "read-results",
    tone: "results",
    position: { left: "66%", top: "50%" },
    icon: BarChart3
  },
  {
    id: "risk",
    title: "Risk Clinic",
    short: "Names limits, assumptions, and non-promises.",
    slug: "risk-limits",
    tone: "risk",
    position: { left: "35%", top: "75%" },
    icon: ShieldCheck
  }
];

export const topicNav = [
  { title: "Overview", slug: "overview", icon: Compass },
  { title: "Architecture", slug: "architecture", icon: Map },
  { title: "Strategy Lifecycle", slug: "strategy-lifecycle", icon: GitBranch },
  { title: "Backtester", slug: "backtester", icon: PlayCircle },
  { title: "Live Execution", slug: "live-execution", icon: RadioTower },
  { title: "Read Results", slug: "read-results", icon: BarChart3 },
  { title: "Glossary", slug: "glossary", icon: BookOpen },
  { title: "For Developers", slug: "for-developers", icon: Braces },
  { title: "For Crypto Traders", slug: "for-crypto-traders", icon: Scale },
  { title: "Risk & Limits", slug: "risk-limits", icon: LifeBuoy }
];

export const docPages: DocPage[] = [
  {
    slug: "overview",
    title: "Overview",
    eyebrow: "Start here",
    description:
      "crypt is a Python research desk for crypto perpetual strategies: data comes in, strategy ideas become code, backtests replay history, and public docs explain the boundary to execution.",
    type: "Overview",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["system map", "research desk", "python", "crypto strategies"],
    sourceRefs: ["README.md", "docs/state/current.yml"],
    sections: [
      {
        heading: "What the project does",
        body: [
          "The repository is built around automated research. It searches for strategy candidates, validates them in exact backtests, archives useful research lines, and keeps live execution logic separate from the explanation surface.",
          "The public docs are curated. They use repository sources as evidence, but they are not a raw mirror of every Markdown file."
        ],
        bullets: [
          "Strategy research and candidate discovery",
          "Backtests with cost and risk reporting",
          "Public architecture for execution boundaries",
          "Guides that connect commands, output, and interpretation"
        ]
      },
      {
        heading: "How to read the Docs Town map",
        body: [
          "Each region is a subsystem. The important path is not a straight line: data quality, strategy rules, execution simulation, and risk interpretation loop back into each other.",
          "Start with the map when you need orientation. Use search when you already know a term, module, or workflow."
        ]
      }
    ],
    related: ["architecture", "strategy-lifecycle", "backtester"]
  },
  {
    slug: "architecture",
    title: "Architecture",
    eyebrow: "System design",
    description:
      "A curated architecture view of the Python modules: data, engines, aggregation, strategies, backtester, execution boundary, and reports.",
    type: "Concept",
    version: currentVersion,
    audience: ["Developers"],
    tags: ["architecture", "modules", "src/crypt", "src/backtester", "closed candles"],
    sourceRefs: ["src/crypt", "src/backtester", "docs/architecture.md"],
    sections: [
      {
        heading: "The stable boundary",
        body: [
          "Research and live behavior should share pure decision logic where possible. The UI explains that boundary without exposing live account state or runtime secrets.",
          "Data and indicators must be causal: public documentation should reinforce the repository rule that features use closed candles only."
        ],
        bullets: [
          "`src/crypt/data` handles ingestion and local store access.",
          "`src/crypt/engines` computes domain signals.",
          "`src/crypt/aggregator` combines evidence into decisions.",
          "`src/backtester` replays strategies and reports money metrics.",
          "`src/crypt/execution` owns exchange-facing execution concepts."
        ]
      },
      {
        heading: "Why the docs are curated",
        body: [
          "Large research repositories accumulate history. A public portal should explain the current model first, then link to source evidence. It should not ask readers to reconstruct product meaning from archive notes."
        ]
      }
    ],
    related: ["overview", "for-developers", "live-execution"]
  },
  {
    slug: "strategy-lifecycle",
    title: "Strategy Lifecycle",
    eyebrow: "From hypothesis to archive",
    description:
      "How strategy ideas move from signals and filters into exact backtests, candidate archives, and neutral execution architecture.",
    type: "Concept",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["strategy", "candidate", "portfolio", "discovery", "signals"],
    sourceRefs: ["docs/strategy_benchmark.md", "strategies/README.md", "src/backtester/strategies"],
    sections: [
      {
        heading: "A strategy starts as a testable rule",
        body: [
          "The project treats a strategy as code and configuration that can be replayed. Signals, filters, exits, risk, and portfolio composition must be explicit enough to reproduce.",
          "Promotion is an owner decision, not an automatic claim that a strategy beats every benchmark."
        ],
        bullets: [
          "Define the signal and the market conditions it expects.",
          "Replay on exact historical windows.",
          "Report money, drawdown, fees, and exit behavior.",
          "Archive evidence and known risks before widening scope."
        ]
      }
    ],
    related: ["backtester", "read-results", "risk-limits"]
  },
  {
    slug: "backtester",
    title: "Backtester",
    eyebrow: "Replay lab",
    description:
      "The backtester evaluates strategy behavior against historical candles, costs, execution windows, risk metrics, and report artifacts.",
    type: "Guide",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["backtester", "uv", "pytest", "load-from", "fees", "slippage", "drawdown"],
    sourceRefs: ["README.md", "docs/backtester_regression.md", "src/backtester"],
    sections: [
      {
        heading: "What a backtest proves",
        body: [
          "A backtest proves how a specific strategy definition behaves under a specific data and execution model. It does not prove future returns.",
          "The project reports money metrics after fees and slippage and keeps warmup windows separate from accounting windows when strict replay requires it."
        ]
      }
    ],
    guideSteps: [
      {
        title: "Run a short smoke backtest",
        command:
          "uv run backtester run \\\n  --from 2025-01-01 \\\n  --to 2025-02-01 \\\n  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \\\n  --output results/smoke_v6_sol_2025_01",
        output: [
          "Backtest completed for the selected strategy and window.",
          "Review the generated result directory for trade logs, metrics, and reports.",
          "Use the same strategy file and explicit dates when comparing future runs."
        ],
        explanation:
          "This mirrors the repository README smoke path. It is a bounded workflow for checking that the backtester can load data, run the selected strategy, and write artifacts."
      }
    ],
    related: ["read-results", "for-developers", "risk-limits"]
  },
  {
    slug: "live-execution",
    title: "Live Execution",
    eyebrow: "Public boundary",
    description:
      "A neutral explanation of the execution architecture: decisions can be handed to exchange connectors, while private account state and runtime settings remain outside the public docs.",
    type: "Concept",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["execution", "OKX", "exchange boundary", "telegram", "runtime", "orders"],
    sourceRefs: ["docs/execution/live_execution.md", "src/crypt/execution"],
    sections: [
      {
        heading: "What is public here",
        body: [
          "The site can explain execution concepts: strategy config, signal runner, risk calculation, order client boundary, exchange synchronization, state recovery, and notifications.",
          "The site must not expose current balances, positions, credentials, private Telegram details, or runtime environment values."
        ],
        bullets: [
          "Public: architecture, contracts, failure modes, and safety concepts.",
          "Private: account state, secrets, exact live deployment values, and current positions."
        ]
      }
    ],
    related: ["architecture", "risk-limits", "for-crypto-traders"]
  },
  {
    slug: "read-results",
    title: "Read Results",
    eyebrow: "Reports and evidence",
    description:
      "How to interpret strategy reports: capital, PnL, monthly returns, drawdown, trade count, win rate, profit factor, exits, and risk notes.",
    type: "Guide",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["results", "reports", "PnL", "drawdown", "profit factor", "benchmark"],
    sourceRefs: ["docs/strategy_benchmark.md", "docs/mandate_reporting.md"],
    sections: [
      {
        heading: "Metrics are evidence, not a promise",
        body: [
          "The benchmark document defines how serious strategy comparisons should be reported. It is an optimization target and reporting frame, not a guarantee about future market behavior.",
          "Good reports name the strategy path, symbol, window, capital, PnL, monthly returns, drawdown, trade count, win rate, profit factor, and known risk gaps."
        ]
      }
    ],
    related: ["strategy-lifecycle", "backtester", "risk-limits"]
  },
  {
    slug: "glossary",
    title: "Glossary",
    eyebrow: "Terms",
    description:
      "A curated vocabulary for reading the project: closed candles, warmup, drawdown, slippage, strategy config, execution boundary, and more.",
    type: "Reference",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["glossary", "terms", "definitions", "concepts"],
    sourceRefs: ["README.md", "docs/strategy_benchmark.md", "docs/backtester_regression.md"],
    sections: [
      {
        heading: "Core terms",
        body: [
          "Glossary entries are written for readers who already understand either Python or crypto, but need project-specific meaning."
        ],
        bullets: [
          "Closed candle: a completed candle used to avoid look-ahead bias.",
          "Warmup window: historical data loaded before the accounting window so indicators can initialize.",
          "Drawdown: decline from a reference equity point, reported under project-specific rules.",
          "Execution boundary: the line between pure strategy decisions and exchange-facing operations.",
          "Strategy config: a saved definition of rules, parameters, and portfolio composition."
        ]
      }
    ],
    related: ["overview", "backtester", "risk-limits"]
  },
  {
    slug: "for-developers",
    title: "For Developers",
    eyebrow: "Build with crypt",
    description:
      "A developer path through setup, source layout, strategy code, tests, backtester commands, and public extension points.",
    type: "Guide",
    version: currentVersion,
    audience: ["Developers"],
    tags: ["developers", "setup", "python", "uv", "source", "tests"],
    sourceRefs: ["README.md", "pyproject.toml", "src/crypt", "src/backtester"],
    sections: [
      {
        heading: "Start from source layout",
        body: [
          "Developers should first map the source tree to the project model. Data, engines, aggregation, strategy runtime, and backtester modules each have a distinct job.",
          "Use repository commands with `UV_CACHE_DIR=/tmp/uv-cache` in agent-driven workflows."
        ]
      }
    ],
    guideSteps: [
      {
        title: "Install project dependencies",
        command: "uv sync --all-extras",
        output: ["Creates or updates the Python environment.", "Installs test, typing, and runtime dependencies."],
        explanation:
          "The README uses `uv` as the package manager. Public docs explain the command, while local setup still depends on environment files that are not public content."
      }
    ],
    related: ["architecture", "backtester", "glossary"]
  },
  {
    slug: "for-crypto-traders",
    title: "For Crypto Traders",
    eyebrow: "Read the research",
    description:
      "A crypto-native path through strategy lifecycle, result interpretation, execution boundaries, and risk limits without private operational detail.",
    type: "Guide",
    version: currentVersion,
    audience: ["Crypto Traders"],
    tags: ["traders", "strategy", "risk", "results", "execution"],
    sourceRefs: ["docs/strategy_benchmark.md", "docs/operator.md"],
    sections: [
      {
        heading: "What to look for",
        body: [
          "A useful strategy report explains the test window, capital path, trade count, exit behavior, and drawdown. It also names what the test does not prove.",
          "The public docs describe how the system thinks about research quality and operational boundaries. They do not tell readers what to trade."
        ]
      }
    ],
    related: ["strategy-lifecycle", "read-results", "risk-limits"]
  },
  {
    slug: "risk-limits",
    title: "Risk & Limits",
    eyebrow: "Boundaries",
    description:
      "The project studies automated crypto strategies. Backtests, benchmarks, and architecture notes are research evidence, not investment advice or return guarantees.",
    type: "Risk",
    version: currentVersion,
    audience: ["Developers", "Crypto Traders"],
    tags: ["risk", "limits", "drawdown", "benchmark", "not advice"],
    sourceRefs: ["docs/strategy_benchmark.md", "AGENTS.md"],
    sections: [
      {
        heading: "Public risk position",
        body: [
          "Trading crypto perpetuals can lose money quickly. The site explains research workflows and system architecture; it does not recommend trades, guarantee results, or publish private live-money state.",
          "Backtest performance depends on data, assumptions, fees, slippage, and implementation details. A strategy can be selected for production by the owner even when it does not satisfy the benchmark target."
        ],
        bullets: [
          "No investment advice.",
          "No guaranteed return claims.",
          "No private exchange account data.",
          "No public order-control surface."
        ]
      }
    ],
    related: ["overview", "read-results", "live-execution"]
  }
];

export const glossaryEntries = [
  {
    term: "Closed candle",
    definition: "A completed candle used by indicators and features so the strategy does not read future market data.",
    tags: ["causality", "data", "no look-ahead"]
  },
  {
    term: "Warmup window",
    definition: "History loaded before an accounting window so indicators have enough context before measured trades begin.",
    tags: ["backtester", "indicators"]
  },
  {
    term: "Execution boundary",
    definition: "The boundary between pure strategy decisions and exchange-facing order, sync, and notification systems.",
    tags: ["execution", "architecture"]
  },
  {
    term: "Below-start drawdown",
    definition: "A monthly risk measure that compares realized equity to month-start capital under the project benchmark.",
    tags: ["risk", "benchmark"]
  },
  {
    term: "Strategy config",
    definition: "A versioned strategy definition that records components, parameters, exits, and portfolio composition.",
    tags: ["strategy", "archive"]
  },
  {
    term: "Slippage",
    definition: "A cost assumption for execution price drift between a model price and the actual fill model.",
    tags: ["backtester", "costs"]
  }
];

export function getPage(slug: string) {
  return docPages.find((page) => page.slug === slug);
}

export function getRelatedPages(page: DocPage) {
  return page.related.map(getPage).filter((item): item is DocPage => Boolean(item));
}

export type SearchResult = {
  title: string;
  route: string;
  type: string;
  version: string;
  excerpt: string;
  tags: string[];
  reason: string;
};

type RankedSearchResult = {
  score: number;
  result: SearchResult;
};

export function searchDocs(query: string): SearchResult[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];

  const pageResults = docPages
    .flatMap<RankedSearchResult>((page) => {
      const haystack = [
        page.title,
        page.eyebrow,
        page.description,
        page.type,
        page.audience.join(" "),
        page.tags.join(" "),
        page.sourceRefs.join(" "),
        page.sections.map((section) => `${section.heading} ${section.body.join(" ")} ${section.bullets?.join(" ") ?? ""}`).join(" "),
        page.guideSteps?.map((step) => `${step.title} ${step.command} ${step.output.join(" ")} ${step.explanation}`).join(" ") ?? ""
      ]
        .join(" ")
        .toLowerCase();

      if (!haystack.includes(normalized)) return [];

      let score = 1;
      let reason = "body match";
      if (page.title.toLowerCase().includes(normalized)) {
        score = 5;
        reason = "title match";
      } else if (page.tags.some((tag) => tag.toLowerCase().includes(normalized))) {
        score = 4;
        reason = "tag match";
      } else if (page.sourceRefs.some((ref) => ref.toLowerCase().includes(normalized))) {
        score = 3;
        reason = "source match";
      }

      return [{
        score,
        result: {
          title: page.title,
          route: `/docs/${page.slug}`,
          type: page.type,
          version: page.version,
          excerpt: page.description,
          tags: page.tags.slice(0, 4),
          reason
        } satisfies SearchResult
      }];
    });

  const glossaryResults = glossaryEntries
    .filter((entry) => [entry.term, entry.definition, entry.tags.join(" ")].join(" ").toLowerCase().includes(normalized))
    .map((entry) => ({
      score: entry.term.toLowerCase().includes(normalized) ? 6 : 2,
      result: {
        title: entry.term,
        route: "/docs/glossary",
        type: "Glossary",
        version: currentVersion,
        excerpt: entry.definition,
        tags: entry.tags,
        reason: entry.term.toLowerCase().includes(normalized) ? "glossary term match" : "glossary body match"
      } satisfies SearchResult
    }));

  const mapResults = mapNodes
    .filter((node) => [node.title, node.short, node.tone].join(" ").toLowerCase().includes(normalized))
    .map((node) => ({
      score: node.title.toLowerCase().includes(normalized) ? 6 : 3,
      result: {
        title: node.title,
        route: `/docs/${node.slug}`,
        type: "Map node",
        version: currentVersion,
        excerpt: node.short,
        tags: [node.tone, "architecture", "system map"],
        reason: "architecture node match"
      } satisfies SearchResult
    }));

  return [...pageResults, ...glossaryResults, ...mapResults]
    .sort((a, b) => b.score - a.score || a.result.title.localeCompare(b.result.title))
    .map((item) => item.result)
    .slice(0, 16);
}
