# Frontend Design Subsystem

This document defines the portable frontend design workflow for AI agents in
this repository. It is framework-agnostic: use the browser, screenshot,
multimodal, image-generation, component-library, and test tools available in the
current environment, but do not make the process depend on one vendor, UI
library, framework, or agent harness.

The subsystem exists to preserve visual quality, product-specific identity,
cross-session consistency, and the reasoning behind frontend decisions.

## Process Depth

Meaningful frontend work must separate design from implementation. Use this
lifecycle, with depth proportional to risk and scope:

```text
DESIGN
  |
IMPLEMENT
  |
RENDER
  |
INSPECT
  |
FIX
```

Classify frontend tasks before acting:

- visual bug;
- small UI modification;
- new component;
- new section;
- new screen;
- major redesign;
- new frontend/product.

Tiny changes should not trigger a full ceremony. New screens, major redesigns,
or a new frontend/product should.

For substantial new frontend work, there are three separate final questions:

- Functional QA: does it work?
- Visual QA: does it look and feel right, including every important viewport?
- Product Completeness Review: is there enough product surface for the
  requested scope?

One check does not replace another.

## Non-Negotiable Gates

For substantial frontend work, production implementation starts from established
frontend memory. This is a state-based gate, not only a new-site gate. It
applies to the first serious frontend task in the repository even when the user
asks for something that sounds implementable immediately.

Frontend memory is not established when any of the durable foundations needed
for the task are still placeholders, for example:

- `docs/frontend/product-surface-model.md` is `Status: not established`;
- `docs/frontend/design-identity.md` is `Status: not established`;
- `docs/frontend/design-system.md` is `Status: not established`;
- visual references are absent for a task that needs visual direction;
- relevant screen contracts or design decisions are missing for a task that
  needs them.

The agent may proceed only when one of these is true:

- the owner explicitly waives design onboarding for this task;
- existing frontend memory already contains enough project-specific product
  surface, identity, visual references, design-system rules, and screen
  contracts to support the change.

If neither condition is true, the phase output is:

1. repository frontend discovery;
2. product knowledge discovery;
3. a short statement that frontend memory is not established;
4. the next adaptive design onboarding interview round with examples for
   abstract questions;
5. a clear statement of which gate or artifact unlocks the next phase.

The owner answering the first onboarding round does not mean frontend memory is
established. After the first answer, the agent must synthesize what was learned,
identify remaining uncertainty, continue the adaptive interview as needed,
draft or update the Product Surface Model, draft preliminary Design Identity,
perform visual exploration when the task needs visual direction, collect owner
feedback, finalize Design Identity and Design System, and only then implement.

First-time frontend onboarding is a deep multi-step discovery process because
the repository has no established frontend memory yet. Set that expectation
before asking the first round.

The first-time onboarding interview asks at least 30 questions, delivered as
adaptive rounds of 5 questions. After question 30, run an Uncertainty Check:
continue with additional 5-question rounds while material product, stack,
scope, visual, content, interaction, accessibility, or success-criteria
decisions remain unresolved. The agent decides each round dynamically from
repository context, product knowledge, previous answers, and remaining
uncertainty. There is no fixed questionnaire.

While frontend memory is still not established, describe the next onboarding,
synthesis, visual exploration, or persistence step. The next owner answer can
advance the process, and implementation unlocks only after the required gates
and artifacts are complete.

Design Identity, Visual Direction Boards, selected and rejected references, and
final design-system choices are grounded in owner answers, inferred existing
product evidence, or explicit owner approval.

After the owner answers enough interview rounds to support a preliminary
identity, the next gate is visual exploration. For first-time frontend
onboarding or any substantial task that needs visual direction, generate the
default five Visual Direction Boards before finalizing Design Identity, unless
the owner explicitly skips or narrows that stage.

Each Visual Direction Board is a rendered visual artifact plus short notes. A
complete board shows a concrete direction study for composition, typography,
density, geometry, surfaces, color, representative UI fragments, imagery or
illustration approach, and signature ideas. After presenting boards, the next
phase is owner selection, mixing, rejection, or correction.

When the owner appears to be testing agent behavior, treat the result as a
methodology test: explain the gated next step and wait for the required input.

