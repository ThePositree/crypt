# Public Docs Platform Flow

- Date: 2026-09-01
- Status: proposed for implementation approval
- Related visual direction:
  `docs/frontend/visual-references/boards/board-05-docs-town.png`

## Navigation Model

```text
Home / Docs Town
  -> Topic navigation
     -> Overview
     -> Architecture
     -> Strategy Lifecycle
     -> Backtester
     -> Live Execution
     -> Glossary
     -> For Developers
     -> For Crypto Traders
     -> Risk & Limits
  -> Journey navigation
     -> Developer path
     -> Crypto Trader path
  -> Interactive map node
     -> subsystem page
     -> related guides
     -> glossary terms
  -> Global search
     -> grouped results
     -> result detail page
     -> empty/error recovery
  -> Version selector
     -> same route in selected semver when available
     -> version index fallback
```

## Developer Journey

- Actor and starting state: a developer arrives from the repository and needs
  to understand the Python system before running anything.
- Action: open the home page, scan Docs Town, choose `For Developers` or click
  a map node such as `Backtest Lab`.
- Decision, permission, or data condition: no auth; all content is public and
  curated. Search only returns public site entries.
- Content, capability, or discovery coverage required by the step: overview,
  architecture, backtester guide, source-linked module references, glossary,
  command/output/explanation steps.
- Resulting state and user-visible feedback: selected map node highlights,
  related docs update, and guide cards show next steps.
- Failure and recovery path: if search has no result, show suggested entry
  points and explain that only curated public docs are indexed. If the search
  API fails, show retry and topic navigation fallback.
- Endpoint: developer reaches a subsystem page or guide with enough context to
  inspect the linked source code.

## Crypto-Trader Journey

- Actor and starting state: a crypto-native reader wants to understand the
  research process and execution boundaries without private account details.
- Action: open the home page, choose `For Crypto Traders`, click Strategy
  Studio, Backtest Lab, Report Library, and Risk Clinic.
- Decision, permission, or data condition: no private pages and no live account
  state. Public live execution page explains neutral architecture and trust
  boundaries only.
- Content, capability, or discovery coverage required by the step: strategy
  lifecycle, result reading, neutral live architecture, risk and limits,
  glossary terms for backtest, drawdown, fees, slippage, and closed candles.
- Resulting state and user-visible feedback: journey cards indicate the next
  recommended page and related glossary concepts.
- Failure and recovery path: when performance claims would require private or
  mutable evidence, copy is softened or moved to Risk & Limits.
- Endpoint: reader understands what the system studies, how results are tested,
  and which claims are intentionally not made.

## Global Search Flow

- Actor and starting state: reader knows a word or subsystem but not the page.
- Action: focus `Search all public docs`, type a query, review grouped
  results, and open a result.
- Decision, permission, or data condition: backend route searches the curated
  public index for the selected docs version.
- Content coverage required: pages, guide steps, glossary terms, architecture
  nodes, concepts, module references, tags, headings, and body summaries.
- Resulting state and feedback: loading state appears, results are grouped by
  type, and each result shows route, type, version, excerpt, and match reason.
- Failure and recovery path: no results suggests related broad terms; API error
  offers retry and topic navigation.
- Endpoint: selected result opens; query state may be preserved in the search
  route.

## Version Flow

- Actor and starting state: reader wants docs for a semver version.
- Action: open version selector and choose a version.
- Decision, permission, or data condition: if the same slug exists for that
  version, navigate there; otherwise use the selected version index.
- Resulting state and feedback: active version label updates and content scope
  is visible.
- Failure and recovery path: missing page shows available versions and the
  nearest current page.
- Endpoint: reader understands which docs version they are reading.
