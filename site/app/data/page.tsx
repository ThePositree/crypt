import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function DataPage() {
  return <CuratedDocPage page={getPage("data")!} />;
}
