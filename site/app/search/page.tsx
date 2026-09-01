import Link from "next/link";
import { Search } from "lucide-react";
import { searchDocs } from "@/lib/content";

export const metadata = {
  title: "Search",
  description: "Search curated public crypt docs."
};

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const results = searchDocs(q);

  return (
    <div className="search-route">
      <header className="doc-hero">
        <p className="eyebrow">Global search</p>
        <h1>Search public docs</h1>
        <p>Search is backed by the curated public index: pages, guide steps, glossary terms, source notes, and map nodes.</p>
      </header>

      <form className="search-page-form">
        <Search size={18} aria-hidden="true" />
        <input name="q" defaultValue={q} placeholder="Try backtester, risk, OKX, closed candles..." aria-label="Search query" />
        <button type="submit">Search</button>
      </form>

      <section className="search-page-results">
        {q ? <p>{results.length ? `${results.length} result${results.length === 1 ? "" : "s"} for "${q}"` : `No results for "${q}"`}</p> : <p>Enter a term to search curated public docs.</p>}
        {results.map((result) => (
          <Link className="search-result" href={result.route} key={`${result.type}-${result.title}`}>
            <span>
              {result.title}
              <small>{result.route}</small>
            </span>
            <em>{result.type} · {result.reason}</em>
            <p>{result.excerpt}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
