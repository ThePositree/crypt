# Docs Portal Wireframe Preflight

- Task Contract revision: Product Surface Model revision 1
- Execution context and methods: current Codex session, Orca browser snapshots
  against local file URLs
- Commit or working-tree state: uncommitted wireframe/screen-contract package
  after commit `033666d`
- Design/control session: current session
- Frontend Lead Contract Review Brief and reviewer/session:
  `docs/frontend/reviews/2026-09-02-docs-portal-contract-review-brief.md`,
  Orca dispatch `ctx_b4b20490149c`, first verdict block with no critical
  findings
- Frontend Implementation Brief and implementation worker/session: not created
  yet
- Independent QA owner/session: not run yet
- Scope validated: proposed HTML wireframe package for `crypt docs`
- Approved HTML wireframe addresses and state matrix:
  `docs/frontend/wireframes/docs-portal/README.md`
- Viewports and screenshots: desktop Orca browser snapshots only; six viewport
  classes remain required before approval completion
- Interactions exercised: header search/search fixture, theme toggle,
  accordion, tabs, command copy button, Home filters, stable zero-result search
  fixture, stable dark theme fixture
- Automated checks: file/route grep, inline script extraction with
  `node --check`, and browser snapshot smoke
- Console/network status: not inspected yet
- Accessibility checks: snapshot confirmed accessible names for major links,
  buttons, headings, textbox, and dialog; full accessibility pass pending
- Messaging System pass: proposed contracts only; full Text Inventory pending
- Text Inventory coverage: pending
- Copy/content reviewer verdict: pending
- Rubric Review:
  - Functional: preflight pass for core local interactions; independent QA
    pending.
  - Responsive: blocked until six viewport classes are inspected.
  - Visual: structure follows Board 3 direction at wireframe fidelity; detailed
    visual QA belongs to production implementation.
  - Copy: pending exhaustive Text Inventory.
  - Content and capability: page list covered by contracts; full content depth
    pending production content brief.
  - Discovery: search states represented; `OKX` query primary result and
    zero-result recovery checked against the expected-result matrix.
  - Accessibility: preliminary snapshot pass; full keyboard/focus/contrast QA
    pending.
  - Instruction control: Product Surface and Visual Direction gates approved;
    Wireframe Approval not yet requested.
- Known gaps and exact next action: run a fresh independent contract review
  after the follow-up fixes, then request Wireframe Approval or continue with
  owner-approved revisions.

## Post-Review Fix Validation

After addressing the first independent contract review block verdict, Orca
browser validation checked these fixtures again:

- `index.html?page=architecture&theme=dark`: nonblank page, dark fixture,
  source-boundary notice, tab panel, unique TOC anchors, and source-backed
  architecture snippet.
- `index.html?page=home&palette=1&q=OKX`: search overlay opens from fixture;
  the first result is Live Execution as required by the expected-result
  matrix.
- `index.html?page=home&palette=1&q=unknown`: zero-result state shows recovery
  links to the framework map and Glossary.
- `index.html?page=home`: Home renders the atlas and all cards; selecting the
  Research filter leaves only reference-section cards.
- `index.html?page=home&palette=1&q=no%20look-ahead%20bias`: grouped search
  results show Data Pipeline first under Guides and supporting Backtester and
  Glossary results under Reference.
- `index.html?page=architecture&nav=1`: drawer fixture exposes a dialog, close
  button, brand link, and navigation links.
- Browser eval confirmed the expected-result matrix primary route for
  `backtester`, `OKX`, `no look-ahead bias`, `strategy config`, `candles`,
  `CLI`, `Railway`, `risk base`, and `warmup`.
