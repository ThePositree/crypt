import Link from "next/link";
import { ArrowLeft, BookOpen } from "lucide-react";
import { getSection, type DocPage } from "@/lib/content";
import {
  CharacterPanel,
  ContractAccordion,
  DocTabs,
  FailureModes,
  RecipeList,
  RelatedLinks,
} from "@/components/portal-widgets";

export function CuratedDocPage({ page }: { page: DocPage }) {
  const section = getSection(page.id);
  const Icon = section?.icon ?? BookOpen;

  return (
    <article className="doc-page">
      <Link href="/" className="back-link">
        <ArrowLeft size={16} />
        К карте системы
      </Link>
      <header className={`doc-hero color-${section?.color ?? "rose"}`}>
        <div>
          <p className="eyebrow">{page.eyebrow}</p>
          <h1>{page.title}</h1>
          <p>{page.summary}</p>
        </div>
        <Icon className="hero-icon" size={48} />
      </header>
      <CharacterPanel name={page.character} role={page.characterRole} variant="wide" />
      <DocTabs page={page} />
      <ContractAccordion title="Контракты и инварианты" items={page.contracts} />
      <RecipeList page={page} />
      <FailureModes items={page.failureModes} />
      <RelatedLinks ids={page.related} terms={page.glossaryTerms} />
      <section className="source-panel">
        <h2>Источник для курации</h2>
        <p>Эти документы и области кода использовались как evidence для страницы; UI не рендерит их напрямую.</p>
        <div className="chip-row">
          {page.sources.map((source) => (
            <span className="chip" key={source}>
              {source}
            </span>
          ))}
        </div>
      </section>
    </article>
  );
}
