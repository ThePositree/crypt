"use client";

import { BookOpen, Boxes, FlaskConical, Menu, Microscope, Search, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { SearchBox } from "@/components/search-box";
import type { SearchEntry } from "@/lib/docs";

const links = [
  { href: "/docs", label: "Docs", icon: BookOpen },
  { href: "/architecture", label: "Architecture", icon: Boxes },
  { href: "/research", label: "Research", icon: FlaskConical },
  { href: "/backtester", label: "Backtester", icon: Microscope },
];

export function TopNav({ searchIndex = [] }: { searchIndex?: SearchEntry[] }) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-[#ead7c3]/80 bg-[#fff8ef]/88 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 w-full max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link className="flex shrink-0 items-center gap-2" href="/">
          <span className="grid size-9 place-items-center rounded-lg border border-[#d9c4ae] bg-[#fff1df] font-mono text-sm font-bold text-[#332f2b]">
            cr
          </span>
          <span className="font-mono text-lg font-semibold">crypt</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                className={`flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium transition ${
                  active
                    ? "bg-[#b9dce8]/55 text-[#263d46]"
                    : "text-[#6f6860] hover:bg-white/60 hover:text-[#332f2b]"
                }`}
                href={href}
                key={href}
              >
                <Icon aria-hidden="true" size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto hidden w-full max-w-md md:block">
          <SearchBox index={searchIndex} />
        </div>

        <button
          aria-expanded={isOpen}
          aria-label="Toggle navigation"
          className="ml-auto grid size-10 place-items-center rounded-lg border border-[#d9c4ae] bg-white/55 text-[#332f2b] md:hidden"
          onClick={() => setIsOpen((value) => !value)}
          type="button"
        >
          {isOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {isOpen ? (
        <div className="border-t border-[#ead7c3]/80 bg-[#fff8ef] px-4 pb-4 md:hidden">
          <div className="py-3">
            <SearchBox index={searchIndex} />
          </div>
          <nav className="grid gap-1">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                className="flex h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium text-[#332f2b] hover:bg-white/70"
                href={href}
                key={href}
                onClick={() => setIsOpen(false)}
              >
                <Icon aria-hidden="true" size={16} />
                {label}
              </Link>
            ))}
            <Link
              className="flex h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium text-[#332f2b] hover:bg-white/70"
              href="/docs"
              onClick={() => setIsOpen(false)}
            >
              <Search aria-hidden="true" size={16} />
              Search docs
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
