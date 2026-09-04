# Product Surface Model

## Current State

- Artifact status: not established
- Revision: 0
- Approval decision: not requested
- Approval decision path or exact owner message:
- Effective date:

Allowed artifact-status values are `not established`, `proposed`, `reviewed`,
`approved`, `blocked`, and `superseded`. Allowed approval-decision values are
`not requested`, `pending`, `approved`, `rejected`, `waived`, and `superseded`.
Write exactly one value in each Current State field.

This file is the canonical frontend source of truth for what product the site,
app, portal, dashboard, tool, or game is building.

Keep it thin when the repository already has a canonical product description.
If a current `product.md`, `PRODUCT.md`, `project.md`, `PROJECT.md`, PRD, spec,
README product section, or equivalent source exists, link to it here and record
only the frontend-specific delta, boundaries, approval state, and conflicts.
Do not duplicate a full product document into this file.

If no canonical product source exists, this file records the product surface
directly until a stronger product source is created.

For a small product, the concrete surface records may live directly in this
file. For a large portal, catalog, dashboard, application, or documentation
corpus, keep this file as the compact authoritative root and point to a
file-backed Route And Template Catalog, normally rooted at
`docs/frontend/product-surface/index.md`. The catalog is a generated contract,
not part of the always-loaded compact memory set.

The Current State block above is the only current lifecycle and approval state
for this artifact. Do not add or restate another current status later in the
file. Historical decisions live in referenced decision records.

## Canonical Product Sources

- Primary source ID or explicit precedence rule:
- Frontend-specific delta kept here:
- Conflicts or stale claims:

| Source ID | Path | Revision or content hash | Status | Precedence | Facts owned | Frontend reads there for |
| --- | --- | --- | --- | --- | --- | --- |

## Product Surface

- Product name:
- Product Surface revision/hash referenced downstream:
- Audience:
- Primary job:
- Secondary jobs:
- Product capabilities in scope:
- Product non-goals explicitly excluded by the owner:
- Route And Template Catalog path, revision, and content hash:
- Required route/screen aggregate count and catalog closure verdict:
- Required pages or screens with stable surface IDs, directly or by catalog:
- Required journeys and endpoints with stable IDs:
- Required state families with stable IDs:
- Required Content Coverage Keys and aggregate count:
- Global shell and navigation:
- System surfaces: not-found, unauthorized, unavailable, offline, or other
  globally reachable states that apply
- Content and data coverage promised by the product:
- Search, discovery, filtering, indexing, and navigation coverage:
- Media, illustration, diagram, and asset coverage:
- Responsive and accessibility coverage:
- Source-of-truth boundaries:
- Risk or safety boundaries:
- Open owner decisions:

## Route And Template Catalog

When the product has enough routes that listing them here would stop this file
being compact, use a sharded catalog rooted at one compact index. Each concrete
route or meaningful screen row records:

- stable `surface_id`, canonical URL or state address, and route status;
- `template_id` and any structural or interaction exception ID;
- canonical `content_id` plus every Content Coverage Key;
- state families and journey IDs;
- global-shell, navigation, search, index, sitemap, and discovery membership;
- responsive and accessibility family IDs;
- source path/revision and row review status.

Each template row records shared structure, information hierarchy, interaction
model, required regions, state families, responsive transformations, and
accessibility relationships. Routes may share a template only when those
properties are actually identical; a structural, behavioral, state,
responsive, or accessibility difference creates an explicit exception or a
new template.

The root catalog records expected and covered route, template, state-family,
journey, system-surface, and Content Coverage Key counts, plus missing,
duplicate, orphan, and unreviewed counts. Approval requires every approved
surface to resolve exactly once to a current route record and every route to
resolve to a current template, reserved `content_id`, and complete Content
Coverage Keys. P03 Copy Approval, not P02 Product Surface Approval, later
requires those identities to resolve to reviewed canonical content leaves. All
missing, duplicate, orphan, and unreviewed Product Surface catalog counts must
be zero. Counts prove closure but do not replace independent semantic review.

## Phase Delivery Boundaries

- Current phase authors now:
- Mandatory later frontend phases and artifacts:
- Product behavior intentionally deferred by owner decision:
- Deferral decision path or waiver:

Phase boundaries are not product scope boundaries. Wireframes, content,
visual-direction boards, the UI library, production assets, screen contracts,
implementation, system routes, and QA must never be listed as product non-goals
merely because an earlier phase does not author them. A phrase such as "first
release" narrows the product only when the owner explicitly approved that
release boundary; it cannot be invented to make the contract smaller.

## Artifact Sources

- Owner onboarding answers:
- Independent factual research artifact:
- Product Surface Author context:
- Product Surface Contract Reviewer context:
- Accepted factual map IDs, revision, and hash:
- Route And Template Catalog author/reviewer, revision, hash, and closure:
- Rejected or unresolved facts:
- Related decisions:

Product Surface Approval updates only the Current State block and writes or
links its durable owner decision record. Approval covers the product surface
and genuine product non-goals. It does not approve skipping any mandatory later
phase listed above.
