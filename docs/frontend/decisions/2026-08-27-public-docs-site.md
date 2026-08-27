# Public Documentation Site Direction

## Context

The repository had no active frontend product surface. The owner requested a
local-only public documentation site for developers and crypto-native readers.
The owner selected Next.js, Tailwind CSS, pnpm, oxlint, oxfmt, and Ultracite,
and requested a production-grade documentation platform rather than an MVP.

## Decision

Build `crypt` as an English-only public documentation platform with:

- short intro plus fast documentation entry on the home page;
- top navigation for Docs, Architecture, Research, and Backtester;
- separate routes for major documentation domains;
- manual curated information architecture;
- source-backed content copied or transformed into frontend content structure;
- full-text search;
- left sidebar navigation inside docs sections;
- syntax highlighting;
- web-native diagrams for architecture and live runtime flow;
- public live execution coverage including runtime flow, without secrets or
  private operational state;
- hidden changelog and task documents.

The owner selected `Board 5: Cartoon Execution Room` as the visual direction:
pastel lo-fi docs platform with a primary hero illustration showing a
public-safe execution room.

## Consequences

- Implementation should prioritize docs completeness, navigation quality, and
  source-backed content over marketing copy.
- The live execution page may be visually prominent, but research and
  backtester pages must remain equally substantial.
- Safety callouts are required anywhere readers could confuse prose docs with
  runtime truth or infer profit promises.
- Public pages must not expose credentials, balances, private runtime
  configuration, task history, or changelog history.
