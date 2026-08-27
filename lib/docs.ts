import fs from "node:fs";
import path from "node:path";

export type DocSection =
  | "Start"
  | "Architecture"
  | "Research"
  | "Backtester"
  | "Live"
  | "Setup"
  | "CLI"
  | "API"
  | "Archive";

export type DocMeta = {
  slug: string;
  title: string;
  description: string;
  section: DocSection;
  sourcePath: string;
};

export type Heading = {
  id: string;
  title: string;
  depth: number;
};

export type LoadedDoc = DocMeta & {
  content: string;
  headings: Heading[];
};

export type SearchEntry = {
  slug: string;
  title: string;
  section: DocSection;
  description: string;
  text: string;
};

export const docs: DocMeta[] = [
  {
    slug: "overview",
    title: "Project overview",
    description: "What crypt is, how the workbench is shaped, and where to start.",
    section: "Start",
    sourcePath: "README.md",
  },
  {
    slug: "architecture",
    title: "Architecture",
    description: "System overview, module boundaries, data contracts, and failure model.",
    section: "Architecture",
    sourcePath: "docs/architecture.md",
  },
  {
    slug: "research",
    title: "Research workbench",
    description: "Strategy discovery, benchmark framing, and research archives.",
    section: "Research",
    sourcePath: "docs/strategy_discovery.md",
  },
  {
    slug: "strategy-benchmark",
    title: "Strategy benchmark",
    description: "Money benchmark, reporting target, and risk interpretation policy.",
    section: "Research",
    sourcePath: "docs/strategy_benchmark.md",
  },
  {
    slug: "candidate-archive",
    title: "Candidate archive",
    description: "Frozen candidate research map and archived strategy lines.",
    section: "Archive",
    sourcePath: "docs/archive/candidates/README.md",
  },
  {
    slug: "router-archive",
    title: "Router archive",
    description: "Archived router experiments and their public context.",
    section: "Archive",
    sourcePath: "docs/archive/routers/README.md",
  },
  {
    slug: "backtester",
    title: "Backtester",
    description: "Backtester role, exact execution simulation, and command entry points.",
    section: "Backtester",
    sourcePath: "docs/backtest.md",
  },
  {
    slug: "backtester-regression",
    title: "Backtester regression",
    description: "Strict checkpoints for detecting parity drift.",
    section: "Backtester",
    sourcePath: "docs/backtester_regression.md",
  },
  {
    slug: "live-execution",
    title: "Live execution",
    description: "Public-safe live OKX execution flow and runtime truth hierarchy.",
    section: "Live",
    sourcePath: "docs/execution/live_execution.md",
  },
  {
    slug: "live-reconciliation",
    title: "Live/backtest reconciliation",
    description: "Phase reconciliation context between live behavior and replay.",
    section: "Live",
    sourcePath: "docs/execution/live_backtest_reconciliation_2026-07-28.md",
  },
  {
    slug: "setup",
    title: "Setup",
    description: "Local setup, smoke runs, and dry-run execution commands.",
    section: "Setup",
    sourcePath: "README.md",
  },
  {
    slug: "cli",
    title: "CLI",
    description: "Backtester CLI runbook and command conventions.",
    section: "CLI",
    sourcePath: "docs/cli.md",
  },
  {
    slug: "api-contracts",
    title: "API and contracts",
    description: "Internal contracts, models, and module API boundaries.",
    section: "API",
    sourcePath: "docs/architecture.md",
  },
];

export const navDocs = docs.filter((doc) =>
  ["overview", "architecture", "research", "backtester", "live-execution"].includes(doc.slug),
);

const contentDirectory = path.join(process.cwd(), "content", "docs");

export function getDoc(slug: string): LoadedDoc {
  const meta = docs.find((doc) => doc.slug === slug);

  if (!meta) {
    throw new Error(`Unknown doc slug: ${slug}`);
  }

  const filePath = path.join(contentDirectory, `${slug}.md`);
  const content = fs.readFileSync(filePath, "utf8").trim();

  return {
    ...meta,
    content,
    headings: getHeadings(content),
  };
}

export function getAllDocs(): LoadedDoc[] {
  return docs.map((doc) => getDoc(doc.slug));
}

export function getSearchIndex(): SearchEntry[] {
  return getAllDocs().map((doc) => ({
    slug: doc.slug,
    title: doc.title,
    section: doc.section,
    description: doc.description,
    text: normalizeForSearch(`${doc.title} ${doc.description} ${stripMarkdown(doc.content)}`),
  }));
}

export function getDocsBySection(): Map<DocSection, DocMeta[]> {
  const groups = new Map<DocSection, DocMeta[]>();

  for (const doc of docs) {
    groups.set(doc.section, [...(groups.get(doc.section) ?? []), doc]);
  }

  return groups;
}

export function sourceUrl(sourcePath: string): string {
  return `/${sourcePath}`;
}

function getHeadings(markdown: string): Heading[] {
  return markdown
    .split("\n")
    .map((line) => /^(#{2,3})\s+(.+)$/.exec(line))
    .filter((match): match is RegExpExecArray => Boolean(match))
    .map((match) => ({
      depth: match[1].length,
      title: match[2].replace(/`/g, "").trim(),
      id: slugify(match[2]),
    }));
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/`/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function stripMarkdown(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*]\([^)]*\)/g, " ")
    .replace(/\[[^\]]*]\(([^)]*)\)/g, " ")
    .replace(/[#>*_\-|]/g, " ")
    .replace(/\s+/g, " ");
}

function normalizeForSearch(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}
