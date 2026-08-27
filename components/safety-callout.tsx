const callouts = {
  "live-execution": {
    label: "Runtime truth",
    body: "Live-money behavior is resolved from loaded runtime configuration and exchange state. Public docs explain the flow; they are not a substitute for OKX fills, orders, positions, fees, account equity, or deployed environment variables.",
  },
  "backtester-regression": {
    label: "Correctness guard",
    body: "Backtester checks are strict drift detectors. Indicators and features must use closed candles only, and replay boundaries matter for live/backtest parity.",
  },
  "strategy-benchmark": {
    label: "Benchmark caveat",
    body: "The benchmark is a reporting and optimization target, not a production veto. Owner-promoted runtime configuration remains the operational source of truth.",
  },
};

export type SafetyCalloutSlug = keyof typeof callouts;

export function hasSafetyCallout(slug: string): slug is SafetyCalloutSlug {
  return slug in callouts;
}

export function SafetyCallout({ slug }: { slug: SafetyCalloutSlug }) {
  const callout = callouts[slug];

  return (
    <div className="mb-8 rounded-lg border border-[#df8d80] bg-[#ffe1db] p-4 text-[#5a312b]">
      <div className="mb-1 text-sm font-black uppercase">{callout.label}</div>
      <p className="text-sm leading-6">{callout.body}</p>
    </div>
  );
}
