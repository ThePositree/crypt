# Frontend Context

Status: established.
Last verified: 2026-09-01.

This repository currently has no active frontend application checked into the
main project tree. When frontend code appears, inspect it before establishing
project-specific frontend rules.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: repository root scan on 2026-09-01.
- Observation: no active frontend application, package manager lockfile, or
  `.openai/hosting.json` exists in the main project tree.
- Confidence: high.

- Source: owner onboarding answers on 2026-09-01.
- Observation: the first frontend should live under `site/` and use Next.js
  with Tailwind CSS.
- Confidence: high.

- Source: Context7 documentation lookup on 2026-09-01.
- Observation: Next.js App Router uses the `app` directory, route handlers are
  implemented as `route.ts` files with named HTTP method exports, and
  production builds use `next build`; Tailwind CSS v4 uses
  `@import "tailwindcss"` in global CSS and `@tailwindcss/postcss` in
  PostCSS config.
- Confidence: high.

## Active Stack

- frontend framework: Next.js App Router under `site/`;
- build, package, and validation setup: npm with `package-lock.json`; scripts
  for `next dev`, `next build`, `next start`, and `tsc --noEmit`;
- styling approach: Tailwind CSS v4 through `@tailwindcss/postcss`, with
  product tokens in `site/app/globals.css`;
- UI libraries and local primitives: local React components plus `lucide-react`
  icons for standard controls and subsystem symbols;
- design tokens and CSS variables: established in `site/app/globals.css` and
  summarized in `docs/frontend/design-system.md`;
- themes and dark/light mode: public docs should start with one light pastel
  theme; dark mode is not in the first approved scope yet;
- typography: proposed in `docs/frontend/design-system.md`;
- icon libraries: `lucide-react`;
- form, chart, table, animation, and visualization libraries: native React/CSS
  for the first interactive map and search surfaces; no charting dependency yet;
- responsive conventions: desktop uses app shell with sidebar and map-first
  content; tablet/mobile collapse to single-column content with stacked map
  nodes and top controls;
- layout patterns: public docs portal with left navigation, journey navigation,
  search, interactive system map, guide pages, reference pages, glossary, and
  version selector;
- assets and imagery: abstract cute lo-fi mascot system and hand-drawn pastel
  diagrams are requested;
- component documentation, examples, or catalogs:
  `docs/frontend/component-registry.md`;
- established screen and component patterns: Docs Town home, curated doc page,
  backend search modal/route, guide step, source notes, and related-doc rail;
- legacy areas, migrations, and inconsistencies: the repository previously
  reverted a local docs portal commit; inspect any reintroduced frontend code
  before assuming it is authoritative.

## Unresolved Or Conflicting Evidence

- Decision affected: deployment target.
- Evidence: no `.openai/hosting.json` exists; Sites tooling is available but
  requires source, build output, commit SHA, and saved version before
  production deployment.
- Required resolution: deploy only after explicit owner request or hosting
  decision, because repository rules do not allow pushing without owner
  instruction.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
