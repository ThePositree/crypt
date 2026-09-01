import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function ArchitecturePage() {
  return <CuratedDocPage page={getPage("architecture")!} />;
}
