# Visual References Interpretation

Status: Visual Direction Boards generated; Visual Direction Approval pending.
Revision: 1
Date: 2026-09-03
Product Surface: `docs/frontend/product-surface-model.md` Revision 2, approved.
Messaging/Design Source: `docs/frontend/messaging.md`, `docs/frontend/design-identity.md`, and `docs/frontend/design-system.md` Revision 2, pending owner visual approval.

This file records the five required raster Visual Direction Boards for the
`crypt docs` documentation portal. These boards are direction studies, not
production copy or final UI screenshots. Production implementation must
translate the selected board into accessible Next.js + Tailwind components and
must not copy generated text literally.

## Board Evidence Table

| Board | Path | Product Hypothesis | Representative UI Fragments | State/Component Coverage | Inspection Evidence | Strengths | Trade-offs |
|---|---|---|---|---|---|---|---|
| Workshop Ledger | `docs/frontend/visual-references/positive/workshop-ledger-board-2026-09-03.png` | A calm workshop notebook for understanding data flows and risk gates. | Header search, left docs nav, central article, right TOC, risk callout, tabs, accordion, flow diagram, command-only CLI panel, table, component sidebar. | Light theme, search input, toggles, checkboxes, radio controls, badges, tabs, accordion, flow steps. | Saved PNG, 1536x1024, visually inspected after generation; readable macro layout; no obvious overlap. | Best balance of friendly lo-fi warmth and dense framework-docs clarity. | Less distinctive than the more specialized architecture and live-risk boards. |
| Signal Playground | `docs/frontend/visual-references/positive/signal-playground-board-2026-09-03.png` | A playful research workbench for DSS v3 and strategy discovery. | Strategy discovery article, command palette, filterable table, tabs, accordions, multi-timeframe diagram, mobile preview, component gallery. | Light theme, mobile preview, filters, pagination, maturity badges, command palette, diagram layers. | Saved PNG, 1536x1024, visually inspected after generation; no blank or broken regions. | Strongest for research/reference interactivity and full-content discovery. | More saturated and playful; may need restraint for live execution pages. |
| Risk Sentry Manual | `docs/frontend/visual-references/positive/risk-sentry-manual-board-2026-09-03.png` | A safety-first operations manual for OKX live execution architecture. | Live execution page, order lifecycle state machine, risk warnings, right TOC, maturity selector, tabs, command-only CLI block, what-to-read-next. | Light theme, risk/protected/operational/invariant badges, accordions, state machine diagram, safety callouts. | Saved PNG, 1536x1024, visually inspected after generation; state hierarchy and risk zones are clear. | Best expression of high-stakes warnings without live metrics. | Darker header and stronger red may dominate if used across the whole portal. |
| Architecture Atlas | `docs/frontend/visual-references/positive/architecture-atlas-board-2026-09-03.png` | A technical atlas where the first viewport is a map of the framework. | Large architecture map, research/runtime split, configuration boundary, right glossary/TOC, mobile preview, component footer, command-only CLI panel. | Light theme, architecture diagram, badges, callouts, tabs, accordions, mobile route map. | Saved PNG, 1536x1024, visually inspected after generation; diagram is the strongest first-viewport product signal. | Best candidate for the portal home and architecture-first navigation. | Generated diagram text is dense; production must redraw diagrams natively. |
| Pocket Framework Handbook | `docs/frontend/visual-references/positive/pocket-framework-handbook-board-2026-09-03.png` | A compact practical handbook joining guided learning and reference docs. | Home/overview page, route cards, command palette, mobile preview, dark theme preview, glossary chips, risk callout, read-next section. | Light and dark theme samples, mobile preview, tabs, accordions, copy button state, chips, route cards. | Saved PNG, 1536x1024, visually inspected after generation; responsive intent is clear. | Best combined tutorial/reference home structure and dark theme hint. | Some generated body text is small; production must use real Russian copy from messaging contracts. |

## Recommended Direction

Recommended selection: **Architecture Atlas mixed with Pocket Framework Handbook**.

Rationale:

- Architecture Atlas gives the clearest first-viewport signal for a
  framework-style documentation portal: the user immediately sees research,
  runtime, configuration, data, and execution boundaries.
- Pocket Framework Handbook has the strongest practical navigation model:
  guided learning route, reference route, search palette, mobile preview, dark
  theme sample, glossary, and what-to-read-next behavior.
