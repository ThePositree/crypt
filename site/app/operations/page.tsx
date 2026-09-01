import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function OperationsPage() {
  return <CuratedDocPage page={getPage("operations")!} />;
}
