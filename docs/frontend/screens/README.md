# Screen Contracts

Store persistent screen contracts here. The P10 author and reviewer read the
approved related flows and wireframes and keep the screen contract aligned with
them. They report any upstream conflict instead of editing those earlier
artifacts; correction returns to the designated upstream author and its
independent re-review loop. P06 production UI-library source and its showcase
intentionally precede these contracts.

Every real page or meaningful screen gets a route-catalog record that resolves
to a screen contract. Store one contract per unique route template and one
delta contract per structural, interaction, state, responsive, or
accessibility exception. Shared shell, navigation, search, overlay, or layout
contracts are separate supporting files. A route may reuse a template contract
only when its Product Surface record proves those properties are identical;
every route still maps its canonical content, states, journeys, wireframe
address, and production unit.

For D3, a write-scoped independent Screen Contract Author creates this package
and a separate read-only Contract Reviewer checks it and its cross-package
mappings.

Use this structure when applicable:

```md
# Screen Name

- Contract ID:
- Contract type: template / route exception / shared system
- Template ID:
- Covered Surface IDs or route-catalog query:
- Explicit exceptions:

## Purpose

## User Goals

## Primary Action

## Information Hierarchy

## Product And Content References

- Product Surface IDs and revision:
- Route And Template Catalog revision/hash:
- Messaging Contract and Identity revision:
- Canonical page-content IDs, paths, revisions, and hashes:
- Shared UI copy IDs:
- Required content depth and state-copy families:
- Unresolved content or source gaps:

## Layout

## Sections

## Components

- Registered production component IDs and source paths:
- UI-library fidelity-scene/catalog evidence:

## Interaction Inventory

- Element or region:
- Expected response:
- URL, state, request, event, feedback, or recovery behavior:
- Keyboard behavior:
- Evidence:

## Data Sources And Trust Boundaries

## States

- loading
- normal
- empty
- error
- disabled
- overflow
- partial data

## Responsive Behavior

- Narrow mobile below 640px:
- Mobile-wide or small tablet at 640px and above:
- Tablet at 768px and above:
- Desktop at 1024px and above:
- Large desktop at 1280px and above:
- Wide desktop at 1536px and above:
- Additional project-specific viewports:

## Accessibility Requirements

## Copy And Microcopy Requirements

## Visual Emphasis

## Related Screens

## Related Flows And Wireframes

## HTML Wireframe Contract

- Stable page/screen address:
- Stable state addresses or fixtures:
- Fidelity: W0 / W1 clickable wireflow / W2 / owner-approved W3
- Demonstrated interaction intent:
- Behavior deferred to production:
- State-matrix reference:
- Viewport evidence:
- Independent First-Use Review evidence:
- Independent Wireframe Rendered Visual QA evidence:

## Wireframe Conformance Invariants

- Frozen structure and hierarchy:
- Frozen navigation and journey endpoints:
- Frozen interactions, states, feedback, focus, and recovery:
- Frozen responsive transformations:
- Frozen accessibility relationships:
- Visual properties intentionally left to the Design System:
- Production route/component mapping:
- Conformance verification:

## Artifact-Phase Rubric

## Acceptance Criteria

- Observable behavior:
- Interaction coverage:
- Links and navigation coverage:
- Messaging System pass:
- Rubric Review:
- Required states:
- Independent Contract Review:
- Wireframe conformance evidence:
- Automated checks:
```