For a new site, app, or major frontend surface, implementation technology is
also a gated decision. If the existing repository does not clearly establish the
frontend stack, ask whether the owner wants a lightweight static implementation,
a framework-based app, specific UI libraries, or another stack preference before
choosing. Missing framework requirements are treated as unresolved stack input,
not as a preference for or against heavy frameworks or UI libraries.

## Owner Decision Gates

Some frontend phases require explicit owner feedback. Treat these states as
distinct:

```text
Interview completed
!=
Onboarding completed
!=
Design approved
!=
Ready for implementation
```

Completing the verbal interview means only that the interview stage is done.
It does not complete onboarding, approve design direction, approve scope, or
authorize implementation. Onboarding is complete only after the required owner
decision gates have passed, durable design memory has been updated, and the
task is explicitly ready for the next phase.

Minimum owner gates and completion criteria:

- Stack Gate: for a new site or application, record the owner-confirmed stack
  when the repository does not already define it.
- Product Surface Gate: for a complete site or product surface, draft the
  Product Surface Model, information architecture, page inventory, journeys,
  content, and functionality, then get owner confirmation before screen design
  or implementation.
- Visual Direction Gate: after generating rendered Visual Direction Boards,
  collect owner feedback. The feedback identifies the selected direction,
  elements to mix, rejected properties, or the need for another exploration
  round.
- Scope/Completeness Gate: for production-ready, complete-site, or many-page
  requests, record the first implementation scope: pages, journeys, content,
  and functionality that are in scope.
- Final Pre-Implementation Gate: before large implementation, show the selected
  stack, product surface, visual direction, pages or screens, and
  implementation plan. Implementation begins after owner confirmation or
  explicit permission to continue.
- UI Contract Gate: every UI edit starts from the current Mermaid flow
  contracts and HTML/CSS/JS wireframes. Create or update them first, render the
  wireframes, and use owner approval as the start signal for production UI code.

Required owner gates pass through explicit owner confirmation, a documented
owner waiver, or existing canonical project evidence that already decides the
gate.

## Phase Handoff Strategy

Large frontend tasks are split into phases rather than one continuous pass in
an overloaded context. The agent should determine the phases
from the requested scope, but common phase boundaries include:

- product understanding and onboarding;
- Product Surface Model and information architecture;
- Design Identity and Visual Exploration;
- Design System, Mermaid flows, HTML wireframes, and screen contracts;
- implementation work units;
- responsive, functional, visual, and product completeness QA.

Use phase handoff for large frontend tasks, including:

- a new production-ready site or application;
- many pages or screens in one request;
- first frontend onboarding, design identity, and implementation in one task;
- major redesigns;
- frontend plus backend surface work in one task;
- any task where onboarding, product model, design, implementation, and QA are
  all in scope;
- any situation where the agent expects active context to become too large.

Small work keeps the proportional workflow. Tiny visual fixes, small UI
modifications, and narrow component changes use phase handoff only when context
is already overloaded.

At the end of each phase with a next phase, new session, or subagent, create a
durable handoff artifact. Fully complete frontend tasks end with canonical
files and reviews rather than a new handoff.

The handoff must record:

- which phase was completed;
- what was done;
- decisions made;
- canonical files created or updated;
- open questions;
- goal of the next phase;
- files and instruction documents the next phase must read;
- files and instruction documents that are optional or deferred for the next
  phase;
- important constraints, risks, and context;
- what is the source of truth going forward.

Canonical files are the source of truth after each phase. Every important
decision, constraint, result, product fact, design fact, or implementation
contract that must survive the phase is persisted to a canonical project file,
such as product documentation,
`docs/frontend/product-surface-model.md`, `docs/frontend/design-identity.md`,
`docs/frontend/design-system.md`, Mermaid flows, HTML wireframes, screen
contracts, component registry, design decisions, `docs/state/current.yml`,
`CHANGELOG.md`, or another appropriate durable document.

Handoff files are temporary technical artifacts. The next phase, subagent, or
fresh session reads the handoff first, then the required files listed inside it.
After durable information is moved or confirmed in canonical files, delete the
consumed handoff file. Before ending any large frontend task, verify that no
temporary frontend handoff files remain. Keeping handoff history for audit or
debugging requires a separate documented decision.

When choosing how to continue after a phase, use this priority:

1. durable phase output and canonical files;
2. isolated subagent, if supported and reliable;
3. fresh user session handoff;
4. continue in the current session only if context remains manageable.

