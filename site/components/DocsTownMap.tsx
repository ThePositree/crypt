"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";
import { mapNodes } from "@/lib/content";
import { Mascot } from "./Mascot";

export function DocsTownMap() {
  const [activeId, setActiveId] = useState(mapNodes[3].id);
  const active = useMemo(() => mapNodes.find((node) => node.id === activeId) ?? mapNodes[0], [activeId]);
  const ActiveIcon = active.icon;

  return (
    <section className="town-section" aria-labelledby="town-title">
      <div className="town-heading">
        <div>
          <p className="eyebrow">Interactive system map</p>
          <h1 id="town-title">Docs Town</h1>
          <p>
            Explore the public model of `crypt`: a Python research desk where data, engines, strategies, backtests,
            reports, execution boundaries, and risk rules are curated into one navigable map.
          </p>
        </div>
        <Mascot mood="builder" label="guide" />
      </div>

      <div className="town-map" aria-label="Docs Town subsystem map">
        <div className="map-river" />
        <div className="map-path path-one" />
        <div className="map-path path-two" />
        {mapNodes.map((node) => {
          const Icon = node.icon;
          const selected = node.id === activeId;
          return (
            <Link
              className={`town-node tone-${node.tone} ${selected ? "selected" : ""}`}
              href={`/docs/${node.slug}`}
              key={node.id}
              onFocus={() => setActiveId(node.id)}
              onMouseEnter={() => setActiveId(node.id)}
              style={{ left: node.position.left, top: node.position.top }}
            >
              <Icon size={24} aria-hidden="true" />
              <span>
                <strong>{node.title}</strong>
                <small>{node.short}</small>
              </span>
            </Link>
          );
        })}
      </div>

      <aside className={`map-detail tone-${active.tone}`}>
        <ActiveIcon size={22} aria-hidden="true" />
        <div>
          <strong>{active.title}</strong>
          <p>{active.short}</p>
          <Link href={`/docs/${active.slug}`}>
            Read this area <ArrowRight size={14} />
          </Link>
        </div>
      </aside>
    </section>
  );
}
