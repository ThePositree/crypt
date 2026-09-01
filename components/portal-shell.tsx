import Link from "next/link";
import { portalPages } from "@/lib/portal-content";
import { SearchDialog } from "@/components/search-dialog";

export function PortalShell({
  children,
  activeSlug,
}: {
  children: React.ReactNode;
  activeSlug?: string;
}) {
  return (
    <div className="desk-grid min-h-screen">
      <header className="sticky top-0 z-30 border-b-2 border-[#3b3340] bg-[#fff8ea]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6">
          <Link href="/" className="focus-ring flex items-center gap-3 rounded-xl">
            <span className="grid size-11 place-items-center rounded-xl border-2 border-[#3b3340] bg-[#bfe8d0] text-lg font-black shadow-[3px_3px_0_rgba(45,42,50,0.18)]">
              c
            </span>
            <span>
              <span className="block text-lg font-black leading-none">crypt</span>
              <span className="block text-xs font-bold uppercase tracking-[0.12em] text-[#726a79]">
                docs portal
              </span>
            </span>
          </Link>
          <SearchDialog />
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 md:grid-cols-[240px_1fr] md:px-6">
        <aside className="md:sticky md:top-24 md:self-start">
          <nav
            className="paper-card rounded-2xl bg-white/78 p-3"
            aria-label="Portal navigation"
          >
            <div className="px-3 pb-2 text-xs font-black uppercase tracking-[0.14em] text-[#726a79]">
              Pages
            </div>
            <div className="grid gap-2">
              {portalPages.map((page) => {
                const Icon = page.icon;
                const active = activeSlug === page.slug;
                return (
                  <Link
                    key={page.slug}
                    href={`/docs/${page.slug}`}
                    className={`focus-ring flex items-center gap-2 rounded-xl border-2 px-3 py-2 text-sm font-extrabold transition ${
                      active
                        ? "border-[#3b3340] bg-[#f7e8a6] shadow-[3px_3px_0_rgba(45,42,50,0.16)]"
                        : "border-transparent hover:border-[#3b3340] hover:bg-[#fff8ea]"
                    }`}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                    <span>{page.navLabel}</span>
                  </Link>
                );
              })}
            </div>
          </nav>
        </aside>
        <main>{children}</main>
      </div>
    </div>
  );
}
