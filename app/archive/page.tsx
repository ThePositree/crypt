import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "Archive",
  description: "Public strategy candidate and router archive context.",
};

export default function ArchivePage() {
  return <DocPage slug="candidate-archive" />;
}
