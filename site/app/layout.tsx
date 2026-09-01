import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: {
    default: "crypt Docs Town",
    template: "%s | crypt Docs Town"
  },
  description:
    "Public curated docs for crypt, a Python research desk for crypto strategy discovery, backtesting, and execution architecture.",
  metadataBase: new URL("https://crypt-docs.example")
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
