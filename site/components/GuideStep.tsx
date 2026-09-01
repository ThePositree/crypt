import type { GuideStep as GuideStepType } from "@/lib/content";
import { CopyButton } from "./CopyButton";

export function GuideStep({ step }: { step: GuideStepType }) {
  return (
    <article className="guide-step">
      <h3>{step.title}</h3>
      <div className="guide-grid">
        <section>
          <div className="panel-heading">Command</div>
          <pre>
            <code>{step.command}</code>
          </pre>
          <CopyButton value={step.command} />
        </section>
        <section>
          <div className="panel-heading">Expected output</div>
          <ul>
            {step.output.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
        <section>
          <div className="panel-heading">Explanation</div>
          <p>{step.explanation}</p>
        </section>
      </div>
    </article>
  );
}
