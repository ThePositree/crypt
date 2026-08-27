import type { Metadata } from "next";
import Link from "next/link";
import { DocsShell } from "@/components/docs-shell";
import { getDocsBySection } from "@/lib/docs";

export const metadata: Metadata = {
  title: "Docs",
  description: "Curated public documentation map for crypt.",
};

export default function DocsIndex() {
  const groups = Array.from(getDocsBySection().entries());

  return (
    <DocsShell activeSlug="overview">
      <div className="mb-8">
        <div className="mb-3 inline-flex rounded-lg border border-[#d9c4ae] bg-[#fff1df] px-3 py-1 text-xs font-semibold uppercase text-[#6f6860]">
          Docs map
        </div>
        <h1 className="mb-3 text-4xl font-black leading-tight text-[#332f2b] sm:text-5xl">
          Choose a route into crypt.
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-[#6f6860]">
          This site exposes a curated public documentation structure. Changelog, task files, private
          runtime state, secrets, and unpublished operational details stay out of the public
          surface.
        </p>
      </div>

      <div className="grid gap-7">
        {groups.map(([section, sectionDocs]) => (
          <section key={section}>
            <h2 className="mb-3 text-xl font-black text-[#332f2b]">{section}</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {sectionDocs.map((doc) => (
                <Link
                  className="min-h-32 rounded-lg border border-[#ead7c3] bg-white/55 p-4 transition hover:bg-white hover:shadow-md hover:shadow-[#6f6860]/10"
                  href={`/docs/${doc.slug}`}
                  key={doc.slug}
                >
                  <span className="block font-black text-[#332f2b]">{doc.title}</span>
                  <span className="mt-2 block text-sm leading-6 text-[#6f6860]">
                    {doc.description}
                  </span>
                  <span className="mt-3 block font-mono text-xs text-[#8a7b6d]">
                    {doc.sourcePath}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </DocsShell>
  );
}