If subagents are available, the agent knows how to use them, the current tools
and instructions support them, and the agent can reliably control their context,
prefer assigning the next phase to an isolated subagent. This is an optional
optimization, not a dependency of the subsystem.

The subagent prompt must include:

- output of the current phase;
- path to the handoff artifact;
- next phase goal;
- required instruction files for that phase;
- relevant project state files;
- scoped instructions for which previous-phase methodology is relevant;
- requirement to create the same durable handoff if another phase remains;
- requirement to delete the consumed handoff after durable information is
  persisted to canonical files;
- requirement to either delegate the next phase to a new isolated subagent when
  phases remain and subagents are available, or report completion to the owner.

If subagents are not available, not understood, not reliable, or not controllable
in the current environment, finish the current phase, write the handoff, and
tell the owner to open a new session with a short practical instruction such
as:

```text
Phase complete. Handoff saved at <path>. To avoid overloading context, open a
new session and write: Continue from <path> and perform the next phase using the
required instructions listed there.
```

The agent manages previous conversation by making canonical files the source of
truth, using fresh sessions, using harness compaction when available, or using
isolated subagents when available. Already loaded conversation history remains
physically present in the active context until the harness compacts or replaces
the context.

## First-Use Discovery

Before establishing new frontend rules for a project, inspect the repository and
infer existing decisions from local evidence first.

Identify:

- frontend framework;
- styling approach;
- UI libraries and local primitives;
- design tokens, CSS variables, themes, and dark/light behavior;
- typography;
- icon libraries;
- form, chart, table, animation, and visualization libraries;
- responsive conventions;
- layout patterns;
- assets and imagery;
- Storybook or similar component documentation;
- established screen and component patterns;
- apparent legacy areas, migrations, and inconsistencies.

Stable, actively used choices are intentional by default. Continue an obvious
local stack. Ask when evidence shows a meaningful unresolved choice, such as
competing active UI libraries, an unfinished migration, strong legacy/current
conflicts, or genuinely ambiguous brand direction.

```text
INFER
  |
ASK ONLY WHAT CANNOT REASONABLY BE INFERRED
  |
PERSIST
```

Persist inferred decisions in `docs/frontend/context.md`.

## Product Knowledge Discovery

For a new site/app, major redesign, or substantial new product surface, the
agent must understand the product before deciding what screens and content
belong in the frontend.

First search for existing product knowledge sources before asking the owner to
repeat product information, such as:

- `product.md` or `PRODUCT.md`;
- `README.md`;
- project documentation;
- requirements and specifications;
- project knowledge directories;
- task context and current state docs;
- any other obvious source of general product information.

If one canonical product source exists, use it as the primary source. If several
sources exist, identify the most authoritative and current one, use the rest as
supporting context, and note contradictions. Ask the owner only about important
product information that is missing, ambiguous, or contradicted.

Use the same rule as frontend discovery:

```text
DISCOVER
  |
INFER FROM EXISTING PRODUCT KNOWLEDGE
  |
ASK ONLY UNRESOLVED IMPORTANT QUESTIONS
  |
PERSIST
```

Persist durable product-surface understanding in
`docs/frontend/product-surface-model.md`.

## Product Surface Model

Before designing screens for a new site/app or substantial product surface,
build a Product Surface Model. The model answers what the user must be able to
do with the frontend, not only which pages the owner named.

Derive the model from the actual product, requested scope, stage of the product,
existing knowledge, and owner answers. Use product-specific evidence for pages
and features.

Reason in this order:

```text
Product knowledge
  |
User capabilities and goals
  |
Required content and features
  |
User journeys
  |
Information architecture
  |
Pages or screens
  |
Sections and components
```

Completeness comes before decoration. Before treating a frontend as designed,
mentally remove the CSS and ask whether a complete useful product surface still
remains for the requested scope. The frontend represents a complete useful
product surface appropriate to the requested scope, with visual direction
serving that surface.

This does not mean every MVP must become large. Completeness is proportional to
the explicit request, product knowledge, user goals, and product stage.

## Product Completeness Review

For a new site/app, major redesign, or substantial product surface, run Product
Completeness Review separately from Functional QA and Visual QA.

Check whether:

