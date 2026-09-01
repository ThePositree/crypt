import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "crypt Docs Portal",
  description:
    "A curated lo-fi docs portal for the crypt research workbench and optional OKX execution runtime.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
