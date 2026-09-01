import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { PortalPage } from "@/lib/portal-content";

const accentClass = {
  mint: "bg-[#bfe8d0]",
  sky: "bg-[#b9d8f2]",
  lavender: "bg-[#d7c6f1]",
  rose: "bg-[#f5b9c6]",
  lemon: "bg-[#f7e8a6]",
};

export function PageCard({ page }: { page: PortalPage }) {
  const Icon = page.icon;

  return (
    <Link
      href={`/docs/${page.slug}`}
      className="focus-ring paper-card group flex min-h-56 flex-col rounded-2xl bg-white/80 p-5 transition hover:-translate-y-1"
    >
      <div className="flex items-start justify-between gap-4">
        <div className={`grid size-12 place-items-center rounded-xl border-2 border-[#3b3340] ${accentClass[page.accent]}`}>
          <Icon className="size-6" aria-hidden="true" />
        </div>
        <ArrowRight className="size-5 transition group-hover:translate-x-1" aria-hidden="true" />
      </div>
      <h3 className="mt-5 text-xl font-black">{page.title}</h3>
      <p className="mt-3 text-sm leading-6 text-[#5f5868]">{page.summary}</p>
    </Link>
  );
}