- primary user goals are covered;
- important secondary goals are covered when they are in scope;
- navigation and information architecture are complete enough;
- necessary content is present, not only decorative or placeholder copy;
- required core interactions exist;
- important user journeys have sensible endpoints;
- obvious placeholder or demo-only surfaces have been removed or explicitly
  marked as out of scope;
- required loading, empty, error, disabled, overflow, and partial-data states
  exist where relevant;
- the frontend is not merely a demonstration of the visual direction.

If the answer is incomplete for the requested scope, fix the product surface,
not only the styling.

## Design Onboarding

When the project lacks a sufficiently established design identity and the task
is significant, run a deep one-time design onboarding before implementation.
Generate questions dynamically for the product and adapt follow-ups to the
owner's answers.

Understand:

- product purpose and domain;
- target audience and expertise;
- usage frequency and context;
- product character and desired emotional response;
- visual personality;
- information density;
- calm versus energetic, restrained versus expressive, conventional versus
  experimental, utilitarian versus premium, human versus clinical;
- desired and undesired associations;
- visual references and what is liked or disliked in them;
- platform and device priorities;
- content and data characteristics;
- motion, imagery, illustration, and iconography direction;
- brand constraints;
- accessibility expectations.

When useful, offer several meaningfully different suggested answers plus a free
custom option. The suggestions are conveniences, not restrictions.

Abstract visual or emotional questions must include examples. The owner should
not need design expertise to participate.

Ask design onboarding questions in the minimum-30 / 5-question-round protocol
defined in Non-Negotiable Gates. Each round covers the highest-leverage
remaining unknowns across product purpose, audience, desired surface, visual
direction, stack constraints, references, and success criteria. After each
owner answer, synthesize what was learned, identify remaining uncertainty, and
ask the next 5-question round. Later rounds depend on earlier answers so the
agent can build a more accurate product model.

For a new site/app, include implementation-stack preferences in an early round
when the repository does not already decide them. Clarify whether the owner
wants static HTML/CSS/JS, a frontend framework, a design-system/UI library,
charts/tables/forms libraries, animation libraries, or constraints such as
deployment target and maintainability expectations.

## Preliminary Identity

After the verbal interview, synthesize a preliminary Design Identity. It is not
final; it is the input to visual exploration.

The preliminary identity should explain why this product should look and feel
the way it does. It can cover core feeling, personality, desired perception,
visual tension, associations, anti-associations, density, expression, utility
versus personality, and possible signature traits.

## Visual Exploration

Visual exploration is the final interactive onboarding stage. Use available
image-generation or visual tools when useful. The default is five Visual
Direction Boards.

Visual Direction Boards are rendered direction studies for choosing visual
language. Each board combines, as relevant:

- moodboard signals;
- miniature design-system exploration;
- representative UI fragments;
- typography study;
- color and surface study;
- geometry study;
- density and rhythm study;
- imagery or illustration direction;
- iconographic direction;
- one or more representative interface fragments.

All five boards must remain plausible interpretations of the owner's answers
and preliminary identity. Variation should be meaningful, not random. Explore
composition, typography, density, geometry, surfaces, hierarchy, navigation,
data presentation, imagery, emphasis, and signature ideas when those axes are
relevant. Named styles are optional labels, not required directions.

After generating boards, the next phase is owner feedback. The board package is
complete when the owner can compare five rendered directions and respond with a
selection, mix, rejection, or request for another iteration.

The owner may select one direction, combine several, prefer individual
properties, reject properties, reject every board, or describe what is missing.
Treat feedback as additional design information. If all directions are rejected,
determine why, revise the interpretation, and generate another exploration when
useful. Only after this feedback may the agent form Final Design Identity and
Design System.

Persist selected and rejected boards as project knowledge in
`docs/frontend/visual-references/interpretation.md`, separating positive and
negative signals. Store actual image assets under
`docs/frontend/visual-references/positive/` and
`docs/frontend/visual-references/negative/` when assets exist.

## Final Design Identity

After visual exploration and owner feedback, finalize
`docs/frontend/design-identity.md`.

It should include, as relevant:

- core feeling;
- personality;
- desired perception;
- visual tension;
- signature traits;
- anti-identity.

Future frontend decisions must be evaluated against this identity.

## Controlled Differentiation

Prevent unrelated projects from converging toward the same recognizable
AI-generated interface. Colors, radii, typography, and layout vary when the
product reasoning calls for it.

