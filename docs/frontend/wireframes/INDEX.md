# Documentation Portal Wireframe Index

Revision: 1
Status: approved; rendered inspection complete
Date: 2026-09-01

| Page | Route | Wireframe | States Covered | Interaction Notes | Content Coverage |
| --- | --- | --- | --- | --- | --- |
| Home | `/` | `home.html` | normal, selected map node, search suggestions, mobile drawer, dark theme | map nodes, top nav, left tree, search, signal journey, theme | all top-level sections |
| Search | `/search` | `search.html` | empty query, loading, results, zero-result, error, focus, dark theme | search input, suggestions, filters, results, retry | full curated corpus |
| Overview | `/overview` | `overview.html` | tabs, accordions, related links, dark theme | overview/deep-dive, route cards | whole project mental model |
| Architecture | `/architecture` | `architecture.html` | selected component, overflow diagram, partial explanation | architecture nodes, contract accordions | system boundaries |
| Data | `/data` | `data.html` | missing data, partial data, error explanation | data-flow steps, invariant accordions | data lifecycle |
| Strategies | `/strategies` | `strategies.html` | selected route, recipe expanded, disabled note | lifecycle tabs, recipes | strategies and discovery |
| Backtesting | `/backtesting` | `backtesting.html` | checkpoint selected, validation error, overflow | validation steps, recipes | backtester contracts |
| Live Execution | `/live-execution` | `live-execution.html` | dry-run, blocked entry, exchange error | trust-boundary tabs, scenarios | live architecture only |
| Operations | `/operations` | `operations.html` | scenario selected, warning, recovery expanded | scenario filters, accordions | operator scenarios |
| Glossary | `/glossary` | `glossary.html` | selected term, filtered terms, zero-result | alphabet, filters, term rows | glossary corpus |
| Signal Journey | `/signal-journey` | `signal-journey.html` | selected step, branch, partial data, blocked entry | timeline, branch toggle, cards | end-to-end signal path |

Declared viewport classes for inspection:

- 390px narrow mobile below 640px;
- 640px mobile-wide or small tablet;
- 768px tablet;
- 1024px desktop;
- 1280px large desktop;
- 1536px wide desktop.

These HTML wireframes are low-fidelity UI contracts. Final implementation may
change visual styling, but route coverage, information hierarchy, interactions,
states, and responsive transformations must remain aligned unless the owner
approves a change.

## Rendered Inspection Evidence

- Static server: `python -m http.server 4177 --bind 127.0.0.1` from
  `docs/frontend/wireframes/`.
- HTTP availability: all 11 wireframe pages returned `200`.
- Playwright snapshots opened: `home.html`, `search.html`,
  `signal-journey.html`.
- Screenshot evidence captured:
  - `docs/frontend/wireframes/evidence/wireframe-home-1536.png` at
    1536 x 960;
  - `docs/frontend/wireframes/evidence/wireframe-home-390.png` at
    390 x 844;
  - `docs/frontend/wireframes/evidence/wireframe-search-640.png` at
    640 x 900;
  - `docs/frontend/wireframes/evidence/wireframe-signal-1024.png` at
    1024 x 768.
- Playwright accessibility snapshots are preserved under
  `docs/frontend/wireframes/evidence/playwright-mcp/`. Raw `.log` files are
  excluded by repository ignore rules; console verdict is recorded here.
- Console status after favicon fix: 0 errors, 0 warnings on the current
  inspected page.
- Responsive verdict: page structure transforms as intended in inspected
  desktop/mobile samples; full six-viewport production QA remains required
  after implementation.

## Artifact-Phase Rubric

- Functional: proposed pass for wireframe phase; all routes are represented and
  core interactions are named.
- Responsive: proposed pass for wireframe phase; key transformations are
  declared and sampled.
- Visual: proposed pass for wireframe phase; low-fidelity layout aligns with
  approved visual direction without final styling.
- Copy: proposed pass for wireframe phase; semantic jobs are named in screen
  contracts, final copy remains implementation work.
- Content and capability: proposed pass for wireframe phase; all approved
  top-level sections have screen contracts.
- Discovery: proposed pass for wireframe phase; search and glossary contracts
  cover query, filter, empty, zero-result, and error states.
- Accessibility: proposed pass for wireframe phase; keyboard/focus obligations
  are recorded for implementation.
- Instruction control: proposed pass; Product Surface and Visual Direction
  approvals are recorded, implementation remains blocked until Final
  Implementation Approval.

## Approval Record

- Decision: approved by owner in chat on 2026-09-01.
- Owner wording: "утверждаю" in response to the Wireframe Approval gate.
- Next phase unlocked: Final Implementation Approval package.
