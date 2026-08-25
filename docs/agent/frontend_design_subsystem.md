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

For substantial frontend work, the agent must not proceed to production
implementation when frontend memory is not established. This is a state-based
gate, not only a new-site gate. It applies to the first serious frontend task in
the repository even when the user asks for something that sounds implementable
immediately.

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

If neither condition is true, the correct output is not implementation. The
correct output is:

1. repository frontend discovery;
2. product knowledge discovery;
3. a short statement that frontend memory is not established;
4. the next adaptive design onboarding interview round with examples for
   abstract questions;
5. no production frontend implementation yet.

The owner answering the first onboarding round does not mean frontend memory is
established. After the first answer, the agent must synthesize what was learned,
identify remaining uncertainty, continue the adaptive interview as needed,
draft or update the Product Surface Model, draft preliminary Design Identity,
perform visual exploration when the task needs visual direction, collect owner
feedback, finalize Design Identity and Design System, and only then implement.

First-time frontend onboarding is deep, not short. Do not describe it as quick,
brief, lightweight, or a short round. The agent should set expectations that
this is a multi-step discovery process because the repository has no established
frontend memory yet.

The full first-time onboarding interview is 30 questions total, delivered as 6
adaptive rounds of 5 questions. Do not ask all 30 questions at once. Do not stop
after one round unless the owner explicitly waives the rest of onboarding. The
agent decides the exact 5 questions in each round dynamically from repository
context, product knowledge, previous answers, and remaining uncertainty. There
is no fixed questionnaire.

Do not promise implementation immediately after the owner's next answer while
frontend memory is still not established. The next owner answer can advance the
process, but it does not automatically unlock implementation. Promise the next
onboarding step, synthesis, visual exploration, or persistence step instead.

Agents must not fill Design Identity, Visual Direction Boards, selected or
rejected references, or final design-system choices from their own taste alone.
Those artifacts require owner answers, inferred existing product evidence, or
explicit owner approval.

After the owner answers enough interview rounds to support a preliminary
identity, the next gate is visual exploration. For first-time frontend
onboarding or any substantial task that needs visual direction, generate the
default five Visual Direction Boards before finalizing Design Identity, unless
the owner explicitly skips or narrows that stage.

Visual Direction Boards are direction studies for owner feedback. They are not
production assets. Do not replace the five boards with one hero image, one
illustration, one mockup, or an asset intended directly for the site/app. After
presenting boards, stop for owner selection, mixing, rejection, or correction
before finalizing Design Identity and implementing.

Do not convert a test of this methodology into a production frontend artifact.
When the owner appears to be testing agent behavior, explain the gated next step
and wait for the required input instead of silently implementing.

For a new site, app, or major frontend surface, implementation technology is
also a gated decision. If the existing repository does not clearly establish the
frontend stack, ask whether the owner wants a lightweight static implementation,
a framework-based app, specific UI libraries, or another stack preference before
choosing. Do not assume the absence of a framework requirement means that heavy
frameworks or UI libraries are unwanted.

## First-Use Discovery

Before establishing new frontend rules for a project, inspect the repository and
infer existing decisions without asking the owner by default.

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
local stack without asking. Ask only when evidence shows a meaningful unresolved
choice, such as competing active UI libraries, an unfinished migration, strong
legacy/current conflicts, or genuinely ambiguous brand direction.

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

Do not ask the owner to repeat product information that already exists in the
repository. First search for existing product knowledge sources, such as:

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
existing knowledge, and owner answers. Do not hardcode a universal set of pages
or features.

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
remains for the requested scope. The frontend must not merely demonstrate the
chosen visual direction. It must represent a complete useful product surface
appropriate to the requested scope.

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
Do not use a fixed questionnaire or a fixed number of questions. Generate
questions dynamically for the product and adapt follow-ups to the owner's
answers.

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

Ask design onboarding questions in the 6-round / 5-question protocol defined in
Non-Negotiable Gates. Each round should cover the highest-leverage remaining
unknowns across product purpose, audience, desired surface, visual direction,
stack constraints, references, and success criteria. The first round must be 5
questions, not a token three-question preflight. After each owner answer,
synthesize what was learned, identify the remaining uncertainty, and ask the
next 5-question round. Do not dump every possible question at once. Later rounds
must depend on earlier answers so the agent can build a more accurate product
model.

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

The boards are not five finished versions of the same website or screen. They
are visual-language studies combining, as relevant:

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
relevant. Do not hardcode named styles as required directions.