Differentiation must emerge from:

```text
Product
+
Audience
+
Domain
+
Existing Project
+
User Preferences
+
Design Identity
+
Visual Exploration
+
References
+
Brand Constraints
=
Visual Direction
```

The result should be distinctive for understandable reasons.

## Signature Traits And Anti-Identity

The final identity should establish a small number of recognizable signature
traits. They should appear consistently enough to create recognition while
remaining functional rather than decorative gimmicks.

Also record the product's anti-identity: the states and associations that would
break the intended identity.

Examples in local identity files stay local to that product.

## Reference Decomposition

When users provide references, decompose them into properties and product
principles.

For each reference, record:

- what is liked;
- what is disliked;
- what remains product-specific to the reference;
- which product-specific principle the reference supports.

References are signals for product-specific principles.

## Design System

After Design Identity is finalized, establish or update
`docs/frontend/design-system.md`.

```text
DESIGN IDENTITY
      |
DESIGN SYSTEM
      |
SCREENS + COMPONENTS
```

The Design System can define typography, spacing, colors, semantic color usage,
surfaces, borders, radii, shadows/elevation, density, iconography, motion,
forms, tables, charts, responsive principles, and semantic states.

Reuse established values across tasks.

UI libraries are part of frontend context and must be respected, but a UI
library is not the product Design System. The Design Identity and Design System
determine how primitives are composed, styled, and used.

## Component Reuse Protocol

Before creating a new component, reason in this order:

```text
Need UI
  |
Existing project component?
  |
Existing UI-library primitive?
  |
Can existing primitives be composed?
  |
Design a new component
  |
Implement
  |
Register
```

Record meaningful reusable components, purpose, location, and usage constraints in
`docs/frontend/component-registry.md`.

## UX Flows

Represent navigation relationships, user journeys, and state transitions
separately from visual design. Mermaid is the default format for user flows,
navigation maps, and state diagrams.

Flows answer where the user can go, under what conditions, how states change,
and where journeys end. Store them under `docs/frontend/flows/`. Every UI edit
starts by checking whether the relevant Mermaid flow contracts need updates.

## Wireframes

Wireframes are persistent screen contracts stored under
`docs/frontend/wireframes/`. They are lightweight HTML/CSS/JS artifacts that
render gray-box page layouts before production UI implementation.

Each page or meaningful screen gets a wireframe before production UI work. A
complete wireframe shows:

- page regions as labeled gray blocks;
- navigation, content, controls, images, data areas, and calls to action;
- block-level descriptions for complex elements;
- interaction notes for accordions, tabs, collapses, menus, forms, filters,
  search, animation, loading, empty, error, and partial-data behavior;
- responsive states for the important viewport widths;
- links to related Mermaid flows and screen contracts.

Wireframe artifacts are shown to the owner after Visual Direction Boards and
before Design System finalization, screen-detail work, or production UI code.
Owner feedback updates the wireframes until the layout, interactions, and
responsive structure are approved. Future UI edits start by reading and updating
the affected Mermaid flows and wireframes, then proceed to production code after
owner approval.

## Screen Contracts

Meaningful screens should have persistent Markdown contracts under
`docs/frontend/screens/`. They serve as agent-readable UX specs and memory
beside Mermaid flows and HTML/CSS/JS wireframes.

A screen contract should include, as relevant:

- purpose;
- user goals;
- primary action;
- information hierarchy;
- layout;
- sections;
- components;
- states: loading, normal, empty, error, disabled, overflow, partial data;
- responsive behavior;
- visual emphasis;
- related screens.
- related flows and wireframes.

Before changing a screen, update the related Mermaid flow, wireframe, and
screen contract, then implement after owner approval.

## Significant UI Changes

For substantial new UI, compare candidate approaches against Design Identity,
then select, combine, or refine.

Approaches should differ materially in hierarchy, composition, density,
interaction model, or another relevant design dimension, not merely color. The
number of alternatives is task-dependent.

## Design Decisions

Persist important frontend decisions under `docs/frontend/decisions/` in a
lightweight ADR-like form:

```md
# Decision Title

## Context

## Decision

## Consequences
```

Future agents must understand why the interface was designed this way, not only
what it does.

## Implementation Rules

Implementation starts after the needed design work. It respects:

