import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function StrategiesPage() {
  return <CuratedDocPage page={getPage("strategies")!} />;
}
