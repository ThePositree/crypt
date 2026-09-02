# Docs Portal Contract Review Result - 2026-09-02

## Review Context

- Reviewer channel: Orca orchestration worker.
- Dispatch: `ctx_b4b20490149c`.
- Task: `task_1d89e1c2a784`.
- Verdict: block.
- Critical findings: none.

## Blocking Findings

- HTML wireframe promised interactions that were not represented in the
  prototype: full-content search grouping, keyboard result navigation, Enter
  open, focus return, filter handlers, tab switching, copy behavior, and unique
  TOC anchors.
- Subsystem pages reused a generic template and exposed a fictional
  `crypt docs-check` command.
- Page contracts were too thin for acceptance: primary action, hierarchy,
  components, trust boundaries, states, responsive behavior, accessibility, and
  acceptance criteria were missing from most pages.
- Screen index wireframe paths were incorrect and did not include an approval
  evidence matrix.

## Non-Blocking Findings

- Some visual-direction documents still contradicted the approved Board 3
  direction.
- Responsive breakpoints differed between shell contract and HTML wireframe.
- Search queries were named but lacked expected-result criteria.
- Russian and English terminology needed a documented glossary/search policy.

## Follow-Up Fixes

- HTML wireframe now includes data-backed search, grouped snippets, keyboard
  result movement, Enter open, Escape focus return, working filters, tab
  switching, copy feedback, accordion state, and unique TOC anchors.
- The fictional `docs-check` snippet was removed and replaced with
  source-backed command/config/concept snippets.
- Page contracts now include the missing canonical fields for every
  first-release page and the search overlay.
- Search overlay now includes an expected-result matrix for representative
  discovery queries.
- Screen index paths and approval evidence rows were corrected.
- Board 3 approval is now reflected in product surface and visual board docs.
- Shell breakpoint contract and HTML breakpoints were aligned.

## Remaining Gate

Run a fresh independent contract review after local wireframe validation. If
the next review passes, the portal can move to owner Wireframe Approval before
Final Implementation Approval.

## Follow-Up Review - Second Pass

- Reviewer channel: Orca orchestration worker.
- Run: `run_6e6854b21301`.
- Dispatch: `ctx_7c4267eff452`.
- Task: `task_c26cb5bbd2d3`.
- Verdict: block.
- Critical findings: none.

The second review confirmed that page coverage, canonical page contracts,
forbidden-content boundaries, Board 3 direction, and principal responsive
thresholds were reconciled. It still blocked on two issues:

- Search fixture behavior did not yet satisfy every expected-result matrix
  query, emitted flat duplicate-heavy results instead of area groups, and
  zero-result recovery omitted Glossary.
- Palette keyboard navigation could lose the arrow/Enter handler after focus
  moved to a result link, and the mobile drawer lacked explicit focus
  containment/restoration behavior.

## Second-Pass Fixes

- Search results now use explicit primary/support query expectations for the
  expected-result matrix and render grouped result sections by area.
- Zero-result search now links to both the framework map and Glossary.
- Palette result activation now uses a local `openSlug()` transition that
  updates `page`, pushes a stable query URL, closes overlays, and re-renders
  the wireframe content.
- Palette keydown handling is attached to the overlay and document fallback so
  ArrowUp, ArrowDown, Enter, and Tab remain owned while the palette is open.
- Drawer open/close now records the opener, focuses the close button on open,
  restores focus on close, closes on backdrop/Escape, and traps Tab within the
  drawer container.

## Second-Pass Validation

- Inline script extraction plus `node --check` passed.
- Orca browser snapshot confirmed grouped results for
  `no look-ahead bias`, with Data Pipeline first.
- Orca browser snapshot confirmed zero-result recovery links to the framework
  map and Glossary.
- Orca browser snapshot confirmed the mobile drawer fixture exposes a dialog,
  close button, brand link, and navigation links.
- Orca browser eval confirmed all expected-result matrix primary routes:
  `backtester -> backtester`, `OKX -> live-execution`,
  `no look-ahead bias -> data-pipeline`,
  `strategy config -> configuration`, `candles -> data-pipeline`,
  `CLI -> cli`, `Railway -> operations`, `risk base -> glossary`, and
  `warmup -> backtester`.

## Follow-Up Review - Third Pass

- Reviewer channel: Orca orchestration worker.
- Run: `run_6e6854b21301`.
- Dispatch: `ctx_d9c83daa12bd`.
- Task: `task_9b66e1634076`.
- Verdict: block.
- Critical findings: none.

The third review confirmed that the previous scope remained intact, but still
blocked on two narrower issues:

- Search matrix results matched the intended pages but not the intended
  section-level results, and grouped output still repeated several near-identical
  page rows for one query.
- Escape restoration could still call both overlay close paths and restore
  focus from stale opener state after sequential palette/drawer use.

## Third-Pass Fixes

- Matrix queries now use explicit section-level result rows matching the search
  contract instead of deriving three repeated rows from every page section.
- Search fallback remains available for non-matrix queries, but representative
  approval queries now resolve to the exact primary/support section labels.
- Overlay close handlers now no-op when already closed and clear their opener
  references after restoration.
- Escape now closes the active palette first, otherwise the drawer, instead of
  closing both unconditionally.
- The `nav=1` fixture now opens the drawer through the same `openDrawer()`
  path as the runtime trigger.

## Third-Pass Validation

- Inline script extraction plus `node --check` passed.
- Orca browser eval confirmed all expected-result matrix primary slug/section
  pairs:
  `backtester -> backtester / Model`, `OKX -> live-execution / Boundaries`,
  `no look-ahead bias -> data-pipeline / Closed candles`,
  `strategy config -> configuration / Runtime truth`,
  `candles -> data-pipeline / Closed candles`,
  `CLI -> cli / Available commands`,
  `Railway -> operations / Railway boundary`,
  `risk base -> glossary / risk base`, and
  `warmup -> backtester / Warmup versus accounting`.
- Orca browser eval confirmed sequential drawer and palette close behavior:
  closing palette leaves drawer open, then closing drawer clears its trigger,
  and both stale opener references are cleared.
