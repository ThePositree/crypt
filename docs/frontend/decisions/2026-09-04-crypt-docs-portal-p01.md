# Crypt Docs Portal P01 Task Contract And Onboarding

- Artifact path: `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md`
- Artifact type: D3 P01 task contract, collaboration check, onboarding record, and uncertainty check
- Revision: 1
- Date: 2026-09-04
- Authoring context: primary Codex session
- Owner approval gate: none for P01 record; Product Surface Approval controls P02 output
- Status: prepared for P02

## Task Contract

### Outcome

Build `crypt docs`, a large documentation portal that explains how the
repository works as a crypto-trading framework. The first production version is
expected to contain complete curated documentation content in source files, not
CMS-backed content and not runtime execution results.

### Scope

In scope:

- Next.js plus Tailwind production frontend.
- Russian portal UI and content.
- Documentation portal for a developer-crypto-trader audience.
- Tutorial-style reading paths and framework-style reference documentation.
- Required sections: Overview, Architecture, Backtester, Strategies, Live
  Execution, Data Pipeline, CLI, Configuration, Operations, and Glossary.
- Full-content search, header search input, and `Cmd/Ctrl+K` command palette.
- Breadcrumbs, left navigation, and desktop on-page TOC.
- Interactive documentation affordances such as expandable diagrams, tabs,
  filters, and copyable command snippets.
- Diagrams for data and decision flow, including candles -> indicators ->
  signal -> portfolio decision -> execution order.
- Light and dark themes.
- Playful lo-fi visual language with abstract mascots.
- Risk markings for live money, OKX execution, configuration, and no
  look-ahead bias.
- "What to read next" guidance on every page.
- Maturity labels such as stable, research, operational, and archived.

Out of scope for the documentation portal:

- Displaying current production balances, positions, live runtime metrics, or
  execution results.
- Quoting source code as the primary teaching format.
- A CMS.
- Mutating live execution state or external accounts.

### Sources Of Truth

- Owner onboarding answers in chat on 2026-09-04.
- `AGENTS.md` for hard rules and product framing.
- `README.md` for public project summary.
- `docs/agent/context_routes.yml` for canonical context routing.
- `docs/state/current.yml` for current project shape and runtime truth
  boundaries.
- Existing domain docs under `docs/`, source code under `src/`, strategy
  archive metadata, and CLI docs for later source-grounded content authoring.

### Constraints

- English in repository documentation artifacts and source identifiers; Russian
  is allowed and required for user-visible portal copy because the owner
  selected Russian for the portal.
- D3 frontend lifecycle applies: Product Surface Approval, messaging/content
  system, visual direction, design system, UI library showcase, flows,
  wireframes, screen contracts, final implementation approval, independent QA,
  and final instruction audit.
- Use Orca-managed native coordination for independent review and QA phases.
- Use Context7 before non-trivial Next.js, Tailwind, or other external-library
  implementation work.
- The live execution section must explain architecture and operating
  guarantees without showing current production money state.
- Risk-critical documentation must mark live money, OKX execution, config, and
  no-look-ahead boundaries explicitly.

### Acceptance Evidence

Final completion must include:

- Approved Product Surface Model.
- Approved Messaging Identity, content/source map, and Text Inventory.
- Approved visual direction and design system.
- Approved flows, wireframes, screen contracts, and implementation brief.
- Production Next.js/Tailwind implementation.
- Rendered desktop and mobile validation, plus the viewport set required by
  the frontend subsystem unless explicitly waived.
- Full-content search evidence.
- Keyboard and command-palette evidence.
- Accessibility and contrast evidence.
- Independent frontend QA evidence through Orca-managed review.
- Updated frontend memory, task files, and changelog.

### Unknowns

- Exact route tree and information architecture must be finalized in P02.
- Exact source corpus boundaries and content depth per section must be
  finalized during source-grounded content authoring.
- Next.js version, App Router choice, search implementation, and package
  details require implementation-time documentation lookup and stack contract.
