# Frontend Context

Status: proposed for first active frontend application.
Last verified: 2026-09-03.

This repository currently has no active frontend application checked into the
main project tree. The owner approved the initial production stack direction in
chat on 2026-09-03: Next.js plus Tailwind CSS for a Russian documentation
portal named `crypt docs`.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: repository root file scan on 2026-09-03.
  Observation: no `package.json`, Next.js config, Vite config, or existing
  frontend application was present at repository root; only Python
  `pyproject.toml` exists.
  Confidence: high.
- Source: `pyproject.toml`.
  Observation: current active product stack is Python 3.12, `uv`, OKX/ccxt,
  pandas, pydantic, APScheduler, aiogram, loguru, pytest, ruff, and mypy.
  Confidence: high.
- Source: owner chat answers on 2026-09-03.
  Observation: first frontend application should use Next.js plus Tailwind,
  Russian UI/content, light and dark themes, full-content search, command
  palette, breadcrumbs, left navigation, desktop on-page TOC, playful lo-fi
  styling, and abstract mascots.
  Confidence: high.
- Source: `README.md`, `docs/state/current.yml`, `docs/architecture.md`.
  Observation: product is a research workbench plus live OKX execution module,
  not the historical signal-only Telegram MVP.
  Confidence: high.

## Active Stack

- Frontend framework: proposed Next.js application.
- Build, package, and validation setup: not implemented yet; must be added
  after Final Implementation Approval or owner waiver.
- Styling approach: proposed Tailwind CSS with local design tokens.
- UI libraries and local primitives: not established; prefer local docs
  components unless a maintained dependency materially reduces risk.
- Design tokens and CSS variables: not established; must support light and
  dark themes.
- Themes and dark/light mode: required by owner.
- Typography: not established; should support readable Russian technical docs.
- Icon libraries: not established; use a maintained icon set if adopted.
- Form, chart, table, animation, and visualization libraries: not established;
  diagrams use production React SVG components styled by Tailwind/CSS
  variables unless a later approved implementation contract supersedes this.
  Mermaid, canvas-only diagrams, and raster-only explanatory diagrams are not
  the default because they make light/dark theming and playful lo-fi styling
  harder to control.
- Responsive conventions: six viewport classes from
  `docs/agent/frontend_design_subsystem.md` apply unless waived.
- Layout patterns: framework-docs portal with top search, breadcrumbs, left
  navigation, right desktop TOC, guided start, and reference navigation.
- Assets and imagery: playful lo-fi abstract mascots are required; production
  raster asset pack applies if generated imagery is selected.
- Component documentation, examples, or catalogs: not established; D3 requires
  a storybook-like component showcase before production pages.
- Established screen and component patterns: none yet.
- Legacy areas, migrations, and inconsistencies: frontend docs exist, but no
  production frontend code exists.

## Unresolved Or Conflicting Evidence

- Decision affected: exact package location and deployment target.
  Evidence: owner chose Next.js plus Tailwind but did not name app directory or
  hosting target.
  Required resolution: propose repo-local package boundary during Final
  Implementation Approval.
- Decision affected: exact search implementation.
  Evidence: owner requires full-content search with command palette and header
  search; no CMS or backend search service is desired.
  Required resolution: propose static build-time index in source-controlled
  content unless implementation research finds a better maintained local
  option.
- Decision affected: exact search library.
  Evidence: full-content search must support mixed Russian and English terms
  without a backend.
  Required resolution: evaluate Pagefind, MiniSearch, and Fuse.js through
  current docs before implementation; choose one in the Final Implementation
  Approval package.
