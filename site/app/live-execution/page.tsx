import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function LiveExecutionPage() {
  return <CuratedDocPage page={getPage("live-execution")!} />;
}
