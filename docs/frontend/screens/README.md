# Screen Contracts

Store persistent screen contracts here. Before changing UI, read or update the
related flows and wireframes, then keep the screen contract
aligned before implementation.

Each real page or meaningful screen gets its own screen contract. Shared shell
or layout contracts describe global structure and are linked from page-level
contracts.
For D3 multi-page or multi-screen work, store each page or meaningful screen in
its own contract file. Shared shell, navigation, search, overlay, or layout
contracts are separate supporting files and link back to page-level contracts.

Use this structure when applicable:

```md
# Screen Name

## Purpose

## User Goals

## Primary Action

## Information Hierarchy

## Messaging Contract

- Starting user state:
- Intended leaving state:
- Main idea:
- Required proof:
- Objections:
- Natural action:
- Generic-copy risks:

## Messaging System Pass

- Messaging Identity:
- Page or screen trajectory:
- Text hierarchy:
- Placement and density:
- Proof:
- Objections:
- Microcopy:
- Specificity risks:

## Layout

## Sections

## Components

## Content And Capability Contract

- Source corpus, data source, asset set, or capability inventory:
- Required coverage:
- Required depth:
- Source-of-truth proof:
- Coverage evidence:

## Discovery Contract

- Search, filter, navigation, recommendation, map, index, or catalog surfaces:
- Corpus and indexed fields:
- Body-content coverage:
- Ranking, grouping, sorting, or result explanation:
- Empty and zero-result behavior:
- Representative queries or discovery tasks:
- Coverage evidence:

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
- Fidelity: W0 / W1 / W2 / owner-approved W3
- Demonstrated interaction intent:
- Behavior deferred to production:
- State-matrix reference:
- Viewport evidence:
- Independent First-Use Review evidence:

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
- Content/capability coverage:
- Discovery/search coverage:
- Interaction coverage:
- Links and navigation coverage:
- Messaging System pass:
- Rubric Review:
- Required states:
- Rendered evidence:
- Independent Contract Review:
- Wireframe conformance evidence:
- Automated checks:
```
