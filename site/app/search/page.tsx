import { Suspense } from "react";
import { SearchResultsPage } from "@/components/search-page";

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="state-card">Загружаю поиск...</p>}>
      <SearchResultsPage />
    </Suspense>
  );
}
