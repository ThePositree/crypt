import type { Metadata } from "next";
import { DocPage } from "@/components/doc-page";

export const metadata: Metadata = {
  title: "CLI",
  description: "Backtester CLI reference and command conventions.",
};

export default function CliPage() {
  return <DocPage slug="cli" />;
}
