import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "Setup",
  description: "Local setup and smoke command entry points.",
};

export default function SetupPage() {
  return <DocPage slug="setup" />;
}
