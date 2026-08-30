# Public Portal Wireframe Review

Date: 2026-08-30
Status: revisions 1-2 superseded; revision 3 ready for owner Wireframe Approval
Artifact revision: 3

## Scope

Overview, Architecture, Research, Strategies, Execution, Concepts, History,
and Search wireframes; shared responsive navigation; page-family screen
contracts; navigation flow; proposed static implementation baseline.

Revision 2 responds to owner feedback that revision 1 was too symmetrical and
showed placeholders instead of real imagery. The Overview now uses a generated
Pocket Field Lab hero illustration as a full-bleed field wall, with typography,
an index tab, and the explanation-only boundary overlapping the image. Content
continues through an uneven specimen river rather than repeated horizontal
text/image bands.

Revision 3 responds to the follow-up that liveliness must apply to every page,
not only Overview. Three additional generated scenes provide architecture,
evidence-bench, and archive-vault visual narratives. All seven remaining pages
now open with alternating, overlapping, asymmetrically cropped chapter scenes;
the same image is reused only when the underlying metaphor is shared, with
page-specific crop, direction, tab, description, and downstream composition.

## Browser Evidence

- Tool: Orca `orca-ide`.
- Mobile composition: 390 x 844; Overview primary navigation collapses and the
  menu opens with correct `aria-expanded` state.
- All eight HTML pages loaded successfully with their shared CSS and JavaScript.
- Browser console: clean.
- Browser network: all HTML/CSS/JS returned 200 from the local server; no
  external requests.
- Structural snapshot confirmed semantic banner, navigation, main content,
  heading hierarchy, controls, content states, and footer on Overview.

## Functional Verdict

The proposed information architecture completes the three approved journeys:
guided learning, finding one answer, and understanding project history. The
Execution page retains a persistent explanation-only boundary and exposes no
operational action.

## Responsive Verdict

The shared contract uses a one-column mobile trail, collapsible navigation,
static local indices, single-column search results, and contained overflow for
wide evidence. Desktop retains asymmetric Overview composition and pinned
chapter indices. Exact production spacing and contrast remain implementation
QA concerns rather than gray-box blockers.

## Covered States

Normal, loading, empty, error, disabled/unavailable, local overflow, partial
data/evidence, and optional-illustration fallback.

## Remaining Decision

Select one stable name for the recurring human field researcher before final
copy freeze. This does not block layout approval.

## Image Generation Record

- Tool: built-in image generation through the `imagegen` skill.
- Assets: `mira-pocket-field-lab-hero-v1.png`,
  `mira-architecture-flow-v1.png`, `mira-evidence-bench-v1.png`, and
  `mira-archive-vault-v1.png` under `wireframes/assets/`.
- Shared invariants: Mira Vale, dusty mint field jacket, editorial gouache and
  pencil, paper collage, visible crypto/candlestick evidence, no readable
  generated text, no dashboard, no live controls, no profit imagery.

## Stack Revision

The owner selected Next.js App Router with TypeScript and Tailwind CSS. The
production plan uses Server Components and static generation by default, with
small Client Components for search, theme, mobile navigation, and focused
interactions. Current official Next.js and Tailwind v4 PostCSS setup guidance
was checked on 2026-08-30 because Context7 was unavailable.

## Gate

Wireframe Approval unlocks production implementation of all eight pages using
Next.js App Router and Tailwind CSS. Approval does not waive later
Functional QA, Visual QA, Product Completeness Review, or Final Implementation
Approval.
