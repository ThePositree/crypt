# Frontend Context

Status: proposed.
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

- frontend framework: proposed Next.js App Router under `site/`;
- build, package, and validation setup: proposed npm scripts for `next dev`,
  `next build`, `next start`, linting, and type-aware TypeScript checks;
- styling approach: proposed Tailwind CSS v4 through `@tailwindcss/postcss`;
- UI libraries and local primitives: not yet selected; prefer small local
  primitives unless a dependency clearly reduces maintenance risk;
- design tokens and CSS variables: proposed in `docs/frontend/design-system.md`;
- themes and dark/light mode: public docs should start with one light pastel
  theme; dark mode is not in the first approved scope yet;
- typography: proposed in `docs/frontend/design-system.md`;
- icon libraries: not yet selected; use a maintained icon package if controls
  need recognizable symbols;
- form, chart, table, animation, and visualization libraries: not yet selected;
  interactive system map may use native React/SVG first unless a library is
  justified by interaction complexity;
- responsive conventions: not established; required before implementation via
  wireframes and screen contracts;
- layout patterns: public docs portal with left navigation, journey navigation,
  search, interactive system map, guide pages, reference pages, glossary, and
  version selector;
- assets and imagery: abstract cute lo-fi mascot system and hand-drawn pastel
  diagrams are requested;
- component documentation, examples, or catalogs: not established;
- established screen and component patterns: none yet;
- legacy areas, migrations, and inconsistencies: the repository previously
  reverted a local docs portal commit; inspect any reintroduced frontend code
  before assuming it is authoritative.

## Unresolved Or Conflicting Evidence

- Decision affected: exact package manager and dependency versions.
- Evidence: Python project has no JavaScript lockfile; owner selected
  Next.js/Tailwind but not npm/pnpm/yarn.
- Required resolution: choose a package manager before implementation.

- Decision affected: deployment target.
- Evidence: no `.openai/hosting.json` exists; Sites tooling is available but
  requires source, build output, commit SHA, and saved version before
  production deployment.
- Required resolution: create local site first, then create/save/deploy through
  Sites after implementation approval and validation.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
