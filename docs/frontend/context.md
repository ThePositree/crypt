# Frontend Context

Status: established.
Last verified: 2026-09-01.

This repository contains a local Next.js docs portal in the main project tree.
It is a manually curated product documentation surface, not a markdown renderer.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: root `app/`, `components/`, `lib/`, `public/` directories.
- Observation: directories existed but were empty before the docs portal implementation.
- Confidence: high.

- Source: `package.json`, `next.config.ts`, `postcss.config.mjs`, `app/layout.tsx`, `app/globals.css`.
- Observation: the portal uses Next.js App Router, TypeScript, React, and Tailwind CSS v4 through PostCSS and `@import "tailwindcss"`.
- Confidence: high.

- Source: owner input on 2026-09-01.
- Observation: the portal is local for now, English language, aimed at crypto developers, visually pastel cartoon lo-fi with developer desk motifs, and manually curated.
- Confidence: high.

## Active Stack

- frontend framework: Next.js App Router.
- build, package, and validation setup: npm scripts `dev`, `build`, `start`.
- styling approach: Tailwind CSS v4 utilities plus project CSS variables in `app/globals.css`.
- UI libraries and local primitives: local React components under `components/`.
- design tokens and CSS variables: pastel desk palette in `:root` of `app/globals.css`.
- themes and dark/light mode: single light lo-fi theme.
- typography: rounded system UI stack, monospace only for terminal-like fragments.
- icon libraries: `lucide-react`.
- form, chart, table, animation, and visualization libraries: no chart or table library yet; lightweight visualization is hand-built React/CSS.
- responsive conventions: mobile and desktop are first-class; layouts use single-column mobile and wider grid compositions from medium/large breakpoints.
- layout patterns: sticky header, left docs navigation on desktop, stacked navigation/content on mobile, card-like page modules with hand-drawn borders.
- assets and imagery: no external raster assets; lo-fi desk illustration is built with HTML/CSS and lucide icons.
- component documentation, examples, or catalogs: component registry records meaningful reusable components.
- established screen and component patterns: portal shell, page cards, search dialog, architecture map, pipeline stepper, module tabs, desk illustration.
- legacy areas, migrations, and inconsistencies: none known for frontend; previous directories were empty.

## Unresolved Or Conflicting Evidence

- Decision affected: deployment target.
- Evidence: owner said local for now and will deploy themselves.
- Required resolution: do not add hosting-specific config until requested.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
