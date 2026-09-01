import { SignalJourney } from "@/components/portal-widgets";
import { CuratedDocPage } from "@/components/doc-page";
import { getPage } from "@/lib/content";

export default function SignalJourneyPage() {
  return (
    <div className="doc-page">
      <SignalJourney />
      <CuratedDocPage page={getPage("signal-journey")!} />
    </div>
  );
}
