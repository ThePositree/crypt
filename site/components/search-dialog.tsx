"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { learningRoutes, type SearchDocument } from "@/lib/content";

type SearchResponse = {
  query: string;
  count: number;
  results: Array<SearchDocument & { score: number; snippet: string }>;
};

export function SearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse["results"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Search index failed");
        const data = (await response.json()) as SearchResponse;
        setResults(data.results);
      } catch (searchError) {
        if (!controller.signal.aborted) {
          setError("Индекс поиска не ответил. Навигация по разделам остаётся доступной.");
          setResults([]);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 120);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, query]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
      if (event.key === "Escape" && open) {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, open]);

  const popular = useMemo(() => ["signal", "strategy", "OKX", "risk", "parity"], []);

  if (!open) return null;

  return (
    <div className="search-overlay" role="dialog" aria-modal="true" aria-label="Поиск по документации">
      <div className="search-panel">
        <div className="search-head">
          <div>
            <p className="eyebrow">Серверный поиск</p>
            <h2>Искать в crypt docs</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Закрыть поиск">
            <X size={18} />
          </button>
        </div>
        <label className="search-field">
          <Search size={18} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="strategy, signal, OKX, parity..."
          />
        </label>
        {!query && (
          <div className="suggestion-block">
            <p className="muted">Пустой запрос показывает маршруты обучения.</p>
            <div className="chip-row">
              {popular.map((item) => (
                <button key={item} className="chip" type="button" onClick={() => setQuery(item)}>
                  {item}
                </button>
              ))}
            </div>
            <div className="route-suggestions">
              {learningRoutes.map((route) => (
                <Link key={route.href} href={route.href} onClick={onClose}>
                  <strong>{route.title}</strong>
                  <span>{route.summary}</span>
                </Link>
              ))}
            </div>
          </div>
        )}
        {query && (
          <div className="result-list" role="listbox" aria-label="Подсказки поиска">
            {loading && <p className="state-card">Ищу по curated content...</p>}
            {error && <p className="state-card error">{error}</p>}
            {!loading && !error && results.length === 0 && (
              <p className="state-card">Ничего не найдено. Попробуй broader term или открой глоссарий.</p>
            )}
            {!loading &&
              !error &&
              results.slice(0, 7).map((result) => (
                <Link key={result.id} href={result.href} onClick={onClose} className="search-result">
                  <span>{result.section}</span>
                  <strong>{highlight(result.title, query)}</strong>
                  <small>{highlight(result.snippet, query)}</small>
                </Link>
              ))}
          </div>
        )}
        <Link
          href={`/search${query ? `?q=${encodeURIComponent(query)}` : ""}`}
          className="primary-link"
          onClick={onClose}
        >
          Все результаты
        </Link>
      </div>
    </div>
  );
}

export function highlight(text: string, query: string) {
  const terms = query.trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return text;
  const pattern = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi");
  return text.split(pattern).map((part, index) =>
    terms.some((term) => part.toLowerCase() === term.toLowerCase()) ? (
      <mark key={`${part}-${index}`}>{part}</mark>
    ) : (
      part
    ),
  );
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