- Workshop Ledger should inform component softness and page density.
- Risk Sentry Manual should inform live execution, OKX, configuration, and
  high-stakes risk callouts.
- Signal Playground should inform DSS v3, strategy discovery, filters, and
  command palette behavior.

If the owner approves this mix, a final combined raster direction board must be
generated before downstream implementation translation, because production
should not reconcile multiple competing boards without a single selected
reference.

## Reference Records

### Workshop Ledger - POSITIVE REFERENCE

SOURCE:
- `docs/frontend/visual-references/positive/workshop-ledger-board-2026-09-03.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen`, 2026-09-03.

LIKE:
- Calm ivory workspace, soft mint emphasis, readable docs layout, clear
  component showcase, friendly abstract mascots, command-only snippet framing.

AVOID:
- Treating the generated CLI text as canonical copy.

DO NOT COPY:
- Exact generated labels, synthetic commands, or raster-rendered text.

LOCAL PRODUCT PRINCIPLE:
- Dense docs can feel approachable without turning into a marketing page.

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- Left navigation, right TOC, central page content, flow schematic, semantic
  badges, risk callout, and mascots are visible in the raster itself.

APPROVAL:
- pending.

### Signal Playground - POSITIVE REFERENCE

SOURCE:
- `docs/frontend/visual-references/positive/signal-playground-board-2026-09-03.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen`, 2026-09-03.

LIKE:
- Research-oriented interactivity: filters, strategy table, command palette,
  multi-timeframe diagram, and mobile preview.

AVOID:
- Over-saturation on pages that need sober operational tone.

DO NOT COPY:
- Exact generated strategy rows, body text, or illustrated claims.

LOCAL PRODUCT PRINCIPLE:
- Research sections should feel exploratory while still preserving evidence,
  filters, and maturity status.

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- Distinct research badges, command palette, layered diagram, filter table,
  playful abstract shapes, and component states are visible.

APPROVAL:
- pending.

### Risk Sentry Manual - POSITIVE REFERENCE

SOURCE:
- `docs/frontend/visual-references/positive/risk-sentry-manual-board-2026-09-03.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen`, 2026-09-03.

LIKE:
- Strong risk hierarchy, visible state machine, operational tone, and clear
  separation between protected, blocked, operational, and closed states.

AVOID:
- Letting red warnings dominate neutral educational pages.

DO NOT COPY:
- Any pseudo-command text or generated lifecycle wording as final copy.

LOCAL PRODUCT PRINCIPLE:
- Live execution pages must feel protective and explicit without becoming a
  live trading terminal.

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- Risk callouts, OKX state machine, side navigation, right TOC, safety mascot,
  and read-next cards are visible.

APPROVAL:
- pending.

### Architecture Atlas - PRIMARY CANDIDATE

SOURCE:
- `docs/frontend/visual-references/positive/architecture-atlas-board-2026-09-03.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen`, 2026-09-03.

LIKE:
- First-viewport framework map, two-domain architecture split, rich route
  taxonomy, glossary/TOC proximity, component footer, and mobile preview.

AVOID:
- Raster-generated diagram labels as production text.

DO NOT COPY:
- Generated diagram copy or any inaccurate module name.

LOCAL PRODUCT PRINCIPLE:
- The home and architecture pages should communicate the framework topology
  before asking the reader to choose a deep section.

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- Architecture map, navigation, semantic badges, diagram legend, mascots,
  mobile preview, and component set are visible.

APPROVAL:
- pending.

### Pocket Framework Handbook - PRIMARY CANDIDATE

SOURCE:
- `docs/frontend/visual-references/positive/pocket-framework-handbook-board-2026-09-03.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen`, 2026-09-03.

LIKE:
- Practical dual-entry homepage, command palette, mobile layout, dark theme
  sample, risk card, glossary chips, and what-to-read-next section.

AVOID:
- Overly compact body copy and any impression of a shallow quick-start only.

DO NOT COPY:
- Exact generated Russian paragraphs or placeholder CLI strings.

LOCAL PRODUCT PRINCIPLE:
- The portal should support both guided reading and direct reference lookup
  from the first screen.

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- Tutorial route, reference route, search palette, mobile preview, dark theme
  sample, route cards, and mascots are visible.

APPROVAL:
- pending.
