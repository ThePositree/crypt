import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { ArchitectureMap } from "@/components/architecture-map";
import { DeskIllustration } from "@/components/desk-illustration";
import { ModuleTabs } from "@/components/module-tabs";
import { PageCard } from "@/components/page-card";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { PortalShell } from "@/components/portal-shell";
import { portalPages, quickLinks } from "@/lib/portal-content";

export default function Home() {
  return (
    <PortalShell activeSlug="overview">
      <div className="space-y-8">
        <section className="grid gap-6 lg:grid-cols-[1fr_0.86fr] lg:items-center">
          <div className="paper-card rounded-3xl bg-white/78 p-6 md:p-8">
            <div className="inline-flex items-center gap-2 rounded-full border-2 border-[#3b3340] bg-[#d7c6f1] px-3 py-1 text-xs font-black uppercase tracking-[0.14em]">
              <Sparkles className="size-4" aria-hidden="true" />
              curated developer portal
            </div>
            <h1 className="mt-5 max-w-3xl text-4xl font-black leading-[1.02] md:text-6xl">
              crypt explains a crypto strategy workbench without hiding the machinery.
            </h1>
            <p className="mt-5 max-w-2xl text-base font-semibold leading-8 text-[#5f5868] md:text-lg">
              A hand-built docs portal for developers who want the product map: research loop,
              backtester, candidate archive, strategy configuration, risk controls, runbooks,
              and the optional OKX execution runtime.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/docs/architecture"
                className="focus-ring hand-drawn inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#bfe8d0] px-5 text-sm font-black transition hover:-translate-y-0.5"
              >
                Start with architecture
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link
                href="/docs/pipeline"
                className="focus-ring hand-drawn inline-flex min-h-12 items-center justify-center rounded-xl bg-[#f7e8a6] px-5 text-sm font-black transition hover:-translate-y-0.5"
              >
                Walk the pipeline
              </Link>
            </div>
          </div>
          <DeskIllustration />
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" aria-label="Quick links">
          {quickLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.label}
                href={link.href}
                className="focus-ring hand-drawn flex min-h-24 items-center gap-3 rounded-2xl bg-white/78 p-4 text-sm font-black transition hover:-translate-y-0.5"
              >
                <Icon className="size-5 shrink-0" aria-hidden="true" />
                {link.label}
              </Link>
            );
          })}
        </section>

        <ArchitectureMap />
        <PipelineStepper />
        <ModuleTabs />

        <section aria-labelledby="portal-pages">
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 id="portal-pages" className="text-3xl font-black">
                Curated pages
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5f5868]">
                Every page is written as product documentation, not a raw markdown mirror.
              </p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {portalPages.map((page) => (
              <PageCard key={page.slug} page={page} />
            ))}
          </div>
        </section>
      </div>
    </PortalShell>
  );
}
