# Frontend Context

Status: established.
Last verified: 2026-09-01.

This repository is gaining a manually curated documentation portal under
`site/`. The portal explains how the `crypt` codebase works. It must not render
repository Markdown files directly and must not display runtime execution
results.

## Sources Inspected

- Source: owner chat, 2026-09-01.
- Observation: the owner selected Next + Tailwind, Russian copy, public access,
  server-side search over curated portal content, and a noticeable cartoon
  lo-fi pastel visual direction with multiple section-role characters.
- Confidence: high.

- Source: `README.md`, 2026-09-01.
- Observation: `crypt` is a research workbench and live OKX execution module
  for owner-selected crypto perpetual strategies. Core areas include research,
  strategy discovery, exact backtests, execution, OKX sync, Telegram reporting,
  and live/backtest reconciliation.
- Confidence: high.

- Source: `docs/state/current.yml`, 2026-09-01.
- Observation: runtime truth comes from loaded config/env, especially
  `EXECUTION_STRATEGY_CONFIG`; OKX is the source of truth for money, fills,
  fees, positions, and account equity.
- Confidence: high.

- Source: filesystem inspection, 2026-09-01.
- Observation: `site/` currently contains only empty app/component/lib/public
  directories and no active package/build files.
- Confidence: high.

## Active Stack

- frontend framework: Next, owner-selected; exact version pending
  implementation setup;
- build, package, and validation setup: pending implementation setup;
- styling approach: Tailwind, owner-selected;
- UI libraries and local primitives: pending implementation setup;
- design tokens and CSS variables: pending visual direction and design system;
- themes and dark/light mode: both required;
- typography: pending visual direction and design system;
- icon libraries: pending implementation setup;
- form, chart, table, animation, and visualization libraries: allowed where
  they support search, maps, diagrams, step flows, accordions, tabs, and
  production-quality docs behavior;
- responsive conventions: six viewport classes from
  `docs/agent/frontend_design_subsystem.md` apply unless waived by owner;
- layout patterns: framework-docs navigation with top categories and left tree;
- assets and imagery: generated raster illustrations for visual boards and
  portal assets; multiple persistent section-role characters;
- component documentation, examples, or catalogs: not yet implemented;
- established screen and component patterns: not yet implemented;
- legacy areas, migrations, and inconsistencies: none active in `site/`.

## Unresolved Or Conflicting Evidence

- Decision affected: exact Next/Tailwind versions and supporting libraries.
- Evidence: owner selected stack, but repository has no package metadata yet.
- Required resolution: consult current framework documentation before setup and
  record final dependencies during implementation planning.