- Frontend Context;
- Design Identity;
- positive and negative visual references;
- Design System;
- Mermaid Flows;
- HTML/CSS/JS Wireframes;
- Screen Contracts;
- Component Registry;
- Design Decisions;
- existing project conventions.

Before implementing a new site/app or major frontend surface, the selected
stack must be supported by one of:

- clear existing repository convention;
- explicit owner preference;
- a documented trade-off in `docs/frontend/decisions/`;
- an explicit owner waiver allowing the agent to choose.

Keep workflow proportional:

```text
Tiny change -> implement -> inspect
New component -> design -> implement states -> inspect
New screen -> UX -> Mermaid flow -> HTML wireframe -> owner approval -> implement -> inspect
Major redesign -> deep design process -> rendered boards -> wireframes -> owner approval -> implement -> full review
```

Keep the workflow proportional.

## Render, Inspect, Fix

Frontend completion includes compiled code, passing relevant checks, and a
rendered inspection of the real UI. Run the application, inspect it with
available browser, screenshot, multimodal, or equivalent capability, fix
problems, and inspect again when needed.

Rendered QA covers viewport sizes that are meaningful for the layout. At
minimum for a new site/app, check:

- narrow mobile;
- wide mobile or small tablet;
- tablet or narrow desktop;
- normal desktop;
- large desktop or wide monitor when content has a max-width, sidebar, rail,
  canvas, dashboard grid, or hero composition.

Record the checked viewport sizes in the review notes when the review is
durable.

Rendered QA also exercises every added interactive zone. Click or activate every
added button, link, tab, menu, toggle, form control, carousel control, and other
focusable/clickable element. Verify the resulting state, navigation target,
URL/hash, enabled/disabled behavior, focus state, error state, and console
output as relevant.

## Responsive Design Pass

Responsive design is intentional composition beyond layout survival. For
meaningful responsive work, run a Responsive Design Pass. Each important
viewport should feel like a designed composition of the same product.

Evaluate each important viewport for:

- visual hierarchy;
- intentional composition for that width;
- information density;
- navigation, header, and content proportions relative to the viewport;
- alignment and spacing rhythm;
- interaction model fit for the device;
- content priorities;
- whether anything should be hidden, collapsed, moved, combined, or changed;
- consistency with Design Identity.

Use the existing structured visual critique approach. Visual quality is captured
as a written critique rather than a numeric formula.

### Responsive Transformation Reasoning

When a layout or interaction changes substantially between viewports, treat that
transformation as a small design task.

Examples of substantial transformations include:

- sidebar to tabs, drawer, select, accordion, compact navigation, or another
  mobile information architecture;
- table to cards, rows, summaries, or a disclosure pattern;
- toolbar to menu, segmented controls, or contextual actions;
- multi-column layout to one column;
- persistent controls to collapsed controls.

Choose the interaction or layout pattern that best preserves the function of the
original element at this viewport.

Visual QA after implementation inspects each important viewport as its own
composition and records how it differs from desktop.

## Visual Review Protocol

Use an explicit rubric. Evaluate relevant dimensions:

- visual hierarchy;
- spacing rhythm;
- alignment;
- typography hierarchy;
- information density;
- composition;
- component consistency;
- color semantics;
- unnecessary decoration;
- excessive card nesting;
- responsive behavior;
- responsive composition quality at each important viewport;
- responsive transformations are justified by function and available CSS
  mechanics;
- loading, empty, error, disabled, overflow, and partial-data states;
- accessibility;
- consistency with Design Identity;
- use of Signature Traits;
- Anti-Identity violations;
- consistency with positive references;
- accidental resemblance to rejected references.
- all added interactive elements are exercised and their post-interaction state
  is checked;
- all added links and buttons either perform the intended action or are
  intentionally disabled/placeholder states documented in the screen contract.

Each meaningful viewport receives a short composition verdict covering
hierarchy, density, navigation fit, spacing, content priority, and interaction
model. The final review asks whether the UI clearly belongs to this product. If
the verdict is inadequate, fix and review again.

## Product-Specific UI Rules

Use visual choices that follow from the Design Identity and product function.
Common AI-default patterns need a product reason before use:

