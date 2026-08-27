"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { SearchEntry } from "@/lib/docs";

export function SearchBox({ index }: { index: SearchEntry[] }) {
  const [query, setQuery] = useState("");
  const normalized = query.trim().toLowerCase();

  const results = useMemo(() => {
    if (normalized.length < 2) {
      return [];
    }

    const tokens = normalized.split(/\s+/).filter(Boolean);

    return index
      .map((entry) => {
        const score = tokens.reduce(
          (total, token) => total + (entry.text.includes(token) ? 1 : 0),
          0,
        );
        return { entry, score };
      })
      .filter((result) => result.score > 0)
      .sort(
        (left, right) =>
          right.score - left.score || left.entry.title.localeCompare(right.entry.title),
      )
      .slice(0, 6);
  }, [index, normalized]);

  return (
    <div className="relative">
      <label className="sr-only" htmlFor="site-search">
        Search documentation
      </label>
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#8a7b6d]"
        size={16}
      />
      <input
        autoComplete="off"
        className="h-10 w-full rounded-lg border border-[#d9c4ae] bg-white/72 pl-9 pr-3 text-sm text-[#332f2b] outline-none transition placeholder:text-[#8a7b6d] focus:border-[#77b6cb] focus:ring-2 focus:ring-[#b9dce8]/60"
        id="site-search"
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search docs..."
        value={query}
      />
      {normalized.length >= 2 ? (
        <div className="absolute right-0 top-12 z-50 w-full min-w-80 rounded-lg border border-[#d9c4ae] bg-[#fff8ef] p-2 shadow-xl shadow-[#6f6860]/10">
          {results.length > 0 ? (
            <div className="grid gap-1">
              {results.map(({ entry }) => (
                <Link
                  className="rounded-lg px-3 py-2 transition hover:bg-white"
                  href={`/docs/${entry.slug}`}
                  key={entry.slug}
                  onClick={() => setQuery("")}
                >
                  <span className="block text-xs font-semibold uppercase text-[#6f6860]">
                    {entry.section}
                  </span>
                  <span className="block text-sm font-semibold text-[#332f2b]">{entry.title}</span>
                  <span className="block text-xs leading-5 text-[#6f6860]">
                    {entry.description}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="px-3 py-4 text-sm text-[#6f6860]">No matching docs.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}
