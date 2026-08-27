import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "Backtester",
  description: "Backtester documentation and reproducibility checkpoints.",
};

export default function BacktesterPage() {
  return <DocPage slug="backtester-regression" />;
}