- excessive rounded cards;
- cards nested inside cards;
- meaningless gradients;
- decorative glow;
- giant headings inside application screens;
- pill-shaped elements everywhere;
- icons beside every label;
- arbitrary shadows;
- excessive whitespace;
- generic dashboard metric-card layouts;
- generic "Welcome back" sections;
- glassmorphism;
- unnecessary explanatory copy.

Techniques are acceptable when they follow from the Design Identity and serve a
clear purpose.

## Responsive Behavior And States

Responsive behavior and UI states are design work. For meaningful screens,
account for relevant device classes such as desktop, tablet, and mobile.

Components and screens should account for default, hover, focus, loading, empty,
error, disabled, overflow, and partial-data states when those states are
meaningful.

## Persistent Frontend Memory

The canonical persistent structure is:

```text
docs/frontend/
|-- context.md
|-- product-surface-model.md
|-- design-identity.md
|-- design-system.md
|-- component-registry.md
|-- visual-references/
|   |-- interpretation.md
|   |-- positive/
|   `-- negative/
|-- wireframes/
|-- flows/
|-- screens/
|-- decisions/
`-- reviews/
```

Separation of responsibilities matters more than this exact file layout:

- Context: what already exists;
- Product Surface Model: what the frontend must let users understand and do;
- Design Identity: what kind of product this is;
- Visual References: what that identity looks like in practice;
- Design System: technical visual rules;
- Flows: how UX connects;
- Wireframes: where screen regions, controls, content, interactions, animation,
  and responsive structure live before production UI code;
- Screens: how individual interfaces are structured;
- Components: reusable building blocks;
- Decisions: why important choices were made;
- Reviews: whether the real product still matches the intended design.

## Lifecycle Summary

First use:

```text
DISCOVER EXISTING FRONTEND
        |
INFER EXISTING DECISIONS
        |
DISCOVER EXISTING PRODUCT KNOWLEDGE
        |
BUILD PRODUCT SURFACE MODEL WHEN SCOPE REQUIRES
        |
DEEP DESIGN INTERVIEW: AT LEAST 30 QUESTIONS + UNCERTAINTY CHECK
        |
ABSTRACT IDENTITY QUESTIONS WITH EXAMPLES
        |
PRELIMINARY DESIGN IDENTITY
        |
GENERATE 5 RENDERED VISUAL DIRECTION BOARDS
        |
USER SELECTS / MIXES / REJECTS
        |
BUILD HTML/CSS/JS WIREFRAMES + MERMAID FLOWS
        |
OWNER APPROVES WIREFRAMES
        |
TARGETED FOLLOW-UP IF NECESSARY
        |
FINAL DESIGN IDENTITY
        |
SIGNATURE TRAITS + ANTI-IDENTITY
        |
DESIGN SYSTEM
        |
PERSIST TEXTUAL + VISUAL KNOWLEDGE
```

Every future frontend task:

```text
CLASSIFY CHANGE
        |
SPLIT LARGE FRONTEND TASKS INTO PHASES WHEN CONTEXT WOULD GROW TOO LARGE
        |
LOAD ONLY RELEVANT FRONTEND CONTEXT
        |
LOAD PRODUCT SURFACE MODEL WHEN SCOPE REQUIRES
        |
UPDATE UX / SCREEN MODEL IF NECESSARY
        |
UPDATE MERMAID FLOWS + HTML WIREFRAMES WHEN UI STRUCTURE CHANGES
        |
OWNER APPROVES UPDATED UI CONTRACTS
        |
EXPLORE ALTERNATIVES IF NECESSARY
        |
REUSE EXISTING COMPONENTS
        |
IMPLEMENT
        |
RENDER REAL INTERFACE
        |
RESPONSIVE DESIGN PASS WHEN SCOPE REQUIRES
        |
FUNCTIONAL QA
        |
VISUAL + IDENTITY REVIEW
        |
PRODUCT COMPLETENESS REVIEW WHEN SCOPE REQUIRES
        |
FIX UNTIL ACCEPTABLE
        |
UPDATE PERSISTENT FRONTEND KNOWLEDGE
        |
DELETE CONSUMED TEMPORARY HANDOFFS WHEN PHASED WORK IS COMPLETE
        |
DONE
```

The subsystem gives agents a design process, long-term design memory, explicit
product identity, positive and negative visual anchors, reusable design rules,
component awareness, persistent reasoning, rendered inspection, and a feedback
loop for correcting visual problems.
