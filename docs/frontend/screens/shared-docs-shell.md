# Shared Documentation Shell

## Purpose And Layout

Provide consistent global orientation across all 13 pages: skip link, header
with `crypt` and Search, left section navigation, measured article column,
contextual table of contents, previous/next navigation, and mobile drawers.

## Components And Interactions

- Logo/Home link; Search button and `/`, `Ctrl/Cmd+K` shortcuts.
- Sidebar page links with current-page state; mobile navigation open/close.
- Right contents heading anchors; previous/next route links.
- Code copy, tabs, disclosures, related-page cards, semantic callouts.
- Expected route, focus, copied, selected, expanded, and error feedback follows
  Product Surface revision 1 and Design System revision 1.

## States

- normal, active route/heading, search open/results/zero/error, mobile drawers,
  copy success/failure, loading index, overflow code/table, partial article build.
- Partial or stale source manifests fail the build rather than publishing an
  unlabeled incomplete page.

## Responsive Behavior

- `<640`: single column, compact header, separate navigation/contents drawers.
- `640–767`: wide mobile article with optional two-column small cards.
- `768–1023`: compact persistent sidebar when article measure survives.
- `1024–1279`: full sidebar; contents becomes inline or collapsible.
- `1280–1535`: three-column docs shell.
- `>=1536`: larger atmospheric gutters; article measure stays capped.

## Accessibility

Semantic landmarks, one H1, ordered headings, skip link, visible focus, dialog
focus trap/restore, keyboard drawers, named icon controls, accessible diagrams,
AA contrast, reduced motion, and minimum `44px` touch targets.

## Acceptance

Every link, anchor, shortcut, drawer, search state, code control, tab, disclosure,
and previous/next target is inventoried and independently exercised.
