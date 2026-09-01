# Docs Portal V1 Wireframe

## Desktop View

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Brand: crypt docs portal                    [Search input trigger]  │
├────────────────┬────────────────────────────────────────────────────┤
│ Side nav       │ Hero: product explanation + primary actions        │
│ - Overview     │ ┌────────────────────────┐ ┌─────────────────────┐ │
│ - Architecture │ │ copy and actions       │ │ lo-fi desk visual   │ │
│ - Pipeline     │ └────────────────────────┘ └─────────────────────┘ │
│ - Research     │ Quick links row                                     │
│ - Backtester   │ Architecture map                                    │
│ - Strategies   │ Pipeline stepper                                    │
│ - Archive      │ Module tabs                                         │
│ - Live         │ Curated page cards                                  │
│ - Risks        │                                                     │
│ - Runbooks     │                                                     │
└────────────────┴────────────────────────────────────────────────────┘
```

## Mobile View

```text
┌──────────────────────────────┐
│ Brand                        │
│ [Search trigger]             │
├──────────────────────────────┤
│ Navigation card              │
├──────────────────────────────┤
│ Hero copy                    │
│ Lo-fi desk visual            │
│ Quick links stacked/grid     │
│ Architecture map stacked     │
│ Pipeline stepper stacked     │
│ Module tabs stacked          │
│ Curated page cards           │
└──────────────────────────────┘
```

## Docs Page View

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Shared header and search                                            │
├────────────────┬────────────────────────────────────────────────────┤
│ Shared nav     │ Back link                                           │
│ active page    │ Page header: label, title, icon, summary            │
│ highlighted    │ Content sections                                    │
│                │ Page-specific interactive module when applicable    │
│                │ Related page cards                                  │
└────────────────┴────────────────────────────────────────────────────┘
```

## States

- Search closed: header trigger visible.
- Search open: centered dialog with input and results.
- Search empty: explicit no-match message and suggested terms.
- Architecture map: selected node changes detail panel and related link.
- Pipeline stepper: selected step changes detail panel and related link.
- Module tabs: selected tab changes body and tags.

## Approval

- Revision: 1
- Status: approved by owner implementation approval on 2026-09-01.
- Implementation scope unlocked: local Next.js docs portal V1.
