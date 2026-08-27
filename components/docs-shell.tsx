import Link from "next/link";
import type { ReactNode } from "react";
import { docs, type Heading } from "@/lib/docs";

export function DocsShell({
  activeSlug,
  children,
  headings,
}: {
  activeSlug: string;
  children: ReactNode;
  headings?: Heading[];
}) {
  return (
    <main className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[16rem_minmax(0,1fr)_13rem] lg:px-8">
      <aside className="lg:sticky lg:top-24 lg:h-[calc(100vh-7rem)] lg:overflow-y-auto">
        <div className="rounded-lg border border-[#ead7c3] bg-white/42 p-3">
          <div className="mb-2 px-2 text-xs font-semibold uppercase text-[#6f6860]">
            Documentation
          </div>
          <nav className="grid gap-1">
            {docs.map((doc) => (
              <Link
                className={`rounded-lg px-3 py-2 text-sm transition ${
                  doc.slug === activeSlug
                    ? "bg-[#b9dce8]/60 font-semibold text-[#263d46]"
                    : "text-[#6f6860] hover:bg-white/70 hover:text-[#332f2b]"
                }`}
                href={`/docs/${doc.slug}`}
                key={doc.slug}
              >
                <span className="block text-[0.7rem] uppercase">{doc.section}</span>
                {doc.title}
              </Link>
            ))}
          </nav>
        </div>
      </aside>

      <section className="min-w-0 rounded-lg border border-[#ead7c3] bg-[#fffdf8]/72 px-5 py-6 shadow-sm shadow-[#6f6860]/5 sm:px-8 lg:px-10">
        {children}
      </section>

      <aside className="hidden lg:block">
        {headings && headings.length > 0 ? (
          <div className="sticky top-24 rounded-lg border border-[#ead7c3] bg-white/38 p-4">
            <div className="mb-3 text-xs font-semibold uppercase text-[#6f6860]">On this page</div>
            <nav className="grid gap-2">
              {headings.slice(0, 12).map((heading) => (
                <a
                  className={`text-sm leading-5 text-[#6f6860] hover:text-[#332f2b] ${
                    heading.depth === 3 ? "pl-3" : ""
                  }`}
                  href={`#${heading.id}`}
                  key={`${heading.id}-${heading.title}`}
                >
                  {heading.title}
                </a>
              ))}
            </nav>
          </div>
        ) : null}
      </aside>
    </main>
  );
}
