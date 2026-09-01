# Docs Portal Product Direction

- Date: 2026-09-01
- Status: approved
- Affected artifact revisions: Product Surface Model revision 1; Messaging revision 1

## Context

The repository has no active frontend. The owner requested a new public
documentation portal and completed the D3 onboarding sequence.

## Decision

Build a Russian-only, curated Next.js and Tailwind CSS documentation portal for
developers who also trade crypto. Present `crypt` as a research-to-execution
workbench. Use a classic documentation shell and a dark pastel, cartoon lo-fi
crypto-workshop identity with three recurring characters: a researcher, a
backtester robot, and a live-execution operator.

The first release covers Home, Quick start, Overview, Architecture, Data,
Strategies, Backtester, Research, Live execution, CLI, Configuration,
Development, and Troubleshooting. It includes local full-text search and deep
authored content, but no strategy performance results, Markdown rendering,
authentication, trading controls, or version switcher.

## Consequences

- Current source code and specialist contracts take precedence over stale
  overview prose.
- Every page requires its own wireframe and screen contract before implementation.
- Live execution documentation is detailed but the site remains read-only.
- The owner approved Product Surface revision 1 on 2026-09-01 by replying `да`
  to the named approval gate. This approval unlocks visual exploration and does
  not authorize implementation.

## Validation Or Revisit Trigger

Revisit when the public audience, page inventory, current-main policy, results
boundary, or read-only product boundary changes.

## Owner Waiver

On 2026-09-01 the owner granted:

`FRONTEND WAIVER: Five raster Visual Direction Boards — создать три направления вместо пяти.`

The waiver changes only the exploration count. Three boards must still satisfy
the full raster UI showcase, component, state, desktop/mobile inspection, and
Visual Direction Approval evidence requirements.

## Visual Direction Approval

On 2026-09-01 the owner selected only Board 1, Warm Workshop. Boards 2 and 3
are rejected directions and must not be mixed into the final identity. This
approval unlocks Design Identity/System finalization and wireframe artifacts;
it does not authorize production implementation.
