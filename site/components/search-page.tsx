"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { highlight } from "@/components/search-dialog";
import { sections, type SearchDocument } from "@/lib/content";

type SearchResponse = {
  query: string;
  count: number;
  results: Array<SearchDocument & { score: number; snippet: string }>;
};

export function SearchResultsPage() {
  const params = useSearchParams();
  const initialQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [section, setSection] = useState("all");
  const [results, setResults] = useState<SearchResponse["results"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");

    fetch(`/api/search?q=${encodeURIComponent(query)}&section=${encodeURIComponent(section)}`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("Search failed");
        return response.json() as Promise<SearchResponse>;
      })
      .then((data) => setResults(data.results))
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Поисковый индекс сейчас недоступен. Можно перейти по разделам слева.");
          setResults([]);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [query, section]);

  const grouped = useMemo(() => {
    return results.reduce<Record<string, typeof results>>((acc, result) => {
      acc[result.section] = [...(acc[result.section] ?? []), result];
      return acc;
    }, {});
  }, [results]);

  return (
    <div className="doc-page">
      <header className="doc-hero color-blue">
        <div>
          <p className="eyebrow">Discovery room</p>
          <h1>Поиск по документации</h1>
          <p>
            Серверный поиск проходит по curated content: страницам, рецептам,
            glossary, headings и связанным понятиям.
          </p>
        </div>
      </header>
      <section className="search-route">
        <label className="search-field large">
          <Search size={20} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Например: signal, OKX, parity, sink"
          />
        </label>
        <div className="chip-row">
          <button className={section === "all" ? "chip active" : "chip"} onClick={() => setSection("all")}>
            Все
          </button>
          {sections.map((item) => (
            <button key={item.id} className={section === item.title ? "chip active" : "chip"} onClick={() => setSection(item.title)}>
              {item.shortTitle}
            </button>
          ))}
        </div>
      </section>
      {loading && <p className="state-card">Ищу совпадения в серверном индексе...</p>}
      {error && <p className="state-card error">{error}</p>}
      {!loading && !error && results.length === 0 && (
        <section className="empty-results">
          <h2>Ничего не найдено</h2>
          <p>Попробуй более широкий термин или начни с карты системы.</p>
          <div className="chip-row">
            <Link className="chip" href="/">Карта системы</Link>
            <Link className="chip" href="/glossary">Глоссарий</Link>
            <Link className="chip" href="/signal-journey">Путь сигнала</Link>
          </div>
        </section>
      )}
      {!loading &&
        !error &&
        Object.entries(grouped).map(([group, items]) => (
          <section className="result-group" key={group}>
            <h2>{group}</h2>
            {items.map((item) => (
              <Link className="search-result large" href={item.href} key={item.id}>
                <span>{item.type}</span>
                <strong>{highlight(item.title, query)}</strong>
                <small>{highlight(item.snippet, query)}</small>
              </Link>
            ))}
          </section>
        ))}
    </div>
  );
}
