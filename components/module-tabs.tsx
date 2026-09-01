"use client";

import { useState } from "react";
import { moduleTabs } from "@/lib/portal-content";

export function ModuleTabs() {
  const [activeId, setActiveId] = useState(moduleTabs[0]?.id ?? "");
  const active = moduleTabs.find((tab) => tab.id === activeId) ?? moduleTabs[0];
  const Icon = active.icon;

  return (
    <section className="paper-card rounded-3xl bg-white/78 p-4 md:p-6" aria-labelledby="module-tabs">
      <h2 id="module-tabs" className="text-2xl font-black md:text-3xl">
        Three loops to keep straight
      </h2>
      <div className="mt-5 flex flex-col gap-2 sm:flex-row">
        {moduleTabs.map((tab) => {
          const TabIcon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveId(tab.id)}
              className={`focus-ring flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-[#3b3340] px-4 text-sm font-black transition hover:-translate-y-0.5 ${
                active.id === tab.id ? "bg-[#d7c6f1] shadow-[3px_3px_0_rgba(45,42,50,0.16)]" : "bg-white/72"
              }`}
            >
              <TabIcon className="size-4" aria-hidden="true" />
              {tab.label}
            </button>
          );
        })}
      </div>
      <div className="mt-4 rounded-2xl border-2 border-[#3b3340] bg-[#fff8ea] p-5">
        <div className="flex items-start gap-4">
          <div className="grid size-12 shrink-0 place-items-center rounded-xl border-2 border-[#3b3340] bg-[#b9d8f2]">
            <Icon className="size-6" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-xl font-black">{active.label}</h3>
            <p className="mt-2 text-sm leading-7 text-[#5f5868]">{active.body}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {active.bullets.map((bullet) => (
                <span
                  key={bullet}
                  className="rounded-full border-2 border-[#3b3340] bg-white/75 px-3 py-1 text-xs font-black"
                >
                  {bullet}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
