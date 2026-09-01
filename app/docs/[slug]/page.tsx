import Link from "next/link";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { notFound } from "next/navigation";
import { ArchitectureMap } from "@/components/architecture-map";
import { ModuleTabs } from "@/components/module-tabs";
import { PageCard } from "@/components/page-card";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { PortalShell } from "@/components/portal-shell";
import { getPortalPage, getRelatedPages, portalPages } from "@/lib/portal-content";

const accentClass = {
  mint: "bg-[#bfe8d0]",
  sky: "bg-[#b9d8f2]",
  lavender: "bg-[#d7c6f1]",
  rose: "bg-[#f5b9c6]",
  lemon: "bg-[#f7e8a6]",
};

export function generateStaticParams() {
  return portalPages.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getPortalPage(slug);
  return {
    title: page ? `${page.title} | crypt Docs Portal` : "crypt Docs Portal",
    description: page?.summary,
  };
}

export default async function DocsPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getPortalPage(slug);

  if (!page) {
    notFound();
  }

  const Icon = page.icon;
  const relatedPages = getRelatedPages(page);

  return (
    <PortalShell activeSlug={page.slug}>
      <article className="space-y-6">
        <Link
          href="/"
          className="focus-ring inline-flex items-center gap-2 rounded-xl border-2 border-[#3b3340] bg-white/75 px-4 py-2 text-sm font-black shadow-[3px_3px_0_rgba(45,42,50,0.14)] transition hover:-translate-y-0.5"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Portal home
        </Link>

        <header className="paper-card overflow-hidden rounded-3xl bg-white/78">
          <div className={`${accentClass[page.accent]} border-b-2 border-[#3b3340] p-5`}>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-xs font-black uppercase tracking-[0.14em] text-[#4f4858]">
                  curated page
                </div>
                <h1 className="mt-2 text-4xl font-black md:text-6xl">{page.title}</h1>
              </div>
              <div className="grid size-20 place-items-center rounded-2xl border-2 border-[#3b3340] bg-white/70 shadow-[4px_4px_0_rgba(45,42,50,0.16)]">
                <Icon className="size-10" aria-hidden="true" />
              </div>
            </div>
          </div>
          <p className="p-5 text-lg font-semibold leading-8 text-[#5f5868] md:p-7">{page.summary}</p>
        </header>

        <div className="grid gap-4">
          {page.sections.map((section) => (
            <section key={section.title} className="paper-card rounded-3xl bg-[#fff8ea]/88 p-5 md:p-7">
              <h2 className="text-2xl font-black">{section.title}</h2>
              <p className="mt-3 text-base leading-8 text-[#5f5868]">{section.body}</p>
              {section.bullets?.length ? (
                <ul className="mt-4 grid gap-3">
                  {section.bullets.map((bullet) => (
                    <li key={bullet} className="flex gap-3 rounded-2xl border-2 border-[#3b3340] bg-white/72 p-3">
                      <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-[#4c7c61]" aria-hidden="true" />
                      <span className="text-sm font-semibold leading-6 text-[#4f4858]">{bullet}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>

        {page.slug === "architecture" ? <ArchitectureMap /> : null}
        {page.slug === "pipeline" ? <PipelineStepper /> : null}
        {page.slug === "overview" ? <ModuleTabs /> : null}

        <section aria-labelledby="related-pages">
          <div className="mb-4 flex items-center gap-2">
            <ArrowRight className="size-5" aria-hidden="true" />
            <h2 id="related-pages" className="text-2xl font-black">
              Read next
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {relatedPages.map((related) => (
              <PageCard key={related.slug} page={related} />
            ))}
          </div>
        </section>
      </article>
    </PortalShell>
  );
}
