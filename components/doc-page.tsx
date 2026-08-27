import type { Metadata } from "next";
import { DocsShell } from "@/components/docs-shell";
import { MarkdownContent } from "@/components/markdown-content";
import { hasSafetyCallout, SafetyCallout } from "@/components/safety-callout";
import { getDoc } from "@/lib/docs";

export function metadataForDoc(slug: string): Metadata {
  const doc = getDoc(slug);
  return {
    title: doc.title,
    description: doc.description,
  };
}

export function DocPage({ slug }: { slug: string }) {
  const doc = getDoc(slug);

  return (
    <DocsShell activeSlug={slug} headings={doc.headings}>
      <div className="mb-7">
        <div className="mb-3 inline-flex rounded-lg border border-[#d9c4ae] bg-[#fff1df] px-3 py-1 text-xs font-semibold uppercase text-[#6f6860]">
          {doc.section}
        </div>
        <h1 className="mb-3 text-4xl font-black leading-tight text-[#332f2b] sm:text-5xl">
          {doc.title}
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-[#6f6860]">{doc.description}</p>
        <p className="mt-4 text-sm text-[#8a7b6d]">Source: {doc.sourcePath}</p>
      </div>

      {hasSafetyCallout(slug) ? <SafetyCallout slug={slug} /> : null}

      <MarkdownContent content={doc.content} />
    </DocsShell>
  );
}
