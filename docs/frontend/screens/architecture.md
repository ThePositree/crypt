# Architecture

- Route: `/docs/architecture`.
- Purpose: explain the current system from data acquisition through artifacts or execution.
- Primary action: follow one path into Data, Backtester, or Live Execution.
- Hierarchy: system map; module boundaries; decision/data flow; shared versus
  runtime-specific behavior; truth boundaries; failure/degradation paths.
- Messaging: from `How do modules connect?` to `I can trace inputs and decisions`;
  explicitly supersede the stale signal-only overview.
- Content contract: source-derived module names and contracts; no invented API.
- Discovery: module names, `EvaluationContext`, scheduler, executor, sync, stores.
- Interactions: diagram nodes/anchors, code links, disclosures, related routes.
- States: complete/partial/missing data paths, diagram vertical fallback, overflow.
- Responsive: wide graph becomes ordered vertical stages with cross-links.
- Accessibility: diagram text equivalent and logical reading order.
- Related: Overview, Data, Backtester, Live Execution.
- Acceptance: each component has input, responsibility, output, failure, and truth owner.
