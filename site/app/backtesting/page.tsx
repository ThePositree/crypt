import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function BacktestingPage() {
  return <CuratedDocPage page={getPage("backtesting")!} />;
}
