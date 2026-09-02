# Documentation Portal Product Direction

- Date: 2026-09-02
- Status: approved
- Affected artifact revisions: Product Surface Model revision 1, Messaging
  revision 1, Design Identity revision 1, Design System seed revision 1

## Context

The repository has no active frontend application. The owner requested a large
documentation portal that explains how the `crypt` codebase works, aimed at a
developer-crypto trader.

## Decision

Build `crypt docs` as a curated Next.js and Tailwind documentation portal. The
portal content will be authored directly in source files. Repository Markdown
documents may inform the content, but the portal will not render Markdown files
from the repository as pages.

The first release scope includes Overview, Architecture, Backtester,
Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, and
Glossary. Navigation must support both guided learning and architecture
reference use. Search must cover full curated page content through a header
search and `Cmd/Ctrl+K` command palette.

The portal must not show command execution results, live balances, current
positions, current production state, or runtime backtest/live metrics. Live
Execution may explain architecture and operational guarantees only.

The visual direction is playful abstract lo-fi in pastel tones, with dark and
light themes, abstract mascots, diagrams, breadcrumbs, left navigation, desktop
page TOC, next-reading blocks, and maturity/risk labels.

Owner approved Product Surface revision 1 with "апрув" on 2026-09-02.

## Consequences

The implementation needs authored content structures rather than an MDX or CMS
pipeline. Search indexing must use the curated source-authored content. Page
contracts must preserve risk boundaries around live money, OKX execution,
configuration, and no-look-ahead bias.

Because this is a D3 frontend surface, production code must wait for Product
Surface Approval, Visual Direction Approval, wireframes, screen contracts,
independent contract review, and Final Implementation Approval unless the owner
grants scoped waivers using `FRONTEND WAIVER:`.

## Validation Or Revisit Trigger

Revisit if the owner asks for Markdown rendering, CMS, runtime dashboards,
performance/result displays, a different audience, or a different visual
direction.
