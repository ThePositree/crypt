# Component Registry

Record meaningful reusable frontend components here.

Before creating a new component, check in order:

1. Existing project component.
2. Existing UI-library primitive.
3. Composition of existing primitives.
4. New component or primitive.

Use this format:

```md
## Component Name

- Location:
- Purpose:
- Built from:
- Why existing primitives were insufficient:
- Usage constraints:
- States:
- Content, data, or capability coverage:
- Discovery/search behavior:
- Accessibility behavior:
- Responsive behavior:
- Related screens:
- Validation evidence:
```

## App Shell

- Location: `site/components/AppShell.tsx`
- Purpose: persistent public docs frame with brand, global search, version
  selector, topic navigation, and helper card.
- Built from: Next.js `Link`, local `SearchBox`, `VersionSelector`, `Mascot`,
  and `lucide-react` icons.
- Why existing primitives were insufficient: first frontend in this repository;
  no local primitives existed.
- Usage constraints: public docs only; no private runtime data or account
  controls.
- States: desktop sidebar, collapsed mobile controls, focus/hover states.
- Content, data, or capability coverage: topic navigation covers approved
  first-version page inventory.
- Discovery/search behavior: exposes global backend search trigger.
- Accessibility behavior: header, navigation labels, links, buttons, and
  visible focus outlines.
- Responsive behavior: sidebar hidden below tablet width; search remains
  available in top controls.
- Related screens: Docs Town home, doc pages, search page.
- Validation evidence: `npm run build`, Playwright desktop/mobile screenshots
  under `docs/frontend/reviews/evidence/site/`.

## Docs Town Map

- Location: `site/components/DocsTownMap.tsx`
- Purpose: interactive first-viewport system map for the public docs portal.
- Built from: curated `mapNodes` content, Next.js `Link`, local `Mascot`, CSS
  subsystem tones, and `lucide-react` icons.
- Why existing primitives were insufficient: the approved visual direction
  needs a product-specific clickable map, not a generic card grid.
- Usage constraints: map nodes link only to curated public docs.
- States: default, hover, focus, selected detail.
- Content, data, or capability coverage: Data Station, Engine Workshop,
  Strategy Studio, Backtest Lab, Execution Boundary Bridge, Report Library, and
  Risk Clinic.
- Discovery/search behavior: complements search by exposing spatial subsystem
  discovery.
- Accessibility behavior: each node is a real link with readable text; mascot
  is decorative.
- Responsive behavior: absolute map on desktop, stacked tappable nodes on
  mobile.
- Related screens: Home/System Map.
- Validation evidence: Playwright screenshots at 1440x1100 and mobile
  viewport, build route inventory.

## Search Box

- Location: `site/components/SearchBox.tsx` and `site/app/api/search/route.ts`
- Purpose: backend-backed search modal over curated public pages, glossary
  entries, and architecture nodes.
- Built from: React client state, Next.js route handler, and
  `searchDocs()` in `site/lib/content.ts`.
- Why existing primitives were insufficient: search behavior needs project
  ranking, grouped result types, and public-content boundaries.
- Usage constraints: index public curated content only.
- States: idle, loading, ready, empty, error.
- Content, data, or capability coverage: pages, guide steps, glossary terms,
  map nodes, tags, body summaries, and source refs.
- Discovery/search behavior: exact title/glossary matches rank before tags and
  body matches.
- Accessibility behavior: dialog role, labelled input, keyboard shortcut, close
  button, focus target.
- Responsive behavior: modal fits mobile viewport.
- Related screens: all docs screens and `/search`.
- Validation evidence: `curl /api/search?q=backtester`, `/search?q=risk`
  Playwright open, build.

## Guide Step

- Location: `site/components/GuideStep.tsx` and
  `site/components/CopyButton.tsx`
- Purpose: curated command -> expected output -> explanation pattern for
  framework-style guides.
- Built from: local React components and Clipboard API.
- Why existing primitives were insufficient: command/output/explanation is a
  product-specific guide contract.
- Usage constraints: commands must be source-backed and public-safe.
- States: default and copied.
- Content, data, or capability coverage: guide steps in `site/lib/content.ts`.
- Discovery/search behavior: guide text is indexed by backend search.
- Accessibility behavior: button labels and readable code blocks.
- Responsive behavior: three columns on desktop, one column on mobile.
- Related screens: Backtester and For Developers.
- Validation evidence: build and rendered doc page QA.
