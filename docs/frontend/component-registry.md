# Component Registry

Record meaningful reusable frontend components here.

Before creating a new component, check in order:

1. Existing project component.
2. Existing UI-library primitive.
3. Composition of existing primitives.
4. New component or primitive.

Use this format:

```md
## Component Name

- Location:
- Purpose:
- Built from:
- Why existing primitives were insufficient:
- Usage constraints:
- States:
- Accessibility behavior:
- Responsive behavior:
- Related screens:
- Validation evidence:
```

## PortalShell

- Location: `components/portal-shell.tsx`
- Purpose: shared header, search entry, and docs navigation layout.
- Built from: Next.js `Link`, local `SearchDialog`, curated page metadata.
- Why existing primitives were insufficient: no frontend primitives existed.
- Usage constraints: use for all portal pages.
- States: active navigation item.
- Accessibility behavior: labeled navigation, keyboard-focusable links and search trigger.
- Responsive behavior: stacked mobile layout, sticky side navigation on desktop.
- Related screens: home and all curated docs pages.
- Validation evidence: see frontend review records.

## SearchDialog

- Location: `components/search-dialog.tsx`
- Purpose: full-content local search over curated portal pages.
- Built from: React state, curated content index, Next.js links.
- Why existing primitives were insufficient: no search primitive existed.
- Usage constraints: search only indexes manually curated page content.
- States: closed, open, default suggestions, matching results, empty result.
- Accessibility behavior: dialog role, modal flag, labeled close button, autofocus input.
- Responsive behavior: centered modal with mobile-safe width and scrollable results.
- Related screens: all portal pages.
- Validation evidence: see frontend review records.

## ArchitectureMap

- Location: `components/architecture-map.tsx`
- Purpose: clickable subsystem map.
- Built from: curated architecture node data and local card controls.
- Why existing primitives were insufficient: product-specific interactive explanation.
- Usage constraints: use where system overview or architecture context is needed.
- States: selected subsystem.
- Accessibility behavior: buttons for node selection and explicit related link.
- Responsive behavior: one-column mobile, multi-column desktop.
- Related screens: home, Architecture page.
- Validation evidence: see frontend review records.

## PipelineStepper

- Location: `components/pipeline-stepper.tsx`
- Purpose: explain the strategy research-to-runtime pipeline.
- Built from: curated pipeline step data.
- Why existing primitives were insufficient: product-specific interaction.
- Usage constraints: use where process sequence matters.
- States: selected step.
- Accessibility behavior: step buttons and related-page link.
- Responsive behavior: stacked mobile, side-stepper desktop.
- Related screens: home, Pipeline page.
- Validation evidence: see frontend review records.

## ModuleTabs

- Location: `components/module-tabs.tsx`
- Purpose: compare research, runtime, and docs loops.
- Built from: curated tab data.
- Why existing primitives were insufficient: product-specific module framing.
- Usage constraints: use for high-level orientation.
- States: selected tab.
- Accessibility behavior: button tabs with visible focus.
- Responsive behavior: stacked or row controls depending on viewport.
- Related screens: home, Overview page.
- Validation evidence: see frontend review records.
