"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Info,
  Sparkles,
} from "lucide-react";
import {
  glossaryTerms,
  journeySteps,
  learningRoutes,
  sections,
  systemNodes,
  type DocPage,
  type GlossaryTerm,
  type SectionId,
} from "@/lib/content";

export function CharacterPanel({
  name,
  role,
  variant = "default",
}: {
  name: string;
  role: string;
  variant?: "default" | "wide";
}) {
  return (
    <aside className={`character-panel ${variant}`}>
      <div className="character-avatar" aria-hidden="true">
        <span>{name.slice(0, 1)}</span>
      </div>
      <div>
        <p className="eyebrow">Постоянный помощник</p>
        <h3>{name}</h3>
        <p>{role}</p>
      </div>
    </aside>
  );
}

export function SystemMap() {
  const [selected, setSelected] = useState<SectionId>("strategies");
  const node = systemNodes.find((item) => item.id === selected) ?? systemNodes[0];
  const section = sections.find((item) => item.id === selected);

  return (
    <section className="map-section" aria-labelledby="system-map-title">
      <div className="section-head">
        <div>
          <p className="eyebrow">Главная карта</p>
          <h2 id="system-map-title">Контрольная комната crypt</h2>
        </div>
        <Link className="ghost-link" href="/overview">
          Полный обзор <ChevronRight size={16} />
        </Link>
      </div>
      <div className="system-map">
        <div className="room-grid">
          {systemNodes.map((item) => {
            const current = item.id === selected;
            const Icon = sections.find((entry) => entry.id === item.id)?.icon ?? BookOpen;
            return (
              <button
                key={item.id}
                type="button"
                className={`room-node color-${sections.find((entry) => entry.id === item.id)?.color ?? "rose"} ${
                  current ? "selected" : ""
                }`}
                onClick={() => setSelected(item.id)}
                aria-pressed={current}
              >
                <Icon size={22} />
                <strong>{item.label}</strong>
                <span>{item.title}</span>
              </button>
            );
          })}
        </div>
        <div className="node-drawer">
          <p className="eyebrow">Выбранная станция</p>
          <h3>{node.title}</h3>
          <p>{node.summary}</p>
          <div className="connection-list">
            {node.connections.map((connection) => (
              <span key={connection}>{sections.find((item) => item.id === connection)?.shortTitle}</span>
            ))}
          </div>
          {section && (
            <Link className="primary-link" href={section.href}>
              Открыть раздел
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}

export function SignalJourney({ compact = false }: { compact?: boolean }) {
  const [selected, setSelected] = useState(journeySteps[0].id);
  const step = journeySteps.find((item) => item.id === selected) ?? journeySteps[0];

  return (
    <section className="journey-section" aria-labelledby="signal-journey-title">
      <div className="section-head">
        <div>
          <p className="eyebrow">Путь сигнала</p>
          <h2 id="signal-journey-title">От свечи до решения</h2>
        </div>
        {compact && (
          <Link className="ghost-link" href="/signal-journey">
            Разобрать глубже <ChevronRight size={16} />
          </Link>
        )}
      </div>
      <div className="journey-track" aria-label="Шаги пути сигнала">
        {journeySteps.map((item, index) => (
          <button
            id={item.id}
            key={item.id}
            type="button"
            className={item.id === selected ? "selected" : ""}
            onClick={() => setSelected(item.id)}
          >
            <span>{index + 1}</span>
            <strong>{item.title}</strong>
          </button>
        ))}
      </div>
      <div className="journey-detail">
        <div>
          <p className="eyebrow">Состояние</p>
          <h3>{step.state}</h3>
          <p>{step.summary}</p>
        </div>
        <div className="contract-card">
          <CheckCircle2 size={18} />
          <span>{step.contract}</span>
        </div>
        <Link className="primary-link" href={`/${step.section}`}>
          Открыть связанный раздел
        </Link>
      </div>
    </section>
  );
}

export function LearningRoutes() {
  return (
    <section className="card-grid four" aria-label="Маршруты обучения">
      {learningRoutes.map((route) => (
        <Link className="learning-card" href={route.href} key={route.href}>
          <Sparkles size={18} />
          <strong>{route.title}</strong>
          <span>{route.summary}</span>
        </Link>
      ))}
    </section>
  );
}

export function DocTabs({ page }: { page: DocPage }) {
  const [tab, setTab] = useState<"overview" | "deep">("overview");

  return (
    <section className="doc-tabs">
      <div className="tab-row" role="tablist" aria-label="Режим чтения">
        <button type="button" className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
          Обзор
        </button>
        <button type="button" className={tab === "deep" ? "active" : ""} onClick={() => setTab("deep")}>
          Глубже
        </button>
      </div>
      {tab === "overview" ? (
        <div className="overview-panel">
          <h2>Mental model</h2>
          <p>{page.mentalModel}</p>
          <div className="info-grid">
            {page.movingParts.map((part) => (
              <article className="info-card" key={part}>
                <Info size={18} />
                <p>{part}</p>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="deep-panel">
          {page.deepDive.map((item) => (
            <article className="deep-card" key={item}>
              <h3>Разбор</h3>
              <p>{item}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function ContractAccordion({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="accordion-section">
      <h2>{title}</h2>
      {items.map((item, index) => (
        <details key={item} open={index === 0}>
          <summary>
            <ShieldLabel index={index} />
            {item.split(".")[0]}
          </summary>
          <p>{item}</p>
        </details>
      ))}
    </section>
  );
}

function ShieldLabel({ index }: { index: number }) {
  return <span className="summary-index">{index + 1}</span>;
}

export function RecipeList({ page }: { page: DocPage }) {
  return (
    <section className="recipe-list" id="recipes">
      <div className="section-head">
        <div>
          <p className="eyebrow">Recipes</p>
          <h2>Как расширять</h2>
        </div>
      </div>
      <div className="card-grid">
        {page.recipes.map((recipeItem) => (
          <article className="recipe-card" key={recipeItem.title}>
            <h3>{recipeItem.title}</h3>
            <p>{recipeItem.summary}</p>
            <ol>
              {recipeItem.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}

export function FailureModes({ items }: { items: string[] }) {
  return (
    <section className="failure-panel">
      <CircleAlert size={19} />
      <div>
        <h2>Failure modes</h2>
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function RelatedLinks({ ids, terms }: { ids: SectionId[]; terms: string[] }) {
  return (
    <section className="related-panel">
      <div>
        <h2>Связанные разделы</h2>
        <div className="chip-row">
          {ids.map((id) => {
            const section = sections.find((item) => item.id === id);
            if (!section) return null;
            return (
              <Link className="chip" href={section.href} key={id}>
                {section.title}
              </Link>
            );
          })}
        </div>
      </div>
      <div>
        <h2>Термины</h2>
        <div className="chip-row">
          {terms.map((term) => (
            <Link className="chip" href={`/glossary?term=${encodeURIComponent(term)}`} key={term}>
              {term}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export function GlossaryExplorer({ initialTerm }: { initialTerm?: string }) {
  const [query, setQuery] = useState(initialTerm ?? "");
  const [section, setSection] = useState("all");
  const [selected, setSelected] = useState(initialTerm ?? glossaryTerms[0].term);

  const filtered = useMemo(
    () =>
      glossaryTerms.filter((term) => {
        const matchesQuery =
          !query ||
          term.term.toLowerCase().includes(query.toLowerCase()) ||
          term.definition.toLowerCase().includes(query.toLowerCase());
        const matchesSection = section === "all" || term.section === section;
        return matchesQuery && matchesSection;
      }),
    [query, section],
  );

  const selectedTerm: GlossaryTerm | undefined =
    glossaryTerms.find((term) => term.term === selected) ?? filtered[0];

  return (
    <section className="glossary-explorer">
      <div className="glossary-controls">
        <label className="search-field compact">
          <span>Фильтр</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="signal, OKX..." />
        </label>
        <div className="chip-row">
          <button className={section === "all" ? "chip active" : "chip"} onClick={() => setSection("all")}>
            Все
          </button>
          {sections.slice(1, 8).map((item) => (
            <button
              key={item.id}
              className={section === item.id ? "chip active" : "chip"}
              onClick={() => setSection(item.id)}
            >
              {item.shortTitle}
            </button>
          ))}
        </div>
      </div>
      <div className="glossary-grid">
        <div className="term-list" role="listbox" aria-label="Термины">
          {filtered.length === 0 && <p className="state-card">Термин не найден. Попробуй broader concept.</p>}
          {filtered.map((term) => (
            <button key={term.term} className={term.term === selectedTerm?.term ? "active" : ""} onClick={() => setSelected(term.term)}>
              <strong>{term.term}</strong>
              <span>{sections.find((item) => item.id === term.section)?.title}</span>
            </button>
          ))}
        </div>
        {selectedTerm && (
          <article className="definition-card">
            <p className="eyebrow">{sections.find((item) => item.id === selectedTerm.section)?.title}</p>
            <h2>{selectedTerm.term}</h2>
            <p>{selectedTerm.definition}</p>
            <div className="chip-row">
              {selectedTerm.related.map((term) => (
                <span className="chip" key={term}>
                  {term}
                </span>
              ))}
            </div>
            <Link className="primary-link" href={`/${selectedTerm.section}`}>
              Открыть раздел
            </Link>
          </article>
        )}
      </div>
    </section>
  );
}
