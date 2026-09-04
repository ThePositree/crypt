# Frontend Reviews

Store durable frontend review records here. This file is the self-contained
base schema for bounded frontend reviewers. The phase-main brief supplies the
phase-specific criteria, immutable inputs, and acceptance boundary; a reviewer
does not need the full frontend subsystem unless instruction compliance is the
assigned review subject.

Each review record should include:

- review type: contract / first-use / wireframe visual / UI library / asset
  pack / copy / implementation QA / rubric / instruction audit;
- artifact paths and revisions reviewed;
- content hashes, dimensions, viewport/state, capture time, and capturer for
  every rendered or binary input;
- reviewer context and independence from the author or implementer;
- owner approvals or `FRONTEND WAIVER:` messages that affect scope;
- methods used: rendered inspection, browser screenshots, source checks,
  command output, accessibility checks, or targeted source verification;
- findings ordered by severity with reproduction, evidence, and required fix;
- verdict: pass / pass-with-fixes / block;
- re-review target when blocking findings are fixed.

Long delegated review output should be file-backed. Worker completion messages
should contain only a compact manifest: review path, verdict, blocking
findings, stable finding IDs, and optional supporting line references. The
design/control context should read targeted findings instead of importing the
whole review transcript.

Review inputs are immutable. Never overwrite a screenshot, raster, content
revision, or report while retaining its old verdict. A changed input receives a
new unique path or revision, supersedes the old one, and invalidates the
affected verdict until re-review. Use stable finding IDs or headings rather than
fragile line numbers as the primary identity.

For D3 heavy artifacts, the main design/control context is neither the artifact
author nor the reviewer. It provides
briefs, routes blockers, records compact manifests, and presents owner gates.
If the main context writes or fixes the reviewed artifact, captures gate visual
evidence, or appends its own visual verdict to a worker review, record the phase
as incomplete unless the owner granted a scoped `FRONTEND WAIVER:`.

Required review roles stay separate unless the owner records a scoped waiver:

- Factual Product Research before Product Surface Model authoring.
- Product Surface Model Contract Review before Product Surface Approval.
- Frontend Lead Contract Review before contract approval or implementation.
- First-Use Review before Wireframe Approval and final completion.
- Wireframe Rendered Visual QA before Wireframe Approval.
- Copy Review for substantial D2/D3 Content Contract Packages.
- Content Package closure review against every approved Content Coverage Key,
  including pinned child/source hashes and zero missing, duplicate, orphan, or
  unreviewed leaves, before Copy Approval.
- Selected Visual Direction Translation and UI Fidelity Asset Seed image review,
  or an explicit independent seed non-applicability verdict, before P05 closes.
- Production UI Library source/reuse and image-fidelity reviews before product
  pages.
- Production Raster Asset Pack Review when raster assets apply.
- Independent Frontend QA after product-surface implementation.

Review records name the exact next action: approve, fix, re-review, request an
owner decision, or stop on a blocker.

Image-fidelity reviewers must open the actual selected raster and fresh rendered
captures. They first compare whole images side by side at declared viewport and
aspect ratio, then inspect critical crops and the Signature Traits Matrix.
Source, CSS, DOM, tokens, or an accessibility tree cannot substitute for the
rendered comparison. A passing report still names the three largest remaining
visible differences and why none is material.

## QA Evidence Record Template

```md
# Frontend Review

- Task Contract revision:
- Execution context and methods:
- Commit or working-tree state:
- Design/control session:
- Frontend Lead Contract Review Brief and reviewer/session:
- First-Use Review brief and reviewer/session:
- Source-Grounded Content Author and source map:
- Independent Copy Reviewer/session:
- Product-Surface Implementation Brief and implementation worker/session:
- Implementer session:
- Independent QA owner/session:
- Independent QA Brief and iteration/decomposition:
- Scope validated:
- Interaction Inventory:
- Approved HTML wireframe addresses and state matrix:
- Wireframe Conformance Contract and production mapping/verdict:
- Links, navigation, interactions, data, and API states exercised:
- Immutable viewport/state screenshots with revision, hash, and capture time:
- Automated checks and console/network status:
- Accessibility checks:
- Messaging System pass:
- Content Contract Package and shared UI copy coverage:
- Copy/content reviewer verdict:
- Rubric, Functional, Visual, Copy, Responsive, and Product Completeness verdicts:
- Final Instruction Audit:
- Known gaps and exact next action:
```
