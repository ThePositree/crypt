import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { TopNav } from "@/components/top-nav";
import { getSearchIndex } from "@/lib/docs";

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: {
    default: "crypt docs",
    template: "%s | crypt",
  },
  description:
    "Public documentation for crypt, a crypto perpetual strategy research workbench and live OKX execution module.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const searchIndex = getSearchIndex();

  return (
    <html
      className={`${geistSans.variable} ${geistMono.variable}`}
      data-scroll-behavior="smooth"
      lang="en"
    >
      <body>
        <TopNav searchIndex={searchIndex} />
        {children}
      </body>
    </html>
  );
}
