"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { pipelineSteps } from "@/lib/portal-content";

export function PipelineStepper() {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = pipelineSteps[activeIndex];

  return (
    <section className="paper-card rounded-3xl bg-[#fff8ea]/88 p-4 md:p-6" aria-labelledby="pipeline-stepper">
      <h2 id="pipeline-stepper" className="text-2xl font-black md:text-3xl">
        Pipeline stepper
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5f5868]">
        Follow the route from a research hypothesis to an archived candidate or optional runtime config.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-[260px_1fr]">
        <div className="grid gap-2">
          {pipelineSteps.map((step, index) => (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={`focus-ring rounded-xl border-2 border-[#3b3340] px-4 py-3 text-left text-sm font-black transition hover:-translate-y-0.5 ${
                active.id === step.id ? "bg-[#f7e8a6] shadow-[4px_4px_0_rgba(45,42,50,0.16)]" : "bg-white/75"
              }`}
            >
              <span className="mr-2 inline-grid size-7 place-items-center rounded-full border-2 border-[#3b3340] bg-[#b9d8f2] text-xs">
                {index + 1}
              </span>
              {step.title}
            </button>
          ))}
        </div>

        <div className="rounded-2xl border-2 border-[#3b3340] bg-white/80 p-5 shadow-[5px_5px_0_rgba(45,42,50,0.14)]">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-[#726a79]">
            step {activeIndex + 1} of {pipelineSteps.length}
          </div>
          <h3 className="mt-3 text-3xl font-black">{active.title}</h3>
          <p className="mt-3 text-lg font-bold leading-7 text-[#4f4858]">{active.summary}</p>
          <p className="mt-4 text-sm leading-7 text-[#5f5868]">{active.detail}</p>
          <Link
            href={`/docs/${active.pageSlug}`}
            className="focus-ring mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-[#3b3340] bg-[#bfe8d0] px-4 text-sm font-black shadow-[3px_3px_0_rgba(45,42,50,0.16)] transition hover:-translate-y-0.5"
          >
            Read related page
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  );
}
