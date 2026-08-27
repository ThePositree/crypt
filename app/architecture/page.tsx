import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";
import { FlowDiagram, architectureFlow } from "@/components/flow-diagram";

export const metadata: Metadata = {
  title: "Architecture",
  description: "System overview, module boundaries, and execution model for crypt.",
};

export default function ArchitecturePage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        <FlowDiagram nodes={architectureFlow} />
      </div>
      <DocPage slug="architecture" />
    </>
  );
}
