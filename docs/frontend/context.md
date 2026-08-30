# Frontend Context

Status: production stack selected; no production frontend yet.
Last verified: 2026-08-30.

This repository currently has no active frontend application checked into the
main project tree. When frontend code appears, inspect it before establishing
project-specific frontend rules.

Record each discovered choice with its evidence rather than inferring a full
stack from one dependency or abandoned file.

## Sources Inspected

- Source: repository file inventory and `pyproject.toml`.
- Observation: no active JavaScript package, frontend framework, build config,
  UI library, or production frontend directory exists.
- Confidence: high.

- Source: approved Product Surface and Pocket Field Lab artifacts.
- Observation: the portal is public, read-only, self-contained, and can meet
  its first-release journeys with generated HTML, CSS, and native JavaScript.
- Confidence: high for first-release requirements.

## Active Stack

- Production frontend: none yet.
- Selected baseline: Next.js, TypeScript, App Router, Tailwind CSS v4, ESLint,
  and PostCSS. Prefer Server Components and static output; use Client
  Components only for genuine interaction.
- Styling: custom properties and component classes derived from Design System
  revision 1.
- Themes: accessible light/dark variables; system reduced-motion behavior.
- Typography: system serif/sans/monospace stacks; no remote fonts.
- Icons/charts/diagrams: inline SVG and semantic HTML/CSS.
- Responsive convention: mobile below 600 px, intermediate 600-999 px,
  desktop 1000-1599 px, wide 1600 px and above.
- Current durable patterns: eight gray-box wireframes under `wireframes/`;
  visual evidence under `visual-directions/` is not production code.

## Unresolved Or Conflicting Evidence

- Decision affected: hosting and generated-output location.
- Evidence: no deployment target or public frontend pipeline exists.
- Required resolution: may be selected during implementation without changing
  the approved user surface; static output must remain portable.

- Decision affected: recurring human guide name.
- Evidence: exploration boards use inconsistent names.
- Required resolution: owner or production copy pass selects one stable name
  before final implementation approval.

Stable, actively used choices are intentional unless stronger evidence shows
otherwise. Include the date observed because dependencies and conventions can
change.
