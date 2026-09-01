# Documentation Portal Wireframe Index

Revision: 1.
Status: ready for Wireframe Approval.
Rendered: 2026-09-01 through Orca CLI `orca-ide` embedded browser.

## Viewport Evidence

Every package contains:

- `narrow-mobile.png`: CSS viewport `390×844`, DSF `1`.
- `mobile-wide.png`: CSS viewport `700×900`, DSF `1`.
- `tablet.png`: CSS viewport `820×1000`, DSF `1`.
- `desktop.png`: CSS viewport `1152×900`, DSF `1`.
- `large-desktop.png`: CSS viewport `1366×900`, DSF `0.9`.
- `wide-desktop.png`: CSS viewport `1600×1000`, DSF `0.75`.

Reduced device scale factors keep the large browser framebuffers within the
Orca client-host surface while preserving the declared CSS viewport and media
query behavior. The initial DSF 1 large/wide captures exposed framebuffer
repetition and were replaced after a clean reduced-DSF verification.

## Page-to-wireframe Map

Each artifact path below is a directory containing the six named PNGs above.

| Page | Route | Wireframe package | Screen contract | States/interactions | Content/discovery coverage | Inspection |
| --- | --- | --- | --- | --- | --- | --- |
| Home | `/` | `wireframes/home/` | `screens/home.md` | CTA, search, cards, nav, narrow/wide | all section destinations | all six rendered; narrow/wide inspected |
| Quick Start | `/docs/quick-start` | `wireframes/quick-start/` | `screens/quick-start.md` | steps, copy, tabs, warning, recovery | install-to-dry-run journey | all six rendered; narrow/wide inspected |
| What Is crypt | `/docs/overview` | `wireframes/overview/` | `screens/overview.md` | boundary cards, diagram, callout | system boundaries | all six rendered; narrow/wide inspected |
| Architecture | `/docs/architecture` | `wireframes/architecture/` | `screens/architecture.md` | diagram, anchors, partial/failure | modules and truth boundaries | all six rendered; narrow/wide inspected |
| Data | `/docs/data` | `wireframes/data/` | `screens/data.md` | tabs, table, copy, missing/error | sources, files, backfill | all six rendered; narrow/wide inspected |
| Strategies | `/docs/strategies` | `wireframes/strategies/` | `screens/strategies.md` | annotated config, diagram, errors | registry/config/signals | all six rendered; narrow/wide inspected |
| Backtester | `/docs/backtester` | `wireframes/backtester/` | `screens/backtester.md` | command, artifacts, invalid/partial | run/flags/artifacts | all six rendered; narrow/wide inspected |
| Research | `/docs/research` | `wireframes/research/` | `screens/research.md` | workflow tabs, copy, stopped/error | optimize and DSS mechanics | all six rendered; narrow/wide inspected |
| Live Execution | `/docs/live-execution` | `wireframes/live-execution/` | `screens/live-execution.md` | mode/sync/recovery states | safety and live boundaries | all six rendered; narrow/wide inspected |
| CLI | `/docs/cli` | `wireframes/cli/` | `screens/cli.md` | filter, copy, zero result | complete command inventory | all six rendered; narrow/wide inspected |
| Configuration | `/docs/configuration` | `wireframes/configuration/` | `screens/configuration.md` | tabs/filter/redaction/errors | setting groups and defaults | all six rendered; narrow/wide inspected |
| Development | `/docs/development` | `wireframes/development/` | `screens/development.md` | module map, checks, failure | modules and validation | all six rendered; narrow/wide inspected |
| Troubleshooting | `/docs/troubleshooting` | `wireframes/troubleshooting/` | `screens/troubleshooting.md` | symptom filter, accordion, blocked | errors and recovery | all six rendered; narrow/wide inspected |

## Shared Interaction Notes

- Search opens through button, `/`, or `Ctrl/Cmd+K`; results, zero, loading, and
  error states follow the Discovery Contract.
- On mobile, `Разделы` and `Содержание` open distinct accessible drawers.
- Code blocks contain local overflow and copy success/failure feedback.
- Diagrams become ordered vertical nodes below `768px`.
- Tables remain contained and horizontally scrollable with semantic headers.
- Previous/next links preserve the approved learning sequence.

## Source

`wireframes/source/` contains the deterministic gray-box renderer and per-page
data used for every capture. It is a design artifact, not production frontend code.
