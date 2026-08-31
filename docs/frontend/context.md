# Frontend Context

Status: initial static site established.
Last verified: 2026-08-31.

This repository has an initial static frontend in `site/`. It is a read-only
HTML/CSS/JavaScript website surface and does not use a package manager,
framework, server runtime, exchange credentials, or live API calls.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: `README.md`
- Observation: repository product framing is a research workbench plus live OKX
  execution module for crypto perpetual strategies.
- Confidence: high.

- Source: `site/index.html`, `site/styles.css`, `site/app.js`
- Observation: active frontend stack is static HTML/CSS/JavaScript with a
  canvas-based illustrative chart and no build step.
- Confidence: high.

- Source: root project files
- Observation: no `package.json`, Next/Vite config, or frontend lockfile exists.
- Confidence: high.

## Active Stack

- frontend framework: none; static HTML.
- build, package, and validation setup: no build step; open `site/index.html`
  directly or serve the repository root with a static HTTP server.
- styling approach: hand-written CSS in `site/styles.css`.
- UI libraries and local primitives: none.
- design tokens and CSS variables: CSS custom properties in `:root`.
- themes and dark/light mode: light site with one dark execution band.
- typography: system sans stack; no external font dependency.
- icon libraries: none.
- form, chart, table, animation, and visualization libraries: canvas chart in
  `site/app.js`; no external libraries.
- responsive conventions: desktop multi-column layouts collapse to one column
  below 1040px and 680px.
- layout patterns: sticky top navigation, full-width sections, individual
  cards for repeated evidence/features, code block for runbook command.
- assets and imagery: code-rendered canvas visual only.
- component documentation, examples, or catalogs: none.
- established screen and component patterns: initial site home documented in
  `docs/frontend/screens/site-home.md`.
- legacy areas, migrations, and inconsistencies: empty `app/`, `components/`,
  `lib/`, and `public/` directories exist without frontend source files.

## Unresolved Or Conflicting Evidence

- Decision affected: future framework adoption.
- Evidence: the current site is static, while empty `app/` and `components/`
  directories could imply an abandoned or planned app-router structure.
- Required resolution: choose a framework only when the owner asks for dynamic
  UI, live data, routing beyond a static site, or deployment requirements that
  justify it.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
