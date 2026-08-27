import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "API and contracts",
  description: "Internal data contracts and module API boundaries.",
};

export default function ApiPage() {
  return <DocPage slug="api-contracts" />;
}
