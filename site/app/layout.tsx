import type { Metadata } from "next";
import { PortalShell } from "@/components/shell";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "crypt docs",
    template: "%s | crypt docs",
  },
  description:
    "Курируемая русская документация о том, как устроен crypt: данные, стратегии, бэктестер, live execution и операционные сценарии.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <PortalShell>{children}</PortalShell>
      </body>
    </html>
  );
}
