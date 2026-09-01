import Link from "next/link";
import { ArrowRight, BookOpen, Code2, Search, ShieldCheck } from "lucide-react";
import { DocsTownMap } from "@/components/DocsTownMap";
import { Mascot } from "@/components/Mascot";
import { docPages, glossaryEntries, mapNodes } from "@/lib/content";

const featured = ["overview", "architecture", "strategy-lifecycle", "backtester", "live-execution", "risk-limits"];

export default function Home() {
  const featuredPages = featured.map((slug) => docPages.find((page) => page.slug === slug)).filter(Boolean);

  return (
    <div className="home-page">
      <DocsTownMap />

      <section className="journey-band" aria-label="Role journeys">
        <article>
          <Code2 size={22} aria-hidden="true" />
          <h2>Developer path</h2>
          <p>Move from source layout to strategy code, backtester commands, search index entries, and public references.</p>
          <Link href="/docs/for-developers">
            Follow developer path <ArrowRight size={15} />
          </Link>
        </article>
        <article>
          <BookOpen size={22} aria-hidden="true" />
          <h2>Crypto trader path</h2>
          <p>Read strategy lifecycle, result reports, execution boundaries, glossary terms, and risk limits without private data.</p>
          <Link href="/docs/for-crypto-traders">
            Follow trader path <ArrowRight size={15} />
          </Link>
        </article>
        <article>
          <Search size={22} aria-hidden="true" />
          <h2>Search everything public</h2>
          <p>Backend search covers curated pages, guide steps, glossary terms, architecture nodes, tags, and source notes.</p>
          <Link href="/search?q=backtester">
            Try search route <ArrowRight size={15} />
          </Link>
        </article>
      </section>

      <section className="page-grid" aria-labelledby="curated-pages">
        <div className="section-title">
          <p className="eyebrow">Curated pages</p>
          <h2 id="curated-pages">Every major subsystem has a place</h2>
          <p>These pages are written for the public portal. They cite repository truth without copying private operations into the site.</p>
        </div>
        <div className="cards-grid">
          {featuredPages.map((page) =>
            page ? (
              <Link className="page-card" href={`/docs/${page.slug}`} key={page.slug}>
                <span>{page.eyebrow}</span>
                <strong>{page.title}</strong>
                <p>{page.description}</p>
              </Link>
            ) : null
          )}
        </div>
      </section>

      <section className="wide-band" aria-label="Guide and risk samples">
        <article className="guide-preview">
          <div className="section-title compact">
            <p className="eyebrow">Guide pattern</p>
            <h2>Command, output, explanation</h2>
          </div>
          <div className="guide-preview-grid">
            <div>
              <span>Command</span>
              <code>uv run backtester run --from 2025-01-01 ...</code>
            </div>
            <div>
              <span>Expected output</span>
              <p>Generated report directory with metrics, trade log, and readable artifacts.</p>
            </div>
            <div>
              <span>Explanation</span>
              <p>The guide explains what the command proves and where the source path lives.</p>
            </div>
          </div>
        </article>
        <article className="risk-preview">
          <ShieldCheck size={24} aria-hidden="true" />
          <h2>Risk lives in one clear section</h2>
          <p>
            The site explains research workflows. It does not promise returns, publish private live state, or tell readers what to trade.
          </p>
          <Link href="/docs/risk-limits">
            Read Risk & Limits <ArrowRight size={15} />
          </Link>
          <Mascot mood="risk" />
        </article>
      </section>

      <section className="coverage-strip" aria-label="Coverage summary">
        <div>
          <strong>{docPages.length}</strong>
          <span>curated pages</span>
        </div>
        <div>
          <strong>{mapNodes.length}</strong>
          <span>map regions</span>
        </div>
        <div>
          <strong>{glossaryEntries.length}</strong>
          <span>glossary terms</span>
        </div>
      </section>
    </div>
  );
}
