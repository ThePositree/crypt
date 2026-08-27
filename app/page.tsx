import { ArrowRight, BookOpen, Boxes, FlaskConical, Microscope, RadioTower } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { FlowDiagram, liveFlow } from "@/components/flow-diagram";
import { docs } from "@/lib/docs";

const primaryRoutes = [
  {
    href: "/docs",
    title: "Docs map",
    body: "Start from the curated public documentation structure.",
    icon: BookOpen,
    tone: "bg-[#fff0b8]",
  },
  {
    href: "/architecture",
    title: "Architecture",
    body: "Trace config, data, engines, decisions, sinks, and failure boundaries.",
    icon: Boxes,
    tone: "bg-[#dff2f8]",
  },
  {
    href: "/research",
    title: "Research",
    body: "Follow strategy discovery, benchmark policy, and archived research lines.",
    icon: FlaskConical,
    tone: "bg-[#fff0b8]",
  },
  {
    href: "/backtester",
    title: "Backtester",
    body: "Inspect parity checkpoints and reproducibility guardrails.",
    icon: Microscope,
    tone: "bg-[#ddf3e4]",
  },
];

export default function Home() {
  return (
    <main>
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:px-8">
        <div>
          <div className="mb-4 inline-flex items-center gap-2 rounded-lg border border-[#d9c4ae] bg-white/54 px-3 py-1 text-sm font-semibold text-[#6f6860]">
            <RadioTower aria-hidden="true" size={16} />
            Research workbench plus live OKX execution
          </div>
          <h1 className="max-w-3xl text-5xl font-black leading-[1.02] text-[#332f2b] sm:text-6xl lg:text-7xl">
            crypt
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[#5f574f]">
            Public docs for an automated crypto perpetual strategy workbench: research, exact
            backtests, archived candidates, and a live execution path that follows runtime truth.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-[#332f2b] px-4 text-sm font-bold text-white transition hover:bg-[#4a433c]"
              href="/docs"
            >
              Open docs
              <ArrowRight aria-hidden="true" size={16} />
            </Link>
            <Link
              className="inline-flex h-11 items-center gap-2 rounded-lg border border-[#d9c4ae] bg-white/58 px-4 text-sm font-bold text-[#332f2b] transition hover:bg-white"
              href="/docs/live-execution"
            >
              Live flow
            </Link>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-lg border border-[#ead7c3] bg-white/42 shadow-xl shadow-[#6f6860]/10">
          <Image
            alt="Lo-fi cartoon execution room with conceptual runtime, docs, and backtester panels."
            className="h-auto w-full"
            height={1024}
            priority
            src="/images/crypt-execution-room.png"
            width={1792}
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {primaryRoutes.map(({ href, title, body, icon: Icon, tone }) => (
            <Link
              className="group min-h-44 rounded-lg border border-[#ead7c3] bg-white/55 p-5 transition hover:-translate-y-0.5 hover:bg-white hover:shadow-lg hover:shadow-[#6f6860]/10"
              href={href}
              key={href}
            >
              <span className={`mb-4 grid size-10 place-items-center rounded-lg ${tone}`}>
                <Icon aria-hidden="true" size={19} />
              </span>
              <span className="block text-lg font-black text-[#332f2b]">{title}</span>
              <span className="mt-2 block text-sm leading-6 text-[#6f6860]">{body}</span>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-[#33758a]">
                Read
                <ArrowRight
                  aria-hidden="true"
                  className="transition group-hover:translate-x-0.5"
                  size={14}
                />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">
        <div className="rounded-lg border border-[#ead7c3] bg-[#fffdf8]/68 p-5 sm:p-7">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-black text-[#332f2b]">Runtime at a glance</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6f6860]">
                Public docs show the flow, while live-money truth remains in runtime config and
                exchange state.
              </p>
            </div>
            <Link className="text-sm font-bold text-[#33758a]" href="/docs/live-execution">
              Read live execution
            </Link>
          </div>
          <FlowDiagram nodes={liveFlow} />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="grid gap-3 md:grid-cols-3">
          {docs.slice(0, 9).map((doc) => (
            <Link
              className="rounded-lg border border-[#ead7c3] bg-white/45 p-4 transition hover:bg-white"
              href={`/docs/${doc.slug}`}
              key={doc.slug}
            >
              <span className="text-xs font-bold uppercase text-[#8a7b6d]">{doc.section}</span>
              <span className="mt-1 block font-black text-[#332f2b]">{doc.title}</span>
              <span className="mt-2 block text-sm leading-6 text-[#6f6860]">{doc.description}</span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
