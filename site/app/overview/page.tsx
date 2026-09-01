import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function OverviewPage() {
  return <CuratedDocPage page={getPage("overview")!} />;
}
