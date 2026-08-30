# Public Portal Wireframe Review

Date: 2026-08-30
Status: revision 1 rejected; revision 2 ready for owner Wireframe Approval
Artifact revision: 2

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