The owner may select one direction, combine several, prefer individual
properties, reject properties, reject every board, or describe what is missing.
Treat feedback as additional design information. If all directions are rejected,
determine why, revise the interpretation, and generate another exploration when
useful.

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
AI-generated interface. Do not randomize colors, radii, typography, or layout
for novelty.

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
traits. They should appear consistently enough to create recognition without
becoming decorative gimmicks.

Also record what the product must not become. Negative constraints are valuable
because they counter common AI-generated defaults.

Examples are allowed in local identity files, but examples must not become
global defaults.

## Reference Decomposition

When users provide references, decompose them into properties instead of copying
templates.

For each reference, record:

- what is liked;
- what is disliked;
- what should not be copied;
- which product-specific principle the reference supports.

References are signals, not permission to clone another product.

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

Reuse established values. Do not invent one-off visual values for every task.

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

Creating a new primitive is the last option. Record meaningful reusable
components, purpose, location, and usage constraints in
`docs/frontend/component-registry.md`.

## UX Flows

Represent navigation relationships and complex user flows separately from
visual design. Markdown and Mermaid are sufficient for many cases.

Flows answer where the user can go, under what conditions, and how. Store them
under `docs/frontend/flows/`.

## Screen Contracts

Meaningful screens should have persistent Markdown contracts under
`docs/frontend/screens/`. They serve as agent-readable UX specs, wireframes, and
memory.

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

Before materially changing a screen, update the contract when necessary, then
implement.

## Significant UI Changes

For substantial new UI, do not automatically implement the first idea. Compare
candidate approaches against Design Identity, then select, combine, or refine.

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

Only after the needed design work should agents modify production code.
Implementation must respect:

- Frontend Context;
- Design Identity;
- positive and negative visual references;
- Design System;
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
New screen -> UX -> screen contract -> exploration -> implement -> inspect
Major redesign -> deep design process -> implement -> full review
```

Avoid bureaucracy for its own sake.

## Render, Inspect, Fix

A frontend task is not complete merely because code compiles, lint passes, or
tests succeed.

Run the application, render the real UI, inspect it with available browser,
screenshot, multimodal, or equivalent capability, fix problems, and inspect
again when needed.

Rendered QA must cover viewport sizes that are meaningful for the layout, not
only one desktop and one mobile width. At minimum for a new site/app, check:

- narrow mobile;
- wide mobile or small tablet;
- tablet or narrow desktop;
- normal desktop;
- large desktop or wide monitor when content has a max-width, sidebar, rail,
  canvas, dashboard grid, or hero composition.

Record the checked viewport sizes in the review notes when the review is
durable.

Rendered QA must also exercise every added interactive zone, not just verify
that it is visible. Click or activate every added button, link, tab, menu,
toggle, form control, carousel control, and other focusable/clickable element.
Verify the resulting state, navigation target, URL/hash, enabled/disabled
behavior, focus state, error state, and console output as relevant.

## Responsive Design Pass

Responsive design is not layout survival. A page that has no overflow,
overlap, or broken buttons can still fail responsive design.

For meaningful responsive work, run a Responsive Design Pass. Each important
viewport should feel like an intentionally designed composition of the same
product, not a desktop layout that CSS managed to compress.

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

Use the existing structured visual critique approach. Do not try to reduce
visual quality to a numeric formula.

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

Do not assume the most obvious technical substitution is correct. Ask which
interaction or layout pattern best preserves the function of the original
element at this viewport.

Visual QA after implementation must inspect each important viewport as its own
composition, not only as a regression check against desktop.

## Visual Review Protocol

Use an explicit rubric instead of asking whether the result "looks good".
Evaluate relevant dimensions:

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
- responsive transformations are justified by function, not only by available
  CSS mechanics;
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

One final review question should be: is this merely a clean interface, or does
it clearly belong to this particular product?

If inadequate, fix and review again.

## Anti-AI-Slop Rules

Do not use common AI-generated UI defaults without product-specific
justification:

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

These are not absolute bans. A technique is allowed when it follows from the
Design Identity and serves a clear purpose.

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
DEEP DESIGN INTERVIEW
        |
ABSTRACT IDENTITY QUESTIONS WITH EXAMPLES
        |
PRELIMINARY DESIGN IDENTITY
        |
GENERATE 5 VISUAL DIRECTION BOARDS
        |
USER SELECTS / MIXES / REJECTS
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
LOAD ONLY RELEVANT FRONTEND CONTEXT
        |
LOAD PRODUCT SURFACE MODEL WHEN SCOPE REQUIRES
        |
UPDATE UX / SCREEN MODEL IF NECESSARY
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
DONE
```

The subsystem gives agents a design process, long-term design memory, explicit
product identity, positive and negative visual anchors, reusable design rules,
component awareness, persistent reasoning, rendered inspection, and a feedback
loop for correcting visual problems.
