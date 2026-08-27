# Public Docs Site Screen Contracts

Status: established for first implementation.

## Global Docs Shell

### Purpose

Provide a production-grade documentation shell for public readers.

### User Goals

- Search documentation.
- Move between curated sections quickly.
- Read source-backed docs with clear safety context.

### Information Hierarchy

1. Site identity: `crypt`.
2. Top navigation: Docs, Architecture, Research, Backtester.
3. Search.
4. Section sidebar.
5. Page content.
6. Source links and local context.

### Layout

- Desktop: top nav, left sidebar, content column, optional right table of
  contents.
- Mobile: top nav with collapsed section navigation, search, then content.

### Components

- TopNav.
- SearchBox.
- DocsSidebar.
- TableOfContents.
- MarkdownContent.
- SafetyCallout.
- SourceLink.

### States

- normal;
- mobile menu open;
- search focused;
- search no results;
- missing content;
- long code overflow.

### Responsive Behavior

Sidebar collapses on mobile. Content remains the priority. Code blocks scroll
horizontally when needed. Diagrams stack into readable flows.

## Home

### Purpose

Orient readers and route them into documentation quickly.

### User Goals

- Understand the project in one screen.
- Start with the right docs section.
- See that live execution is active but bounded by safety rules.

### Primary Action

Search or select a documentation route.

### Information Hierarchy

1. Short intro for `crypt`.
2. Cartoon execution room hero illustration.
3. Primary docs entry grid.
4. System route highlights.
5. Safety/truth hierarchy callout.

### Sections

- Hero intro.
- Docs entry grid.
- Runtime/research/backtester route summary.
- Selected command snippets.

### Visual Emphasis

Pastel lo-fi execution room, but the docs entry grid remains the functional
center of the first screen.

## Docs Index

### Purpose

Expose the curated manual documentation structure.

### Sections

- Getting started.
- Architecture.
- Research.
- Backtester.
- Live execution.
- Setup.
- CLI.
- API/contracts.
- Archive.

### Required Interactions

Search, sidebar navigation, source links, and route cards.

## Architecture

### Purpose

Explain the system model and module boundaries.

### Sections

- System overview diagram.
- Config and data layer.
- Evaluation context.
- Engines, aggregator, and decision layer.
- Sinks and execution boundary.
- Failure model.

### Visual Emphasis

Web-native flow diagram using semantic colors. Avoid raw terminal/dashboard
styling.

## Research

### Purpose

Explain strategy discovery, benchmark framing, donor portfolio construction,
and public archive routes.

### Sections

- Research workbench overview.
- Strategy benchmark policy.
- Candidate and router archive map.
- Owner promotion policy and known caveats.

### Visual Emphasis

Archive map and research paths should feel navigable rather than exhaustive
dumping.

## Backtester

### Purpose

Explain reproducibility, strict regression checkpoints, and live/backtest
parity expectations.

### Sections

- Backtester role.
- Canonical regression checks.
- Phase B/C live reconciliation framing.
- No look-ahead and closed-candle safety callouts.
- Commands.

### Visual Emphasis

Mint/reproducibility semantics with prominent correctness callouts.

## Live Execution

### Purpose

Explain live OKX execution as an active public project capability without
exposing private operational state.

### Sections

- Runtime truth hierarchy.
- Sync and dirty-state blocking.
- Orders and fills.
- Persistent state.
- Telegram reporting.
- Railway/deployment context.
- Public-safe limitations.

### Visual Emphasis

The richest visual treatment: cartoon execution room and runtime flow diagram.

## Setup / CLI / API

### Purpose

Give developers practical entry points without exposing private runtime data.

### Sections

- Local setup.
- Research smoke command.
- Full-history backtest command.
- Dry-run live execution command.
- CLI reference.
- Internal data contracts and API-like module boundaries.

### Visual Emphasis

Readable code blocks, precise source links, minimal decoration.
