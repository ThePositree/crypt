# Docs Portal Wireframe Package

Status: proposed for Wireframe Approval
Revision: 1
Date: 2026-09-02
Approved visual direction: Board 3, `System Islands Atlas`

## Directly Openable HTML

Open `index.html` directly in a browser. The shared renderer exposes stable
addresses through query parameters:

| Page or state | Address |
| --- | --- |
| Home | `index.html?page=home` |
| Overview | `index.html?page=overview` |
| Architecture | `index.html?page=architecture` |
| Backtester | `index.html?page=backtester` |
| Strategies | `index.html?page=strategies` |
| Live Execution | `index.html?page=live-execution` |
| Data Pipeline | `index.html?page=data-pipeline` |
| CLI | `index.html?page=cli` |
| Configuration | `index.html?page=configuration` |
| Operations | `index.html?page=operations` |
| Glossary | `index.html?page=glossary` |
| Search overlay | `index.html?page=home&palette=1` |
| Zero-result search | `index.html?page=home&palette=1&q=unknown` |
| Mobile navigation state | `index.html?page=architecture&nav=1` |
| Dark theme state | `index.html?page=architecture&theme=dark` |

## State Matrix

| State | Entry action or fixture | Expected behavior | Evidence target |
| --- | --- | --- | --- |
| Normal page | `?page=<slug>` | Shell, breadcrumbs, left nav, content, TOC, badges, and next-reading render. | Browser visual inspection at six viewport classes. |
| Search open | `?palette=1` or `Cmd/Ctrl+K` | Command palette opens, focus is in search input, results group by area. | Functional and keyboard QA. |
| Zero search | `?palette=1&q=unknown` | Empty state explains no curated match and links to map/glossary. | Discovery QA. |
| Theme dark | `?theme=dark` or theme toggle | Dark documentation chrome appears without changing structure. | Visual and accessibility QA. |
| Mobile nav | `?nav=1` below 768px | Navigation drawer opens, page content remains behind overlay. | Mobile rendered QA. |
| Accordion expanded | Click any accordion row | Row expands with local explanatory text. | Functional QA. |
| Tab selected | Click tab | Active panel changes without navigation. | Functional QA. |
| Command copied | Click copy button | Button gives local copied feedback. | Functional QA. |

## Operable Interactions

- Left navigation links.
- Breadcrumb links.
- Header search and `Cmd/Ctrl+K` command palette.
- Search result selection.
- Theme toggle.
- Mobile navigation drawer open/close.
- Page TOC anchor links.
- Tabs.
- Accordions.
- Copy command buttons.
- Status/risk filters on Home.
- Next-reading links.

## Responsive Coverage

Required viewport classes:

- 360px narrow mobile.
- 640px mobile-wide or small tablet.
- 768px tablet.
- 1024px desktop.
- 1280px large desktop.
- 1536px wide desktop.

The wireframe must be rendered and inspected at these widths before
Wireframe Approval.

## Rendered Preflight Evidence

- 2026-09-02 Orca browser opened
  `file:///home/n-tretyakov/projects/crypt/docs/frontend/wireframes/docs-portal/index.html?page=architecture`.
- Snapshot evidence showed nonblank shell, left navigation, breadcrumbs,
  page heading, risk/status badges, tabs, candles-to-execution flow,
  accordion rows, command copy button, next-reading links, and desktop TOC.
- Stable fixture
  `index.html?page=home&palette=1&q=unknown` showed the command palette
  zero-result state with recovery links to the framework map and Glossary.
- Stable fixture `index.html?page=architecture&theme=dark` showed the dark
  theme page structure.
- Click preflight exercised header search, theme toggle, accordion row, and
  copy command button. These checks are preflight only and do not replace
  independent QA.
- Post-review validation confirmed grouped search results for
  `no look-ahead bias`, Live Execution as the first `OKX` result, and drawer
  fixture visibility after the search/focus follow-up fixes.
- Remaining approval evidence required: six viewport classes, full state
  matrix screenshots or snapshots, and independent contract review before
  Wireframe Approval can be treated as complete.

## Content Coverage

Every first-release page is represented in the shared HTML renderer and has a
screen contract under `docs/frontend/screens/docs-portal/`.
