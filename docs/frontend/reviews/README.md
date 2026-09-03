# Frontend Reviews

Store durable frontend review records here. The canonical review rules live in
`docs/agent/frontend_design_subsystem.md`; do not duplicate that subsystem in
individual review files.

Each review record should include:

- review type: contract / first-use / wireframe visual / UI library / asset
  pack / copy / implementation QA / rubric / instruction audit;
- artifact paths and revisions reviewed;
- reviewer context and independence from the author or implementer;
- owner approvals or `FRONTEND WAIVER:` messages that affect scope;
- methods used: rendered inspection, browser screenshots, source checks,
  command output, accessibility checks, or targeted source verification;
- findings ordered by severity with reproduction, evidence, and required fix;
- verdict: pass / pass-with-fixes / block;
- re-review target when blocking findings are fixed.

Long delegated review output should be file-backed. Worker completion messages
should contain only a compact manifest: review path, verdict, blocking
findings, and line references. The design/control context should read targeted
lines instead of importing the whole review transcript.

For D3 heavy artifacts, the main design/control context is neither the artifact
author nor the reviewer when independent contexts are available. It provides
briefs, routes blockers, records compact manifests, and presents owner gates.
If the main context writes the reviewed artifact itself after delegating
research, record the phase as incomplete unless the owner granted a scoped
`FRONTEND WAIVER:`.

Required review roles stay separate unless the owner records a scoped waiver:

- Factual Product Research before Product Surface Model authoring.
- Product Surface Model Contract Review before Product Surface Approval.
- Frontend Lead Contract Review before contract approval or implementation.
- First-Use Review before Wireframe Approval and final completion.
- Wireframe Rendered Visual QA before Wireframe Approval.
- Copy Review for substantial D2/D3 text and Text Inventory.
- UI Library Approval Review before production pages.
- Production Raster Asset Pack Review when raster assets apply.
- Independent Frontend QA after production implementation.

Review records name the exact next action: approve, fix, re-review, request an
owner decision, or stop on a blocker.
