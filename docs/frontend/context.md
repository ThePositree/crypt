# Frontend Context

Status: proposed.
Last verified: 2026-09-02.

This repository currently has no active frontend application checked into the
main project tree. When frontend code appears, inspect it before establishing
project-specific frontend rules.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: owner chat on 2026-09-02.
- Observation: the requested surface is a large curated documentation portal,
  built with Next.js and Tailwind. The portal must not render repository
  Markdown files directly; existing Markdown documents may be used only as
  source material for curated page content.
- Confidence: high for requested direction; implementation not started.

- Source: repository inspection on 2026-09-02.
- Observation: no active frontend application, package.json, Next.js config,
  Vite config, or `.openai/hosting.json` exists in the main project tree.
- Confidence: high for current checkout.

## Active Stack

- frontend framework: proposed Next.js;
- build, package, and validation setup: not implemented yet;
- styling approach: proposed Tailwind CSS with project-owned tokens;
- UI libraries and local primitives: not selected yet;
- design tokens and CSS variables: required, not implemented yet;
- themes and dark/light mode: both required in first release;
- typography: not selected yet;
- icon libraries: not selected yet;
- form, chart, table, animation, and visualization libraries: not selected yet;
- responsive conventions: use six viewport classes from
  `docs/agent/frontend_design_subsystem.md`;
- layout patterns: framework-docs shell with breadcrumbs, left navigation,
  top search, command palette, and desktop on-page table of contents;
- assets and imagery: playful abstract lo-fi mascots plus explanatory diagrams;
- component documentation, examples, or catalogs: not established yet;
- established screen and component patterns: none in production code;
- legacy areas, migrations, and inconsistencies: prior unfinished
  documentation-portal artifacts were reverted per `CHANGELOG.md`.

## Unresolved Or Conflicting Evidence

- Decision affected: final component library and search implementation.
- Evidence: owner selected Next.js, Tailwind, full-content search, and curated
  source-authored content, but no package exists yet.
- Required resolution: choose implementation libraries during Final
  Implementation Approval after visual direction, wireframes, and screen
  contracts are approved.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
