"use client";

import Link from "next/link";
import { useState } from "react";
import { architectureNodes } from "@/lib/portal-content";

const toneClass = {
  mint: "bg-[#bfe8d0]",
  sky: "bg-[#b9d8f2]",
  lavender: "bg-[#d7c6f1]",
  rose: "bg-[#f5b9c6]",
  lemon: "bg-[#f7e8a6]",
};

export function ArchitectureMap() {
  const [activeId, setActiveId] = useState(architectureNodes[0]?.id ?? "");
  const active = architectureNodes.find((node) => node.id === activeId) ?? architectureNodes[0];

  return (
    <section className="paper-card rounded-3xl bg-white/78 p-4 md:p-6" aria-labelledby="architecture-map">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 id="architecture-map" className="text-2xl font-black md:text-3xl">
            Clickable architecture map
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5f5868]">
            Tap a subsystem to see its job, then open the curated page behind it.
          </p>
        </div>
        <Link
          href={`/docs/${active.pageSlug}`}
          className="focus-ring hand-drawn inline-flex min-h-11 items-center justify-center rounded-xl bg-[#bfe8d0] px-4 text-sm font-black transition hover:-translate-y-0.5"
        >
          Open {active.title}
        </Link>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="relative grid gap-3 rounded-2xl border-2 border-[#3b3340] bg-[#fff8ea] p-4 sm:grid-cols-2 lg:grid-cols-3">
          {architectureNodes.map((node) => (
            <button
              key={node.id}
              type="button"
              onClick={() => setActiveId(node.id)}
              className={`focus-ring min-h-32 rounded-2xl border-2 border-[#3b3340] p-4 text-left shadow-[4px_4px_0_rgba(45,42,50,0.14)] transition hover:-translate-y-0.5 ${
                toneClass[node.tone]
              } ${active.id === node.id ? "ring-4 ring-[#2d2a32]/20" : ""}`}
            >
              <div className="text-lg font-black">{node.title}</div>
              <p className="mt-2 text-sm leading-6 text-[#4f4858]">{node.summary}</p>
            </button>
          ))}
        </div>

        <div className="rounded-2xl border-2 border-[#3b3340] bg-[#2d2a32] p-5 text-[#fff8ea] shadow-[5px_5px_0_rgba(45,42,50,0.16)]">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-[#f7e8a6]">
            selected note
          </div>
          <h3 className="mt-3 text-2xl font-black">{active.title}</h3>
          <p className="mt-3 text-sm leading-6 text-[#fff8ea]/85">{active.summary}</p>
          <div className="mt-5 rounded-xl border border-[#fff8ea]/20 bg-[#fff8ea]/10 p-4 font-mono text-xs leading-6">
            source truth: docs, config, exchange boundaries
          </div>
        </div>
      </div>
    </section>
  );
}
