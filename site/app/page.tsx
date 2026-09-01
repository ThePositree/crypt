import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BookOpen, ShieldCheck } from "lucide-react";
import { sections } from "@/lib/content";
import { CharacterPanel, LearningRoutes, SignalJourney, SystemMap } from "@/components/portal-widgets";

export default function HomePage() {
  return (
    <div className="home-page">
      <section className="home-intro">
        <div>
          <p className="eyebrow">Курируемая документация</p>
          <h1>crypt docs объясняет кодовую базу как контрольную комнату.</h1>
          <p>
            Здесь нет live PnL, runtime значений и Markdown-rendering. Портал вручную
            раскладывает систему на понятные комнаты: данные, стратегии, бэктестер,
            исполнение, операции и справочник терминов.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" href="/overview">
              Начать обзор <ArrowRight size={16} />
            </Link>
            <Link className="secondary-link" href="/signal-journey">
              Показать путь сигнала
            </Link>
          </div>
        </div>
        <div className="visual-reference">
          <Image
            src="/visual/control-room-hero.png"
            alt="Мультяшная контрольная комната crypt docs"
            width={720}
            height={480}
            priority
          />
        </div>
      </section>

      <SystemMap />
      <SignalJourney compact />

      <section className="section-block">
        <div className="section-head">
          <div>
            <p className="eyebrow">Маршруты</p>
            <h2>Читать как framework docs</h2>
          </div>
        </div>
        <LearningRoutes />
      </section>

      <section className="section-block">
        <div className="section-head">
          <div>
            <p className="eyebrow">Разделы</p>
            <h2>Все комнаты портала</h2>
          </div>
        </div>
        <div className="card-grid three">
          {sections.slice(0, 8).map((section) => {
            const Icon = section.icon;
            return (
              <Link href={section.href} key={section.id} className={`section-card color-${section.color}`}>
                <Icon size={20} />
                <strong>{section.title}</strong>
                <span>{section.summary}</span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="proof-strip">
        <div>
          <BookOpen size={20} />
          <strong>Страницы курируются вручную</strong>
          <span>Markdown из репозитория используется как evidence, но не как renderer.</span>
        </div>
        <div>
          <ShieldCheck size={20} />
          <strong>Live границы сохранены</strong>
          <span>Архитектура объясняется без секретов, балансов и runtime values.</span>
        </div>
      </section>

      <CharacterPanel name="Команда комнат" role="несколько постоянных помощников ведут читателя по разделам, recipes и glossary" />
    </div>
  );
}
