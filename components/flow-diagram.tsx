import { ArrowRight } from "lucide-react";

type FlowNode = {
  title: string;
  body: string;
  tone: "runtime" | "research" | "backtester" | "warning" | "neutral";
};

const toneClass = {
  runtime: "border-[#8bc5d8] bg-[#dff2f8]",
  research: "border-[#e9c85f] bg-[#fff0b8]",
  backtester: "border-[#8dc79d] bg-[#ddf3e4]",
  warning: "border-[#df8d80] bg-[#ffe1db]",
  neutral: "border-[#d9c4ae] bg-white/62",
};

export function FlowDiagram({ nodes }: { nodes: FlowNode[] }) {
  return (
    <div className="my-8 rounded-lg border border-[#ead7c3] bg-white/42 p-4">
      <div className="flex flex-col gap-3 lg:flex-row">
        {nodes.map((node, index) => (
          <div className="flex flex-col gap-3 lg:flex-1 lg:flex-row" key={node.title}>
            <div className={`min-h-32 flex-1 rounded-lg border p-4 ${toneClass[node.tone]}`}>
              <div className="mb-2 text-sm font-black text-[#332f2b]">{node.title}</div>
              <p className="text-sm leading-6 text-[#5f574f]">{node.body}</p>
            </div>
            {index < nodes.length - 1 ? (
              <div className="hidden items-center text-[#8a7b6d] lg:flex">
                <ArrowRight aria-hidden="true" size={18} />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export const architectureFlow: FlowNode[] = [
  {
    title: "Config and data",
    body: "Runtime configuration and normalized market data feed the evaluation path.",
    tone: "neutral",
  },
  {
    title: "Evaluation context",
    body: "Per-symbol context is fully populated before engines run.",
    tone: "runtime",
  },
  {
    title: "Engines",
    body: "Trend, mean reversion, derivatives, volatility, SMC, and regime logic emit signals.",
    tone: "research",
  },
  {
    title: "Decision",
    body: "Aggregator and filters produce a verdict for sinks or execution.",
    tone: "backtester",
  },
];

export const liveFlow: FlowNode[] = [
  {
    title: "Runtime config",
    body: "The loaded strategy JSON and env decide what live execution actually runs.",
    tone: "warning",
  },
  {
    title: "Exchange sync",
    body: "OKX positions, fills, fees, and orders are reconciled before money-path actions.",
    tone: "runtime",
  },
  {
    title: "Order path",
    body: "Signals pass through risk and precision rules before placement or blocking.",
    tone: "backtester",
  },
  {
    title: "State and reporting",
    body: "Durable state and Telegram reports reflect the operator-facing runtime.",
    tone: "research",
  },
];
