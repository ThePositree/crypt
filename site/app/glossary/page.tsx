import { Suspense } from "react";
import { GlossaryExplorer } from "@/components/portal-widgets";

export default function GlossaryPage({
  searchParams,
}: {
  searchParams?: Promise<{ term?: string }>;
}) {
  return (
    <Suspense>
      <GlossaryContent searchParams={searchParams} />
    </Suspense>
  );
}

async function GlossaryContent({
  searchParams,
}: {
  searchParams?: Promise<{ term?: string }>;
}) {
  const params = await searchParams;
  return (
    <div className="doc-page">
      <header className="doc-hero color-sage">
        <div>
          <p className="eyebrow">Reference room</p>
          <h1>Глоссарий проекта</h1>
          <p>
            Термины crypt связаны с разделами, где они реально используются.
            Это справочник для чтения кода, а не общая энциклопедия крипты.
          </p>
        </div>
      </header>
      <GlossaryExplorer initialTerm={params?.term} />
    </div>
  );
}
