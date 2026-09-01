"use client";

import { Search, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { getSearchIndex } from "@/lib/portal-content";

export function SearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const index = useMemo(() => getSearchIndex(), []);
  const normalizedQuery = query.trim().toLowerCase();
  const results = normalizedQuery
    ? index
        .map((item) => ({
          ...item,
          score: normalizedQuery
            .split(/\s+/)
            .filter((token) => item.content.includes(token)).length,
        }))
        .filter((item) => item.score > 0)
        .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    : index.slice(0, 5);

  return (
    <>
      <button
        id="search"
        type="button"
        onClick={() => setOpen(true)}
        className="focus-ring hand-drawn flex min-h-12 w-full items-center gap-3 rounded-xl bg-white/82 px-4 text-left text-sm text-[#5f5868] transition hover:-translate-y-0.5 hover:bg-white md:w-80"
        aria-haspopup="dialog"
      >
        <Search className="size-5" aria-hidden="true" />
        <span className="flex-1">Search architecture, runtime, risk...</span>
        <kbd className="hidden rounded-md border border-[#3b3340] bg-[#fff8ea] px-2 py-1 text-xs text-[#726a79] sm:inline">
          /
        </kbd>
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 bg-[#2d2a32]/35 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Search portal"
        >
          <div className="paper-card mx-auto mt-8 max-w-2xl rounded-2xl bg-[#fff8ea] p-4 md:mt-20 md:p-5">
            <div className="flex items-center gap-3">
              <Search className="size-5 shrink-0" aria-hidden="true" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search every curated page..."
                className="focus-ring min-h-12 flex-1 rounded-xl border-2 border-[#3b3340] bg-white/80 px-3 outline-none"
              />
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="focus-ring rounded-xl border-2 border-[#3b3340] bg-[#f5b9c6] p-3 shadow-[3px_3px_0_rgba(45,42,50,0.16)]"
                aria-label="Close search"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>

            <div className="mt-4 max-h-[60vh] space-y-3 overflow-y-auto pr-1">
              {results.length ? (
                results.map((result) => (
                  <Link
                    key={result.slug}
                    href={`/docs/${result.slug}`}
                    onClick={() => setOpen(false)}
                    className="focus-ring block rounded-xl border-2 border-[#3b3340] bg-white/75 p-4 transition hover:-translate-y-0.5 hover:bg-[#e6f2ed]"
                  >
                    <div className="text-base font-black">{result.title}</div>
                    <p className="mt-1 text-sm leading-6 text-[#5f5868]">{result.summary}</p>
                  </Link>
                ))
              ) : (
                <div className="rounded-xl border-2 border-dashed border-[#3b3340] bg-white/70 p-5">
                  <div className="font-black">No page matched that search.</div>
                  <p className="mt-1 text-sm leading-6 text-[#5f5868]">
                    Try a system word like backtester, runtime, archive, candles, risk, or runbook.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
