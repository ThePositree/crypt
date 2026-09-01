import Link from "next/link";
import { ArrowRight, BookMarked } from "lucide-react";
import type { DocPage } from "@/lib/content";
import { getRelatedPages } from "@/lib/content";
import { GuideStep } from "./GuideStep";

export function PageSections({ page }: { page: DocPage }) {
  const related = getRelatedPages(page);

  return (
    <article className="doc-page">
      <header className="doc-hero">
        <p className="eyebrow">{page.eyebrow}</p>
        <h1>{page.title}</h1>
        <p>{page.description}</p>
        <div className="meta-row">
          <span>{page.type}</span>
          <span>{page.version}</span>
          {page.audience.map((audience) => (
            <span key={audience}>{audience}</span>
          ))}
        </div>
      </header>

      <div className="doc-layout">
        <div className="doc-body">
          {page.sections.map((section) => (
            <section className="doc-section" key={section.heading}>
              <h2>{section.heading}</h2>
              {section.body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {section.bullets ? (
                <ul>
                  {section.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}

          {page.guideSteps?.map((step) => <GuideStep key={step.title} step={step} />)}
        </div>

        <aside className="doc-rail">
          <section>
            <h2>Source notes</h2>
            {page.sourceRefs.map((ref) => (
              <code key={ref}>{ref}</code>
            ))}
          </section>

          <section>
            <h2>Related docs</h2>
            {related.map((item) => (
              <Link href={`/docs/${item.slug}`} key={item.slug}>
                <BookMarked size={15} aria-hidden="true" />
                <span>{item.title}</span>
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            ))}
          </section>
        </aside>
      </div>
    </article>
  );
}