- Visual direction needs approved raster boards before final styling.
- Deployment target is not selected; local production build is the default
  implementation target until the owner requests deployment.

## Collaboration Check

- Phase: P01 now; P02 next.
- Owner decision: use Orca subagents / independent contexts for review and QA;
  Orca CLI is repaired; launch through Orca native coordination.
- Applicable coordination: Orca-managed independent review and QA phases for
  D3 artifacts.
- P01 delegation: not used; P01 is a compact owner-answer capture and contract
  artifact.
- Later required independent work: factual product research, contract review,
  copy review, visual and wireframe review, implementation where required by
  phase separation, and final QA.
- Main context boundary: the main context owns gates, compact manifests,
  handoffs, owner decisions, and integration; large D3 research/review outputs
  should be file-backed.

## Owner Onboarding Answers

1. Product: a huge documentation portal that fully explains how the code works.
2. Audience: developer-crypto-trader.
3. First screen: explain the project and how the code works; do not display
   code execution results.
4. Stack: Next.js plus Tailwind.
5. Review/QA coordination: use Orca subagents / independent contexts through
   native Orca.
6. Portal language: Russian.
7. Primary reader: developer-crypto-trader.
8. Navigation: support both architecture-first and learning-route navigation.
9. Code depth: framework-style documentation; do not quote source code.
10. First-release search: required.
11. Content shape: both tutorial and reference documentation.
12. Required sections: Overview, Architecture, Backtester, Strategies, Live
    Execution, Data Pipeline, CLI, Configuration, Operations, Glossary.
13. Diagrams: required for data and decision flows.
14. Search scope: full curated page content.
15. Visual style: playful; no CMS; all content lives in source.
16. Homepage: both framework map and guided start.
17. Interactions: expandable diagrams, tabs, filters, and copyable commands.
18. CLI commands: practical snippets without execution results.
19. Live Execution: architecture and operational guarantees only, no current
    production balances or positions.
20. Theme: dark theme required; light theme also remains in scope.
21. Name: `crypt docs`.
22. Framework-docs navigation: breadcrumbs and sidebar required.
23. Desktop on-page TOC: required.
24. Search UI: both header search and `Cmd/Ctrl+K`.
25. Mascots: needed.
26. Mascots: abstract, not crypto meme characters.
27. Risk markers: required for live money, OKX execution, config, and no
    look-ahead bias.
28. Every page needs "what to read next".
29. Section maturity statuses: stable, research, operational, archived.
30. First release should fill all sections thoroughly, not only provide a
    skeleton.

## Uncertainty Check

- Product scope: resolved as a large source-backed documentation portal for the
  whole repository.
- Stack: resolved as Next.js plus Tailwind; exact versions and router/search
  library remain implementation details.
- Data and API: no runtime metrics or current live data; content is static
  source-authored documentation.
- Auth and permissions: unresolved but likely not required unless later
  deployment target requires access control.
- Content: required sections are resolved; exact page tree and per-section
  source map remain for P02/P03.
- Visual direction: playful lo-fi with abstract mascots is resolved at a high
  level; five raster direction boards remain required before approval.
- Interaction and states: search, command palette, tabs, expandable diagrams,
  filters, copyable commands, breadcrumbs, side nav, desktop TOC, dark/light
  theme, risk labels, maturity labels, and next-read blocks are required.
- Accessibility and responsive behavior: standard D3 responsive and
  accessibility obligations apply; no waiver recorded.
- Success criteria: a developer-crypto-trader can understand how `crypt` works
  like a framework, navigate by learning path or subsystem, search full
  curated content, and understand risk/source-of-truth boundaries without live
  state exposure.

## Verdict

- Resolved evidence: owner answers 1-30, repository bootstrap, README, current
  state, and frontend subsystem.
- Remaining material unknowns: route map, content source map, implementation
  package details, visual boards, wireframes, screen contracts, QA evidence,
  and deployment target.
- Next phase: P02 factual product research, Product Surface Model authoring,
  independent review, and Product Surface Approval.
- Required owner gate: Product Surface Approval after P02 artifacts are ready.
