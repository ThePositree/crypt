import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";
import { FlowDiagram, liveFlow } from "@/components/flow-diagram";

export const metadata: Metadata = {
  title: "Live execution",
  description: "Public-safe live OKX execution runtime flow.",
};

export default function LivePage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        <FlowDiagram nodes={liveFlow} />
      </div>
      <DocPage slug="live-execution" />
    </>
  );
}
