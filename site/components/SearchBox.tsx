"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import type { SearchResult } from "@/lib/content";
import { Mascot } from "./Mascot";

type SearchState = "idle" | "loading" | "ready" | "empty" | "error";

export function SearchBox({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>("idle");
  const [results, setResults] = useState<SearchResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const grouped = useMemo(() => {
    return results.reduce<Record<string, SearchResult[]>>((groups, result) => {
      groups[result.type] ??= [];
      groups[result.type].push(result);
      return groups;
    }, {});
  }, [results]);

  async function runSearch(nextQuery: string) {
    setQuery(nextQuery);
    if (!nextQuery.trim()) {
      setResults([]);
      setState("idle");
      return;
    }

    setState("loading");
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(nextQuery)}`);
      if (!response.ok) throw new Error(`Search failed: ${response.status}`);
      const payload = (await response.json()) as { results: SearchResult[] };
      setResults(payload.results);
      setState(payload.results.length ? "ready" : "empty");
    } catch {
      setResults([]);
      setState("error");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch(query);
  }

  return (
    <>
      <button className={compact ? "search-trigger compact" : "search-trigger"} onClick={() => setOpen(true)} type="button">
        <Search size={18} aria-hidden="true" />
        <span>Search all public docs</span>
        <kbd>⌘K</kbd>
      </button>

      {open ? (
        <div className="search-overlay" role="dialog" aria-modal="true" aria-label="Search public docs">
          <div className="search-modal">
            <form className="search-form" onSubmit={submit}>
              <Search size={18} aria-hidden="true" />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => void runSearch(event.target.value)}
                placeholder="Search backtester, risk, OKX, closed candles..."
                aria-label="Search query"
              />
              <button aria-label="Close search" onClick={() => setOpen(false)} type="button">
                <X size={18} />
              </button>
            </form>

            <div className="search-body">
              {state === "idle" ? (
                <SearchEmpty title="Start with a system word" body="Try backtester, strategy lifecycle, risk, OKX, fees, or closed candles." />
              ) : null}

              {state === "loading" ? (
                <div className="search-skeleton" aria-label="Search loading">
                  <span />
                  <span />
                  <span />
                </div>
              ) : null}

              {state === "empty" ? (
                <SearchEmpty title="No results found" body="Only curated public docs are indexed. Try a broader subsystem or open the Docs Town map." />
              ) : null}

              {state === "error" ? (
                <SearchEmpty title="Search failed" body="Retry the query or use topic navigation while the backend search route recovers." tone="error" />
              ) : null}

              {state === "ready"
                ? Object.entries(grouped).map(([group, groupResults]) => (
                    <section className="search-group" key={group}>
                      <h3>{group}</h3>
                      {groupResults.map((result) => (
                        <Link className="search-result" href={result.route} key={`${result.type}-${result.title}`} onClick={() => setOpen(false)}>
                          <span>
                            {result.title}
                            <small>{result.route}</small>
                          </span>
                          <em>{result.reason}</em>
                          <p>{result.excerpt}</p>
                        </Link>
                      ))}
                    </section>
                  ))
                : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function SearchEmpty({ title, body, tone }: { title: string; body: string; tone?: "error" }) {
  return (
    <div className={`search-empty ${tone === "error" ? "error" : ""}`}>
      <Mascot mood={tone === "error" ? "risk" : "search"} />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
