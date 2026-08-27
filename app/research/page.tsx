import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "Research",
  description: "Strategy discovery, benchmark policy, and public archive context.",
};

export default function ResearchPage() {
  return <DocPage slug="research" />;
}
